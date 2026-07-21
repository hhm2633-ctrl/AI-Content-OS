"""Campaign Compliance Phase 1 -- output contract constants and assembly.

Builds the final, JSON-serializable compliance result dict. Contains no
checking logic itself (see `campaign_compliance_checker.py`) -- only the
schema constants and the pure assembly/error-path functions every checker run
funnels through.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "campaign_compliance_phase_1.v1"

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_MANUAL_REVIEW = "manual_review"
STATUS_NOT_APPLICABLE = "not_applicable"

# Mirrors modules/card_news/evidence_input_validator.py's
# RENDER_ALLOWED_COPYRIGHT_STATUSES taxonomy (same real-world rights vocabulary
# already established in this repository) -- reused as a value set, not
# imported, per this project's "reuse pattern across engines" convention.
ALLOWED_RIGHTS_STATUSES = frozenset({
    "owned",
    "licensed",
    "public_domain",
    "official_reuse_allowed",
    "user_supplied_with_permission",
})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_compliance_result(
    package_id: Optional[str],
    campaign_id: Optional[str],
    requirement_results: List[Dict[str, Any]],
    passed_count: int,
    failed_count: int,
    manual_review_count: int,
    blocking_reasons: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
    manual_checklist: List[Dict[str, Any]],
) -> Dict[str, Any]:
    publish_ready = not blocking_reasons and manual_review_count == 0

    return {
        "schema_version": SCHEMA_VERSION,
        "package_id": package_id,
        "campaign_id": campaign_id,
        "checked_at": _now_iso(),
        "requirement_results": requirement_results,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "manual_review_count": manual_review_count,
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "manual_checklist": manual_checklist,
        "publish_ready": publish_ready,
    }


def build_error_result(package_id: Optional[str], campaign_id: Optional[str]) -> Dict[str, Any]:
    """Fail-closed structured result for an internal checker error.

    Never includes exception text or any raw input content -- only a fixed,
    generic reason -- so a stray secret/token embedded in a link or an
    exception message can never leak through this path.
    """
    return build_compliance_result(
        package_id=package_id,
        campaign_id=campaign_id,
        requirement_results=[],
        passed_count=0,
        failed_count=0,
        manual_review_count=0,
        blocking_reasons=[{
            "code": "compliance_check_internal_error",
            "requirement_id": None,
            "requirement_type": None,
            "message": "Compliance check failed internally; treated as blocked pending manual review.",
        }],
        warnings=[],
        manual_checklist=[{
            "requirement_id": None,
            "requirement_type": None,
            "label": "Compliance checker internal error",
            "reason": "Review the campaign contract and content package manually before publishing.",
        }],
    )


def build_contract_error_result(
    package_id: Optional[str], campaign_id: Optional[str], contract_errors: List[str]
) -> Dict[str, Any]:
    """Fail-closed structured result for an invalid campaign contract.

    Returned instead of `build_error_result` when the campaign itself is
    structurally invalid (not a dict/list, missing/non-list `requirements`,
    or a duplicate `requirement_id`) -- distinct from an internal exception:
    the input needs to be fixed and resubmitted, not silently best-effort
    evaluated. No requirement or content-package check ever runs in this
    path.
    """
    return build_compliance_result(
        package_id=package_id,
        campaign_id=campaign_id,
        requirement_results=[],
        passed_count=0,
        failed_count=0,
        manual_review_count=0,
        blocking_reasons=[
            {
                "code": "campaign_contract_invalid",
                "requirement_id": None,
                "requirement_type": None,
                "message": error,
            }
            for error in contract_errors
        ],
        warnings=[],
        manual_checklist=[{
            "requirement_id": None,
            "requirement_type": None,
            "label": "Campaign contract is invalid",
            "reason": "Fix the campaign contract structure (see blocking_reasons) and resubmit before this content package can be checked.",
        }],
    )
