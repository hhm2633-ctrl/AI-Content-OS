"""Build a compact gap report from existing shallow collection output.

This module is analysis-only and does not perform any collection.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

STATUS_NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
STATUS_FALLBACK_ONLY = "FALLBACK_ONLY"
STATUS_FAILED = "FAILED"
STATUS_OK = "OK"

VALID_STATUS_ORDER = [
    STATUS_NOT_IMPLEMENTED,
    STATUS_FALLBACK_ONLY,
    STATUS_FAILED,
    STATUS_OK,
]

KNOWN_NEWS_PORTAL_IDS = {
    "naver_news",
    "daum_news",
    "nate_news_rank",
    "hankyung_economy",
    "mk_economy",
    "moneytoday",
    "edaily",
    "yonhap",
    "newsis",
    "news1",
}


def _load_collection_result(collection_result_or_path: Any) -> Dict[str, Any]:
    if isinstance(collection_result_or_path, dict):
        return collection_result_or_path

    if isinstance(collection_result_or_path, str):
        with open(collection_result_or_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    raise TypeError("collection_result_or_path must be dict or path string.")


def _to_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _collect_lane_memberships(plan_lanes: List[Dict[str, Any]]) -> Tuple[
    Dict[str, List[str]],
    Dict[str, List[str]],
    List[str],
]:
    source_to_lanes: Dict[str, List[str]] = {}
    source_to_excluded_lanes: Dict[str, List[str]] = {}
    all_lanes: List[str] = []

    for lane in plan_lanes:
        lane_id = lane.get("lane_id")
        if not isinstance(lane_id, str):
            continue
        if lane_id not in all_lanes:
            all_lanes.append(lane_id)
        for source_id in _to_list(lane.get("shallow_profiles")):
            source_to_lanes.setdefault(source_id, [])
            if lane_id not in source_to_lanes[source_id]:
                source_to_lanes[source_id].append(lane_id)
        for excluded in lane.get("excluded_sources", []) or []:
            source_id = excluded.get("source_id") if isinstance(excluded, dict) else None
            if not source_id:
                continue
            source_to_excluded_lanes.setdefault(source_id, [])
            if lane_id not in source_to_excluded_lanes[source_id]:
                source_to_excluded_lanes[source_id].append(lane_id)

    return source_to_lanes, source_to_excluded_lanes, all_lanes


def _is_fallback_method(method_value: Any) -> bool:
    if not isinstance(method_value, str):
        return False
    lowered = method_value.lower()
    return "fallback" in lowered or "settings" in lowered or "cache" in lowered


def _has_visible_metrics(visible_metrics: Any) -> bool:
    if not isinstance(visible_metrics, dict):
        return False
    for value in visible_metrics.values():
        if isinstance(value, (int, float)) and value > 0:
            return True
    return False


def _is_blocked_issue(skip_reason: Any, access_status: Any, error_text: Any) -> bool:
    if isinstance(skip_reason, str):
        lowered = skip_reason.lower()
        if any(keyword in lowered for keyword in ("403", "forbidden", "blocked", "access", "login")):
            return True
    if isinstance(access_status, str) and access_status.lower() == "blocked":
        return True
    if isinstance(error_text, str):
        lowered = error_text.lower()
        if any(keyword in lowered for keyword in ("403", "forbidden", "blocked", "access", "login")):
            return True
    return False


def _score_source_for_implementation(
    source_id: str,
    lanes: List[str],
    status: str,
    source_type: Any,
    has_visible_metrics: bool,
    skip_reason: str,
    access_status: Any,
    attempted: bool,
) -> int:
    score = 0
    if len(lanes) > 1:
        score += 100
    if source_id in KNOWN_NEWS_PORTAL_IDS or (
        isinstance(source_type, str) and source_type.lower() == "news"
    ):
        score += 80
    if isinstance(source_type, str) and source_type.lower() == "community" and has_visible_metrics:
        score += 50
    if status == STATUS_NOT_IMPLEMENTED:
        score += 20
    if status == STATUS_FAILED and attempted:
        score -= 80
    if status == STATUS_FAILED and _is_blocked_issue(skip_reason, access_status, None):
        score -= 30
    if len(lanes) == 0 and status != STATUS_OK:
        score -= 20
    return score


def _evaluate_status(
    source_id: str,
    attempted: bool,
    success: bool,
    item_count: int,
    fallback_items: int,
    skip_reason: Any,
    lane_status: str,
) -> str:
    if lane_status == STATUS_NOT_IMPLEMENTED:
        return STATUS_NOT_IMPLEMENTED
    if attempted and not success:
        return STATUS_FAILED
    if not attempted and skip_reason:
        return STATUS_FAILED
    if not attempted:
        return STATUS_NOT_IMPLEMENTED if (skip_reason == "collector_not_implemented") else STATUS_FAILED

    if item_count > 0 and item_count == fallback_items:
        return STATUS_FALLBACK_ONLY
    if success:
        return STATUS_OK
    return STATUS_FAILED


def build_collection_gap_report(collection_result_or_path: Any) -> Dict[str, Any]:
    collection_result = _load_collection_result(collection_result_or_path)
    plan = collection_result.get("plan", {})
    plan_lanes = plan.get("lanes", [])
    if not isinstance(plan_lanes, list):
        plan_lanes = []
    source_to_lanes, source_to_excluded_lanes, all_lanes = _collect_lane_memberships(plan_lanes)

    source_entries: Dict[str, Dict[str, Any]] = {}
    item_groups: Dict[str, List[Dict[str, Any]]] = {}
    for item in collection_result.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        source_id = item.get("source_id")
        if not isinstance(source_id, str):
            continue
        item_groups.setdefault(source_id, []).append(item)

    source_results = collection_result.get("source_results", []) or []
    for source in source_results:
        if not isinstance(source, dict):
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str):
            continue
        record = source_entries.setdefault(
            source_id,
            {
                "source_id": source_id,
                "source_type": None,
                "status": STATUS_OK,
                "attempted": False,
                "success": False,
                "skip_reason": None,
                "error": None,
                "item_count": 0,
                "fallback_item_count": 0,
                "has_visible_metrics": False,
                "lane_impact": [],
            },
        )
        record["attempted"] = bool(source.get("attempted", False)) or record["attempted"]
        record["success"] = bool(source.get("success", False)) or record["success"]
        if source.get("skip_reason"):
            record["skip_reason"] = source.get("skip_reason")
        if source.get("error"):
            record["error"] = source.get("error")
        if not record.get("lane_impact"):
            record["lane_impact"] = sorted(
                dict.fromkeys(source_to_lanes.get(source_id, []) + source_to_excluded_lanes.get(source_id, []))
            )
            if not record["lane_impact"]:
                for entry in plan_lanes:
                    for field in ("shallow_profiles",):
                        if source_id in _to_list(entry.get(field)):
                            lane_id = entry.get("lane_id")
                            if isinstance(lane_id, str) and lane_id not in record["lane_impact"]:
                                record["lane_impact"].append(lane_id)

    for source in source_results:
        source_id = source.get("source_id")
        if not isinstance(source_id, str):
            continue
        record = source_entries[source_id]
        record["source_type"] = record["source_type"] or source.get("source_type")
        items = item_groups.get(source_id, [])
        if items:
            fallback_count = 0
            visible = False
            for item in items:
                if not isinstance(item, dict):
                    continue
                fallback = item.get("is_fallback")
                method = item.get("collection_method")
                if fallback is True or _is_fallback_method(method):
                    fallback_count += 1
                if _has_visible_metrics(item.get("visible_metrics")):
                    visible = True
            record["item_count"] = len(items)
            record["fallback_item_count"] = fallback_count
            record["has_visible_metrics"] = visible
            record["source_type"] = record["source_type"] or items[0].get("source_type")

    for lane in plan_lanes:
        if not isinstance(lane, dict):
            continue
        lane_id = lane.get("lane_id")
        if not isinstance(lane_id, str):
            continue
        for excluded in lane.get("excluded_sources") or []:
            if not isinstance(excluded, dict):
                continue
            source_id = excluded.get("source_id")
            if not isinstance(source_id, str):
                continue
            record = source_entries.setdefault(
                source_id,
                {
                    "source_id": source_id,
                    "source_type": excluded.get("source_type"),
                    "status": STATUS_OK,
                    "attempted": False,
                    "success": False,
                    "skip_reason": excluded.get("skip_reason"),
                    "error": excluded.get("error"),
                    "item_count": 0,
                    "fallback_item_count": 0,
                    "has_visible_metrics": False,
                    "lane_impact": [],
                },
            )
            record["source_type"] = record["source_type"] or excluded.get("source_type")
            record["skip_reason"] = record.get("skip_reason") or excluded.get("skip_reason")
            if not record["lane_impact"]:
                record["lane_impact"] = sorted(
                    dict.fromkeys(source_to_lanes.get(source_id, []) + source_to_excluded_lanes.get(source_id, []))
                )

    for source_id in source_to_lanes:
        if source_id not in source_entries:
            source_entries[source_id] = {
                "source_id": source_id,
                "source_type": None,
                "status": STATUS_OK,
                "attempted": False,
                "success": False,
                "skip_reason": None,
                "error": None,
                "item_count": 0,
                "fallback_item_count": 0,
                "has_visible_metrics": False,
                "lane_impact": sorted(source_to_lanes[source_id]),
            }

    not_implemented: List[Dict[str, Any]] = []
    fallback_only: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    ok: List[Dict[str, Any]] = []

    status_order = []
    for source_id, record in source_entries.items():
        status = _evaluate_status(
            source_id=source_id,
            attempted=bool(record["attempted"]),
            success=bool(record["success"]),
            item_count=int(record["item_count"]),
            fallback_items=int(record["fallback_item_count"]),
            skip_reason=record.get("skip_reason"),
            lane_status=STATUS_NOT_IMPLEMENTED if record.get("skip_reason") == "collector_not_implemented" and not record["attempted"] else STATUS_OK,
        )
        record["status"] = status
        record["lane_impact_count"] = len(record.get("lane_impact") or [])

        if status == STATUS_NOT_IMPLEMENTED:
            not_implemented.append(record)
        elif status == STATUS_FALLBACK_ONLY:
            fallback_only.append(record)
        elif status == STATUS_FAILED:
            failed.append(record)
        else:
            ok.append(record)
        status_order.append((status, record["source_id"]))

    all_statuses = {}
    for status, entries in [
        (STATUS_NOT_IMPLEMENTED, not_implemented),
        (STATUS_FALLBACK_ONLY, fallback_only),
        (STATUS_FAILED, failed),
        (STATUS_OK, ok),
    ]:
        all_statuses[status] = [
            {
                "source_id": entry["source_id"],
                "lane_impact": entry["lane_impact"],
                "skip_reason": entry.get("skip_reason"),
                "status": status,
                "source_type": entry.get("source_type"),
                "item_count": entry.get("item_count", 0),
            }
            for entry in sorted(entries, key=lambda item: item["source_id"])
        ]

    recommendation_candidates = []
    for status, entries in [
        (STATUS_NOT_IMPLEMENTED, not_implemented),
        (STATUS_FALLBACK_ONLY, fallback_only),
        (STATUS_FAILED, failed),
    ]:
        for entry in entries:
            score = _score_source_for_implementation(
                source_id=entry["source_id"],
                lanes=entry["lane_impact"] or [],
                status=status,
                source_type=entry.get("source_type"),
                has_visible_metrics=bool(entry["has_visible_metrics"]),
                skip_reason=entry.get("skip_reason"),
                access_status=entry.get("access_status"),
                attempted=bool(entry.get("attempted")),
            )
            recommendation_candidates.append(
                {
                    "source_id": entry["source_id"],
                    "status": status,
                    "score": score,
                    "lane_impact": entry["lane_impact"],
                    "skip_reason": entry.get("skip_reason"),
                }
            )

    recommendation_candidates.sort(key=lambda item: (-item["score"], item["source_id"]))

    total_sources = len(source_entries)
    status_counts = {
        STATUS_NOT_IMPLEMENTED: len(not_implemented),
        STATUS_FALLBACK_ONLY: len(fallback_only),
        STATUS_FAILED: len(failed),
        STATUS_OK: len(ok),
    }

    return {
        "schema_version": "collection_gap_report_v1",
        "source_count": total_sources,
        "status_counts": status_counts,
        "all_lanes": all_lanes,
        "status_summary": {
            STATUS_NOT_IMPLEMENTED: not_implemented,
            STATUS_FALLBACK_ONLY: fallback_only,
            STATUS_FAILED: failed,
            STATUS_OK: ok,
        },
        "source_status_by_status": all_statuses,
        "sources_sorted": [
            entry[1]
            for entry in sorted(status_order, key=lambda item: (VALID_STATUS_ORDER.index(item[0]), item[1]))
        ],
        "recommended_implementation_order": recommendation_candidates,
        "lane_count": len(all_lanes),
    }
