"""Build a compact, auditable prompt pack for one category job.

The pack reads the already-adapted category asset and a bounded set of durable
owner directives.  It never reloads the Agency Agents upstream repository or
the full owner-feedback log during dispatch.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from modules.agent_console.category_prompt_loader import build_category_prompt
from modules.agent_console.contracts import sanitize_json
from modules.agent_console.owner_feedback_learning import select_category_learning


SCHEMA_VERSION = "agent_execution_prompt_pack_v1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIRECTIVES_PATH = REPOSITORY_ROOT / "knowledge" / "owner_directives" / "cardnews_owner_directives.json"

COMMON_ABSOLUTE_RULES = (
    "게시·링크 발급·Git·자동화 재개 금지",
    "현재 후보와 제공 출처만 사용하고 사실·성과·사용 경험을 만들지 않기",
    "가변 슬라이드와 별도 피드 본문을 전제로 하며 생성·재연 매체는 표시하기",
    "결과는 짧은 JSON 인계로 반환하고 공용 상태문서·코드를 수정하지 않기",
)

CATEGORY_DIRECTIVE_IDS = {
    "news": ("OD-CARD-010", "OD-CARD-011", "OD-CARD-012", "OD-CARD-013", "OD-CARD-016"),
    "story": ("OD-CARD-002", "OD-CARD-003", "OD-CARD-008", "OD-CARD-012", "OD-CARD-016"),
    "fashion": ("OD-CARD-004", "OD-CARD-005", "OD-CARD-006", "OD-CARD-009", "OD-CARD-011"),
    "beauty": ("OD-CARD-001", "OD-CARD-004", "OD-CARD-011", "OD-CARD-013", "OD-CARD-016"),
}

# These are production invariants, not relevance-ranked memories.  They must be
# supplied to every CardNews production job even when the compact learning
# search selects different category-specific feedback.
PRODUCTION_HARD_DIRECTIVE_IDS = (
    "OD-CARD-017",
    "OD-CARD-018",
    "OD-CARD-019",
    "OD-CARD-020",
)

_CONTEXT_FIELDS = (
    "source", "request_id", "candidate_id", "grade", "account", "category", "title",
    "source_urls", "requested_media", "execution_enabled", "network_executed",
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _compact_list(value: Any, *, limit: int, item_limit: int = 500) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_text(item)[:item_limit] for item in value if _text(item)][:limit]


def compact_candidate_context(context: Any) -> dict[str, Any]:
    source = sanitize_json(context) if isinstance(context, Mapping) else {}
    compact: dict[str, Any] = {}
    for key in _CONTEXT_FIELDS:
        if key not in source:
            continue
        value = source[key]
        if key == "source_urls":
            compact[key] = _compact_list(value, limit=3, item_limit=1000)
        elif key == "requested_media":
            compact[key] = _compact_list(value, limit=6, item_limit=120)
        elif isinstance(value, str):
            compact[key] = value[:1000]
        else:
            compact[key] = value
    return compact


def select_owner_learning(
    category: str,
    *,
    directives_path: str | Path | None = None,
    limit: int = 5,
) -> list[dict[str, str]]:
    path = Path(directives_path) if directives_path is not None else DEFAULT_DIRECTIVES_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    allowed = CATEGORY_DIRECTIVE_IDS.get(str(category or "").strip().lower(), ())
    by_id = {
        _text(item.get("claim_id")): item
        for item in payload.get("directives", [])
        if isinstance(item, Mapping) and item.get("owner_approved") is True
    }
    selected = []
    for claim_id in allowed[: max(0, min(int(limit), 5))]:
        item = by_id.get(claim_id)
        if not item:
            continue
        selected.append({
            "claim_id": claim_id,
            "title": _text(item.get("title"))[:120],
            "rule": _text(item.get("rule"))[:500],
        })
    return selected


def select_production_hard_rules(
    *,
    directives_path: str | Path | None = None,
) -> list[dict[str, str]]:
    path = Path(directives_path) if directives_path is not None else DEFAULT_DIRECTIVES_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    by_id = {
        _text(item.get("claim_id")): item
        for item in payload.get("directives", [])
        if isinstance(item, Mapping) and item.get("owner_approved") is True
    }
    return [
        {
            "claim_id": claim_id,
            "title": _text(by_id[claim_id].get("title"))[:120],
            "rule": _text(by_id[claim_id].get("rule"))[:500],
        }
        for claim_id in PRODUCTION_HARD_DIRECTIVE_IDS
        if claim_id in by_id
    ]


def build_execution_prompt_pack(job: Mapping[str, Any], context: Any) -> dict[str, Any]:
    category = _text(job.get("category")).lower()
    current_candidate = compact_candidate_context(context)
    dynamic_learning, learning_receipt = select_category_learning(category, current_candidate, limit=5)
    # Keep two core owner directives and add the three most relevant newer
    # learned rules.  This preserves the manually curated baseline while
    # allowing feedback after that snapshot to change future execution.
    curated_learning = select_owner_learning(category, limit=2)
    learning = (curated_learning + dynamic_learning[:3])[:5]
    if not learning:
        learning = select_owner_learning(category)
    hard_rules = select_production_hard_rules()
    pack = {
        "schema_version": SCHEMA_VERSION,
        "common_absolute_rules": list(COMMON_ABSOLUTE_RULES),
        "production_hard_rules": hard_rules,
        "category_education": build_category_prompt(category),
        "current_candidate": current_candidate,
        "past_owner_learning": learning,
        "deferred_tool_assignment": {
            "assigned_tools": list(job.get("requested_tools", [])),
            "assignment_receipt": sanitize_json(job.get("tool_assignment", {})),
            "tools_are_not_evidence_until_used": True,
            "publishing_tools_allowed": False,
        },
        "source_policy": {
            "agency_agents_upstream_reloaded": False,
            "adapted_category_asset_used": True,
            "full_feedback_log_reloaded": False,
            "compact_owner_learning_index_used": bool(dynamic_learning),
        },
    }
    canonical = json.dumps(pack, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    pack["education_receipt"] = {
        "category": category,
        "owner_learning_ids": [
            item.get("learning_id") or item.get("claim_id")
            for item in learning
            if item.get("learning_id") or item.get("claim_id")
        ],
        "owner_learning_count": len(learning),
        "production_hard_rule_ids": [item["claim_id"] for item in hard_rules],
        "production_hard_rule_count": len(hard_rules),
        "production_hard_rules_complete": tuple(item["claim_id"] for item in hard_rules)
        == PRODUCTION_HARD_DIRECTIVE_IDS,
        "owner_feedback_event_count": learning_receipt.get("feedback_event_count", 0),
        "active_owner_rule_count": learning_receipt.get("active_owner_rule_count", 0),
        "owner_learning_source_sha256": learning_receipt.get("source_sha256", ""),
        "prompt_pack_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "assigned_tool_ids": list(job.get("requested_tools", [])),
    }
    return pack


__all__ = [
    "build_execution_prompt_pack",
    "compact_candidate_context",
    "select_owner_learning",
    "COMMON_ABSOLUTE_RULES",
    "CATEGORY_DIRECTIVE_IDS",
    "PRODUCTION_HARD_DIRECTIVE_IDS",
    "select_production_hard_rules",
    "SCHEMA_VERSION",
]
