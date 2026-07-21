"""Apply the selective verification tier for standalone source intake.

The policy is deliberately offline and non-mutating.  It distinguishes a
human-reviewed strong fact-check from a lower-risk source-attribution fast
path.  Passing the fast path never means that the candidate's claims were
fact-checked or that risk was affirmatively cleared.
"""

from __future__ import annotations

import copy
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Iterable, Mapping, Optional
from urllib.parse import urlsplit, urlunsplit

from modules.source_intake.reviewed_evidence_validator import (
    is_verified_reviewed_evidence_bundle,
)


SELECTIVE_VERIFICATION_POLICY_VERSION = "selective_verification_policy_v1"
VERIFICATION_TIERS = frozenset({
    "strong_fact_check",
    "source_attribution_only",
    "fail_closed",
})


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _ordered_unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen = set()
    for value in values:
        normalized = _text(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _string_list(value: Any) -> Optional[list[str]]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return _ordered_unique(value)


def _first_text(candidate: Mapping[str, Any], fields: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(fields, list) or not fields or not all(isinstance(item, str) for item in fields):
        return None, None
    for field in fields:
        value = _text(candidate.get(field))
        if value:
            return field, value
    return None, None


def _canonical_https_url(value: Any) -> Optional[str]:
    raw = _text(value)
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        hostname = (parsed.hostname or "").lower().strip(".")
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    return urlunsplit(("https", hostname, parsed.path or "/", parsed.query, ""))


def _parse_timestamp(value: Any) -> Optional[datetime]:
    raw = _text(value)
    if not raw:
        return None
    try:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return parsedate_to_datetime(raw)
    except (TypeError, ValueError, OverflowError):
        return None


def _minimum_attribution(
    candidate: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    minimum = policy.get("common_minimum")
    if not isinstance(minimum, Mapping):
        return {
            "valid": False,
            "reason_code": "invalid_common_minimum_config",
            "missing": ["valid_policy_config"],
            "provenance": {},
        }

    url_field, raw_url = _first_text(candidate, minimum.get("url_fields"))
    url = _canonical_https_url(raw_url)
    identity_field, identity = _first_text(candidate, minimum.get("identity_fields"))
    timestamp_field, timestamp_raw = _first_text(candidate, minimum.get("timestamp_fields"))
    timestamp = _parse_timestamp(timestamp_raw)
    attribution_field, attribution = _first_text(candidate, minimum.get("attribution_fields"))

    missing: list[str] = []
    if url is None:
        missing.append("valid_https_source_url")
    if identity is None:
        missing.append("source_identity")
    if timestamp is None:
        missing.append("valid_source_timestamp")
    if attribution is None:
        missing.append("source_attribution")

    return {
        "valid": not missing,
        "reason_code": "minimum_attribution_valid" if not missing else "minimum_attribution_missing_or_malformed",
        "missing": missing,
        "provenance": {
            "url": {"field": url_field, "value": url},
            "identity": {"field": identity_field, "value": identity},
            "timestamp": {
                "field": timestamp_field,
                "value": timestamp_raw if timestamp is not None else None,
                "timezone_aware": bool(
                    timestamp is not None
                    and timestamp.tzinfo is not None
                    and timestamp.utcoffset() is not None
                ),
            },
            "attribution": {"field": attribution_field, "value": attribution},
        },
    }


def _closed(
    reason_code: str,
    evidence_needs: Iterable[str],
    *,
    minimum: Optional[Mapping[str, Any]] = None,
    escalated_by: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": SELECTIVE_VERIFICATION_POLICY_VERSION,
        "status": "closed",
        "verification_tier": "fail_closed",
        "eligible": False,
        "fact_checked": False,
        "reason_code": reason_code,
        "reasons": [reason_code],
        "common_minimum": copy.deepcopy(dict(minimum or {})),
        "escalated_by": _ordered_unique(escalated_by or []),
        "remaining_evidence_needs": _ordered_unique(evidence_needs),
        "resolved_evidence_needs": [],
        "provenance": {
            "policy": SELECTIVE_VERIFICATION_POLICY_VERSION,
            "claim_verification": "not_verified",
        },
    }


def evaluate_selective_verification(
    candidate: Any,
    primary_category: Any,
    config: Any,
) -> Dict[str, Any]:
    """Choose and evaluate the candidate's verification tier.

    Strong-category or configured high-risk candidates can pass only with a
    reviewed evidence bundle and explicit risk clearance.  All other configured
    categories may use the attribution-only path when the common minimum is
    valid and shallow risk detection completed without an escalated indicator.
    """

    if not isinstance(candidate, Mapping) or not isinstance(config, Mapping):
        return _closed("invalid_policy_input", ["manual_verification_policy_review"])
    policy = config.get("selective_verification")
    if not isinstance(policy, Mapping):
        return _closed("selective_verification_config_missing", ["manual_verification_policy_review"])

    strong_categories = _string_list(policy.get("strong_fact_check_categories"))
    fast_categories = _string_list(policy.get("source_attribution_only_categories"))
    high_risk_flags = _string_list(policy.get("strong_fact_check_risk_flags"))
    replaceable_needs = _string_list(policy.get("fast_path_replaced_evidence_needs"))
    hard_risks = _string_list(candidate.get("hard_risk_flags", []))
    soft_risks = _string_list(candidate.get("soft_risk_flags", []))
    evidence_needs = _string_list(candidate.get("evidence_needs", []))
    if None in (
        strong_categories,
        fast_categories,
        high_risk_flags,
        replaceable_needs,
        hard_risks,
        soft_risks,
        evidence_needs,
    ):
        return _closed("malformed_policy_or_candidate_flags", ["manual_verification_policy_review"])
    taxonomy = _string_list(config.get("taxonomy"))
    configured_soft_risks = _string_list(config.get("soft_risk_flags"))
    if (
        taxonomy is None
        or configured_soft_risks is None
        or set(strong_categories) & set(fast_categories)
        or set(strong_categories) | set(fast_categories) != set(taxonomy)
        or not set(high_risk_flags).issubset(set(configured_soft_risks))
    ):
        return _closed("invalid_verification_category_or_risk_partition", ["manual_verification_policy_review"])

    minimum = _minimum_attribution(candidate, policy)
    if hard_risks:
        return _closed(
            "hard_risk_rejection",
            list(evidence_needs) + ["hard_risk_manual_review"],
            minimum=minimum,
            escalated_by=[f"hard_risk:{flag}" for flag in hard_risks],
        )
    if not isinstance(primary_category, str) or not primary_category:
        return _closed(
            "category_required_before_verification",
            list(evidence_needs) + ["category_classification_review"],
            minimum=minimum,
        )
    if not minimum.get("valid"):
        minimum_needs = minimum.get("missing", []) if isinstance(minimum.get("missing"), list) else []
        return _closed(
            "common_minimum_failed",
            list(evidence_needs) + list(minimum_needs),
            minimum=minimum,
        )

    escalated_flags = [flag for flag in soft_risks if flag in set(high_risk_flags)]
    strong_required = primary_category in strong_categories or bool(escalated_flags)
    if strong_required:
        escalated_by = []
        if primary_category in strong_categories:
            escalated_by.append(f"category:{primary_category}")
        escalated_by.extend(f"risk:{flag}" for flag in escalated_flags)
        remaining = list(evidence_needs)
        bundle_verified = is_verified_reviewed_evidence_bundle(candidate.get("evidence_bundle"))
        risk_cleared = candidate.get("risk_detection_status") == "cleared"
        if not bundle_verified:
            remaining.append("verified_evidence_bundle_review")
        if not risk_cleared:
            remaining.append("risk_clearance_review")
        remaining = _ordered_unique(remaining)
        eligible = bundle_verified and risk_cleared and not remaining
        return {
            "schema_version": SELECTIVE_VERIFICATION_POLICY_VERSION,
            "status": "ok",
            "verification_tier": "strong_fact_check",
            "eligible": eligible,
            "fact_checked": eligible,
            "reason_code": "strong_fact_check_verified" if eligible else "strong_fact_check_required",
            "reasons": ["strong_fact_check_verified" if eligible else "strong_fact_check_required"],
            "common_minimum": minimum,
            "escalated_by": escalated_by,
            "remaining_evidence_needs": remaining,
            "resolved_evidence_needs": [],
            "provenance": {
                "policy": SELECTIVE_VERIFICATION_POLICY_VERSION,
                "claim_verification": "human_reviewed_bundle" if eligible else "not_verified",
                "reviewed_evidence_bundle_valid": bundle_verified,
                "risk_clearance_explicit": risk_cleared,
                "risk_detector_status": copy.deepcopy(candidate.get("risk_detector_status")),
                "risk_detection_status": copy.deepcopy(candidate.get("risk_detection_status")),
            },
        }

    if primary_category not in fast_categories:
        return _closed(
            "category_not_configured_for_verification",
            list(evidence_needs) + ["manual_verification_policy_review"],
            minimum=minimum,
        )

    detector_status = candidate.get("risk_detector_status")
    risk_status = candidate.get("risk_detection_status")
    risk_assessment_usable = risk_status == "cleared" or (
        detector_status == "ok" and risk_status == "undetermined" and not soft_risks
    )
    if soft_risks or not risk_assessment_usable:
        return _closed(
            "risk_assessment_not_eligible_for_fast_path",
            list(evidence_needs) + ["risk_clearance_review"],
            minimum=minimum,
            escalated_by=[f"risk:{flag}" for flag in soft_risks],
        )

    replaceable = set(replaceable_needs)
    remaining = [need for need in evidence_needs if need not in replaceable]
    resolved = [need for need in evidence_needs if need in replaceable]
    eligible = not remaining
    return {
        "schema_version": SELECTIVE_VERIFICATION_POLICY_VERSION,
        "status": "ok",
        "verification_tier": "source_attribution_only",
        "eligible": eligible,
        "fact_checked": False,
        "reason_code": "source_attribution_fast_path_allowed" if eligible else "unresolved_nonreplaceable_evidence_need",
        "reasons": [
            "valid source identity, URL, timestamp, and attribution minimum",
            "no configured escalated-risk indicator observed; this is not affirmative risk clearance",
        ],
        "common_minimum": minimum,
        "escalated_by": [],
        "remaining_evidence_needs": _ordered_unique(remaining),
        "resolved_evidence_needs": _ordered_unique(resolved),
        "provenance": {
            "policy": SELECTIVE_VERIFICATION_POLICY_VERSION,
            "claim_verification": "not_fact_checked_source_attribution_only",
            "reviewed_evidence_bundle_valid": False,
            "risk_clearance_explicit": risk_status == "cleared",
            "risk_detector_status": copy.deepcopy(detector_status),
            "risk_detection_status": copy.deepcopy(risk_status),
        },
    }


__all__ = [
    "SELECTIVE_VERIFICATION_POLICY_VERSION",
    "VERIFICATION_TIERS",
    "evaluate_selective_verification",
]
