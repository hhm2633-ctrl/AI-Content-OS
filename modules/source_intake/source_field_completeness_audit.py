"""Deterministic analyzer for completed daily_shallow_collection_v1 payloads.

The analyzer never mutates payloads or storage. It classifies field/metric
completeness by source, separates missing/unsupported/fallback/cache/malformed
states, and emits evidence-based remediation priorities without making network calls.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from modules.source_intake.source_intake_schema import VISIBLE_METRIC_KEYS

SCHEMA_VERSION = "source_field_completeness_audit_v1"
DAILY_SCHEMA_VERSION = "daily_shallow_collection_v1"
DEFAULT_CONFIG_PATH = os.path.join("config", "source_intake_field_completeness.json")

STATUS_PRESENT = "present"
STATUS_MISSING = "missing"
STATUS_MALFORMED = "malformed"
STATUS_UNSUPPORTED = "unsupported"
STATUS_NO_DATA = "no_data"
STATUS_UNKNOWN = "unknown"


def _coerce_today(today: Optional[Any]) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    if isinstance(today, (datetime, date)):
        return today.isoformat()
    return str(today)


def _load_json(path: str) -> Optional[Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return None
    except Exception:
        return None


def _empty_output() -> Dict[str, Any]:
    return {
        "status": "invalid_input",
        "schema_version": SCHEMA_VERSION,
        "payload_schema_version": None,
        "date": None,
        "today": None,
        "source_count": 0,
        "item_count": 0,
        "malformed_item_count": 0,
        "errors": [],
        "source_reports": {},
        "remediation_queue": [],
    }


def _default_config() -> Dict[str, Any]:
    return {
        "schema_version": "source_field_completeness_config_v1",
        "tracked_fields": [
            "title",
            "link",
            "summary",
            "publisher",
            "published_at",
            "rank_position",
        ],
        "tracked_engagement_metrics": list(VISIBLE_METRIC_KEYS) + ["scraps", "shares"],
        "field_aliases": {
            "title": ["title", "keyword"],
            "link": ["link", "url"],
            "summary": ["summary"],
            "publisher": ["publisher", "source_name", "source"],
            "published_at": ["published_at", "published_date", "published_at_iso"],
            "rank_position": ["rank_position", "rank"],
        },
        "metric_aliases": {
            key: [key] for key in (list(VISIBLE_METRIC_KEYS) + ["scraps", "shares"])
        },
        "source_supported_engagement_metrics": {},
        "remediation_scoring": {
            "field_weights": {
                "title": 1.9,
                "link": 1.8,
                "summary": 1.5,
                "publisher": 1.2,
                "published_at": 1.5,
                "rank_position": 1.3,
            },
            "field_malformed_multiplier": 1.4,
            "engagement_supported_metric": {"missing": 0.9, "malformed": 1.2},
            "fallback_penalty": 0.7,
            "cache_penalty": 0.4,
            "no_data_penalty": 6.0,
        },
        "remediation_thresholds": {
            "critical": 72.0,
            "high": 44.0,
            "medium": 18.0,
            "low": 4.0,
        },
    }


def _coerce_config(raw: Any) -> Dict[str, Any]:
    base = _default_config()
    if not isinstance(raw, dict):
        return base

    config = dict(base)
    for key, value in raw.items():
        if value is None:
            continue
        config[key] = value

    config["tracked_fields"] = list(config.get("tracked_fields") or base["tracked_fields"])
    config["tracked_engagement_metrics"] = list(
        config.get("tracked_engagement_metrics")
        or base["tracked_engagement_metrics"]
    )
    return config


def _normalize_source_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_empty_text(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip()


def _to_positive_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        return int(value) if value.is_integer() and value >= 0 else None
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        return int(cleaned) if cleaned.isdigit() else None
    return None


def _has_valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False

    from email.utils import parsedate_to_datetime

    candidates = [value, value.replace("Z", "+00:00")]
    for raw in candidates:
        if not raw:
            continue
        if " " in raw and "," in raw:
            try:
                parsed = parsedate_to_datetime(raw)
                if parsed:
                    return True
            except (TypeError, ValueError, IndexError):
                pass
        try:
            datetime.fromisoformat(raw)
            return True
        except (TypeError, ValueError):
            pass
    return False


def _extract_value(item: Dict[str, Any], aliases: Sequence[str]) -> Tuple[Any, bool]:
    for key in aliases:
        if key in item:
            return item.get(key), True
    return None, False


def _extract_metric(item: Dict[str, Any], metric: str, aliases: Sequence[str]) -> Tuple[Any, bool]:
    value, found = _extract_value(item, aliases)
    if found:
        return value, True

    visible_metrics = item.get("visible_metrics")
    if isinstance(visible_metrics, dict):
        for key in aliases:
            if key in visible_metrics:
                return visible_metrics.get(key), True

    return None, False


def _evaluate_required_field(
    item: Dict[str, Any],
    field: str,
    aliases: Sequence[str],
    malformed_count: int,
    missing_count: int,
    present_count: int,
) -> Tuple[int, int, int, str]:
    del malformed_count, missing_count, present_count

    value, found = _extract_value(item, aliases)

    if not found or value is None:
        return 0, 1, 0, STATUS_MISSING

    if field in {"title", "link", "summary", "publisher"}:
        if _is_empty_text(value):
            return 0, 1, 0, STATUS_MISSING
        if not isinstance(value, str):
            return 0, 0, 1, STATUS_MALFORMED
        return 1, 0, 0, STATUS_PRESENT

    if field == "published_at":
        if not _has_valid_timestamp(str(value)):
            return 0, 0, 1, STATUS_MALFORMED
        return 1, 0, 0, STATUS_PRESENT

    if field == "rank_position":
        if _to_positive_int(value) is None:
            return 0, 0, 1, STATUS_MALFORMED
        return 1, 0, 0, STATUS_PRESENT

    return 0, 0, 1, STATUS_MALFORMED


def _classify_metric(
    raw: Any,
    observed: bool,
    metric_supported: bool,
    item_count: int,
    present: int,
    missing: int,
    malformed: int,
) -> Dict[str, Any]:
    if metric_supported:
        if not observed:
            return {
                "supported": True,
                "status": STATUS_MISSING,
                "present_count": present,
                "missing_count": item_count,
                "malformed_count": malformed,
                "observed_count": 0,
                "present_rate": 0.0,
                "missing_rate": 1.0 if item_count else 0.0,
                "malformed_rate": 0.0,
            }

        normalized = _to_positive_int(raw)
        if normalized is None:
            return {
                "supported": True,
                "status": STATUS_MALFORMED,
                "present_count": present,
                "missing_count": missing,
                "malformed_count": malformed + 1,
                "observed_count": present + malformed + 1,
                "present_rate": round((present) / item_count, 4) if item_count else 0.0,
                "missing_rate": round((missing) / item_count, 4) if item_count else 0.0,
                "malformed_rate": round((malformed + 1) / item_count, 4) if item_count else 0.0,
            }

        return {
            "supported": True,
            "status": STATUS_PRESENT,
            "present_count": present + 1,
            "missing_count": missing,
            "malformed_count": malformed,
            "observed_count": present + malformed + 1,
            "present_rate": round((present + 1) / item_count, 4) if item_count else 0.0,
            "missing_rate": round((missing) / item_count, 4) if item_count else 0.0,
            "malformed_rate": 0.0,
        }

    observed_present = present + missing + malformed
    status = STATUS_UNSUPPORTED if missing == 0 and malformed == 0 and present == 0 else STATUS_MALFORMED
    return {
        "supported": False,
        "status": status,
        "present_count": 0,
        "missing_count": 0,
        "malformed_count": 0,
        "observed_count": observed_present,
        "present_rate": 0.0,
        "missing_rate": 0.0,
        "malformed_rate": 0.0,
    }


def _rate(value: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(value / denominator, 4)


def _build_field_block(counts: Dict[str, int], denominator: int) -> Dict[str, Any]:
    present = counts["present"]
    missing = counts["missing"]
    malformed = counts["malformed"]
    if denominator == 0:
        status = STATUS_NO_DATA
    elif present == denominator and malformed == 0:
        status = STATUS_PRESENT
    elif malformed > 0 and malformed >= missing:
        status = STATUS_MALFORMED
    elif missing > 0:
        status = STATUS_MISSING
    elif present > 0:
        status = STATUS_PRESENT
    else:
        status = STATUS_UNKNOWN

    return {
        "status": status,
        "present_count": present,
        "missing_count": missing,
        "malformed_count": malformed,
        "present_rate": _rate(present, denominator),
        "missing_rate": _rate(missing, denominator),
        "malformed_rate": _rate(malformed, denominator),
    }


def _build_metric_block(
    metric: str,
    raw_supported: bool,
    source_config: Dict[str, Any],
    counts: Dict[str, int],
    item_count: int,
    metrics_aliases: Dict[str, Sequence[str]],
    item_values: List[Any],
) -> Dict[str, Any]:
    present = 0
    missing = 0
    malformed = 0
    for value in item_values:
        if value is None:
            missing += 1
            continue

        normalized = _to_positive_int(value)
        if normalized is None:
            malformed += 1
        else:
            present += 1

    if not raw_supported:
        return {
            "metric": metric,
            "supported": False,
            "status": STATUS_UNSUPPORTED,
            "present_count": 0,
            "missing_count": 0,
            "malformed_count": 0,
            "observed_count": sum(1 for value in item_values if value is not None),
            "rate": 0.0,
            "aliases": list(metrics_aliases.get(metric, (metric,))),
            "evidence": {
                "reason": "Metric not configured as supported for this source in field completeness config.",
            },
        }

    if item_count == 0:
        status = STATUS_NO_DATA
        present_rate = missing_rate = malformed_rate = 0.0
    else:
        present_rate = _rate(present, item_count)
        missing_rate = _rate(missing, item_count)
        malformed_rate = _rate(malformed, item_count)
        if present == item_count:
            status = STATUS_PRESENT
        elif malformed > 0:
            status = STATUS_MALFORMED
        elif missing > 0:
            status = STATUS_MISSING
        else:
            status = STATUS_UNKNOWN

    return {
        "metric": metric,
        "supported": True,
        "status": status,
        "present_count": present,
        "missing_count": missing,
        "malformed_count": malformed,
        "observed_count": present + malformed,
        "rate": present_rate,
        "aliases": list(metrics_aliases.get(metric, (metric,))),
        "rates": {
            "present": present_rate,
            "missing": missing_rate,
            "malformed": malformed_rate,
        },
    }


def _remediation_priority(
    source_id: str,
    item_count: int,
    field_report: Dict[str, Dict[str, Any]],
    metric_report: Dict[str, Dict[str, Any]],
    collection_profile: Dict[str, Any],
    remediation_cfg: Dict[str, Any],
    source_supported_metrics: Sequence[str],
) -> Dict[str, Any]:
    if item_count == 0:
        score = remediation_cfg.get("no_data_penalty", 0.0)
        reasons = [
            {
                "area": "collection",
                "issue": "no_items",
                "impact": min(round(score, 4), 100.0),
                "evidence": "No collected items for source in payload. Remediation must treat this as blocked ingestion."
            }
        ]
    else:
        score = 0.0
        reasons = []
        field_weights = remediation_cfg.get("field_weights", {})

        for field, details in field_report.items():
            missing_rate = details["missing_rate"]
            malformed_rate = details["malformed_rate"]
            weight = float(field_weights.get(field, 1.0))
            malformed_factor = float(remediation_cfg.get("field_malformed_multiplier", 1.0))

            if malformed_rate > 0:
                penalty = malformed_rate * weight * malformed_factor * 100.0
                score += penalty
                reasons.append({
                    "area": "field",
                    "issue": "malformed",
                    "field": field,
                    "impact": round(penalty, 4),
                    "count": details["malformed_count"],
                })
            if missing_rate > 0:
                penalty = missing_rate * weight * 100.0
                score += penalty
                reasons.append({
                    "area": "field",
                    "issue": "missing",
                    "field": field,
                    "impact": round(penalty, 4),
                    "count": details["missing_count"],
                })

        metric_cfg = remediation_cfg.get("engagement_supported_metric", {})
        for metric, details in metric_report.items():
            if not details.get("supported", False):
                continue
            missing_rate = details["rates"]["missing"]
            malformed_rate = details["rates"]["malformed"]
            if details["missing_count"] > 0:
                penalty = missing_rate * float(metric_cfg.get("missing", 0.0)) * 100.0
                score += penalty
                reasons.append({
                    "area": "metric",
                    "issue": "missing",
                    "metric": metric,
                    "impact": round(penalty, 4),
                    "count": details["missing_count"],
                })
            if malformed_rate > 0:
                penalty = malformed_rate * float(metric_cfg.get("malformed", 0.0)) * 100.0
                score += penalty
                reasons.append({
                    "area": "metric",
                    "issue": "malformed",
                    "metric": metric,
                    "impact": round(penalty, 4),
                    "count": details["malformed_count"],
                })

        fallback_ratio = collection_profile.get("fallback_item_ratio", 0.0)
        if fallback_ratio > 0:
            penalty = fallback_ratio * float(remediation_cfg.get("fallback_penalty", 0.0)) * 100.0
            score += penalty
            reasons.append({
                "area": "reliability",
                "issue": "fallback_items",
                "impact": round(penalty, 4),
                "count": collection_profile.get("fallback_item_count", 0),
            })

        if collection_profile.get("cache_used", False):
            penalty = float(remediation_cfg.get("cache_penalty", 0.0)) * 100.0
            score += penalty
            reasons.append({
                "area": "reliability",
                "issue": "cache_used",
                "impact": round(penalty, 4),
                "count": collection_profile.get("cache_item_count", 0),
            })

        if source_supported_metrics:
            score = max(score, 0.0)
            score = min(score, 100.0)
            reasons.append({
                "area": "coverage",
                "issue": "supported_metric_support",
                "impact": round(_supported_metric_gap_penalty(metric_report, source_supported_metrics), 4),
                "count": sum(1 for _m in source_supported_metrics if _m in metric_report and metric_report[_m]["status"] != STATUS_PRESENT),
            })

    severity = "none"
    thresholds = {
        "critical": float(remediation_cfg.get("critical", 72.0)),
        "high": float(remediation_cfg.get("high", 44.0)),
        "medium": float(remediation_cfg.get("medium", 18.0)),
        "low": float(remediation_cfg.get("low", 4.0)),
    }
    if score >= thresholds["critical"]:
        severity = "critical"
    elif score >= thresholds["high"]:
        severity = "high"
    elif score >= thresholds["medium"]:
        severity = "medium"
    elif score >= thresholds["low"]:
        severity = "low"

    return {
        "source_id": source_id,
        "score": round(min(score, 100.0), 4),
        "severity": severity,
        "reasons": sorted(reasons, key=lambda entry: entry.get("impact", 0.0), reverse=True),
    }


def _supported_metric_gap_penalty(
    metric_report: Dict[str, Dict[str, Any]],
    supported_metrics: Sequence[str],
) -> float:
    if not supported_metrics:
        return 0.0
    penalties = []
    for metric in supported_metrics:
        details = metric_report.get(metric)
        if not details:
            continue
        if details.get("status") == STATUS_PRESENT:
            continue
        missing_rate = details.get("rates", {}).get("missing", 0.0)
        malformed_rate = details.get("rates", {}).get("malformed", 0.0)
        penalties.append(missing_rate + malformed_rate)

    if not penalties:
        return 0.0
    return round(sum(penalties) / len(supported_metrics), 4) * 100.0


def _analyze_one_source(
    source_id: str,
    items: Sequence[Any],
    source_result: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    source_id = _normalize_source_id(source_id)
    payload_items = list(items or [])
    total_items = len(payload_items)
    malformed_items = 0

    tracked_fields = list(config.get("tracked_fields") or [])
    tracked_metrics = list(config.get("tracked_engagement_metrics") or [])
    field_aliases = config.get("field_aliases") or {}
    metric_aliases = config.get("metric_aliases") or {}

    required_summary: Dict[str, Dict[str, int]] = {
        field: {"present": 0, "missing": 0, "malformed": 0}
        for field in tracked_fields
    }

    metric_values: Dict[str, List[Any]] = {
        metric: [] for metric in tracked_metrics
    }
    source_supported_metrics = set(config.get("source_supported_engagement_metrics", {}).get(source_id, []))
    fallback_item_count = 0

    for item in payload_items:
        if not isinstance(item, dict):
            malformed_items += 1
            continue

        is_fallback = bool(item.get("is_fallback"))
        if is_fallback:
            fallback_item_count += 1

        for field in tracked_fields:
            aliases = field_aliases.get(field) or [field]
            _, missing, malformed, status = _evaluate_required_field(item, field, aliases, 0, 0, 0)
            if status == STATUS_PRESENT:
                required_summary[field]["present"] += 1
            elif status == STATUS_MALFORMED:
                required_summary[field]["malformed"] += 1
            else:
                required_summary[field]["missing"] += 1

        for metric in tracked_metrics:
            aliases = metric_aliases.get(metric) or [metric]
            raw, observed = _extract_metric(item, metric, aliases)
            metric_values[metric].append(raw if observed else None)

    field_report = {
        field: _build_field_block(required_summary[field], total_items)
        for field in tracked_fields
    }

    metric_report = {}
    for metric in tracked_metrics:
        metric_report[metric] = _build_metric_block(
            metric,
            metric in source_supported_metrics,
            source_result,
            {
                "present": 0,
                "missing": 0,
                "malformed": 0,
            },
            total_items,
            metric_aliases,
            metric_values.get(metric, []),
        )

    for metric, details in metric_report.items():
        if not details.get("supported", False):
            continue
        # recompute counts for supported metrics with explicit present/missing/malformed values
        # since _build_metric_block already filled these, keep as-is but derive summary ratios below.
        pass

    usage = source_result.get("used_cache") is True
    fallback_source = bool(
        source_result.get("fallback_reason")
        or source_result.get("failed_reason")
        or source_result.get("final_error_type")
        or (
            isinstance(source_result.get("service_diagnostic"), dict)
            and source_result.get("service_diagnostic", {}).get("status") == "fallback_used"
        )
    )

    cache_item_count = total_items if usage else 0
    fallback_item_ratio = _rate(fallback_item_count, total_items)
    cache_item_ratio = _rate(cache_item_count, total_items)

    collection_evidence = {
        "attempted": bool(source_result.get("attempted", False)),
        "success": bool(source_result.get("success", False)),
        "skipped": bool(source_result.get("skipped", False)),
        "skip_reason": source_result.get("skip_reason"),
        "count_reported_by_source_result": source_result.get("count"),
        "lane_id": source_result.get("lane_id"),
        "collection_method": source_result.get("collection_method"),
        "used_cache": usage,
        "fallback_reason": source_result.get("fallback_reason"),
        "final_error_type": source_result.get("final_error_type"),
        "service_diagnostic": source_result.get("service_diagnostic"),
        "fallback_source": fallback_source,
        "retry_count": source_result.get("retry_count"),
        "item_state_distribution": {
            "malformed_item_count": malformed_items,
            "fallback_item_count": fallback_item_count,
            "cache_item_count": cache_item_count,
            "live_item_count": max(total_items - fallback_item_count, 0),
        },
        "fallback_item_ratio": fallback_item_ratio,
        "cache_item_ratio": cache_item_ratio,
    }

    metric_supported_count = len([metric for metric in tracked_metrics if metric in source_supported_metrics])
    metric_present_rate = 0.0
    if metric_supported_count > 0 and total_items > 0:
        metric_rates = [
            metric_report[metric]["rate"]
            for metric in tracked_metrics
            if metric in source_supported_metrics
        ]
        metric_present_rate = round(sum(metric_rates) / metric_supported_count, 4)

    source_state = "ok"
    if total_items == 0:
        source_state = "no_data"
    elif malformed_items > 0 or fallback_source or fallback_item_count > 0 or any(
        details["status"] in (STATUS_MISSING, STATUS_MALFORMED) for details in field_report.values()
    ):
        source_state = "degraded"

    supported_metric_list = sorted(source_supported_metrics)
    unsupported_metric_list = sorted([m for m in tracked_metrics if m not in source_supported_metrics])

    remediation = _remediation_priority(
        source_id,
        total_items,
        field_report,
        metric_report,
        collection_evidence,
        remediation_cfg=config.get("remediation_scoring", {}),
        source_supported_metrics=supported_metric_list,
    )

    return {
        "source_id": source_id,
        "state": source_state,
        "item_count": total_items,
        "malformed_item_count": malformed_items,
        "valid_item_count": max(total_items - malformed_items, 0),
        "fields": field_report,
        "engagement_metrics": {
            metric: {
                key: value
                for key, value in details.items()
                if key != "rates"
            }
            for metric, details in metric_report.items()
        },
        "engagement_metrics_detailed": metric_report,
        "engagement_support": {
            "supported_metric_count": metric_supported_count,
            "unsupported_metric_count": len(unsupported_metric_list),
            "supported_metrics": supported_metric_list,
            "unsupported_metrics": unsupported_metric_list,
            "supported_metric_presence_rate": metric_present_rate,
        },
        "collection": collection_evidence,
        "remediation": remediation,
    }


def analyze_daily_shallow_collection(
    payload_or_path: Any,
    config_path: str = DEFAULT_CONFIG_PATH,
    payload_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Run deterministic field-completeness analysis on a completed payload."""
    output = _empty_output()

    payload = payload_or_path
    if isinstance(payload_or_path, str):
        payload_path = payload_or_path
        payload = _load_json(payload_or_path)

    if not isinstance(payload, dict):
        output["errors"].append("payload_is_not_a_dict")
        output["payload_path"] = payload_path
        return output

    schema_version = payload.get("schema_version")
    payload_date = payload.get("date")
    if schema_version != DAILY_SCHEMA_VERSION:
        output["errors"].append(f"unexpected_schema_version:{schema_version}")

    config_raw = _load_json(config_path)
    config = _coerce_config(config_raw)

    source_results = payload.get("source_results")
    if not isinstance(source_results, list):
        source_results = []

    source_result_map = {}
    for entry in source_results:
        if isinstance(entry, dict) and isinstance(entry.get("source_id"), str):
            source_result_map[_normalize_source_id(entry.get("source_id"))] = entry

    items = payload.get("items", [])
    if not isinstance(items, list):
        items = []
        output["errors"].append("items_is_not_list_or_missing")

    output.update(
        {
            "status": "completed",
            "payload_schema_version": schema_version,
            "date": payload_date,
            "today": _coerce_today(payload_date or date.today()),
            "source_count": 0,
            "item_count": len(items),
            "malformed_item_count": 0,
            "source_reports": {},
            "payload_path": payload_path,
            "config_path": config_path,
            "remediation_queue": [],
            "errors": output["errors"],
            "tracked_fields": config.get("tracked_fields", []),
            "tracked_engagement_metrics": config.get("tracked_engagement_metrics", []),
        }
    )

    source_buckets: Dict[str, List[Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            output["malformed_item_count"] += 1
            continue
        source_id = _normalize_source_id(item.get("source_id"))
        if not source_id:
            source_id = "__missing_source_id__"
        source_buckets.setdefault(source_id, []).append(item)

    source_ids = set(source_buckets.keys()) | set(source_result_map.keys())
    output["source_count"] = len(source_ids)

    source_reports: Dict[str, Any] = {}
    remediation_entries = []

    for source_id in sorted(source_ids):
        report = _analyze_one_source(
            source_id=source_id,
            items=source_buckets.get(source_id, []),
            source_result=source_result_map.get(source_id, {}),
            config=config,
        )
        source_reports[source_id] = report
        remediation_entries.append(report["remediation"])

    output["source_reports"] = source_reports
    output["remediation_queue"] = sorted(
        remediation_entries,
        key=lambda entry: (
            entry.get("severity") != "none",
            entry.get("score", 0.0),
            entry.get("source_id"),
        ),
        reverse=True,
    )

    return output


def run_source_field_completeness_audit(
    payload_path: str,
    config_path: str = DEFAULT_CONFIG_PATH,
) -> Dict[str, Any]:
    return analyze_daily_shallow_collection(payload_path, config_path=config_path)


def load_and_analyze_payload(
    payload_path: str,
    config_path: str = DEFAULT_CONFIG_PATH,
) -> Dict[str, Any]:
    return analyze_daily_shallow_collection(payload_path, config_path=config_path)
