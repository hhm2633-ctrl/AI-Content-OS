"""Fail-closed bridge from reviewed Stage-2 results to format-fit routing.

The bridge does not calculate format scores or eligibility.  It only validates
that a Stage-2 ``GO`` result has completed the explicit human, evidence, and
risk-clearance gates, then supplies the caller-provided ``format_fit`` records
to :func:`run_format_fit_router`, which remains the scoring source of truth.
Human-review metadata is caller-attested offline input, not authenticated
reviewer identity.

This module is standalone and side-effect free.  It performs no collection,
deep dive, production work, publishing, storage writes, or WorkflowEngine
integration.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Dict, Mapping

from modules.source_intake.format_fit_router import run_format_fit_router
from modules.source_intake.reviewed_evidence_validator import is_verified_reviewed_evidence_bundle


STAGE2_FORMAT_ROUTER_BRIDGE_VERSION = "stage2_format_router_bridge_v1"
_CLEARED_RISK_STATUSES = frozenset({"cleared"})
_APPROVED_REVIEW_STATUSES = frozenset({"approved"})
_REVIEW_ATTESTATION = "caller_attested_offline_not_identity_authenticated"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _closed(candidate_id: Any, reason_code: str, reason: str) -> Dict[str, Any]:
    """Return the existing router-shaped closed contract without any routes."""

    return {
        "status": "closed",
        "fallback_used": True,
        "reason_code": reason_code,
        "reason": reason,
        "routes": [],
        "not_eligible_routes": [],
        "route_count": 0,
        "candidate_id": candidate_id,
        "bridge_schema_version": STAGE2_FORMAT_ROUTER_BRIDGE_VERSION,
        "router_invoked": False,
        "review_gate_passed": False,
        "review_attestation": _REVIEW_ATTESTATION,
    }


def _string_list_is_empty(value: Any) -> bool:
    return isinstance(value, list) and not value


def _timezone_aware_timestamp(value: Any) -> bool:
    raw = _text(value)
    if not raw:
        return False
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _review_is_approved(value: Any, candidate_id: str) -> bool:
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("approved") is True
        and _text(value.get("status")).lower() in _APPROVED_REVIEW_STATUSES
        and bool(_text(value.get("reviewer_id")))
        and _text(value.get("reviewer_type")).lower() == "human"
        and _timezone_aware_timestamp(value.get("reviewed_at"))
        and _text(value.get("reviewed_candidate_id")) == candidate_id
        and value.get("reviewed_decision") == "GO"
        and _text(value.get("risk_clearance")).lower() == "cleared"
    )


def route_reviewed_stage2_candidate(
    stage2_result: Any,
    format_fit_assessment: Any,
) -> Dict[str, Any]:
    """Route one explicitly reviewed and evidence-verified Stage-2 candidate.

    Required review metadata is carried on ``stage2_result`` as
    ``human_review`` and ``evidence_bundle``.  ``format_fit_assessment`` must be
    the precomputed mapping keyed by the formats supported by the existing
    router.  The bridge never changes or supplements assessment scores.
    """

    candidate_id = stage2_result.get("candidate_id") if isinstance(stage2_result, Mapping) else None
    if not isinstance(stage2_result, Mapping):
        return _closed(None, "invalid_stage2_result", "stage2_result must be an object")
    if stage2_result.get("status") != "ok":
        return _closed(candidate_id, "stage2_not_ok", "Stage-2 status must be ok")
    if stage2_result.get("decision") != "GO":
        return _closed(candidate_id, "stage2_not_go", "Stage-2 decision must be GO")
    if not _text(candidate_id):
        return _closed(candidate_id, "missing_candidate_id", "candidate_id must be a non-empty string")
    if not _text(stage2_result.get("primary_category")):
        return _closed(candidate_id, "missing_primary_category", "primary_category must be present")

    if not _review_is_approved(stage2_result.get("human_review"), _text(candidate_id)):
        return _closed(
            candidate_id,
            "human_review_not_approved",
            "explicit approved human_review is required",
        )
    if not is_verified_reviewed_evidence_bundle(stage2_result.get("evidence_bundle")):
        return _closed(
            candidate_id,
            "evidence_not_verified_or_eligible",
            "evidence_bundle must be verified and eligible",
        )

    if not _string_list_is_empty(stage2_result.get("hard_risk_flags")):
        return _closed(candidate_id, "hard_risk_present", "hard_risk_flags must be an empty list")
    if not _string_list_is_empty(stage2_result.get("soft_risk_flags")):
        return _closed(candidate_id, "soft_risk_present", "soft_risk_flags must be an empty list")
    if not _string_list_is_empty(stage2_result.get("evidence_needs")):
        return _closed(candidate_id, "evidence_needs_present", "evidence_needs must be an empty list")

    risk_status = _text(stage2_result.get("risk_detection_status")).lower()
    if risk_status not in _CLEARED_RISK_STATUSES:
        return _closed(
            candidate_id,
            "risk_not_cleared",
            "risk_detection_status must be explicitly cleared; undetermined is not eligible",
        )
    if not isinstance(format_fit_assessment, Mapping):
        return _closed(
            candidate_id,
            "invalid_format_fit_assessment",
            "format_fit_assessment must be an object",
        )

    candidate: Dict[str, Any] = {
        "candidate_id": _text(candidate_id),
        "category_id": _text(stage2_result.get("primary_category")),
        "risk_status": risk_status,
        "evidence_status": _text(stage2_result["evidence_bundle"].get("status")).lower(),
        "format_fit": copy.deepcopy(dict(format_fit_assessment)),
    }
    for key in (
        "cluster_id",
        "source_id",
        "source_lane_id",
        "source_type",
        "source_name",
        "source_attribution",
        "source_refs",
    ):
        if key in stage2_result:
            candidate[key] = copy.deepcopy(stage2_result[key])

    routed = run_format_fit_router(candidate)
    result = copy.deepcopy(routed)
    result["bridge_schema_version"] = STAGE2_FORMAT_ROUTER_BRIDGE_VERSION
    result["router_invoked"] = True
    result["review_gate_passed"] = True
    result["review_attestation"] = _REVIEW_ATTESTATION
    return result


__all__ = [
    "STAGE2_FORMAT_ROUTER_BRIDGE_VERSION",
    "route_reviewed_stage2_candidate",
]
