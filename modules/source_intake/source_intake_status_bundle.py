"""Build a compact status bundle for source-intake artifacts.

This module is intentionally non-crawler: it only reads already generated JSON
artifacts under ``storage/source_intake/<today>`` and emits a compact summary.
Missing artifacts are tolerated and surfaced in the return payload.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from modules.source_intake.collection_gap_report import (
    STATUS_FALLBACK_ONLY,
    STATUS_FAILED,
    STATUS_NOT_IMPLEMENTED,
    STATUS_OK,
)


DEFAULT_SOURCE_INTAKE_ROOT = os.path.join("storage", "source_intake")

ARTIFACTS = [
    "daily_collection_plan.json",
    "daily_shallow_collection.json",
    "collection_gap_report.json",
    "collector_implementation_queue.json",
    "lane_collection_summary.json",
]

_FORBIDDEN_METRIC_ORIGIN = {"fabricated", "estimated", "guessed", "synthetic", "invented"}
_COMMERCE_DETAIL_KEYWORD = "commerce_detail"


def _coerce_today(today: Optional[Any]) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    if isinstance(today, (datetime, date)):
        return today.isoformat()
    return str(today)


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return 0
    return 0


def _coerce_rank(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 10 ** 9
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return 10 ** 9
    return 10 ** 9


def _collect_forbidden_payload_paths(path: str, value: Any, violations: List[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text

            if key_text == "fabricated_metrics":
                violations.append(f"{child_path}:fabricated_metrics_present")
            if key_text == "metrics_origin":
                origin = str(item).lower()
                if origin in _FORBIDDEN_METRIC_ORIGIN:
                    violations.append(f"{child_path}:{origin}")

            if _COMMERCE_DETAIL_KEYWORD in key_text.lower():
                violations.append(f"{child_path}:commerce_detail_key")

            if isinstance(item, str) and _COMMERCE_DETAIL_KEYWORD in item.lower():
                violations.append(f"{child_path}:commerce_detail_value")

            _collect_forbidden_payload_paths(child_path, item, violations)
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _collect_forbidden_payload_paths(f"{path}[{index}]", item, violations)


def _collect_artifact_safety_violations(name: str, payload: Any) -> List[str]:
    if not isinstance(payload, (dict, list)):
        return []

    violations: List[str] = []
    _collect_forbidden_payload_paths(name, payload, violations)
    return violations


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return None
    except Exception:
        return None

    if isinstance(payload, dict):
        return payload
    return None


def _source_ids_from_status_summary(payload: Dict[str, Any], status: str) -> List[str]:
    summary = payload.get("status_summary")
    if not isinstance(summary, dict):
        return []

    entries = summary.get(status)
    if not isinstance(entries, list):
        return []

    source_ids: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        source_id = entry.get("source_id")
        if isinstance(source_id, str):
            source_ids.append(source_id)
    return source_ids


def _extract_top_queue_sources(queue_payload: Dict[str, Any], limit: int = 5) -> List[str]:
    queue = queue_payload.get("implementation_queue")
    if not isinstance(queue, list):
        return []

    ranked: List[tuple[int, str]] = []
    for item in queue:
        if not isinstance(item, dict):
            continue
        source_id = item.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            continue
        ranked.append((_coerce_rank(item.get("rank")), source_id))

    ranked.sort(key=lambda pair: (pair[0], pair[1]))
    return [source_id for _, source_id in ranked[:limit]]


def _extract_status_counts(gap_payload: Optional[Dict[str, Any]]) -> Dict[str, int]:
    status_counts = {
        STATUS_NOT_IMPLEMENTED: 0,
        STATUS_FALLBACK_ONLY: 0,
        STATUS_FAILED: 0,
        STATUS_OK: 0,
    }

    if not isinstance(gap_payload, dict):
        return status_counts

    raw = gap_payload.get("status_counts")
    if not isinstance(raw, dict):
        return status_counts

    for status in status_counts:
        status_counts[status] = _coerce_int(raw.get(status))

    return status_counts


def _extract_item_count(
    shallow_payload: Optional[Dict[str, Any]],
    gap_payload: Optional[Dict[str, Any]],
    queue_payload: Optional[Dict[str, Any]],
) -> int:
    if isinstance(shallow_payload, dict):
        item_count = shallow_payload.get("item_count")
        if item_count is not None:
            return _coerce_int(item_count)

    if isinstance(gap_payload, dict):
        if gap_payload.get("item_count") is not None:
            return _coerce_int(gap_payload.get("item_count"))
        if gap_payload.get("source_count") is not None:
            return _coerce_int(gap_payload.get("source_count"))

    if isinstance(queue_payload, dict):
        queue = queue_payload.get("implementation_queue")
        if isinstance(queue, list):
            return len(queue)

    return 0


def build_source_intake_status_bundle(
    today: Optional[Any] = None,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    today_str = _coerce_today(today)
    base_root = root or DEFAULT_SOURCE_INTAKE_ROOT
    day_root = os.path.join(base_root, today_str)

    artifact_payloads: Dict[str, Optional[Dict[str, Any]]] = {}
    artifacts_present: Dict[str, bool] = {}
    for name in ARTIFACTS:
        path = os.path.join(day_root, name)
        artifacts_present[name] = os.path.exists(path)
        artifact_payloads[name] = _read_json(path) if artifacts_present[name] else None

    plan_payload = artifact_payloads["daily_collection_plan.json"]
    shallow_payload = artifact_payloads["daily_shallow_collection.json"]
    gap_payload = artifact_payloads["collection_gap_report.json"]
    queue_payload = artifact_payloads["collector_implementation_queue.json"]
    summary_payload = artifact_payloads["lane_collection_summary.json"]

    status_counts = _extract_status_counts(gap_payload)
    weak_lanes: List[str] = []
    blocked_lanes: List[str] = []
    if isinstance(summary_payload, dict):
        raw_weak = summary_payload.get("weak_lanes")
        if isinstance(raw_weak, list):
            weak_lanes = [lane for lane in raw_weak if isinstance(lane, str)]
    blocked_lanes = weak_lanes[:]

    top_queue_sources = []
    if isinstance(queue_payload, dict):
        top_queue_sources = _extract_top_queue_sources(queue_payload)

    fallback_only_sources = _source_ids_from_status_summary(gap_payload or {}, STATUS_FALLBACK_ONLY)
    not_implemented_count = status_counts.get(STATUS_NOT_IMPLEMENTED, 0)

    missing_artifacts = [name for name, present in artifacts_present.items() if not present]

    if plan_payload is not None and isinstance(plan_payload, dict):
        blockers_from_plan = plan_payload.get("blocked_lanes")
        if isinstance(blockers_from_plan, list):
            blocked_lanes = [
                lane for lane in blockers_from_plan if isinstance(lane, str)
            ] or blocked_lanes

    safety_violations: List[str] = []
    for artifact_name, payload in artifact_payloads.items():
        safety_violations.extend(_collect_artifact_safety_violations(artifact_name, payload))

    return {
        "artifacts_present": artifacts_present,
        "item_count": _extract_item_count(shallow_payload, gap_payload, queue_payload),
        "status_counts": status_counts,
        "weak_lanes": weak_lanes,
        "top_queue_sources": top_queue_sources,
        "blockers": {
            "missing_artifacts": missing_artifacts,
            "blocked_lanes": blocked_lanes,
            "fallback_only_sources": fallback_only_sources,
            "not_implemented_count": not_implemented_count,
            "safety_violations": safety_violations,
        },
    }


def run_source_intake_status_bundle(
    today: Optional[Any] = None,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    today_str = _coerce_today(today)
    base_root = root or DEFAULT_SOURCE_INTAKE_ROOT
    day_root = os.path.join(base_root, today_str)
    output_path = os.path.join(day_root, "source_intake_status_bundle.json")

    bundle = build_source_intake_status_bundle(today=today_str, root=base_root)
    result = {
        "status": "write_failed",
        "today": today_str,
        "bundle_path": output_path,
        "bundle": bundle,
    }

    try:
        os.makedirs(day_root, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(bundle, handle, ensure_ascii=False, indent=2)
        result["status"] = "written"
    except Exception as error:
        result["error"] = str(error)

    return result
