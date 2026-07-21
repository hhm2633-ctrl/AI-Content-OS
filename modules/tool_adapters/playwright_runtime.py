"""Resolve the installed Playwright Chromium runtime without launching it.

The resolver is deliberately side-effect free: it reads an environment mapping,
checks regular files, and returns diagnostics.  It never changes environment
variables, imports Playwright, downloads a browser, or starts a process.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
from typing import Mapping, Sequence


PLAYWRIGHT_EXECUTABLE_ENV = "PLAYWRIGHT_CHROMIUM_EXECUTABLE"
PLAYWRIGHT_BROWSERS_PATH_ENV = "PLAYWRIGHT_BROWSERS_PATH"
DEFAULT_PLAYWRIGHT_BROWSERS_PATH = Path(
    r"F:\AI-Content-OS-Data\tools\playwright-browsers"
)

_HEADLESS_PREFIX = "chromium_headless_shell-"
_CHROMIUM_PREFIX = "chromium-"
_HEADLESS_RELATIVE_EXECUTABLE = Path(
    "chrome-headless-shell-win64", "chrome-headless-shell.exe"
)
_CHROMIUM_RELATIVE_EXECUTABLE = Path("chrome-win64", "chrome.exe")


@dataclass(frozen=True)
class PlaywrightRuntimeResolution:
    """Serializable readiness result for a local Playwright executable."""

    ready: bool
    executable_path: str
    browser_root: str
    source: str
    diagnostics: tuple[str, ...]
    checked_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _clean_path(value: object) -> Path | None:
    text = str(value or "").strip().strip('"')
    return Path(text).expanduser() if text else None


def _revision_key(path: Path, prefix: str) -> tuple[int, str]:
    suffix = path.name[len(prefix) :]
    try:
        revision = int(suffix)
    except ValueError:
        revision = -1
    return revision, path.name.casefold()


def _candidate_paths(root: Path) -> tuple[Path, ...]:
    """Return deterministic candidates, preferring the headless runtime."""

    families: Sequence[tuple[str, Path]] = (
        (_HEADLESS_PREFIX, _HEADLESS_RELATIVE_EXECUTABLE),
        (_CHROMIUM_PREFIX, _CHROMIUM_RELATIVE_EXECUTABLE),
    )
    candidates: list[Path] = []
    for prefix, relative_executable in families:
        try:
            directories = sorted(
                (
                    path
                    for path in root.glob(f"{prefix}*")
                    if path.is_dir()
                ),
                key=lambda path: _revision_key(path, prefix),
                reverse=True,
            )
        except OSError:
            directories = []
        candidates.extend(path / relative_executable for path in directories)

    # These exact verified-layout paths make missing-store diagnostics useful
    # even when the root itself or all revision directories are absent.
    if not candidates:
        candidates.extend(
            (
                root / f"{_HEADLESS_PREFIX}1228" / _HEADLESS_RELATIVE_EXECUTABLE,
                root / f"{_CHROMIUM_PREFIX}1228" / _CHROMIUM_RELATIVE_EXECUTABLE,
            )
        )
    return tuple(candidates)


def _readiness_error(path: Path) -> str | None:
    try:
        if not path.exists():
            return "missing"
        if not path.is_file():
            return "not_regular_file"
        if path.suffix.casefold() != ".exe":
            return "not_windows_executable"
        if path.stat().st_size <= 0:
            return "empty_file"
    except OSError as exc:
        return f"filesystem_error:{type(exc).__name__}:{exc}"
    return None


def resolve_playwright_runtime(
    *,
    env: Mapping[str, str] | None = None,
    default_browser_root: str | Path = DEFAULT_PLAYWRIGHT_BROWSERS_PATH,
) -> PlaywrightRuntimeResolution:
    """Resolve a ready Chromium executable from overrides or the F: default.

    Precedence is strict and deterministic:

    1. ``PLAYWRIGHT_CHROMIUM_EXECUTABLE`` (a direct executable override),
    2. ``PLAYWRIGHT_BROWSERS_PATH`` (a Playwright browser-store override),
    3. :data:`DEFAULT_PLAYWRIGHT_BROWSERS_PATH`.

    A configured direct override never silently falls back.  This makes a
    stale deployment setting visible instead of unexpectedly selecting another
    browser installation.
    """

    environment = os.environ if env is None else env
    executable_override = _clean_path(environment.get(PLAYWRIGHT_EXECUTABLE_ENV))
    if executable_override is not None:
        error = _readiness_error(executable_override)
        diagnostics = () if error is None else (
            f"executable_override_{error}:{executable_override}",
        )
        return PlaywrightRuntimeResolution(
            ready=error is None,
            executable_path=str(executable_override) if error is None else "",
            browser_root=str(executable_override.parent),
            source="environment_executable",
            diagnostics=diagnostics,
            checked_paths=(str(executable_override),),
        )

    root_override = _clean_path(environment.get(PLAYWRIGHT_BROWSERS_PATH_ENV))
    root = root_override or Path(default_browser_root).expanduser()
    source = "environment_browser_root" if root_override else "default_browser_root"
    candidates = _candidate_paths(root)
    diagnostics: list[str] = []
    if not root.is_dir():
        diagnostics.append(f"browser_root_missing:{root}")

    for candidate in candidates:
        error = _readiness_error(candidate)
        if error is None:
            return PlaywrightRuntimeResolution(
                ready=True,
                executable_path=str(candidate),
                browser_root=str(root),
                source=source,
                diagnostics=tuple(diagnostics),
                checked_paths=tuple(str(path) for path in candidates),
            )
        diagnostics.append(f"candidate_{error}:{candidate}")

    diagnostics.append(
        "playwright_executable_missing:"
        + "|".join(str(path) for path in candidates)
    )
    return PlaywrightRuntimeResolution(
        ready=False,
        executable_path="",
        browser_root=str(root),
        source=source,
        diagnostics=tuple(diagnostics),
        checked_paths=tuple(str(path) for path in candidates),
    )


def resolve_playwright_executable(
    *,
    env: Mapping[str, str] | None = None,
    default_browser_root: str | Path = DEFAULT_PLAYWRIGHT_BROWSERS_PATH,
) -> str:
    """Return the resolved executable or an empty string when not ready."""

    return resolve_playwright_runtime(
        env=env,
        default_browser_root=default_browser_root,
    ).executable_path


__all__ = [
    "DEFAULT_PLAYWRIGHT_BROWSERS_PATH",
    "PLAYWRIGHT_BROWSERS_PATH_ENV",
    "PLAYWRIGHT_EXECUTABLE_ENV",
    "PlaywrightRuntimeResolution",
    "resolve_playwright_executable",
    "resolve_playwright_runtime",
]
