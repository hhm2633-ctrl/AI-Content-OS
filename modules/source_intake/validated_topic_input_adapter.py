"""Validated adapter from source-intake shallow payloads to topic-engine input."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Union

from modules.source_intake.collector_readiness_registry import (
    CollectorReadinessRegistry,
    CollectorReadinessRegistryError,
)

TOPIC_INPUT_ADAPTER_VERSION = "validated_topic_input_adapter_v1"
TOPIC_INPUT_EXPECTED_SCHEMA = "daily_shallow_collection_v1"
TOPIC_INPUT_SOURCE_DIAGNOSTIC_SCHEMA = "topic_input_source_diagnostics_v1"
TOPIC_INPUT_PROVENANCE_MARKER = "validated_topic_input_adapter/v1"


def _fail_closed(reason_code: str, message: str) -> Dict[str, Any]:
    return {
        "trends": [],
        "source_diagnostics": {
            "status": "closed",
            "reason_code": reason_code,
            "reason": message,
            "adapter_version": TOPIC_INPUT_ADAPTER_VERSION,
            "schema_version": TOPIC_INPUT_SOURCE_DIAGNOSTIC_SCHEMA,
        },
    }


def _coerce_score(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def _coerce_text(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return default
    return str(value).strip()


def _is_ready_registry(registry: Any) -> bool:
    return (
        isinstance(registry, CollectorReadinessRegistry)
        and callable(getattr(registry, "require_ready", None))
        and callable(getattr(registry, "get", None))
    )


def _load_payload(payload_or_path: Union[str, Mapping[str, Any]]) -> Dict[str, Any]:
    if isinstance(payload_or_path, str):
        try:
            with open(payload_or_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except Exception as exc:
            raise CollectorReadinessRegistryError("malformed_json", str(exc))
        if not isinstance(loaded, dict):
            raise CollectorReadinessRegistryError("malformed_json", "payload is not an object")
        return loaded

    if not isinstance(payload_or_path, dict):
        raise CollectorReadinessRegistryError("malformed_json", "payload is not a dict")

    return dict(payload_or_path)


def _append_filter_diagnostic(diagnostics: Dict[str, Any], source_id: str, reason: str) -> None:
    source_diagnostics = diagnostics.setdefault("filtered_sources", {})
    source_diagnostics.setdefault(reason, [])
    source_diagnostics[reason].append({"source_id": source_id, "reason": reason})
    diagnostics["filtered_count"] += 1


def _build_trend_item(item: Mapping[str, Any], keyword: str, title: str) -> Dict[str, Any]:
    trend = dict(item)

    trend.update(
        {
            "source_id": item.get("source_id"),
            "source_name": item.get("source_name", item.get("source_id", "")),
            "source_type": item.get("source_type", ""),
            "keyword": keyword,
            "title": title,
            "link": _coerce_text(item.get("link")),
            "published_at": _coerce_text(item.get("published_at")),
            "collection_method": _coerce_text(item.get("collection_method")),
            "is_fallback": bool(item.get("is_fallback", False)),
            "source_lane_id": item.get("source_lane_id"),
            "rank_position": item.get("rank_position"),
            "summary": item.get("summary"),
            "publisher": item.get("publisher"),
            "collected_at": item.get("collected_at"),
            "board_or_category": item.get("board_or_category"),
            "category": item.get("category"),
            "visible_metrics": item.get("visible_metrics"),
            "media_flags": item.get("media_flags"),
            "metrics_origin": item.get("metrics_origin"),
            "base_score": _coerce_score(item.get("base_score")),
            "score": _coerce_score(item.get("score", item.get("base_score", 0))),
            "provenance": TOPIC_INPUT_PROVENANCE_MARKER,
        }
    )

    return trend


def run_validated_topic_input_adapter(
    daily_shallow_collection: Union[str, Mapping[str, Any]],
    registry: Any,
) -> Dict[str, Any]:
    if not _is_ready_registry(registry):
        return _fail_closed("invalid_registry", "readiness registry is missing required API")

    try:
        payload = _load_payload(daily_shallow_collection)
    except CollectorReadinessRegistryError as exc:
        return _fail_closed(exc.reason_code, exc.args[0])

    if not isinstance(payload, dict):
        return _fail_closed("malformed_payload", "payload must be a json object")

    items = payload.get("items")
    if not isinstance(items, list):
        return _fail_closed("malformed_items", "payload.items must be a list")

    trends: List[Dict[str, Any]] = []
    diagnostics = {
        "status": "ok",
        "adapter_version": TOPIC_INPUT_ADAPTER_VERSION,
        "schema_version": TOPIC_INPUT_SOURCE_DIAGNOSTIC_SCHEMA,
        "input_schema_version": payload.get("schema_version", "unknown"),
        "input_schema_expected": TOPIC_INPUT_EXPECTED_SCHEMA,
        "ready_count": 0,
        "filtered_count": 0,
        "filtered_sources": {},
    }

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return _fail_closed(
                "malformed_items",
                f"payload.items[{index}] must be an object",
            )

        source_id = item.get("source_id")
        source_key = _coerce_text(source_id, default="<missing_source_id>")

        if not isinstance(source_id, str):
            _append_filter_diagnostic(
                diagnostics,
                source_key,
                "invalid_source_id",
            )
            continue

        try:
            query = registry.get(source_id)
        except Exception as exc:  # pragma: no cover - registry defensive fallback
            return _fail_closed("invalid_registry", f"registry.get failure for {source_id}: {exc}")

        if not isinstance(query, Mapping) or not query.get("selectable"):
            reason = query.get("reason_code", "unknown_source")
            _append_filter_diagnostic(diagnostics, source_id, str(reason))
            continue

        keyword = _coerce_text(item.get("keyword"))
        title = _coerce_text(item.get("title"))
        display_keyword = keyword or title

        trend = _build_trend_item(item, display_keyword, title or keyword)
        trend["source_diagnostics"] = {
            "source_id": source_id,
            "readiness_status": query.get("readiness_status"),
            "provenance": "source_intake_ready",
        }
        trends.append(trend)
        diagnostics["ready_count"] += 1

    if diagnostics["ready_count"] == 0:
        diagnostics["status"] = "closed"
        diagnostics["reason_code"] = "no_ready_items"
        diagnostics["reason"] = "no ready valid items after readiness filtering"

    return {
        "trends": trends,
        "source_diagnostics": diagnostics,
    }


__all__ = [
    "run_validated_topic_input_adapter",
    "TOPIC_INPUT_ADAPTER_VERSION",
    "TOPIC_INPUT_EXPECTED_SCHEMA",
    "TOPIC_INPUT_SOURCE_DIAGNOSTIC_SCHEMA",
    "TOPIC_INPUT_PROVENANCE_MARKER",
]
