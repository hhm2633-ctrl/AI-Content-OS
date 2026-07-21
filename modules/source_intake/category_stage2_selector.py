"""Deterministic Stage-2 category selector for source-intake candidates.

The selector consumes supplied Stage-1 normalized signals and supplied shallow
category assessments.  It never reads or normalizes raw engagement metrics,
never performs collection, and never turns format or auxiliary tags into a
category.  Missing values remain missing: observed category weights are
renormalized for value scoring and coverage is represented separately in
confidence and ``missing_signals``.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from modules.source_intake.selective_verification_policy import evaluate_selective_verification


CATEGORY_STAGE2_SCHEMA_VERSION = "source_intake_category_stage2_result_v1"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "source_intake_category_stage2.json"

DECISIONS = ("GO", "NEEDS_EVIDENCE", "WATCH", "REJECT")
FORMAT_NAMES = {"card_news", "shorts", "shorts_reels", "reels", "commerce"}


def _is_score(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 1.0
    )


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _ordered_unique(values: Sequence[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _closed_result(candidate_id: Any, reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "schema_version": CATEGORY_STAGE2_SCHEMA_VERSION,
        "status": "closed",
        "reason_code": reason_code,
        "reason": reason,
        "candidate_id": candidate_id,
        "primary_category": None,
        "routing_state": "uncategorized",
        "secondary_categories": [],
        "category_fit_all": {},
        "category_value_score": None,
        "category_value_all": {},
        "attention": {"score": None, "confidence": None},
        "confidence": 0.0,
        "origin_independence": {"score": None},
        "distribution_spread": {"score": None},
        "decision": "REJECT",
        "evidence_needs": [],
        "hard_risk_flags": [],
        "soft_risk_flags": [],
        "verification_policy": {
            "status": "closed",
            "verification_tier": "fail_closed",
            "eligible": False,
            "fact_checked": False,
            "reason_code": reason_code,
        },
        "tags": {"international": False, "commerce_signal": False, "seasonality": None},
        "freshness": None,
        "reasons": [reason_code],
        "missing_signals": [],
        "calibration_status": "unknown",
    }


def _load_config(config_path: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    path = Path(config_path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, TypeError) as exc:
        return None, f"config load failed safely: {type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, "config root must be an object"
    return payload, None


def _validate_config(config: Mapping[str, Any]) -> Optional[str]:
    taxonomy = config.get("taxonomy")
    categories = config.get("categories")
    routing = config.get("routing")
    confidence = config.get("confidence")
    if not _string_list(taxonomy) or len(taxonomy) != 7 or len(set(taxonomy)) != 7:
        return "taxonomy must contain seven unique category ids"
    if not isinstance(categories, Mapping) or set(categories) != set(taxonomy):
        return "categories must exactly match taxonomy"
    if any(category in FORMAT_NAMES for category in taxonomy):
        return "formats must not appear in taxonomy"

    for category_id in taxonomy:
        profile = categories.get(category_id)
        weights = profile.get("weights") if isinstance(profile, Mapping) else None
        if not isinstance(weights, Mapping) or not weights:
            return f"{category_id}.weights must be a non-empty object"
        if any(isinstance(weight, bool) or not isinstance(weight, (int, float)) or weight <= 0 for weight in weights.values()):
            return f"{category_id}.weights must contain positive numbers"
        if not math.isclose(sum(float(weight) for weight in weights.values()), 100.0, abs_tol=1e-9):
            return f"{category_id}.weights must sum to 100"

    required_routing = {
        "primary_min_fit",
        "secondary_min_fit",
        "secondary_max_gap",
        "uncategorized_watch_min_fit",
        "go_min_fit",
        "go_min_value",
        "go_min_confidence",
        "risk_sensitive_tie_margin",
        "community_subject_preference_margin",
    }
    if not isinstance(routing, Mapping) or any(not _is_score(routing.get(key)) for key in required_routing):
        return "routing score thresholds must be numbers in [0,1]"
    if not isinstance(routing.get("secondary_max_count"), int) or routing["secondary_max_count"] < 0:
        return "secondary_max_count must be a non-negative integer"
    if not isinstance(confidence, Mapping) or any(not _is_score(value) for value in confidence.values()):
        return "confidence weights must be numbers in [0,1]"
    if not math.isclose(sum(float(value) for value in confidence.values()), 1.0, abs_tol=1e-9):
        return "confidence weights must sum to 1"
    return None


def _validate_score_map(value: Any, taxonomy: Sequence[str], name: str) -> Optional[str]:
    if not isinstance(value, Mapping):
        return f"{name} must be an object"
    for category_id in taxonomy:
        score = value.get(category_id)
        if not _is_score(score):
            return f"{name}.{category_id} must be a number in [0,1]"
    return None


def _validate_score_record(value: Any, name: str) -> Optional[str]:
    if not isinstance(value, Mapping):
        return f"{name} must be an object"
    if value.get("score") is not None and not _is_score(value.get("score")):
        return f"{name}.score must be null or a number in [0,1]"
    return None


def _validate_stage1_metric_records(stage1: Mapping[str, Any]) -> Optional[str]:
    """Accept Lane-HN normalized metric records without reading raw values.

    Stage-2 may receive preserved ``raw_value`` metadata inside a normalized
    record, but it only validates the record's normalized contract.  A direct
    numeric value under a raw metric name is rejected because it cannot prove
    that Stage-1 normalization occurred.
    """

    for metric_name in ("rank_position", "views", "comments", "likes", "dislikes"):
        if metric_name not in stage1:
            continue
        record = stage1.get(metric_name)
        if not isinstance(record, Mapping):
            return f"stage1_normalized_signals.{metric_name} must be a normalized signal record"
        normalized_value = record.get("normalized_value")
        if normalized_value is not None and not _is_score(normalized_value):
            return f"stage1_normalized_signals.{metric_name}.normalized_value must be null or a number in [0,1]"
        if "status" in record and not isinstance(record.get("status"), str):
            return f"stage1_normalized_signals.{metric_name}.status must be a string"
    return None


def _score_category(
    category_id: str,
    weights: Mapping[str, Any],
    supplied_signals: Mapping[str, Any],
) -> Dict[str, Any]:
    observed_weight = 0.0
    weighted_points = 0.0
    missing: List[str] = []
    breakdown: Dict[str, Any] = {}

    for signal_name, raw_weight in weights.items():
        weight = float(raw_weight)
        value = supplied_signals.get(signal_name)
        if value is None:
            missing.append(signal_name)
            breakdown[signal_name] = {
                "value": None,
                "weight": weight,
                "observed": False,
                "weighted_points": None,
            }
            continue
        if not _is_score(value):
            raise ValueError(f"category_signals.{category_id}.{signal_name} must be null or a number in [0,1]")
        points = float(value) * weight
        observed_weight += weight
        weighted_points += points
        breakdown[signal_name] = {
            "value": float(value),
            "weight": weight,
            "observed": True,
            "weighted_points": round(points, 6),
        }

    score = weighted_points / observed_weight if observed_weight else None
    for detail in breakdown.values():
        points = detail["weighted_points"]
        detail["normalized_contribution"] = round(points / observed_weight, 6) if points is not None and observed_weight else None

    return {
        "score": round(score, 6) if score is not None else None,
        "observed_weight": round(observed_weight, 6),
        "coverage": round(observed_weight / 100.0, 6),
        "weighted_breakdown": breakdown,
        "missing_signals": missing,
    }


def _normalize_tags(value: Any) -> Dict[str, Any]:
    result = {"international": False, "commerce_signal": False, "seasonality": None}
    if not isinstance(value, Mapping):
        return result
    if isinstance(value.get("international"), bool):
        result["international"] = value["international"]
    if isinstance(value.get("commerce_signal"), bool):
        result["commerce_signal"] = value["commerce_signal"]
    seasonality = value.get("seasonality")
    if isinstance(seasonality, (str, bool)) or seasonality is None:
        result["seasonality"] = seasonality
    return result


def _verified_official_origin(candidate: Mapping[str, Any], primary: Optional[str], config: Mapping[str, Any]) -> bool:
    """Accept the official-origin exception only for a configured verified domain."""
    if not primary or candidate.get("authoritative_official_origin") is not True:
        return False
    evidence_config = config.get("evidence", {})
    if evidence_config.get("authoritative_official_origin_exception") is not True:
        return False
    if primary not in evidence_config.get("authoritative_origin_exception_categories", []):
        return False
    verification = candidate.get("authoritative_origin_verification")
    if (
        not isinstance(verification, Mapping)
        or verification.get("verified") is not True
        or verification.get("original_document_verified") is not True
        or verification.get("claim_alignment_verified") is not True
        or verification.get("reviewer_type") != "human"
    ):
        return False
    source_url = verification.get("source_url")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        return False
    try:
        parsed_url = urlsplit(source_url)
        hostname = (parsed_url.hostname or "").lower().strip(".")
        port = parsed_url.port
    except ValueError:
        return False
    if port not in (None, 443) or parsed_url.username is not None or parsed_url.password is not None:
        return False
    allowed = [
        domain.lower().strip(".")
        for domain in evidence_config.get("authoritative_origin_domains", [])
        if isinstance(domain, str)
    ]
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in allowed)


def _risk_aware_primary(
    fit_all: Mapping[str, float],
    taxonomy: Sequence[str],
    config: Mapping[str, Any],
) -> str:
    routing = config["routing"]
    priority = config.get("risk_priority", {})
    indexed = {category_id: index for index, category_id in enumerate(taxonomy)}
    ordered = sorted(taxonomy, key=lambda category_id: (-fit_all[category_id], indexed[category_id]))
    best_fit = fit_all[ordered[0]]
    tied = [category_id for category_id in ordered if best_fit - fit_all[category_id] <= float(routing["risk_sensitive_tie_margin"])]
    selected = sorted(tied, key=lambda category_id: (-int(priority.get(category_id, 0)), indexed[category_id]))[0]

    if selected == "community_buzz":
        subject_candidates = [
            category_id
            for category_id in taxonomy
            if category_id != "community_buzz"
            and fit_all[category_id] >= float(routing["primary_min_fit"])
            and best_fit - fit_all[category_id] <= float(routing["community_subject_preference_margin"])
        ]
        if subject_candidates:
            selected = sorted(
                subject_candidates,
                key=lambda category_id: (-fit_all[category_id], -int(priority.get(category_id, 0)), indexed[category_id]),
            )[0]
    return selected


def _secondary_categories(
    primary: str,
    fit_all: Mapping[str, float],
    taxonomy: Sequence[str],
    routing: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    primary_fit = fit_all[primary]
    index = {category_id: order for order, category_id in enumerate(taxonomy)}
    eligible = [
        category_id
        for category_id in taxonomy
        if category_id != primary
        and fit_all[category_id] >= float(routing["secondary_min_fit"])
        and primary_fit - fit_all[category_id] <= float(routing["secondary_max_gap"])
    ]
    eligible.sort(key=lambda category_id: (-fit_all[category_id], index[category_id]))
    return [
        {"category_id": category_id, "fit_score": fit_all[category_id]}
        for category_id in eligible[: int(routing["secondary_max_count"])]
    ]


def run_category_stage2_selector(
    candidate: Any,
    config_path: Any = DEFAULT_CONFIG_PATH,
) -> Dict[str, Any]:
    """Return one deterministic Stage-2 category result.

    Required candidate fields are ``candidate_id``, ``category_fit_all`` (all
    seven semantic fit scores), ``category_signals`` (precomputed normalized
    category features), ``stage1_normalized_signals``,
    ``origin_independence`` and ``distribution_spread``.  Raw metrics are not
    accepted or inspected.
    """

    candidate_id = candidate.get("candidate_id") if isinstance(candidate, Mapping) else None
    if not isinstance(candidate, Mapping):
        return _closed_result(None, "invalid_candidate_type", "candidate must be an object")

    config, config_error = _load_config(config_path)
    if config_error or config is None:
        return _closed_result(candidate_id, "invalid_config", config_error or "config unavailable")
    validation_error = _validate_config(config)
    if validation_error:
        return _closed_result(candidate_id, "invalid_config", validation_error)

    taxonomy: List[str] = list(config["taxonomy"])
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        return _closed_result(candidate_id, "missing_candidate_id", "candidate_id must be a non-empty string")

    stage1 = candidate.get("stage1_normalized_signals")
    if not isinstance(stage1, Mapping):
        return _closed_result(candidate_id, "missing_stage1_signals", "stage1_normalized_signals must be an object")
    stage1_error = _validate_stage1_metric_records(stage1)
    if stage1_error:
        return _closed_result(candidate_id, "raw_metrics_prohibited", stage1_error)

    fit_all = candidate.get("category_fit_all")
    score_map_error = _validate_score_map(fit_all, taxonomy, "category_fit_all")
    if score_map_error:
        return _closed_result(candidate_id, "invalid_category_fit", score_map_error)
    normalized_fit = {category_id: float(fit_all[category_id]) for category_id in taxonomy}

    category_signals = candidate.get("category_signals")
    if not isinstance(category_signals, Mapping):
        return _closed_result(candidate_id, "invalid_category_signals", "category_signals must be an object")

    origin = candidate.get("origin_independence")
    spread = candidate.get("distribution_spread")
    origin_error = _validate_score_record(origin, "origin_independence")
    spread_error = _validate_score_record(spread, "distribution_spread")
    if origin_error:
        return _closed_result(candidate_id, "invalid_origin_independence", origin_error)
    if spread_error:
        return _closed_result(candidate_id, "invalid_distribution_spread", spread_error)

    hard_risks = candidate.get("hard_risk_flags", [])
    soft_risks = candidate.get("soft_risk_flags", [])
    evidence_needs = candidate.get("evidence_needs", [])
    if not _string_list(hard_risks) or not _string_list(soft_risks) or not _string_list(evidence_needs):
        return _closed_result(candidate_id, "invalid_gate_flags", "risk flags and evidence_needs must be lists of strings")
    hard_risks = _ordered_unique(hard_risks)
    soft_risks = _ordered_unique(soft_risks)
    evidence_needs = _ordered_unique(evidence_needs)
    risk_detection_status = candidate.get("risk_detection_status")

    category_values: Dict[str, Any] = {}
    all_missing: List[str] = []
    try:
        for category_id in taxonomy:
            signals = category_signals.get(category_id, {})
            if not isinstance(signals, Mapping):
                return _closed_result(candidate_id, "invalid_category_signals", f"category_signals.{category_id} must be an object")
            detail = _score_category(category_id, config["categories"][category_id]["weights"], signals)
            category_values[category_id] = detail
            all_missing.extend(f"{category_id}.{name}" for name in detail["missing_signals"])
    except ValueError as exc:
        return _closed_result(candidate_id, "invalid_category_signal", str(exc))

    routing = config["routing"]
    top_category = _risk_aware_primary(normalized_fit, taxonomy, config)
    max_fit = normalized_fit[top_category]
    primary: Optional[str] = top_category if max_fit >= float(routing["primary_min_fit"]) else None
    routing_state = "categorized" if primary else "uncategorized"
    secondary = _secondary_categories(primary, normalized_fit, taxonomy, routing) if primary else []

    official_origin = _verified_official_origin(candidate, primary, config)
    verification_candidate = copy.deepcopy(dict(candidate))
    verification_candidate["hard_risk_flags"] = hard_risks
    verification_candidate["soft_risk_flags"] = soft_risks
    verification_candidate["evidence_needs"] = evidence_needs
    verification_policy = evaluate_selective_verification(
        verification_candidate,
        primary,
        config,
    )
    policy_needs = verification_policy.get("remaining_evidence_needs")
    evidence_needs = _ordered_unique(policy_needs) if _string_list(policy_needs) else [
        "manual_verification_policy_review"
    ]

    selected_value = category_values[primary]["score"] if primary else None
    selected_coverage = category_values[primary]["coverage"] if primary else 0.0
    effective_origin_quality = 1.0 if official_origin else (
        float(origin["score"]) if origin.get("score") is not None else 0.0
    )
    confidence_weights = config["confidence"]
    confidence = (
        selected_coverage * float(confidence_weights["observed_weight_coverage"])
        + effective_origin_quality * float(confidence_weights["origin_evidence_quality"])
    )
    confidence = round(min(1.0, max(0.0, confidence)), 6)

    reasons: List[str] = []
    if hard_risks:
        decision = "REJECT"
        reasons.append("hard_risk_gate")
    elif primary is None:
        if max_fit >= float(routing["uncategorized_watch_min_fit"]):
            decision = "WATCH"
            reasons.append("uncategorized_fit_0_30_to_0_49")
        else:
            decision = "REJECT"
            reasons.append("category_fit_below_0_30")
    elif verification_policy.get("eligible") is not True or evidence_needs:
        decision = "NEEDS_EVIDENCE"
        reasons.append(verification_policy.get("reason_code", "resolvable_risk_or_evidence_gap"))
    elif (
        max_fit >= float(routing["go_min_fit"])
        and selected_value is not None
        and selected_value >= float(routing["go_min_value"])
        and confidence >= float(routing["go_min_confidence"])
    ):
        decision = "GO"
        reasons.append("category_value_and_confidence_passed")
    else:
        decision = "WATCH"
        reasons.append("categorized_but_below_go_threshold")

    attention_score = stage1.get("attention")
    attention_confidence = stage1.get("attention_confidence")
    if attention_score is not None and not _is_score(attention_score):
        return _closed_result(candidate_id, "invalid_stage1_attention", "stage1_normalized_signals.attention must be null or a number in [0,1]")
    if attention_confidence is not None and not _is_score(attention_confidence):
        return _closed_result(candidate_id, "invalid_stage1_attention", "stage1_normalized_signals.attention_confidence must be null or a number in [0,1]")

    missing_selected = category_values[primary]["missing_signals"] if primary else all_missing
    result = {
        "schema_version": CATEGORY_STAGE2_SCHEMA_VERSION,
        "config_schema_version": config.get("schema_version"),
        "status": "ok",
        "reason_code": "ok",
        "reason": "deterministic Stage-2 category selection completed",
        "candidate_id": candidate_id,
        "cluster_id": copy.deepcopy(candidate.get("cluster_id")),
        "primary_category": primary,
        "routing_state": routing_state,
        "secondary_categories": secondary,
        "category_fit_all": normalized_fit,
        "category_value_score": selected_value,
        "category_value_all": category_values,
        "attention": {
            "score": float(attention_score) if attention_score is not None else None,
            "confidence": float(attention_confidence) if attention_confidence is not None else None,
        },
        "confidence": confidence,
        "origin_independence": copy.deepcopy(dict(origin)),
        "distribution_spread": copy.deepcopy(dict(spread)),
        "authoritative_official_origin": official_origin,
        "decision": decision,
        "evidence_needs": evidence_needs,
        "hard_risk_flags": hard_risks,
        "soft_risk_flags": soft_risks,
        "risk_detection_status": copy.deepcopy(risk_detection_status or "undetermined"),
        "risk_detector_status": copy.deepcopy(candidate.get("risk_detector_status", "unknown")),
        "verification_policy": copy.deepcopy(verification_policy),
        "evidence_bundle": copy.deepcopy(candidate.get("evidence_bundle")),
        "tags": _normalize_tags(candidate.get("tags")),
        "freshness": copy.deepcopy(candidate.get("freshness")),
        "reasons": reasons,
        "missing_signals": list(missing_selected),
        "calibration_status": config.get("calibration_status"),
        "calibration_note": config.get("calibration_note"),
    }

    for key in (
        "source_id",
        "source_lane_id",
        "source_type",
        "source_name",
        "source_attribution",
        "source_refs",
        "title",
        "representative_title",
        "recurrence",
        "cluster_confidence",
        "source_observation_count",
        "independent_origin_count",
        "cluster_match_reasons",
        "cluster_match_provenance",
    ):
        if key in candidate:
            result[key] = copy.deepcopy(candidate[key])
    return result


__all__ = [
    "CATEGORY_STAGE2_SCHEMA_VERSION",
    "DEFAULT_CONFIG_PATH",
    "DECISIONS",
    "run_category_stage2_selector",
]
