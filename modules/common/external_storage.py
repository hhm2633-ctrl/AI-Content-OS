"""Configuration-backed paths for new heavy AI-Content-OS artifacts.

Lightweight workflow/index JSON remains in the repository.  Callers use this
module only for raw media, rendered CardNews files, and other large artifacts.
Path resolution is read-only by default; directories are created only when a
caller explicitly requests a write path.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Union


PathLike = Union[str, os.PathLike[str]]

DEFAULT_CONFIG_PATH = Path("config/source_data_storage.json")
DEFAULT_EXTERNAL_ROOT = Path("F:/AI-Content-OS-Data")
DEFAULT_FALLBACK_ROOT = Path("artifacts/_external_storage_fallback")
DEFAULT_BUCKETS = {
    "source_data": "source_intake",
    "card_news": "card_news",
    "artifacts": "artifacts",
}


class ExternalStorageUnavailableError(RuntimeError):
    """Raised when heavy external storage is enabled but unreachable.

    Fail-closed by design: when the owner has *not* explicitly disabled
    heavy external storage (``enabled: false`` in config), a large write
    must never be silently redirected back onto the repository disk.
    Callers that genuinely need a local fallback for this case must opt in
    explicitly via ``allow_local_fallback=True``.
    """


@dataclass(frozen=True)
class ExternalStorageResolution:
    """Resolved heavy-storage directory and its fallback provenance."""

    path: Path
    root: Path
    bucket: str
    fallback_used: bool
    reason: str = ""


def _read_config(config_path: Path) -> Mapping[str, Any]:
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _config_base(config_path: Path) -> Path:
    """Return the repository-like base for relative configured paths."""
    parent = config_path.parent
    return parent.parent if parent.name.lower() == "config" else parent


def _absolute_or_based(path_value: Any, base: Path, default: Path) -> Path:
    text = str(path_value or "").strip()
    path = Path(text) if text else default
    if path.is_absolute() or path.drive:
        return path
    return base / path


def _root_is_available(root: Path) -> bool:
    """Check only the existing anchor; never create a directory while reading."""
    if not root.is_absolute() and not root.drive:
        return True
    anchor = Path(root.anchor) if root.anchor else root
    return anchor.exists()


def _safe_parts(parts: tuple[PathLike, ...]) -> tuple[str, ...]:
    safe: list[str] = []
    for raw_part in parts:
        part = Path(raw_part)
        if part.is_absolute() or part.drive or ".." in part.parts:
            raise ValueError(f"external storage subpath must stay relative: {raw_part}")
        safe.extend(piece for piece in part.parts if piece not in ("", "."))
    return tuple(safe)


def resolve_external_storage(
    bucket: str,
    *parts: PathLike,
    config_path: PathLike = DEFAULT_CONFIG_PATH,
    create: bool = False,
    allow_local_fallback: bool = False,
) -> ExternalStorageResolution:
    """Resolve a directory beneath a configured heavy-storage bucket.

    ``bucket`` is one of ``source_data``, ``card_news``, or ``artifacts`` by
    default.  ``create=False`` performs no filesystem writes.

    Fail-closed contract for ``create=True``:
      * If the owner explicitly disabled heavy external storage in config
        (``enabled: false``), the repository-local fallback is used, same
        as before -- this is an intentional owner choice, not a failure.
      * If heavy external storage is *enabled* but unreachable (drive not
        mounted, or directory creation fails), this function raises
        :class:`ExternalStorageUnavailableError` instead of silently
        writing large data back onto the repository disk. Pass
        ``allow_local_fallback=True`` to opt into the old silent-fallback
        behavior for a specific call site that has already reviewed the
        risk (e.g. small operational receipts, not bulk media).
    """
    config_file = Path(config_path)
    config = _read_config(config_file)
    heavy_config = config.get("external_heavy_storage", {})
    if not isinstance(heavy_config, dict):
        heavy_config = {}

    configured_buckets = heavy_config.get("buckets", {})
    buckets = dict(DEFAULT_BUCKETS)
    if isinstance(configured_buckets, dict):
        buckets.update(
            {
                str(key): str(value)
                for key, value in configured_buckets.items()
                if str(key).strip() and str(value).strip()
            }
        )
    if bucket not in buckets:
        raise ValueError(f"unknown external storage bucket: {bucket}")

    base = _config_base(config_file)
    primary_value = heavy_config.get("root", config.get("source_data_root"))
    primary_root = _absolute_or_based(primary_value, base, DEFAULT_EXTERNAL_ROOT)
    fallback_root = _absolute_or_based(
        heavy_config.get("fallback_root"), base, DEFAULT_FALLBACK_ROOT
    )
    relative_parts = _safe_parts(parts)
    bucket_part = _safe_parts((buckets[bucket],))

    enabled = heavy_config.get("enabled", True) is not False
    disabled_by_owner = not enabled
    root_unreachable = enabled and not _root_is_available(primary_root)
    fallback_used = disabled_by_owner or root_unreachable
    reason = "external_storage_disabled" if disabled_by_owner else ""
    if root_unreachable:
        reason = "external_root_unavailable"

    selected_root = fallback_root if fallback_used else primary_root
    target = selected_root.joinpath(*bucket_part, *relative_parts)

    if create:
        if root_unreachable and not disabled_by_owner and not allow_local_fallback:
            raise ExternalStorageUnavailableError(
                "Heavy external storage is enabled but unreachable at "
                f"'{primary_root}'. Refusing to write bucket '{bucket}' to the "
                "repository disk. Reconnect the external drive, or pass "
                "allow_local_fallback=True if this call site has reviewed "
                "the risk of a local write."
            )
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            if fallback_used:
                raise
            if not allow_local_fallback:
                raise ExternalStorageUnavailableError(
                    "Heavy external storage directory creation failed for "
                    f"bucket '{bucket}' at '{primary_root}' "
                    f"({type(error).__name__}: {error}). Refusing to fall "
                    "back to a repository-local write. Pass "
                    "allow_local_fallback=True to opt in explicitly."
                ) from error
            fallback_used = True
            reason = f"external_create_failed:{type(error).__name__}"
            selected_root = fallback_root
            target = selected_root.joinpath(*bucket_part, *relative_parts)
            target.mkdir(parents=True, exist_ok=True)

    return ExternalStorageResolution(
        path=target,
        root=selected_root,
        bucket=bucket,
        fallback_used=fallback_used,
        reason=reason,
    )


def resolve_external_path(
    bucket: str,
    *parts: PathLike,
    config_path: PathLike = DEFAULT_CONFIG_PATH,
    create: bool = False,
    allow_local_fallback: bool = False,
) -> Path:
    """Convenience API returning only the resolved directory path."""
    return resolve_external_storage(
        bucket,
        *parts,
        config_path=config_path,
        create=create,
        allow_local_fallback=allow_local_fallback,
    ).path


def resolve_heavy_path(
    bucket: str,
    *parts: PathLike,
    config_path: PathLike = DEFAULT_CONFIG_PATH,
    create: bool = False,
    allow_local_fallback: bool = False,
) -> Path:
    """Readable alias retained for callers describing heavy output routing."""
    return resolve_external_path(
        bucket,
        *parts,
        config_path=config_path,
        create=create,
        allow_local_fallback=allow_local_fallback,
    )

