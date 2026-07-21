"""Provider-neutral, offline style matching for Account C.

The matcher compares only explicit style attributes supplied by the caller.  It
does not collect products, infer prices, inspect images, or claim product or
celebrity equivalence.  Missing/unknown values are ignored rather than scored
as mismatches, and candidates need enough comparable evidence to be selected.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple


STYLE_ATTRIBUTES: Tuple[str, ...] = (
    "item_type",
    "silhouette",
    "color",
    "material",
    "pattern",
    "detail",
    "use_context",
)

PRICE_TIERS: Tuple[str, ...] = (
    "luxury_reference",
    "mid_range",
    "accessible",
)

SAFE_RELATION_LABELS: Tuple[str, ...] = (
    "similar_mood",
    "similar_silhouette",
)

DEFAULT_THRESHOLD = 0.67
DEFAULT_MIN_COMPARED_ATTRIBUTES = 3

_UNKNOWN_VALUES = {
    "",
    "unknown",
    "unspecified",
    "not specified",
    "n/a",
    "na",
    "none",
    "null",
    "미상",
    "알 수 없음",
    "정보 없음",
    "미확인",
}

_CLAIM_FIELDS = (
    "relation_label",
    "relation_claim",
    "claim",
    "equivalence_claim",
)

_FORBIDDEN_CLAIM_PATTERN = re.compile(
    r"(?:\bidentical\b|\bdupe\b|\bexact(?:\s+match)?\b|"
    r"\bcelebrity[\s_-]*worn\b|동일\s*(?:제품|상품)?|듀프|"
    r"완전\s*같(?:은|다)|셀럽\s*착용)",
    re.IGNORECASE,
)


def _closed(reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "schema_version": "account_c_style_matcher_v1",
        "status": "closed",
        "fallback_used": True,
        "reason_code": reason_code,
        "reason": reason,
        "matches": [],
        "matches_by_tier": {tier: [] for tier in PRICE_TIERS},
        "manual_review": [],
        "excluded": [],
        "selected_count": 0,
    }


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    normalized = re.sub(r"[_\-/]+", " ", normalized)
    return " ".join(normalized.split())


def _normalized_values(value: Any) -> Set[str]:
    if isinstance(value, str):
        values: Sequence[Any] = [value]
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = list(value)
    else:
        return set()

    normalized: Set[str] = set()
    for item in values:
        if not isinstance(item, str):
            continue
        text = _normalize_text(item)
        if text and text not in _UNKNOWN_VALUES:
            normalized.add(text)
    return normalized


def _candidate_id(candidate: Mapping[str, Any], index: int) -> str:
    value = candidate.get("candidate_id", candidate.get("item_id", candidate.get("id")))
    if isinstance(value, str) and value.strip():
        return value.strip()
    return f"candidate:{index:06d}"


def _price_tier(candidate: Mapping[str, Any]) -> str:
    value = candidate.get("price_tier", candidate.get("tier"))
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    return re.sub(r"[\s\-/]+", "_", normalized)


def _has_forbidden_claim(candidate: Mapping[str, Any]) -> bool:
    for field in _CLAIM_FIELDS:
        value = candidate.get(field)
        values = value if isinstance(value, (list, tuple, set, frozenset)) else [value]
        for item in values:
            if isinstance(item, str) and _FORBIDDEN_CLAIM_PATTERN.search(item):
                return True
    return False


def _compare(
    fingerprint: Mapping[str, Any], candidate: Mapping[str, Any]
) -> Tuple[List[str], List[str], Dict[str, Dict[str, List[str]]]]:
    compared: List[str] = []
    matched: List[str] = []
    evidence: Dict[str, Dict[str, List[str]]] = {}

    for attribute in STYLE_ATTRIBUTES:
        topic_values = _normalized_values(fingerprint.get(attribute))
        candidate_values = _normalized_values(candidate.get(attribute))
        if not topic_values or not candidate_values:
            continue
        compared.append(attribute)
        overlap = sorted(topic_values & candidate_values)
        if overlap:
            matched.append(attribute)
            evidence[attribute] = {"shared_values": overlap}

    return compared, matched, evidence


def _safe_relation_label(matched_attributes: Sequence[str]) -> str:
    if "silhouette" in matched_attributes:
        return "similar_silhouette"
    return "similar_mood"


def _sort_key(match: Mapping[str, Any]) -> Tuple[int, float, int, str]:
    tier_order = {tier: index for index, tier in enumerate(PRICE_TIERS)}
    return (
        tier_order[str(match["tier"])],
        -float(match["score"]),
        -len(match["matched_attributes"]),
        str(match["candidate_id"]),
    )


def run_account_c_style_matcher(
    style_fingerprint: Any,
    candidates: Any,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    min_compared_attributes: int = DEFAULT_MIN_COMPARED_ATTRIBUTES,
) -> Dict[str, Any]:
    """Match explicit topic/style attributes to candidate item dictionaries.

    The score is the ratio of matched attributes to attributes that were
    meaningfully present on both sides.  Unknown attributes do not improve or
    reduce the score.  Output is deterministic and contains no source payload
    or unsafe equivalence claim.
    """

    try:
        if not isinstance(style_fingerprint, Mapping):
            return _closed("invalid_style_fingerprint", "style_fingerprint must be a mapping")
        if not isinstance(candidates, list):
            return _closed("invalid_candidates", "candidates must be a list")
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not 0.0 <= float(threshold) <= 1.0
        ):
            return _closed("invalid_threshold", "threshold must be numeric in [0,1]")
        if (
            isinstance(min_compared_attributes, bool)
            or not isinstance(min_compared_attributes, int)
            or not 1 <= min_compared_attributes <= len(STYLE_ATTRIBUTES)
        ):
            return _closed(
                "invalid_min_compared_attributes",
                f"min_compared_attributes must be an integer in [1,{len(STYLE_ATTRIBUTES)}]",
            )

        fingerprint = copy.deepcopy(dict(style_fingerprint))
        matches: List[Dict[str, Any]] = []
        manual_review: List[Dict[str, Any]] = []
        excluded: List[Dict[str, Any]] = []

        for index, raw_candidate in enumerate(candidates):
            if not isinstance(raw_candidate, Mapping):
                excluded.append(
                    {
                        "candidate_id": f"candidate:{index:06d}",
                        "reason_code": "malformed_candidate",
                    }
                )
                continue

            candidate = copy.deepcopy(dict(raw_candidate))
            candidate_id = _candidate_id(candidate, index)
            tier = _price_tier(candidate)
            compared, matched, evidence = _compare(fingerprint, candidate)

            if _has_forbidden_claim(candidate):
                manual_review.append(
                    {
                        "candidate_id": candidate_id,
                        "tier": tier if tier in PRICE_TIERS else None,
                        "reason_code": "forbidden_equivalence_claim_removed",
                        "safe_relation_label": _safe_relation_label(matched),
                    }
                )
                continue

            if tier not in PRICE_TIERS:
                manual_review.append(
                    {
                        "candidate_id": candidate_id,
                        "tier": None,
                        "reason_code": "missing_or_invalid_price_tier",
                        "safe_relation_label": _safe_relation_label(matched),
                    }
                )
                continue

            if len(compared) < min_compared_attributes:
                excluded.append(
                    {
                        "candidate_id": candidate_id,
                        "tier": tier,
                        "reason_code": "insufficient_compared_attributes",
                        "compared_attribute_count": len(compared),
                    }
                )
                continue

            score = round(len(matched) / len(compared), 6)
            if score < float(threshold):
                excluded.append(
                    {
                        "candidate_id": candidate_id,
                        "tier": tier,
                        "reason_code": "below_match_threshold",
                        "score": score,
                        "compared_attributes": compared,
                    }
                )
                continue

            matches.append(
                {
                    "candidate_id": candidate_id,
                    "tier": tier,
                    "score": score,
                    "relation_label": _safe_relation_label(matched),
                    "matched_attributes": matched,
                    "evidence": {
                        "compared_attributes": compared,
                        "matched_values": evidence,
                        "compared_attribute_count": len(compared),
                        "matched_attribute_count": len(matched),
                    },
                }
            )

        matches.sort(key=_sort_key)
        manual_review.sort(key=lambda item: str(item["candidate_id"]))
        excluded.sort(key=lambda item: str(item["candidate_id"]))
        matches_by_tier = {
            tier: [copy.deepcopy(match) for match in matches if match["tier"] == tier]
            for tier in PRICE_TIERS
        }

        return {
            "schema_version": "account_c_style_matcher_v1",
            "status": "matched" if matches else "no_matches",
            "fallback_used": False,
            "reason_code": "ok" if matches else "no_eligible_matches",
            "reason": "style matching completed",
            "matches": matches,
            "matches_by_tier": matches_by_tier,
            "manual_review": manual_review,
            "excluded": excluded,
            "selected_count": len(matches),
            "threshold": float(threshold),
            "min_compared_attributes": min_compared_attributes,
            "compared_attribute_contract": list(STYLE_ATTRIBUTES),
            "safe_relation_labels": list(SAFE_RELATION_LABELS),
            "provider_neutral": True,
            "production_wired": False,
        }
    except Exception as exc:
        return _closed(
            "unexpected_error",
            f"account C style matcher failed safely: {type(exc).__name__}",
        )


__all__ = [
    "DEFAULT_MIN_COMPARED_ATTRIBUTES",
    "DEFAULT_THRESHOLD",
    "PRICE_TIERS",
    "SAFE_RELATION_LABELS",
    "STYLE_ATTRIBUTES",
    "run_account_c_style_matcher",
]
