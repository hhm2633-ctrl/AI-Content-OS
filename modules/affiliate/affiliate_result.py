"""Affiliate Revenue Router Phase 1 -- output contract constants and assembly.

No routing/gating logic lives here (see `affiliate_policy_gate.py` and
`affiliate_revenue_router.py`) -- only the schema vocabulary and the pure
result-assembly/error-path functions every routing run funnels through.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "affiliate_revenue_router_phase_1.v1"

STATUS_ELIGIBLE = "eligible"
STATUS_MANUAL_REVIEW = "manual_review"
STATUS_REJECTED = "rejected"

# Most-restrictive-wins ranking: 0 is the most restrictive. Combining several
# independent gate outcomes (program / offer / pairing) always takes the
# lowest rank.
STATUS_RANK = {STATUS_REJECTED: 0, STATUS_MANUAL_REVIEW: 1, STATUS_ELIGIBLE: 2}
RANK_TO_STATUS = {rank: status for status, rank in STATUS_RANK.items()}

# Mirrors modules/card_news/evidence_input_validator.py's
# RENDER_ALLOWED_COPYRIGHT_STATUSES / modules/compliance's
# ALLOWED_RIGHTS_STATUSES -- same real-world rights vocabulary, reused as a
# value set per this project's "reuse pattern, not code" convention.
#
# NO-GO fix (rule 23): this vocabulary means "image usage is permitted" only.
# It is never read as, and must never be treated as, program-enrollment
# approval -- see `affiliate_policy_gate.py::_enrollment_evidence_complete`,
# which is the *only* gate that can move a candidate toward `eligible`.
ALLOWED_RIGHTS_STATUSES = frozenset({
    "owned",
    "licensed",
    "public_domain",
    "official_reuse_allowed",
    "user_supplied_with_permission",
})


def combine_status(*statuses: str) -> str:
    """Return the most restrictive of one or more status strings."""
    ranks = [STATUS_RANK.get(status, STATUS_RANK[STATUS_REJECTED]) for status in statuses]
    return RANK_TO_STATUS[min(ranks)] if ranks else STATUS_REJECTED


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_routing_result(
    request_id: Optional[str],
    status: str,
    eligible_candidates: List[Dict[str, Any]],
    rejected_candidates: List[Dict[str, Any]],
    manual_review_candidates: List[Dict[str, Any]],
    tracking_link_requests: List[Dict[str, Any]],
    disclosure_texts: List[Dict[str, Any]],
    manual_actions: List[Dict[str, Any]],
    blocking_reasons: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
    policy_receipts: List[Dict[str, Any]],
    disclosure_policy_verified: bool = False,
    human_approval: bool = False,
) -> Dict[str, Any]:
    eligible_ids = {candidate["candidate_id"] for candidate in eligible_candidates}
    disclosed_ids = {entry["candidate_id"] for entry in disclosure_texts}

    # NO-GO fix (rules 17/18): auto-generated disclosure boilerplate existing
    # for every eligible candidate is not, by itself, sufficient to open
    # `publish_ready` -- an explicit, separately-recorded
    # `disclosure_policy_verified` AND `human_approval` signal is required in
    # addition to every other existing condition.
    publish_ready = (
        bool(eligible_candidates)
        and not blocking_reasons
        and eligible_ids.issubset(disclosed_ids)
        and disclosure_policy_verified
        and human_approval
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "status": status,
        "eligible_candidates": eligible_candidates,
        "rejected_candidates": rejected_candidates,
        "manual_review_candidates": manual_review_candidates,
        "tracking_link_requests": tracking_link_requests,
        "disclosure_texts": disclosure_texts,
        "manual_actions": manual_actions,
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "policy_receipts": policy_receipts,
        "disclosure_policy_verified": disclosure_policy_verified,
        "human_approval": human_approval,
        "publish_ready": publish_ready,
        "network_used": False,
    }


def build_error_result(request_id: Optional[str]) -> Dict[str, Any]:
    """Fail-closed structured result for an internal router error.

    Never includes exception text, a file path, or a credential -- only a
    fixed, generic reason.
    """
    return build_routing_result(
        request_id=request_id,
        status="blocked",
        eligible_candidates=[],
        rejected_candidates=[],
        manual_review_candidates=[],
        tracking_link_requests=[],
        disclosure_texts=[],
        manual_actions=[],
        blocking_reasons=[{
            "code": "affiliate_router_internal_error",
            "message": "Affiliate routing failed internally; treated as blocked pending manual review.",
        }],
        warnings=[],
        policy_receipts=[],
    )


def build_contract_error_result(request_id: Optional[str], contract_errors: List[str]) -> Dict[str, Any]:
    """Fail-closed structured result for an invalid routing-request contract
    (a structurally invalid campaign shape, a duplicate program/offer id, or
    an input-size limit violation -- NO-GO fixes). No program/offer/pairing
    is ever evaluated in this path.
    """
    return build_routing_result(
        request_id=request_id,
        status="blocked",
        eligible_candidates=[],
        rejected_candidates=[],
        manual_review_candidates=[],
        tracking_link_requests=[],
        disclosure_texts=[],
        manual_actions=[],
        blocking_reasons=[
            {"code": "affiliate_contract_invalid", "message": error} for error in contract_errors
        ],
        warnings=[],
        policy_receipts=[],
    )
