"""Promote explicitly reviewed WATCH entries for account routing only.

This gate is deliberately separate from Stage-2.  It never mutates the source
WATCH result and never claims production or publishing readiness.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from modules.source_intake.reviewed_evidence_validator import (
    is_verified_reviewed_evidence_bundle,
)


REVIEWED_WATCH_PROMOTION_VERSION = "source_intake_reviewed_watch_promotion_v1"
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "source_intake_reviewed_watch_promotion.json"
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _load_config(path: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with Path(path).resolve().open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, TypeError, ValueError) as exc:
        return None, f"config_load_failed:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, "config_root_must_be_object"
    return payload, None


def _aware_timestamp(value: Any) -> bool:
    if not _text(value):
        return False
    try:
        parsed = datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _closed(reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "schema_version": REVIEWED_WATCH_PROMOTION_VERSION,
        "status": "closed",
        "fallback_used": True,
        "reason_code": reason_code,
        "reason": reason,
        "routing_candidates": [],
        "promoted_count": 0,
        "blocked": [],
        "blocked_count": 0,
        "original_stage2_decisions_mutated": False,
        "production_ready": False,
        "publishing_ready": False,
    }


def _block(entry: Mapping[str, Any], reason_code: str) -> Dict[str, Any]:
    return {
        "candidate_id": copy.deepcopy(entry.get("candidate_id")),
        "cluster_id": copy.deepcopy(entry.get("cluster_id")),
        "review_state": copy.deepcopy(entry.get("review_state")),
        "reason_code": reason_code,
    }


def _routing_candidate(entry: Mapping[str, Any]) -> Dict[str, Any]:
    scores = entry.get("score_diagnostics")
    scores = scores if isinstance(scores, Mapping) else {}
    evidence = entry.get("evidence_diagnostics")
    evidence = evidence if isinstance(evidence, Mapping) else {}
    risk = entry.get("risk_diagnostics")
    risk = risk if isinstance(risk, Mapping) else {}
    category = _text(entry.get("primary_category"))
    attention_score = scores.get("attention")
    return {
        "status": "ok",
        "decision": "GO",
        "decision_origin": "human_reviewed_watch_promotion",
        "routing_decision": "REVIEWED_GO",
        "original_stage2_status": "ok",
        "original_stage2_decision": "WATCH",
        "candidate_id": copy.deepcopy(entry.get("candidate_id")),
        "cluster_id": copy.deepcopy(entry.get("cluster_id")),
        "primary_category": category,
        "secondary_categories": copy.deepcopy(entry.get("secondary_categories", [])),
        "category_fit_all": {category: copy.deepcopy(scores.get("category_fit"))},
        "category_value_score": copy.deepcopy(scores.get("category_value_score")),
        "confidence": copy.deepcopy(scores.get("confidence")),
        "attention": {"score": copy.deepcopy(attention_score), "confidence": None},
        "verification_policy": copy.deepcopy(entry.get("verification_policy")),
        "evidence_bundle": copy.deepcopy(evidence.get("evidence_bundle")),
        "evidence_needs": copy.deepcopy(evidence.get("evidence_needs") or []),
        "missing_signals": copy.deepcopy(evidence.get("missing_signals") or []),
        "hard_risk_flags": copy.deepcopy(risk.get("hard_risk_flags") or []),
        "soft_risk_flags": copy.deepcopy(risk.get("soft_risk_flags") or []),
        "risk_detection_status": copy.deepcopy(risk.get("risk_detection_status")),
        "risk_detector_status": copy.deepcopy(risk.get("risk_detector_status")),
        "human_review": copy.deepcopy(entry.get("human_review")),
        "title": copy.deepcopy(entry.get("title")),
        "representative_title": copy.deepcopy(entry.get("title")),
        "freshness": copy.deepcopy(entry.get("freshness")),
        "recurrence": copy.deepcopy(entry.get("recurrence")),
        "tags": copy.deepcopy(entry.get("tags")),
        "cluster_confidence": copy.deepcopy(entry.get("cluster_confidence")),
        "source_observation_count": copy.deepcopy(entry.get("source_observation_count")),
        "independent_origin_count": copy.deepcopy(entry.get("independent_origin_count")),
        "source_id": copy.deepcopy(entry.get("source_id")),
        "source_name": copy.deepcopy(entry.get("source_name")),
        "source_attribution": copy.deepcopy(entry.get("source_attribution")),
        "source_refs": copy.deepcopy(entry.get("source_refs")),
        "production_ready": False,
        "publishing_ready": False,
    }


def run_reviewed_watch_promotion_gate(
    watch_review_queue: Any,
    *,
    config_path: Any = DEFAULT_CONFIG_PATH,
) -> Dict[str, Any]:
    """Return separately marked routing candidates for safe approved entries."""

    config, error = _load_config(config_path)
    if error or config is None:
        return _closed("config_load_failed", error or "promotion config unavailable")
    if not isinstance(watch_review_queue, Mapping):
        return _closed("invalid_input", "watch_review_queue must be an object")
    queues = watch_review_queue.get("queue_by_account")
    if not isinstance(queues, Mapping):
        return _closed("invalid_input", "queue_by_account must be an object")

    strong = set(config.get("strong_fact_check_categories") or [])
    fast = set(config.get("source_attribution_only_categories") or [])
    routing_candidates: List[Dict[str, Any]] = []
    blocked: List[Dict[str, Any]] = []

    for account_id in sorted(queues):
        entries = queues.get(account_id)
        if not isinstance(entries, list):
            blocked.append({"account_id": account_id, "reason_code": "account_queue_must_be_list"})
            continue
        for raw_entry in entries:
            if not isinstance(raw_entry, Mapping):
                blocked.append({"account_id": account_id, "reason_code": "queue_entry_must_be_object"})
                continue
            entry = copy.deepcopy(dict(raw_entry))
            if entry.get("review_state") != config.get("eligible_review_state"):
                blocked.append(_block(entry, "review_state_not_approved"))
                continue
            review = entry.get("human_review")
            if not isinstance(review, Mapping):
                blocked.append(_block(entry, "human_review_missing"))
                continue
            if (
                review.get("reviewer_type") != "human"
                or not _text(review.get("reviewer_id"))
                or not _aware_timestamp(review.get("reviewed_at"))
                or review.get("reviewed_stage2_label")
                != config.get("eligible_reviewed_stage2_label")
            ):
                blocked.append(_block(entry, "human_review_invalid"))
                continue
            if (
                entry.get("stage2_status") != config.get("required_original_stage2_status")
                or entry.get("stage2_decision") != config.get("required_original_stage2_decision")
            ):
                blocked.append(_block(entry, "original_stage2_not_watch"))
                continue
            reviewed_category = _text(review.get("reviewed_category"))
            category = _text(entry.get("primary_category"))
            if reviewed_category and reviewed_category != category:
                blocked.append(_block(entry, "category_change_requires_stage2_reclassification"))
                continue

            risk = entry.get("risk_diagnostics")
            if not isinstance(risk, Mapping):
                blocked.append(_block(entry, "risk_diagnostics_missing"))
                continue
            hard = risk.get("hard_risk_flags")
            soft = risk.get("soft_risk_flags")
            if not isinstance(hard, list) or not isinstance(soft, list) or hard or soft:
                blocked.append(_block(entry, "risk_flags_not_clear"))
                continue

            verification = entry.get("verification_policy")
            if not isinstance(verification, Mapping) or verification.get("eligible") is not True:
                blocked.append(_block(entry, "verification_not_eligible"))
                continue
            minimum = verification.get("common_minimum")
            if not isinstance(minimum, Mapping) or minimum.get("valid") is not True:
                blocked.append(_block(entry, "common_minimum_not_valid"))
                continue
            tier = _text(verification.get("verification_tier"))
            if category in strong:
                provenance = verification.get("provenance")
                provenance = provenance if isinstance(provenance, Mapping) else {}
                evidence = entry.get("evidence_diagnostics")
                evidence = evidence if isinstance(evidence, Mapping) else {}
                if (
                    tier != "strong_fact_check"
                    or verification.get("fact_checked") is not True
                    or provenance.get("risk_detection_status") != "cleared"
                    or not is_verified_reviewed_evidence_bundle(evidence.get("evidence_bundle"))
                ):
                    blocked.append(_block(entry, "strong_fact_check_incomplete"))
                    continue
            elif category in fast:
                if tier != "source_attribution_only" or verification.get("fact_checked") is not False:
                    blocked.append(_block(entry, "fast_path_verification_invalid"))
                    continue
            else:
                blocked.append(_block(entry, "category_not_configured"))
                continue

            routing_candidates.append(_routing_candidate(entry))

    routing_candidates.sort(key=lambda item: (_text(item.get("cluster_id")), _text(item.get("candidate_id"))))
    promoted_count = len(routing_candidates)
    return {
        "schema_version": REVIEWED_WATCH_PROMOTION_VERSION,
        "config_schema_version": config.get("schema_version"),
        "status": "promoted" if promoted_count else "closed",
        "fallback_used": promoted_count == 0,
        "reason_code": "ok" if promoted_count else "no_reviewed_watch_candidate_promoted",
        "reason": "human-reviewed WATCH candidates cleared for account routing" if promoted_count else "no reviewed WATCH candidate passed promotion gates",
        "routing_candidates": routing_candidates,
        "promoted_count": promoted_count,
        "blocked": blocked,
        "blocked_count": len(blocked),
        "original_stage2_decisions_mutated": False,
        "production_ready": False,
        "publishing_ready": False,
    }


__all__ = [
    "REVIEWED_WATCH_PROMOTION_VERSION",
    "DEFAULT_CONFIG_PATH",
    "run_reviewed_watch_promotion_gate",
]
