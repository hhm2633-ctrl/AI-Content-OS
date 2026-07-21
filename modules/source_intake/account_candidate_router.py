"""Fail-closed routing of reviewed Stage-2 candidates into CardNews accounts.

This standalone module performs account portfolio distribution only.  It does
not collect data, cluster items, rank TOP topics, plan slides, render, publish,
or write storage.  A cluster can appear in at most one account portfolio.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


ACCOUNT_CANDIDATE_ROUTER_VERSION = "source_intake_account_candidate_router_v1"
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "source_intake_account_routing.json"
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _score(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        return None
    return number


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_text(item) for item in value)


def _load_config(config_path: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        path = Path(config_path).resolve()
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, TypeError, ValueError) as exc:
        return None, f"config_load_failed:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, "config_root_must_be_object"
    return payload, None


def _validate_config(config: Mapping[str, Any]) -> Optional[str]:
    accounts = config.get("accounts")
    tie_priority = config.get("account_tie_priority")
    eligible = config.get("eligible_decisions")
    strong = config.get("strong_fact_check_categories")
    unassigned = config.get("unassigned_categories")

    if not isinstance(accounts, Mapping) or not accounts:
        return "accounts_must_be_nonempty_object"
    if not _string_list(tie_priority) or set(tie_priority) != set(accounts):
        return "account_tie_priority_must_match_accounts"
    if not _string_list(eligible):
        return "eligible_decisions_must_be_nonempty_string_list"
    if not _string_list(strong) or not _string_list(unassigned):
        return "category_policy_lists_must_be_string_lists"
    if config.get("require_cluster_id") is not True:
        return "require_cluster_id_must_be_true"
    if config.get("global_cluster_exclusivity") is not True:
        return "global_cluster_exclusivity_must_be_true"

    seen_categories: set[str] = set()
    for account_id, profile in accounts.items():
        if not _text(account_id) or not isinstance(profile, Mapping):
            return "invalid_account_profile"
        categories = profile.get("category_portfolio")
        if not _string_list(categories):
            return f"invalid_category_portfolio:{account_id}"
        overlap = seen_categories.intersection(categories)
        if overlap:
            return f"category_assigned_to_multiple_accounts:{sorted(overlap)[0]}"
        seen_categories.update(categories)
    overlap = seen_categories.intersection(unassigned)
    if overlap:
        return f"assigned_category_marked_unassigned:{sorted(overlap)[0]}"
    return None


def _closed(reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "schema_version": ACCOUNT_CANDIDATE_ROUTER_VERSION,
        "status": "closed",
        "fallback_used": True,
        "reason_code": reason_code,
        "reason": reason,
        "portfolios": {},
        "portfolio_counts": {},
        "routed_count": 0,
        "on_hold": [],
        "rejected": [],
        "unassigned": [],
        "duplicate_cluster_suppressed": [],
    }


def _category_account_map(config: Mapping[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for account_id, profile in config["accounts"].items():
        for category in profile["category_portfolio"]:
            result[category] = account_id
    return result


def _verification_gate(candidate: Mapping[str, Any], strong_categories: set[str]) -> Optional[str]:
    verification = candidate.get("verification_policy")
    if not isinstance(verification, Mapping):
        return "missing_verification_policy"
    if verification.get("eligible") is not True:
        return "verification_not_eligible"
    if candidate.get("evidence_needs") not in ([], None):
        return "unresolved_evidence_needs"
    if candidate.get("hard_risk_flags") not in ([], None):
        return "hard_risk_present"

    category = _text(candidate.get("primary_category"))
    tier = _text(verification.get("verification_tier"))
    if category in strong_categories:
        if tier != "strong_fact_check" or verification.get("fact_checked") is not True:
            return "strong_fact_check_required"
    elif tier == "source_attribution_only":
        if verification.get("fact_checked") is not False:
            return "fast_path_must_not_claim_fact_checked"
    elif tier == "strong_fact_check":
        if verification.get("fact_checked") is not True:
            return "escalated_fact_check_incomplete"
    else:
        return "unsupported_verification_tier"
    return None


def _candidate_sort_key(candidate: Mapping[str, Any], priority: Mapping[str, int]) -> tuple[Any, ...]:
    category = _text(candidate.get("primary_category"))
    fit_all = candidate.get("category_fit_all")
    category_fit = _score(fit_all.get(category)) if isinstance(fit_all, Mapping) else None
    confidence = _score(candidate.get("confidence"))
    value = _score(candidate.get("category_value_score"))
    return (
        -(category_fit if category_fit is not None else -1.0),
        -(confidence if confidence is not None else -1.0),
        -(value if value is not None else -1.0),
        priority.get(_text(candidate.get("account_id")), len(priority)),
        _text(candidate.get("candidate_id")),
    )


def _portfolio_entry(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    category = _text(candidate.get("primary_category"))
    fit_all = candidate.get("category_fit_all")
    verification = candidate.get("verification_policy")
    reviewed_promotion = candidate.get("decision_origin") == "human_reviewed_watch_promotion"
    return {
        "account_id": candidate.get("account_id"),
        "candidate_id": candidate.get("candidate_id"),
        "cluster_id": candidate.get("cluster_id"),
        "primary_category": category,
        "secondary_categories": copy.deepcopy(candidate.get("secondary_categories", [])),
        "category_fit": copy.deepcopy(fit_all.get(category)) if isinstance(fit_all, Mapping) else None,
        "category_value_score": copy.deepcopy(candidate.get("category_value_score")),
        "attention": copy.deepcopy(candidate.get("attention")),
        "confidence": copy.deepcopy(candidate.get("confidence")),
        "verification_tier": copy.deepcopy(verification.get("verification_tier"))
        if isinstance(verification, Mapping)
        else None,
        "fact_checked": copy.deepcopy(verification.get("fact_checked"))
        if isinstance(verification, Mapping)
        else None,
        "title": copy.deepcopy(candidate.get("title")),
        "representative_title": copy.deepcopy(candidate.get("representative_title")),
        "freshness": copy.deepcopy(candidate.get("freshness")),
        "recurrence": copy.deepcopy(candidate.get("recurrence")),
        "cluster_confidence": copy.deepcopy(candidate.get("cluster_confidence")),
        "source_observation_count": copy.deepcopy(candidate.get("source_observation_count")),
        "independent_origin_count": copy.deepcopy(candidate.get("independent_origin_count")),
        "tags": copy.deepcopy(candidate.get("tags")),
        "source_id": copy.deepcopy(candidate.get("source_id")),
        "source_name": copy.deepcopy(candidate.get("source_name")),
        "source_attribution": copy.deepcopy(candidate.get("source_attribution")),
        "source_refs": copy.deepcopy(candidate.get("source_refs")),
        "decision_origin": copy.deepcopy(candidate.get("decision_origin", "stage2")),
        "routing_decision": copy.deepcopy(candidate.get("routing_decision", "GO")),
        "original_stage2_decision": copy.deepcopy(candidate.get("original_stage2_decision")),
        "human_review": copy.deepcopy(candidate.get("human_review")),
        "routing_reasons": [
            "human_reviewed_watch_promotion" if reviewed_promotion else "stage2_go",
            "verification_gate_passed",
            "category_portfolio_match",
            "global_cluster_exclusivity_applied",
        ],
    }


def run_account_candidate_router(
    stage2_results: Any,
    *,
    config_path: Any = DEFAULT_CONFIG_PATH,
) -> Dict[str, Any]:
    """Distribute eligible Stage-2 candidates to exclusive account portfolios."""

    config, load_error = _load_config(config_path)
    if load_error or config is None:
        return _closed("config_load_failed", load_error or "unknown_config_error")
    config_error = _validate_config(config)
    if config_error:
        return _closed("invalid_config", config_error)
    if not isinstance(stage2_results, Sequence) or isinstance(stage2_results, (str, bytes, bytearray)):
        return _closed("invalid_input", "stage2_results must be a sequence of objects")

    accounts = config["accounts"]
    category_accounts = _category_account_map(config)
    unassigned_categories = set(config["unassigned_categories"])
    strong_categories = set(config["strong_fact_check_categories"])
    eligible_decisions = set(config["eligible_decisions"])
    priority = {account_id: index for index, account_id in enumerate(config["account_tie_priority"])}
    portfolios: Dict[str, List[Dict[str, Any]]] = {account_id: [] for account_id in accounts}
    on_hold: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    unassigned: List[Dict[str, Any]] = []
    eligible_by_cluster: Dict[str, List[Dict[str, Any]]] = {}

    for index, raw_candidate in enumerate(stage2_results):
        if not isinstance(raw_candidate, Mapping):
            rejected.append({"input_index": index, "reason_code": "candidate_must_be_object"})
            continue
        candidate = copy.deepcopy(dict(raw_candidate))
        candidate_id = _text(candidate.get("candidate_id"))
        cluster_id = _text(candidate.get("cluster_id"))
        category = _text(candidate.get("primary_category"))
        decision = _text(candidate.get("decision"))
        base_ref = {"candidate_id": candidate_id or None, "cluster_id": cluster_id or None}

        if not candidate_id:
            rejected.append({**base_ref, "input_index": index, "reason_code": "missing_candidate_id"})
            continue
        if candidate.get("status") != "ok":
            on_hold.append({**base_ref, "reason_code": "stage2_not_ok"})
            continue
        if not cluster_id:
            on_hold.append({**base_ref, "reason_code": "missing_cluster_id"})
            continue
        if decision not in eligible_decisions:
            target = rejected if decision == "REJECT" else on_hold
            target.append({**base_ref, "decision": decision or None, "reason_code": "stage2_not_go"})
            continue
        if category in unassigned_categories:
            unassigned.append({**base_ref, "primary_category": category, "reason_code": "category_has_no_owner_account"})
            continue
        account_id = category_accounts.get(category)
        if not account_id:
            unassigned.append({**base_ref, "primary_category": category or None, "reason_code": "category_not_configured"})
            continue
        gate_error = _verification_gate(candidate, strong_categories)
        if gate_error:
            on_hold.append({**base_ref, "primary_category": category, "reason_code": gate_error})
            continue

        candidate["account_id"] = account_id
        eligible_by_cluster.setdefault(cluster_id, []).append(candidate)

    duplicate_suppressed: List[Dict[str, Any]] = []
    for cluster_id in sorted(eligible_by_cluster):
        candidates = sorted(eligible_by_cluster[cluster_id], key=lambda item: _candidate_sort_key(item, priority))
        winner = candidates[0]
        portfolios[winner["account_id"]].append(_portfolio_entry(winner))
        for suppressed in candidates[1:]:
            duplicate_suppressed.append(
                {
                    "cluster_id": cluster_id,
                    "candidate_id": suppressed.get("candidate_id"),
                    "suppressed_account_id": suppressed.get("account_id"),
                    "selected_candidate_id": winner.get("candidate_id"),
                    "selected_account_id": winner.get("account_id"),
                    "reason_code": "cluster_already_assigned",
                }
            )

    for account_id in portfolios:
        portfolios[account_id].sort(key=lambda item: (_text(item.get("cluster_id")), _text(item.get("candidate_id"))))
    routed_count = sum(len(items) for items in portfolios.values())
    return {
        "schema_version": ACCOUNT_CANDIDATE_ROUTER_VERSION,
        "config_schema_version": config.get("schema_version"),
        "status": "routed" if routed_count else "closed",
        "fallback_used": routed_count == 0,
        "reason_code": "ok" if routed_count else "no_eligible_account_candidates",
        "reason": "exclusive account portfolio routing completed" if routed_count else "no candidate passed account routing gates",
        "routing_scope": "card_news_only",
        "portfolios": portfolios,
        "portfolio_counts": {account_id: len(items) for account_id, items in portfolios.items()},
        "routed_count": routed_count,
        "on_hold": on_hold,
        "rejected": rejected,
        "unassigned": unassigned,
        "duplicate_cluster_suppressed": duplicate_suppressed,
        "global_cluster_exclusivity": True,
        "top_topic_selection": "deferred_to_downstream_stage",
        "calibration_status": config.get("calibration_status"),
    }


__all__ = [
    "ACCOUNT_CANDIDATE_ROUTER_VERSION",
    "DEFAULT_CONFIG_PATH",
    "run_account_candidate_router",
]
