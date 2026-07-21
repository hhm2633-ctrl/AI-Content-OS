"""Fail-closed handoff contract from selected evidence to production inputs.

No existing production module is imported or executed here. The adapter only
builds data that can be reviewed before a later integration Sprint.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping


READY_EVIDENCE_STATUSES = {"ready", "verified", "evidence_ready"}
BLOCKED_RISK_STATUSES = {"blocked", "policy_blocked", "reject", "rejected"}
CLEARED_RISK_STATUSES = {"reviewed", "safe", "cleared"}


def _closed(reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "status": "blocked",
        "reason_code": reason_code,
        "reason": reason,
        "workflow_wired": False,
        "production_executed": False,
        "handoffs": [],
        "handoff_count": 0,
    }


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]


def _bundle_index(completed_bundles: Any) -> Dict[str, Mapping[str, Any]]:
    if isinstance(completed_bundles, Mapping):
        return {
            str(key): value
            for key, value in completed_bundles.items()
            if isinstance(value, Mapping)
        }
    if isinstance(completed_bundles, list):
        indexed: Dict[str, Mapping[str, Any]] = {}
        for value in completed_bundles:
            if not isinstance(value, Mapping):
                continue
            candidate_id = _text(value.get("candidate_id"))
            if candidate_id:
                indexed[candidate_id] = value
        return indexed
    return {}


def _card_news_target(request: Mapping[str, Any], bundle: Mapping[str, Any]) -> Dict[str, Any]:
    candidate_id = _text(request.get("candidate_id"))
    title = _text(bundle.get("title"))
    summary = _text(bundle.get("summary"))
    key_points = _string_list(bundle.get("key_points"))
    source_refs = copy.deepcopy(bundle.get("source_refs")) if isinstance(
        bundle.get("source_refs"), list
    ) else []

    missing = []
    if not title:
        missing.append("title")
    if not summary:
        missing.append("summary")
    if not key_points:
        missing.append("key_points")
    if not source_refs:
        missing.append("source_refs")

    if missing:
        return {
            "format": "card_news",
            "status": "blocked",
            "reason_code": "missing_production_evidence",
            "missing_requirements": missing,
            "target_contract": "ContentModule.run(research_result)",
            "payload": None,
        }

    keyword = _text(bundle.get("keyword")) or title
    research_input = {
        "candidate_id": candidate_id,
        "keyword": keyword,
        "title": title,
        "summary": summary,
        "key_points": key_points,
        "target": _text(bundle.get("target")),
        "topic_angle": _text(bundle.get("topic_angle")),
        "source_refs": source_refs,
        "evidence_status": _text(bundle.get("evidence_status")),
        "risk_status": _text(bundle.get("risk_status")) or "unknown",
    }
    return {
        "format": "card_news",
        "status": "ready_for_manual_integration",
        "reason_code": "evidence_contract_satisfied",
        "missing_requirements": [],
        "target_contract": "ContentModule.run(research_result)",
        "payload": research_input,
    }


def build_content_production_handoff(
    deep_dive_queue: Any,
    completed_bundles: Any,
) -> Dict[str, Any]:
    """Build reviewable production handoffs without executing production."""

    if not isinstance(deep_dive_queue, Mapping):
        return _closed("malformed_deep_dive_queue", "deep_dive_queue must be an object")
    if deep_dive_queue.get("status") != "queue_ready":
        return _closed("deep_dive_queue_not_ready", "deep_dive queue is not ready")
    requests = deep_dive_queue.get("requests")
    if not isinstance(requests, list):
        return _closed("malformed_requests", "deep_dive_queue.requests must be a list")

    bundles = _bundle_index(completed_bundles)
    handoffs: List[Dict[str, Any]] = []

    for raw_request in requests:
        if not isinstance(raw_request, Mapping):
            continue
        request = dict(raw_request)
        candidate_id = _text(request.get("candidate_id"))
        if not candidate_id or request.get("status") != "planned":
            continue

        formats = [
            value
            for value in request.get("requested_formats", [])
            if value in {"card_news", "shorts_reels", "commerce"}
        ] if isinstance(request.get("requested_formats"), list) else []
        bundle = bundles.get(candidate_id)

        if not isinstance(bundle, Mapping):
            handoffs.append(
                {
                    "candidate_id": candidate_id,
                    "status": "blocked",
                    "reason_code": "deep_dive_not_completed",
                    "targets": [],
                }
            )
            continue

        completion_status = _text(bundle.get("status")).lower()
        evidence_status = _text(bundle.get("evidence_status")).lower()
        risk_status = _text(bundle.get("risk_status")).lower()
        if completion_status not in {"complete", "completed"}:
            handoffs.append(
                {
                    "candidate_id": candidate_id,
                    "status": "blocked",
                    "reason_code": "deep_dive_not_completed",
                    "targets": [],
                }
            )
            continue
        if evidence_status not in READY_EVIDENCE_STATUSES:
            handoffs.append(
                {
                    "candidate_id": candidate_id,
                    "status": "blocked",
                    "reason_code": "evidence_not_ready",
                    "targets": [],
                }
            )
            continue
        if risk_status in BLOCKED_RISK_STATUSES:
            handoffs.append(
                {
                    "candidate_id": candidate_id,
                    "status": "blocked",
                    "reason_code": "risk_blocked",
                    "targets": [],
                }
            )
            continue
        if risk_status not in CLEARED_RISK_STATUSES:
            handoffs.append(
                {
                    "candidate_id": candidate_id,
                    "status": "blocked",
                    "reason_code": "risk_not_cleared",
                    "targets": [],
                }
            )
            continue

        targets: List[Dict[str, Any]] = []
        if "card_news" in formats:
            targets.append(_card_news_target(request, bundle))
        if "shorts_reels" in formats:
            targets.append(
                {
                    "format": "shorts_reels",
                    "status": "planned_not_wired",
                    "reason_code": "requires_content_result_adapter",
                    "target_contract": "ShortsModule standalone input",
                    "payload": None,
                }
            )
        if "commerce" in formats:
            targets.append(
                {
                    "format": "commerce",
                    "status": "planned_not_wired",
                    "reason_code": "requires_approved_product_fact_contract",
                    "target_contract": "Commerce standalone input",
                    "payload": None,
                }
            )

        ready = any(target.get("status") == "ready_for_manual_integration" for target in targets)
        handoffs.append(
            {
                "candidate_id": candidate_id,
                "status": "ready_for_manual_integration" if ready else "blocked",
                "reason_code": "target_ready" if ready else "no_wired_target",
                "targets": targets,
            }
        )

    ready_count = sum(
        1 for handoff in handoffs if handoff.get("status") == "ready_for_manual_integration"
    )
    return {
        "status": "handoff_ready" if ready_count else "blocked",
        "reason_code": "manual_integration_only" if ready_count else "no_ready_handoffs",
        "workflow_wired": False,
        "production_executed": False,
        "handoffs": handoffs,
        "handoff_count": len(handoffs),
        "ready_count": ready_count,
    }


__all__ = ["build_content_production_handoff"]
