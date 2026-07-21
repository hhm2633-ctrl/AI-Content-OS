"""Build a deterministic Source Health / Collector Statistics dashboard."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from modules.source_intake.collection_gap_report import (
    STATUS_FAILED,
    STATUS_FALLBACK_ONLY,
    STATUS_NOT_IMPLEMENTED,
    STATUS_OK,
)
from modules.source_intake.lane_collection_summary import (
    READINESS_BLOCKED,
    READINESS_PARTIAL,
    READINESS_READY_SHALLOW,
)

SCHEMA_VERSION = "source_health_dashboard_v1"
EVIDENCE_SCOPE = "artifact_reported"

DASHBOARD_STATUS_READY = "ready"
DASHBOARD_STATUS_PARTIAL = "partial"
DASHBOARD_STATUS_BLOCKED = "blocked"

FRESHNESS_STALE_THRESHOLD_SECONDS = 24 * 60 * 60
SOURCE_STATUS_ORDER = [
    STATUS_FAILED,
    STATUS_NOT_IMPLEMENTED,
    STATUS_FALLBACK_ONLY,
    STATUS_OK,
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return None, "missing"
    except Exception as exc:
        return None, f"malformed:{type(exc).__name__}"

    if not isinstance(payload, dict):
        return None, "malformed:not_object"
    return payload, None


def _coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return default
    return default


def _to_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _parse_timestamp(raw: Any) -> Optional[datetime]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _extract_timestamp(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for key in ("updated_at", "generated_at", "checked_at", "as_of", "generated"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _freshness_status(timestamp: Optional[str]) -> str:
    if not timestamp:
        return "unknown"
    parsed = _parse_timestamp(timestamp)
    if not parsed:
        return "unknown"
    age = datetime.now(timezone.utc).astimezone(timezone.utc) - parsed
    if age.total_seconds() < 0:
        return "unknown"
    if age.total_seconds() <= FRESHNESS_STALE_THRESHOLD_SECONDS:
        return "fresh"
    return "stale"


def _build_freshness_summary(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {"fresh": 0, "stale": 0, "unknown": 0}
    for entry in entries:
        status = entry.get("freshness", "unknown")
        if status not in counts:
            status = "unknown"
        counts[status] += 1

    if counts["stale"] > 0:
        aggregate = "stale"
    elif counts["fresh"] > 0:
        aggregate = "fresh"
    else:
        aggregate = "unknown"

    return {
        "aggregate": aggregate,
        "counts": counts,
        "inputs": entries,
    }


def _build_status_counts(payload: Dict[str, Any]) -> Dict[str, int]:
    raw = payload.get("status_counts")
    if not isinstance(raw, dict):
        return {
            STATUS_NOT_IMPLEMENTED: 0,
            STATUS_FALLBACK_ONLY: 0,
            STATUS_FAILED: 0,
            STATUS_OK: 0,
        }
    result = {
        STATUS_NOT_IMPLEMENTED: _coerce_int(raw.get(STATUS_NOT_IMPLEMENTED)),
        STATUS_FALLBACK_ONLY: _coerce_int(raw.get(STATUS_FALLBACK_ONLY)),
        STATUS_FAILED: _coerce_int(raw.get(STATUS_FAILED)),
        STATUS_OK: _coerce_int(raw.get(STATUS_OK)),
    }
    return result


def _safe_percent(numerator: Any, denominator: Any) -> float:
    total = _coerce_int(denominator)
    if total <= 0:
        return 0.0
    return round(max(0, _coerce_int(numerator)) / total * 100.0, 2)


def _normalize_source_health(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {"present": False}

    latest = payload.get("latest")
    records = payload.get("records", [])
    by_source: Dict[str, Dict[str, Any]] = {}
    if isinstance(latest, dict):
        for source, value in latest.items():
            if isinstance(value, dict):
                by_source[str(source)] = value

    if not by_source and isinstance(records, list):
        for item in records:
            if not isinstance(item, dict):
                continue
            source = item.get("source")
            if not isinstance(source, str):
                continue
            by_source[source] = item

    return {
        "present": True,
        "updated_at": payload.get("updated_at"),
        "records_count": len(records) if isinstance(records, list) else 0,
        "latest_by_source": by_source,
    }


def _normalize_collector_statistics(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "present": False,
            "updated_at": None,
            "source_count": 0,
            "totals": {
                "total_attempts": 0,
                "total_success": 0,
                "total_failures": 0,
                "total_fallback_used": 0,
            },
        }

    sources = payload.get("sources")
    source_map: Dict[str, Dict[str, Any]] = {}
    if isinstance(sources, list):
        for item in sources:
            if not isinstance(item, dict):
                continue
            source_id = item.get("source")
            if isinstance(source_id, str):
                source_map[source_id] = item

    total_attempts = 0
    total_success = 0
    total_failures = 0
    total_fallback_used = 0
    for item in source_map.values():
        total_attempts += _coerce_int(item.get("total_attempts"))
        total_success += _coerce_int(item.get("total_success"))
        total_failures += _coerce_int(item.get("total_failures"))
        total_fallback_used += _coerce_int(item.get("total_fallback_used"))

    return {
        "present": True,
        "updated_at": payload.get("updated_at"),
        "source_count": len(source_map),
        "totals": {
            "total_attempts": total_attempts,
            "total_success": total_success,
            "total_failures": total_failures,
            "total_fallback_used": total_fallback_used,
        },
        "success_rate": _safe_percent(total_success, total_attempts),
        "by_source": source_map,
    }


def _collect_source_rows(
    gap_payload: Optional[Dict[str, Any]],
    source_health: Dict[str, Any],
    collector_stats: Dict[str, Any],
) -> List[Dict[str, Any]]:
    status_summary = {}
    if isinstance(gap_payload, dict):
        status_summary = gap_payload.get("status_summary", {})
    if not isinstance(status_summary, dict):
        return []

    rows_by_source: Dict[str, Dict[str, Any]] = {}
    for status in SOURCE_STATUS_ORDER:
        entries = status_summary.get(status, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            source_id = entry.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                continue
            lane_impact = sorted(set(_to_list(entry.get("lane_impact"))))
            row = {
                "source_id": source_id,
                "reported_status": status,
                "counts": {
                    "items": _coerce_int(entry.get("item_count", 0)),
                    "fallback_items": _coerce_int(entry.get("fallback_item_count", 0)),
                },
                "evidence": {
                    "lanes": lane_impact,
                    "attempted": bool(entry.get("attempted", False)),
                    "success": bool(entry.get("success", False)),
                    "skip_reason": entry.get("skip_reason"),
                    "error": entry.get("error"),
                    "source_type": entry.get("source_type"),
                },
                "source_health": source_health.get("latest_by_source", {}).get(source_id, {}),
                "collector_statistics": collector_stats.get("by_source", {}).get(source_id, {}),
            }
            row["counts"]["fallback_ratio"] = _safe_percent(row["counts"]["fallback_items"], row["counts"]["items"])
            existing = rows_by_source.get(source_id)
            if existing is None or SOURCE_STATUS_ORDER.index(status) < SOURCE_STATUS_ORDER.index(existing["reported_status"]):
                rows_by_source[source_id] = row

    rows = list(rows_by_source.values())
    rows.sort(key=lambda item: (SOURCE_STATUS_ORDER.index(item["reported_status"]), item["source_id"]))
    return rows


def _collect_lane_rows(
    lane_payload: Optional[Dict[str, Any]],
    gap_payload: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not isinstance(lane_payload, dict):
        return []

    lane_summary = lane_payload.get("lane_summary")
    if not isinstance(lane_summary, dict):
        return []

    if isinstance(gap_payload, dict):
        all_lanes = gap_payload.get("all_lanes")
        if isinstance(all_lanes, list):
            for lane_id in all_lanes:
                lane_summary.setdefault(str(lane_id), lane_summary.get(str(lane_id), {}))

    rows: List[Dict[str, Any]] = []
    for lane_id in sorted(lane_summary.keys()):
        lane_data = lane_summary[lane_id]
        if not isinstance(lane_data, dict):
            lane_data = {}
        counts = lane_data.get("counts_by_status", {})
        rows.append(
            {
                "lane_id": lane_id,
                "lane_readiness": lane_data.get("lane_readiness", READINESS_BLOCKED),
                "counts_by_status": {
                    STATUS_NOT_IMPLEMENTED: _coerce_int(counts.get(STATUS_NOT_IMPLEMENTED)),
                    STATUS_FALLBACK_ONLY: _coerce_int(counts.get(STATUS_FALLBACK_ONLY)),
                    STATUS_FAILED: _coerce_int(counts.get(STATUS_FAILED)),
                    STATUS_OK: _coerce_int(counts.get(STATUS_OK)),
                },
                "top_missing_sources": _to_list(lane_data.get("top_missing_sources")),
            }
        )
    return rows


def _quality_checks(
    status_bundle: Optional[Dict[str, Any]],
    gap_payload: Optional[Dict[str, Any]],
    lane_summary: Optional[Dict[str, Any]],
    quality: Dict[str, Any],
) -> None:
    if status_bundle is not None and isinstance(status_bundle, dict):
        status_counts = _build_status_counts(gap_payload or {})
        source_count = _coerce_int((gap_payload or {}).get("source_count"))
        if source_count and source_count != sum(status_counts.values()):
            quality["contradictory_inputs"].append("gap_report:source_count_mismatch")
        if status_bundle.get("source_count") and status_bundle.get("source_count") != source_count:
            quality["contradictory_inputs"].append("status_bundle:source_count_mismatch")

    if isinstance(lane_summary, dict):
        expected = _coerce_int(lane_summary.get("lane_count"))
        lane_rows = _collect_lane_rows(lane_summary, gap_payload)
        if expected and expected != len(lane_rows):
            quality["contradictory_inputs"].append("lane_summary:lane_count_mismatch")


def _collect_blockers(
    required_quality: List[str],
    optional_quality: List[str],
    lane_rows: List[Dict[str, Any]],
    source_rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, str]], List[str], bool]:
    blockers: List[Dict[str, str]] = []
    next_actions: List[str] = []
    is_blocked = False

    for item in required_quality:
        is_blocked = True
        path = item["path"]
        reason = item["reason"]
        blockers.append({"type": "required_artifact", "path": path, "reason": reason})
        next_actions.append(f"Re-run upstream step to produce a valid JSON artifact at {path}.")

    for item in optional_quality:
        blockers.append(
            {
                "type": "optional_artifact",
                "path": item["path"],
                "reason": item["reason"],
            }
        )
        next_actions.append(f"Optional artifact {item['path']} could not be parsed; run its producer to repopulate.")

    for row in lane_rows:
        if row["lane_readiness"] in {READINESS_BLOCKED, READINESS_PARTIAL}:
            blockers.append(
                {
                    "type": "lane_readiness",
                    "path": row["lane_id"],
                    "reason": f"lane_readiness_{row['lane_readiness']}",
                }
            )
            next_actions.append(f"Improve lane '{row['lane_id']}' by addressing missing/failed source coverage.")

    for row in source_rows:
        status = row["reported_status"]
        if status in {STATUS_FAILED, STATUS_NOT_IMPLEMENTED, STATUS_FALLBACK_ONLY}:
            blockers.append(
                {
                    "type": "source_status",
                    "path": row["source_id"],
                    "reason": status,
                }
            )

    blockers.sort(key=lambda item: (item["type"], item["path"], item["reason"]))
    seen_next = set()
    ordered_next = []
    for action in next_actions:
        if action in seen_next:
            continue
        seen_next.add(action)
        ordered_next.append(action)

    return blockers[:40], ordered_next[:40], is_blocked


def _build_readiness_counts_and_percentages(lane_rows: List[Dict[str, Any]]) -> Tuple[Dict[str, int], Dict[str, float]]:
    counts = {
        "ready": 0,
        "partial": 0,
        "blocked": 0,
    }
    for row in lane_rows:
        readiness = row.get("lane_readiness")
        if readiness == READINESS_READY_SHALLOW:
            counts["ready"] += 1
        elif readiness == READINESS_PARTIAL:
            counts["partial"] += 1
        else:
            counts["blocked"] += 1

    total = max(1, sum(counts.values()))
    return counts, {
        "ready": _safe_percent(counts["ready"], total),
        "partial": _safe_percent(counts["partial"], total),
        "blocked": _safe_percent(counts["blocked"], total),
    }


def build_source_health_dashboard(
    status_bundle_path: str,
    gap_report_path: str,
    lane_summary_path: str,
    source_health_path: Optional[str] = None,
    collector_statistics_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a deterministic dashboard from artifact inputs."""
    generated_at = _now_iso()

    status_bundle, status_bundle_error = _read_json(status_bundle_path)
    gap_payload, gap_error = _read_json(gap_report_path)
    lane_payload, lane_error = _read_json(lane_summary_path)
    source_health_payload, source_health_error = (
        _read_json(source_health_path)
        if source_health_path
        else (None, None)
    )
    collector_payload, collector_error = (
        _read_json(collector_statistics_path)
        if collector_statistics_path
        else (None, None)
    )

    required_quality_missing: List[Dict[str, str]] = []
    optional_quality: List[Dict[str, str]] = []

    for path, error, required in (
        (status_bundle_path, status_bundle_error, True),
        (gap_report_path, gap_error, True),
        (lane_summary_path, lane_error, True),
        (source_health_path, source_health_error, False),
        (collector_statistics_path, collector_error, False),
    ):
        if error == "missing":
            item = {"path": path, "reason": "missing_artifact"}
            (required_quality_missing if required else optional_quality).append(item)
        if error and error.startswith("malformed"):
            item = {"path": path, "reason": error}
            (required_quality_missing if required else optional_quality).append(item)

    source_health = _normalize_source_health(source_health_payload)
    collector_stats = _normalize_collector_statistics(collector_payload)

    source_rows = _collect_source_rows(gap_payload, source_health, collector_stats)
    lane_rows = _collect_lane_rows(lane_payload, gap_payload)

    quality = {
        "missing_artifacts": [item["path"] for item in required_quality_missing if item["reason"] == "missing_artifact"],
        "malformed_artifacts": [
            {"path": item["path"], "reason": item["reason"]}
            for item in required_quality_missing
            if item["reason"].startswith("malformed")
        ]
        + [
            {"path": item["path"], "reason": item["reason"]}
            for item in optional_quality
            if item["reason"].startswith("malformed")
        ],
        "contradictory_inputs": [],
    }
    _quality_checks(status_bundle, gap_payload, lane_payload, quality)

    freshness_inputs = []
    for name, payload in (
        ("status_bundle", status_bundle),
        ("gap_report", gap_payload),
        ("lane_summary", lane_payload),
        ("source_health", source_health_payload),
        ("collector_statistics", collector_payload),
    ):
        if payload is None:
            timestamp = None
        else:
            timestamp = _extract_timestamp(payload)
        freshness_inputs.append(
            {
                "artifact": name,
                "timestamp": timestamp,
                "freshness": _freshness_status(timestamp),
                "source_path": locals()[f"{name}_path"] if f"{name}_path" in locals() else None,
            }
        )

    freshness = _build_freshness_summary(freshness_inputs)
    source_counts = _build_status_counts(gap_payload or {})
    source_count = _coerce_int((gap_payload or {}).get("source_count", sum(source_counts.values())))

    source_percentages = {
        STATUS_NOT_IMPLEMENTED: _safe_percent(source_counts[STATUS_NOT_IMPLEMENTED], source_count),
        STATUS_FALLBACK_ONLY: _safe_percent(source_counts[STATUS_FALLBACK_ONLY], source_count),
        STATUS_FAILED: _safe_percent(source_counts[STATUS_FAILED], source_count),
        STATUS_OK: _safe_percent(source_counts[STATUS_OK], source_count),
    }

    readiness_counts, readiness_percentages = _build_readiness_counts_and_percentages(lane_rows)
    blockers, next_actions, hard_block = _collect_blockers(
        required_quality_missing,
        optional_quality,
        lane_rows,
        source_rows,
    )

    if quality["contradictory_inputs"]:
        hard_block = True
    status = (
        DASHBOARD_STATUS_BLOCKED if hard_block
        else DASHBOARD_STATUS_PARTIAL if blockers
        else DASHBOARD_STATUS_READY
    )

    if status != DASHBOARD_STATUS_READY:
        pass

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "input_paths": {
            "status_bundle": status_bundle_path,
            "gap_report": gap_report_path,
            "lane_summary": lane_summary_path,
            "source_health": source_health_path,
            "collector_statistics": collector_statistics_path,
        },
        "input_timestamps": {
            "status_bundle": _extract_timestamp(status_bundle),
            "gap_report": _extract_timestamp(gap_payload),
            "lane_summary": _extract_timestamp(lane_payload),
            "source_health": _extract_timestamp(source_health_payload),
            "collector_statistics": _extract_timestamp(collector_payload),
        },
        "evidence_scope": EVIDENCE_SCOPE,
        "freshness": freshness,
        "dashboard_status": status,
        "source_summary": {
            "sources_total": source_count,
            "status_counts": source_counts,
            "status_percentages": source_percentages,
            "weak_lanes": _to_list((status_bundle or {}).get("weak_lanes"))
            if isinstance(status_bundle, dict)
            else [],
        },
        "readiness_summary": {
            "source_intake_lanes": {
                "counts": readiness_counts,
                "percentages": readiness_percentages,
            },
            "implementation_counts": {
                "blocked": _coerce_int((status_bundle or {}).get("status_counts", {}).get("BLOCKED", 0)),
                "partial": _coerce_int((status_bundle or {}).get("status_counts", {}).get("PARTIAL", 0)),
                "ready": _coerce_int((status_bundle or {}).get("status_counts", {}).get("READY", 0)),
            },
        },
        "lane_summaries": lane_rows,
        "source_rows": source_rows,
        "collector_statistics": {
            "present": collector_stats["present"],
            "payload": collector_stats,
            "summary": {
                "updated_at": collector_stats.get("updated_at"),
                "source_count": collector_stats.get("source_count", 0),
                "totals": collector_stats["totals"],
            },
        },
        "source_health": {
            "present": source_health["present"],
            "payload": source_health,
        },
        "data_quality": quality,
        "blockers": blockers,
        "next_actions": next_actions,
    }


def write_source_health_dashboard(
    dashboard: Dict[str, Any],
    output_path: Optional[str],
) -> Dict[str, Any]:
    result = {
        "status": "skipped",
        "output_path": output_path,
        "dashboard": dashboard,
    }
    if not output_path:
        return result

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(dashboard, handle, ensure_ascii=False, indent=2)
        result["status"] = "written"
    except Exception as error:
        result["status"] = "write_failed"
        result["error"] = str(error)
    return result
