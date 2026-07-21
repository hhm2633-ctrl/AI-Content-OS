"""Facade for topic-candidate preparation.

Composes:
1) collector readiness registry loading,
2) validated topic-input adapter,
3) topic-input quality gate.

This is intentionally standalone, deterministic, and fail-closed.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Union

from modules.source_intake.collector_readiness_registry import (
    CollectorReadinessRegistryError,
    load_collector_readiness_registry,
)
from modules.source_intake.topic_input_quality_gate import run_topic_input_quality_gate
from modules.source_intake.validated_topic_input_adapter import run_validated_topic_input_adapter


def _diagnostic(reason_code: str, reason: str, status: str = "closed") -> Dict[str, Any]:
    return {
        "status": status,
        "reason_code": reason_code,
        "reason": reason,
    }


def _is_path_like_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        return {"status": "closed", "reason_code": "missing_file", "reason": str(exc)}
    except json.JSONDecodeError as exc:
        return {"status": "closed", "reason_code": "malformed_json", "reason": str(exc)}
    except OSError as exc:
        return {"status": "closed", "reason_code": "missing_file", "reason": str(exc)}
    if not isinstance(payload, dict):
        return {
            "status": "closed",
            "reason_code": "malformed_json",
            "reason": "gap payload top-level must be object",
        }
    return {"status": "ok", "payload": payload}


def run_validated_topic_candidate_pipeline(
    *,
    daily_shallow_collection: Union[str, Mapping[str, Any]],
    source_intake_status_bundle_path: str,
    collection_gap_report_path: str,
) -> Dict[str, Any]:
    """Execute registry -> adapter -> quality in strict fail-closed order."""

    stage_diagnostics = {
        "registry": {},
        "adapter": {},
        "quality_gate": {},
        "inputs": {
            "source_intake_status_bundle_path": source_intake_status_bundle_path,
            "collection_gap_report_path": collection_gap_report_path,
        },
    }

    # Explicit gap-report validation. Keeps contract observability for the required path.
    gap_diagnostic = _is_path_like_json(collection_gap_report_path)
    if gap_diagnostic.get("status") == "closed":
        stage_diagnostics["registry"] = _diagnostic(
            "pipeline_short_circuit",
            "explicit gap report payload failed validation",
        )
        stage_diagnostics["adapter"] = {"status": "closed", "reason_code": "pipeline_short_circuit"}
        stage_diagnostics["quality_gate"] = {"status": "closed", "reason_code": "pipeline_short_circuit"}
        return {
            "status": "closed",
            "candidates": [],
            "stage_diagnostics": stage_diagnostics,
        }

    # Load registry (fail-closed by contract).
    try:
        registry = load_collector_readiness_registry(source_intake_status_bundle_path)
    except CollectorReadinessRegistryError as exc:
        stage_diagnostics["registry"] = {
            "status": "closed",
            "reason_code": exc.reason_code,
            "reason": str(exc),
        }
        stage_diagnostics["adapter"] = {
            "status": "closed",
            "reason_code": "pipeline_short_circuit",
            "reason": "registry stage closed",
        }
        stage_diagnostics["quality_gate"] = {
            "status": "closed",
            "reason_code": "pipeline_short_circuit",
            "reason": "registry stage closed",
        }
        return {
            "status": "closed",
            "candidates": [],
            "stage_diagnostics": stage_diagnostics,
        }

    stage_diagnostics["registry"] = {
        "status": "ok",
        "reason_code": "ok",
        "reason": "registry loaded",
        "source_count": getattr(registry, "total_sources", 0),
    }

    # Adapter pass (keeps deterministic order and produces source_diagnostics).
    adapter_output = run_validated_topic_input_adapter(
        daily_shallow_collection=daily_shallow_collection,
        registry=registry,
    )
    adapter_diagnostics = adapter_output.get("source_diagnostics", {})
    stage_diagnostics["adapter"] = dict(adapter_diagnostics)

    # Quality gate pass (dedupe + source agreement). No final selection.
    quality_output = run_topic_input_quality_gate(adapter_output)
    quality_diagnostics = quality_output.get("quality_diagnostics", {})
    stage_diagnostics["quality_gate"] = dict(quality_diagnostics)

    adapter_closed = adapter_diagnostics.get("status") == "closed"
    quality_closed = quality_diagnostics.get("status") == "closed"
    candidates = quality_output.get("candidates", []) or []

    if adapter_closed or quality_closed or len(candidates) == 0:
        if candidates is None:
            candidates = []
        return {
            "status": "closed",
            "candidates": [],
            "stage_diagnostics": stage_diagnostics,
        }

    return {
        "status": "candidate_ready",
        "candidates": candidates,
        "stage_diagnostics": stage_diagnostics,
    }


__all__ = ["run_validated_topic_candidate_pipeline"]
