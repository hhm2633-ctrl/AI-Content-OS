"""Load explicit owner-approved indirect Commerce association references."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


DEFAULT_REFERENCE_PATH = Path("knowledge/owner_feedback/commerce_association_reference_v1.json")
ALLOWED_RELATION_TYPES = {
    "fandom_merch",
    "material_craft",
    "body_context",
    "activity_tool",
    "visual_similarity",
    "scene_function",
    "name_wordplay",
    "object_adjacent",
    "color_wordplay",
    "visible_accessory",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _strings(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_text(item) for item in value if _text(item)]


def _candidate_text(candidate: Mapping[str, Any]) -> str:
    parts = [
        _text(candidate.get("title")),
        _text(candidate.get("context")),
        _text(candidate.get("hook")),
        _text(candidate.get("body")),
        _text(candidate.get("visual_context")),
    ]
    for field in ("keywords", "visual_entities", "scene_entities", "people_entities"):
        parts.extend(_strings(candidate.get(field)))
    return " ".join(part for part in parts if part).casefold()


def load_owner_association_references(
    path: str | Path = DEFAULT_REFERENCE_PATH,
) -> list[dict[str, Any]]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return []
    if not isinstance(payload, Mapping):
        return []
    if payload.get("status") != "ACTIVE_OWNER_RULE":
        return []
    if payload.get("source") != "human_owner_chat":
        return []
    if payload.get("is_performance_evidence") is not False:
        return []
    references = payload.get("references")
    if not isinstance(references, list):
        return []
    valid: list[dict[str, Any]] = []
    for reference in references:
        if not isinstance(reference, Mapping):
            continue
        relation_type = _text(reference.get("relation_type"))
        trigger_terms = _strings(reference.get("trigger_terms"))
        association_terms = _strings(reference.get("association_terms"))
        minimum = reference.get("min_trigger_matches", 1)
        if (
            relation_type not in ALLOWED_RELATION_TYPES
            or not trigger_terms
            or not association_terms
            or not isinstance(minimum, int)
            or minimum < 1
        ):
            continue
        valid.append(dict(reference))
    return valid


def learned_association_signals(
    candidate: Mapping[str, Any],
    *,
    reference_path: str | Path = DEFAULT_REFERENCE_PATH,
) -> list[dict[str, Any]]:
    """Return traceable signals when owner-reference triggers are observed."""

    text = _candidate_text(candidate)
    if not text:
        return []
    signals: list[dict[str, Any]] = []
    for reference in load_owner_association_references(reference_path):
        triggers = _strings(reference.get("trigger_terms"))
        matched = [trigger for trigger in triggers if trigger.casefold() in text]
        if len(matched) < int(reference.get("min_trigger_matches", 1)):
            continue
        signals.append(
            {
                "reference_id": _text(reference.get("reference_id")),
                "relation_type": _text(reference.get("relation_type")),
                "matched_source_terms": matched,
                "association_terms": _strings(reference.get("association_terms")),
                "explanation": _text(reference.get("explanation")),
                "humor_allowed": reference.get("humor_allowed") is True,
                "source": "active_owner_rule",
                "is_performance_evidence": False,
            }
        )
    explicit = candidate.get("commerce_associations")
    for signal in explicit if isinstance(explicit, list) else []:
        if not isinstance(signal, Mapping):
            continue
        relation_type = _text(signal.get("relation_type"))
        terms = _strings(signal.get("association_terms"))
        explanation = _text(signal.get("explanation"))
        if relation_type not in ALLOWED_RELATION_TYPES or not terms or not explanation:
            continue
        signals.append(
            {
                "reference_id": _text(signal.get("reference_id")) or "runtime_observation",
                "relation_type": relation_type,
                "matched_source_terms": _strings(signal.get("matched_source_terms")),
                "association_terms": terms,
                "explanation": explanation,
                "humor_allowed": signal.get("humor_allowed") is True,
                "source": "runtime_content_observation",
                "is_performance_evidence": False,
            }
        )
    return signals


__all__ = [
    "ALLOWED_RELATION_TYPES",
    "DEFAULT_REFERENCE_PATH",
    "learned_association_signals",
    "load_owner_association_references",
]
