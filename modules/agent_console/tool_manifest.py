"""Allow-listed, deferred tool registry.

Factories are invoked only when ``load`` is explicitly called. Merely rendering
the manifest never connects to MCP servers or reads tool credentials.
"""

from __future__ import annotations

import shutil
import subprocess
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping

from modules.agent_console.tool_assignment_policy import assign_deferred_tools


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    provider: str
    purpose: str
    mode: str = "read_only"

    def to_dict(self, available: bool) -> Dict[str, Any]:
        payload = asdict(self)
        payload["deferred"] = True
        payload["loader_registered"] = available
        return payload


class LazyToolRegistry:
    """Register descriptors and factories without eagerly creating tool clients."""

    def __init__(self) -> None:
        self._specs: Dict[str, ToolSpec] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._loaded: Dict[str, Any] = {}

    def register(self, spec: ToolSpec, factory: Callable[[], Any] | None = None) -> None:
        if not spec.tool_id.strip():
            raise ValueError("tool_id is required")
        self._specs[spec.tool_id] = spec
        if factory is not None:
            self._factories[spec.tool_id] = factory

    def manifest(self, allowed_tools: Iterable[str] | None = None) -> Dict[str, Dict[str, Any]]:
        allow = set(allowed_tools) if allowed_tools is not None else set(self._specs)
        return {
            tool_id: self._specs[tool_id].to_dict(tool_id in self._factories)
            for tool_id in sorted(self._specs)
            if tool_id in allow
        }

    def load(self, tool_id: str, allowed_tools: Iterable[str]) -> Any:
        if tool_id not in set(allowed_tools):
            raise PermissionError(f"tool not allowed for agent: {tool_id}")
        if tool_id not in self._specs:
            raise KeyError(f"unknown tool: {tool_id}")
        if tool_id not in self._factories:
            raise RuntimeError(f"tool adapter is not connected: {tool_id}")
        if tool_id not in self._loaded:
            self._loaded[tool_id] = self._factories[tool_id]()
        return self._loaded[tool_id]

    @property
    def loaded_tool_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._loaded))

    def assign_for_job(
        self,
        job: Mapping[str, Any],
        *,
        allowed_tools: Iterable[str],
        requested_tools: Iterable[str] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Resolve a job policy without loading any registered adapter."""

        return assign_deferred_tools(
            job,
            allowed_tools=allowed_tools,
            requested_tools=requested_tools,
            context=context,
            registered_tools=self._specs,
        )


class BoundedFilesystemAdapter:
    """Read-only filesystem access constrained to one repository root."""

    def __init__(self, root: str | Path, *, max_bytes: int = 200_000) -> None:
        self.root = Path(root).resolve()
        self.max_bytes = max_bytes

    def _resolve(self, relative_path: str | Path) -> Path:
        requested = Path(relative_path)
        if requested.is_absolute():
            raise PermissionError("absolute paths are not allowed")
        resolved = (self.root / requested).resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise PermissionError("path must stay inside the repository")
        return resolved

    def read_text(self, relative_path: str | Path) -> str:
        resolved = self._resolve(relative_path)
        if resolved.stat().st_size > self.max_bytes:
            raise ValueError(f"file exceeds read limit: {self.max_bytes} bytes")
        return resolved.read_text(encoding="utf-8")

    def list_names(self, relative_path: str | Path = ".") -> list[str]:
        resolved = self._resolve(relative_path)
        return sorted(entry.name for entry in resolved.iterdir())


def graphify_output_root(
    root: str | Path, *, config_path: str | Path = "config/source_data_storage.json"
) -> Path:
    """Resolve where Graphify's graph/cache output lives.

    Precedence: an already-set ``GRAPHIFY_OUT`` environment variable (the
    caller's own explicit choice) > a configured
    ``external_heavy_storage.graphify_output_root`` > the repository-relative
    ``graphify-out`` default (today's unchanged behavior). This keeps current
    installs working as-is until an owner-approved migration sets the config
    key and moves the existing graph data.
    """
    repo_root = Path(root).resolve()
    env_value = os.environ.get("GRAPHIFY_OUT", "").strip()
    if env_value:
        return Path(env_value)
    config_file = repo_root / Path(config_path)
    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        config = {}
    heavy = config.get("external_heavy_storage", {})
    configured = heavy.get("graphify_output_root") if isinstance(heavy, dict) else None
    if isinstance(configured, str) and configured.strip():
        candidate = Path(configured.strip())
        return candidate if candidate.is_absolute() or candidate.drive else repo_root / candidate
    return repo_root / "graphify-out"


class GraphifyCliAdapter:
    """Scoped Graphify CLI calls with no shell interpolation."""

    def __init__(self, root: str | Path, *, timeout_seconds: int = 60) -> None:
        self.root = Path(root).resolve()
        self.executable = shutil.which("graphify")
        self.timeout_seconds = timeout_seconds
        self.output_root = graphify_output_root(self.root)
        if not self.executable:
            raise RuntimeError("graphify executable is not available")
        if not (self.output_root / "graph.json").exists():
            raise RuntimeError(f"{self.output_root / 'graph.json'} is not available")

    def _run(self, *arguments: str) -> str:
        environment = dict(os.environ)
        environment["GRAPHIFY_OUT"] = str(self.output_root)
        result = subprocess.run(
            [self.executable, *arguments],
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_seconds,
            env=environment,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "graphify command failed").strip()
            raise RuntimeError(detail[:1000])
        return result.stdout

    def query(self, question: str) -> str:
        return self._run("query", question)

    def explain(self, concept: str) -> str:
        return self._run("explain", concept)

    def path(self, source: str, target: str) -> str:
        return self._run("path", source, target)


class FocusedProjectCliAdapter:
    """Only the two focused Agent Console validation commands are callable."""

    def __init__(self, root: str | Path, *, timeout_seconds: int = 120) -> None:
        self.root = Path(root).resolve()
        self.timeout_seconds = timeout_seconds

    def _run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            arguments,
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_seconds,
        )

    def test_agent_console(self) -> subprocess.CompletedProcess[str]:
        return self._run(["py", "-m", "unittest", "tests.test_agent_console"])

    def compile_agent_console(self) -> subprocess.CompletedProcess[str]:
        return self._run(["py", "-m", "compileall", "modules/agent_console", "tests/test_agent_console.py"])


class HyperFramesDiagnosticsAdapter:
    """Local HyperFrames adapter with owner-gated rendering and no publishing."""

    def __init__(self, repository_root: str | Path) -> None:
        self.repository_root = Path(repository_root).resolve()
        manifest_path = self.repository_root / "config" / "external_tools" / "hyperframes_local.json"
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if self.manifest.get("status") not in {
            "diagnostics_ready_render_blocked",
            "local_render_adapter_connected_owner_gated",
        }:
            raise RuntimeError("HyperFrames diagnostics are not ready")
        self.npx = shutil.which("npx")
        if not self.npx:
            raise RuntimeError("npx is not available")
        self.package_spec = f'hyperframes@{self.manifest["runtime"]["cli_version"]}'

    def environment(self) -> dict[str, str]:
        runtime = self.manifest["runtime"]
        environment = dict(os.environ)
        environment["PATH"] = f'{runtime["ffmpeg_bin"]}{os.pathsep}{environment.get("PATH", "")}'
        environment["npm_config_cache"] = runtime["npm_cache"]
        environment.update(self.manifest.get("environment", {}))
        return environment

    def doctor(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.npx, "--offline", "--yes", self.package_spec, "doctor"],
            cwd=self.repository_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env=self.environment(),
        )

    def render_command(
        self,
        *,
        project_dir: str | Path,
        output_path: str | Path,
        composition: str | None = None,
        output_format: str = "mp4",
    ) -> list[str]:
        """Build a validated local command without starting a render."""

        if output_format not in {"mp4", "webm"}:
            raise ValueError("HyperFrames output_format must be mp4 or webm")
        project = Path(project_dir).resolve()
        output = Path(output_path).resolve()
        data_root = Path(self.manifest["upstream"]["local_root"]).resolve().parents[2]
        allowed_projects = (self.repository_root, data_root)
        if not any(project == root or root in project.parents for root in allowed_projects):
            raise PermissionError("HyperFrames project must stay inside the repository or configured F: data root")
        if output != data_root and data_root not in output.parents:
            raise PermissionError("HyperFrames renders must stay inside the configured F: data root")
        command = [
            self.npx,
            "--offline",
            "--yes",
            self.package_spec,
            "render",
            "--format",
            output_format,
            "-o",
            str(output),
        ]
        if composition:
            command.extend(["--composition", str(composition)])
        return command

    def render_local(
        self,
        *,
        project_dir: str | Path,
        output_path: str | Path,
        composition: str | None = None,
        output_format: str = "mp4",
        owner_approved: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Render locally only after an explicit owner approval is passed in."""

        if not owner_approved:
            raise PermissionError("HyperFrames render requires explicit owner approval")
        project = Path(project_dir).resolve()
        output = Path(output_path).resolve()
        command = self.render_command(
            project_dir=project,
            output_path=output,
            composition=composition,
            output_format=output_format,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        return subprocess.run(
            command,
            cwd=project,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
            env=self.environment(),
        )


def default_tool_specs() -> Mapping[str, ToolSpec]:
    """Known capabilities; adapters are intentionally not assumed connected."""

    return {
        "graphify": ToolSpec("graphify", "local_cli", "scoped codebase graph query"),
        "filesystem": ToolSpec("filesystem", "host", "bounded project file access"),
        "browser": ToolSpec("browser", "host", "read-only browser research"),
        "project_cli": ToolSpec("project_cli", "host", "approved project commands"),
        "hyperframes": ToolSpec(
            "hyperframes",
            "local_cli",
            "diagnostics and owner-gated local preview preparation",
            mode="diagnostics_only",
        ),
    }


def build_default_tool_registry(repository_root: str | Path) -> LazyToolRegistry:
    """Register real local adapters only where a bounded callable path exists."""

    root = Path(repository_root).resolve()
    registry = LazyToolRegistry()
    specs = default_tool_specs()
    registry.register(specs["filesystem"], lambda: BoundedFilesystemAdapter(root))
    if shutil.which("graphify") and (graphify_output_root(root) / "graph.json").exists():
        registry.register(specs["graphify"], lambda: GraphifyCliAdapter(root))
    else:
        registry.register(specs["graphify"])
    registry.register(specs["project_cli"], lambda: FocusedProjectCliAdapter(root))
    hyperframes_manifest = root / "config" / "external_tools" / "hyperframes_local.json"
    if hyperframes_manifest.exists() and shutil.which("npx"):
        registry.register(specs["hyperframes"], lambda: HyperFramesDiagnosticsAdapter(root))
    else:
        registry.register(specs["hyperframes"])
    # The browser available in the Codex app has no callable local Python adapter.
    registry.register(specs["browser"])
    return registry


__all__ = [
    "BoundedFilesystemAdapter",
    "FocusedProjectCliAdapter",
    "GraphifyCliAdapter",
    "HyperFramesDiagnosticsAdapter",
    "LazyToolRegistry",
    "ToolSpec",
    "build_default_tool_registry",
    "default_tool_specs",
    "graphify_output_root",
]
