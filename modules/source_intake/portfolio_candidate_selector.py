"""Portfolio selector for routed format-fit candidates.

Takes router outputs and enforces deterministic per-format selection limits
without inventing any additional fit logic.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from modules.source_intake.format_fit_router import SUPPORTED_FORMATS


DEFAULT_PER_FORMAT_LIMITS: Dict[str, int] = {
    "card_news": 5,
    "shorts_reels": 5,
    "commerce": 5,
}


def _build_closed_result(
    *,
    reason_code: str,
    reason: str,
    selected_by_format: Mapping[str, Any] | None = None,
    not_selected: Sequence[Mapping[str, Any]] = (),
) -> Dict[str, Any]:
    return {
        "status": "closed",
        "fallback_used": True,
        "reason_code": reason_code,
        "reason": reason,
        "selected_by_format": {fmt: [] for fmt in SUPPORTED_FORMATS}
        if selected_by_format is None
        else copy.deepcopy(dict(selected_by_format)),
        "selected_count": 0,
        "not_selected": [dict(item) for item in not_selected],
        "planned_constraints": {
            "category_balance": "deferred",
            "source_balance": "deferred",
        },
    }


def _coerce_limit(value: Any, format_name: str) -> Tuple[bool, int, str]:
    if not isinstance(value, int):
        return False, 0, f"per_format_limits[{format_name}] must be int"
    if value <= 0:
        return False, 0, f"per_format_limits[{format_name}] must be > 0"
    return True, value, ""


def _is_number_in_range(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1


def _extract_routes(router_result: Any) -> Tuple[bool, List[Mapping[str, Any]], str]:
    if not isinstance(router_result, Mapping):
        return False, [], "router result must be a mapping"

    status = router_result.get("status")
    if status == "closed":
        return False, [], (router_result.get("reason_code") or "router_closed")

    routes = router_result.get("routes")
    if not isinstance(routes, list):
        return False, [], "router result.routes must be a list"

    return True, list(routes), ""


def _route_sort_key(route: Mapping[str, Any]) -> tuple[float, float, str]:
    return (-float(route.get("score", 0.0)), -float(route.get("confidence", 0.0)), str(route.get("candidate_id", "")))


def _normalize_route(route: Mapping[str, Any], route_format: str) -> Dict[str, Any]:
    return {
        "format": route_format,
        "candidate_id": route.get("candidate_id"),
        "cluster_id": route.get("cluster_id"),
        "category": route.get("category"),
        "category_id": route.get("category_id"),
        "source_id": route.get("source_id"),
        "source_lane_id": route.get("source_lane_id"),
        "source_type": route.get("source_type"),
        "source_name": route.get("source_name"),
        "board_or_category": route.get("board_or_category"),
        "source_attribution": copy.deepcopy(route.get("source_attribution")),
        "source_refs": copy.deepcopy(route.get("source_refs")),
        "risk_status": route.get("risk_status"),
        "evidence_status": route.get("evidence_status"),
        "score": float(route.get("score", 0.0)),
        "confidence": float(route.get("confidence", 0.0)),
        "reasons": list(route.get("reasons", [])),
        "missing_requirements": list(route.get("missing_requirements", [])),
    }


def run_portfolio_candidate_selector(
    router_result: Any,
    *,
    per_format_limits: Mapping[str, int] | None = None,
) -> Dict[str, Any]:
    """Select bounded routes from router output using deterministic ordering.

    Ordering is:
    1) score desc
    2) confidence desc
    3) candidate_id asc
    """

    try:
        has_routes, routes, route_reason = _extract_routes(router_result)
        if not has_routes:
            return _build_closed_result(reason_code="malformed_router_result", reason=route_reason)

        limits = dict(DEFAULT_PER_FORMAT_LIMITS)
        if per_format_limits:
            for fmt, value in per_format_limits.items():
                if fmt not in SUPPORTED_FORMATS:
                    return _build_closed_result(
                        reason_code="unsupported_format_limit",
                        reason=f"unsupported format in limits: {fmt}",
                    )
                ok_limit, typed_value, limit_reason = _coerce_limit(value, fmt)
                if not ok_limit:
                    return _build_closed_result(
                        reason_code="invalid_per_format_limit",
                        reason=limit_reason,
                    )
                limits[fmt] = typed_value

        grouped_routes: Dict[str, List[Mapping[str, Any]]] = {fmt: [] for fmt in SUPPORTED_FORMATS}

        for route in routes:
            if not isinstance(route, Mapping):
                return _build_closed_result(
                    reason_code="malformed_route",
                    reason="Each route must be a mapping",
                )

            route_format = route.get("format")
            if route_format not in SUPPORTED_FORMATS:
                continue

            score = route.get("score")
            confidence = route.get("confidence")
            if not _is_number_in_range(score) or not _is_number_in_range(confidence):
                return _build_closed_result(
                    reason_code="malformed_route_metrics",
                    reason="Route score/confidence must be numeric in [0,1]",
                )

            candidate_id = route.get("candidate_id")
            if not isinstance(candidate_id, str):
                candidate_id = str(candidate_id) if candidate_id is not None else ""

            route_copy = _normalize_route(route, str(route_format))
            route_copy["candidate_id"] = candidate_id
            grouped_routes[str(route_format)].append(route_copy)

        selected_by_format: Dict[str, List[Dict[str, Any]]] = {fmt: [] for fmt in SUPPORTED_FORMATS}
        not_selected: List[Dict[str, Any]] = []

        for route_format in SUPPORTED_FORMATS:
            group = sorted(grouped_routes[route_format], key=_route_sort_key)
            seen_clusters: set[Any] = set()
            selected = selected_by_format[route_format]

            for route in group:
                if route_format and len(selected) >= limits[route_format]:
                    not_selected.append(
                        {
                            "format": route_format,
                            "candidate_id": route["candidate_id"],
                            "reason_code": "format_limit_exceeded",
                            "route": copy.deepcopy(route),
                        }
                    )
                    continue

                cluster_id = route.get("cluster_id")
                dedupe_key = cluster_id or f"candidate:{route['candidate_id']}"
                if dedupe_key in seen_clusters:
                    not_selected.append(
                        {
                            "format": route_format,
                            "candidate_id": route["candidate_id"],
                            "reason_code": "duplicate_cluster",
                            "cluster_id": copy.deepcopy(cluster_id),
                            "route": copy.deepcopy(route),
                        }
                    )
                    continue

                seen_clusters.add(dedupe_key)

                selected.append(copy.deepcopy(route))

        selected_count = sum(len(routes) for routes in selected_by_format.values())

        if selected_count == 0:
            return _build_closed_result(
                reason_code="no_selected_routes",
                reason="no routable routes were selected",
                selected_by_format=selected_by_format,
                not_selected=not_selected,
            )

        return {
            "status": "selected",
            "fallback_used": False,
            "reason_code": "ok",
            "reason": "selection completed",
            "selected_by_format": selected_by_format,
            "selected_count": selected_count,
            "not_selected": not_selected,
            "planned_constraints": {
                "category_balance": "deferred",
                "source_balance": "deferred",
            },
            "limits": dict(limits),
        }
    except Exception as exc:
        return _build_closed_result(
            reason_code="unexpected_error",
            reason=f"portfolio selector failed safely: {type(exc).__name__}",
        )


__all__ = [
    "DEFAULT_PER_FORMAT_LIMITS",
    "run_portfolio_candidate_selector",
]
