"""Run local multi-account CardNews discovery from an existing collection file.

This entrypoint never collects, deep-fetches, renders, publishes, or performs
owner selection. Both input and output paths must be supplied explicitly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Sequence

from modules.source_intake.multi_account_card_news_discovery_pipeline import (
    run_multi_account_card_news_discovery_pipeline,
)


STAGE1_ENTRYPOINT_SCHEMA_VERSION = "multi_account_discovery_entrypoint_v1"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _validate_input(payload: Any) -> str:
    if not isinstance(payload, Mapping):
        return "input_must_be_object"
    if payload.get("schema_version") != "daily_shallow_collection_v1":
        return "unexpected_collection_schema"
    if payload.get("status") != "completed":
        return "collection_not_completed"
    items = payload.get("items")
    if not isinstance(items, list):
        return "collection_items_must_be_list"
    if not items:
        return "collection_items_empty"
    if any(not isinstance(item, Mapping) for item in items):
        return "collection_item_must_be_object"
    return ""


def _cluster_memberships(pipeline_result: Mapping[str, Any]) -> Dict[int, str]:
    stages = pipeline_result.get("stages")
    stages = stages if isinstance(stages, Mapping) else {}
    clustering = stages.get("clustering")
    clustering = clustering if isinstance(clustering, Mapping) else {}
    clusters = clustering.get("clusters")
    memberships: Dict[int, str] = {}
    if not isinstance(clusters, list):
        return memberships
    for cluster in clusters:
        if not isinstance(cluster, Mapping):
            continue
        cluster_id = _text(cluster.get("cluster_id"))
        indexes = cluster.get("indexes")
        if not cluster_id or not isinstance(indexes, list):
            continue
        for eligible_index in indexes:
            if isinstance(eligible_index, int) and not isinstance(eligible_index, bool):
                memberships[eligible_index] = cluster_id
    return memberships


def _candidate_ledger(
    items: Sequence[Mapping[str, Any]],
    pipeline_result: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    stages = pipeline_result.get("stages")
    stages = stages if isinstance(stages, Mapping) else {}
    eligibility = stages.get("collection_eligibility")
    eligibility = eligibility if isinstance(eligibility, Mapping) else {}
    filtered = eligibility.get("filtered")
    filtered = filtered if isinstance(filtered, list) else []
    excluded_by_index = {
        entry.get("input_index"): _text(entry.get("reason_code")) or "eligibility_excluded"
        for entry in filtered
        if isinstance(entry, Mapping)
        and isinstance(entry.get("input_index"), int)
        and not isinstance(entry.get("input_index"), bool)
    }
    original_to_eligible: Dict[int, int] = {}
    eligible_index = 0
    for input_index in range(len(items)):
        if input_index not in excluded_by_index:
            original_to_eligible[input_index] = eligible_index
            eligible_index += 1

    memberships = _cluster_memberships(pipeline_result)
    clustering = stages.get("clustering")
    clustering_ok = isinstance(clustering, Mapping) and clustering.get("status") == "ok"
    ledger: list[Dict[str, Any]] = []
    for input_index, item in enumerate(items):
        base = {
            "input_index": input_index,
            "candidate_id": _text(item.get("candidate_id")) or None,
            "title": _text(item.get("title") or item.get("keyword") or item.get("headline")) or None,
            "source_id": _text(item.get("source_id")) or None,
            "url": _text(item.get("link") or item.get("url")) or None,
        }
        if input_index in excluded_by_index:
            ledger.append({
                **base,
                "disposition": "excluded",
                "reason_code": excluded_by_index[input_index],
                "cluster_id": None,
            })
            continue
        cluster_id = memberships.get(original_to_eligible[input_index])
        if clustering_ok and cluster_id:
            ledger.append({
                **base,
                "disposition": "included",
                "reason_code": "accepted_into_discovery_cluster",
                "cluster_id": cluster_id,
            })
        else:
            ledger.append({
                **base,
                "disposition": "held",
                "reason_code": "pipeline_did_not_confirm_cluster_membership",
                "cluster_id": None,
            })
    return ledger


def _closed_result(input_path: Path, output_path: Path, reason_code: str) -> Dict[str, Any]:
    return {
        "schema_version": STAGE1_ENTRYPOINT_SCHEMA_VERSION,
        "status": "closed",
        "reason_code": reason_code,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "pipeline_called": False,
        "external_collection_performed": False,
        "deep_fetch_performed": False,
        "owner_selection_performed": False,
        "render_performed": False,
        "publishing_performed": False,
        "candidate_preservation": {
            "input_count": 0,
            "included_count": 0,
            "excluded_count": 0,
            "held_count": 0,
            "accounted_count": 0,
            "all_candidates_accounted_for": False,
            "ledger": [],
        },
        "pipeline_result": None,
    }


def run_from_paths(
    input_path: Path,
    output_path: Path,
    *,
    deep_input_path: Path | None = None,
    pipeline_runner: Callable[..., Dict[str, Any]] = run_multi_account_card_news_discovery_pipeline,
) -> Dict[str, Any]:
    input_path = Path(input_path)
    output_path = Path(output_path)
    if input_path.resolve() == output_path.resolve():
        result = _closed_result(input_path, output_path, "input_output_paths_must_differ")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result = _closed_result(input_path, output_path, f"input_read_failed:{type(exc).__name__}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    validation_error = _validate_input(payload)
    if validation_error:
        result = _closed_result(input_path, output_path, validation_error)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    deep_payload = None
    if deep_input_path is not None:
        try:
            deep_payload = json.loads(Path(deep_input_path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            result = _closed_result(
                input_path,
                output_path,
                f"deep_input_read_failed:{type(exc).__name__}",
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return result

    if deep_payload is None:
        pipeline_result = pipeline_runner(payload)
    else:
        pipeline_result = pipeline_runner(
            payload,
            deep_discovery_result=deep_payload,
        )
    if not isinstance(pipeline_result, Mapping):
        pipeline_result = {
            "status": "closed",
            "reason_code": "pipeline_result_must_be_object",
            "stages": {},
        }
    ledger = _candidate_ledger(payload["items"], pipeline_result)
    counts = {
        disposition: sum(1 for entry in ledger if entry["disposition"] == disposition)
        for disposition in ("included", "excluded", "held")
    }
    accounted_count = sum(counts.values())
    all_accounted = accounted_count == len(payload["items"])
    result = {
        "schema_version": STAGE1_ENTRYPOINT_SCHEMA_VERSION,
        "status": "completed" if all_accounted else "closed",
        "reason_code": "all_candidates_accounted_for" if all_accounted else "candidate_accounting_failed",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "pipeline_called": True,
        "external_collection_performed": False,
        "deep_fetch_performed": False,
        "existing_deep_result_consumed": deep_payload is not None,
        "owner_selection_performed": False,
        "render_performed": False,
        "publishing_performed": False,
        "candidate_preservation": {
            "input_count": len(payload["items"]),
            "included_count": counts["included"],
            "excluded_count": counts["excluded"],
            "held_count": counts["held"],
            "accounted_count": accounted_count,
            "all_candidates_accounted_for": all_accounted,
            "ledger": ledger,
        },
        "pipeline_result": dict(pipeline_result),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deep-input", type=Path)
    args = parser.parse_args()
    result = run_from_paths(
        args.input,
        args.output,
        deep_input_path=args.deep_input,
    )
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "reason_code": result["reason_code"],
        "output_path": result["output_path"],
        "candidate_preservation": result["candidate_preservation"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
