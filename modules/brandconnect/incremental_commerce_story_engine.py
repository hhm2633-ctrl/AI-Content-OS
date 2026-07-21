"""Incremental shard consumer turning relation/story rows into commerce story briefs.

Shards arrive one category at a time (beauty/lifestyle now, fashion later).
Completed shards are never reprocessed; late shards merge into the same state
without touching earlier categories. Rows are streamed one line at a time —
callers never need to load a whole JSONL file. Every brief field is copied from
supplied rows; nothing (price, stock, review, personal use, links) is invented.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional

ENGINE_SCHEMA_VERSION = "incremental_commerce_story_engine.v1"
BRIEF_SCHEMA_VERSION = "candidate_commerce_story_briefs.v1"
PROPOSAL_STATUS = "future_blog_seeds_not_publish_drafts"
_UNIQUENESS_SUFFIX_PATTERN = re.compile(r"·\d+$")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _display_story(value: Any) -> str:
    """Remove generator-only uniqueness suffixes from reader-facing copy."""

    return _UNIQUENESS_SUFFIX_PATTERN.sub("", _text(value)).rstrip()


def iter_jsonl_file(path: str) -> Iterator[Any]:
    """Stream one JSONL row at a time; parse failures yield the raw line."""

    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                yield line


def new_engine_state() -> Dict[str, Any]:
    return {
        "schema_version": ENGINE_SCHEMA_VERSION,
        "shards": {},
        "products": {},
    }


def _normalize_story_row(raw: Mapping[str, Any], category: str, shard_id: str, index: int) -> Optional[Dict[str, Any]]:
    product_id = _text(str(raw.get("product_id", "")))
    product_name = _text(raw.get("product_name"))
    if not product_id or not product_name:
        return None

    season_context = raw.get("season_context")
    relation_reason = ""
    relation_reason_source = "missing"
    if isinstance(season_context, Mapping):
        relation_reason = _text(season_context.get("relation_reason"))
        if relation_reason:
            relation_reason_source = "explicit"
        else:
            selection_basis = _text(season_context.get("selection_basis"))
            if selection_basis:
                relation_reason = selection_basis
                relation_reason_source = "selection_basis"
        season_text = _text(season_context.get("best_context")) or " · ".join(
            part
            for part in (
                _text(season_context.get("season")),
                _text(season_context.get("weather")),
                _text(season_context.get("daily_environment")),
            )
            if part
        )
    else:
        season_text = _text(season_context)
    if not relation_reason:
        product_role = _text(raw.get("product_role"))
        if product_role:
            relation_reason = product_role
            relation_reason_source = "product_role"

    confidence = raw.get("confidence")
    return {
        "product_id": product_id,
        "product_name": product_name,
        "category": category,
        "source_shard": shard_id,
        "row_index": index,
        "season_context": season_text,
        "relation_reason": relation_reason,
        "relation_reason_source": relation_reason_source,
        "practical_topic": _text(raw.get("practical_topic")),
        "short_story": _display_story(raw.get("short_story")),
        "product_role": _text(raw.get("product_role")),
        "derived_terms": [
            _text(term)
            for term in raw.get("derived_terms", [])
            if _text(term)
        ] if isinstance(raw.get("derived_terms"), (list, tuple)) else [],
        "blog_seed": deepcopy(raw.get("blog_seed")),
        "confidence": float(confidence) if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) else None,
        "fallback_used": raw.get("fallback_used") is True,
    }


def ingest_relation_shard(
    state: Dict[str, Any],
    shard_id: str,
    category: str,
    rows: Iterable[Any],
    report: Any = None,
) -> Dict[str, Any]:
    """Consume one category shard incrementally; completed shards are skipped."""

    shard_id = _text(shard_id)
    category = _text(category).lower()
    if not shard_id or not category:
        return {"shard_id": shard_id, "status": "rejected_invalid_shard", "accepted": 0, "dropped": []}

    existing = state["shards"].get(shard_id)
    if existing and existing.get("status") == "completed":
        return {
            "shard_id": shard_id,
            "status": "already_completed",
            "accepted": 0,
            "dropped": [],
            "row_count": existing.get("row_count", 0),
        }

    report_invalid = False
    if isinstance(report, Mapping):
        validation = report.get("validation")
        report_invalid = report.get("valid") is False or (
            isinstance(validation, Mapping)
            and any(value is False for value in validation.values())
        )
    if report_invalid:
        state["shards"][shard_id] = {"category": category, "status": "rejected_invalid_report", "row_count": 0}
        return {"shard_id": shard_id, "status": "rejected_invalid_report", "accepted": 0, "dropped": []}

    accepted = 0
    duplicates = 0
    dropped: List[Dict[str, Any]] = []
    row_count = 0
    for index, raw in enumerate(rows):
        row_count += 1
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError:
                dropped.append({"row_index": index, "reason": "invalid_json"})
                continue
        if not isinstance(raw, Mapping):
            dropped.append({"row_index": index, "reason": "malformed_row"})
            continue
        normalized = _normalize_story_row(raw, category, shard_id, index)
        if normalized is None:
            dropped.append({"row_index": index, "reason": "missing_product_id_or_name"})
            continue
        if normalized["product_id"] in state["products"]:
            duplicates += 1
            continue
        state["products"][normalized["product_id"]] = normalized
        accepted += 1

    report_count = None
    if isinstance(report, Mapping):
        for field in ("product_count", "output_row_count", "story_count"):
            if isinstance(report.get(field), int):
                report_count = report[field]
                break
    shard_record = {
        "category": category,
        "status": "completed",
        "row_count": row_count,
        "accepted": accepted,
        "duplicates": duplicates,
        "dropped_count": len(dropped),
        "report_product_count": report_count,
        "report_count_match": (report_count == row_count) if isinstance(report_count, int) else None,
    }
    state["shards"][shard_id] = shard_record
    return {"shard_id": shard_id, "status": "completed", "accepted": accepted, "dropped": dropped, **{
        "row_count": row_count, "duplicates": duplicates, "report_count_match": shard_record["report_count_match"],
    }}


def ingested_categories(state: Mapping[str, Any]) -> List[str]:
    return sorted(
        {
            shard.get("category", "")
            for shard in state.get("shards", {}).values()
            if shard.get("status") == "completed" and shard.get("category")
        }
    )


def build_candidate_story_briefs(state: Mapping[str, Any], candidates: Any) -> Dict[str, Any]:
    """Attach supplied story rows to candidate product matches; never invent."""

    products = state.get("products", {}) if isinstance(state, Mapping) else {}
    results = []
    for candidate in candidates if isinstance(candidates, list) else []:
        if not isinstance(candidate, Mapping):
            continue
        candidate_id = _text(str(candidate.get("candidate_id", "") or candidate.get("id", "")))
        if not candidate_id:
            continue
        briefs: List[Dict[str, Any]] = []
        missing: List[str] = []
        for match in candidate.get("matches") if isinstance(candidate.get("matches"), list) else []:
            if not isinstance(match, Mapping):
                continue
            product_id = _text(str(match.get("product_id", "")))
            if not product_id:
                continue
            story = products.get(product_id)
            if story is None:
                missing.append(product_id)
                continue
            briefs.append(
                {
                    "product_id": story["product_id"],
                    "product_name": story["product_name"],
                    "relation_reason": story["relation_reason"],
                    "relation_reason_source": story["relation_reason_source"],
                    "season_context": story["season_context"],
                    "practical_topic": story["practical_topic"],
                    "short_story": story["short_story"],
                    "product_role": story["product_role"],
                    "blog_seed": deepcopy(story["blog_seed"]),
                    "category": story["category"],
                    "source_shard": story["source_shard"],
                    "row_index": story["row_index"],
                    "confidence": story["confidence"],
                    "fallback_used": story["fallback_used"],
                    "link_issued": False,
                }
            )
        results.append(
            {
                "candidate_id": candidate_id,
                "title": _text(candidate.get("title")),
                "status": "ready" if briefs else ("awaiting_shards" if missing else "no_matched_products"),
                "briefs": briefs,
                "missing_products": missing,
            }
        )

    return {
        "schema_version": BRIEF_SCHEMA_VERSION,
        "proposal_status": PROPOSAL_STATUS,
        "ingested_categories": ingested_categories(state),
        "candidates": results,
        "network_used": False,
        "link_issuance": False,
        "publishing": False,
    }


__all__ = [
    "new_engine_state",
    "ingest_relation_shard",
    "build_candidate_story_briefs",
    "ingested_categories",
    "iter_jsonl_file",
    "ENGINE_SCHEMA_VERSION",
    "BRIEF_SCHEMA_VERSION",
    "PROPOSAL_STATUS",
]
