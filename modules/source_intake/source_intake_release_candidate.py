"""Release-candidate gate for source-intake candidate pipeline.

This module performs strict preflight checks and only allows candidate
composition when source runtime truth and storage artifacts agree.
Any defect returns zero candidates and no exception leakage.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from modules.source_intake.collector_readiness_registry import (
    READINESS_BLOCKED,
    READINESS_EXTERNAL_BLOCKED,
    READINESS_PARTIAL,
    READINESS_READY,
    load_collector_readiness_registry,
)
from modules.source_intake.daily_collection_executor import (
    COLLECTOR_METHODS,
    DIRECT_COLLECTOR_FACTORIES,
    _has_manager_collector_method,
)
from modules.source_intake.source_intake_consistency_validator import (
    build_source_intake_consistency_report,
)
from modules.source_intake.source_intake_schema import SOURCE_INTAKE_STORAGE_ROOT
from modules.source_intake.validated_topic_candidate_pipeline import (
    run_validated_topic_candidate_pipeline,
)
from modules.trend_collector.trend_source_manager import TrendSourceManager

RC_STATUS_GO = "GO"
RC_STATUS_NO_GO = "NO_GO"


def _coerce_today(today: Optional[Any]) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    if isinstance(today, (datetime, date)):
        return today.isoformat()
    return str(today)


def _read_json(path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not os.path.exists(path):
        return None, f"missing_file:{path}"
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        return None, f"read_failed:{exc}"

    if not isinstance(payload, dict):
        return None, f"invalid_payload_type:{type(payload).__name__}"
    return payload, None


def _dedupe_ordered(values: Sequence[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _extract_readiness_status_by_source(gap_payload: Dict[str, Any]) -> Dict[str, str]:
    sources: Dict[str, str] = {}

    by_readiness = gap_payload.get("source_status_by_readiness")
    if isinstance(by_readiness, dict):
        for readiness_status, entries in by_readiness.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                source_id = entry.get("source_id")
                if isinstance(source_id, str) and source_id:
                    sources[source_id] = str(readiness_status)
        if sources:
            return sources

    status_summary = gap_payload.get("status_summary")
    if not isinstance(status_summary, dict):
        return sources

    for readiness_status, entries in status_summary.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            source_id = entry.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                continue
            source_status = entry.get("readiness_status")
            status = source_status if isinstance(source_status, str) else str(readiness_status)
            sources[source_id] = status

    return sources


def _resolve_source_callability(
    source_manager: Any,
    source_id: str,
    *,
    include_direct: bool,
) -> Dict[str, Any]:
    method_name = COLLECTOR_METHODS.get(source_id)
    if method_name and _has_manager_collector_method(source_manager, method_name):
        return {
            "callable": True,
            "path": "manager",
            "path_ref": method_name,
            "reason": "manager_method",
        }

    if include_direct and source_id in DIRECT_COLLECTOR_FACTORIES:
        factory = DIRECT_COLLECTOR_FACTORIES.get(source_id)
        if callable(factory):
            return {
                "callable": True,
                "path": "direct_factory",
                "path_ref": source_id,
                "reason": "direct_factory",
            }

    return {
        "callable": False,
        "path": None,
        "path_ref": None,
        "reason": "unreachable",
    }


def _build_callability_matrices(
    source_ids: Sequence[str],
    source_manager: Any,
) -> Dict[str, Any]:
    before: Dict[str, Any] = {}
    after: Dict[str, Any] = {}
    for source_id in source_ids:
        before[source_id] = _resolve_source_callability(
            source_manager,
            source_id,
            include_direct=False,
        )
        after[source_id] = _resolve_source_callability(
            source_manager,
            source_id,
            include_direct=True,
        )

    before_reachable = _dedupe_ordered(
        source_id for source_id, info in before.items() if info.get("callable")
    )
    after_reachable = _dedupe_ordered(
        source_id for source_id, info in after.items() if info.get("callable")
    )

    return {
        "before": before,
        "after": after,
        "added_by_factory": _dedupe_ordered(
            [source_id for source_id in after_reachable if source_id not in before_reachable]
        ),
        "removed_by_factory": _dedupe_ordered(
            [source_id for source_id in before_reachable if source_id not in after_reachable]
        ),
        "mapped_unreachable": [
            source_id
            for source_id in source_ids
            if source_id in COLLECTOR_METHODS and not after[source_id]["callable"]
        ],
    }


def _fail_closed(
    reason_code: str,
    preflight: Dict[str, Any],
    source_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    return {
        "status": RC_STATUS_NO_GO,
        "go_no_go": RC_STATUS_NO_GO,
        "reason_code": reason_code,
        "candidates": [],
        "candidate_count": 0,
        "preflight": preflight,
        "candidate_source_count": len(source_ids or []),
    }


def run_source_intake_release_candidate(
    *,
    today: Optional[Any] = None,
    root: Optional[str] = None,
    source_manager: Optional[Any] = None,
    source_intake_status_bundle_path: Optional[str] = None,
    collection_gap_report_path: Optional[str] = None,
    daily_shallow_collection_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Run preflight and validated candidate composition.

    Returns "GO" only when preflight gates are fully satisfied and the
    candidate pipeline returns candidate-ready results.
    """

    today_str = _coerce_today(today)
    base_root = os.path.join(root or SOURCE_INTAKE_STORAGE_ROOT, today_str)
    runtime_manager = source_manager or TrendSourceManager()

    status_bundle_path = (
        source_intake_status_bundle_path
        or os.path.join(base_root, "source_intake_status_bundle.json")
    )
    gap_path = collection_gap_report_path or os.path.join(base_root, "collection_gap_report.json")
    shallow_path = daily_shallow_collection_path or os.path.join(base_root, "daily_shallow_collection.json")

    status_bundle_dir = os.path.dirname(os.path.abspath(status_bundle_path))
    gap_path_dir = os.path.dirname(os.path.abspath(gap_path))
    if status_bundle_dir != gap_path_dir:
        return {
            "status": RC_STATUS_NO_GO,
            "go_no_go": RC_STATUS_NO_GO,
            "reason_code": "gap_path_sibling_mismatch",
            "candidates": [],
            "candidate_count": 0,
            "preflight": {
                "stage": "artifact_paths",
                "status_bundle_path": status_bundle_path,
                "collection_gap_report_path": gap_path,
                "sibling_path_mismatch": f"bundle_parent={status_bundle_dir}|gap_parent={gap_path_dir}",
            },
        }

    status_bundle_basename = os.path.basename(status_bundle_dir)
    consistency_root = (
        os.path.dirname(status_bundle_dir)
        if status_bundle_basename == today_str
        else status_bundle_dir
    )
    report = build_source_intake_consistency_report(
        today=today_str,
        root=consistency_root,
    )

    preflight: Dict[str, Any] = {
        "stage": "preflight",
        "today": today_str,
        "status_bundle_path": status_bundle_path,
        "collection_gap_report_path": gap_path,
        "daily_shallow_collection_path": shallow_path,
        "consistency_status": report.get("status"),
        "consistency_mismatches": report.get("mismatches", []),
        "consistency_source_counts": report.get("counts", {}),
    }

    if report.get("status") != "ok":
        preflight["status"] = "consistency_failed"
        return _fail_closed("consistency_failed", preflight, report.get("source_ids", {}).get("gap", []))

    # Ensure gap report and status bundle can be loaded and parsed as objects.
    status_bundle_payload, status_bundle_error = _read_json(status_bundle_path)
    if status_bundle_payload is None:
        preflight["status_bundle_error"] = status_bundle_error
        return _fail_closed("status_bundle_load_failed", preflight)

    gap_payload, gap_error = _read_json(gap_path)
    if gap_payload is None:
        preflight["gap_report_error"] = gap_error
        return _fail_closed("gap_report_load_failed", preflight)

    preflight["status_bundle_error"] = status_bundle_error
    preflight["gap_report_error"] = gap_error

    # Confirm explicit artifacts are present in the same readiness scope.
    # (read artifacts as data-only checks; no runtime execution here.)
    _, shallow_error = _read_json(shallow_path)
    preflight["daily_shallow_collection_error"] = shallow_error
    if shallow_error is not None:
        return _fail_closed("daily_shallow_collection_load_failed", preflight)

    # Derive runtime truth for each source from registry + callability checks.
    readiness_by_source = _extract_readiness_status_by_source(gap_payload)
    source_ids = list(readiness_by_source.keys())
    preflight["gap_source_ids"] = source_ids

    readiness_counts = {
        READINESS_READY: 0,
        READINESS_PARTIAL: 0,
        READINESS_BLOCKED: 0,
        READINESS_EXTERNAL_BLOCKED: 0,
    }
    for value in readiness_by_source.values():
        if value in readiness_counts:
            readiness_counts[value] += 1
    preflight["readiness_counts"] = readiness_counts

    if not source_ids:
        preflight["status"] = "empty_gap_source_set"
        return _fail_closed("gap_source_set_empty", preflight)

    # Keep partial/blocked/external_blocked fail-closed.
    if readiness_counts[READINESS_PARTIAL] > 0 or readiness_counts[READINESS_BLOCKED] > 0 or readiness_counts[READINESS_EXTERNAL_BLOCKED] > 0:
        preflight["status"] = "non_ready_readiness"
        return _fail_closed("non_ready_sources_blocked", preflight, source_ids)

    callability = _build_callability_matrices(source_ids, runtime_manager)
    preflight["callability_matrix_before"] = callability["before"]
    preflight["callability_matrix_after"] = callability["after"]
    preflight["callability_delta"] = {
        "added_by_factory": callability["added_by_factory"],
        "removed_by_factory": callability["removed_by_factory"],
    }
    preflight["mapped_unreachable"] = callability["mapped_unreachable"]

    # Reject if claimed readiness does not agree with runtime callability.
    mismatches: List[str] = []
    for source_id in source_ids:
        claimed = readiness_by_source.get(source_id)
        callable_after = bool(callability["after"].get(source_id, {}).get("callable"))
        if claimed == READINESS_READY and not callable_after:
            mismatches.append(f"ready_source_not_callable:{source_id}")
        elif claimed in {READINESS_PARTIAL, READINESS_BLOCKED, READINESS_EXTERNAL_BLOCKED} and callable_after:
            mismatches.append(f"callable_source_not_ready:{source_id}:{claimed}")

    if mismatches:
        preflight["readiness_callability_mismatches"] = mismatches
        return _fail_closed("readiness_callability_mismatch", preflight, source_ids)

    if callability["mapped_unreachable"]:
        preflight["status"] = "mapped_unreachable"
        return _fail_closed("mapped_unreachable", preflight, callability["mapped_unreachable"])

    try:
        pipeline_result = run_validated_topic_candidate_pipeline(
            daily_shallow_collection=shallow_path,
            source_intake_status_bundle_path=status_bundle_path,
            collection_gap_report_path=gap_path,
        )
    except Exception as exc:
        preflight["pipeline_exception"] = f"{type(exc).__name__}: {exc}"
        return _fail_closed("pipeline_exception", preflight, source_ids)

    preflight["pipeline_status"] = pipeline_result.get("status")
    preflight["pipeline_stage_diagnostics"] = pipeline_result.get("stage_diagnostics", {})

    candidates = pipeline_result.get("candidates") or []
    if pipeline_result.get("status") != "candidate_ready" or not candidates:
        preflight["status"] = "pipeline_blocked"
        return _fail_closed("pipeline_blocked", preflight, source_ids)

    return {
        "status": RC_STATUS_GO,
        "go_no_go": RC_STATUS_GO,
        "reason_code": "ready",
        "candidates": candidates,
        "candidate_count": len(candidates),
        "preflight": preflight,
        "pipeline": pipeline_result,
    }


__all__ = ["run_source_intake_release_candidate", "RC_STATUS_GO", "RC_STATUS_NO_GO"]
