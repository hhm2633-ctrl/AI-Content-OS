from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from modules.card_news.canvas_contract import (
    MAX_ALLOWED_CARD_SLIDE_COUNT,
    MIN_ALLOWED_CARD_SLIDE_COUNT,
)


ACCOUNT_VARIABLE_SLIDE_PLANNER_VERSION = "card_news_account_variable_slide_planner_v1"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "card_news_account_variable_slides.json"


CANONICAL_ROLES = ("hook", "problem", "solution", "cta")
SEMANTIC_ROLES = (
    "cover",
    "context",
    "problem",
    "evidence",
    "explanation",
    "social_proof",
    "counterpoint",
    "conclusion",
    "debate_cta",
)
SUPPORTED_LAYOUT_TYPES = {
    "notebook",
    "dark_editorial",
    "bold_ai",
    "character_diary",
    "comparison",
    "tutorial",
    "checklist",
    "timeline",
    "warning",
    "number_list",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _safe_int(value: Any) -> Optional[int]:
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or not stripped.isdigit():
            return None
        value = int(stripped)
    if isinstance(value, bool) or not isinstance(value, int):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        else:
            return None
    return int(value) if value is not None and isinstance(value, (int, float)) else None


def _safe_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not number.isfinite() or number < 0:
        return None
    return number


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _load_json(path: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with Path(path).resolve().open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, TypeError, ValueError) as exc:
        return None, f"config_load_failed:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, "config_root_must_be_object"
    return payload, None


def _closed(reason_code: str, reason: str, account_id: str = "", candidate_id: str = "", cluster_id: str = "", *, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "schema_version": ACCOUNT_VARIABLE_SLIDE_PLANNER_VERSION,
        "config_schema_version": (config or {}).get("schema_version"),
        "status": "planning_not_ready",
        "fallback_used": False,
        "reason_code": reason_code,
        "reason": reason,
        "account_id": account_id or None,
        "candidate_id": candidate_id or None,
        "cluster_id": cluster_id or None,
        "slide_count": 0,
        "selected_pattern": {},
        "slides": [],
        "slide_count_bounds": {},
        "pattern_provenance": {},
        "missing_requirements": [reason],
        "renderer_compatibility_notes": [
            "planner did not produce slides due input/config unrecoverable issue"
        ],
    }


def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _normalize_budgets(value: Any, default_budget: Dict[str, Any]) -> Dict[str, Any]:
    base = dict(default_budget or {})
    if not isinstance(value, Mapping):
        return base
    return {
        "headline_chars": _safe_int(value.get("headline_chars")) or base.get("headline_chars", 28),
        "headline_lines": _safe_int(value.get("headline_lines")) or base.get("headline_lines", 1),
        "body_chars": _safe_int(value.get("body_chars")) or base.get("body_chars", 180),
        "body_lines": _safe_int(value.get("body_lines")) or base.get("body_lines", 2),
    }


def _enforce_mobile_density(
    budget: Dict[str, Any],
    density_limits: Dict[str, int],
) -> Tuple[Dict[str, Any], List[str]]:
    warnings: List[str] = []
    result = dict(budget)
    headline_chars = _safe_int(result.get("headline_chars")) or 0
    headline_lines = _safe_int(result.get("headline_lines")) or 0
    body_chars = _safe_int(result.get("body_chars")) or 0
    body_lines = _safe_int(result.get("body_lines")) or 0

    headline_chars_cap = _safe_int(density_limits.get("headline_chars_max")) or headline_chars
    headline_lines_cap = _safe_int(density_limits.get("headline_lines_max")) or headline_lines
    body_chars_cap = _safe_int(density_limits.get("body_chars_max")) or body_chars
    body_lines_cap = _safe_int(density_limits.get("body_lines_max")) or body_lines

    if headline_chars > headline_chars_cap:
        result["headline_chars"] = headline_chars_cap
        warnings.append(f"headline_chars_clamped_to_{headline_chars_cap}")
    if headline_lines > headline_lines_cap:
        result["headline_lines"] = headline_lines_cap
        warnings.append(f"headline_lines_clamped_to_{headline_lines_cap}")
    if body_chars > body_chars_cap:
        result["body_chars"] = body_chars_cap
        warnings.append(f"body_chars_clamped_to_{body_chars_cap}")
    if body_lines > body_lines_cap:
        result["body_lines"] = body_lines_cap
        warnings.append(f"body_lines_clamped_to_{body_lines_cap}")

    return result, warnings


def _validate_config(config: Mapping[str, Any]) -> Optional[str]:
    if "schema_version" not in config:
        return "schema_version_missing"
    accounts = config.get("accounts")
    patterns = config.get("pattern_definitions")
    if not isinstance(accounts, Mapping):
        return "accounts_must_be_object"
    if not isinstance(patterns, Mapping) or not patterns:
        return "pattern_definitions_must_be_non_empty_object"

    for account_id, profile in accounts.items():
        if not _text(account_id):
            return "account_id_must_be_non_empty"
        if not isinstance(profile, Mapping):
            return f"{account_id}.profile_must_be_object"
        signatures = profile.get("signature_profiles")
        if not isinstance(signatures, Mapping):
            return f"{account_id}.signature_profiles_must_be_object"
        default_profile = signatures.get("default")
        if not isinstance(default_profile, Mapping):
            return f"{account_id}.signature_profiles.default_must_exist"
        for sig, sig_conf in signatures.items():
            if not isinstance(sig_conf, Mapping):
                return f"{account_id}.{sig}.signature_profile_must_be_object"
            candidates = sig_conf.get("pattern_candidates")
            if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes, bytearray)):
                return f"{account_id}.{sig}.pattern_candidates_must_be_array"
            if not candidates:
                return f"{account_id}.{sig}.pattern_candidates_cannot_be_empty"
            for candidate in candidates:
                if _text(candidate) not in patterns:
                    return f"{account_id}.{sig}.pattern_candidate_not_defined:{candidate}"
    return None


def _load_supported_layouts(config: Mapping[str, Any]) -> List[str]:
    template_types = config.get("supported_layouts")
    if isinstance(template_types, Sequence) and template_types:
        return [str(x) for x in template_types if str(x)]

    fallback = []
    template_path = Path("templates") / "card_news_layout_rules.json"
    if template_path.exists():
        try:
            with template_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            layouts = payload.get("layouts") if isinstance(payload, Mapping) else None
            if isinstance(layouts, Mapping):
                fallback = sorted({str(key) for key in layouts.keys()})
        except (OSError, ValueError, TypeError):
            fallback = []
    if not fallback:
        fallback = sorted(SUPPORTED_LAYOUT_TYPES)
    return fallback


def _normalize_binding(binding: Any) -> Dict[str, Any]:
    return copy.deepcopy(binding) if isinstance(binding, Mapping) else {}


def _is_binding_recent(binding: Mapping[str, Any], ttl_days: float, now: datetime) -> bool:
    status = _text(binding.get("status")).lower()
    if status and status not in {"active", "bound", "validated", "ok", "ready"}:
        return False

    if "bound_at" not in binding:
        return False
    bound_at = binding.get("bound_at")
    parsed = None
    if isinstance(bound_at, (int, float)):
        try:
            parsed = datetime.fromtimestamp(float(bound_at), tz=timezone.utc)
        except (OSError, OverflowError, ValueError, TypeError):
            parsed = None
    elif isinstance(bound_at, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(bound_at, fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue
        if parsed is None:
            try:
                parsed = datetime.fromisoformat(bound_at)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                parsed = None
    if parsed is None:
        return False

    if parsed > now:
        return False
    ttl_seconds = _safe_float(ttl_days)
    if ttl_seconds is None:
        return False
    age_seconds = (now - parsed).total_seconds()
    return age_seconds <= ttl_seconds * 86400.0


def _build_topic_signature(candidate: Mapping[str, Any], account_id: str, config: Mapping[str, Any]) -> str:
    explicit = _text(
        candidate.get("topic_signature")
        or candidate.get("topic_type")
        or candidate.get("story_type")
    )
    if explicit:
        return explicit

    topic_text = " ".join(
        [
            _text(candidate.get("title")),
            _text(candidate.get("representative_title")),
            _text(candidate.get("primary_category")),
            _text(candidate.get("topic")),
            _text(candidate.get("keyword")),
        ]
    ).lower()

    alias_map: Dict[str, Sequence[str]] = {
        "breaking_news": config.get("signature_aliases", {}).get("breaking_news", ()),
        "incident_timeline": config.get("signature_aliases", {}).get("incident_timeline", ()),
        "explainer": config.get("signature_aliases", {}).get("explainer", ()),
        "issue_story": config.get("signature_aliases", {}).get("issue_story", ()),
        "relationship_story": config.get("signature_aliases", {}).get("relationship_story", ()),
        "beauty_guide": config.get("signature_aliases", {}).get("beauty_guide", ()),
    }

    for signature, keywords in alias_map.items():
        for keyword in keywords:
            if not isinstance(keyword, str):
                continue
            if keyword.lower() in topic_text:
                return signature

    if account_id.startswith("account_a"):
        return "breaking_news"
    if account_id.startswith("account_c"):
        return "beauty_guide"
    return "issue_story"


def _find_pattern_from_binding(
    binding: Mapping[str, Any],
    config: Mapping[str, Any],
    now: datetime,
    account_id: str,
    target_category: str,
    target_signature: str,
    defaults: Mapping[str, Any],
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], List[str]]]:
    if not binding:
        return None

    if not _is_binding_recent(binding, defaults.get("pattern_binding_ttl_days", 0), now):
        return None

    if _text(binding.get("account_id")) and _text(binding.get("account_id")) != account_id:
        return None
    if _text(binding.get("primary_category")) and _text(binding.get("primary_category")) != target_category:
        return None

    pattern_id = _text(binding.get("pattern_id") or binding.get("instagram_pattern_id"))
    pattern_def = None
    provenance = {
        "source": "instagram_pattern_binding",
        "binding_status": "valid",
        "pattern_id": pattern_id or None,
        "provider": _text(binding.get("provider")) or "instagram",
        "bound_at": _text(binding.get("bound_at")),
        "target_signature": target_signature,
        "account_id": account_id,
    }

    patterns = config.get("pattern_definitions", {})
    if pattern_id and pattern_id in patterns:
        candidate = patterns.get(pattern_id)
        if isinstance(candidate, Mapping):
            pattern_def = copy.deepcopy(candidate)
            pattern_def.setdefault("pattern_id", pattern_id)
    else:
        inline = _normalize_binding(binding.get("pattern"))
        if isinstance(inline, Mapping) and inline.get("pattern_id"):
            pattern_def = inline
            pattern_def.setdefault("pattern_id", _text(inline.get("pattern_id")))
            provenance["pattern_id"] = pattern_def["pattern_id"]

    if not isinstance(pattern_def, Mapping):
        return None

    if _text(pattern_def.get("pattern_id")) == "":
        return None
    if _text(pattern_def.get("signature")) and _text(pattern_def.get("signature")) != target_signature:
        return None
    return pattern_def, provenance, []


def _pattern_count_options(pattern: Mapping[str, Any]) -> List[int]:
    raw = pattern.get("slides_by_count")
    if not isinstance(raw, Mapping):
        return []
    counts: List[int] = []
    for key in raw.keys():
        count = _safe_int(key)
        if count is not None and count > 0:
            counts.append(count)
    return sorted(counts)


def _sequence_length(value: Any) -> int:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return 0
    return len(value)


def _derive_requested_count(
    payload: Mapping[str, Any],
    binding: Mapping[str, Any],
    signature: str,
    fallback_target: Optional[int],
) -> Tuple[Optional[int], str]:
    for source, value in (
        ("candidate_requested_slide_count", payload.get("requested_slide_count")),
        ("candidate_planned_slide_count", payload.get("planned_slide_count")),
        ("binding_requested_slide_count", binding.get("requested_slide_count")),
    ):
        parsed = _safe_int(value)
        if parsed is not None:
            return parsed, source

    planned_count = _sequence_length(payload.get("planned_slides"))
    if planned_count:
        return planned_count, "completed_planned_slides"

    media_count = max(
        _sequence_length(payload.get("assets")),
        _sequence_length(payload.get("media")),
        _sequence_length(payload.get("images")),
    )
    scene_count = _sequence_length(payload.get("reconstruction_scenes"))
    comment_count = _sequence_length(payload.get("comments"))
    key_point_count = _sequence_length(payload.get("key_points"))
    supported_counts = [
        media_count,
        1 + scene_count + comment_count if scene_count or comment_count else 0,
        1 + key_point_count if key_point_count else 0,
    ]
    evidence_driven_count = max(supported_counts)
    if evidence_driven_count:
        return evidence_driven_count, "available_content_and_media"

    return None, "deferred_until_deep_content"


def _pick_count(
    pattern: Mapping[str, Any],
    requested_count: Optional[int],
    signature: str,
    bounds: Tuple[int, int],
    profile_target_count: Optional[int],
) -> Tuple[Optional[int], List[str]]:
    min_bound, max_bound = bounds
    available = _pattern_count_options(pattern)
    if not available:
        return None, ["pattern_count_options_empty"]
    notes: List[str] = []

    if requested_count is not None:
        if not min_bound <= requested_count <= max_bound:
            notes.append(f"requested_slide_count_{requested_count}_out_of_bounds")
            return None, notes
        if requested_count not in available:
            notes.append(f"dynamic_slide_count_{requested_count}_derived_from_content")
        return requested_count, notes

    if profile_target_count and profile_target_count in available and min_bound <= profile_target_count <= max_bound:
        return profile_target_count, notes

    in_bounds = [x for x in available if min_bound <= x <= max_bound]
    if not in_bounds:
        notes.append("pattern_count_no_valid_in_bounds")
        return None, notes

    if signature == "breaking_news":
        return min(in_bounds), notes
    if signature in {"issue_story", "relationship_story", "beauty_guide", "explainer", "incident_timeline"}:
        return max(in_bounds), notes
    return sorted(in_bounds)[len(in_bounds) // 2], notes


def _extract_pattern(
    pattern_map: Mapping[str, Any],
    pattern_id: str,
) -> Optional[Dict[str, Any]]:
    if not isinstance(pattern_id, str):
        return None
    pattern = pattern_map.get(pattern_id)
    return copy.deepcopy(pattern) if isinstance(pattern, Mapping) else None


def _validate_pattern(
    pattern: Mapping[str, Any],
    supported_layouts: Sequence[str],
    bounds: Tuple[int, int],
) -> List[str]:
    reasons: List[str] = []
    min_bound, max_bound = bounds

    pattern_id = _text(pattern.get("pattern_id"))
    if not pattern_id:
        reasons.append("pattern_id_missing")

    layouts = _text(pattern.get("layout_type") or pattern.get("layout"))
    if layouts and layouts not in supported_layouts:
        reasons.append(f"unsupported_layout:{layouts}")

    count_range = pattern.get("slide_count_range") or {}
    if isinstance(count_range, Mapping):
        min_count = _safe_int(count_range.get("min"))
        max_count = _safe_int(count_range.get("max"))
        if min_count is None or max_count is None or min_count < 0 or max_count < 0:
            reasons.append("invalid_slide_count_range")
        elif min_count > max_count:
            reasons.append("slide_count_range_min_gt_max")
        elif min_count > max_bound or max_count < min_bound:
            reasons.append("pattern_range_out_of_profile_bounds")

    slides_by_count = pattern.get("slides_by_count")
    if not isinstance(slides_by_count, Mapping) or not slides_by_count:
        reasons.append("slides_by_count_missing")
        return reasons

    valid_counts = 0
    for count_key, roles in slides_by_count.items():
        count_value = _safe_int(count_key)
        if count_value is None:
            reasons.append("non_integer_slide_count_key")
            continue
        if not isinstance(roles, Sequence) or isinstance(roles, (str, bytes, bytearray)):
            reasons.append(f"roles_for_count_{count_value}_must_be_array")
            continue
        if len(roles) != count_value:
            reasons.append(f"count_mismatch_for_{count_value}_slides")
        for index, raw_role in enumerate(roles, start=1):
            if not isinstance(raw_role, Mapping):
                reasons.append(f"count_{count_value}_slide_{index}_must_be_object")
                continue
            semantic = _text(raw_role.get("semantic_role"))
            canonical = _text(raw_role.get("canonical_role"))
            if semantic and semantic not in SEMANTIC_ROLES:
                reasons.append(f"unsupported_semantic_role:{semantic}")
            if canonical and canonical not in CANONICAL_ROLES:
                reasons.append(f"unsupported_canonical_role:{canonical}")
        valid_counts += 1
    if valid_counts == 0:
        reasons.append("slides_by_count_has_no_valid_counts")
    return reasons


def _build_default_slide(
    role_type: str,
    pattern_config: Mapping[str, Any],
    density_limits: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    default_slide_templates = pattern_config.get("default_slide_templates", {})
    template = default_slide_templates.get(role_type)
    if not isinstance(template, Mapping):
        return None
    budget, _ = _enforce_mobile_density(
        _normalize_budgets(template.get("content_budget"), pattern_config.get("default_content_budget", {})),
        dict(density_limits),
    )
    return {
        "canonical_role": _text(template.get("canonical_role") or role_type),
        "semantic_role": _text(template.get("semantic_role") or role_type),
        "purpose": _normalize_text(template.get("purpose") or role_type),
        "content_budget": budget,
        "content_budget_overrides_clamped": [],
        "metadata": {"source": "fallback_template"},
    }


def _plan_slides(
    pattern: Mapping[str, Any],
    chosen_count: int,
    signature: str,
    account_profile: Mapping[str, Any],
    bounds: Tuple[int, int],
    pattern_config: Mapping[str, Any],
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    selected: List[Dict[str, Any]] = []
    notes: List[str] = []
    missing: List[str] = []

    slides_by_count = pattern.get("slides_by_count") or {}
    raw_roles = slides_by_count.get(str(chosen_count))
    if raw_roles is None:
        raw_roles = slides_by_count.get(chosen_count)
    if not isinstance(raw_roles, Sequence) or isinstance(raw_roles, (str, bytes, bytearray)):
        available = _pattern_count_options(pattern)
        if not available:
            return _fallback_slides(account_profile, bounds, pattern_config)
        nearest = min(available, key=lambda count: abs(count - chosen_count))
        raw_roles = slides_by_count.get(str(nearest))
        if raw_roles is None:
            raw_roles = slides_by_count.get(nearest)
        notes.append(f"dynamic_role_sequence_seeded_from_{nearest}_slide_pattern")

    for role in raw_roles:
        if not isinstance(role, Mapping):
            continue
        semantic = _text(role.get("semantic_role"))
        canonical = _text(role.get("canonical_role"))
        if not canonical:
            canonical = _text(role.get("role"))
        purpose = _normalize_text(role.get("purpose") or semantic or canonical)
        budget, budget_notes = _enforce_mobile_density(
            _normalize_budgets(role.get("content_budget"), pattern_config.get("default_content_budget", {})),
            dict(pattern_config.get("mobile_density", {})),
        )
        selected.append({
            "slide_order": len(selected) + 1,
            "canonical_role": canonical or "solution",
            "semantic_role": semantic or canonical or "explanation",
            "purpose": purpose,
            "content_budget": budget,
            "content_budget_overrides_clamped": budget_notes,
            "metadata": {"source": "pattern"},
        })

    if not selected:
        return _fallback_slides(account_profile, bounds, pattern_config)

    if chosen_count == 1:
        selected = [selected[0]]
    elif chosen_count < len(selected):
        selected = [selected[0], *selected[1:-1][: max(0, chosen_count - 2)], selected[-1]]
    elif chosen_count > len(selected):
        closing = selected.pop() if len(selected) > 1 else None
        expansion_roles = ("evidence", "solution", "counterpoint")
        while len(selected) + (1 if closing is not None else 0) < chosen_count:
            role_type = expansion_roles[len(selected) % len(expansion_roles)]
            extra = _build_default_slide(
                role_type,
                pattern_config,
                pattern_config.get("mobile_density", {}),
            )
            if extra is None:
                return _fallback_slides(account_profile, bounds, pattern_config)
            extra["metadata"] = {
                **(extra.get("metadata") or {}),
                "source": "content_driven_dynamic_expansion",
            }
            selected.append(extra)
        if closing is not None:
            selected.append(closing)

    for index, item in enumerate(selected, start=1):
        item["slide_order"] = index

    min_bound, max_bound = bounds
    if len(selected) < min_bound or len(selected) > max_bound:
        notes.append("selected_pattern_count_out_of_bounds")

    # Hook/body/closing coherence.
    default_opening = _build_default_slide("opening", pattern_config, pattern_config.get("mobile_density", {}))
    if default_opening is not None:
        default_opening["slide_order"] = 1
    default_closing = _build_default_slide("closing", pattern_config, pattern_config.get("mobile_density", {}))
    if default_closing is not None:
        default_closing["slide_order"] = max(len(selected) + 1, 1)

    if selected and selected[0].get("canonical_role") != "hook":
        notes.append("first_slide_not_hook_or_cover; opening 역할로 강제 정규화")
        if default_opening:
            selected[0] = default_opening
        else:
            selected[0]["canonical_role"] = "hook"
            selected[0]["semantic_role"] = "cover"

    if len(selected) > 1 and selected[-1].get("canonical_role") != "cta":
        notes.append("last_slide_not_cta; closing 보정 적용")
        if len(selected) < max_bound and default_closing is not None:
            default_closing["slide_order"] = len(selected) + 1
            selected.append(default_closing)
        else:
            selected[-1]["canonical_role"] = "cta"
            selected[-1]["semantic_role"] = "conclusion"
            selected[-1]["metadata"] = {
                **(selected[-1].get("metadata") or {}),
                "closing_forced": True,
            }

    required_roles = account_profile.get("required_roles") or []
    for required in required_roles:
        if required not in SEMANTIC_ROLES:
            continue
        if not any(item.get("semantic_role") == required for item in selected):
            missing.append(required)

    return selected, notes, missing


def _fallback_slides(
    account_profile: Mapping[str, Any],
    bounds: Tuple[int, int],
    pattern_config: Mapping[str, Any],
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    min_bound, max_bound = bounds
    target_count = min(max_bound, max(min_bound, 1))
    fallback_pattern = account_profile.get("fallback_pattern")
    fallback = []
    if isinstance(fallback_pattern, Sequence) and not isinstance(fallback_pattern, (str, bytes, bytearray)):
        fallback = [item for item in fallback_pattern if isinstance(item, Mapping)]
    if len(fallback) < target_count:
        fallback = [item for item in (
            _build_default_slide("opening", pattern_config, pattern_config.get("mobile_density", {})),
        ) if isinstance(item, Mapping)]

    selected = []
    for index in range(target_count):
        if index >= len(fallback):
            break
        source = fallback[index]
        item = dict(source)
        item["slide_order"] = index + 1
        item["metadata"] = {
            **(item.get("metadata") or {}),
            "source": "conservative_fallback",
        }
        selected.append(item)

    return selected, ["conservative_account_fallback_legacy_pattern_used"], []


def run_account_variable_slide_planner(
    account_top_topic: Any,
    instagram_pattern_binding: Optional[Dict[str, Any]] = None,
    *,
    config_path: Any = DEFAULT_CONFIG_PATH,
) -> Dict[str, Any]:
    try:
        config, load_error = _load_json(config_path)
        if load_error or config is None:
            return _closed("config_load_failed", load_error or "unknown_config_error")
        config_error = _validate_config(config)
        if config_error:
            return _closed("invalid_config", config_error, account_id="", candidate_id="", cluster_id="")

        if not isinstance(account_top_topic, Mapping):
            return _closed("invalid_input", "account_top_topic must be an object")

        payload = copy.deepcopy(dict(account_top_topic))
        account_id = _text(payload.get("account_id"))
        candidate_id = _text(payload.get("candidate_id"))
        cluster_id = _text(payload.get("cluster_id"))
        target_category = _text(payload.get("primary_category"))
        if not account_id:
            return _closed("missing_account_id", "account_id is required", candidate_id=candidate_id, cluster_id=cluster_id)
        if not candidate_id:
            return _closed("missing_candidate_id", "candidate_id is required", account_id=account_id, cluster_id=cluster_id)
        if not cluster_id:
            return _closed("missing_cluster_id", "cluster_id is required", account_id=account_id, candidate_id=candidate_id)

        accounts = config.get("accounts") or {}
        account_profile = accounts.get(account_id)
        if not isinstance(account_profile, Mapping):
            return _closed("unknown_account", f"account profile not found: {account_id}", account_id=account_id, candidate_id=candidate_id, cluster_id=cluster_id)

        now = _now_utc()
        supported_layouts = _load_supported_layouts(config)
        min_bound = _safe_int(account_profile.get("min_slides")) or _safe_int(config.get("global_min_max", {}).get("min")) or MIN_ALLOWED_CARD_SLIDE_COUNT
        max_bound = _safe_int(account_profile.get("max_slides")) or _safe_int(config.get("global_min_max", {}).get("max")) or MAX_ALLOWED_CARD_SLIDE_COUNT
        if min_bound is None or max_bound is None or min_bound > max_bound:
            min_bound, max_bound = MIN_ALLOWED_CARD_SLIDE_COUNT, MAX_ALLOWED_CARD_SLIDE_COUNT
        bounds = (min_bound, max_bound)

        topic_signature = _build_topic_signature(payload, account_id, config)
        signature_profiles = account_profile.get("signature_profiles") or {}
        signature_profile = signature_profiles.get(topic_signature) or signature_profiles.get("default", {})
        if not isinstance(signature_profile, Mapping):
            return _closed("signature_profile_invalid", f"{account_id}.{topic_signature} profile must be object", account_id=account_id, candidate_id=candidate_id, cluster_id=cluster_id, config=config)

        pattern_candidates = list(signature_profile.get("pattern_candidates") or [])
        fallback_used = False
        reasons: List[str] = []
        selected_pattern: Optional[Dict[str, Any]] = None
        pattern_provenance: Dict[str, Any] = {}

        binding = _normalize_binding(instagram_pattern_binding)
        bound_pattern, bound_provenance, bound_reasons = (
            None,
            None,
            [],
        )
        if binding:
            found = _find_pattern_from_binding(
                binding,
                config,
                now,
                account_id,
                target_category,
                topic_signature,
                config,
            )
            if found is not None:
                bound_pattern, bound_provenance, bound_reasons = found
                reasons.extend(bound_reasons)

        if isinstance(bound_pattern, Mapping):
            selected_pattern = copy.deepcopy(bound_pattern)
            pattern_provenance = dict(bound_provenance or {})
            pattern_provenance["chosen_from"] = "instagram_pattern_binding"
            reasons.append("instagram_pattern_binding_used")
        else:
            for pattern_id in pattern_candidates:
                if isinstance(pattern_id, str):
                    candidate = _extract_pattern(config.get("pattern_definitions", {}), pattern_id)
                    if candidate is not None:
                        selected_pattern = candidate
                        pattern_provenance = {
                            "source": "configured_fallback",
                            "chosen_from": "configured_profile",
                            "pattern_id": pattern_id,
                        }
                        break

            if selected_pattern is None:
                fallback_pattern_id = _text(account_profile.get("fallback_pattern"))
                if fallback_pattern_id:
                    candidate = _extract_pattern(config.get("pattern_definitions", {}), fallback_pattern_id)
                    if candidate is not None:
                        selected_pattern = candidate
                        pattern_provenance = {
                            "source": "configured_fallback",
                            "chosen_from": "account_fallback",
                            "pattern_id": fallback_pattern_id,
                        }
                if selected_pattern is None:
                    return _closed(
                        "no_usable_pattern",
                        "configured profile fallback pattern also unavailable",
                        account_id=account_id,
                        candidate_id=candidate_id,
                        cluster_id=cluster_id,
                        config=config,
                    )
            fallback_used = not bound_pattern
            if fallback_used:
                reasons.append("instagram_pattern_binding_stale_or_unavailable; configured_fallback_used")

        pattern_id = _text(selected_pattern.get("pattern_id"))
        pattern_validate_reasons = _validate_pattern(selected_pattern, supported_layouts, bounds)
        if pattern_validate_reasons:
            return _closed(
                "invalid_pattern",
                f"pattern_validation_failed: {pattern_validate_reasons[0]}",
                account_id=account_id,
                candidate_id=candidate_id,
                cluster_id=cluster_id,
                config=config,
            )

        target_count = _safe_int(signature_profile.get("target_count")) or _safe_int(selected_pattern.get("default_slide_count"))
        requested_count, count_basis = _derive_requested_count(
            payload,
            binding,
            topic_signature,
            target_count,
        )
        if requested_count is None:
            return {
                "schema_version": ACCOUNT_VARIABLE_SLIDE_PLANNER_VERSION,
                "config_schema_version": config.get("schema_version"),
                "status": "planning_deferred",
                "fallback_used": fallback_used,
                "reason_code": "deep_content_required_for_slide_count",
                "reason": "final slide count requires source-backed content and usable media",
                "account_id": account_id,
                "candidate_id": candidate_id,
                "cluster_id": cluster_id,
                "primary_category": target_category,
                "topic_signature": topic_signature,
                "slide_count": 0,
                "slide_count_bounds": {"min": min_bound, "max": max_bound},
                "selected_pattern": {
                    "pattern_id": pattern_id,
                    "name": _text(selected_pattern.get("name")),
                    "signature": _text(selected_pattern.get("signature")),
                    "source": pattern_provenance.get("source"),
                    "provenance": pattern_provenance,
                    "chosen_count": None,
                    "requested_count": None,
                    "count_basis": count_basis,
                },
                "slides": [],
                "reasons": [*reasons, "slide_count_not_guessed_from_topic_type_or_image_count"],
                "missing_requirements": ["deep_content_and_media_inventory"],
                "renderer_compatibility": {
                    "layout_type": _text(selected_pattern.get("layout_type") or selected_pattern.get("layout")),
                    "layout_fallback_used": False,
                    "unsupported_semantic_roles": [],
                    "unsupported_canonical_roles": [],
                    "renderer_notes": ["rendering_not_authorized_without_final_content_driven_count"],
                },
            }
        chosen_count, count_notes = _pick_count(selected_pattern, requested_count, topic_signature, bounds, target_count)
        reasons.extend(count_notes)
        if chosen_count is None:
            return _closed(
                "count_not_within_bounds",
                "no usable pattern count within configured bounds",
                account_id=account_id,
                candidate_id=candidate_id,
                cluster_id=cluster_id,
                config=config,
            )

        global_density = config.get("global_mobile_density") or {}
        pattern_config = {
            "default_content_budget": config.get("default_content_budget", {}),
            "mobile_density": global_density,
            "default_slide_templates": config.get("default_slide_templates", {}),
        }

        slides, coherence_notes, missing_required = _plan_slides(
            selected_pattern,
            chosen_count,
            topic_signature,
            account_profile,
            bounds,
            pattern_config,
        )
        reasons.extend(coherence_notes)

        required_roles = list(signature_profile.get("required_roles") or [])
        if required_roles and len(slides) > 1:
            required_set = set(required_roles)
            for required in required_set:
                if required not in {item.get("semantic_role") for item in slides}:
                    missing_required.append(required)
                    reasons.append(f"required_semantic_role_missing:{required}")
        elif required_roles and len(slides) == 1:
            reasons.append("single_slide_compacts_supporting_roles_into_copy_and_caption")

        status = "planned_with_fallback" if fallback_used else "planned"

        if missing_required:
            status = "planning_not_ready"
            return _closed(
                "required_roles_missing",
                f"missing requirements: {', '.join(sorted(set(missing_required)))}",
                account_id=account_id,
                candidate_id=candidate_id,
                cluster_id=cluster_id,
                config=config,
            ) | {
                "status": "planned_with_missing_requirements",
                "fallback_used": fallback_used,
                "slide_count": len(slides),
                "missing_requirements": sorted(set(missing_required)),
                "reasons": reasons,
            }

        renderer_layout = _text(selected_pattern.get("layout_type") or selected_pattern.get("layout"))
        renderer_layout_fallback = False
        if renderer_layout not in supported_layouts:
            renderer_layout_fallback = True
            renderer_layout = config.get("fallback_layout") or config.get("default_layout") or "bold_ai"
            reasons.append(f"layout_{selected_pattern.get('layout_type')}_unsupported; fallback to {renderer_layout}")

        unsupported_semantic_roles = sorted(
            {
                _text(item.get("semantic_role"))
                for item in slides
                if _text(item.get("semantic_role")) and _text(item.get("semantic_role")) not in SEMANTIC_ROLES
            }
        )
        unsupported_canonical_roles = sorted(
            {
                _text(item.get("canonical_role"))
                for item in slides
                if _text(item.get("canonical_role")) and _text(item.get("canonical_role")) not in CANONICAL_ROLES
            }
        )

        renderer_notes = [
            "renderer_compatibility_verified",
            "legacy_4_slide_sequence_is_supported_as_fallback_option",
        ]
        if unsupported_semantic_roles:
            renderer_notes.append(f"unsupported_semantic_roles_detected:{','.join(unsupported_semantic_roles)}")
        if unsupported_canonical_roles:
            renderer_notes.append(f"unsupported_canonical_roles_detected:{','.join(unsupported_canonical_roles)}")
        if renderer_layout_fallback:
            renderer_notes.append("unsupported_layout_fallback")

        return {
            "schema_version": ACCOUNT_VARIABLE_SLIDE_PLANNER_VERSION,
            "config_schema_version": config.get("schema_version"),
            "status": status,
            "fallback_used": fallback_used,
            "planner_reason": " / ".join(reasons) if reasons else "configured_or_bound_pattern_applied",
            "account_id": account_id,
            "candidate_id": candidate_id,
            "cluster_id": cluster_id,
            "primary_category": target_category,
            "topic_signature": topic_signature,
            "slide_count": len(slides),
            "slide_count_bounds": {"min": min_bound, "max": max_bound},
            "selected_pattern": {
                "pattern_id": pattern_id,
                "name": _text(selected_pattern.get("name")),
                "signature": _text(selected_pattern.get("signature")),
                "source": pattern_provenance.get("source"),
                "provenance": pattern_provenance,
                "chosen_count": chosen_count,
                "requested_count": requested_count,
                "count_basis": count_basis,
            },
            "slides": [
                {
                    "order": item.get("slide_order"),
                    "canonical_role": item.get("canonical_role"),
                    "semantic_role": item.get("semantic_role"),
                    "purpose": item.get("purpose"),
                    "content_budget": item.get("content_budget"),
                    "content_budget_overrides_clamped": item.get("content_budget_overrides_clamped") or [],
                }
                for item in slides
            ],
            "pattern_provenance": {
                "source": pattern_provenance.get("source", "unknown"),
                "chosen_from": pattern_provenance.get("chosen_from"),
                "account_id": pattern_provenance.get("account_id"),
                "target_signature": pattern_provenance.get("target_signature"),
                "binding_status": pattern_provenance.get("binding_status"),
                "bound_at": pattern_provenance.get("bound_at"),
                "provider": pattern_provenance.get("provider"),
            },
            "reasons": reasons,
            "missing_requirements": [],
            "renderer_compatibility": {
                "layout_type": renderer_layout,
                "layout_fallback_used": renderer_layout_fallback,
                "unsupported_semantic_roles": unsupported_semantic_roles,
                "unsupported_canonical_roles": unsupported_canonical_roles,
                "renderer_notes": renderer_notes,
            },
        }
    except Exception as error:
        return _closed("planner_exception", f"account_variable_slide_planner_exception:{type(error).__name__}")


__all__ = [
    "ACCOUNT_VARIABLE_SLIDE_PLANNER_VERSION",
    "DEFAULT_CONFIG_PATH",
    "run_account_variable_slide_planner",
]
