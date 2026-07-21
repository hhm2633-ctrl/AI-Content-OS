"""Aggregate dated human Stage-2 reviews into advisory calibration evidence.

This module never changes active configuration.  It reports deterministic
precision/recall and evidence-gap observations from an explicit 28-day review
window, and withholds recommendations until both the minimum elapsed window and
sample requirements are met.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


STAGE2_REVIEW_CALIBRATION_SCHEMA_VERSION = "stage2_review_calibration_v1"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "source_intake_category_stage2.json"

MINIMUM_WINDOW_DAYS = 14
TARGET_WINDOW_DAYS = 28
MINIMUM_TOTAL_OBSERVATIONS = 28
TARGET_TOTAL_OBSERVATIONS = 70
MINIMUM_CATEGORY_OBSERVATIONS = 5
MAX_THRESHOLD_DELTA = 0.05
QUALITY_GUARDRAIL = 0.70
EVIDENCE_GAP_GUARDRAIL = 0.50

DECISIONS = {"GO", "NEEDS_EVIDENCE", "WATCH", "REJECT"}


def _closed(reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "schema_version": STAGE2_REVIEW_CALIBRATION_SCHEMA_VERSION,
        "status": "closed",
        "reason_code": reason_code,
        "reason": reason,
        "calibration_ready": False,
        "recommendation_status": "not_authorized",
        "active_config_changed": False,
        "policy": _policy(),
        "window": None,
        "summary": {},
        "categories": {},
        "recommendations": [],
    }


def _policy() -> Dict[str, Any]:
    return {
        "minimum_window_days": MINIMUM_WINDOW_DAYS,
        "target_window_days": TARGET_WINDOW_DAYS,
        "minimum_total_observations": MINIMUM_TOTAL_OBSERVATIONS,
        "target_total_observations": TARGET_TOTAL_OBSERVATIONS,
        "minimum_category_observations": MINIMUM_CATEGORY_OBSERVATIONS,
        "maximum_advisory_threshold_delta": MAX_THRESHOLD_DELTA,
        "active_config_mutation_allowed": False,
        "human_reviews_required": True,
    }


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _load_config(config_path: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with Path(config_path).open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, TypeError, ValueError) as exc:
        return None, f"config_load_failed:{type(exc).__name__}"
    taxonomy = config.get("taxonomy") if isinstance(config, Mapping) else None
    if (
        not isinstance(taxonomy, list)
        or len(taxonomy) != 7
        or len(set(taxonomy)) != 7
        or not all(isinstance(item, str) and item.strip() for item in taxonomy)
    ):
        return None, "config_taxonomy_invalid"
    return dict(config), None


def _parse_reviewed_at(value: Any) -> Optional[datetime]:
    raw = _text(value)
    if not raw:
        return None
    try:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _validate_observation(
    observation: Any,
    index: int,
    taxonomy: Sequence[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not isinstance(observation, Mapping):
        return None, f"observations[{index}] must be an object"

    candidate_id = _text(observation.get("candidate_id"))
    reviewer_id = _text(observation.get("reviewer_id"))
    reviewer_type = _text(observation.get("reviewer_type")).lower()
    category_id = observation.get("category_id")
    decision = observation.get("decision")
    label = observation.get("reviewer_label")
    reviewed_at = _parse_reviewed_at(observation.get("reviewed_at"))

    if not candidate_id:
        return None, f"observations[{index}].candidate_id is required"
    if not reviewer_id:
        return None, f"observations[{index}].reviewer_id is required"
    if reviewer_type != "human":
        return None, f"observations[{index}].reviewer_type must be human"
    if category_id is not None and category_id not in taxonomy:
        return None, f"observations[{index}].category_id is invalid"
    if decision not in DECISIONS:
        return None, f"observations[{index}].decision is invalid"
    if reviewed_at is None:
        return None, f"observations[{index}].reviewed_at must be timezone-aware ISO or RFC2822"
    if not isinstance(label, Mapping):
        return None, f"observations[{index}].reviewer_label must be an object"

    reviewed_category = label.get("category_id")
    reviewed_decision = label.get("decision")
    evidence_gaps = label.get("evidence_gaps", [])
    if reviewed_category is not None and reviewed_category not in taxonomy:
        return None, f"observations[{index}].reviewer_label.category_id is invalid"
    if reviewed_decision not in DECISIONS:
        return None, f"observations[{index}].reviewer_label.decision is invalid"
    if not _string_list(evidence_gaps) and evidence_gaps != []:
        return None, f"observations[{index}].reviewer_label.evidence_gaps must be a string list"
    if reviewed_decision == "NEEDS_EVIDENCE" and not evidence_gaps:
        return None, f"observations[{index}] NEEDS_EVIDENCE review must name evidence_gaps"
    if reviewed_decision != "NEEDS_EVIDENCE" and evidence_gaps:
        return None, f"observations[{index}] evidence_gaps require NEEDS_EVIDENCE review decision"

    return {
        "candidate_id": candidate_id,
        "reviewer_id": reviewer_id,
        "reviewer_type": reviewer_type,
        "category_id": category_id,
        "decision": decision,
        "reviewed_category": reviewed_category,
        "reviewed_decision": reviewed_decision,
        "evidence_gaps": sorted(set(item.strip() for item in evidence_gaps)),
        "reviewed_at": reviewed_at,
    }, None


def _ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def _category_metrics(category_id: str, observations: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    predicted = [item for item in observations if item["category_id"] == category_id]
    reviewer_positive = [item for item in observations if item["reviewed_category"] == category_id]
    true_positive = sum(
        1 for item in observations
        if item["category_id"] == category_id and item["reviewed_category"] == category_id
    )
    false_positive = sum(
        1 for item in observations
        if item["category_id"] == category_id and item["reviewed_category"] != category_id
    )
    false_negative = sum(
        1 for item in observations
        if item["reviewed_category"] == category_id and item["category_id"] != category_id
    )
    assigned = [
        item for item in observations
        if item["category_id"] == category_id or item["reviewed_category"] == category_id
    ]
    gap_assigned = [
        item for item in observations
        if (item["reviewed_category"] or item["category_id"]) == category_id
    ]
    gap_counts: Counter = Counter()
    for item in gap_assigned:
        gap_counts.update(item["evidence_gaps"])
    reviewed_decisions = Counter(item["reviewed_decision"] for item in assigned)
    predicted_decisions = Counter(item["decision"] for item in assigned)
    decision_agreement = sum(1 for item in assigned if item["decision"] == item["reviewed_decision"])
    with_gap = sum(1 for item in gap_assigned if item["evidence_gaps"])
    reviewed_count = len(assigned)
    return {
        "reviewed_observation_count": reviewed_count,
        "predicted_count": len(predicted),
        "reviewer_positive_count": len(reviewer_positive),
        "true_positive_count": true_positive,
        "false_positive_count": false_positive,
        "false_negative_count": false_negative,
        "precision": _ratio(true_positive, len(predicted)),
        "recall": _ratio(true_positive, len(reviewer_positive)),
        "false_positive_rate": _ratio(false_positive, len(predicted)),
        "false_negative_rate": _ratio(false_negative, len(reviewer_positive)),
        "decision_agreement_rate": _ratio(decision_agreement, reviewed_count),
        "predicted_decision_distribution": {
            decision: predicted_decisions.get(decision, 0) for decision in sorted(DECISIONS)
        },
        "reviewer_decision_distribution": {
            decision: reviewed_decisions.get(decision, 0) for decision in sorted(DECISIONS)
        },
        "evidence_gap_observation_rate": _ratio(with_gap, len(gap_assigned)),
        "evidence_gap_distribution": dict(sorted(gap_counts.items())),
        "sample_sufficient_for_advisory": reviewed_count >= MINIMUM_CATEGORY_OBSERVATIONS,
    }


def _recommendations(categories: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    recommendations: List[Dict[str, Any]] = []
    for category_id, metrics in categories.items():
        if not metrics["sample_sufficient_for_advisory"]:
            continue
        precision = metrics["precision"] if metrics["predicted_count"] >= MINIMUM_CATEGORY_OBSERVATIONS else None
        recall = metrics["recall"] if metrics["reviewer_positive_count"] >= MINIMUM_CATEGORY_OBSERVATIONS else None
        gap_rate = metrics["evidence_gap_observation_rate"]
        if precision is not None and recall is not None and precision < QUALITY_GUARDRAIL and recall < QUALITY_GUARDRAIL:
            action = "review_category_features_before_threshold_change"
            threshold = None
            direction = None
        elif precision is not None and precision < QUALITY_GUARDRAIL:
            action = "review_category_precision_features_and_weights"
            threshold = None
            direction = "more_selective"
        elif recall is not None and recall < QUALITY_GUARDRAIL:
            action = "review_category_recall_features_and_weights"
            threshold = None
            direction = "less_selective"
        else:
            action = None
            threshold = None
            direction = None
        if action:
            recommendations.append({
                "category_id": category_id,
                "action": action,
                "threshold_path": threshold,
                "direction": direction,
                "maximum_delta": None,
                "approval_status": "advisory_unapproved",
                "config_change_applied": False,
            })
        if gap_rate is not None and gap_rate >= EVIDENCE_GAP_GUARDRAIL:
            recommendations.append({
                "category_id": category_id,
                "action": "review_evidence_inputs_before_threshold_change",
                "threshold_path": None,
                "direction": None,
                "maximum_delta": None,
                "approval_status": "advisory_unapproved",
                "config_change_applied": False,
            })
    return recommendations


def calibrate_stage2_reviews(
    observations: Any,
    config_path: Any = DEFAULT_CONFIG_PATH,
) -> Dict[str, Any]:
    """Validate and aggregate explicit human review observations.

    Input is not mutated.  The latest supplied ``reviewed_at`` timestamp is the
    deterministic anchor for a trailing 28-calendar-day window.  No threshold
    recommendation is emitted before a 14-calendar-day elapsed span and 28 valid
    in-window reviews are both available.
    """

    if not isinstance(observations, list):
        return _closed("invalid_observations", "observations must be a list")
    config, config_error = _load_config(config_path)
    if config_error or config is None:
        return _closed("invalid_config", config_error or "config unavailable")
    taxonomy = list(config["taxonomy"])

    validated: List[Dict[str, Any]] = []
    for index, observation in enumerate(observations):
        parsed, error = _validate_observation(observation, index, taxonomy)
        if error or parsed is None:
            return _closed("invalid_review_observation", error or "review observation invalid")
        validated.append(parsed)

    candidate_ids = {item["candidate_id"] for item in validated}
    reviewer_ids = {item["reviewer_id"] for item in validated}
    if len(candidate_ids) != len(validated):
        result = _closed(
            "duplicate_review_observation",
            "repeated candidate_id found; reviewer consensus is not implemented",
        )
        result["summary"] = {
            "supplied_observation_count": len(observations),
            "validated_observation_count": len(validated),
            "distinct_candidate_count": len(candidate_ids),
            "reviewer_count": len(reviewer_ids),
        }
        return result

    if not validated:
        return {
            **_closed("no_review_observations", "no human review observations supplied"),
            "status": "collecting",
            "reason_code": "collecting_no_observations",
            "recommendation_status": "not_authorized_collecting",
        }

    anchor = max(item["reviewed_at"] for item in validated)
    window_start_date = anchor.date() - timedelta(days=TARGET_WINDOW_DAYS - 1)
    in_window = [item for item in validated if item["reviewed_at"].date() >= window_start_date]
    earliest = min(item["reviewed_at"] for item in in_window)
    elapsed_days = (anchor.date() - earliest.date()).days + 1
    categories = {
        category_id: _category_metrics(category_id, in_window)
        for category_id in taxonomy
    }
    total_count = len(in_window)
    minimum_ready = elapsed_days >= MINIMUM_WINDOW_DAYS and total_count >= MINIMUM_TOTAL_OBSERVATIONS
    target_ready = elapsed_days >= TARGET_WINDOW_DAYS and total_count >= TARGET_TOTAL_OBSERVATIONS
    status = "target_ready" if target_ready else "minimum_ready" if minimum_ready else "collecting"
    recommendations = _recommendations(categories) if minimum_ready else []

    predicted_uncategorized = sum(1 for item in in_window if item["category_id"] is None)
    reviewer_uncategorized = sum(1 for item in in_window if item["reviewed_category"] is None)
    return {
        "schema_version": STAGE2_REVIEW_CALIBRATION_SCHEMA_VERSION,
        "status": status,
        "reason_code": status,
        "reason": "review observations aggregated; recommendations remain advisory and unapproved",
        "calibration_ready": minimum_ready,
        "target_window_ready": target_ready,
        "recommendation_status": "advisory_unapproved" if minimum_ready else "not_authorized_collecting",
        "active_config_changed": False,
        "config_schema_version": config.get("schema_version"),
        "source_calibration_status": config.get("calibration_status"),
        "policy": _policy(),
        "window": {
            "anchor_reviewed_at": anchor.isoformat(),
            "start_date": window_start_date.isoformat(),
            "end_date": anchor.date().isoformat(),
            "elapsed_calendar_days": elapsed_days,
            "excluded_older_observation_count": len(validated) - total_count,
        },
        "summary": {
            "supplied_observation_count": len(validated),
            "in_window_observation_count": total_count,
            "distinct_candidate_count": len({item["candidate_id"] for item in in_window}),
            "reviewer_count": len({item["reviewer_id"] for item in in_window}),
            "predicted_uncategorized_count": predicted_uncategorized,
            "reviewer_uncategorized_count": reviewer_uncategorized,
            "minimum_window_met": elapsed_days >= MINIMUM_WINDOW_DAYS,
            "minimum_sample_met": total_count >= MINIMUM_TOTAL_OBSERVATIONS,
            "target_window_met": elapsed_days >= TARGET_WINDOW_DAYS,
            "target_sample_met": total_count >= TARGET_TOTAL_OBSERVATIONS,
        },
        "categories": categories,
        "recommendations": recommendations,
    }


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "STAGE2_REVIEW_CALIBRATION_SCHEMA_VERSION",
    "calibrate_stage2_reviews",
]
