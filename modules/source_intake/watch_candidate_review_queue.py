"""Fail-closed human-review queue for Stage-2 WATCH candidates.

The queue assigns reviewable WATCH candidates provisionally to existing
multi-account category portfolios.  It never changes Stage-2 decisions, writes
review history, promotes a candidate, or executes production/publishing.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


WATCH_REVIEW_QUEUE_VERSION = "source_intake_watch_review_queue_v1"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "source_intake_watch_review.json"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _score(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if 0.0 <= numeric <= 1.0 else None


def _load_json(path: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, TypeError, ValueError) as exc:
        return None, f"json_load_failed:{type(exc).__name__}"
    return (dict(payload), None) if isinstance(payload, Mapping) else (None, "json_root_must_be_object")


def _resolve_routing_path(config: Mapping[str, Any], config_path: Any) -> Path:
    raw = _text(config.get("routing_config_path"))
    if not raw:
        return Path(__file__).resolve().parents[2] / "config" / "source_intake_account_routing.json"
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    repository_root = Path(__file__).resolve().parents[2]
    return repository_root / candidate


def _validate_config(config: Mapping[str, Any], routing: Mapping[str, Any]) -> Optional[str]:
    states = config.get("human_review_states")
    state_map = config.get("review_state_to_stage2_label")
    accounts = routing.get("accounts")
    tie_priority = routing.get("account_tie_priority")
    if not _string_list(states) or set(states) != {"approved", "hold", "excluded"}:
        return "human_review_states_must_be_approved_hold_excluded"
    if not isinstance(state_map, Mapping) or set(state_map) != set(states):
        return "review_state_mapping_must_match_states"
    if set(state_map.values()) != {"GO", "WATCH", "REJECT"}:
        return "review_state_mapping_has_invalid_stage2_labels"
    if not isinstance(accounts, Mapping) or not accounts:
        return "routing_accounts_missing"
    if not _string_list(tie_priority) or set(tie_priority) != set(accounts):
        return "routing_tie_priority_must_match_accounts"
    for account_id, profile in accounts.items():
        portfolio = profile.get("category_portfolio") if isinstance(profile, Mapping) else None
        if not _text(account_id) or not _string_list(portfolio) or not portfolio:
            return "account_category_portfolio_invalid"
    return None


def _closed(reason_code: str, reason: str, diagnostics: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    return {
        "schema_version": WATCH_REVIEW_QUEUE_VERSION,
        "status": "closed",
        "fallback_used": True,
        "reason_code": reason_code,
        "reason": reason,
        "queue_by_account": {},
        "queued_count": 0,
        "review_state_counts": {"pending": 0, "approved": 0, "hold": 0, "excluded": 0},
        "excluded": [],
        "calibration_observations": [],
        "diagnostics": copy.deepcopy(dict(diagnostics or {})),
        "stage2_decisions_mutated": False,
        "production_ready": False,
        "publishing_ready": False,
    }


def _parse_reviewed_at(value: Any) -> Optional[str]:
    raw = _text(value)
    if not raw:
        return None
    parsed: Optional[datetime] = None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError, IndexError):
            parsed = None
    if parsed is None or parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.isoformat()


def _normalize_review_records(
    review_records: Any,
    config: Mapping[str, Any],
) -> Tuple[Optional[Dict[str, Dict[str, Any]]], Optional[str]]:
    if review_records is None:
        return {}, None
    if not isinstance(review_records, Mapping):
        return None, "review_records_must_be_candidate_mapping"
    allowed = set(config["human_review_states"])
    state_labels = config["review_state_to_stage2_label"]
    normalized: Dict[str, Dict[str, Any]] = {}
    for raw_candidate_id, raw_record in review_records.items():
        candidate_id = _text(raw_candidate_id)
        if not candidate_id or not isinstance(raw_record, Mapping):
            return None, "review_record_identity_or_shape_invalid"
        state = _text(raw_record.get("review_state")).lower()
        reviewer_id = _text(raw_record.get("reviewer_id"))
        reviewer_type = _text(raw_record.get("reviewer_type")).lower()
        reviewed_at = _parse_reviewed_at(raw_record.get("reviewed_at"))
        if state not in allowed:
            return None, f"review_state_invalid:{candidate_id}"
        if config.get("require_human_reviewer") is True and (not reviewer_id or reviewer_type != "human"):
            return None, f"human_reviewer_required:{candidate_id}"
        if config.get("require_timezone_aware_reviewed_at") is True and reviewed_at is None:
            return None, f"timezone_aware_reviewed_at_required:{candidate_id}"
        reviewed_category = raw_record.get("reviewed_category")
        if reviewed_category is not None and not _text(reviewed_category):
            return None, f"reviewed_category_invalid:{candidate_id}"
        evidence_gaps = raw_record.get("evidence_gaps", [])
        if not _string_list(evidence_gaps):
            return None, f"review_evidence_gaps_invalid:{candidate_id}"
        normalized[candidate_id] = {
            "review_state": state,
            "reviewer_id": reviewer_id,
            "reviewer_type": "human",
            "reviewed_at": reviewed_at,
            "reviewed_category": _text(reviewed_category) or None,
            "reviewed_stage2_label": state_labels[state],
            "evidence_gaps": sorted({item.strip() for item in evidence_gaps if item.strip()}),
            "notes": _text(raw_record.get("notes")) or None,
        }
    return normalized, None


def _account_for_category(category: str, routing: Mapping[str, Any]) -> Optional[str]:
    accounts = routing["accounts"]
    for account_id in routing["account_tie_priority"]:
        profile = accounts.get(account_id, {})
        if category in profile.get("category_portfolio", []):
            return account_id
    return None


def _candidate_sort_key(item: Mapping[str, Any]) -> Tuple[float, float, float, str]:
    diagnostics = item.get("score_diagnostics", {})
    return (
        -float(diagnostics.get("category_fit") or 0.0),
        -float(diagnostics.get("category_value_score") or 0.0),
        -float(diagnostics.get("confidence") or 0.0),
        _text(item.get("candidate_id")),
    )


def _calibration_observation(entry: Mapping[str, Any], review: Mapping[str, Any]) -> Dict[str, Any]:
    evidence_gaps = review.get("evidence_gaps", [])
    reviewed_label = review["reviewed_stage2_label"]
    if reviewed_label != "NEEDS_EVIDENCE":
        evidence_gaps = []
    return {
        "candidate_id": entry.get("candidate_id"),
        "reviewer_id": review.get("reviewer_id"),
        "reviewer_type": "human",
        "category_id": entry.get("primary_category"),
        "decision": "WATCH",
        "reviewer_label": {
            "category_id": review.get("reviewed_category") or entry.get("primary_category"),
            "decision": reviewed_label,
            "evidence_gaps": copy.deepcopy(evidence_gaps),
        },
        "reviewed_at": review.get("reviewed_at"),
    }


def run_watch_candidate_review_queue(
    stage2_results: Any,
    *,
    review_records: Any = None,
    config_path: Any = DEFAULT_CONFIG_PATH,
) -> Dict[str, Any]:
    """Build a provisional account queue without changing Stage-2 decisions."""

    config, config_error = _load_json(config_path)
    if config_error or config is None:
        return _closed("config_load_failed", config_error or "watch review config unavailable")
    routing_path = _resolve_routing_path(config, config_path)
    routing, routing_error = _load_json(routing_path)
    if routing_error or routing is None:
        return _closed("routing_config_load_failed", routing_error or "account routing config unavailable")
    validation_error = _validate_config(config, routing)
    if validation_error:
        return _closed("invalid_config", validation_error)
    if not isinstance(stage2_results, Sequence) or isinstance(stage2_results, (str, bytes, bytearray)):
        return _closed("invalid_input", "stage2_results must be a sequence")
    reviews, review_error = _normalize_review_records(review_records, config)
    if review_error or reviews is None:
        return _closed("invalid_review_records", review_error or "review records unavailable")

    queue_by_account: Dict[str, List[Dict[str, Any]]] = {
        account_id: [] for account_id in routing["account_tie_priority"]
    }
    excluded: List[Dict[str, Any]] = []
    seen_clusters: Dict[str, str] = {}
    used_review_ids = set()
    calibration_observations: List[Dict[str, Any]] = []
    review_counts = {"pending": 0, "approved": 0, "hold": 0, "excluded": 0}

    for index, raw_candidate in enumerate(stage2_results):
        if not isinstance(raw_candidate, Mapping):
            excluded.append({"input_index": index, "reason_code": "candidate_must_be_object"})
            continue
        candidate = copy.deepcopy(dict(raw_candidate))
        candidate_id = _text(candidate.get("candidate_id"))
        cluster_id = _text(candidate.get("cluster_id"))
        primary = _text(candidate.get("primary_category"))
        base = {"input_index": index, "candidate_id": candidate_id or None, "cluster_id": cluster_id or None}
        if candidate.get("status") != config.get("eligible_stage2_status"):
            excluded.append({**base, "reason_code": "stage2_status_not_eligible"})
            continue
        if candidate.get("decision") != config.get("eligible_stage2_decision"):
            excluded.append({**base, "reason_code": "stage2_decision_not_watch"})
            continue
        hard_risks = candidate.get("hard_risk_flags", [])
        soft_risks = candidate.get("soft_risk_flags", [])
        evidence_needs = candidate.get("evidence_needs", [])
        missing_signals = candidate.get("missing_signals", [])
        if not all(_string_list(value) for value in (hard_risks, soft_risks, evidence_needs, missing_signals)):
            excluded.append({**base, "reason_code": "diagnostic_lists_malformed"})
            continue
        if hard_risks:
            excluded.append({**base, "reason_code": "hard_risk_not_review_queue_eligible", "hard_risk_flags": hard_risks})
            continue
        if not candidate_id or (config.get("require_cluster_id") is True and not cluster_id):
            excluded.append({**base, "reason_code": "candidate_or_cluster_identity_missing"})
            continue
        account_id = _account_for_category(primary, routing)
        if account_id is None:
            excluded.append({**base, "reason_code": "category_has_no_account_portfolio", "primary_category": primary or None})
            continue
        if config.get("global_cluster_exclusivity") is True and cluster_id in seen_clusters:
            excluded.append({**base, "reason_code": "global_cluster_duplicate", "first_account_id": seen_clusters[cluster_id]})
            continue
        seen_clusters[cluster_id] = account_id

        fit_score = None
        fit_all = candidate.get("category_fit_all")
        if isinstance(fit_all, Mapping):
            fit_score = _score(fit_all.get(primary))
        value_score = _score(candidate.get("category_value_score"))
        confidence = _score(candidate.get("confidence"))
        attention = candidate.get("attention")
        attention_score = _score(attention.get("score")) if isinstance(attention, Mapping) else None
        review = reviews.get(candidate_id)
        review_state = review["review_state"] if review else config.get("system_default_review_state", "pending")
        review_counts[review_state] = review_counts.get(review_state, 0) + 1
        if review:
            used_review_ids.add(candidate_id)

        entry = {
            "candidate_id": candidate_id,
            "cluster_id": cluster_id,
            "account_id": account_id,
            "account_assignment": "provisional_review_only",
            "title": copy.deepcopy(candidate.get("representative_title") or candidate.get("title")),
            "primary_category": primary,
            "secondary_categories": copy.deepcopy(candidate.get("secondary_categories", [])),
            "freshness": copy.deepcopy(candidate.get("freshness")),
            "recurrence": copy.deepcopy(candidate.get("recurrence")),
            "tags": copy.deepcopy(candidate.get("tags")),
            "cluster_confidence": copy.deepcopy(candidate.get("cluster_confidence")),
            "source_observation_count": copy.deepcopy(candidate.get("source_observation_count")),
            "independent_origin_count": copy.deepcopy(candidate.get("independent_origin_count")),
            "source_id": copy.deepcopy(candidate.get("source_id")),
            "source_name": copy.deepcopy(candidate.get("source_name")),
            "source_attribution": copy.deepcopy(candidate.get("source_attribution")),
            "source_refs": copy.deepcopy(candidate.get("source_refs")),
            "stage2_status": candidate.get("status"),
            "stage2_decision": "WATCH",
            "verification_policy": copy.deepcopy(candidate.get("verification_policy")),
            "score_diagnostics": {
                "category_fit": fit_score,
                "category_value_score": value_score,
                "confidence": confidence,
                "attention": attention_score,
            },
            "evidence_diagnostics": {
                "evidence_needs": copy.deepcopy(evidence_needs),
                "missing_signals": copy.deepcopy(missing_signals),
                "evidence_bundle": copy.deepcopy(candidate.get("evidence_bundle")),
            },
            "risk_diagnostics": {
                "hard_risk_flags": [],
                "soft_risk_flags": copy.deepcopy(soft_risks),
                "risk_detection_status": copy.deepcopy(candidate.get("risk_detection_status")),
                "risk_detector_status": copy.deepcopy(candidate.get("risk_detector_status")),
            },
            "review_state": review_state,
            "human_review": copy.deepcopy(review),
            "promotion_status": "not_promoted",
            "production_eligible": False,
            "fact_checked": False,
        }
        queue_by_account[account_id].append(entry)
        if review:
            calibration_observations.append(_calibration_observation(entry, review))

    for items in queue_by_account.values():
        items.sort(key=_candidate_sort_key)
        for rank, item in enumerate(items, start=1):
            item["review_priority_rank"] = rank

    queued_count = sum(len(items) for items in queue_by_account.values())
    unused_review_ids = sorted(set(reviews) - used_review_ids)
    return {
        "schema_version": WATCH_REVIEW_QUEUE_VERSION,
        "config_schema_version": config.get("schema_version"),
        "routing_config_schema_version": routing.get("schema_version"),
        "status": "queued" if queued_count else "closed",
        "fallback_used": queued_count == 0,
        "reason_code": "ok" if queued_count else "no_watch_candidates_eligible",
        "reason": "WATCH candidates assigned to provisional human-review queues" if queued_count else "no WATCH candidate passed review-queue gates",
        "queue_by_account": queue_by_account,
        "queue_counts": {account_id: len(items) for account_id, items in queue_by_account.items()},
        "queued_count": queued_count,
        "review_state_counts": review_counts,
        "excluded": excluded,
        "unused_review_record_candidate_ids": unused_review_ids,
        "calibration_observations": calibration_observations,
        "stage2_decisions_mutated": False,
        "approved_means_stage2_go": False,
        "global_cluster_exclusivity": bool(config.get("global_cluster_exclusivity")),
        "production_ready": False,
        "publishing_ready": False,
    }


__all__ = [
    "WATCH_REVIEW_QUEUE_VERSION",
    "DEFAULT_CONFIG_PATH",
    "run_watch_candidate_review_queue",
]
