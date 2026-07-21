"""Build a read-only diagnostic for Naver News fallback behavior.

This module is analysis-only and reads artifacts already generated under
``storage/source_intake/<today>``. It does not call any web endpoints.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from modules.source_intake.collection_gap_report import (
    STATUS_FAILED,
    STATUS_FALLBACK_ONLY,
    STATUS_NOT_IMPLEMENTED,
    STATUS_OK,
)
from modules.source_intake.source_intake_schema import SOURCE_INTAKE_STORAGE_ROOT


DIAGNOSTIC_VERSION = "naver_news_fallback_diagnostic_v1"
DEFAULT_SOURCE_ID = "naver_news"
ARTIFACTS = [
    "daily_shallow_collection.json",
    "collection_gap_report.json",
    "daily_collection_plan.json",
]
_EMPTY_LIST: List[str] = []


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
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return None

    if isinstance(payload, dict):
        return payload
    return None


def _coerce_truthy_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _collect_gap_status(gap_payload: Optional[Dict[str, Any]], source_id: str) -> Optional[str]:
    if not isinstance(gap_payload, dict):
        return None
    status_summary = gap_payload.get("status_summary")
    if not isinstance(status_summary, dict):
        return None
    for status, entries in status_summary.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("source_id") == source_id:
                return str(status)
    return None


def _normalise_items(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _collect_source_items(items: List[Dict[str, Any]], source_id: str) -> List[Dict[str, Any]]:
    return [item for item in items if item.get("source_id") == source_id]


def _collect_source_results(
    source_results: Any,
    source_id: str,
) -> List[Dict[str, Any]]:
    if not isinstance(source_results, list):
        return []
    return [result for result in source_results if isinstance(result, dict) and result.get("source_id") == source_id]


def _coerce_bool(value: Any) -> bool:
    return bool(value)


def _to_lower(value: Any) -> str:
    return str(value).lower() if value is not None else ""


def _is_parser_failure(method: str, trend_reason: str) -> bool:
    method_lower = _to_lower(method)
    reason_lower = _to_lower(trend_reason)
    return "parse_failed" in method_lower or "parse_failed" in reason_lower or (
        "parse" in method_lower and "fail" in method_lower
    )


def _is_fallback_method(method: Any) -> bool:
    method_lower = _to_lower(method)
    if not method_lower:
        return False
    return "fallback" in method_lower or "settings" in method_lower or "cache" in method_lower


def _collect_parser_reasons(items: List[Dict[str, Any]]) -> List[str]:
    reasons: List[str] = []
    for item in items:
        method = item.get("collection_method", "")
        trend_reason = item.get("trend_reason", "")
        if _is_parser_failure(_to_lower(method), _to_lower(trend_reason)):
            if isinstance(method, str) and method.strip():
                reasons.append(method)
            if isinstance(trend_reason, str) and trend_reason.strip():
                reasons.append(trend_reason)
    return reasons


def build_naver_news_fallback_diagnostic(
    today: Optional[Any] = None,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    today_str = _coerce_today(today)
    base_root = root or SOURCE_INTAKE_STORAGE_ROOT
    day_root = os.path.join(base_root, today_str)

    shallow_path = os.path.join(day_root, "daily_shallow_collection.json")
    gap_path = os.path.join(day_root, "collection_gap_report.json")
    plan_path = os.path.join(day_root, "daily_collection_plan.json")

    shallow_payload = _read_json(shallow_path)
    gap_payload = _read_json(gap_path)
    plan_payload = _read_json(plan_path)

    artifacts_present = {
        "daily_shallow_collection.json": os.path.exists(shallow_path),
        "collection_gap_report.json": os.path.exists(gap_path),
        "daily_collection_plan.json": os.path.exists(plan_path),
    }

    naver_items = _collect_source_items(_normalise_items(shallow_payload.get("items") if shallow_payload else None), DEFAULT_SOURCE_ID)
    source_results = _collect_source_results(shallow_payload.get("source_results") if shallow_payload else None, DEFAULT_SOURCE_ID)

    lane_ids: List[str] = []
    attempted = False
    success = False
    skipped = False
    skip_reasons: List[str] = []
    errors: List[str] = []
    for result in source_results:
        if result.get("attempted"):
            attempted = True
        if result.get("success"):
            success = True
        if result.get("skipped"):
            skipped = True
        if isinstance(result.get("skip_reason"), str):
            skip_reasons.append(result.get("skip_reason", ""))
        if isinstance(result.get("error"), str):
            errors.append(result.get("error", ""))
        lane = result.get("lane_id")
        if isinstance(lane, str) and lane and lane not in lane_ids:
            lane_ids.append(lane)

    fallback_items = [item for item in naver_items if _coerce_bool(item.get("is_fallback", False))]
    fallback_only_methods = [
        _to_lower(item.get("collection_method"))
        for item in naver_items
        if _coerce_bool(item.get("is_fallback", False))
    ]

    parser_fail_reasons = _collect_parser_reasons(naver_items)
    parser_fail_count = len(parser_fail_reasons)

    gap_status = _collect_gap_status(gap_payload, DEFAULT_SOURCE_ID)
    effective_status = gap_status if gap_status else (
        STATUS_FALLBACK_ONLY
        if naver_items and fallback_items and len(fallback_items) == len(naver_items)
        else STATUS_OK
        if naver_items and not fallback_items
        else STATUS_NOT_IMPLEMENTED
        if not attempted
        else STATUS_FAILED
    )

    if not effective_status:
        effective_status = STATUS_NOT_IMPLEMENTED

    if effective_status == STATUS_FALLBACK_ONLY:
        if parser_fail_reasons:
            primary_reason = "parser_failed_and_fallback_used"
            explanation = (
                "Naver News returned only fallback items because parsing failed "
                f"({', '.join(sorted(set(parser_fail_reasons)))})."
            )
        elif fallback_items:
            primary_reason = "fallback_collected_without_parser_marker"
            fallback_methods = sorted(set(method for method in fallback_only_methods if method))
            explanation = (
                "Naver News returned only fallback items. "
                f"Observed fallback methods: {', '.join(fallback_methods)}."
            )
        else:
            primary_reason = "fallback_unknown"
            explanation = "Naver News was marked fallback-only without explicit fallback markers."
    elif effective_status == STATUS_NOT_IMPLEMENTED:
        primary_reason = "collector_not_invoked"
        explanation = "Naver News was not attempted in collected source results."
    elif effective_status == STATUS_OK:
        primary_reason = "direct_collection"
        explanation = "Naver News was collected directly without fallback usage."
    elif effective_status == STATUS_FAILED:
        primary_reason = "collection_failed"
        explanation = "Naver News collection failed without fallback output."
    else:
        primary_reason = "status_unknown"
        explanation = "Naver News status could not be fully determined from current artifacts."

    plan_lanes = []
    if isinstance(plan_payload, dict):
        for lane in plan_payload.get("lanes") or []:
            if isinstance(lane, dict):
                lane_id = lane.get("lane_id")
                if isinstance(lane_id, str):
                    plan_lanes.append(lane_id)

    return {
        "schema_version": DIAGNOSTIC_VERSION,
        "source_id": DEFAULT_SOURCE_ID,
        "today": today_str,
        "artifacts_present": artifacts_present,
        "status": effective_status,
        "raw_collection_status": {
            "attempted": attempted,
            "success": success,
            "skipped": skipped,
            "skip_reasons": sorted(set(skip_reasons)),
            "errors": sorted(set(errors)),
            "lanes": lane_ids,
        },
        "coverage": {
            "item_count": len(naver_items),
            "fallback_item_count": len(fallback_items),
            "fallback_methods": sorted(set(filter(None, fallback_only_methods))),
            "fallback_unique_trend_reasons": sorted(
                {
                    str(item.get("trend_reason", "")).strip()
                    for item in naver_items
                    if str(item.get("trend_reason", "")).strip()
                }
            ),
        },
        "diagnostic": {
            "primary_reason": primary_reason,
            "explanation": explanation,
            "parser_failure_count": parser_fail_count,
            "parser_failure_examples": sorted(set(parser_fail_reasons)),
        },
        "plan_lanes": sorted(set(plan_lanes)),
    }

