"""Build a tiny markdown brief from a source intake status bundle."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional


DEFAULT_SOURCE_INTAKE_ROOT = os.path.join("storage", "source_intake")
BUNDLE_FILE_NAME = "source_intake_status_bundle.json"
BRIEF_FILE_NAME = "source_intake_brief.md"


def _coerce_today(today: Optional[Any]) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    if isinstance(today, (datetime, date)):
        return today.isoformat()
    return str(today)


def _coerce_items(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    result: List[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text:
            result.append(text)
    return result


def _read_bundle(bundle_or_path: Any) -> Optional[Dict[str, Any]]:
    if isinstance(bundle_or_path, dict):
        return bundle_or_path

    if not isinstance(bundle_or_path, str):
        return None
    if not os.path.exists(bundle_or_path):
        return None

    try:
        with open(bundle_or_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None

    if isinstance(payload, dict):
        return payload
    return None


def _collect_not_implemented(bundle: Dict[str, Any]) -> List[str]:
    explicit = bundle.get("not_implemented_collectors") or bundle.get("not_implemented_sources")
    if isinstance(explicit, list):
        items = _coerce_items(explicit)
        if items:
            return items

    summary = bundle.get("status_summary", {})
    if isinstance(summary, dict):
        status_entries = summary.get("NOT_IMPLEMENTED")
        if isinstance(status_entries, list):
            status_ids = [
                str(item.get("source_id"))
                for item in status_entries
                if isinstance(item, dict) and isinstance(item.get("source_id"), str)
            ]
            if status_ids:
                return status_ids

    fallback_count = bundle.get("blockers", {}).get("not_implemented_count")
    if isinstance(fallback_count, int) and fallback_count > 0:
        return [f"count: {fallback_count}"]

    return []


def _collect_fallback_only(bundle: Dict[str, Any]) -> List[str]:
    direct = bundle.get("fallback_only_sources")
    if isinstance(direct, list):
        items = _coerce_items(direct)
        if items:
            return items

    blocked = bundle.get("blockers", {}).get("fallback_only_sources")
    return _coerce_items(blocked)


def _collect_blocked_weak_lanes(bundle: Dict[str, Any]) -> List[str]:
    for key in ("blocked_lanes", "weak_lanes"):
        values = _coerce_items(bundle.get(key))
        if values:
            return values

    blocker_payload = bundle.get("blockers", {})
    for key in ("blocked_lanes", "weak_lanes"):
        values = _coerce_items(blocker_payload.get(key))
        if values:
            return values
    return []


def _collect_top_queue_sources(bundle: Dict[str, Any]) -> List[str]:
    top_queue = _coerce_items(bundle.get("top_queue_sources"))
    if top_queue:
        return top_queue[:5]

    queue_payload = bundle.get("queue") or bundle.get("collector_implementation_queue", {})
    queue_items = queue_payload.get("implementation_queue") if isinstance(queue_payload, dict) else []
    if not isinstance(queue_items, list):
        return []

    output: List[str] = []
    for item in queue_items:
        source_id = item.get("source_id") if isinstance(item, dict) else None
        if isinstance(source_id, str) and source_id.strip():
            output.append(source_id.strip())
        if len(output) >= 5:
            break
    return output


def _format_section(title: str, values: List[str]) -> str:
    lines = [f"## {title}"]
    if not values:
        lines.append("- (none)")
    else:
        lines.extend([f"- {value}" for value in values])
    return "\n".join(lines)


def build_source_intake_brief(bundle_or_path: Any) -> str:
    """Build brief markdown from a bundle object or JSON path."""
    bundle = _read_bundle(bundle_or_path)
    if not isinstance(bundle, dict):
        return ""

    not_implemented = _collect_not_implemented(bundle)
    fallback_only = _collect_fallback_only(bundle)
    blocked_lanes = _collect_blocked_weak_lanes(bundle)
    top_queue = _collect_top_queue_sources(bundle)

    return (
        f"{_format_section('Not implemented collectors', not_implemented)}\n\n"
        f"{_format_section('Fallback only sources', fallback_only)}\n\n"
        f"{_format_section('Blocked/weak lanes', blocked_lanes)}\n\n"
        f"{_format_section('Next queue top 5', top_queue)}\n"
    )


def run_source_intake_brief(
    today: Optional[Any] = None,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    today_str = _coerce_today(today)
    base_root = root or DEFAULT_SOURCE_INTAKE_ROOT
    day_root = os.path.join(base_root, today_str)
    bundle_path = os.path.join(day_root, BUNDLE_FILE_NAME)
    brief_path = os.path.join(day_root, BRIEF_FILE_NAME)

    bundle = _read_bundle(bundle_path)
    if not isinstance(bundle, dict):
        return {
            "status": "input_missing",
            "today": today_str,
            "bundle_path": bundle_path,
            "brief_path": brief_path,
        }

    markdown = build_source_intake_brief(bundle)
    try:
        os.makedirs(day_root, exist_ok=True)
        with open(brief_path, "w", encoding="utf-8") as handle:
            handle.write(markdown)
    except Exception as exc:  # pragma: no cover
        return {
            "status": "write_failed",
            "today": today_str,
            "bundle_path": bundle_path,
            "brief_path": brief_path,
            "error": f"{type(exc).__name__}: {exc}",
        }

    return {
        "status": "written",
        "today": today_str,
        "bundle_path": bundle_path,
        "brief_path": brief_path,
    }
