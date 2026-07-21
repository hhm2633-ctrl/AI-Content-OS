"""Deterministic per-account TOP topic selection for CardNews candidates.

The selector consumes the exclusive portfolios emitted by
``account_candidate_router``.  Accounts are scored independently and global
cluster uniqueness is rechecked.  This module does not consume Instagram
patterns, plan slides, render, publish, write storage, or mutate its input.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


ACCOUNT_TOP_TOPIC_SELECTOR_VERSION = "source_intake_account_top_topic_selector_v1"
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "source_intake_account_top_selection.json"
)
SIGNALS = (
    "category_fit",
    "category_value",
    "attention",
    "confidence",
    "freshness",
    "recurrence",
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


def _load_config(config_path: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with Path(config_path).resolve().open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, TypeError, ValueError) as exc:
        return None, f"config_load_failed:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, "config_root_must_be_object"
    return payload, None


def _validate_config(config: Mapping[str, Any]) -> Optional[str]:
    accounts = config.get("accounts")
    minimum_coverage = _score(config.get("minimum_signal_coverage"))
    saturation = config.get("recurrence_saturation_repeat_count")
    if not isinstance(accounts, Mapping) or not accounts:
        return "accounts_must_be_nonempty_object"
    if minimum_coverage is None:
        return "minimum_signal_coverage_must_be_score"
    if not isinstance(saturation, int) or isinstance(saturation, bool) or saturation <= 0:
        return "recurrence_saturation_repeat_count_must_be_positive_int"

    for account_id, profile in accounts.items():
        if not _text(account_id) or not isinstance(profile, Mapping):
            return "invalid_account_profile"
        for field in ("top_limit", "backup_limit", "max_per_category", "max_per_primary_source"):
            value = profile.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                return f"{account_id}.{field}_must_be_positive_int"
        top_min = _score(profile.get("top_min_score"))
        backup_min = _score(profile.get("backup_min_score"))
        if top_min is None or backup_min is None or backup_min > top_min:
            return f"{account_id}.invalid_score_thresholds"
        weights = profile.get("weights")
        if not isinstance(weights, Mapping) or set(weights) != set(SIGNALS):
            return f"{account_id}.weights_must_match_signals"
        parsed_weights = [_score(value) for value in weights.values()]
        if any(value is None for value in parsed_weights):
            return f"{account_id}.weights_must_be_scores"
        if not math.isclose(sum(value for value in parsed_weights if value is not None), 1.0, abs_tol=1e-9):
            return f"{account_id}.weights_must_sum_to_one"
    return None


def _closed(reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "schema_version": ACCOUNT_TOP_TOPIC_SELECTOR_VERSION,
        "status": "closed",
        "fallback_used": True,
        "reason_code": reason_code,
        "reason": reason,
        "top_by_account": {},
        "backup_by_account": {},
        "hold_by_account": {},
        "top_count": 0,
        "backup_count": 0,
    }


def _record_score(value: Any) -> Optional[float]:
    if isinstance(value, Mapping):
        for field in ("score", "value", "normalized_value"):
            parsed = _score(value.get(field))
            if parsed is not None:
                return parsed
        return None
    return _score(value)


def _recurrence_score(value: Any, saturation: int) -> Tuple[Optional[float], Dict[str, Any]]:
    direct = _record_score(value)
    if direct is not None:
        return direct, {"method": "supplied_normalized_score", "raw_repeat_count": None}
    if not isinstance(value, Mapping):
        return None, {"method": "missing", "raw_repeat_count": None}
    repeat_count = value.get("repeat_count")
    if not isinstance(repeat_count, int) or isinstance(repeat_count, bool) or repeat_count < 0:
        return None, {"method": "missing", "raw_repeat_count": None}
    normalized = min(1.0, repeat_count / float(saturation))
    return round(normalized, 6), {
        "method": "bounded_repeat_count_saturation",
        "raw_repeat_count": repeat_count,
        "saturation_repeat_count": saturation,
    }


def _signal_values(candidate: Mapping[str, Any], saturation: int) -> Tuple[Dict[str, Optional[float]], Dict[str, Any]]:
    recurrence, recurrence_provenance = _recurrence_score(candidate.get("recurrence"), saturation)
    values = {
        "category_fit": _score(candidate.get("category_fit")),
        "category_value": _score(candidate.get("category_value_score")),
        "attention": _record_score(candidate.get("attention")),
        "confidence": _score(candidate.get("confidence")),
        "freshness": _record_score(candidate.get("freshness")),
        "recurrence": recurrence,
    }
    return values, {"recurrence": recurrence_provenance}


def _score_candidate(
    candidate: Mapping[str, Any],
    profile: Mapping[str, Any],
    saturation: int,
) -> Dict[str, Any]:
    values, provenance = _signal_values(candidate, saturation)
    weights = profile["weights"]
    contributions: Dict[str, Any] = {}
    observed_weight = 0.0
    weighted_score = 0.0
    missing: List[str] = []

    for signal in SIGNALS:
        value = values[signal]
        weight = float(weights[signal])
        if value is None:
            missing.append(signal)
            contributions[signal] = {"value": None, "weight": weight, "contribution": None}
            continue
        contribution = value * weight
        observed_weight += weight
        weighted_score += contribution
        contributions[signal] = {
            "value": value,
            "weight": weight,
            "contribution": round(contribution, 6),
        }

    # Missing evidence is not imputed and does not receive renormalized credit.
    score = round(weighted_score, 6)
    coverage = round(observed_weight, 6)
    return {
        "score": score,
        "signal_coverage": coverage,
        "signals": values,
        "contributions": contributions,
        "missing_signals": missing,
        "normalization_provenance": provenance,
    }


def _ranking_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    selection = item["selection_score"]
    return (
        -float(selection["score"]),
        -float(selection["signal_coverage"]),
        _text(item.get("cluster_id")),
        _text(item.get("candidate_id")),
    )


def _selection_entry(candidate: Mapping[str, Any], selection: Mapping[str, Any], rank: int) -> Dict[str, Any]:
    return {
        "rank": rank,
        "account_id": copy.deepcopy(candidate.get("account_id")),
        "candidate_id": copy.deepcopy(candidate.get("candidate_id")),
        "cluster_id": copy.deepcopy(candidate.get("cluster_id")),
        "title": copy.deepcopy(candidate.get("representative_title") or candidate.get("title")),
        "primary_category": copy.deepcopy(candidate.get("primary_category")),
        "source_id": copy.deepcopy(candidate.get("source_id")),
        "source_name": copy.deepcopy(candidate.get("source_name")),
        "source_attribution": copy.deepcopy(candidate.get("source_attribution")),
        "source_refs": copy.deepcopy(candidate.get("source_refs")),
        "verification_tier": copy.deepcopy(candidate.get("verification_tier")),
        "fact_checked": copy.deepcopy(candidate.get("fact_checked")),
        "selection_score": copy.deepcopy(dict(selection)),
        "selection_reasons": [
            "account_portfolio_eligible",
            "account_specific_weighted_score",
            "account_diversity_constraints_applied",
        ],
        "instagram_pattern_binding": "deferred_to_next_stage",
    }


def run_account_top_topic_selector(
    account_router_result: Any,
    *,
    config_path: Any = DEFAULT_CONFIG_PATH,
) -> Dict[str, Any]:
    """Select TOP and backup topics independently inside each account."""

    config, load_error = _load_config(config_path)
    if load_error or config is None:
        return _closed("config_load_failed", load_error or "unknown_config_error")
    config_error = _validate_config(config)
    if config_error:
        return _closed("invalid_config", config_error)
    if not isinstance(account_router_result, Mapping):
        return _closed("invalid_input", "account_router_result must be an object")
    if account_router_result.get("status") != "routed":
        return _closed("account_router_not_routed", _text(account_router_result.get("reason_code")) or "upstream_closed")
    portfolios = account_router_result.get("portfolios")
    if not isinstance(portfolios, Mapping):
        return _closed("invalid_portfolios", "portfolios must be an object")
    if set(portfolios) != set(config["accounts"]):
        return _closed("account_set_mismatch", "portfolio accounts must exactly match selection config")

    top_by_account: Dict[str, List[Dict[str, Any]]] = {account_id: [] for account_id in config["accounts"]}
    backup_by_account: Dict[str, List[Dict[str, Any]]] = {account_id: [] for account_id in config["accounts"]}
    hold_by_account: Dict[str, List[Dict[str, Any]]] = {account_id: [] for account_id in config["accounts"]}
    seen_clusters: Dict[str, str] = {}
    saturation = int(config["recurrence_saturation_repeat_count"])
    minimum_coverage = float(config["minimum_signal_coverage"])

    for account_id, profile in config["accounts"].items():
        candidates = portfolios.get(account_id)
        if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes, bytearray)):
            return _closed("invalid_account_portfolio", f"{account_id} portfolio must be a list")
        scored: List[Dict[str, Any]] = []

        for index, raw_candidate in enumerate(candidates):
            if not isinstance(raw_candidate, Mapping):
                hold_by_account[account_id].append({"input_index": index, "reason_code": "candidate_must_be_object"})
                continue
            candidate = copy.deepcopy(dict(raw_candidate))
            candidate_id = _text(candidate.get("candidate_id"))
            cluster_id = _text(candidate.get("cluster_id"))
            if not candidate_id or not cluster_id:
                hold_by_account[account_id].append(
                    {"candidate_id": candidate_id or None, "cluster_id": cluster_id or None, "reason_code": "missing_identity"}
                )
                continue
            if _text(candidate.get("account_id")) != account_id:
                hold_by_account[account_id].append(
                    {"candidate_id": candidate_id, "cluster_id": cluster_id, "reason_code": "account_identity_mismatch"}
                )
                continue
            previous_account = seen_clusters.get(cluster_id)
            if previous_account is not None:
                hold_by_account[account_id].append(
                    {
                        "candidate_id": candidate_id,
                        "cluster_id": cluster_id,
                        "reason_code": "global_cluster_duplicate",
                        "first_account_id": previous_account,
                    }
                )
                continue
            seen_clusters[cluster_id] = account_id
            selection = _score_candidate(candidate, profile, saturation)
            candidate["selection_score"] = selection
            scored.append(candidate)

        ranked = sorted(scored, key=_ranking_key)
        category_counts: Dict[str, int] = {}
        source_counts: Dict[str, int] = {}
        top_limit = int(profile["top_limit"])
        backup_limit = int(profile["backup_limit"])

        for candidate in ranked:
            selection = candidate["selection_score"]
            score = float(selection["score"])
            coverage = float(selection["signal_coverage"])
            candidate_ref = {
                "candidate_id": candidate.get("candidate_id"),
                "cluster_id": candidate.get("cluster_id"),
                "score": score,
                "signal_coverage": coverage,
            }
            if coverage < minimum_coverage:
                hold_by_account[account_id].append({**candidate_ref, "reason_code": "insufficient_signal_coverage"})
                continue
            if score < float(profile["backup_min_score"]):
                hold_by_account[account_id].append({**candidate_ref, "reason_code": "below_backup_threshold"})
                continue

            category = _text(candidate.get("primary_category")) or "unknown"
            source = _text(candidate.get("source_id")) or "unknown"
            category_full = category_counts.get(category, 0) >= int(profile["max_per_category"])
            source_full = source_counts.get(source, 0) >= int(profile["max_per_primary_source"])
            top_eligible = (
                score >= float(profile["top_min_score"])
                and len(top_by_account[account_id]) < top_limit
                and not category_full
                and not source_full
            )
            if top_eligible:
                entry = _selection_entry(candidate, selection, len(top_by_account[account_id]) + 1)
                top_by_account[account_id].append(entry)
                category_counts[category] = category_counts.get(category, 0) + 1
                source_counts[source] = source_counts.get(source, 0) + 1
                continue

            if len(backup_by_account[account_id]) < backup_limit:
                entry = _selection_entry(candidate, selection, len(backup_by_account[account_id]) + 1)
                if category_full:
                    entry["selection_reasons"].append("top_category_quota_reached")
                if source_full:
                    entry["selection_reasons"].append("top_source_quota_reached")
                if score < float(profile["top_min_score"]):
                    entry["selection_reasons"].append("below_top_threshold")
                if len(top_by_account[account_id]) >= top_limit:
                    entry["selection_reasons"].append("top_limit_reached")
                backup_by_account[account_id].append(entry)
            else:
                hold_by_account[account_id].append({**candidate_ref, "reason_code": "backup_limit_reached"})

    top_count = sum(len(items) for items in top_by_account.values())
    backup_count = sum(len(items) for items in backup_by_account.values())
    return {
        "schema_version": ACCOUNT_TOP_TOPIC_SELECTOR_VERSION,
        "config_schema_version": config.get("schema_version"),
        "status": "selected" if top_count else "closed",
        "fallback_used": top_count == 0,
        "reason_code": "ok" if top_count else "no_top_topics_selected",
        "reason": "per-account TOP topic selection completed" if top_count else "no account candidate met TOP requirements",
        "top_by_account": top_by_account,
        "backup_by_account": backup_by_account,
        "hold_by_account": hold_by_account,
        "top_count": top_count,
        "backup_count": backup_count,
        "account_independent_ranking": True,
        "global_cluster_exclusivity_rechecked": True,
        "instagram_pattern_binding": "deferred_to_next_stage",
        "calibration_status": config.get("calibration_status"),
        "calibration_note": config.get("calibration_note"),
    }


__all__ = [
    "ACCOUNT_TOP_TOPIC_SELECTOR_VERSION",
    "DEFAULT_CONFIG_PATH",
    "run_account_top_topic_selector",
]
