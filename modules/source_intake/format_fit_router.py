"""Format fit router for candidate eligibility records.

The router is intentionally strict and fail-closed:
- it only reads precomputed assessments in ``format_fit``
- it never derives fit from any metric or raw field
- malformed input never raises and always returns a structured closed result

Each candidate route record keeps score and confidence as independent values.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple


SUPPORTED_FORMATS: Tuple[str, ...] = ("card_news", "shorts_reels", "commerce")

DEFAULT_MIN_SCORE = 0.0
DEFAULT_MIN_CONFIDENCE = 0.0

REQUIRED_ASSESSMENT_FIELDS = ("score", "confidence", "eligible", "reasons", "missing_requirements")


def _build_closed_result(
    *,
    status: str,
    reason_code: str,
    reason: str,
    routes: Sequence[Mapping[str, Any]] = (),
    not_eligible_routes: Sequence[Mapping[str, Any]] = (),
    candidate_id: Any = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "fallback_used": True,
        "reason_code": reason_code,
        "reason": reason,
        "routes": [dict(route) for route in routes],
        "not_eligible_routes": [dict(route) for route in not_eligible_routes],
        "route_count": 0,
        "candidate_id": candidate_id,
    }


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    if math.isnan(float(value)) or math.isinf(float(value)):
        return False
    return True


def _number_in_range(value: Any) -> bool:
    return _is_finite_number(value) and 0.0 <= float(value) <= 1.0


def _is_string_list(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    return all(isinstance(item, str) for item in value)


def _to_float(value: Any) -> float:
    return float(value)


def _extract_reference_fields(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    reference_fields: Dict[str, Any] = {}

    for key in (
        "candidate_id",
        "cluster_id",
        "category",
        "category_id",
        "source_id",
        "source_lane_id",
        "source_type",
        "source_name",
        "board_or_category",
        "source_attribution",
        "source_refs",
        "risk_status",
        "evidence_status",
    ):
        if key in candidate:
            reference_fields[key] = copy.deepcopy(candidate[key])

    return reference_fields


def _build_route(
    *,
    base: Mapping[str, Any],
    candidate_format: str,
    score: float,
    confidence: float,
    eligible: bool,
    reasons: Sequence[str],
    missing_requirements: Sequence[str],
) -> Dict[str, Any]:
    route: Dict[str, Any] = {
        "format": candidate_format,
        "score": score,
        "confidence": confidence,
        "eligible": eligible,
        "reasons": list(reasons),
        "missing_requirements": list(missing_requirements),
    }
    route.update(copy.deepcopy(base))
    return route


def _validate_assessment(format_name: str, assessment: Any) -> Tuple[bool, Dict[str, Any], str]:
    if not isinstance(assessment, Mapping):
        return False, {}, f"format_fit.{format_name} must be an object"

    for field in REQUIRED_ASSESSMENT_FIELDS:
        if field not in assessment:
            return False, {}, f"format_fit.{format_name} missing required field: {field}"

    score = assessment.get("score")
    confidence = assessment.get("confidence")
    eligible = assessment.get("eligible")
    reasons = assessment.get("reasons")
    missing_requirements = assessment.get("missing_requirements")

    if not _number_in_range(score):
        return False, {}, f"format_fit.{format_name}.score must be a number in [0,1]"
    if not _number_in_range(confidence):
        return False, {}, f"format_fit.{format_name}.confidence must be a number in [0,1]"
    if not isinstance(eligible, bool):
        return False, {}, f"format_fit.{format_name}.eligible must be boolean"
    if not _is_string_list(reasons):
        return False, {}, f"format_fit.{format_name}.reasons must be a list of strings"
    if not _is_string_list(missing_requirements):
        return False, {}, f"format_fit.{format_name}.missing_requirements must be a list of strings"

    normalized = {
        "score": _to_float(score),
        "confidence": _to_float(confidence),
        "eligible": eligible,
        "reasons": list(reasons),
        "missing_requirements": list(missing_requirements),
    }
    return True, normalized, ""


def run_format_fit_router(
    candidate: Any,
    *,
    min_score: float = DEFAULT_MIN_SCORE,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> Dict[str, Any]:
    """Build routed format candidates from precomputed ``candidate['format_fit']``.

    A fail-closed result is returned for malformed inputs or malformed format
    assessments. No metric derivation or invention occurs in this stage.
    """

    if not isinstance(candidate, Mapping):
        return _build_closed_result(
            status="closed",
            reason_code="invalid_candidate_type",
            reason="candidate must be a mapping",
        )

    try:
        format_fit = candidate.get("format_fit")
        if not isinstance(format_fit, Mapping):
            return _build_closed_result(
                status="closed",
                reason_code="missing_or_invalid_format_fit",
                reason="candidate.format_fit is required and must be a mapping",
                candidate_id=candidate.get("candidate_id"),
            )

        if not _number_in_range(min_score):
            return _build_closed_result(
                status="closed",
                reason_code="invalid_min_score",
                reason="min_score must be a finite number in [0,1]",
                candidate_id=candidate.get("candidate_id"),
            )

        if not _number_in_range(min_confidence):
            return _build_closed_result(
                status="closed",
                reason_code="invalid_min_confidence",
                reason="min_confidence must be a finite number in [0,1]",
                candidate_id=candidate.get("candidate_id"),
            )

        base_reference = _extract_reference_fields(candidate)
        candidate_id = candidate.get("candidate_id")
        routed: List[Dict[str, Any]] = []
        not_eligible: List[Dict[str, Any]] = []

        for candidate_format in SUPPORTED_FORMATS:
            if candidate_format not in format_fit:
                continue

            assessment = format_fit[candidate_format]
            is_valid, normalized, validation_error = _validate_assessment(candidate_format, assessment)
            if not is_valid:
                return _build_closed_result(
                    status="closed",
                    reason_code="malformed_format_assessment",
                    reason=f"validation failure: {validation_error}",
                    candidate_id=candidate_id,
                )

            score = normalized["score"]
            confidence = normalized["confidence"]
            eligible = normalized["eligible"]

            route = _build_route(
                base=base_reference,
                candidate_format=candidate_format,
                score=score,
                confidence=confidence,
                eligible=eligible,
                reasons=normalized["reasons"],
                missing_requirements=normalized["missing_requirements"],
            )

            if not eligible:
                route["reason_code"] = "ineligible_assessment"
                not_eligible.append(route)
                continue

            if score < _to_float(min_score) or confidence < _to_float(min_confidence):
                route["reason_code"] = "below_threshold"
                not_eligible.append(route)
                continue

            routed.append(route)

        if not routed:
            return {
                "status": "closed",
                "fallback_used": True,
                "reason_code": "no_eligible_routes",
                "reason": "No format assessments met eligible + threshold criteria.",
                "routes": [],
                "not_eligible_routes": not_eligible,
                "route_count": 0,
                "candidate_id": candidate_id,
            }

        return {
            "status": "routed",
            "fallback_used": False,
            "reason_code": "ok",
            "reason": "routing completed",
            "routes": routed,
            "not_eligible_routes": not_eligible,
            "route_count": len(routed),
            "candidate_id": candidate_id,
            "supported_formats": list(SUPPORTED_FORMATS),
        }
    except Exception as exc:
        return _build_closed_result(
            status="closed",
            reason_code="unexpected_error",
            reason=f"format fit router failed safely: {type(exc).__name__}",
            candidate_id=(candidate.get("candidate_id") if isinstance(candidate, Mapping) else None),
        )


__all__ = [
    "SUPPORTED_FORMATS",
    "run_format_fit_router",
    "DEFAULT_MIN_SCORE",
    "DEFAULT_MIN_CONFIDENCE",
]
