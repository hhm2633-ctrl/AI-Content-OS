"""Validate and merge incremental relation/story shards into candidate briefs.

This integration layer is local and read-only. It accepts one category shard at
a time, validates it before ingestion, preserves an optional prior engine state,
and attaches only supplied story data to already-matched product IDs.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping

from modules.brandconnect.incremental_commerce_story_engine import (
    build_candidate_story_briefs,
    ingest_relation_shard,
    iter_jsonl_file,
    new_engine_state,
)
from modules.brandconnect.relation_story_shard_validator import (
    validate_relation_story_shard,
)


SCHEMA_VERSION = "commerce_story_integration.v1"


def _load_report(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def merge_commerce_story_shards(
    candidates: Any,
    shard_specs: Iterable[Mapping[str, Any]],
    state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Validate available shards, merge accepted rows, and build story briefs."""

    engine_state = state if isinstance(state, dict) else new_engine_state()
    shard_results = []
    accepted_shards = 0
    rejected_shards = 0

    for raw_spec in shard_specs if shard_specs is not None else []:
        if not isinstance(raw_spec, Mapping):
            rejected_shards += 1
            shard_results.append({"status": "rejected_invalid_spec"})
            continue
        shard_id = str(raw_spec.get("shard_id") or "").strip()
        category = str(raw_spec.get("category") or "").strip()
        shard_path = str(raw_spec.get("shard_path") or "").strip()
        report_path = str(raw_spec.get("report_path") or "").strip()
        validation = validate_relation_story_shard(
            shard_path=shard_path,
            report_path=report_path,
        )
        if not shard_id or not category or validation.get("valid") is not True:
            rejected_shards += 1
            shard_results.append(
                {
                    "shard_id": shard_id,
                    "category": category,
                    "status": "rejected_validation",
                    "validation": validation,
                }
            )
            continue

        ingestion = ingest_relation_shard(
            engine_state,
            shard_id,
            category,
            iter_jsonl_file(shard_path),
            _load_report(report_path),
        )
        if ingestion.get("status") in {"completed", "already_completed"}:
            accepted_shards += 1
        else:
            rejected_shards += 1
        shard_results.append(
            {
                "shard_id": shard_id,
                "category": category,
                "status": ingestion.get("status"),
                "validation": {
                    "status": validation.get("status"),
                    "valid": validation.get("valid"),
                    "metrics": deepcopy(validation.get("metrics", {})),
                },
                "ingestion": ingestion,
            }
        )

    briefs = build_candidate_story_briefs(engine_state, candidates)
    status = "completed" if accepted_shards and not rejected_shards else (
        "partial" if accepted_shards else "closed"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "accepted_shards": accepted_shards,
        "rejected_shards": rejected_shards,
        "unique_product_count": len(engine_state.get("products", {})),
        "shards": shard_results,
        "story_briefs": briefs,
        "engine_state": engine_state,
        "network_used": False,
        "link_issuance": False,
        "publishing": False,
    }


__all__ = ["merge_commerce_story_shards", "SCHEMA_VERSION"]
