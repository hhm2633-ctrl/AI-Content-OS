"""Deterministic per-account Instagram pattern binding for CardNews topics.

This stage consumes the per-account TOP/backup topics emitted by
``account_top_topic_selector`` and binds only real, already-registered
learning patterns onto the production roles ``hook_strategy``,
``story_structure``, ``visual_direction``, and ``cta_strategy``, plus
evidence-backed variable slide-count hints.

Boundaries:

- read-only and non-mutating: inputs are never modified and nothing is
  written to storage, network, or Instagram;
- fail-closed: unverifiable config, input, registry, freshness, evidence, or
  risk state produces an explicit closed/unavailable result, never a guess;
- account isolation: each account is bound only against its own profile and
  its own topics; no cross-account state is shared;
- no invention: pattern ids must already exist in the caller-supplied records
  or the local pattern registry; measured Instagram performance, promotion
  status, and slide-count numbers are never fabricated; reference-tier
  (CANDIDATE/VERIFIED/hypothesis) patterns never silently become
  production-approved.
"""

from __future__ import annotations

import copy
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from modules.knowledge.pattern_contract import Pattern, PatternStatus, parse_version
from modules.knowledge.pattern_registry import PatternRegistry, PatternRegistryError


ACCOUNT_INSTAGRAM_PATTERN_BINDER_VERSION = "source_intake_account_instagram_pattern_binder_v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "source_intake_instagram_pattern_binding.json"

PRODUCTION_ROLES = ("hook_strategy", "story_structure", "visual_direction", "cta_strategy")
SLIDE_HINT_ROLE = "slide_count_hint"
ALLOWED_HINT_TYPES = frozenset({"variable_length_list_supported"})
FIT_COMPONENTS = ("category_applicability", "evidence_strength", "status_tier", "freshness")

# Promotion-policy safeguard: only PROMOTED may ever be production-approved,
# and reference use is limited to CANDIDATE/VERIFIED. DEPRECATED/REJECTED are
# never selectable. Config cannot widen these sets.
ALLOWED_PRODUCTION_STATUSES = frozenset({"PROMOTED"})
ALLOWED_REFERENCE_STATUSES = frozenset({"CANDIDATE", "VERIFIED"})

STALE_REASON_CODES = frozenset(
    {"expired_pattern", "freshness_unverifiable", "review_window_exceeded"}
)
ROLE_BINDING_KEYS = frozenset({"role", "pattern_id", "applicable_categories", "applicability_basis"})
HINT_BINDING_KEYS = frozenset({"pattern_id", "hint_type", "applicable_categories", "basis"})
ACCOUNT_PROFILE_KEYS = frozenset(
    {"categories", "allowed_pattern_domains", "role_bindings", "slide_count_hint_bindings"}
)
PROVENANCE_KEYS = (
    "evidence_status",
    "observation_count",
    "account_count",
    "category_count",
    "dataset_hash",
    "import_version",
    "source_dataset",
    "risk_flags",
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


def _positive_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _string_list(value: Any, *, allow_empty: bool = True) -> Optional[List[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return None
    result: List[str] = []
    for item in value:
        text = _text(item)
        if not text:
            return None
        if text not in result:
            result.append(text)
    if not allow_empty and not result:
        return None
    return result


def _parse_iso(value: Any) -> Optional[datetime]:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _load_config(config_path: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with Path(config_path).resolve().open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, TypeError, ValueError) as exc:
        return None, f"config_load_failed:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, "config_root_must_be_object"
    return payload, None


def _validate_binding_entry(
    entry: Any,
    *,
    account_id: str,
    account_categories: List[str],
    supported_roles: List[str],
    is_hint: bool,
) -> Optional[str]:
    expected_keys = HINT_BINDING_KEYS if is_hint else ROLE_BINDING_KEYS
    if not isinstance(entry, Mapping) or set(entry) != expected_keys:
        return f"{account_id}.binding_entry_keys_must_be_exact"
    if not _text(entry.get("pattern_id")):
        return f"{account_id}.binding_pattern_id_must_be_nonempty"
    applicable = _string_list(entry.get("applicable_categories"), allow_empty=False)
    if applicable is None or not set(applicable).issubset(account_categories):
        return f"{account_id}.applicable_categories_must_be_account_categories"
    if is_hint:
        if entry.get("hint_type") not in ALLOWED_HINT_TYPES:
            return f"{account_id}.hint_type_not_allowed"
        if not _text(entry.get("basis")):
            return f"{account_id}.hint_basis_must_be_nonempty"
    else:
        if entry.get("role") not in supported_roles:
            return f"{account_id}.binding_role_not_supported"
        if not _text(entry.get("applicability_basis")):
            return f"{account_id}.applicability_basis_must_be_nonempty"
    return None


def _validate_config(config: Mapping[str, Any]) -> Optional[str]:
    if not _text(config.get("schema_version")):
        return "schema_version_must_be_nonempty"
    if not _text(config.get("pattern_registry_path")):
        return "pattern_registry_path_must_be_nonempty"
    if config.get("reference_time") is not None and _parse_iso(config.get("reference_time")) is None:
        return "reference_time_must_be_null_or_iso_datetime"
    if _positive_int(config.get("max_reviewed_age_days")) is None:
        return "max_reviewed_age_days_must_be_positive_int"
    if _positive_int(config.get("minimum_source_claims")) is None:
        return "minimum_source_claims_must_be_positive_int"
    if _positive_int(config.get("evidence_saturation_claim_count")) is None:
        return "evidence_saturation_claim_count_must_be_positive_int"

    production_statuses = _string_list(config.get("production_statuses"), allow_empty=False)
    reference_statuses = _string_list(config.get("reference_statuses"), allow_empty=False)
    if production_statuses is None or not set(production_statuses).issubset(ALLOWED_PRODUCTION_STATUSES):
        return "production_statuses_must_be_subset_of_promoted"
    if reference_statuses is None or not set(reference_statuses).issubset(ALLOWED_REFERENCE_STATUSES):
        return "reference_statuses_must_be_subset_of_candidate_verified"

    supported_roles = _string_list(config.get("supported_roles"), allow_empty=False)
    if supported_roles is None or not set(supported_roles).issubset(PRODUCTION_ROLES):
        return "supported_roles_must_be_known_production_roles"
    required_roles = _string_list(config.get("required_production_roles"))
    if required_roles is None or not set(required_roles).issubset(supported_roles):
        return "required_production_roles_must_be_supported_roles"

    weights = config.get("fit_weights")
    if not isinstance(weights, Mapping) or set(weights) != set(FIT_COMPONENTS):
        return "fit_weights_must_match_fit_components"
    parsed_weights = [_score(value) for value in weights.values()]
    if any(value is None for value in parsed_weights):
        return "fit_weights_must_be_scores"
    if not math.isclose(sum(value for value in parsed_weights if value is not None), 1.0, abs_tol=1e-9):
        return "fit_weights_must_sum_to_one"

    tier_scores = config.get("status_tier_scores")
    all_statuses = set(production_statuses) | set(reference_statuses)
    if not isinstance(tier_scores, Mapping) or not all_statuses.issubset(set(tier_scores)):
        return "status_tier_scores_must_cover_selectable_statuses"
    if any(_score(tier_scores[status]) is None for status in all_statuses):
        return "status_tier_scores_must_be_scores"

    blocked = config.get("blocked_risk_flags_by_role")
    expected_risk_keys = set(supported_roles) | {SLIDE_HINT_ROLE}
    if not isinstance(blocked, Mapping) or set(blocked) != expected_risk_keys:
        return "blocked_risk_flags_by_role_must_cover_all_roles_and_hint"
    if any(_string_list(value) is None for value in blocked.values()):
        return "blocked_risk_flags_must_be_string_lists"

    accounts = config.get("accounts")
    if not isinstance(accounts, Mapping) or not accounts:
        return "accounts_must_be_nonempty_object"
    for account_id, profile in accounts.items():
        if not _text(account_id) or not isinstance(profile, Mapping):
            return "invalid_account_profile"
        if set(profile) != ACCOUNT_PROFILE_KEYS:
            return f"{account_id}.profile_keys_must_be_exact"
        categories = _string_list(profile.get("categories"), allow_empty=False)
        if categories is None:
            return f"{account_id}.categories_must_be_nonempty_string_list"
        if _string_list(profile.get("allowed_pattern_domains")) is None:
            return f"{account_id}.allowed_pattern_domains_must_be_string_list"
        role_bindings = profile.get("role_bindings")
        hint_bindings = profile.get("slide_count_hint_bindings")
        for bindings, is_hint in ((role_bindings, False), (hint_bindings, True)):
            if not isinstance(bindings, Sequence) or isinstance(bindings, (str, bytes, bytearray)):
                return f"{account_id}.bindings_must_be_lists"
            for entry in bindings:
                error = _validate_binding_entry(
                    entry,
                    account_id=account_id,
                    account_categories=categories,
                    supported_roles=supported_roles,
                    is_hint=is_hint,
                )
                if error:
                    return error
    return None


def _closed(reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "schema_version": ACCOUNT_INSTAGRAM_PATTERN_BINDER_VERSION,
        "status": "closed",
        "fallback_used": True,
        "reason_code": reason_code,
        "reason": reason,
        "pattern_source": None,
        "pattern_pool_size": 0,
        "invalid_pattern_records": [],
        "bindings_by_account": {},
        "skipped_topics_by_account": {},
        "topic_count": 0,
        "bound_topic_count": 0,
        "bound_role_binding_count": 0,
        "production_approved_binding_count": 0,
        "reference_only_binding_count": 0,
        "account_isolation": True,
        "deterministic": True,
        "input_mutated": False,
        "reference_time": None,
    }


def _load_pattern_pool(
    pattern_records: Optional[Sequence[Any]],
    registry_path: Path,
) -> Tuple[Optional[Dict[str, Pattern]], List[Dict[str, Any]], Optional[str], Optional[str]]:
    invalid: List[Dict[str, Any]] = []
    records: List[Pattern] = []
    if pattern_records is not None:
        if not isinstance(pattern_records, Sequence) or isinstance(pattern_records, (str, bytes, bytearray)):
            return None, invalid, "pattern_records_must_be_list", None
        for index, raw in enumerate(pattern_records):
            try:
                if isinstance(raw, Pattern):
                    records.append(raw)
                elif isinstance(raw, Mapping):
                    records.append(Pattern.from_dict(dict(raw)))
                else:
                    raise ValueError("pattern record must be an object")
            except (TypeError, ValueError) as exc:
                # Invalid records are excluded, never repaired or guessed.
                invalid.append(
                    {
                        "input_index": index,
                        "reason_code": "invalid_pattern_record",
                        "detail": str(exc)[:200],
                    }
                )
        source = "caller_supplied"
    else:
        try:
            records = list(PatternRegistry(path=registry_path).current().values())
        except (PatternRegistryError, OSError, TypeError, ValueError) as exc:
            return None, invalid, f"pattern_registry_load_failed:{type(exc).__name__}", None
        source = "local_registry"

    current: Dict[str, Pattern] = {}
    for pattern in records:
        previous = current.get(pattern.pattern_id)
        if previous is None or parse_version(pattern.version) > parse_version(previous.version):
            current[pattern.pattern_id] = pattern
    return current, invalid, None, source


def _parse_provenance(pattern: Pattern) -> Dict[str, Any]:
    parsed: Dict[str, Any] = {}
    for item in pattern.preconditions:
        key, separator, value = item.partition("=")
        if separator and key.strip() in PROVENANCE_KEYS:
            parsed[key.strip()] = value.strip()
    risk_text = parsed.get("risk_flags", "")
    risk_flags = sorted({flag.strip() for flag in risk_text.split(",") if flag.strip()})
    return {
        "source_claim_count": len(pattern.source_claim_ids),
        "source_claim_ids": copy.deepcopy(pattern.source_claim_ids),
        "owner_skill": pattern.owner_skill,
        "evidence_status": parsed.get("evidence_status"),
        "observation_count": parsed.get("observation_count"),
        "account_count": parsed.get("account_count"),
        "category_count": parsed.get("category_count"),
        "dataset_hash": parsed.get("dataset_hash"),
        "import_version": parsed.get("import_version"),
        "source_dataset": parsed.get("source_dataset"),
        "risk_flags": risk_flags,
    }


def _evaluate_freshness(
    pattern: Pattern,
    tier: str,
    reference_dt: Optional[datetime],
    reference_text: Optional[str],
    max_reviewed_age_days: int,
) -> Tuple[Dict[str, Any], Optional[str], float]:
    """Return (freshness_detail, stale_exclusion_reason_or_None, component)."""

    detail: Dict[str, Any] = {
        "expires_at": pattern.expires_at,
        "reviewed_at": pattern.reviewed_at,
        "reference_time": reference_text,
        "evaluation": None,
    }
    if pattern.expires_at:
        expires = _parse_iso(pattern.expires_at)
        if expires is None or reference_dt is None:
            # An explicit expiry that cannot be checked fails closed as stale.
            detail["evaluation"] = "freshness_unverifiable"
            return detail, "freshness_unverifiable", 0.0
        if expires <= reference_dt:
            detail["evaluation"] = "expired"
            return detail, "expired_pattern", 0.0
    if pattern.reviewed_at:
        reviewed = _parse_iso(pattern.reviewed_at)
        if reviewed is None or reference_dt is None:
            detail["evaluation"] = "review_age_unverifiable"
            if tier == "production_approved":
                return detail, "freshness_unverifiable", 0.0
            return detail, None, 0.0
        age_days = (reference_dt - reviewed).total_seconds() / 86400.0
        if age_days > float(max_reviewed_age_days):
            detail["evaluation"] = "review_window_exceeded"
            return detail, "review_window_exceeded", 0.0
        detail["evaluation"] = "reviewed_within_window"
        return detail, None, 1.0
    detail["evaluation"] = "unreviewed"
    if tier == "production_approved":
        # The pattern contract already forbids unreviewed PROMOTED records;
        # this branch is a defensive fail-closed backstop.
        return detail, "freshness_unverifiable", 0.0
    return detail, None, 0.0


def _reference_missing_needs(pattern: Pattern, provenance: Mapping[str, Any]) -> List[str]:
    needs: List[str] = []
    if pattern.status is PatternStatus.CANDIDATE:
        needs.append("independent_verification_per_promotion_policy")
    if not pattern.reviewed_at:
        needs.append("human_review_evidence")
    if provenance.get("evidence_status") in ("hypothesis_only", None):
        needs.append("independent_observation_evidence")
    needs.append("measured_instagram_performance_evidence")
    needs.append("explicit_human_promotion_approval")
    return needs


def _unavailable(role: str, reason_code: str, exclusions: List[Dict[str, Any]], missing_needs: List[str]) -> Dict[str, Any]:
    return {
        "role": role,
        "status": reason_code,
        "reason_code": reason_code,
        "bound": False,
        "pattern_id": None,
        "excluded_patterns": exclusions,
        "missing_needs": missing_needs,
        "production_planning_eligible": False,
    }


def _evaluate_binding(
    role: str,
    entries: List[Mapping[str, Any]],
    topic_category: str,
    allowed_domains: List[str],
    pool: Mapping[str, Pattern],
    gates: Mapping[str, Any],
    pattern_source: str,
) -> Dict[str, Any]:
    if not entries:
        return _unavailable(
            role,
            "pattern_unavailable",
            [],
            ["configured_role_binding_for_account", "eligible_existing_pattern"],
        )

    exclusions: List[Dict[str, Any]] = []
    eligible: List[Tuple[float, int, str, Dict[str, Any]]] = []

    for entry in entries:
        pattern_id = _text(entry.get("pattern_id"))
        pattern = pool.get(pattern_id)
        if pattern is None:
            exclusions.append({"pattern_id": pattern_id, "reason_code": "pattern_id_not_found"})
            continue

        status_value = pattern.status.value
        if status_value in gates["production_statuses"]:
            tier = "production_approved"
        elif status_value in gates["reference_statuses"]:
            tier = "reference_only"
        else:
            exclusions.append(
                {"pattern_id": pattern_id, "reason_code": "status_not_selectable", "pattern_status": status_value}
            )
            continue
        if pattern.domain not in allowed_domains:
            exclusions.append(
                {"pattern_id": pattern_id, "reason_code": "domain_not_allowed_for_account", "domain": pattern.domain}
            )
            continue
        applicable = entry.get("applicable_categories") or []
        if topic_category not in applicable:
            exclusions.append(
                {"pattern_id": pattern_id, "reason_code": "category_not_applicable", "topic_category": topic_category}
            )
            continue
        if len(pattern.source_claim_ids) < int(gates["minimum_source_claims"]):
            exclusions.append(
                {
                    "pattern_id": pattern_id,
                    "reason_code": "insufficient_source_claims",
                    "source_claim_count": len(pattern.source_claim_ids),
                }
            )
            continue

        provenance = _parse_provenance(pattern)
        blocked_flags = sorted(set(provenance["risk_flags"]) & set(gates["blocked_risk_flags"].get(role, [])))
        if blocked_flags:
            exclusions.append(
                {"pattern_id": pattern_id, "reason_code": "blocked_risk_flag", "blocked_flags": blocked_flags}
            )
            continue

        freshness_detail, stale_reason, freshness_component = _evaluate_freshness(
            pattern,
            tier,
            gates["reference_dt"],
            gates["reference_time"],
            int(gates["max_reviewed_age_days"]),
        )
        if stale_reason:
            exclusions.append({"pattern_id": pattern_id, "reason_code": stale_reason})
            continue

        saturation = int(gates["evidence_saturation_claim_count"])
        components = {
            "category_applicability": 1.0,
            "evidence_strength": round(min(1.0, len(pattern.source_claim_ids) / float(saturation)), 6),
            "status_tier": float(gates["status_tier_scores"][status_value]),
            "freshness": freshness_component,
        }
        weights = gates["fit_weights"]
        fit_score = round(sum(float(weights[name]) * components[name] for name in FIT_COMPONENTS), 6)

        missing_needs = [] if tier == "production_approved" else _reference_missing_needs(pattern, provenance)
        binding = {
            "role": role,
            "status": "bound",
            "reason_code": "ok",
            "bound": True,
            "pattern_id": pattern.pattern_id,
            "pattern_name": pattern.name,
            "pattern_version": pattern.version,
            "pattern_status": status_value,
            "pattern_domain": pattern.domain,
            "binding_tier": tier,
            "production_planning_eligible": tier == "production_approved",
            "pattern_source": pattern_source,
            "provenance": provenance,
            "recommended_action": pattern.recommended_action,
            "prohibited_actions": copy.deepcopy(pattern.prohibited_actions),
            "risk_flags": provenance["risk_flags"],
            "fit": {"score": fit_score, "components": components, "weights": dict(weights)},
            "freshness": freshness_detail,
            "applicability_basis": _text(entry.get("applicability_basis")) or _text(entry.get("basis")),
            "reasons": [
                f"pattern_exists_in_{pattern_source}",
                f"status_selectable:{status_value}",
                "account_domain_allowed",
                "topic_category_applicable",
                f"source_claims_present:{len(pattern.source_claim_ids)}",
                "risk_gate_passed",
                "freshness_gate_passed",
                f"binding_tier:{tier}",
            ],
            "missing_needs": missing_needs,
        }
        eligible.append((-fit_score, -len(pattern.source_claim_ids), pattern.pattern_id, binding))

    if not eligible:
        existing = [item for item in exclusions if item["reason_code"] != "pattern_id_not_found"]
        stale_only = bool(existing) and all(item["reason_code"] in STALE_REASON_CODES for item in existing)
        reason_code = "stale_pattern" if stale_only else "pattern_unavailable"
        return _unavailable(role, reason_code, exclusions, ["eligible_existing_pattern"])

    eligible.sort(key=lambda item: (item[0], item[1], item[2]))
    best = eligible[0][3]
    best["excluded_patterns"] = exclusions
    return best


def _bind_hint(binding: Dict[str, Any], hint_type: str) -> Dict[str, Any]:
    binding["hint_type"] = hint_type
    binding["variable_length_supported"] = hint_type == "variable_length_list_supported"
    # No measured slide-count distribution exists in the evidence; the hint
    # only asserts what was actually observed and never invents a number.
    binding["slide_count"] = None
    binding["slide_count_range"] = None
    binding["fixed_slide_count_contract"] = False
    binding["missing_needs"] = list(binding.get("missing_needs", [])) + [
        "measured_slide_count_distribution_by_account_category"
    ]
    return binding


def _topic_identity(topic: Mapping[str, Any], tier: str) -> Dict[str, Any]:
    selection = topic.get("selection_score")
    score = None
    coverage = None
    if isinstance(selection, Mapping):
        score = _score(selection.get("score"))
        coverage = _score(selection.get("signal_coverage"))
    return {
        "account_id": copy.deepcopy(topic.get("account_id")),
        "candidate_id": copy.deepcopy(topic.get("candidate_id")),
        "cluster_id": copy.deepcopy(topic.get("cluster_id")),
        "title": copy.deepcopy(topic.get("title")),
        "primary_category": copy.deepcopy(topic.get("primary_category")),
        "topic_tier": tier,
        "rank": copy.deepcopy(topic.get("rank")),
        "selection_score": score,
        "selection_signal_coverage": coverage,
    }


def run_account_instagram_pattern_binder(
    selection_result: Any,
    *,
    pattern_records: Optional[Sequence[Any]] = None,
    config_path: Any = DEFAULT_CONFIG_PATH,
    reference_time: Optional[str] = None,
) -> Dict[str, Any]:
    """Bind existing Instagram-learned patterns onto per-account TOP/backup topics.

    ``pattern_records`` optionally supplies pattern dicts/objects already
    loaded by the caller; otherwise the local pattern registry JSONL is read.
    ``reference_time`` (ISO-8601) is the only freshness clock; the wall clock
    is never read, keeping the stage deterministic.
    """

    config, load_error = _load_config(config_path)
    if load_error or config is None:
        return _closed("config_load_failed", load_error or "unknown_config_error")
    config_error = _validate_config(config)
    if config_error:
        return _closed("invalid_config", config_error)

    if not isinstance(selection_result, Mapping):
        return _closed("invalid_input", "selection_result must be an object")
    if selection_result.get("status") != "selected":
        return _closed(
            "topic_selection_not_selected",
            _text(selection_result.get("reason_code")) or "upstream_closed",
        )
    top_by_account = selection_result.get("top_by_account")
    backup_by_account = selection_result.get("backup_by_account")
    if not isinstance(top_by_account, Mapping) or not isinstance(backup_by_account, Mapping):
        return _closed("invalid_input", "top_by_account and backup_by_account must be objects")
    if set(top_by_account) != set(config["accounts"]) or not set(backup_by_account).issubset(set(config["accounts"])):
        return _closed("account_set_mismatch", "selection accounts must exactly match binding config accounts")

    resolved_reference = _text(reference_time) or (_text(config.get("reference_time")) or None)
    reference_dt = _parse_iso(resolved_reference) if resolved_reference else None
    if resolved_reference and reference_dt is None:
        return _closed("invalid_reference_time", "reference_time must be an ISO-8601 datetime")

    registry_path = (REPO_ROOT / str(config["pattern_registry_path"])).resolve()
    pool, invalid_records, pool_error, pattern_source = _load_pattern_pool(pattern_records, registry_path)
    if pool_error or pool is None or pattern_source is None:
        return _closed("pattern_pool_load_failed", pool_error or "unknown_pattern_pool_error")

    gates = {
        "production_statuses": set(config["production_statuses"]),
        "reference_statuses": set(config["reference_statuses"]),
        "minimum_source_claims": int(config["minimum_source_claims"]),
        "evidence_saturation_claim_count": int(config["evidence_saturation_claim_count"]),
        "max_reviewed_age_days": int(config["max_reviewed_age_days"]),
        "status_tier_scores": config["status_tier_scores"],
        "fit_weights": config["fit_weights"],
        "blocked_risk_flags": config["blocked_risk_flags_by_role"],
        "reference_dt": reference_dt,
        "reference_time": resolved_reference,
    }
    supported_roles = list(config["supported_roles"])
    required_roles = list(config["required_production_roles"])

    bindings_by_account: Dict[str, List[Dict[str, Any]]] = {}
    skipped_by_account: Dict[str, List[Dict[str, Any]]] = {}
    topic_count = 0
    bound_topic_count = 0
    bound_role_binding_count = 0
    production_count = 0
    reference_count = 0
    any_stale = False

    # Accounts are processed strictly one at a time against their own profile;
    # no selection, scoring, or exclusion state crosses account boundaries.
    for account_id, profile in config["accounts"].items():
        bindings_by_account[account_id] = []
        skipped_by_account[account_id] = []
        account_categories = list(profile["categories"])
        allowed_domains = list(profile["allowed_pattern_domains"])
        role_entries: Dict[str, List[Mapping[str, Any]]] = {role: [] for role in supported_roles}
        for entry in profile["role_bindings"]:
            role_entries[entry["role"]].append(entry)
        hint_entries = list(profile["slide_count_hint_bindings"])

        tiers = [("top", top_by_account.get(account_id)), ("backup", backup_by_account.get(account_id))]
        for tier_name, topics in tiers:
            if topics is None:
                continue
            if not isinstance(topics, Sequence) or isinstance(topics, (str, bytes, bytearray)):
                return _closed("invalid_input", f"{account_id} {tier_name} topics must be a list")
            for index, topic in enumerate(topics):
                if not isinstance(topic, Mapping):
                    skipped_by_account[account_id].append(
                        {"topic_tier": tier_name, "input_index": index, "reason_code": "topic_must_be_object"}
                    )
                    continue
                candidate_id = _text(topic.get("candidate_id"))
                cluster_id = _text(topic.get("cluster_id"))
                if not candidate_id or not cluster_id:
                    skipped_by_account[account_id].append(
                        {"topic_tier": tier_name, "input_index": index, "reason_code": "missing_topic_identity"}
                    )
                    continue
                if _text(topic.get("account_id")) != account_id:
                    skipped_by_account[account_id].append(
                        {"topic_tier": tier_name, "candidate_id": candidate_id, "reason_code": "account_identity_mismatch"}
                    )
                    continue
                topic_category = _text(topic.get("primary_category"))
                if topic_category not in account_categories:
                    skipped_by_account[account_id].append(
                        {
                            "topic_tier": tier_name,
                            "candidate_id": candidate_id,
                            "reason_code": "category_not_in_account_profile",
                            "primary_category": topic_category or None,
                        }
                    )
                    continue

                topic_count += 1
                roles: Dict[str, Dict[str, Any]] = {}
                for role in supported_roles:
                    roles[role] = _evaluate_binding(
                        role, role_entries[role], topic_category, allowed_domains, pool, gates, pattern_source
                    )

                hint_result = _evaluate_binding(
                    SLIDE_HINT_ROLE, hint_entries, topic_category, allowed_domains, pool, gates, pattern_source
                )
                if hint_result["bound"]:
                    hint_entry_match = next(
                        entry for entry in hint_entries if _text(entry.get("pattern_id")) == hint_result["pattern_id"]
                    )
                    hint_result = _bind_hint(hint_result, str(hint_entry_match["hint_type"]))

                bound_roles = [role for role in supported_roles if roles[role]["bound"]]
                stale_roles = [role for role in supported_roles if roles[role]["reason_code"] == "stale_pattern"]
                if bound_roles:
                    binding_status = "bound"
                elif stale_roles:
                    binding_status = "stale_pattern"
                    any_stale = True
                else:
                    binding_status = "pattern_unavailable"

                production_eligible = bool(required_roles) and all(
                    roles.get(role, {}).get("bound") and roles[role]["binding_tier"] == "production_approved"
                    for role in required_roles
                )
                missing_needs = sorted(
                    {
                        need
                        for record in list(roles.values()) + [hint_result]
                        for need in record.get("missing_needs", [])
                    }
                )

                entry = _topic_identity(topic, tier_name)
                entry.update(
                    {
                        "binding_status": binding_status,
                        "roles": roles,
                        "slide_count_hint": hint_result,
                        "bound_role_count": len(bound_roles),
                        "production_planning_eligible": production_eligible,
                        "missing_needs": missing_needs,
                    }
                )
                bindings_by_account[account_id].append(entry)

                if bound_roles:
                    bound_topic_count += 1
                for record in list(roles.values()) + [hint_result]:
                    if record["bound"]:
                        bound_role_binding_count += 1
                        if record["binding_tier"] == "production_approved":
                            production_count += 1
                        else:
                            reference_count += 1

    if bound_role_binding_count:
        status = "bound"
        reason_code = "ok"
        reason = "per-account Instagram pattern binding completed"
    elif any_stale:
        status = "closed"
        reason_code = "stale_pattern"
        reason = "every configured pattern failed freshness verification"
    else:
        status = "closed"
        reason_code = "pattern_unavailable"
        reason = "no eligible existing pattern could be bound for any account topic"

    return {
        "schema_version": ACCOUNT_INSTAGRAM_PATTERN_BINDER_VERSION,
        "config_schema_version": config.get("schema_version"),
        "status": status,
        "fallback_used": bound_role_binding_count == 0,
        "reason_code": reason_code,
        "reason": reason,
        "pattern_source": pattern_source,
        "pattern_pool_size": len(pool),
        "invalid_pattern_records": invalid_records,
        "bindings_by_account": bindings_by_account,
        "skipped_topics_by_account": skipped_by_account,
        "topic_count": topic_count,
        "bound_topic_count": bound_topic_count,
        "bound_role_binding_count": bound_role_binding_count,
        "production_approved_binding_count": production_count,
        "reference_only_binding_count": reference_count,
        "account_isolation": True,
        "deterministic": True,
        "input_mutated": False,
        "reference_time": resolved_reference,
        "production_status_gate": "only_non_expired_promoted_patterns_may_be_production_approved",
        "calibration_status": config.get("calibration_status"),
        "calibration_note": config.get("calibration_note"),
    }


__all__ = [
    "ACCOUNT_INSTAGRAM_PATTERN_BINDER_VERSION",
    "DEFAULT_CONFIG_PATH",
    "run_account_instagram_pattern_binder",
]
