"""Replay the candidate queue through commerce matching and automatic selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.brandconnect.brandconnect_product_catalog import normalize_brandconnect_catalog
from modules.brandconnect.brandconnect_second_stage import run_brandconnect_second_stage
from modules.brandconnect.catalog_function_relation_builder import build_catalog_function_relations
from modules.brandconnect.incremental_commerce_story_engine import (
    build_candidate_story_briefs,
    ingest_relation_shard,
    new_engine_state,
)
from modules.source_intake.owner_ranked_final_candidate_selector import select_owner_ranked_final_candidates


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_production_handoff(selection: Mapping[str, Any]) -> Dict[str, Any]:
    candidates = []
    accounts = selection.get("accounts")
    accounts = accounts if isinstance(accounts, Mapping) else {}
    for account in ("A", "B", "C"):
        bucket = accounts.get(account)
        bucket = bucket if isinstance(bucket, Mapping) else {}
        for item in bucket.get("selected", []):
            if not isinstance(item, Mapping):
                continue
            candidates.append(
                {
                    **dict(item),
                    "selection_authority": "automatic_policy",
                    "owner_grade_consumed": item.get("grade") is not None,
                }
            )
    return {
        "schema_version": "cardnews_automatic_production_handoff_v1",
        "status": "ready" if candidates else "empty",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "owner_grade_required": False,
        "owner_feedback_optional": True,
        "automatic_selection_is_not_owner_approval": True,
        "owner_approval_required_at": "pre_upload_manual_upload_ready",
        "manual_upload_ready": False,
        "actual_publish": False,
        "upload_executed": False,
    }


def execute(
    *,
    repository_root: Path,
    queue_path: Path,
    catalog_path: Path,
    console_root: Path,
    output_path: Path,
) -> Dict[str, Any]:
    queue = _read(queue_path)
    catalog = _read(catalog_path)
    normalized_catalog = normalize_brandconnect_catalog(catalog)
    function_relations = build_catalog_function_relations(normalized_catalog.get("products", []))
    requests = [item for item in queue.get("requests", []) if isinstance(item, dict)]
    candidates = [
        {
            "id": item.get("candidate_id"),
            "title": item.get("title"),
            "category": item.get("category"),
        }
        for item in requests
    ]
    ratings = {
        str(item.get("candidate_id")): {"grade": item.get("grade")}
        for item in requests
        if str(item.get("grade") or "").strip()
    }
    brandconnect = run_brandconnect_second_stage(
        candidates,
        ratings,
        catalog,
        relation_index=function_relations["relations"],
    )
    relation_index_supplied = bool(function_relations.get("relations"))
    relation_signal_annotation_count = sum(
        1
        for item in brandconnect.get("annotations", [])
        if isinstance(item, dict) and item.get("relation_signals_used")
    )
    relation_index_connected = (
        relation_index_supplied
        and relation_signal_annotation_count > 0
    )
    selection = select_owner_ranked_final_candidates(queue, brandconnect)
    production_handoff = _build_production_handoff(selection)

    story_state = new_engine_state()
    story_ingestion = ingest_relation_shard(
        story_state,
        "cached-catalog-functions:2026-07-19",
        "fashion_beauty",
        function_relations["story_rows"],
    )
    story_briefs = build_candidate_story_briefs(story_state, brandconnect.get("annotations", []))

    payload = {
        "schema_version": "owner_ranked_final_selection_run_v1",
        "source_queue": str(queue_path),
        "source_catalog": str(catalog_path),
        "brandconnect_summary": {
            "status": brandconnect.get("status"),
            "catalog_product_count": brandconnect.get("catalog", {}).get("product_count"),
            "annotation_count": len(brandconnect.get("annotations", [])),
            "commerce_status_counts": {
                status: sum(1 for item in brandconnect.get("annotations", []) if item.get("commerce_status") == status)
                for status in sorted({str(item.get("commerce_status")) for item in brandconnect.get("annotations", [])})
            },
            "network_used": brandconnect.get("network_used"),
            "link_issuance": brandconnect.get("link_issuance"),
            "publishing": brandconnect.get("publishing"),
            "relation_index_supplied": relation_index_supplied,
            "relation_index_connected": relation_index_connected,
            "relation_signal_annotation_count": relation_signal_annotation_count,
            "relation_count": function_relations["relation_count"],
            "relation_profile_counts": function_relations["profile_counts"],
        },
        "commerce_story_stage": {
            "relation_source": function_relations["source_contract"],
            "ingestion": story_ingestion,
            "story_briefs": story_briefs,
            "network_used": False,
            "link_issuance": False,
            "publishing": False,
        },
        "selection": selection,
        "production_handoff": production_handoff,
        "agent_console": {
            "status": "not_used_as_owner_selection_gate",
            "console_root": str(console_root),
            "owner_review_gate_used": False,
            "automatic_selection_is_not_owner_approval": True,
            "owner_review_status_counts": {},
            "execution_started": False,
        },
        "manual_upload_ready": False,
        "actual_publish": False,
        "upload_executed": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="storage/owner_review/selective_deep_dive_queue.json")
    parser.add_argument("--catalog", default="storage/owner_review/brandconnect_catalog_snapshot.json")
    parser.add_argument("--console-root", default="artifacts/agent_console_v1")
    parser.add_argument("--output", default="F:/AI-Content-OS-Data/source_intake/owner_ranked_final_selection_2026-07-19_fixed.json")
    args = parser.parse_args()
    repository = REPOSITORY_ROOT.resolve()
    result = execute(
        repository_root=repository,
        queue_path=(repository / args.queue).resolve(),
        catalog_path=(repository / args.catalog).resolve(),
        console_root=(repository / args.console_root).resolve(),
        output_path=Path(args.output).resolve(),
    )
    print(json.dumps({
        "status": result["selection"]["status"],
        "selected_count": result["selection"]["selected_count"],
        "not_selected_count": result["selection"]["not_selected_count"],
        "agent_console": result["agent_console"]["owner_review_status_counts"],
        "production_handoff_count": result["production_handoff"]["candidate_count"],
        "owner_grade_required": result["production_handoff"]["owner_grade_required"],
        "manual_upload_ready": result["manual_upload_ready"],
        "actual_publish": result["actual_publish"],
        "upload_executed": result["upload_executed"],
        "output": str(Path(args.output).resolve()),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
