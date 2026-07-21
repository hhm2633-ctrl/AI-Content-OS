"""Static SeaweedFS CLI readiness probe that never starts a service."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
from typing import Mapping


SEAWEEDFS_EXECUTABLE_ENV = "SEAWEEDFS_EXECUTABLE"
DEFAULT_SEAWEEDFS_EXECUTABLE = Path(
    r"F:\AI-Content-OS-Data\tools\seaweedfs\4.39\weed.exe"
)
_LICENSE_NAMES = ("LICENSE", "LICENSE.txt", "COPYING", "NOTICE")


@dataclass(frozen=True)
class SeaweedFSRuntime:
    ready: bool
    executable_path: str
    version: str
    platform: str
    license: str
    license_path: str
    source: str
    diagnostics: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _version_from_path(path: Path) -> str:
    parent_name = path.parent.name.strip()
    return parent_name if parent_name and parent_name[0].isdigit() else ""


def resolve_seaweedfs_runtime(
    *, env: Mapping[str, str] | None = None
) -> SeaweedFSRuntime:
    environment = os.environ if env is None else env
    override = str(environment.get(SEAWEEDFS_EXECUTABLE_ENV, "")).strip().strip('"')
    executable = Path(override).expanduser() if override else DEFAULT_SEAWEEDFS_EXECUTABLE
    source = "environment_executable" if override else "default_executable"
    diagnostics: list[str] = []
    if not executable.exists():
        diagnostics.append(f"executable_missing:{executable}")
    elif not executable.is_file():
        diagnostics.append(f"executable_not_regular_file:{executable}")
    elif executable.suffix.casefold() != ".exe":
        diagnostics.append(f"not_windows_executable:{executable}")
    elif executable.stat().st_size <= 0:
        diagnostics.append(f"executable_empty:{executable}")

    license_path = next(
        (executable.parent / name for name in _LICENSE_NAMES if (executable.parent / name).is_file()),
        None,
    )
    if license_path is None:
        diagnostics.append(f"license_file_missing:{executable.parent}")

    # A missing adjacent license is reported for compliance but does not make
    # the CLI binary unusable.  No process is run to infer additional metadata.
    executable_ready = not any(
        diagnostic.startswith(("executable_", "not_windows_executable:"))
        for diagnostic in diagnostics
    )
    return SeaweedFSRuntime(
        ready=executable_ready,
        executable_path=str(executable) if executable_ready else "",
        version=_version_from_path(executable),
        platform="windows-amd64" if executable_ready else "",
        license="locally_verified" if license_path else "unverified",
        license_path=str(license_path) if license_path else "",
        source=source,
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "DEFAULT_SEAWEEDFS_EXECUTABLE",
    "SEAWEEDFS_EXECUTABLE_ENV",
    "SeaweedFSRuntime",
    "resolve_seaweedfs_runtime",
]
