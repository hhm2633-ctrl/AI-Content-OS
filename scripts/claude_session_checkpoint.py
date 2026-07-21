"""Local, disabled-by-default operational session checkpoints.

Only caller-supplied, allowlisted operational metadata is persisted.  This
utility never reads prompts, transcripts, tool payloads, environment variables,
browser state, credentials, or hidden reasoning.  Importing the module has no
side effects; no path is created until an enabled configuration is explicitly
used to record a valid event.

CLI example (activation is intentionally separate from this foundation)::

    py scripts/claude_session_checkpoint.py --event assignment \
      --metadata-json '{"session_id":"s1","occurred_at":"2026-07-16T10:00:00+09:00","task_id":"t1"}'

The command prints one structured JSON result and returns zero even when a
checkpoint is disabled or cannot be written, so a future hook cannot fail the
parent session.  Invalid command syntax is also converted to a structured,
nonfatal result.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


CHECKPOINT_SCHEMA_VERSION = "claude_session_checkpoint_v1"
CONFIG_SCHEMA_VERSION = "claude_session_checkpoint_config_v1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPOSITORY_ROOT / "config" / "claude_session_checkpoint.json"

ACCEPTED_EVENTS = frozenset({
    "assignment",
    "complete",
    "blocked",
    "precompact",
    "session_start",
    "session_end",
})

STRING_FIELDS = frozenset({
    "session_id",
    "occurred_at",
    "task_id",
    "task_name",
    "lane_id",
    "agent_id",
    "status",
    "reason_code",
    "note",
    "next_action",
})
LIST_FIELDS = frozenset({"owned_files", "changed_files", "blocker_codes"})
PATH_LIST_FIELDS = frozenset({"owned_files", "changed_files"})
ALLOWED_METADATA_FIELDS = STRING_FIELDS | LIST_FIELDS

FIELD_LIMITS = {
    "session_id": 160,
    "occurred_at": 80,
    "task_id": 160,
    "task_name": 240,
    "lane_id": 160,
    "agent_id": 160,
    "status": 64,
    "reason_code": 160,
    "note": 500,
    "next_action": 320,
    "list_item": 320,
}

SECRET_PATTERN = re.compile(
    r"(?i)(authorization\s*:|bearer\s+[a-z0-9]|api[_-]?key\s*[:=]|"
    r"password\s*[:=]|secret\s*[:=]|cookie\s*[:=]|sk-[a-z0-9]{12,})"
)


def _result(status: str, reason_code: str, **values: Any) -> Dict[str, Any]:
    result = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "status": status,
        "reason_code": reason_code,
        "written": status == "ok",
    }
    result.update(values)
    return result


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _aware_timestamp(value: Any) -> bool:
    raw = _text(value)
    if not raw:
        return False
    try:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, OverflowError):
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _safe_repository_path(raw_path: Any) -> Optional[Path]:
    """Resolve a configured output path while keeping it inside the repository."""
    value = _text(raw_path)
    if not value:
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    try:
        resolved = (REPOSITORY_ROOT / relative).resolve(strict=False)
        resolved.relative_to(REPOSITORY_ROOT)
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved


def _safe_metadata_path(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and ":" not in value


def _contains_secret(value: str) -> bool:
    return SECRET_PATTERN.search(value) is not None


def _load_config(config_path: Any) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Load config without raising; the config itself must also be repository-bounded."""
    try:
        candidate = Path(config_path)
        if not candidate.is_absolute():
            candidate = REPOSITORY_ROOT / candidate
        candidate = candidate.resolve(strict=False)
        candidate.relative_to(REPOSITORY_ROOT)
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, _result("closed", "unsafe_config_path")
    try:
        with candidate.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, TypeError, ValueError) as exc:
        return None, _result("fallback", "config_load_failed", error_type=type(exc).__name__)
    if not isinstance(config, Mapping) or config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        return None, _result("closed", "invalid_config_schema")
    return dict(config), None


def _validate_metadata(
    event: Any,
    metadata: Any,
    config: Mapping[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    event_name = _text(event).lower()
    configured_events = config.get("accepted_events")
    if event_name not in ACCEPTED_EVENTS:
        return None, _result("closed", "unsupported_event")
    if not isinstance(configured_events, list) or event_name not in configured_events:
        return None, _result("closed", "event_disabled_by_config")
    if not isinstance(metadata, Mapping):
        return None, _result("closed", "metadata_must_be_object")

    unknown_fields = sorted(set(metadata) - ALLOWED_METADATA_FIELDS)
    if unknown_fields:
        return None, _result("closed", "unsupported_metadata_field", fields=unknown_fields)
    if not _text(metadata.get("session_id")):
        return None, _result("closed", "missing_session_id")
    if not _aware_timestamp(metadata.get("occurred_at")):
        return None, _result("closed", "invalid_occurred_at")
    if event_name in {"assignment", "complete"} and not any(
        _text(metadata.get(field)) for field in ("task_id", "task_name", "lane_id")
    ):
        return None, _result("closed", "missing_task_identity")
    if event_name == "blocked" and not (
        _text(metadata.get("reason_code")) or metadata.get("blocker_codes")
    ):
        return None, _result("closed", "missing_blocker_code")

    maximum_list_items = config.get("maximum_list_items", 40)
    if isinstance(maximum_list_items, bool) or not isinstance(maximum_list_items, int):
        return None, _result("closed", "invalid_config_limits")
    maximum_list_items = max(1, min(maximum_list_items, 100))

    cleaned: Dict[str, Any] = {}
    for field in sorted(metadata):
        value = metadata[field]
        if field in STRING_FIELDS:
            if not isinstance(value, str):
                return None, _result("closed", "invalid_metadata_type", field=field)
            normalized = value.strip()
            if len(normalized) > FIELD_LIMITS[field]:
                return None, _result("closed", "metadata_value_too_long", field=field)
            if _contains_secret(normalized):
                return None, _result("closed", "secret_like_metadata_rejected", field=field)
            if normalized:
                cleaned[field] = normalized
            continue

        if not isinstance(value, list) or len(value) > maximum_list_items:
            return None, _result("closed", "invalid_metadata_list", field=field)
        normalized_items = []
        seen = set()
        for item in value:
            normalized = _text(item)
            if (
                not normalized
                or len(normalized) > FIELD_LIMITS["list_item"]
                or _contains_secret(normalized)
                or (field in PATH_LIST_FIELDS and not _safe_metadata_path(normalized))
            ):
                return None, _result("closed", "invalid_metadata_list_item", field=field)
            if normalized not in seen:
                seen.add(normalized)
                normalized_items.append(normalized)
        cleaned[field] = normalized_items

    record = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "event": event_name,
        "metadata": cleaned,
    }
    maximum_record_bytes = config.get("maximum_record_bytes", 16384)
    if isinstance(maximum_record_bytes, bool) or not isinstance(maximum_record_bytes, int):
        return None, _result("closed", "invalid_config_limits")
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > max(1024, min(maximum_record_bytes, 65536)):
        return None, _result("closed", "record_too_large")
    return record, None


def _prepare_output_path(path: Path) -> bool:
    """Create the parent and re-check resolution to reject repository escapes/symlinks."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.resolve(strict=False).relative_to(REPOSITORY_ROOT)
        path.parent.resolve(strict=True).relative_to(REPOSITORY_ROOT)
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _append_jsonl(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(payload + b"\n")
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("append returned no bytes")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, payload: bytes) -> None:
    temporary_name: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(payload + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass


def record_checkpoint(
    event: Any,
    metadata: Any,
    config_path: Any = DEFAULT_CONFIG_PATH,
) -> Dict[str, Any]:
    """Append one validated record and atomically replace the latest snapshot.

    All failures are returned as structured results.  No exception is intended
    to escape into a future session hook.
    """
    try:
        config, config_error = _load_config(config_path)
        if config_error or config is None:
            return config_error or _result("fallback", "config_unavailable")
        if config.get("enabled") is not True:
            return _result("disabled", "checkpoint_disabled")
        if config.get("automatic_hooks_enabled") is True and config.get("owner_approved") is not True:
            return _result("closed", "automatic_hooks_require_owner_approval")

        record, validation_error = _validate_metadata(event, metadata, config)
        if validation_error or record is None:
            return validation_error or _result("closed", "invalid_record")
        history_path = _safe_repository_path(config.get("history_path"))
        latest_path = _safe_repository_path(config.get("latest_path"))
        if history_path is None or latest_path is None or history_path == latest_path:
            return _result("closed", "unsafe_output_path")
        if not _prepare_output_path(history_path) or not _prepare_output_path(latest_path):
            return _result("fallback", "output_path_unavailable")

        payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        _append_jsonl(history_path, payload)
        _atomic_json(latest_path, payload)
        return _result(
            "ok",
            "checkpoint_recorded",
            event=record["event"],
            history_path=history_path.relative_to(REPOSITORY_ROOT).as_posix(),
            latest_path=latest_path.relative_to(REPOSITORY_ROOT).as_posix(),
        )
    except Exception as exc:  # Hook contract: unexpected local failures remain nonfatal.
        return _result("fallback", "checkpoint_write_failed", error_type=type(exc).__name__)


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record a bounded local Claude session checkpoint")
    parser.add_argument("--event")
    parser.add_argument("--metadata-json")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        arguments = _argument_parser().parse_args(argv)
    except SystemExit:
        print(json.dumps(_result("closed", "invalid_cli_arguments"), ensure_ascii=False, sort_keys=True))
        return 0
    if not arguments.event or arguments.metadata_json is None:
        result = _result("closed", "missing_cli_arguments")
    else:
        try:
            metadata = json.loads(arguments.metadata_json)
        except (TypeError, ValueError):
            result = _result("closed", "invalid_metadata_json")
        else:
            result = record_checkpoint(arguments.event, metadata, arguments.config)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
