"""Integration facade for multi-account CardNews discovery and planning.

The facade connects already-produced shallow collection data to clustering,
Stage-1/2 classification, exclusive account routing, per-account TOP selection,
and variable-slide planning.  It never performs collection, storage writes,
rendering, publishing, browser/API work, or WorkflowEngine integration.

Instagram pattern bindings are optional caller-supplied inputs.  When absent,
the slide planner may use only its explicitly labelled configured fallback; the
facade never claims that fallback was Instagram-learned.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Optional, Sequence

from modules.card_news.account_variable_slide_planner import (
    run_account_variable_slide_planner,
)
from modules.card_news.learning_design_compiler import (
    compile_learning_driven_blueprint,
)
from modules.source_intake.account_candidate_router import run_account_candidate_router
from modules.source_intake.account_instagram_pattern_binder import (
    run_account_instagram_pattern_binder,
)
from modules.source_intake.account_top_topic_selector import run_account_top_topic_selector
from modules.source_intake.category_candidate_pipeline import run_category_candidate_pipeline
from modules.source_intake.same_event_topic_clusterer import run_same_event_topic_clustering
from modules.source_intake.reviewed_watch_promotion_gate import (
    run_reviewed_watch_promotion_gate,
)
from modules.source_intake.watch_candidate_review_queue import (
    run_watch_candidate_review_queue,
)


MULTI_ACCOUNT_DISCOVERY_PIPELINE_VERSION = "multi_account_card_news_discovery_pipeline_v1"
DEEP_ACCOUNT_IDS = {
    "account_a_news_incident": "A",
    "account_b_issue_story": "B",
    "account_c_beauty_fashion": "C",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _closed(reason_code: str, reason: str, stages: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    return {
        "schema_version": MULTI_ACCOUNT_DISCOVERY_PIPELINE_VERSION,
        "status": "closed",
        "fallback_used": True,
        "reason_code": reason_code,
        "reason": reason,
        "stages": copy.deepcopy(dict(stages or {})),
        "top_topics": {},
        "slide_plans": {},
        "watch_review_queue": {},
        "reviewed_watch_promotion": {},
        "instagram_pattern_binding_status": "unavailable",
        "production_ready": False,
        "publishing_ready": False,
    }


def _validate_collection_result(collection_result: Any) -> Optional[str]:
    if not isinstance(collection_result, Mapping):
        return "collection_result_must_be_object"
    if collection_result.get("schema_version") != "daily_shallow_collection_v1":
        return "unexpected_collection_schema"
    if collection_result.get("status") != "completed":
        return "collection_not_completed"
    items = collection_result.get("items")
    if not isinstance(items, list):
        return "collection_items_must_be_list"
    if not items:
        return "collection_items_empty"
    if any(not isinstance(item, Mapping) for item in items):
        return "collection_item_must_be_object"
    return None


def _cluster_candidates(
    collection_items: Sequence[Mapping[str, Any]],
    clusters: Sequence[Mapping[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build one Stage-2 candidate per cluster from the original representative row."""

    candidates: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []
    for cluster in clusters:
        cluster_id = _text(cluster.get("cluster_id"))
        indexes = cluster.get("indexes")
        if not cluster_id or not isinstance(indexes, list) or not indexes:
            diagnostics.append({"cluster_id": cluster_id or None, "reason_code": "invalid_cluster_identity"})
            continue
        representative_index = indexes[0]
        if (
            not isinstance(representative_index, int)
            or isinstance(representative_index, bool)
            or representative_index < 0
            or representative_index >= len(collection_items)
        ):
            diagnostics.append({"cluster_id": cluster_id, "reason_code": "representative_index_out_of_range"})
            continue

        candidate = copy.deepcopy(dict(collection_items[representative_index]))
        candidate["candidate_id"] = f"topic:{cluster_id}"
        candidate["cluster_id"] = cluster_id
        candidate["title"] = cluster.get("representative_title") or candidate.get("title")
        candidate["representative_title"] = cluster.get("representative_title")
        candidate["link"] = cluster.get("representative_link") or candidate.get("link")
        candidate["published_at"] = cluster.get("earliest_publication_time") or candidate.get("published_at")
        candidate["source_refs"] = copy.deepcopy(cluster.get("source_observations", []))
        candidate["recurrence"] = copy.deepcopy(cluster.get("recurrence"))
        candidate["cluster_confidence"] = copy.deepcopy(cluster.get("confidence"))
        candidate["source_observation_count"] = copy.deepcopy(cluster.get("source_observations_count"))
        candidate["independent_origin_count"] = copy.deepcopy(cluster.get("independent_origin_count"))
        candidate["cluster_match_reasons"] = copy.deepcopy(cluster.get("match_reasons", []))
        candidate["cluster_match_provenance"] = copy.deepcopy(cluster.get("match_provenance", []))
        candidate["cluster_status"] = copy.deepcopy(cluster.get("status"))
        candidate["category_hints"] = copy.deepcopy(cluster.get("category_hints", []))
        candidates.append(candidate)
    return candidates, diagnostics


def _eligible_collection_items(collection_result: Mapping[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Keep only honest live rows from sources reported successful in this payload."""

    successful_sources = {
        _text(result.get("source_id"))
        for result in collection_result.get("source_results", [])
        if isinstance(result, Mapping) and result.get("success") is True
    }
    eligible: List[Dict[str, Any]] = []
    filtered: List[Dict[str, Any]] = []
    for index, raw_item in enumerate(collection_result.get("items", [])):
        item = copy.deepcopy(dict(raw_item))
        source_id = _text(item.get("source_id"))
        reason_code = ""
        if item.get("is_fallback") is True:
            reason_code = "fallback_item_excluded"
        elif source_id not in successful_sources:
            reason_code = "source_not_successful_in_same_payload"
        elif not _text(item.get("title") or item.get("keyword")):
            reason_code = "missing_title"
        elif not _text(item.get("link") or item.get("url")):
            reason_code = "missing_link"
        if reason_code:
            filtered.append({"input_index": index, "source_id": source_id or None, "reason_code": reason_code})
            continue
        eligible.append(item)
    return eligible, filtered


def _binding_for_topic(
    topic: Mapping[str, Any],
    binder_result: Optional[Mapping[str, Any]],
) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Return planner guidance and the full evidence reference record.

    Role-level CANDIDATE/VERIFIED records remain reference-tier evidence, but
    their approved guidance is no longer discarded before planning.  The
    planner receives the guidance separately from a production pattern so it
    cannot be mistaken for a promoted or performance-validated layout.
    """

    if not isinstance(binder_result, Mapping):
        return None, None
    bindings_by_account = binder_result.get("bindings_by_account")
    if not isinstance(bindings_by_account, Mapping):
        return None, None
    account_bindings = bindings_by_account.get(_text(topic.get("account_id")))
    if not isinstance(account_bindings, list):
        return None, None
    candidate_id = _text(topic.get("candidate_id"))
    cluster_id = _text(topic.get("cluster_id"))
    for raw_binding in account_bindings:
        if not isinstance(raw_binding, Mapping):
            continue
        if (
            _text(raw_binding.get("candidate_id")) != candidate_id
            or _text(raw_binding.get("cluster_id")) != cluster_id
        ):
            continue
        reference = copy.deepcopy(dict(raw_binding))
        role_guidance: Dict[str, Dict[str, Any]] = {}
        roles = raw_binding.get("roles")
        if isinstance(roles, Mapping):
            for role, raw_role in roles.items():
                if not isinstance(raw_role, Mapping) or raw_role.get("bound") is not True:
                    continue
                recommended_action = _text(raw_role.get("recommended_action"))
                if not recommended_action:
                    continue
                role_guidance[str(role)] = {
                    "pattern_id": copy.deepcopy(raw_role.get("pattern_id")),
                    "pattern_name": copy.deepcopy(raw_role.get("pattern_name")),
                    "pattern_status": copy.deepcopy(raw_role.get("pattern_status")),
                    "binding_tier": copy.deepcopy(raw_role.get("binding_tier")),
                    "recommended_action": recommended_action,
                    "prohibited_actions": copy.deepcopy(raw_role.get("prohibited_actions", [])),
                    "provenance": copy.deepcopy(raw_role.get("provenance", {})),
                }
                for field in (
                    "visual_direction",
                    "emotion",
                    "mood",
                    "palette",
                    "palette_intent",
                    "color_palette",
                    "visual_relevance_labels",
                ):
                    if field in raw_role:
                        role_guidance[str(role)][field] = copy.deepcopy(
                            raw_role.get(field)
                        )
        if not role_guidance:
            reference["planner_bridge_status"] = "no_role_guidance_available"
            return None, reference

        binding = {
            "status": "reference_guidance",
            "mode": "reference_guidance",
            "account_id": copy.deepcopy(raw_binding.get("account_id")),
            "candidate_id": copy.deepcopy(raw_binding.get("candidate_id")),
            "cluster_id": copy.deepcopy(raw_binding.get("cluster_id")),
            "primary_category": copy.deepcopy(raw_binding.get("primary_category")),
            "production_planning_eligible": raw_binding.get("production_planning_eligible") is True,
            "reference_only": raw_binding.get("production_planning_eligible") is not True,
            "role_guidance": role_guidance,
        }
        reference["planner_bridge_status"] = "reference_guidance_supplied"
        reference["planner_guidance_roles"] = sorted(role_guidance)
        return binding, reference
    return None, None


def _build_slide_plans(
    top_result: Mapping[str, Any],
    binder_result: Optional[Mapping[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    plans: Dict[str, List[Dict[str, Any]]] = {}
    top_by_account = top_result.get("top_by_account")
    if not isinstance(top_by_account, Mapping):
        return plans
    for account_id, topics in top_by_account.items():
        account_plans: List[Dict[str, Any]] = []
        if isinstance(topics, list):
            for topic in topics:
                if not isinstance(topic, Mapping):
                    continue
                binding, reference = _binding_for_topic(topic, binder_result)
                plan = run_account_variable_slide_planner(
                    copy.deepcopy(dict(topic)),
                    instagram_pattern_binding=binding,
                )
                plan["instagram_binding_supplied"] = binding is not None
                plan["instagram_pattern_reference"] = reference
                plan["instagram_pattern_consumed"] = bool(
                    plan.get("learning_guidance_consumed")
                    or (
                        binding is not None
                        and plan.get("selected_pattern", {}).get("source")
                        == "instagram_pattern_binding"
                    )
                )
                if reference is not None and binding is None:
                    plan["instagram_pattern_nonconsumption_reason"] = (
                        "no_usable_role_guidance_or_concrete_slide_pattern"
                    )
                plan["production_blueprint"] = compile_learning_driven_blueprint(
                    topic,
                    plan,
                    pattern_reference=reference,
                )
                account_plans.append(plan)
        plans[str(account_id)] = account_plans
    return plans


def _source_urls(topic: Mapping[str, Any]) -> List[str]:
    urls: List[str] = []
    for value in (topic.get("link"), topic.get("url")):
        text = _text(value)
        if text and text not in urls:
            urls.append(text)
    for reference in topic.get("source_refs", []):
        if not isinstance(reference, Mapping):
            continue
        text = _text(reference.get("link") or reference.get("url"))
        if text and text not in urls:
            urls.append(text)
    return urls


def _build_deep_discovery_requests(top_result: Mapping[str, Any]) -> Dict[str, Any]:
    requests: List[Dict[str, Any]] = []
    top_by_account = top_result.get("top_by_account")
    if isinstance(top_by_account, Mapping):
        for account_id, topics in top_by_account.items():
            deep_account = DEEP_ACCOUNT_IDS.get(str(account_id))
            if not deep_account or not isinstance(topics, list):
                continue
            for topic in topics:
                if not isinstance(topic, Mapping):
                    continue
                candidate_id = _text(topic.get("candidate_id"))
                if not candidate_id:
                    continue
                requests.append(
                    {
                        "account": deep_account,
                        "candidate_id": candidate_id,
                        "title": _text(topic.get("title")),
                        "category": _text(topic.get("primary_category")),
                        "source_urls": _source_urls(topic),
                    }
                )
    return {
        "schema_version": "account_deep_discovery_request_queue_v1",
        "status": "ready" if requests else "empty",
        "request_count": len(requests),
        "requests": requests,
        "network_executed": False,
    }


def _body_units(body: str) -> List[str]:
    units: List[str] = []
    for paragraph in body.splitlines():
        normalized = " ".join(paragraph.split())
        if normalized:
            units.append(normalized)
        if len(units) >= 19:
            break
    if not units and body.strip():
        units.append(" ".join(body.split()))
    return units


def _merge_deep_discovery(
    top_result: Mapping[str, Any],
    deep_result: Optional[Mapping[str, Any]],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    enriched = copy.deepcopy(dict(top_result))
    if not isinstance(deep_result, Mapping):
        return enriched, {
            "status": "not_supplied",
            "reason_code": "existing_deep_discovery_result_required",
            "matched_topic_count": 0,
            "body_count": 0,
            "usable_media_count": 0,
        }
    if (
        deep_result.get("schema_version") != "account_deep_discovery_result_v1"
        or deep_result.get("status") != "completed"
    ):
        return enriched, {
            "status": "closed",
            "reason_code": "invalid_or_incomplete_deep_discovery_result",
            "matched_topic_count": 0,
            "body_count": 0,
            "usable_media_count": 0,
        }

    by_candidate: Dict[str, List[Mapping[str, Any]]] = {}
    accounts = deep_result.get("accounts")
    if isinstance(accounts, Mapping):
        for account_data in accounts.values():
            results = account_data.get("results") if isinstance(account_data, Mapping) else None
            for result in results if isinstance(results, list) else []:
                if not isinstance(result, Mapping):
                    continue
                candidate_id = _text(result.get("candidate_id"))
                if candidate_id:
                    by_candidate.setdefault(candidate_id, []).append(result)

    matched = 0
    body_count = 0
    usable_media_count = 0
    top_by_account = enriched.get("top_by_account")
    if isinstance(top_by_account, Mapping):
        for topics in top_by_account.values():
            if not isinstance(topics, list):
                continue
            for topic in topics:
                if not isinstance(topic, dict):
                    continue
                results = by_candidate.get(_text(topic.get("candidate_id")), [])
                if not results:
                    continue
                article_bodies: List[Dict[str, Any]] = []
                key_points: List[str] = []
                assets: List[Dict[str, Any]] = []
                related_sources: List[Dict[str, Any]] = []
                comments: List[Dict[str, Any]] = []
                reconstruction_scenes: List[Dict[str, Any]] = []
                for result in results:
                    for operation in result.get("operations", []):
                        if not isinstance(operation, Mapping):
                            continue
                        role = _text(operation.get("artifact_role"))
                        for raw_asset in operation.get("assets", []):
                            if not isinstance(raw_asset, Mapping):
                                continue
                            asset = copy.deepcopy(dict(raw_asset))
                            if role == "article_body":
                                body = _text(asset.get("body"))
                                if body:
                                    article_bodies.append(asset)
                                    key_points.extend(_body_units(body))
                                continue
                            if role == "real_comment":
                                if asset.get("is_real_comment") is True:
                                    comments.append(asset)
                                continue
                            if role == "related_news":
                                related_url = _text(asset.get("url"))
                                related_title = _text(asset.get("title"))
                                if related_url and related_title:
                                    related_sources.append(asset)
                                    description = _text(asset.get("description"))
                                    if description:
                                        key_points.append(description)
                                continue
                            if role == "reconstruction_scene_fact":
                                reconstruction_scenes.append(asset)
                                continue
                            if (
                                asset.get("usable_in_production") is True
                                and asset.get("reference_only") is not True
                                and _text(asset.get("url") or asset.get("remote_url"))
                            ):
                                assets.append(asset)
                if not (
                    article_bodies
                    or assets
                    or related_sources
                    or comments
                    or reconstruction_scenes
                ):
                    continue
                matched += 1
                body_count += len(article_bodies)
                usable_media_count += len(assets)
                topic["article_bodies"] = article_bodies
                topic["key_points"] = key_points[:19]
                topic["assets"] = assets
                topic["related_sources"] = related_sources
                topic["comments"] = comments
                topic["reconstruction_scenes"] = reconstruction_scenes
                topic["deep_content_status"] = "ready"
                topic["deep_content_provenance"] = {
                    "schema_version": deep_result.get("schema_version"),
                    "network_executed_by_pipeline": False,
                }
    return enriched, {
        "status": "merged" if matched else "unmatched",
        "reason_code": "ok" if matched else "no_deep_result_matched_top_topics",
        "matched_topic_count": matched,
        "body_count": body_count,
        "usable_media_count": usable_media_count,
        "network_executed_by_pipeline": False,
    }


def run_multi_account_card_news_discovery_pipeline(
    collection_result: Any,
    *,
    instagram_pattern_records: Optional[Sequence[Any]] = None,
    instagram_reference_time: Optional[str] = None,
    watch_review_records: Optional[Mapping[str, Any]] = None,
    deep_discovery_result: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Connect completed standalone stages without external side effects."""

    validation_error = _validate_collection_result(collection_result)
    if validation_error:
        return _closed("invalid_collection_result", validation_error)

    stages: Dict[str, Any] = {
        "collection": {
            "status": "accepted",
            "schema_version": collection_result.get("schema_version"),
            "item_count": len(collection_result["items"]),
            "collection_executed_by_facade": False,
        }
    }
    try:
        collection_items, collection_filtered = _eligible_collection_items(collection_result)
        stages["collection_eligibility"] = {
            "status": "ok" if collection_items else "closed",
            "eligible_count": len(collection_items),
            "filtered_count": len(collection_filtered),
            "filtered": collection_filtered,
            "fallback_items_allowed": False,
        }
        if not collection_items:
            return _closed("no_eligible_live_collection_items", "no honest live item passed collection eligibility", stages)
        clustering = run_same_event_topic_clustering(collection_items)
        stages["clustering"] = clustering
        if clustering.get("status") != "ok":
            return _closed("clustering_closed", _text(clustering.get("reason")) or "clustering closed", stages)

        cluster_candidates, adaptation_diagnostics = _cluster_candidates(
            collection_items,
            clustering.get("clusters", []),
        )
        stages["cluster_adaptation"] = {
            "status": "ok" if cluster_candidates else "closed",
            "candidate_count": len(cluster_candidates),
            "diagnostics": adaptation_diagnostics,
        }
        if not cluster_candidates:
            return _closed("cluster_adaptation_closed", "no cluster candidate could be adapted", stages)

        category = run_category_candidate_pipeline(cluster_candidates)
        stages["category_stage2"] = category
        if category.get("status") != "ok":
            return _closed("category_stage2_closed", _text(category.get("reason")) or "category stage closed", stages)

        watch_review_queue = run_watch_candidate_review_queue(
            category.get("items", []),
            review_records=watch_review_records,
        )
        stages["watch_review_queue"] = watch_review_queue

        reviewed_watch_promotion = run_reviewed_watch_promotion_gate(watch_review_queue)
        stages["reviewed_watch_promotion"] = reviewed_watch_promotion
        original_go_items = [
            copy.deepcopy(item)
            for item in category.get("items", [])
            if isinstance(item, Mapping) and item.get("decision") == "GO"
        ]
        routing_input = original_go_items + copy.deepcopy(
            reviewed_watch_promotion.get("routing_candidates", [])
        )
        account_routing = run_account_candidate_router(routing_input)
        stages["account_routing"] = account_routing
        top_selection = run_account_top_topic_selector(account_routing)
        stages["top_selection"] = top_selection
        deep_requests = _build_deep_discovery_requests(top_selection)
        stages["deep_discovery_requests"] = deep_requests
        planning_selection, deep_bridge = _merge_deep_discovery(
            top_selection,
            deep_discovery_result,
        )
        stages["deep_content_bridge"] = deep_bridge

        instagram_binding = run_account_instagram_pattern_binder(
            planning_selection,
            pattern_records=instagram_pattern_records,
            reference_time=instagram_reference_time,
        )
        stages["instagram_pattern_binding"] = instagram_binding

        slide_plans = _build_slide_plans(planning_selection, instagram_binding)
        planned_count = sum(
            1
            for plans in slide_plans.values()
            for plan in plans
            if plan.get("status") in {"planned", "planned_with_fallback"}
        )
        deferred_count = sum(
            1
            for plans in slide_plans.values()
            for plan in plans
            if plan.get("status") == "planning_deferred"
        )
        stages["variable_slide_planning"] = {
            "status": "planned" if planned_count else ("deferred" if deferred_count else "closed"),
            "planned_count": planned_count,
            "deferred_count": deferred_count,
            "plans": slide_plans,
        }

        top_count = int(top_selection.get("top_count") or 0)
        if planned_count:
            status = "planning_ready"
            reason_code = (
                "ok_with_production_pattern_bindings"
                if int(instagram_binding.get("production_approved_binding_count") or 0) > 0
                else "ok_with_configured_slide_fallback"
            )
        elif deferred_count:
            status = "top_topics_ready"
            reason_code = "deep_content_required_for_final_slide_count"
        elif top_count:
            status = "top_topics_ready"
            reason_code = "slide_planning_not_ready"
        elif account_routing.get("status") == "routed":
            status = "account_candidates_ready"
            reason_code = "no_top_topics_selected"
        elif int(watch_review_queue.get("queued_count") or 0) > 0:
            status = "review_queue_ready"
            reason_code = "watch_candidates_awaiting_human_review"
        else:
            status = "closed"
            reason_code = _text(account_routing.get("reason_code")) or "no_account_candidates"

        return {
            "schema_version": MULTI_ACCOUNT_DISCOVERY_PIPELINE_VERSION,
            "status": status,
            "fallback_used": int(instagram_binding.get("production_approved_binding_count") or 0) == 0,
            "reason_code": reason_code,
            "reason": "standalone multi-account discovery stages connected",
            "stages": stages,
            "top_topics": copy.deepcopy(planning_selection.get("top_by_account", {})),
            "slide_plans": slide_plans,
            "deep_discovery_requests": copy.deepcopy(deep_requests),
            "deep_content_bridge": copy.deepcopy(deep_bridge),
            "watch_review_queue": copy.deepcopy(watch_review_queue),
            "reviewed_watch_promotion": copy.deepcopy(reviewed_watch_promotion),
            "reviewed_watch_promoted_count": int(
                reviewed_watch_promotion.get("promoted_count") or 0
            ),
            "instagram_pattern_binding_status": instagram_binding.get("status", "unavailable"),
            "instagram_pattern_binding_reason_code": instagram_binding.get("reason_code"),
            "instagram_production_binding_count": int(
                instagram_binding.get("production_approved_binding_count") or 0
            ),
            "instagram_reference_only_binding_count": int(
                instagram_binding.get("reference_only_binding_count") or 0
            ),
            "instagram_learning_claimed": False,
            "production_ready": False,
            "publishing_ready": False,
        }
    except Exception as exc:
        return _closed(
            "integration_exception",
            f"multi-account discovery integration failed safely: {type(exc).__name__}",
            stages,
        )


__all__ = [
    "MULTI_ACCOUNT_DISCOVERY_PIPELINE_VERSION",
    "run_multi_account_card_news_discovery_pipeline",
]
