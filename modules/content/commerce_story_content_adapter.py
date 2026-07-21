"""Adapt commerce story briefs into content-adapter inputs for card copy + captions.

This adapter is intentionally small and non-destructive:
- it only converts brief payloads that are already marked ready,
- keeps absent briefs non-blocking,
- preserves supplied short-story fields when already under 30 chars,
- and does not invent personal-use/price/stock/review claims.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping, Tuple

SCHEMA_VERSION = "commerce_story_content_adapter_v1"
EXPECTED_STORY_BRIEF_SCHEMA = "candidate_commerce_story_briefs.v1"
MAX_SHORT_STORY_LEN = 29

_FORBIDDEN_BLOG_SEED_KEYS = {
    "delivery",
    "discount",
    "discount_rate",
    "inventory",
    "personal_use",
    "purchase_claim",
    "purchase_count",
    "price",
    "rank",
    "ranking",
    "rating",
    "sales_count",
    "shipping",
    "stock",
    "stock_status",
    "review_count",
    "review_score",
    "reviews",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_list(value: Any) -> List[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _short_story(value: Any) -> str:
    story = _text(value)
    if len(story) > MAX_SHORT_STORY_LEN:
        return story[:MAX_SHORT_STORY_LEN].strip()
    return story


def _clean_blog_seed(value: Any) -> Any:
    if isinstance(value, list):
        return [_clean_blog_seed(entry) for entry in value]
    if not isinstance(value, Mapping):
        return deepcopy(value)
    return {
        key: _clean_blog_seed(entry)
        for key, entry in value.items()
        if not isinstance(key, str) or key.casefold() not in _FORBIDDEN_BLOG_SEED_KEYS
    }


def _product_key(brief: Mapping[str, Any]) -> Tuple[str, str]:
    product_id = _text(brief.get("product_id"))
    if product_id:
        return ("product_id", product_id)
    product_name = _text(brief.get("product_name"))
    if product_name:
        return ("product_name", " ".join(product_name.casefold().split()))
    return ("short_story", _short_story(brief.get("short_story")).casefold())


def _stable_unique_text(values: Any) -> List[Any]:
    if not isinstance(values, list):
        return []
    unique: List[Any] = []
    seen = set()
    for value in values:
        marker = (type(value).__name__, repr(value))
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(deepcopy(value))
    return unique


def _coalesce_candidates(candidates: List[Mapping[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """Merge repeated candidate rows without changing first-seen candidate/brief order."""

    merged: List[Dict[str, Any]] = []
    by_id: Dict[str, Dict[str, Any]] = {}
    duplicate_count = 0
    for candidate in candidates:
        candidate_id = _text(candidate.get("candidate_id") or candidate.get("id"))
        if not candidate_id:
            merged.append(dict(candidate))
            continue

        current = by_id.get(candidate_id)
        if current is None:
            current = dict(candidate)
            current["candidate_id"] = candidate_id
            current["briefs"] = (
                list(_as_list(candidate.get("briefs")))
                if _text(candidate.get("status")) == "ready"
                else []
            )
            current["missing_products"] = _stable_unique_text(candidate.get("missing_products"))
            by_id[candidate_id] = current
            merged.append(current)
            continue

        duplicate_count += 1
        if not _text(current.get("title")):
            current["title"] = _text(candidate.get("title"))
        if _text(candidate.get("status")) == "ready":
            current["status"] = "ready"
            current["briefs"].extend(_as_list(candidate.get("briefs")))
        current["missing_products"] = _stable_unique_text(
            list(current.get("missing_products") or [])
            + list(candidate.get("missing_products") or [])
        )
    return merged, duplicate_count


def _brief_trace(brief: Mapping[str, Any], candidate_id: str, candidate_title: str) -> Dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "candidate_title": candidate_title,
        "product_id": _text(brief.get("product_id")),
        "product_name": _text(brief.get("product_name")),
        "category": _text(brief.get("category")),
        "source_shard": _text(brief.get("source_shard")),
        "row_index": brief.get("row_index"),
        "relation_reason": _text(brief.get("relation_reason")),
    }


def _candidate_entry(
    candidate: Mapping[str, Any],
    *,
    candidate_id: str,
    candidate_title: str,
) -> Dict[str, Any]:
    briefs = _as_list(candidate.get("briefs"))
    status = _text(candidate.get("status"))
    if status != "ready" or not briefs:
        return {
            "candidate_id": candidate_id,
            "candidate_title": candidate_title,
            "status": status or "awaiting_briefs",
            "content_inputs": [],
            "missing_products": list(candidate.get("missing_products") or []),
        }

    content_inputs = []
    seen_products = set()
    duplicate_product_count = 0
    for brief in briefs:
        short_story = _short_story(brief.get("short_story"))
        if not short_story:
            continue

        product_key = _product_key(brief)
        if product_key in seen_products:
            duplicate_product_count += 1
            continue
        seen_products.add(product_key)

        card_copy = {
            "short_story": short_story,
            "practical_topic": _text(brief.get("practical_topic")),
            "product_name": _text(brief.get("product_name")),
            "product_role": _text(brief.get("product_role")),
            "season_context": _text(brief.get("season_context")),
        }
        product_name = _text(brief.get("product_name"))
        feed_caption = f"{product_name} - {short_story}" if product_name else short_story
        content_inputs.append(
            {
                "traceability": _brief_trace(brief, candidate_id, candidate_title),
                "card_copy": card_copy,
                "feed_caption": feed_caption,
                "future_blog_seed": _clean_blog_seed(brief.get("blog_seed")),
            }
        )

    return {
        "candidate_id": candidate_id,
        "candidate_title": candidate_title,
        "status": "ready" if content_inputs else "awaiting_briefs",
        "content_inputs": content_inputs,
        "missing_products": _stable_unique_text(candidate.get("missing_products")),
        "duplicate_product_count": duplicate_product_count,
    }


def build_commerce_story_content_inputs(story_briefs: Any) -> Dict[str, Any]:
    if not isinstance(story_briefs, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "reason_code": "malformed_story_briefs",
            "content_candidates": [],
            "network_used": False,
            "link_issuance": False,
            "publishing": False,
        }

    candidates, duplicate_candidate_count = _coalesce_candidates(
        _as_list(story_briefs.get("candidates"))
    )
    content_candidates = []
    skipped_candidates = 0
    for candidate in candidates:
        candidate_id = _text(candidate.get("candidate_id") or candidate.get("id"))
        if not candidate_id:
            skipped_candidates += 1
            continue
        candidate_title = _text(candidate.get("title"))
        content_candidates.append(
            _candidate_entry(
                candidate,
                candidate_id=candidate_id,
                candidate_title=candidate_title,
            )
        )

    ready_count = sum(
        1 for entry in content_candidates if entry.get("status") == "ready" and entry.get("content_inputs")
    )
    blocked_count = skipped_candidates

    if not content_candidates and _text(story_briefs.get("schema_version")):
        global_status = "no_candidates"
    elif ready_count and all(
        entry.get("status") == "ready" for entry in content_candidates
    ):
        global_status = "ready"
    elif ready_count:
        global_status = "partial"
    else:
        global_status = "awaiting_briefs"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": global_status,
        "input_schema_version": _text(story_briefs.get("schema_version")),
        "expected_input_schema_version": EXPECTED_STORY_BRIEF_SCHEMA,
        "input_ready": ready_count,
        "candidate_count": len(content_candidates),
        "blocked_candidate_count": blocked_count,
        "duplicate_candidate_count": duplicate_candidate_count,
        "duplicate_product_count": sum(
            int(entry.get("duplicate_product_count") or 0) for entry in content_candidates
        ),
        "content_candidates": content_candidates,
        "network_used": False,
        "link_issuance": False,
        "publishing": False,
    }


def run_commerce_story_content_adapter(story_briefs: Any) -> Dict[str, Any]:
    return build_commerce_story_content_inputs(story_briefs)


__all__ = [
    "build_commerce_story_content_inputs",
    "run_commerce_story_content_adapter",
    "SCHEMA_VERSION",
]
