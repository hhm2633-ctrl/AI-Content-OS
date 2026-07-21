"""Bridge owner-ranked CardNews finalists into the gated Agent Console queue.

The final selector's owner grade is selection input, not execution approval.
This adapter therefore delegates to ``sync_owner_review_queue`` so every new
job remains ``awaiting_second_stage`` until the console's explicit promotion
operation is called elsewhere.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Mapping, Protocol


SELECTION_SCHEMA = "cardnews_final_selection_v1"
OWNER_QUEUE_SCHEMA = "owner_ranked_deep_dive_queue_v1"


class OwnerReviewConsole(Protocol):
    def sync_owner_review_queue(self, queue: Mapping[str, Any]) -> Dict[str, int]: ...
    def reconcile_owner_review_selection(self, source_request_ids: list[str]) -> Dict[str, list[str]]: ...


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _closed(reason_code: str) -> Dict[str, Any]:
    return {
        "schema_version": "cardnews_agent_console_bridge_v1",
        "status": "closed",
        "reason_code": reason_code,
        "selected_count": 0,
        "synced_count": 0,
        "owner_approval_required": True,
        "execution_enabled": False,
        "network_executed": False,
        "publishing": False,
    }


def _selected_requests(selection: Mapping[str, Any]) -> list[Dict[str, Any]]:
    accounts = selection.get("accounts")
    if not isinstance(accounts, Mapping):
        return []

    requests: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for account in ("A", "B", "C"):
        bucket = accounts.get(account)
        if not isinstance(bucket, Mapping):
            continue
        selected = bucket.get("selected")
        if not isinstance(selected, list):
            continue
        for candidate in selected:
            if not isinstance(candidate, Mapping) or candidate.get("selection_status") == "not_selected":
                continue
            candidate_id = _text(candidate.get("candidate_id"))
            candidate_account = _text(candidate.get("account")).upper()
            category = _text(candidate.get("category"))
            title = _text(candidate.get("title"))
            grade = _text(candidate.get("grade"))
            if not candidate_id or candidate_account != account or not category or not title or grade not in {"1", "2", "3"}:
                continue
            request_id = _text(candidate.get("request_id")) or f"owner_review:{candidate_id}"
            if request_id in seen:
                continue
            seen.add(request_id)
            source_urls = [
                _text(url)
                for url in candidate.get("source_urls", [])
                if isinstance(url, str) and _text(url)
            ]
            requested_media = candidate.get("requested_media")
            requests.append(
                {
                    "request_id": request_id,
                    "candidate_id": candidate_id,
                    "account": account,
                    "category": category,
                    "title": title,
                    "grade": grade,
                    "source_urls": source_urls,
                    "requested_media": copy.deepcopy(requested_media) if isinstance(requested_media, list) else [],
                    "execution_enabled": False,
                    "network_executed": False,
                    "publishing": False,
                }
            )
    return requests


def sync_selected_cardnews_candidates(
    selection: Any,
    console: OwnerReviewConsole,
    *,
    owner_queue: Mapping[str, Any] | None = None,
    execution_approved: bool = False,
) -> Dict[str, Any]:
    """Synchronize only selected finalists without granting execution approval."""

    if not isinstance(selection, Mapping) or selection.get("schema_version") != SELECTION_SCHEMA:
        return _closed("invalid_final_selection")
    if selection.get("status") not in {None, "selected"}:
        return _closed("final_selection_not_selected")

    requests = _selected_requests(selection)
    if not requests:
        return _closed("no_valid_selected_candidates")

    queue = dict(owner_queue) if isinstance(owner_queue, Mapping) else {
        "schema_version": OWNER_QUEUE_SCHEMA,
        "source_schema_version": SELECTION_SCHEMA,
        "requests": requests,
        "execution_enabled": False,
        "network_executed": False,
        "publishing": False,
    }
    counters = console.sync_owner_review_queue(queue)
    request_ids = [request["request_id"] for request in requests]
    reconciliation = None
    if execution_approved:
        reconciliation = console.reconcile_owner_review_selection(request_ids)
    return {
        "schema_version": "cardnews_agent_console_bridge_v1",
        "status": "synced",
        "reason_code": "ok",
        "selected_count": len(requests),
        "synced_count": int(counters.get("created", 0)) + int(counters.get("updated", 0)),
        "sync": dict(counters),
        "request_ids": request_ids,
        "reconciliation": reconciliation,
        "owner_approval_required": not execution_approved,
        "execution_enabled": execution_approved,
        "network_executed": False,
        "publishing": False,
    }


__all__ = ["sync_selected_cardnews_candidates"]
