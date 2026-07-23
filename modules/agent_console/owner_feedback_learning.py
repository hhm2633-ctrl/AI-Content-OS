"""Compile explicit owner feedback into compact category learning memory.

The append-only feedback log remains the audit source.  This module builds a
small derived index with explicit stages so Agent Console jobs do not reread
the full history on every dispatch.

Owner-authored corrections may become ACTIVE_OWNER_RULE without pretending to
be measured performance evidence.  Hypotheses and candidate-specific labels
remain non-active learning evidence until the owner explicitly changes them.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "cardnews_owner_learning_index_v4"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEEDBACK_PATH = (
    REPOSITORY_ROOT / "knowledge" / "owner_feedback" / "cardnews_owner_feedback.jsonl"
)
DEFAULT_INDEX_PATH = (
    REPOSITORY_ROOT / "knowledge" / "owner_feedback" / "cardnews_owner_learning_index.json"
)

EXECUTION_CATEGORIES = ("news", "story", "fashion", "beauty")
_CANDIDATE_ONLY_TYPES = {
    "candidate_decision",
    "candidate_group_decision",
    "candidate_batch_decision",
    "sample_production_selection",
}
_ACTIVE_STATUSES = {"ACTIVE", "ACTIVE_DIRECTION"}
_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")
_OWNER_REVIEW_KINDS = {"candidate_evaluation", "correction", "directive", "hypothesis"}
_OWNER_SOURCES = {"human_owner_chat", "human_owner_review_workspace"}
_EXPLICIT_RULE_TYPE_TOKENS = (
    "correction", "direction", "rejection", "hard_exclusion", "hard_lock",
)
_TRACE_TEXT_FIELDS = (
    "job_id", "result_receipt_id", "result_status", "prompt_pack_sha256", "handoff_path",
)
_SEMANTIC_STOPWORDS = {
    "owner", "corpus", "rule", "card", "news", "content", "project", "learning",
    "카드뉴스", "콘텐츠", "프로젝트", "학습", "규칙", "적용", "사용", "한다",
}
_VARIABLE_COUNT_MARKERS = ("가변", "variable", "정보량", "자료량", "근거량", "고정하지")
_FIXED_COUNT_RE = re.compile(r"(?:항상|무조건|고정).{0,12}(?:[0-9]{1,2}\s*장|슬라이드)|(?:4|5|10|20)\s*장\s*(?:고정|으로)")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_list(value: Any, *, limit: int = 20) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_text(item) for item in value if _text(item)][:limit]


def _execution_trace(
    execution_context: Mapping[str, Any] | None,
    result_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Keep only bounded, non-secret identifiers needed to audit a learned result."""

    merged: dict[str, Any] = {}
    for source in (execution_context or {}, result_receipt or {}):
        if not isinstance(source, Mapping):
            continue
        education = source.get("education_receipt")
        if isinstance(education, Mapping):
            source = {**source, **education}
        for field in _TRACE_TEXT_FIELDS:
            value = _text(source.get(field))
            if value:
                merged[field] = value[:1000]
        learning_ids = source.get("learning_ids", source.get("selected_learning_ids"))
        if learning_ids is None:
            learning_ids = source.get("owner_learning_ids")
        values = _string_list(learning_ids, limit=20)
        if values:
            merged["learning_ids"] = values
    return merged


def normalize_owner_review_event(
    payload: Mapping[str, Any],
    *,
    execution_context: Mapping[str, Any] | None = None,
    result_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize one explicit owner review into the append-only feedback contract.

    Candidate evaluations remain examples.  Only payloads explicitly identified as
    ``correction`` or ``directive`` receive the activation marker.
    """

    if not isinstance(payload, Mapping):
        raise ValueError("owner review payload must be an object")
    review_kind = _text(payload.get("review_kind")).lower()
    if review_kind not in _OWNER_REVIEW_KINDS:
        raise ValueError("review_kind must be candidate_evaluation, correction, directive, or hypothesis")
    owner_decision = _text(payload.get("owner_decision"))
    owner_reason = _text(payload.get("owner_reason"))
    if not owner_decision or not owner_reason:
        raise ValueError("owner_decision and owner_reason are required")

    feedback_type = _text(payload.get("feedback_type"))
    if not feedback_type:
        feedback_type = {
            "candidate_evaluation": "candidate_decision",
            "correction": "owner_review_correction",
            "directive": "owner_review_direction",
            "hypothesis": "owner_review_hypothesis",
        }[review_kind]
    canonical = {
        "review_kind": review_kind,
        "feedback_type": feedback_type,
        "candidate_id": _text(payload.get("candidate_id")),
        "category": _text(payload.get("category")),
        "title": _text(payload.get("title")),
        "owner_decision": owner_decision,
        "owner_reason": owner_reason,
        "applies_to": _string_list(payload.get("applies_to")),
        "supersedes_event_id": _text(payload.get("supersedes_event_id")),
    }
    event_id = _text(payload.get("event_id"))
    if not event_id:
        digest = hashlib.sha256(
            json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20]
        event_id = f"owner-feedback-{digest}"
    source = _text(payload.get("source")) or "human_owner_chat"
    if source not in _OWNER_SOURCES:
        raise ValueError("owner review source is not allowed")
    event: dict[str, Any] = {
        "event_id": event_id,
        "recorded_at": _text(payload.get("recorded_at")) or datetime.now(timezone.utc).isoformat(),
        "source": source,
        "feedback_type": feedback_type,
        "category": canonical["category"],
        "title": canonical["title"][:300],
        "owner_decision": owner_decision,
        "owner_reason": owner_reason[:2000],
        "applies_to": canonical["applies_to"],
        "is_performance_evidence": False,
        "consumption_status": "HYPOTHESIS_ONLY" if review_kind == "hypothesis" else "ACTIVE",
        "review_kind": review_kind,
        "owner_rule_activation": "EXPLICIT" if review_kind in {"correction", "directive"} else "NONE",
    }
    for optional in ("candidate_id", "supersedes_event_id"):
        value = canonical[optional]
        if value:
            event[optional] = value
    trace = _execution_trace(execution_context, result_receipt)
    if trace:
        event["execution_trace"] = trace
    return event


def _event_categories(event: Mapping[str, Any]) -> list[str]:
    raw_category = _text(event.get("category")).lower()
    applies = " ".join(_string_list(event.get("applies_to"))).lower()
    raw = f"{raw_category} {applies}"
    categories: list[str] = []
    if raw_category == "agent_orchestration":
        return []
    if raw_category == "multi_account":
        for category in EXECUTION_CATEGORIES:
            if category in applies:
                categories.append(category)
        if "account_a" in applies:
            categories.append("news")
        if "account_b" in applies:
            categories.append("story")
        if "account_c" in applies:
            categories.extend(("fashion", "beauty"))
        if categories:
            return [category for category in EXECUTION_CATEGORIES if category in categories]
        return list(EXECUTION_CATEGORIES)
    if any(token in raw for token in ("news", "incident", "economy", "market", "policy", "world_news", "뉴스", "사건")):
        categories.append("news")
    if (
        "story" in raw_category
        or any(token in raw for token in ("community", "relationship", "dopamine", "entertainment", "썰", "연애", "도파민", "연예"))
    ):
        categories.append("story")
    if any(token in raw for token in ("fashion", "style", "runway", "패션", "착장")):
        categories.append("fashion")
    if any(token in raw for token in ("beauty", "makeup", "hair", "skin", "향수", "뷰티", "헤어", "메이크업")):
        categories.append("beauty")
    return [category for category in EXECUTION_CATEGORIES if category in categories]


def _rule_text(event: Mapping[str, Any]) -> str:
    reason = _text(event.get("owner_reason"))
    guardrails = _string_list(event.get("hard_guardrails"), limit=12)
    required_order = _string_list(event.get("required_order"), limit=12)
    parts = [reason]
    if required_order:
        parts.append("필수 순서: " + " → ".join(required_order))
    if guardrails:
        parts.append("금지/고정: " + ", ".join(guardrails))
    return " ".join(part for part in parts if part)[:1200]


def _rule_semantic_tokens(value: Any) -> set[str]:
    return {
        token
        for token in _tokens(value)
        if token not in _SEMANTIC_STOPWORDS and len(token) >= 2
    }


def _rule_family_and_direction(rule: str) -> tuple[str | None, str | None]:
    lowered = rule.casefold()
    if any(marker in lowered for marker in _VARIABLE_COUNT_MARKERS):
        return "slide_count", "variable"
    if _FIXED_COUNT_RE.search(lowered):
        return "slide_count", "fixed"
    return None, None


def _categories_overlap(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return bool(set(left.get("categories", [])) & set(right.get("categories", [])))


def _semantic_duplicate(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if not _categories_overlap(left, right):
        return False
    left_tokens = set(left.get("semantic_tokens", []))
    right_tokens = set(right.get("semantic_tokens", []))
    common = left_tokens & right_tokens
    union = left_tokens | right_tokens
    return len(common) >= 6 and bool(union) and len(common) / len(union) >= 0.82


def classify_feedback_event(event: Mapping[str, Any], *, sequence: int = 0) -> dict[str, Any]:
    """Return a deterministic staged learning record for one feedback event."""

    event_id = _text(event.get("event_id"))
    feedback_type = _text(event.get("feedback_type"))
    status = _text(event.get("consumption_status")).upper()
    categories = _event_categories(event)
    explicit_owner = _text(event.get("source")) in _OWNER_SOURCES
    explicit_activation = (
        _text(event.get("owner_rule_activation")).upper() == "EXPLICIT"
        or any(token in feedback_type for token in _EXPLICIT_RULE_TYPE_TOKENS)
    )
    candidate_only = feedback_type in _CANDIDATE_ONLY_TYPES
    hypothesis = status == "HYPOTHESIS_ONLY" or "hypothesis" in feedback_type
    rule = _rule_text(event)
    rule_family, rule_direction = _rule_family_and_direction(rule)
    semantic_tokens = sorted(
        _rule_semantic_tokens(
            " ".join(
                [
                    _text(event.get("title")),
                    rule,
                    " ".join(_string_list(event.get("applies_to"))),
                ]
            )
        )
    )

    if not event_id or not feedback_type:
        stage = "REJECTED_INVALID"
        active = False
        reason = "missing_event_id_or_type"
    elif candidate_only:
        stage = "CLASSIFIED_EXAMPLE"
        active = False
        reason = "candidate_specific_feedback_is_not_generalized"
        if not rule:
            rule = _text(event.get("title")) or _text(event.get("owner_decision"))
    elif not rule:
        stage = "REJECTED_INVALID"
        active = False
        reason = "missing_owner_rule_text"
    elif hypothesis:
        stage = "LEARNING_CANDIDATE"
        active = False
        reason = "owner_marked_hypothesis_requires_later_confirmation"
    elif explicit_owner and explicit_activation and status in _ACTIVE_STATUSES and categories:
        stage = "ACTIVE_OWNER_RULE"
        active = True
        reason = "explicit_owner_direction_active_without_performance_claim"
    else:
        stage = "CLASSIFIED_PENDING"
        active = False
        reason = "not_eligible_for_automatic_owner_rule_activation"

    fingerprint_source = json.dumps(
        {"categories": categories, "rule": rule.casefold(), "type": feedback_type},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "learning_id": event_id,
        "sequence": int(sequence),
        "recorded_at": _text(event.get("recorded_at")),
        "feedback_type": feedback_type,
        "owner_decision": _text(event.get("owner_decision")),
        "title": _text(event.get("title"))[:300],
        "categories": categories,
        "applies_to": _string_list(event.get("applies_to")),
        "rule": rule,
        "rule_family": rule_family,
        "rule_direction": rule_direction,
        "semantic_tokens": semantic_tokens,
        "stage": stage,
        "active": active,
        "stage_reason": reason,
        "is_performance_evidence": event.get("is_performance_evidence") is True,
        "supersedes_event_id": _text(event.get("supersedes_event_id")) or None,
        "fingerprint": hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest(),
    }


def _load_feedback_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"feedback_read_failed:{exc.__class__.__name__}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"invalid_json_line:{line_number}")
            continue
        if isinstance(payload, dict):
            rows.append(payload)
        else:
            errors.append(f"non_object_line:{line_number}")
    return rows, errors


def build_owner_learning_index(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    records = [classify_feedback_event(row, sequence=index) for index, row in enumerate(rows, start=1)]
    by_id = {record["learning_id"]: record for record in records if record["learning_id"]}

    for record in records:
        target = record.get("supersedes_event_id")
        if target and target in by_id:
            by_id[target]["active"] = False
            by_id[target]["stage"] = "SUPERSEDED"
            by_id[target]["stage_reason"] = f"superseded_by:{record['learning_id']}"

    # Exact duplicate active rules keep the newest owner statement only.
    newest_by_fingerprint: dict[str, dict[str, Any]] = {}
    for record in records:
        if not record["active"]:
            continue
        prior = newest_by_fingerprint.get(record["fingerprint"])
        if prior is not None:
            prior["active"] = False
            prior["stage"] = "SUPERSEDED_DUPLICATE"
            prior["stage_reason"] = f"duplicate_replaced_by:{record['learning_id']}"
        newest_by_fingerprint[record["fingerprint"]] = record

    semantic_duplicate_count = 0
    active_records = [record for record in records if record["active"]]
    for index, current in enumerate(active_records):
        if not current["active"]:
            continue
        for prior in active_records[:index]:
            if not prior["active"]:
                continue
            if _semantic_duplicate(prior, current):
                prior["active"] = False
                prior["stage"] = "SUPERSEDED_SEMANTIC_DUPLICATE"
                prior["stage_reason"] = f"semantic_duplicate_replaced_by:{current['learning_id']}"
                semantic_duplicate_count += 1

    conflict_resolved_count = 0
    for category in EXECUTION_CATEGORIES:
        scoped = [
            record
            for record in records
            if record["active"]
            and category in record["categories"]
            and record.get("rule_family") == "slide_count"
            and record.get("rule_direction") in {"variable", "fixed"}
        ]
        if not scoped:
            continue
        winner = max(scoped, key=lambda record: int(record.get("sequence") or 0))
        for record in scoped:
            if record is winner or record.get("rule_direction") == winner.get("rule_direction"):
                continue
            record["active"] = False
            record["stage"] = "SUPERSEDED_CONFLICT"
            record["stage_reason"] = (
                f"conflict:{category}:slide_count:{record.get('rule_direction')}"
                f"_replaced_by_{winner.get('rule_direction')}:{winner['learning_id']}"
            )
            conflict_resolved_count += 1

    categories = {
        category: [
            record["learning_id"]
            for record in records
            if record["active"] and category in record["categories"]
        ]
        for category in EXECUTION_CATEGORIES
    }
    stage_counts: dict[str, int] = {}
    for record in records:
        stage_counts[record["stage"]] = stage_counts.get(record["stage"], 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "learning_boundary": {
            "owner_rules_are_performance_evidence": False,
            "automatic_performance_promotion_allowed": False,
            "explicit_owner_directions_may_activate": True,
        },
        "stats": {
            "feedback_event_count": len(records),
            "active_owner_rule_count": sum(1 for record in records if record["active"]),
            "stage_counts": stage_counts,
            "semantic_duplicate_count": semantic_duplicate_count,
            "conflict_resolved_count": conflict_resolved_count,
        },
        "categories": categories,
        "records": records,
    }


def _source_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def ensure_owner_learning_index(
    *,
    feedback_path: str | Path | None = None,
    index_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load the compact index, rebuilding it only when the feedback log changed."""

    feedback = Path(feedback_path) if feedback_path is not None else DEFAULT_FEEDBACK_PATH
    index = Path(index_path) if index_path is not None else DEFAULT_INDEX_PATH
    digest = _source_digest(feedback)
    try:
        cached = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cached = {}
    if (
        isinstance(cached, dict)
        and cached.get("schema_version") == SCHEMA_VERSION
        and cached.get("source_sha256") == digest
    ):
        cached["feedback_log_reloaded"] = False
        return cached

    rows, errors = _load_feedback_rows(feedback)
    payload = build_owner_learning_index(rows)
    payload["source"] = str(feedback)
    payload["source_sha256"] = digest
    payload["errors"] = errors
    payload["feedback_log_reloaded"] = True
    if digest:
        _atomic_write_json(index, payload)
    return payload


def append_owner_feedback_event(
    event: Mapping[str, Any],
    *,
    feedback_path: str | Path | None = None,
    index_path: str | Path | None = None,
) -> dict[str, Any]:
    """Append one explicit owner event and immediately refresh the learning index."""

    feedback = Path(feedback_path) if feedback_path is not None else DEFAULT_FEEDBACK_PATH
    required = (
        "event_id", "recorded_at", "source", "feedback_type", "owner_decision",
        "owner_reason", "applies_to", "is_performance_evidence", "consumption_status",
    )
    missing = [key for key in required if key not in event]
    if missing:
        raise ValueError("missing owner feedback fields: " + ", ".join(missing))
    event_id = _text(event.get("event_id"))
    if not event_id:
        raise ValueError("event_id must be a non-empty string")
    rows, errors = _load_feedback_rows(feedback) if feedback.exists() else ([], [])
    if errors:
        raise ValueError("owner feedback log is invalid: " + ", ".join(errors))
    if any(_text(row.get("event_id")) == event_id for row in rows):
        raise ValueError(f"duplicate owner feedback event_id: {event_id}")
    feedback.parent.mkdir(parents=True, exist_ok=True)
    with feedback.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(dict(event), ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return ensure_owner_learning_index(feedback_path=feedback, index_path=index_path)


def append_owner_review_feedback(
    payload: Mapping[str, Any],
    *,
    execution_context: Mapping[str, Any] | None = None,
    result_receipt: Mapping[str, Any] | None = None,
    feedback_path: str | Path | None = None,
    index_path: str | Path | None = None,
) -> dict[str, Any]:
    """Normalize, append, and return the exact learning receipt for an owner review."""

    event = normalize_owner_review_event(
        payload, execution_context=execution_context, result_receipt=result_receipt
    )
    index = append_owner_feedback_event(
        event, feedback_path=feedback_path, index_path=index_path
    )
    record = next(
        (item for item in index.get("records", []) if item.get("learning_id") == event["event_id"]),
        None,
    )
    return {
        "event": event,
        "learning_record": record,
        "index_receipt": {
            "source_sha256": index.get("source_sha256", ""),
            "feedback_event_count": index.get("stats", {}).get("feedback_event_count", 0),
            "active_owner_rule_count": index.get("stats", {}).get("active_owner_rule_count", 0),
        },
    }


def _tokens(value: Any) -> set[str]:
    return {token.casefold() for token in _TOKEN_RE.findall(str(value or ""))}


def select_category_learning(
    category: str,
    context: Mapping[str, Any] | None = None,
    *,
    limit: int = 5,
    feedback_path: str | Path | None = None,
    index_path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return the most relevant 3-5 active owner rules for one category."""

    normalized = _text(category).lower()
    payload = ensure_owner_learning_index(feedback_path=feedback_path, index_path=index_path)
    records = {
        record.get("learning_id"): record
        for record in payload.get("records", [])
        if isinstance(record, dict)
    }
    ids = payload.get("categories", {}).get(normalized, [])
    context_tokens = _tokens(json.dumps(context or {}, ensure_ascii=False))
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for learning_id in ids:
        record = records.get(learning_id)
        if not record or not record.get("active"):
            continue
        overlap = len(context_tokens & _tokens(" ".join([
            _text(record.get("title")),
            _text(record.get("rule")),
            " ".join(_string_list(record.get("applies_to"))),
        ])))
        hard = 2 if "hard" in _text(record.get("feedback_type")) or "금지/고정:" in _text(record.get("rule")) else 0
        correction = 1 if any(token in _text(record.get("feedback_type")) for token in ("correction", "rejection")) else 0
        ranked.append((overlap * 5 + hard + correction, int(record.get("sequence") or 0), record))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = [
        {
            "learning_id": record["learning_id"],
            "title": record["title"],
            "rule": record["rule"],
            "feedback_type": record["feedback_type"],
            "stage": record["stage"],
        }
        for _, _, record in ranked[: max(0, min(int(limit), 5))]
    ]
    receipt = {
        "feedback_event_count": payload.get("stats", {}).get("feedback_event_count", 0),
        "active_owner_rule_count": payload.get("stats", {}).get("active_owner_rule_count", 0),
        "feedback_log_reloaded": payload.get("feedback_log_reloaded") is True,
        "source_sha256": payload.get("source_sha256", ""),
        "selected_learning_ids": [item["learning_id"] for item in selected],
    }
    return selected, receipt


__all__ = [
    "DEFAULT_FEEDBACK_PATH",
    "DEFAULT_INDEX_PATH",
    "SCHEMA_VERSION",
    "build_owner_learning_index",
    "classify_feedback_event",
    "ensure_owner_learning_index",
    "append_owner_feedback_event",
    "append_owner_review_feedback",
    "normalize_owner_review_event",
    "select_category_learning",
]
