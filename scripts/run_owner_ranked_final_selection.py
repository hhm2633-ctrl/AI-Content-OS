"""Replay the saved owner queue through commerce matching and final selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.agent_console.console import AgentConsole
from modules.agent_console.cardnews_flow_bridge import sync_selected_cardnews_candidates
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
    ratings = {str(item.get("candidate_id")): {"grade": item.get("grade")} for item in requests}
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

    story_state = new_engine_state()
    story_ingestion = ingest_relation_shard(
        story_state,
        "cached-catalog-functions:2026-07-19",
        "fashion_beauty",
        function_relations["story_rows"],
    )
    story_briefs = build_candidate_story_briefs(story_state, brandconnect.get("annotations", []))

    console = AgentConsole(console_root, repository_root=repository_root)
    bridge = sync_selected_cardnews_candidates(
        selection,
        console,
        owner_queue=queue,
        execution_approved=True,
    )
    snapshot = console.snapshot()
    status_counts: Dict[str, int] = {}
    for job in snapshot.get("jobs", []):
        if job.get("source") == "owner_review":
            status = str(job.get("status"))
            status_counts[status] = status_counts.get(status, 0) + 1

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
        "agent_console": {
            "bridge": bridge,
            "sync": bridge.get("sync", {}),
            "reconciliation": bridge.get("reconciliation"),
            "owner_review_status_counts": status_counts,
            "execution_started": False,
        },
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
        "output": str(Path(args.output).resolve()),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
