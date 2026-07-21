"""Build an offline diagnostic contract artifact for Instiz access failure.

This module reads existing Spark/task artifacts and never performs scraping or
browser activity. It is read-only and deterministic by design.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from modules.source_intake.collection_gap_report import STATUS_FAILED
from modules.source_intake.source_capability_map import SourceCapabilityMap
from modules.source_intake.source_intake_schema import SOURCE_INTAKE_STORAGE_ROOT

DIAGNOSTIC_VERSION = "instiz_diagnostic_contract_v1"
DIAGNOSTIC_FILENAME = "instiz_diagnostic.json"
DIAGNOSTIC_SOURCE_ID = "instiz"
SPARK_QUEUE_FILENAME = "spark_task_queue.json"
GAP_REPORT_FILENAME = "collection_gap_report.json"
PLAN_FILENAME = "daily_collection_plan.json"
SHALLOW_COLLECTION_FILENAME = "daily_shallow_collection.json"
ARTIFACT_FILENAMES = [
    SPARK_QUEUE_FILENAME,
    GAP_REPORT_FILENAME,
    PLAN_FILENAME,
    SHALLOW_COLLECTION_FILENAME,
]


def _coerce_today(today: Optional[Any]) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    return str(today)


def _coerce_str(value: Any) -> str:
    return str(value) if value is not None else ""


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _coerce_sources(payload: Any) -> List[Dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _coerce_string_list(payload: Any) -> List[str]:
    if not isinstance(payload, list):
        return []
    values = []
    for item in payload:
        if isinstance(item, str) and item.strip():
            values.append(item.strip())
    return values


def _contains_http_block_reason(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return any(token in lowered for token in ("403", "forbidden", "blocked", "access", "login"))


def _find_gap_entry(gap_payload: Optional[Dict[str, Any]], source_id: str) -> Optional[Dict[str, Any]]:
    if not isinstance(gap_payload, dict):
        return None
    for status in gap_payload.get("status_summary", {}).values():
        if not isinstance(status, list):
            continue
        for entry in status:
            if isinstance(entry, dict) and entry.get("source_id") == source_id:
                return entry
    return None


def _collect_plan_excludes(plan_payload: Optional[Dict[str, Any]], source_id: str) -> List[Dict[str, Any]]:
    if not isinstance(plan_payload, dict):
        return []

    plans: List[Dict[str, Any]] = []
    for lane in plan_payload.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        lane_id = _coerce_str(lane.get("lane_id"))
        if not lane_id:
            continue

        for excluded in lane.get("excluded_sources", []) or []:
            if not isinstance(excluded, dict):
                continue
            if excluded.get("source_id") == source_id:
                record = dict(excluded)
                record.setdefault("lane_id", lane_id)
                plans.append(record)
    return plans


def _collect_lanes(plan_payload: Optional[Dict[str, Any]], source_id: str) -> List[str]:
    if not isinstance(plan_payload, dict):
        return []

    lanes: List[str] = []
    for lane in plan_payload.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        lane_id = _coerce_str(lane.get("lane_id"))
        if not lane_id:
            continue
        excluded = lane.get("excluded_sources", []) or []
        is_present = any(
            isinstance(item, dict) and item.get("source_id") == source_id
            for item in excluded
        )
        if is_present and lane_id not in lanes:
            lanes.append(lane_id)
    return lanes


def _find_spark_task(queue_payload: Optional[Dict[str, Any]], source_id: str) -> Optional[Dict[str, Any]]:
    if not isinstance(queue_payload, dict):
        return None
    items = _coerce_sources(queue_payload.get("spark_task_queue"))
    for item in items:
        if item.get("source_id") == source_id and str(item.get("rank")) == "1":
            return item
    return items[0] if items else None


def build_instiz_diagnostic_contract(
    today: Optional[Any] = None,
    source_id: str = DIAGNOSTIC_SOURCE_ID,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    today_str = _coerce_today(today)
    base_root = root or SOURCE_INTAKE_STORAGE_ROOT
    day_root = os.path.join(base_root, today_str)

    queue_payload = _read_json(os.path.join(day_root, SPARK_QUEUE_FILENAME))
    gap_payload = _read_json(os.path.join(day_root, GAP_REPORT_FILENAME))
    plan_payload = _read_json(os.path.join(day_root, PLAN_FILENAME))
    shallow_payload = _read_json(os.path.join(day_root, SHALLOW_COLLECTION_FILENAME))

    artifacts_present = {
        name: os.path.exists(os.path.join(day_root, name))
        for name in ARTIFACT_FILENAMES
    }

    spark_task = _find_spark_task(queue_payload, source_id)
    gap_entry = _find_gap_entry(gap_payload, source_id) or {}
    plan_lanes = _collect_lanes(plan_payload, source_id)
    plan_excludes = _collect_plan_excludes(plan_payload, source_id)

    queue_status = _coerce_str(spark_task.get("status")).upper() if spark_task else ""
    queue_lane_impact = spark_task.get("lane_impact") if isinstance(spark_task, dict) and isinstance(spark_task.get("lane_impact"), list) else plan_lanes

    gap_status = _coerce_str(gap_entry.get("status")).upper()
    gap_skip = _coerce_str(gap_entry.get("skip_reason"))
    gap_item_count = gap_entry.get("item_count", 0)
    gap_attempted = bool(gap_entry.get("attempted", False))

    source_results = [
        item for item in _coerce_sources(shallow_payload.get("source_results") if isinstance(shallow_payload, dict) else None)
        if item.get("source_id") == source_id
    ]

    source_result_summary = {
        "attempted": any(bool(item.get("attempted")) for item in source_results),
        "success": any(bool(item.get("success")) for item in source_results),
        "skipped": any(bool(item.get("skipped")) for item in source_results),
        "errors": sorted({
            _coerce_str(item.get("error"))
            for item in source_results
            if isinstance(item.get("error"), str)
        }),
    }

    effective_status = STATUS_FAILED
    if gap_status:
        effective_status = gap_status
    elif queue_status:
        effective_status = queue_status
    if not effective_status:
        effective_status = STATUS_FAILED

    access_blocked = (
        _contains_http_block_reason(gap_skip)
        or any(_contains_http_block_reason(entry.get("skip_reason")) for entry in plan_excludes)
        or "blocked" in str(gap_entry.get("access_status", "")).lower()
    )
    access_state = "blocked" if access_blocked else "unknown"

    required_inputs: Dict[str, Any] = {
        "contract_ready": False if access_blocked else True,
        "required_preconditions": [
            "verify access state for instiz",
            "record a fresh status check timestamp",
            "only proceed to collector implementation after access_state resolves to ok",
        ],
        "source_profile": SourceCapabilityMap().get(source_id),
        "required_lane_impact": sorted(set(queue_lane_impact or plan_lanes)),
        "required_output_contract": {
            "source_result_expected_fields": [
                "source_id",
                "lane_id",
                "attempted",
                "success",
                "skipped",
                "count",
                "skip_reason",
                "error",
            ],
            "item_expected_fields": [
                "schema_version",
                "item_id",
                "source_id",
                "source_type",
                "channel_candidates",
                "title",
                "url",
                "rank_position",
                "visible_metrics",
                "derived_metrics",
                "media_flags",
                "ad_signals",
                "deep_dive_priority",
                "rights_status",
                "metrics_origin",
            ],
            "item_requirements": {
                "must_include_source_id": source_id,
                "minimum_required_metrics_origin": "parsed",
                "metric_origin_not_allowed": ["fabricated", "estimated", "guessed", "synthetic", "invented"],
            },
        },
    }

    return {
        "schema_version": DIAGNOSTIC_VERSION,
        "today": today_str,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_id": source_id,
        "task": {
            "rank": int(spark_task.get("rank")) if isinstance(spark_task, dict) and str(spark_task.get("rank")).isdigit() else 1,
            "task_type": _coerce_str(spark_task.get("task_type")) if isinstance(spark_task, dict) else "diagnostic_contract",
            "status": effective_status,
            "lane_impact": sorted(set(_coerce_string_list(queue_lane_impact) + plan_lanes)),
            "next_action": _coerce_str(spark_task.get("next_action")) if isinstance(spark_task, dict) else "",
        },
        "current_state": {
            "collection_status": effective_status,
            "access_state": access_state,
            "lane_impact_from_plan": plan_lanes,
            "gap_skip_reason": gap_skip,
            "gap_item_count": gap_item_count,
            "attempted": gap_attempted,
            "source_results": source_result_summary,
            "plan_exclusions": [
                {
                    "lane_id": _coerce_str(entry.get("lane_id")),
                    "skip_reason": _coerce_str(entry.get("skip_reason")),
                    "access_status": _coerce_str(entry.get("access_status")),
                    "workflow_impact": _coerce_str(entry.get("workflow_impact")),
                }
                for entry in plan_excludes
            ],
        },
        "required_future_collector_inputs": required_inputs,
        "artifacts_present": artifacts_present,
    }


def run_instiz_diagnostic_contract(
    today: Optional[Any] = None,
    source_id: str = DIAGNOSTIC_SOURCE_ID,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    today_str = _coerce_today(today)
    base_root = root or SOURCE_INTAKE_STORAGE_ROOT
    day_root = os.path.join(base_root, today_str)
    output_path = os.path.join(day_root, DIAGNOSTIC_FILENAME)

    diagnostic = build_instiz_diagnostic_contract(today=today_str, source_id=source_id, root=base_root)
    result = {
        "status": "write_failed",
        "today": today_str,
        "source_id": source_id,
        "output_path": output_path,
        "diagnostic": diagnostic,
    }

    try:
        os.makedirs(day_root, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(diagnostic, handle, ensure_ascii=False, indent=2)
        result["status"] = "written"
    except Exception as error:
        result["error"] = str(error)
        return result

    return result
