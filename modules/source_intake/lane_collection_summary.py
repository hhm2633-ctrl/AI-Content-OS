"""Build lane-level summaries from collection gap reports."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Set

from modules.source_intake.collection_gap_report import (
    STATUS_FAILED,
    STATUS_FALLBACK_ONLY,
    STATUS_NOT_IMPLEMENTED,
    STATUS_OK,
    build_collection_gap_report,
)


READINESS_BLOCKED = "BLOCKED"
READINESS_PARTIAL = "PARTIAL"
READINESS_READY_SHALLOW = "READY_SHALLOW"

SUMMARY_STATUSES = (
    STATUS_NOT_IMPLEMENTED,
    STATUS_FALLBACK_ONLY,
    STATUS_FAILED,
    STATUS_OK,
)

_MISSING_STATUSES = {STATUS_NOT_IMPLEMENTED, STATUS_FALLBACK_ONLY, STATUS_FAILED}


def _load_gap_payload(gap_report_or_path: Any) -> Dict[str, Any]:
    if isinstance(gap_report_or_path, dict):
        return gap_report_or_path
    if isinstance(gap_report_or_path, str):
        with open(gap_report_or_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    raise TypeError("gap_report_or_path must be a dict or path string.")


def _to_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _looks_like_gap_report(payload: Dict[str, Any]) -> bool:
    status_summary = payload.get("status_summary")
    return isinstance(status_summary, dict) and bool(status_summary)


def _build_summary_payload(gap_report_or_path: Any) -> Dict[str, Any]:
    payload = _load_gap_payload(gap_report_or_path)
    if _looks_like_gap_report(payload):
        return payload
    if isinstance(payload, dict) and "plan" in payload:
        return build_collection_gap_report(payload)
    return build_collection_gap_report(payload)


def _coerce_counts_dict() -> Dict[str, int]:
    return {
        STATUS_NOT_IMPLEMENTED: 0,
        STATUS_FALLBACK_ONLY: 0,
        STATUS_FAILED: 0,
        STATUS_OK: 0,
    }


def build_lane_collection_summary(gap_report_or_path: Any) -> Dict[str, Any]:
    gap_report = _build_summary_payload(gap_report_or_path)
    status_summary = gap_report.get("status_summary", {})
    recommendations = gap_report.get("recommended_implementation_order") or []

    if not isinstance(status_summary, dict):
        raise TypeError("gap report payload must include a dict status_summary.")
    if not isinstance(recommendations, list):
        recommendations = []

    lanes = _to_list(gap_report.get("all_lanes"))
    lane_summary: Dict[str, Dict[str, Any]] = {}
    for lane_id in lanes:
        lane_summary[lane_id] = {
            "counts_by_status": _coerce_counts_dict(),
            "top_missing_sources": [],
            "lane_readiness": None,
        }

    for status in SUMMARY_STATUSES:
        entries = status_summary.get(status, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            source_id = entry.get("source_id")
            if not isinstance(source_id, str):
                continue
            impacted_lanes = _to_list(entry.get("lane_impact"))
            for lane_id in impacted_lanes:
                row = lane_summary.setdefault(
                    lane_id,
                    {
                        "counts_by_status": _coerce_counts_dict(),
                        "top_missing_sources": [],
                        "lane_readiness": None,
                    },
                )
                row["counts_by_status"][status] += 1

                # Keep only known statuses; ignore any fabricated extension points.
                if status not in SUMMARY_STATUSES:
                    continue

    weak_sources_by_lane: Dict[str, List[str]] = {}
    seen_by_lane: Dict[str, Set[str]] = {}
    for item in recommendations:
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        if status not in _MISSING_STATUSES:
            continue
        source_id = item.get("source_id")
        if not isinstance(source_id, str):
            continue
        for lane_id in _to_list(item.get("lane_impact")):
            bucket = weak_sources_by_lane.setdefault(lane_id, [])
            seen = seen_by_lane.setdefault(lane_id, set())
            if source_id not in seen:
                seen.add(source_id)
                bucket.append(source_id)

    for lane_id, row in lane_summary.items():
        counts = row["counts_by_status"]
        if counts[STATUS_OK] == 0:
            readiness = READINESS_BLOCKED
        elif any(counts[status] > 0 for status in _MISSING_STATUSES):
            readiness = READINESS_PARTIAL
        else:
            readiness = READINESS_READY_SHALLOW
        row["lane_readiness"] = readiness
        row["top_missing_sources"] = weak_sources_by_lane.get(lane_id, [])

    weak_lanes = [lane_id for lane_id, row in lane_summary.items() if row["lane_readiness"] != READINESS_READY_SHALLOW]

    return {
        "schema_version": "lane_collection_summary_v1",
        "lane_count": len(lane_summary),
        "lane_ids": list(lane_summary.keys()),
        "lane_summary": lane_summary,
        "weak_lanes": weak_lanes,
    }
