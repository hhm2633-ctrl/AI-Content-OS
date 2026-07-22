"""Adapter from owner review deep-dive queue payload to source-intake contract."""

import copy
from typing import Any, Dict, List, Mapping

from modules.source_intake.selective_deep_dive_queue import build_selective_deep_dive_queue

OWNED_FORMAT = "card_news"
ALLOWED_GRADES = {"1", "2", "3"}
GRADE_ROUTE_SCORES = {"1": 1.0, "2": 0.65, "3": 0.35}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return copy.deepcopy(value) if isinstance(value, list) else []


def _source_refs(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []
    for source_url in _list(payload.get("source_urls")):
        if isinstance(source_url, str):
            source_url = source_url.strip()
            if source_url:
                refs.append(
                    {
                        "type": "owner_source_url",
                        "kind": "source_url",
                        "value": source_url,
                    }
                )
    for media in _list(payload.get("requested_media")):
        if isinstance(media, str):
            media = media.strip()
            if media:
                refs.append(
                    {
                        "type": "owner_requested_media",
                        "kind": "requested_media",
                        "value": media,
                    }
                )
    refs.append(
        {
            "type": "owner_traceability",
            "kind": "owner_grade",
            "value": _text(payload.get("grade")),
        }
    )
    refs.append(
        {
            "type": "owner_traceability",
            "kind": "owner_account",
            "value": _text(payload.get("account")),
        }
    )
    refs.append(
        {
            "type": "owner_traceability",
            "kind": "owner_category",
            "value": _text(payload.get("category")),
        }
    )
    refs.append(
        {
            "type": "owner_traceability",
            "kind": "owner_title",
            "value": _text(payload.get("title")),
        }
    )
    return refs


def adapt_owner_ranked_queue_to_selective_contract(payload: Any) -> Dict[str, Any]:
    """Convert owner queue payload to source-intake deep-dive queue contract."""

    if not isinstance(payload, Mapping):
        return {
            "status": "closed",
            "reason_code": "malformed_owner_queue",
            "reason": "owner_queue payload must be an object",
            "execution_enabled": False,
            "network_executed": False,
            "requests": [],
            "request_count": 0,
            "blocked": [],
        }

    requests = payload.get("requests")
    if not isinstance(requests, list):
        return {
            "status": "closed",
            "reason_code": "malformed_owner_queue_requests",
            "reason": "owner_ranked_deep_dive_queue_v1.requests must be a list",
            "execution_enabled": False,
            "network_executed": False,
            "requests": [],
            "request_count": 0,
            "blocked": [],
        }

    selected = []
    for index, request in enumerate(requests):
        if not isinstance(request, Mapping):
            continue
        candidate_id = _text(request.get("candidate_id")) or _text(request.get("request_id")).split(":", 1)[-1]
        grade = _text(request.get("grade"))
        if grade not in ALLOWED_GRADES or not candidate_id:
            continue

        route_score = GRADE_ROUTE_SCORES[grade]

        selected.append(
            {
                "candidate_id": candidate_id,
                "cluster_id": "",
                "category_id": _text(request.get("category")),
                "route_score": route_score,
                "route_confidence": 1.0,
                "risk_status": "reviewed",
                "evidence_status": "owner_reviewed_queue",
                "source_refs": _source_refs(request),
                "owner_payload": {
                    "grade": grade,
                    "account": _text(request.get("account")),
                    "category": _text(request.get("category")),
                    "title": _text(request.get("title")),
                    "source_urls": _list(request.get("source_urls")),
                    "requested_media": _list(request.get("requested_media")),
                    "source": _text(request.get("source")),
                    "status": _text(request.get("status")),
                },
            }
        )

    portfolio_contract = {
        "selected_by_format": {
            OWNED_FORMAT: selected,
            "shorts_reels": [],
            "commerce": [],
        }
    }

    result = build_selective_deep_dive_queue(portfolio_contract)
    owner_by_candidate = {
        entry["candidate_id"]: entry["owner_payload"]
        for entry in selected
    }
    for request in result.get("requests", []):
        if not isinstance(request, dict):
            continue
        owner_payload = owner_by_candidate.get(_text(request.get("candidate_id")))
        if not isinstance(owner_payload, Mapping):
            continue
        request["account"] = _text(owner_payload.get("account"))
        request["title"] = _text(owner_payload.get("title"))
        request["grade"] = _text(owner_payload.get("grade"))
        request["category"] = _text(owner_payload.get("category"))
        request["source_urls"] = _list(owner_payload.get("source_urls"))
        request["requested_media"] = _list(owner_payload.get("requested_media"))
        request["owner_payload"] = copy.deepcopy(dict(owner_payload))
    return result


__all__ = ["adapt_owner_ranked_queue_to_selective_contract"]
