"""Fail-safe composition for selected CardNews discovery and render preparation.

The flow performs no network work by itself.  Network access remains confined to
the explicitly injected discovery provider, while bridge and plan-builder stages
are pure injected contracts.  Missing downstream stages are reported honestly
instead of fabricating production plans or evidence.
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Mapping

from modules.card_news.selected_candidate_render_input_adapter import (
    build_selected_candidate_render_inputs,
)
from modules.card_news.selected_candidate_production_planner import (
    build_selected_candidate_production_plan,
)
from modules.content.commerce_story_content_adapter import (
    build_commerce_story_content_inputs,
)
from modules.source_intake.account_deep_discovery_runner import (
    MAX_REQUESTS_PER_ACCOUNT,
    run_account_deep_discovery,
)
from modules.source_intake.candidate_selection_signal_normalizer import (
    normalize_candidate_selection_signals,
)
from modules.source_intake.discovery_result_render_bridge import (
    run_discovery_result_render_bridge,
)


SCHEMA_VERSION = "selected_candidate_production_flow_v1"


def _normalize_selection(selection: Any) -> Any:
    """Normalize candidate signals without mutating the owner's selection."""

    normalized = copy.deepcopy(selection)
    if isinstance(normalized, list):
        return [
            normalize_candidate_selection_signals(item)
            if isinstance(item, Mapping)
            else item
            for item in normalized
        ]
    if not isinstance(normalized, Mapping):
        return normalized

    normalized = dict(normalized)
    accounts = normalized.get("accounts")
    if isinstance(accounts, Mapping):
        normalized_accounts: Dict[str, Any] = {}
        for account, raw_bucket in accounts.items():
            if not isinstance(raw_bucket, Mapping):
                normalized_accounts[str(account)] = raw_bucket
                continue
            bucket = dict(raw_bucket)
            selected = bucket.get("selected")
            if isinstance(selected, list):
                bucket["selected"] = [
                    normalize_candidate_selection_signals(item)
                    if isinstance(item, Mapping)
                    else item
                    for item in selected
                ]
            normalized_accounts[str(account)] = bucket
        normalized["accounts"] = normalized_accounts
    elif isinstance(normalized.get("requests"), list):
        normalized["requests"] = [
            normalize_candidate_selection_signals(item)
            if isinstance(item, Mapping)
            else item
            for item in normalized["requests"]
        ]
    return normalized


def _closed(reason_code: str, reason: str, **stages: Any) -> Dict[str, Any]:
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "closed",
        "reason_code": reason_code,
        "reason": reason,
        "network_executed": False,
        "render_inputs": [],
        "failures": [],
    }
    result.update(stages)
    return result


def _plans(value: Any) -> List[Mapping[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)]
    if isinstance(value, Mapping):
        raw = value.get("plans")
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, Mapping)]
        if value.get("schema_version") == "selected_candidate_production_plan_v1":
            return [value]
    return []


def _candidate_index(selection: Any) -> Dict[str, Dict[str, Any]]:
    entries: List[Mapping[str, Any]] = []
    if isinstance(selection, list):
        entries = [item for item in selection if isinstance(item, Mapping)]
    elif isinstance(selection, Mapping):
        accounts = selection.get("accounts")
        if isinstance(accounts, Mapping):
            for account, raw_bucket in accounts.items():
                selected = raw_bucket.get("selected") if isinstance(raw_bucket, Mapping) else None
                for item in selected if isinstance(selected, list) else []:
                    if isinstance(item, Mapping):
                        entries.append({**dict(item), "account": str(account).upper()})
        elif isinstance(selection.get("requests"), list):
            entries = [
                item for item in selection["requests"] if isinstance(item, Mapping)
            ]
    return {
        str(item.get("candidate_id") or item.get("id")): copy.deepcopy(dict(item))
        for item in entries
        if str(item.get("candidate_id") or item.get("id") or "").strip()
    }


def _default_production_plans(
    normalized_selection: Any,
    discovery: Mapping[str, Any],
    bridged: Any,
) -> Dict[str, Any]:
    """Adapt bridge rows to the existing evidence-bound production planner."""

    del discovery
    index = _candidate_index(normalized_selection)
    rows = bridged.get("candidates") if isinstance(bridged, Mapping) else None
    plans: List[Dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        candidate_id = str(row.get("candidate_id") or "").strip()
        candidate = copy.deepcopy(index.get(candidate_id, {}))
        if not candidate:
            continue
        candidate.setdefault("account", str(row.get("account") or "").upper())

        all_source_rows = [
            item
            for item in row.get("media_source_inputs", [])
            if isinstance(item, Mapping)
        ]
        media_rows = [
            item for item in all_source_rows if item.get("render_allowed") is True
        ]
        assets: List[Dict[str, Any]] = []
        source_refs: List[str] = []
        summaries: List[str] = []
        article_bodies: List[str] = []
        evidence_points: List[str] = []
        comments: List[Dict[str, Any]] = []
        for media in all_source_rows:
            raw = media.get("raw_source_asset")
            raw = raw if isinstance(raw, Mapping) else {}
            source_url = str(media.get("source_url") or "").strip()
            if source_url and source_url not in source_refs:
                source_refs.append(source_url)
            summary = str(raw.get("summary") or raw.get("description") or "").strip()
            if summary and summary not in summaries:
                summaries.append(summary)
            if str(media.get("operation_artifact_role") or "") == "article_body":
                body = str(
                    raw.get("article_body")
                    or raw.get("body")
                    or raw.get("content")
                    or raw.get("text")
                    or ""
                ).strip()
                if body and body not in article_bodies:
                    article_bodies.append(body)
                raw_points = raw.get("key_points") or raw.get("facts") or raw.get("claims")
                if isinstance(raw_points, list):
                    for point in raw_points:
                        point_text = str(point or "").strip()
                        if point_text and point_text not in evidence_points:
                            evidence_points.append(point_text)
            provenance = media.get("real_comment_provenance")
            if isinstance(provenance, Mapping) and provenance.get("is_real_comment") is True:
                comments.append(
                    {
                        "comment_id": provenance.get("comment_id"),
                        "text": provenance.get("text"),
                        "identity_masked": provenance.get("identity_masked") is True,
                        "is_real_comment": True,
                        "source_url": source_url,
                    }
                )

        for body in article_bodies:
            for paragraph in body.splitlines():
                paragraph = paragraph.strip()
                if paragraph and paragraph not in evidence_points:
                    evidence_points.append(paragraph)

        for position, media in enumerate(media_rows, start=1):
            raw = media.get("raw_source_asset")
            raw = raw if isinstance(raw, Mapping) else {}
            source_url = str(media.get("source_url") or "").strip()
            media_url = str(media.get("media_url") or "").strip()
            raw_type = str(media.get("media_type") or "").lower()
            media_type = {
                "youtube_video": "video",
                "news_article": "editorial",
            }.get(raw_type, raw_type or "editorial")
            assets.append(
                {
                    "asset_id": f"{candidate_id}-source-{position}",
                    "media_type": media_type,
                    "origin": "official" if "official" in str(media.get("operation_artifact_role") or "") else "source",
                    "asset_class": "source_evidence",
                    "remote_url": media_url,
                    "source_url": source_url,
                    "rights_status": str(media.get("rights_status") or "unrecorded"),
                    "role_hint": str(media.get("operation_artifact_role") or "source_context"),
                    "reference_only": bool(media.get("reference_only")),
                }
            )
        source_summary = summaries[0] if summaries else (evidence_points[0] if evidence_points else "")
        deep_bundle = {
            "status": "ready",
            "title": str(row.get("candidate_title") or candidate.get("title") or ""),
            "summary": source_summary,
            "feed_body": source_summary,
            "key_points": evidence_points[:20] or summaries[:20],
            "article_bodies": article_bodies,
            "source_refs": source_refs,
            "assets": assets,
            "comments": comments,
            "reconstruction_scenes": [],
            "content_type": str(candidate.get("category") or ""),
        }
        plan = build_selected_candidate_production_plan(candidate, deep_bundle)
        story_payload = {
            "schema_version": "candidate_commerce_story_briefs.v1",
            "candidates": [
                {
                    "candidate_id": candidate_id,
                    "title": str(candidate.get("title") or row.get("candidate_title") or ""),
                    "status": (
                        "ready"
                        if isinstance(candidate.get("commerce_story_briefs"), list)
                        and candidate.get("commerce_story_briefs")
                        else str(candidate.get("commerce_story_status") or "awaiting_briefs")
                    ),
                    "briefs": copy.deepcopy(candidate.get("commerce_story_briefs", [])),
                    "missing_products": [],
                }
            ],
        }
        adapted = build_commerce_story_content_inputs(story_payload)
        adapted_candidates = adapted.get("content_candidates", [])
        adapted_entry = adapted_candidates[0] if adapted_candidates else {}
        content_inputs = adapted_entry.get("content_inputs", []) if isinstance(adapted_entry, Mapping) else []
        if content_inputs:
            plan.setdefault("copy_plan", {})["commerce_story_inputs"] = copy.deepcopy(content_inputs)
            plan.setdefault("commerce", {})["story_content_status"] = "ready"
            plan["commerce"]["future_blog_seeds"] = [
                copy.deepcopy(item.get("future_blog_seed"))
                for item in content_inputs
                if item.get("future_blog_seed")
            ]
        else:
            plan.setdefault("commerce", {})["story_content_status"] = str(
                adapted_entry.get("status") or "not_available"
            )
        plans.append(plan)
    return {"plans": plans}


def run_selected_candidate_production_flow(
    selection: Any,
    provider: Any,
    discovery_bridge: Callable[[Mapping[str, Any]], Any] | None,
    production_plan_builder: Callable[[Any, Mapping[str, Any], Any], Any] | None = None,
    render_input_builder: Callable[[Any, Any], Mapping[str, Any]] = (
        build_selected_candidate_render_inputs
    ),
    max_per_account: int = MAX_REQUESTS_PER_ACCOUNT,
) -> Dict[str, Any]:
    """Run bounded selected-item preparation while keeping every stage honest."""

    normalized_selection = _normalize_selection(selection)
    discovery = run_account_deep_discovery(
        normalized_selection,
        provider,
        max_per_account=max_per_account,
    )
    if discovery.get("status") != "completed":
        result = _closed(
            discovery.get("reason_code", "discovery_closed"),
            discovery.get("reason", "deep discovery did not run"),
            normalized_selection=normalized_selection,
            discovery=discovery,
        )
        result["failures"] = copy.deepcopy(discovery.get("failures", []))
        return result

    if not callable(discovery_bridge):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "discovery_ready",
            "reason_code": "missing_discovery_bridge",
            "network_executed": bool(discovery.get("network_executed")),
            "normalized_selection": normalized_selection,
            "discovery": discovery,
            "bridge": None,
            "render_inputs": [],
            "failures": copy.deepcopy(discovery.get("failures", [])),
        }

    failures = copy.deepcopy(discovery.get("failures", []))
    try:
        bridged = discovery_bridge(discovery)
    except Exception as error:
        failures.append({"stage": "discovery_bridge", "error": str(error)})
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "partial",
            "reason_code": "discovery_bridge_failed",
            "network_executed": bool(discovery.get("network_executed")),
            "normalized_selection": normalized_selection,
            "discovery": discovery,
            "bridge": None,
            "render_inputs": [],
            "failures": failures,
        }

    if not callable(production_plan_builder):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "media_inputs_ready",
            "reason_code": "production_plan_builder_required",
            "network_executed": bool(discovery.get("network_executed")),
            "normalized_selection": normalized_selection,
            "discovery": discovery,
            "bridge": copy.deepcopy(bridged),
            "render_inputs": [],
            "failures": failures,
        }

    try:
        raw_plans = production_plan_builder(normalized_selection, discovery, bridged)
    except Exception as error:
        failures.append({"stage": "production_plan_builder", "error": str(error)})
        raw_plans = []

    plans = _plans(raw_plans)
    render_inputs: List[Dict[str, Any]] = []
    for plan in plans:
        try:
            rendered = render_input_builder(plan, None)
            render_inputs.append(copy.deepcopy(dict(rendered)))
        except Exception as error:
            failures.append(
                {
                    "stage": "render_input_builder",
                    "candidate_id": str(plan.get("candidate_id", "")),
                    "error": str(error),
                }
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "render_inputs_ready" if render_inputs else "partial",
        "reason_code": (
            "selected_discovery_render_flow_completed"
            if render_inputs
            else "no_render_inputs_built"
        ),
        "network_executed": bool(discovery.get("network_executed")),
        "normalized_selection": normalized_selection,
        "discovery": discovery,
        "bridge": copy.deepcopy(bridged),
        "production_plans": copy.deepcopy(plans),
        "render_inputs": render_inputs,
        "failures": failures,
    }


def run_default_selected_candidate_production_flow(
    selection: Any,
    provider: Any,
    max_per_account: int = MAX_REQUESTS_PER_ACCOUNT,
) -> Dict[str, Any]:
    """Run the repository's concrete bridge, planner and render-input adapters."""

    return run_selected_candidate_production_flow(
        selection=selection,
        provider=provider,
        discovery_bridge=run_discovery_result_render_bridge,
        production_plan_builder=_default_production_plans,
        render_input_builder=build_selected_candidate_render_inputs,
        max_per_account=max_per_account,
    )


__all__ = [
    "run_selected_candidate_production_flow",
    "run_default_selected_candidate_production_flow",
    "SCHEMA_VERSION",
]
