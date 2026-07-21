"""Brand Connect second-stage matching: after owner grading, before final four.

Composes catalog normalization and candidate matching into one deterministic,
networkless stage. Only owner-graded (1/2/3) candidates are annotated. A missing
catalog leaves the stage explicitly incomplete instead of pretending readiness,
and unmatched candidates are never penalized for lacking a commerce link.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from modules.brandconnect.brandconnect_candidate_matcher import (
    match_candidate_to_products,
    prepare_products_for_matching,
)
from modules.brandconnect.brandconnect_product_catalog import normalize_brandconnect_catalog
from modules.brandconnect.relation_aware_candidate_matcher import (
    match_candidate_with_relations,
    prepare_relation_index,
)

STAGE_SCHEMA_VERSION = "brandconnect_second_stage.v1"
STAGE_POSITION = "after_owner_grading_before_final_four"
GRADED = {"1", "2", "3"}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def run_brandconnect_second_stage(
    candidates: Any,
    ratings: Any,
    catalog_snapshot: Any,
    threshold: float = None,
    max_matches: int = None,
    relation_index: Any = None,
) -> Dict[str, Any]:
    """Annotate graded candidates with commerce match results; never fabricate."""

    catalog = normalize_brandconnect_catalog(catalog_snapshot)
    catalog_ready = catalog["status"] == "ready"
    prepared_products = prepare_products_for_matching(catalog["products"]) if catalog_ready else []
    prepared_relations = (
        prepare_relation_index(relation_index, prepared_products)
        if catalog_ready and isinstance(relation_index, Mapping) and relation_index
        else None
    )

    graded: List[Mapping[str, Any]] = []
    for candidate in candidates if isinstance(candidates, list) else []:
        if not isinstance(candidate, Mapping):
            continue
        candidate_id = _text(str(candidate.get("id", "")) or "")
        decision = ratings.get(candidate_id) if isinstance(ratings, Mapping) else None
        grade = _text(str(decision.get("grade", ""))) if isinstance(decision, Mapping) else ""
        if grade in GRADED:
            graded.append(candidate)

    annotations = []
    for candidate in graded:
        candidate_id = _text(str(candidate.get("id", "")))
        base = {
            "candidate_id": candidate_id,
            "title": _text(candidate.get("title")),
            "category": _text(candidate.get("category")) or _text(candidate.get("raw_category")),
        }
        if not catalog_ready:
            annotations.append(
                {
                    **base,
                    "commerce_status": "catalog_unavailable",
                    "commerce_fit": None,
                    "penalized": False,
                    "matches": [],
                }
            )
            continue
        kwargs = {}
        if threshold is not None:
            kwargs["threshold"] = threshold
        if max_matches is not None:
            kwargs["max_matches"] = max_matches
        if prepared_relations is not None:
            outcome = match_candidate_with_relations(
                candidate,
                prepared_products,
                relation_index=prepared_relations,
                **kwargs,
            )
        else:
            outcome = match_candidate_to_products(candidate, prepared_products, **kwargs)
        annotations.append(
            {
                **base,
                "commerce_status": outcome["match_status"],
                "commerce_fit": outcome["commerce_fit"],
                "penalized": False,
                "matches": outcome["matches"],
                "relation_signals_used": outcome.get("relation_signals_used", False),
            }
        )

    return {
        "schema_version": STAGE_SCHEMA_VERSION,
        "stage_position": STAGE_POSITION,
        "status": "completed" if catalog_ready else "incomplete_catalog",
        "complete": catalog_ready,
        "catalog": {
            "status": catalog["status"],
            "source": catalog["source"],
            "captured_at": catalog["captured_at"],
            "product_count": catalog["product_count"],
            "dropped": catalog["dropped"],
        },
        "graded_candidate_count": len(graded),
        "annotations": annotations,
        "network_used": False,
        "login_automation": False,
        "link_issuance": False,
        "publishing": False,
    }


__all__ = ["run_brandconnect_second_stage", "STAGE_SCHEMA_VERSION", "STAGE_POSITION"]
