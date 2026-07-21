"""Contract-only collector readiness registry for source-intake truth.

This module loads a refreshed readiness truth and exposes explicit
selection checks that fail closed on invalid or missing truth.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Mapping, MutableMapping

CanonicalReadiness = Literal["ready", "partial", "blocked", "external_blocked"]


class ReadinessQuery(dict):
    """Typed, dict-compatible shape for registry query responses."""


READINESS_READY: CanonicalReadiness = "ready"
READINESS_PARTIAL: CanonicalReadiness = "partial"
READINESS_BLOCKED: CanonicalReadiness = "blocked"
READINESS_EXTERNAL_BLOCKED: CanonicalReadiness = "external_blocked"

CANONICAL_READINESS: List[CanonicalReadiness] = [
    READINESS_READY,
    READINESS_PARTIAL,
    READINESS_BLOCKED,
    READINESS_EXTERNAL_BLOCKED,
]

REASON_OK = "ok"
REASON_MISSING_FILE = "missing_file"
REASON_MALFORMED_JSON = "malformed_json"
REASON_DUPLICATE_SOURCE = "duplicate_source"
REASON_UNKNOWN_STATUS = "unknown_status"
REASON_COUNT_MISMATCH = "count_mismatch"
REASON_SOURCE_NOT_READY = "source_not_ready"
REASON_UNKNOWN_SOURCE = "unknown_source"


class CollectorReadinessRegistryError(ValueError):
    """Raised when registry loading or readiness checks fail closed."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True)
class CollectorReadinessRegistry:
    source_statuses: Mapping[str, CanonicalReadiness]
    total_sources: int
    source_count_sources: int

    def get(self, source_id: str) -> ReadinessQuery:
        if not isinstance(source_id, str) or not source_id:
            return ReadinessQuery(
                source_id=str(source_id),
                readiness_status="unknown",
                selectable=False,
                reason_code=REASON_UNKNOWN_SOURCE,
            )

        readiness = self.source_statuses.get(source_id)
        if readiness is None:
            return ReadinessQuery(
                source_id=source_id,
                readiness_status="unknown",
                selectable=False,
                reason_code=REASON_UNKNOWN_SOURCE,
            )

        reason_code = REASON_OK if readiness == READINESS_READY else REASON_SOURCE_NOT_READY
        return ReadinessQuery(
            source_id=source_id,
            readiness_status=readiness,
            selectable=readiness == READINESS_READY,
            reason_code=reason_code,
        )

    def require_ready(self, source_id: str) -> ReadinessQuery:
        result = self.get(source_id)
        if not result["selectable"]:
            raise CollectorReadinessRegistryError(
                result["reason_code"],
                f"source {source_id} not ready: {result['reason_code']}",
            )
        return result


def _load_json(payload_path: str) -> Dict[str, Any]:
    path = Path(payload_path)
    if not path.is_file():
        raise CollectorReadinessRegistryError(
            REASON_MISSING_FILE,
            f"missing file: {payload_path}",
        )

    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise CollectorReadinessRegistryError(
            REASON_MALFORMED_JSON,
            f"malformed json: {payload_path}: {exc}",
        ) from exc
    except OSError as exc:
        raise CollectorReadinessRegistryError(
            REASON_MISSING_FILE,
            f"missing file: {payload_path}: {exc}",
        ) from exc

    if not isinstance(payload, dict):
        raise CollectorReadinessRegistryError(
            REASON_MALFORMED_JSON,
            f"malformed json: {payload_path}: top-level must be object",
        )
    return payload


def _extract_readiness_from_gap(payload: Mapping[str, Any]) -> Dict[str, CanonicalReadiness]:
    readiness_by_source: Dict[str, CanonicalReadiness] = {}
    source_status_by_readiness = payload.get("source_status_by_readiness", {})
    if not isinstance(source_status_by_readiness, dict):
        raise CollectorReadinessRegistryError(
            REASON_MALFORMED_JSON,
            "malformed json: collection_gap_report missing source_status_by_readiness dict",
        )

    for status_value, entries in source_status_by_readiness.items():
        if status_value not in CANONICAL_READINESS:
            raise CollectorReadinessRegistryError(
                REASON_UNKNOWN_STATUS,
                f"unknown status in source_status_by_readiness: {status_value}",
            )

        if not isinstance(entries, list):
            raise CollectorReadinessRegistryError(
                REASON_MALFORMED_JSON,
                f"malformed source list for status {status_value}",
            )

        for entry in entries:
            if not isinstance(entry, dict):
                raise CollectorReadinessRegistryError(
                    REASON_MALFORMED_JSON,
                    "malformed source entry: expected object",
                )

            source_id = entry.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                raise CollectorReadinessRegistryError(
                    REASON_MALFORMED_JSON,
                    "malformed source entry: missing source_id",
                )

            if source_id in readiness_by_source:
                raise CollectorReadinessRegistryError(
                    REASON_DUPLICATE_SOURCE,
                    f"duplicate source_id: {source_id}",
                )

            readiness_by_source[source_id] = status_value

    return readiness_by_source


def _extract_bundle_counts(payload: Mapping[str, Any]) -> MutableMapping[str, int]:
    raw = payload.get("readiness_status_counts", {})
    if not isinstance(raw, dict):
        raise CollectorReadinessRegistryError(
            REASON_MALFORMED_JSON,
            "malformed status bundle: missing readiness_status_counts",
        )

    counts: MutableMapping[str, int] = {}
    for status in CANONICAL_READINESS:
        value = raw.get(status, 0)
        if not isinstance(value, int):
            raise CollectorReadinessRegistryError(
                REASON_MALFORMED_JSON,
                f"malformed readiness_status_counts value: {status}",
            )
        counts[status] = value
    return counts


def _to_int(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value
    raise CollectorReadinessRegistryError(
        REASON_MALFORMED_JSON,
        f"malformed numeric value: {value}",
    )


def load_collector_readiness_registry(source_intake_status_bundle_path: str) -> CollectorReadinessRegistry:
    """Load registry from explicit files.

    The collection_gap_report.json is resolved relative to the directory
    containing the status bundle.
    """

    status_payload = _load_json(source_intake_status_bundle_path)
    status_counts = _extract_bundle_counts(status_payload)

    bundle_dir = os.path.dirname(os.fspath(source_intake_status_bundle_path))
    collection_gap_report_path = os.path.join(bundle_dir, "collection_gap_report.json")
    gap_payload = _load_json(collection_gap_report_path)

    source_statuses = _extract_readiness_from_gap(gap_payload)

    bundle_count = _to_int(status_payload.get("classification_source_count"))
    source_count = _to_int(gap_payload.get("source_count", 0))

    registry_count = len(source_statuses)
    if bundle_count and bundle_count != registry_count:
        raise CollectorReadinessRegistryError(
            REASON_COUNT_MISMATCH,
            f"count_mismatch classification_source_count={bundle_count} source_ids={registry_count}",
        )

    if source_count and source_count != registry_count:
        raise CollectorReadinessRegistryError(
            REASON_COUNT_MISMATCH,
            f"count_mismatch source_count={source_count} source_ids={registry_count}",
        )

    status_sum = sum(status_counts.values())
    if status_sum != registry_count:
        raise CollectorReadinessRegistryError(
            REASON_COUNT_MISMATCH,
            f"count_mismatch readiness_status_counts_sum={status_sum} source_ids={registry_count}",
        )

    return CollectorReadinessRegistry(
        source_statuses=source_statuses,
        total_sources=registry_count,
        source_count_sources=bundle_count,
    )


def run_collector_readiness_registry(source_intake_status_bundle_path: str) -> Dict[str, Any]:
    """Compatibility helper mirroring other source-intake modules."""

    registry = load_collector_readiness_registry(source_intake_status_bundle_path)
    return {
        "status": "ok",
        "source_count": registry.total_sources,
        "ready_count": sum(1 for value in registry.source_statuses.values() if value == READINESS_READY),
        "source_statuses": dict(registry.source_statuses),
    }


__all__ = [
    "CollectorReadinessRegistry",
    "CollectorReadinessRegistryError",
    "ReadinessQuery",
    "load_collector_readiness_registry",
    "run_collector_readiness_registry",
    "REASON_DUPLICATE_SOURCE",
    "REASON_MALFORMED_JSON",
    "REASON_MISSING_FILE",
    "REASON_COUNT_MISMATCH",
    "REASON_UNKNOWN_STATUS",
    "REASON_UNKNOWN_SOURCE",
    "REASON_SOURCE_NOT_READY",
]
