"""Operational CardNews collection entrypoint up to owner review.

Connects shallow collection, source-intake artifacts, release-candidate, and
multi-account discovery. It stops before owner ranking, deep discovery,
production, rendering, and publishing.
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
MAX_OWNER_REVIEW_REQUESTS_PER_ACCOUNT = 5
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


def build_owner_review_queue(discovery: Mapping[str, Any]) -> Dict[str, Any]:
    """Build a pending queue without inferring an owner grade."""

    requests = []
    seen_candidate_ids = set()
    top_topics = discovery.get("top_topics")
    top_topics = top_topics if isinstance(top_topics, Mapping) else {}
    watch_queue = discovery.get("watch_review_queue")
    watch_queue = watch_queue if isinstance(watch_queue, Mapping) else {}
    watch_by_account = watch_queue.get("queue_by_account")
    watch_by_account = watch_by_account if isinstance(watch_by_account, Mapping) else {}
    for logical_account, account in ACCOUNT_IDS.items():
        topics = top_topics.get(logical_account)
        account_request_count = 0
        for topic in topics if isinstance(topics, list) else []:
            if not isinstance(topic, Mapping):
                continue
            candidate_id = str(topic.get("candidate_id") or "").strip()
            title = str(topic.get("title") or "").strip()
            if not candidate_id or not title or candidate_id in seen_candidate_ids:
                continue
            requests.append(
                {
                    "request_id": f"owner_review:{candidate_id}",
                    "candidate_id": candidate_id,
                    "account": account,
                    "category": str(topic.get("primary_category") or "unknown"),
                    "title": title,
                    "grade": None,
                    "review_state": "pending_owner_grade",
                    "source_urls": _source_urls(topic),
                    "requested_media": [],
                    "selection_score": copy.deepcopy(topic.get("selection_score")),
                    "automatic_owner_selection": False,
                    "review_track": "top_topic_grade",
                    "stage2_decision": "GO",
                    "watch_promotion_required": False,
                    "production_eligible": False,
                }
            )
            seen_candidate_ids.add(candidate_id)
            account_request_count += 1
            if account_request_count >= MAX_OWNER_REVIEW_REQUESTS_PER_ACCOUNT:
                break

        watch_topics = watch_by_account.get(logical_account)
        for topic in watch_topics if isinstance(watch_topics, list) else []:
            if account_request_count >= MAX_OWNER_REVIEW_REQUESTS_PER_ACCOUNT:
                break
            if not isinstance(topic, Mapping):
                continue
            candidate_id = str(topic.get("candidate_id") or "").strip()
            title = str(topic.get("title") or "").strip()
            if not candidate_id or not title or candidate_id in seen_candidate_ids:
                continue
            requests.append(
                {
                    "request_id": f"owner_review:{candidate_id}",
                    "candidate_id": candidate_id,
                    "account": account,
                    "category": str(topic.get("primary_category") or "unknown"),
                    "title": title,
                    "grade": None,
                    "review_state": "pending_watch_approval",
                    "source_urls": _source_urls(topic),
                    "requested_media": [],
                    "selection_score": copy.deepcopy(topic.get("score_diagnostics")),
                    "automatic_owner_selection": False,
                    "review_track": "watch_promotion",
                    "stage2_decision": "WATCH",
                    "watch_promotion_required": True,
                    "production_eligible": False,
                }
            )
            seen_candidate_ids.add(candidate_id)
            account_request_count += 1
    return {
        "schema_version": OWNER_REVIEW_QUEUE_SCHEMA,
        "status": "pending_owner_review" if requests else "empty",
        "requests": requests,
        "request_count": len(requests),
        "owner_grades_inferred": False,
        "owner_selection_performed": False,
        "deep_discovery_performed": False,
        "production_performed": False,
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
    """Run collection through a pending owner-review queue, then stop."""

    today_str = _coerce_today(today)
    root = output_root or SOURCE_INTAKE_STORAGE_ROOT
    day_root = Path(root) / today_str
    manager = source_manager or TrendSourceManager()
    stages: Dict[str, Any] = {}
    flags = {
        "owner_selection_performed": False,
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
                **flags,
            }

        eligible_collection = release_candidate.get("eligible_collection")
        if not isinstance(eligible_collection, Mapping):
            eligible_collection = collection
        discovery = discovery_runner(eligible_collection)
        stages["multi_account_discovery"] = discovery
        owner_queue = build_owner_review_queue(discovery)
        resolved_queue_path = (
            Path(owner_queue_path) if owner_queue_path else day_root / "owner_review_queue.json"
        )
        _write_json(resolved_queue_path, owner_queue)
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "owner_review_ready" if owner_queue["request_count"] else "closed",
            "reason_code": "pending_owner_grade" if owner_queue["request_count"] else "no_owner_review_candidates",
            "today": today_str,
            "output_root": str(day_root),
            "owner_queue_path": str(resolved_queue_path),
            "stages": stages,
            "owner_review_queue": owner_queue,
            **flags,
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
            **flags,
        }


__all__ = [
    "ACCOUNT_IDS",
    "MAX_OWNER_REVIEW_REQUESTS_PER_ACCOUNT",
    "OWNER_REVIEW_QUEUE_SCHEMA",
    "SCHEMA_VERSION",
    "build_owner_review_queue",
    "run_cardnews_collection_orchestrator",
]
