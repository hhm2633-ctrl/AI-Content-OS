"""Bounded local adapter for the isolated PySceneDetect runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from email.parser import Parser
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping


PYSCENEDETECT_RUNTIME_ROOT_ENV = "PYSCENEDETECT_RUNTIME_ROOT"
DEFAULT_PYSCENEDETECT_RUNTIME_ROOT = Path(
    r"F:\AI-Content-OS-Data\external_tools\runtimes\pyscenedetect"
)
DEFAULT_FFMPEG_EXECUTABLE = Path(
    r"F:\AI-Content-OS-Data\external_tools\runtimes\ffmpeg"
    r"\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"
)
SUPPORTED_VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".mkv", ".webm", ".avi"})


@dataclass(frozen=True)
class PySceneDetectRuntime:
    ready: bool
    root: str
    python_executable: str
    package_path: str
    version: str
    license: str
    ffmpeg_executable: str
    diagnostics: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _metadata(root: Path) -> tuple[str, str]:
    candidates = sorted(
        (root / "Lib" / "site-packages").glob("scenedetect-*.dist-info/METADATA")
    )
    if not candidates:
        return "", ""
    try:
        message = Parser().parsestr(candidates[-1].read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return "", ""
    return str(message.get("Version", "")), str(
        message.get("License-Expression") or message.get("License") or ""
    )


def resolve_pyscenedetect_runtime(
    *, env: Mapping[str, str] | None = None
) -> PySceneDetectRuntime:
    environment = os.environ if env is None else env
    override = str(environment.get(PYSCENEDETECT_RUNTIME_ROOT_ENV, "")).strip().strip('"')
    root = Path(override).expanduser() if override else DEFAULT_PYSCENEDETECT_RUNTIME_ROOT
    python = root / "Scripts" / "python.exe"
    package = root / "Lib" / "site-packages" / "scenedetect" / "__init__.py"
    version, license_name = _metadata(root)
    diagnostics: list[str] = []
    if not python.is_file():
        diagnostics.append(f"python_executable_missing:{python}")
    if not package.is_file():
        diagnostics.append(f"package_missing:{package}")
    if not version:
        diagnostics.append("package_version_missing")
    if license_name != "BSD-3-Clause":
        diagnostics.append(f"license_unexpected:{license_name or 'missing'}")
    if not DEFAULT_FFMPEG_EXECUTABLE.is_file():
        diagnostics.append(f"ffmpeg_missing:{DEFAULT_FFMPEG_EXECUTABLE}")
    return PySceneDetectRuntime(
        ready=not diagnostics,
        root=str(root),
        python_executable=str(python) if python.is_file() else "",
        package_path=str(package) if package.is_file() else "",
        version=version,
        license=license_name,
        ffmpeg_executable=(
            str(DEFAULT_FFMPEG_EXECUTABLE) if DEFAULT_FFMPEG_EXECUTABLE.is_file() else ""
        ),
        diagnostics=tuple(diagnostics),
    )


_DETECT_SCRIPT = r"""
import json
import sys
from scenedetect import ContentDetector, detect
scenes = detect(sys.argv[1], ContentDetector())
print(json.dumps([
    {"start_seconds": start.get_seconds(), "end_seconds": end.get_seconds()}
    for start, end in scenes
]))
""".strip()


def detect_scenes(
    video_path: str | Path,
    *,
    timeout_seconds: int = 120,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, object]:
    path = Path(video_path).resolve()
    runtime = resolve_pyscenedetect_runtime()
    if not runtime.ready:
        return {"status": "blocked", "scenes": [], "errors": list(runtime.diagnostics)}
    if not path.is_file():
        return {"status": "blocked", "scenes": [], "errors": [f"video_missing:{path}"]}
    if path.suffix.casefold() not in SUPPORTED_VIDEO_SUFFIXES:
        return {"status": "blocked", "scenes": [], "errors": ["unsupported_video_suffix"]}
    timeout = max(1, min(int(timeout_seconds), 300))
    try:
        completed = runner(
            [runtime.python_executable, "-c", _DETECT_SCRIPT, str(path)],
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "failed", "scenes": [], "errors": [type(exc).__name__]}
    if completed.returncode != 0:
        return {
            "status": "failed",
            "scenes": [],
            "errors": [f"process_exit:{completed.returncode}", completed.stderr[-1000:]],
        }
    try:
        scenes = json.loads(completed.stdout.strip())
    except json.JSONDecodeError:
        return {"status": "failed", "scenes": [], "errors": ["invalid_json"]}
    if not isinstance(scenes, list):
        return {"status": "failed", "scenes": [], "errors": ["invalid_scene_payload"]}
    return {"status": "completed", "scenes": scenes, "errors": []}


__all__ = [
    "DEFAULT_PYSCENEDETECT_RUNTIME_ROOT",
    "PYSCENEDETECT_RUNTIME_ROOT_ENV",
    "PySceneDetectRuntime",
    "detect_scenes",
    "resolve_pyscenedetect_runtime",
]
