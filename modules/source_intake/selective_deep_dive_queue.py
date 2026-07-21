"""Data-only selective deep-dive request planning.

This module never performs collection. It converts already-selected portfolio
routes into bounded request descriptors so expensive detail work can happen
later, after explicit implementation and approval gates.
"""

from __future__ import annotations

import copy
from collections import OrderedDict
from typing import Any, Dict, List, Mapping


SUPPORTED_FORMATS = ("card_news", "shorts_reels", "commerce")
BLOCKED_RISK_STATUSES = {"blocked", "policy_blocked", "reject", "rejected"}
CLEARED_RISK_STATUSES = {"reviewed", "safe", "cleared"}
FORMAT_REQUIREMENTS = {
    "card_news": ("article_body", "source_evidence", "image_rights"),
    "shorts_reels": ("article_body", "source_evidence", "visual_asset_rights"),
    "commerce": (
        "product_facts",
        "price_stock_freshness",
        "affiliate_compliance",
    ),
}


def _closed(reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "status": "closed",
        "reason_code": reason_code,
        "reason": reason,
        "execution_enabled": False,
        "network_executed": False,
        "requests": [],
        "request_count": 0,
        "blocked": [],
    }


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return copy.deepcopy(value) if isinstance(value, list) else []


def _is_risk_blocked(value: Any) -> bool:
    return _text(value).lower() in BLOCKED_RISK_STATUSES


def build_selective_deep_dive_queue(portfolio_result: Any) -> Dict[str, Any]:
    """Build non-executable deep-dive requests from selected format routes."""

    if not isinstance(portfolio_result, Mapping):
        return _closed("malformed_portfolio", "portfolio_result must be an object")

    selected_by_format = portfolio_result.get("selected_by_format")
    if not isinstance(selected_by_format, Mapping):
        return _closed(
            "malformed_selected_by_format",
            "portfolio_result.selected_by_format must be an object",
        )

    grouped: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    blocked: List[Dict[str, Any]] = []

    for format_id in SUPPORTED_FORMATS:
        entries = selected_by_format.get(format_id, [])
        if entries is None:
            entries = []
        if not isinstance(entries, list):
            return _closed(
                "malformed_selected_entries",
                f"selected_by_format.{format_id} must be a list",
            )

        for index, raw_entry in enumerate(entries):
            if not isinstance(raw_entry, Mapping):
                blocked.append(
                    {
                        "format": format_id,
                        "index": index,
                        "reason_code": "malformed_selected_entry",
                    }
                )
                continue

            entry = dict(raw_entry)
            candidate_id = _text(entry.get("candidate_id"))
            if not candidate_id:
                blocked.append(
                    {
                        "format": format_id,
                        "index": index,
                        "reason_code": "missing_candidate_id",
                    }
                )
                continue

            risk_status = _text(entry.get("risk_status")) or "unknown"
            if _is_risk_blocked(risk_status):
                blocked.append(
                    {
                        "candidate_id": candidate_id,
                        "format": format_id,
                        "reason_code": "risk_blocked",
                        "risk_status": risk_status,
                    }
                )
                continue
            if risk_status.lower() not in CLEARED_RISK_STATUSES:
                blocked.append(
                    {
                        "candidate_id": candidate_id,
                        "format": format_id,
                        "reason_code": "risk_not_cleared",
                        "risk_status": risk_status,
                    }
                )
                continue

            request = grouped.setdefault(
                candidate_id,
                {
                    "request_id": f"deep_dive:{candidate_id}",
                    "candidate_id": candidate_id,
                    "cluster_id": _text(entry.get("cluster_id")),
                    "category_id": _text(entry.get("category_id")),
                    "requested_formats": [],
                    "required_artifacts": [],
                    "source_refs": _list(entry.get("source_refs")),
                    "evidence_status": _text(entry.get("evidence_status")) or "unknown",
                    "risk_status": risk_status,
                    "selection_refs": [],
                    "status": "planned",
                    "execution_enabled": False,
                    "network_executed": False,
                },
            )

            if format_id not in request["requested_formats"]:
                request["requested_formats"].append(format_id)
            for artifact in FORMAT_REQUIREMENTS[format_id]:
                if artifact not in request["required_artifacts"]:
                    request["required_artifacts"].append(artifact)
            request["selection_refs"].append(
                {
                    "format": format_id,
                    "route_score": entry.get("route_score", entry.get("score")),
                    "route_confidence": entry.get(
                        "route_confidence", entry.get("confidence")
                    ),
                }
            )

    requests = list(grouped.values())
    if not requests:
        result = _closed("no_eligible_selected_candidates", "no safe selected candidates")
        result["blocked"] = blocked
        return result

    return {
        "status": "queue_ready",
        "reason_code": "planned_requests_only",
        "reason": "selected candidates converted to non-executable deep-dive requests",
        "execution_enabled": False,
        "network_executed": False,
        "requests": requests,
        "request_count": len(requests),
        "blocked": blocked,
    }


__all__ = [
    "build_selective_deep_dive_queue",
    "SUPPORTED_FORMATS",
    "FORMAT_REQUIREMENTS",
]
