"""JSON stdin/stdout bridge for the local Brand Connect second-stage matcher."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.brandconnect.brandconnect_second_stage import run_brandconnect_second_stage
from modules.brandconnect.commerce_story_integration import merge_commerce_story_shards
from modules.brandconnect.incremental_commerce_story_engine import build_candidate_story_briefs


def execute(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}
    story_shards = payload.get("story_shards")
    integration = None
    relation_index = None
    if isinstance(story_shards, list) and story_shards:
        integration = merge_commerce_story_shards([], story_shards)
        relation_index = integration.get("engine_state", {}).get("products", {})

    stage = run_brandconnect_second_stage(
        payload.get("candidates"),
        payload.get("ratings"),
        payload.get("catalog_snapshot"),
        threshold=payload.get("threshold"),
        max_matches=payload.get("max_matches"),
        relation_index=relation_index,
    )
    if integration is not None:
        integration["story_briefs"] = build_candidate_story_briefs(
            integration.get("engine_state", {}),
            stage.get("annotations"),
        )
        integration.pop("engine_state", None)
        stage["commerce_story_stage"] = integration
    return stage


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        json.dump(execute(payload), sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    except Exception as error:  # pragma: no cover - defensive process boundary
        json.dump(
            {
                "schema_version": "brandconnect_second_stage.v1",
                "status": "bridge_error",
                "complete": False,
                "error": type(error).__name__,
                "annotations": [],
                "network_used": False,
                "link_issuance": False,
                "publishing": False,
            },
            sys.stdout,
            ensure_ascii=False,
        )
        sys.stdout.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
