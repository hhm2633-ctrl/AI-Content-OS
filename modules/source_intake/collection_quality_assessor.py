"""Deterministic quality assessment for shallow collection outputs."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


STATUS_EMPTY = "EMPTY"
STATUS_LIMITED = "LIMITED"
STATUS_USABLE_SHALLOW = "USABLE_SHALLOW"

USABLE_RATIO_THRESHOLD = 0.8
MAX_FALLBACK_RATIO = 0.25

OPTIONAL_EVIDENCE_FIELDS = ("summary", "publisher", "published_at")
VISIBLE_METRIC_FIELDS = ("views", "comments", "likes", "dislikes")
VISIBLE_METRIC_ALIASES = {
    "views": ("view_count",),
    "comments": ("comment_count",),
    "likes": ("recommend_count", "recommends"),
    "dislikes": ("dislike_count",),
}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _first_present(item: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = item.get(key)
        if _present(value):
            return value
    return None


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _availability(
    items: List[Dict[str, Any]], field: str, aliases: Iterable[str] = ()
) -> Dict[str, Any]:
    keys = (field, *tuple(aliases))
    available = sum(1 for item in items if _first_present(item, keys) is not None)
    total = len(items)
    return {
        "available": available,
        "missing": total - available,
        "ratio": _ratio(available, total),
    }


def _visible_metric_availability(
    items: List[Dict[str, Any]], field: str, aliases: Iterable[str] = ()
) -> Dict[str, Any]:
    """Count flat legacy metrics and canonical nested visible metrics.

    Collectors using the shallow-item contract store parsed values under
    ``visible_metrics`` while older collectors expose the same values at the
    item root. Availability is a provenance/completeness fact only: explicit
    zero is available, and missing/None stays missing.
    """
    keys = (field, *tuple(aliases))
    available = 0

    for item in items:
        value = _first_present(item, keys)
        if value is None:
            nested = item.get("visible_metrics")
            if isinstance(nested, dict):
                value = _first_present(nested, keys)
        if value is not None:
            available += 1

    total = len(items)
    return {
        "available": available,
        "missing": total - available,
        "ratio": _ratio(available, total),
    }


def assess_collection_quality(
    items: Any,
    source_results: Optional[Any] = None,
) -> Dict[str, Any]:
    """Assess shallow usability without claiming factual/card-news readiness."""

    raw_items = items if isinstance(items, list) else []
    valid_items = [item for item in raw_items if isinstance(item, dict)]
    malformed_item_count = len(raw_items) - len(valid_items)

    raw_source_results = source_results if isinstance(source_results, list) else []
    valid_source_results = [
        result for result in raw_source_results if isinstance(result, dict)
    ]

    item_count = len(valid_items)
    fallback_item_count = sum(
        1 for item in valid_items if item.get("is_fallback") is True
    )
    live_item_count = sum(
        1 for item in valid_items if item.get("is_fallback") is False
    )
    unknown_fallback_state_count = (
        item_count - fallback_item_count - live_item_count
    )

    usable_item_count = 0
    for item in valid_items:
        title = _first_present(item, ("title", "keyword"))
        link = _first_present(item, ("link", "url"))
        source_id = _first_present(item, ("source_id", "source"))
        if title and link and source_id and item.get("is_fallback") is False:
            usable_item_count += 1

    fallback_ratio = _ratio(fallback_item_count, item_count)
    usable_ratio = _ratio(usable_item_count, item_count)

    if item_count == 0:
        status = STATUS_EMPTY
    elif (
        usable_ratio >= USABLE_RATIO_THRESHOLD
        and fallback_ratio <= MAX_FALLBACK_RATIO
    ):
        status = STATUS_USABLE_SHALLOW
    else:
        status = STATUS_LIMITED

    source_ids = []
    for item in valid_items:
        source_id = _first_present(item, ("source_id", "source"))
        if source_id is not None and str(source_id) not in source_ids:
            source_ids.append(str(source_id))
    for result in valid_source_results:
        source_id = result.get("source_id")
        if _present(source_id) and str(source_id) not in source_ids:
            source_ids.append(str(source_id))

    required_field_completeness = {
        "title": _availability(valid_items, "title", ("keyword",)),
        "link": _availability(valid_items, "link", ("url",)),
        "source_id": _availability(valid_items, "source_id", ("source",)),
    }
    optional_evidence_availability = {
        field: _availability(valid_items, field)
        for field in OPTIONAL_EVIDENCE_FIELDS
    }
    visible_metric_availability = {
        field: _visible_metric_availability(
            valid_items, field, VISIBLE_METRIC_ALIASES.get(field, ())
        )
        for field in VISIBLE_METRIC_FIELDS
    }

    return {
        "schema_version": "collection_quality_summary_v1",
        "status": status,
        "scope": "shallow_collection_quality_only",
        "cardnews_readiness_claimed": False,
        "factual_verification_claimed": False,
        "item_count": item_count,
        "malformed_item_count": malformed_item_count,
        "source_count": len(source_ids),
        "source_ids": source_ids,
        "source_result_count": len(valid_source_results),
        "successful_source_count": sum(
            1 for result in valid_source_results if result.get("success") is True
        ),
        "live_item_count": live_item_count,
        "fallback_item_count": fallback_item_count,
        "unknown_fallback_state_count": unknown_fallback_state_count,
        "usable_shallow_item_count": usable_item_count,
        "live_ratio": _ratio(live_item_count, item_count),
        "fallback_ratio": fallback_ratio,
        "usable_shallow_ratio": usable_ratio,
        "required_field_completeness": required_field_completeness,
        "optional_evidence_availability": optional_evidence_availability,
        "visible_metric_availability": visible_metric_availability,
        "thresholds": {
            "usable_shallow_ratio_min": USABLE_RATIO_THRESHOLD,
            "fallback_ratio_max": MAX_FALLBACK_RATIO,
            "requires_explicit_non_fallback": True,
        },
    }
