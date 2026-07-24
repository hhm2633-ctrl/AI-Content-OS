"""Operational CardNews collection entrypoint through production handoff.

Connects shallow collection, source-intake artifacts, release-candidate, and
multi-account discovery. Owner feedback is optional selection evidence. The
orchestrator may create a data-only production handoff, but never renders,
publishes, or marks a package ready for upload.
"""

from __future__ import annotations

import copy
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from modules.source_intake.collection_gap_runner import run_collection_gap_report
from modules.source_intake.daily_collection_executor import (
    COLLECTOR_METHODS,
    DIRECT_COLLECTOR_FACTORIES,
    _has_manager_collector_method,
    execute_daily_shallow_collection,
)
from modules.source_intake.lane_collection_summary_runner import run_lane_collection_summary
from modules.source_intake.multi_account_card_news_discovery_pipeline import (
    run_multi_account_card_news_discovery_pipeline,
)
from modules.source_intake.source_intake_release_candidate import (
    RC_STATUS_GO,
    run_source_intake_release_candidate,
)
from modules.source_intake.source_intake_schema import SOURCE_INTAKE_STORAGE_ROOT
from modules.source_intake.source_intake_status_bundle import run_source_intake_status_bundle
from modules.source_intake.spark_task_queue_builder import run_spark_task_queue
from modules.trend_collector.trend_source_manager import TrendSourceManager

SCHEMA_VERSION = "cardnews_collection_orchestrator_v1"
OWNER_REVIEW_QUEUE_SCHEMA = "owner_ranked_deep_dive_queue_v1"
MAX_OWNER_REVIEW_REQUESTS_PER_ACCOUNT = 5  # Legacy display hint, not a storage cap.
ACCOUNT_IDS = {
    "account_a_news_incident": "A",
    "account_b_issue_story": "B",
    "account_c_beauty_fashion": "C",
}


def _coerce_today(value: Optional[Any]) -> str:
    if not value:
        return date.today().isoformat()
    if isinstance(value, str):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _write_json(path: os.PathLike[str] | str, payload: Mapping[str, Any]) -> None:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _retry_owner(source_id: str, manager: Any) -> str:
    method_name = COLLECTOR_METHODS.get(source_id)
    if method_name and _has_manager_collector_method(manager, method_name):
        return "manager"
    if source_id in DIRECT_COLLECTOR_FACTORIES:
        return "collector"
    return "unspecified"


def _preserve_retry_owner(collection: Dict[str, Any], manager: Any) -> Dict[str, Any]:
    enriched = copy.deepcopy(collection)
    owners: Dict[str, str] = {}
    for result in enriched.get("source_results", []):
        if not isinstance(result, dict):
            continue
        source_id = str(result.get("source_id") or "")
        owner = str(result.get("retry_owner") or "") or _retry_owner(source_id, manager)
        result["retry_owner"] = owner
        owners[source_id] = owner
    for item in enriched.get("items", []):
        if isinstance(item, dict):
            source_id = str(item.get("source_id") or "")
            item.setdefault("retry_owner", owners.get(source_id) or _retry_owner(source_id, manager))
    enriched["retry_ownership"] = {
        "by_source": owners,
        "metadata_only": True,
        "does_not_imply_retry_occurred": True,
    }
    return enriched


def _complete_status_bundle(
    bundle_result: Mapping[str, Any],
    gap_path: Path,
    bundle_path: Path,
) -> Dict[str, Any]:
    bundle = copy.deepcopy(bundle_result.get("bundle"))
    if not isinstance(bundle, dict):
        bundle = {}
    gap_payload = json.loads(gap_path.read_text(encoding="utf-8"))
    buckets = gap_payload.get("source_status_by_readiness")
    buckets = buckets if isinstance(buckets, Mapping) else {}
    counts = {
        status: len(buckets.get(status, [])) if isinstance(buckets.get(status), list) else 0
        for status in ("ready", "partial", "blocked", "external_blocked")
    }
    bundle["readiness_status_counts"] = counts
    bundle["classification_source_count"] = sum(counts.values())
    _write_json(bundle_path, bundle)
    return bundle


def _source_urls(topic: Mapping[str, Any]) -> list[str]:
    urls: list[str] = []
    for value in topic.get("source_refs", []):
        if isinstance(value, str):
            candidate = value.strip()
        elif isinstance(value, Mapping):
            candidate = str(value.get("url") or value.get("link") or "").strip()
        else:
            candidate = ""
        if candidate and candidate not in urls:
            urls.append(candidate)
    return urls


def _candidate_lookup(discovery: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    stages = discovery.get("stages")
    stages = stages if isinstance(stages, Mapping) else {}
    routing = stages.get("account_routing")
    routing = routing if isinstance(routing, Mapping) else {}
    portfolios = routing.get("portfolios")
    portfolios = portfolios if isinstance(portfolios, Mapping) else {}
    category = stages.get("category_stage2")
    category = category if isinstance(category, Mapping) else {}
    groups = list(portfolios.values()) + [category.get("items", [])]
    for group in groups:
        for item in group if isinstance(group, list) else []:
            if not isinstance(item, Mapping):
                continue
            candidate_id = str(item.get("candidate_id") or "").strip()
            if candidate_id:
                lookup[candidate_id] = copy.deepcopy(dict(item))
    return lookup


def _review_sources(discovery: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    stages = discovery.get("stages")
    stages = stages if isinstance(stages, Mapping) else {}
    selection = stages.get("top_selection")
    selection = selection if isinstance(selection, Mapping) else {}
    top = selection.get("top_by_account")
    if not isinstance(top, Mapping):
        top = discovery.get("top_topics")
    return {
        "TOP": top if isinstance(top, Mapping) else {},
        "BACKUP": selection.get("backup_by_account")
        if isinstance(selection.get("backup_by_account"), Mapping)
        else {},
        "HOLD": selection.get("hold_by_account")
        if isinstance(selection.get("hold_by_account"), Mapping)
        else {},
        "WATCH": (
            discovery.get("watch_review_queue", {}).get("queue_by_account", {})
            if isinstance(discovery.get("watch_review_queue"), Mapping)
            else {}
        ),
    }


def build_owner_review_queue(discovery: Mapping[str, Any]) -> Dict[str, Any]:
    """Preserve every selection bucket while keeping owner feedback optional."""

    requests: list[Dict[str, Any]] = []
    seen_candidate_ids: set[str] = set()
    lookup = _candidate_lookup(discovery)
    sources = _review_sources(discovery)
    hidden_records: list[Dict[str, Any]] = []
    status_counts = {status: 0 for status in sources}
    by_category: Dict[str, list[Dict[str, Any]]] = {}

    for selection_status in ("TOP", "BACKUP", "HOLD", "WATCH"):
        buckets = sources[selection_status]
        for logical_account, account in ACCOUNT_IDS.items():
            topics = buckets.get(logical_account)
            for raw_topic in topics if isinstance(topics, list) else []:
                if not isinstance(raw_topic, Mapping):
                    hidden_records.append(
                        {
                            "account": account,
                            "selection_status": selection_status,
                            "reason_code": "candidate_must_be_object",
                            "raw": copy.deepcopy(raw_topic),
                        }
                    )
                    continue
                candidate_id = str(raw_topic.get("candidate_id") or "").strip()
                hydrated = copy.deepcopy(lookup.get(candidate_id, {}))
                hydrated.update(copy.deepcopy(dict(raw_topic)))
                title = str(
                    hydrated.get("title") or hydrated.get("representative_title") or ""
                ).strip()
                category = str(hydrated.get("primary_category") or "unknown")
                artifact_entry = {
                    "candidate_id": candidate_id or None,
                    "account": account,
                    "category": category,
                    "title": title or None,
                    "selection_status": selection_status,
                    "production_eligible": selection_status == "TOP",
                    "raw": hydrated,
                }
                status_counts[selection_status] += 1
                by_category.setdefault(category, []).append(copy.deepcopy(artifact_entry))
                if not candidate_id or not title:
                    hidden_records.append(
                        {
                            **artifact_entry,
                            "reason_code": "identity_or_title_missing",
                        }
                    )
                    continue
                if candidate_id in seen_candidate_ids:
                    hidden_records.append(
                        {
                            **artifact_entry,
                            "reason_code": "duplicate_candidate_preserved_in_category_artifact",
                        }
                    )
                    continue
                seen_candidate_ids.add(candidate_id)
                is_watch = selection_status == "WATCH"
                requests.append(
                    {
                        "request_id": f"candidate_review:{candidate_id}",
                        "candidate_id": candidate_id,
                        "account": account,
                        "category": category,
                        "title": title,
                        "grade": None,
                        "review_state": "optional_owner_feedback",
                        "source_urls": _source_urls(hydrated),
                        "requested_media": [],
                        "selection_score": copy.deepcopy(
                            hydrated.get("selection_score")
                            or hydrated.get("score_diagnostics")
                        ),
                        "selection_status": selection_status,
                        "selection_authority": "automatic_account_policy",
                        "owner_grade_required": False,
                        "owner_grade_role": "optional_reference_signal",
                        "automatic_owner_selection": False,
                        "review_track": (
                            "watch_promotion"
                            if is_watch
                            else "optional_candidate_feedback"
                        ),
                        "stage2_decision": "WATCH" if is_watch else "GO",
                        "watch_promotion_required": is_watch,
                        "production_eligible": selection_status == "TOP",
                    }
                )

    category_review_artifact = {
        "schema_version": "cardnews_category_review_artifact_v1",
        "status": "ready" if by_category or hidden_records else "empty",
        "candidate_count": sum(status_counts.values()),
        "status_counts": status_counts,
        "categories": by_category,
        "unaddressable_or_duplicate_records": hidden_records,
        "owner_feedback_optional": True,
        "automatic_selection_is_not_owner_approval": True,
    }
    return {
        "schema_version": OWNER_REVIEW_QUEUE_SCHEMA,
        "status": "automatic_selection_ready" if requests else "empty",
        "requests": requests,
        "request_count": len(requests),
        "category_review_artifact": category_review_artifact,
        "owner_grades_inferred": False,
        "owner_grade_required": False,
        "owner_feedback_optional": True,
        "owner_selection_performed": False,
        "automatic_selection_performed": bool(
            any(item.get("production_eligible") is True for item in requests)
        ),
        "deep_discovery_performed": False,
        "production_performed": False,
        "publishing_performed": False,
        "actual_publish": False,
        "upload_executed": False,
    }


def build_automatic_production_handoff(owner_queue: Mapping[str, Any]) -> Dict[str, Any]:
    """Create a data-only handoff from automatic TOP selections."""

    candidates = [
        {
            **copy.deepcopy(dict(item)),
            "grade": item.get("grade"),
            "owner_grade_consumed": item.get("grade") is not None,
            "selection_authority": "automatic_account_policy",
        }
        for item in owner_queue.get("requests", [])
        if isinstance(item, Mapping) and item.get("production_eligible") is True
    ]
    return {
        "schema_version": "cardnews_automatic_production_handoff_v1",
        "status": "ready" if candidates else "empty",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "selection_authority": "automatic_account_policy",
        "owner_grade_required": False,
        "owner_feedback_optional": True,
        "owner_approval_required_at": "pre_upload_manual_upload_ready",
        "manual_upload_ready": False,
        "actual_publish": False,
        "upload_executed": False,
        "production_performed": False,
        "render_performed": False,
        "publishing_performed": False,
    }


def run_cardnews_collection_orchestrator(
    *,
    account_profiles: Optional[Sequence[str]] = None,
    today: Optional[Any] = None,
    output_root: Optional[str] = None,
    owner_queue_path: Optional[str] = None,
    source_manager: Optional[Any] = None,
    collection_runner: Callable[..., Dict[str, Any]] = execute_daily_shallow_collection,
    gap_runner: Callable[..., Dict[str, Any]] = run_collection_gap_report,
    lane_runner: Callable[..., Dict[str, Any]] = run_lane_collection_summary,
    spark_runner: Callable[..., Dict[str, Any]] = run_spark_task_queue,
    bundle_runner: Callable[..., Dict[str, Any]] = run_source_intake_status_bundle,
    rc_runner: Callable[..., Dict[str, Any]] = run_source_intake_release_candidate,
    discovery_runner: Callable[..., Dict[str, Any]] = run_multi_account_card_news_discovery_pipeline,
) -> Dict[str, Any]:
    """Run collection through an automatic data-only production handoff."""

    today_str = _coerce_today(today)
    root = output_root or SOURCE_INTAKE_STORAGE_ROOT
    day_root = Path(root) / today_str
    manager = source_manager or TrendSourceManager()
    stages: Dict[str, Any] = {}
    flags = {
        "owner_selection_performed": False,
        "automatic_selection_performed": False,
        "deep_discovery_performed": False,
        "production_performed": False,
        "render_performed": False,
        "publishing_performed": False,
    }
    try:
        collection = collection_runner(
            account_profiles=list(account_profiles) if account_profiles else None,
            today=today_str,
            output_root=root,
            source_manager=manager,
            allow_direct_collectors=True,
        )
        collection = _preserve_retry_owner(collection, manager)
        stages["daily_shallow_collection"] = collection
        shallow_path = day_root / "daily_shallow_collection.json"
        plan_path = day_root / "daily_collection_plan.json"
        _write_json(shallow_path, collection)
        _write_json(plan_path, collection.get("plan", {}))

        gap = gap_runner(
            collection_result_path=str(shallow_path),
            today=today_str,
            output_root=root,
        )
        stages["collection_gap"] = gap
        gap_path = day_root / "collection_gap_report.json"
        implementation_queue_path = day_root / "collector_implementation_queue.json"
        stages["lane_collection_summary"] = lane_runner(
            gap_report_path=str(gap_path),
            today=today_str,
            output_root=root,
        )
        stages["spark_task_queue"] = spark_runner(
            queue_path=str(implementation_queue_path),
            output_path=str(day_root / "spark_task_queue.json"),
        )
        bundle_result = bundle_runner(today=today_str, root=root)
        bundle_path = day_root / "source_intake_status_bundle.json"
        stages["source_intake_status_bundle"] = {
            **dict(bundle_result),
            "bundle": _complete_status_bundle(bundle_result, gap_path, bundle_path),
        }

        release_candidate = rc_runner(
            today=today_str,
            root=root,
            source_manager=manager,
            source_intake_status_bundle_path=str(bundle_path),
            collection_gap_report_path=str(gap_path),
            daily_shallow_collection_path=str(shallow_path),
        )
        stages["release_candidate"] = release_candidate
        if release_candidate.get("status") != RC_STATUS_GO:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "closed",
                "reason_code": "release_candidate_closed",
                "today": today_str,
                "stages": stages,
                "owner_review_queue": build_owner_review_queue({}),
                "production_handoff": build_automatic_production_handoff({}),
                **flags,
            }

        eligible_collection = release_candidate.get("eligible_collection")
        if not isinstance(eligible_collection, Mapping):
            eligible_collection = collection
        discovery = discovery_runner(eligible_collection)
        stages["multi_account_discovery"] = discovery
        owner_queue = build_owner_review_queue(discovery)
        production_handoff = build_automatic_production_handoff(owner_queue)
        resolved_queue_path = (
            Path(owner_queue_path) if owner_queue_path else day_root / "owner_review_queue.json"
        )
        review_artifact_path = day_root / "category_review_artifact.json"
        handoff_path = day_root / "automatic_production_handoff.json"
        _write_json(resolved_queue_path, owner_queue)
        _write_json(review_artifact_path, owner_queue["category_review_artifact"])
        _write_json(handoff_path, production_handoff)
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "production_handoff_ready"
            if production_handoff["candidate_count"]
            else "closed",
            "reason_code": "automatic_selection_ready_owner_feedback_optional"
            if production_handoff["candidate_count"]
            else "no_production_handoff_candidates",
            "today": today_str,
            "output_root": str(day_root),
            "owner_queue_path": str(resolved_queue_path),
            "category_review_artifact_path": str(review_artifact_path),
            "production_handoff_path": str(handoff_path),
            "stages": stages,
            "owner_review_queue": owner_queue,
            "production_handoff": production_handoff,
            **{
                **flags,
                "automatic_selection_performed": production_handoff["candidate_count"] > 0,
            },
        }
    except Exception as error:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "closed",
            "reason_code": "orchestration_exception",
            "error": f"{type(error).__name__}: {error}",
            "today": today_str,
            "stages": stages,
            "owner_review_queue": build_owner_review_queue({}),
            "production_handoff": build_automatic_production_handoff({}),
            **flags,
        }


__all__ = [
    "ACCOUNT_IDS",
    "MAX_OWNER_REVIEW_REQUESTS_PER_ACCOUNT",
    "OWNER_REVIEW_QUEUE_SCHEMA",
    "SCHEMA_VERSION",
    "build_automatic_production_handoff",
    "build_owner_review_queue",
    "run_cardnews_collection_orchestrator",
]
