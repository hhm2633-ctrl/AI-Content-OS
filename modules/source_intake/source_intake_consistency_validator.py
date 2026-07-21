"""Validate cross-artifact consistency for source-intake day outputs."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from modules.source_intake.source_intake_status_bundle import STATUS_FAILED, STATUS_FALLBACK_ONLY, STATUS_NOT_IMPLEMENTED, STATUS_OK
from modules.source_intake.source_intake_schema import SOURCE_INTAKE_STORAGE_ROOT

ARTIFACTS = [
    "daily_collection_plan.json",
    "daily_shallow_collection.json",
    "collection_gap_report.json",
    "lane_collection_summary.json",
    "source_intake_status_bundle.json",
    "spark_task_queue.json",
]


def _coerce_today(today: Optional[Any]) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    if isinstance(today, (datetime, date)):
        return today.isoformat()
    return str(today)


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None


def _dedupe_ordered(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _to_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _extract_plan_sources(payload: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(payload, dict):
        return []
    lanes = payload.get("lanes", [])
    if not isinstance(lanes, list):
        return []
    source_ids: List[str] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        source_ids.extend(_to_list(lane.get("shallow_profiles")))
        for excluded in _to_list([source.get("source_id") for source in lane.get("excluded_sources", []) if isinstance(source, dict)]):
            source_ids.append(excluded)
    return _dedupe_ordered(source_ids)


def _extract_shallow_sources(payload: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(payload, dict):
        return []
    source_ids: List[str] = []
    for item in payload.get("source_results", []) or []:
        if isinstance(item, dict) and isinstance(item.get("source_id"), str):
            source_ids.append(item["source_id"])
    for item in payload.get("items", []) or []:
        if isinstance(item, dict) and isinstance(item.get("source_id"), str):
            source_ids.append(item["source_id"])
    return _dedupe_ordered(source_ids)


def _extract_gap_sources(payload: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(payload, dict):
        return []
    source_ids: List[str] = []
    for status, entries in (payload.get("status_summary", {}) or {}).items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("source_id"), str):
                source_ids.append(entry["source_id"])
    if not source_ids:
        for status, entries in (payload.get("source_status_by_status", {}) or {}).items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and isinstance(entry.get("source_id"), str):
                    source_ids.append(entry["source_id"])
    return _dedupe_ordered(source_ids)


def _extract_lane_summary_sources(payload: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(payload, dict):
        return []
    lane_summary = payload.get("lane_summary", {})
    source_ids: List[str] = []
    if isinstance(lane_summary, dict):
        for summary in lane_summary.values():
            if not isinstance(summary, dict):
                continue
            source_ids.extend(_to_list(summary.get("top_missing_sources")))
    return _dedupe_ordered(source_ids)


def _extract_status_bundle_counts(payload: Optional[Dict[str, Any]]) -> Dict[str, int]:
    counts = {
        STATUS_NOT_IMPLEMENTED: 0,
        STATUS_FALLBACK_ONLY: 0,
        STATUS_FAILED: 0,
        STATUS_OK: 0,
    }
    if not isinstance(payload, dict):
        return counts
    raw = payload.get("status_counts", {})
    if isinstance(raw, dict):
        for key in counts:
            value = raw.get(key)
            if isinstance(value, int):
                counts[key] = value
    return counts


def _extract_gap_counts(payload: Optional[Dict[str, Any]]) -> Dict[str, int]:
    counts = {
        STATUS_NOT_IMPLEMENTED: 0,
        STATUS_FALLBACK_ONLY: 0,
        STATUS_FAILED: 0,
        STATUS_OK: 0,
    }
    if not isinstance(payload, dict):
        return counts
    raw = payload.get("status_counts")
    if isinstance(raw, dict):
        for key in counts:
            value = raw.get(key)
            if isinstance(value, int):
                counts[key] = value
    return counts


def _extract_gap_status_counts(payload: Optional[Dict[str, Any]]) -> Optional[int]:
    if not isinstance(payload, dict):
        return None
    source_count = payload.get("source_count")
    if isinstance(source_count, int):
        return source_count
    return None


def _extract_lane_summary_counts(payload: Optional[Dict[str, Any]]) -> Tuple[int, int]:
    if not isinstance(payload, dict):
        return 0, 0
    lane_count = payload.get("lane_count")
    lane_ids = payload.get("lane_ids")
    lane_count_declared = lane_count if isinstance(lane_count, int) else 0
    lane_count_actual = len(_to_list(lane_ids))
    return lane_count_declared, lane_count_actual


def _extract_spark_queue_sources(payload: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(payload, dict):
        return []
    queue_items = payload.get("spark_task_queue", [])
    if not isinstance(queue_items, list):
        return []
    sources: List[str] = []
    for item in queue_items:
        if isinstance(item, dict) and isinstance(item.get("source_id"), str):
            sources.append(item["source_id"])
    return _dedupe_ordered(sources)


def _extract_spark_task_count(payload: Optional[Dict[str, Any]]) -> Optional[int]:
    if not isinstance(payload, dict):
        return None
    count = payload.get("task_count")
    return count if isinstance(count, int) else None


def _extract_dates(payloads: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Optional[str]]:
    artifact_dates: Dict[str, Optional[str]] = {}
    for artifact_name, payload in payloads.items():
        if isinstance(payload, dict):
            date_value = payload.get("date")
            artifact_dates[artifact_name] = str(date_value) if date_value is not None else None
        else:
            artifact_dates[artifact_name] = None
    return artifact_dates


def _set_diff(actual: Sequence[str], expected: Sequence[str]) -> Tuple[List[str], List[str]]:
    actual_set = set(actual)
    expected_set = set(expected)
    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    return missing, extra


def build_source_intake_consistency_report(
    today: Optional[Any] = None,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    today_str = _coerce_today(today)
    base_root = root or SOURCE_INTAKE_STORAGE_ROOT
    day_root = os.path.join(base_root, today_str)

    payloads: Dict[str, Optional[Dict[str, Any]]] = {}
    artifacts_present: Dict[str, bool] = {}
    for artifact_name in ARTIFACTS:
        path = os.path.join(day_root, artifact_name)
        artifacts_present[artifact_name] = os.path.exists(path)
        payloads[artifact_name] = _read_json(path) if artifacts_present[artifact_name] else None

    plan_sources = _extract_plan_sources(payloads["daily_collection_plan.json"])
    shallow_sources = _extract_shallow_sources(payloads["daily_shallow_collection.json"])
    gap_sources = _extract_gap_sources(payloads["collection_gap_report.json"])
    lane_summary_sources = _extract_lane_summary_sources(payloads["lane_collection_summary.json"])
    spark_queue_sources = _extract_spark_queue_sources(payloads["spark_task_queue.json"])

    plan_date = payloads["daily_collection_plan.json"].get("date") if isinstance(payloads["daily_collection_plan.json"], dict) else None
    shallow_date = payloads["daily_shallow_collection.json"].get("date") if isinstance(payloads["daily_shallow_collection.json"], dict) else None

    mismatch_reasons: List[str] = []

    missing_artifacts = [name for name, present in artifacts_present.items() if not present]
    for missing in missing_artifacts:
        mismatch_reasons.append(f"missing_artifact:{missing}")

    if plan_date and shallow_date and str(plan_date) != str(shallow_date):
        mismatch_reasons.append(
            f"date_mismatch:daily_collection_plan.json={plan_date},daily_shallow_collection.json={shallow_date}"
        )

    dates_with_values = _extract_dates(payloads)
    unique_dates = {value for value in dates_with_values.values() if isinstance(value, str)}
    if len(unique_dates) > 1:
        mismatch_reasons.append(f"date_field_mismatch:{sorted(unique_dates)}")

    plan_set = set(plan_sources)
    shallow_set = set(shallow_sources)
    gap_set = set(gap_sources)
    lane_set = set(lane_summary_sources)
    spark_set = set(spark_queue_sources)

    if gap_set != plan_set:
        missing, extra = _set_diff(gap_sources, plan_sources)
        mismatch_reasons.append(f"source_ids_mismatch:plan_vs_gap_missing={missing}:extra={extra}")
    if gap_set != shallow_set:
        missing, extra = _set_diff(gap_sources, shallow_sources)
        mismatch_reasons.append(f"source_ids_mismatch:shallow_vs_gap_missing={missing}:extra={extra}")
    if not spark_set.issubset(gap_set):
        missing, extra = _set_diff(spark_queue_sources, gap_sources)
        mismatch_reasons.append(f"source_ids_mismatch:spark_not_subset_of_gap_missing={missing}:extra={extra}")
    if not lane_set.issubset(gap_set):
        missing, extra = _set_diff(lane_summary_sources, gap_sources)
        mismatch_reasons.append(f"source_ids_mismatch:lane_top_missing_not_in_gap_missing={missing}:extra={extra}")

    gap_status_counts = _extract_gap_counts(payloads["collection_gap_report.json"])
    status_bundle_counts = _extract_status_bundle_counts(payloads["source_intake_status_bundle.json"])
    gap_source_count = _extract_gap_status_counts(payloads["collection_gap_report.json"])

    if sum(gap_status_counts.values()) != gap_source_count and gap_source_count is not None:
        mismatch_reasons.append(
            f"count_mismatch:collection_gap_report.status_counts_sum={sum(gap_status_counts.values())},source_count={gap_source_count}"
        )

    expected_gap_count = len(gap_set)
    if gap_source_count is not None and gap_source_count != expected_gap_count:
        mismatch_reasons.append(
            f"count_mismatch:collection_gap_report.source_count={gap_source_count},unique_gap_sources={expected_gap_count}"
        )

    if plan_date is not None and payloads["daily_collection_plan.json"] is not None:
        if str(plan_date) != today_str:
            mismatch_reasons.append(f"date_mismatch:payload_vs_requested_date:{plan_date}!={today_str}")

    if status_bundle_counts != gap_status_counts:
        mismatch_reasons.append("count_mismatch:source_intake_status_bundle.status_counts_vs_gap.status_counts")

    status_total_bundle = sum(status_bundle_counts.values())
    if gap_source_count is not None and status_total_bundle != gap_source_count:
        mismatch_reasons.append(
            f"count_mismatch:source_intake_status_bundle.status_count_sum={status_total_bundle},gap_source_count={gap_source_count}"
        )

    item_count = payloads["daily_shallow_collection.json"].get("item_count") if isinstance(payloads["daily_shallow_collection.json"], dict) else None
    status_item_count = payloads["source_intake_status_bundle.json"].get("item_count") if isinstance(payloads["source_intake_status_bundle.json"], dict) else None
    if isinstance(item_count, int) and isinstance(status_item_count, int) and item_count != status_item_count:
        mismatch_reasons.append(f"count_mismatch:shallow.item_count={item_count},status_bundle.item_count={status_item_count}")

    spark_task_count = _extract_spark_task_count(payloads["spark_task_queue.json"])
    if isinstance(spark_task_count, int) and spark_task_count != len(spark_queue_sources):
        mismatch_reasons.append(
            f"count_mismatch:spark_task_queue.task_count={spark_task_count},spark_task_queue_source_count={len(spark_queue_sources)}"
        )

    lane_count_declared, lane_count_actual = _extract_lane_summary_counts(payloads["lane_collection_summary.json"])
    if lane_count_declared != lane_count_actual:
        mismatch_reasons.append(f"count_mismatch:lane_summary.lane_count={lane_count_declared},lane_summary_ids={lane_count_actual}")

    status = "fail_closed" if mismatch_reasons else "ok"

    return {
        "status": status,
        "today": today_str,
        "day_root": day_root,
        "artifacts_present": artifacts_present,
        "date_fields": {
            "daily_collection_plan.json": str(plan_date) if plan_date is not None else None,
            "daily_shallow_collection.json": str(shallow_date) if shallow_date is not None else None,
        },
        "mismatches": mismatch_reasons,
        "source_ids": {
            "plan": plan_sources,
            "shallow": shallow_sources,
            "gap": gap_sources,
            "lane_summary": lane_summary_sources,
            "spark_queue": spark_queue_sources,
        },
        "counts": {
            "plan_source_count": len(plan_sources),
            "shallow_source_count": len(shallow_sources),
            "gap_source_count": gap_source_count if gap_source_count is not None else len(gap_sources),
            "gap_status_count_sum": sum(gap_status_counts.values()),
            "status_bundle_status_count_sum": status_total_bundle,
            "shallow_item_count": item_count,
            "status_bundle_item_count": status_item_count,
            "spark_task_count": spark_task_count,
            "lane_count_declared": lane_count_declared,
            "lane_count_actual": lane_count_actual,
            "spark_task_unique_source_count": len(spark_queue_sources),
        },
    }


def run_source_intake_consistency_report(
    today: Optional[Any] = None,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    today_str = _coerce_today(today)
    base_root = root or SOURCE_INTAKE_STORAGE_ROOT
    day_root = os.path.join(base_root, today_str)
    report_path = os.path.join(day_root, "source_intake_consistency_report.json")

    report = build_source_intake_consistency_report(today=today_str, root=base_root)
    result = {
        "status": "write_failed",
        "today": today_str,
        "report_path": report_path,
        "report": report,
    }

    try:
        os.makedirs(day_root, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        result["status"] = report["status"]
    except Exception as error:
        result["error"] = str(error)

    return result
