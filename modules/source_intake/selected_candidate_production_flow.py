"""Fail-safe composition for selected CardNews discovery and render preparation.

The flow performs no network work by itself.  Network access remains confined to
the explicitly injected discovery provider, while bridge and plan-builder stages
are pure injected contracts.  Missing downstream stages are reported honestly
instead of fabricating production plans or evidence.
"""

from __future__ import annotations

import copy
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Mapping
from urllib.parse import urlparse

from modules.card_news.selected_candidate_render_input_adapter import (
    build_selected_candidate_render_inputs,
)
from modules.card_news.selected_candidate_production_planner import (
    build_selected_candidate_production_plan,
)
from modules.card_news.reference_driven_production import (
    produce_reference_driven_slide,
)
from modules.card_news.story_comment_spotlight import (
    build_story_comment_spotlight,
)
from modules.design_learning.production_profile_compiler import (
    ProductionProfileCompiler,
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
    run_discovery_result_render_bridge_with_supplements,
)


SCHEMA_VERSION = "selected_candidate_production_flow_v1"
MAX_EVIDENCE_UNIT_CHARS = 170


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


def _display_source_label(copy_plan: Any) -> str:
    if not isinstance(copy_plan, Mapping):
        return "출처 · 원문"
    sources = copy_plan.get("source_credit")
    first = (
        str(sources[0]).strip()
        if isinstance(sources, list) and sources
        else ""
    )
    if not first:
        return "출처 · 원문"
    parsed = urlparse(first)
    host = parsed.netloc.lower().removeprefix("www.")
    return f"출처 · {host or '원문'}"


def _source_backed_resolved_copy(plan: Mapping[str, Any]) -> List[Dict[str, str]]:
    """Fill renderer copy gaps using only text already approved by the plan."""

    raw_slides = plan.get("slide_plan")
    slides = [item for item in raw_slides if isinstance(item, Mapping)] if isinstance(raw_slides, list) else []
    copy_plan = plan.get("copy_plan") if isinstance(plan.get("copy_plan"), Mapping) else {}
    title = str(plan.get("title") or "").strip()
    feed_body = str(copy_plan.get("feed_body") or "").strip()
    raw_points = copy_plan.get("key_points")
    key_points = [
        str(item).strip()
        for item in raw_points
        if isinstance(item, str) and item.strip()
    ] if isinstance(raw_points, list) else []

    resolved: List[Dict[str, str]] = []
    for index, slide in enumerate(slides):
        body = str(slide.get("body") or "").strip()
        if not body and key_points:
            body = key_points[min(index, len(key_points) - 1)]
        if not body:
            body = feed_body
        body = re.sub(r"https?://\S+\s*", "", body).strip()
        headline = str(slide.get("headline") or "").strip()
        if not headline or (index > 0 and headline == title):
            headline_source = re.sub(
                r"^\[[^\]:]{1,24}\]\s*",
                "",
                body,
            ).strip()
            headline = re.split(
                r"(?<=[.!?。！？])\s+",
                headline_source,
                maxsplit=1,
            )[0].strip()
            if len(headline) > 34:
                headline = headline[:34].rstrip() + "…"
        if not headline:
            headline = title
        resolved.append({"headline": headline, "body": body})
    return resolved


def _split_evidence_units(body: str) -> List[str]:
    """Split source text into readable units without rewriting its claims."""

    units: List[str] = []
    for raw_paragraph in str(body or "").splitlines():
        paragraph = re.sub(r"\s+", " ", raw_paragraph).strip()
        if not paragraph:
            continue
        sentences = [
            value.strip()
            for value in re.split(r"(?<=[.!?。！？])\s+", paragraph)
            if value.strip()
        ]
        if not sentences:
            sentences = [paragraph]
        current = ""
        for sentence in sentences:
            if current and len(current) + 1 + len(sentence) > MAX_EVIDENCE_UNIT_CHARS:
                units.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            units.append(current)
    return units


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
            comment_source = (
                provenance
                if isinstance(provenance, Mapping)
                else raw
                if raw.get("is_real_comment") is True
                else {}
            )
            if (
                isinstance(comment_source, Mapping)
                and comment_source.get("is_real_comment") is True
            ):
                comment_text = str(
                    comment_source.get("text")
                    or raw.get("text")
                    or ""
                ).strip()
                if not comment_text:
                    continue
                comments.append(
                    {
                        "comment_id": (
                            comment_source.get("comment_id")
                            or f"comment-{len(comments) + 1}"
                        ),
                        "text": comment_text,
                        "identity_masked": (
                            comment_source.get("identity_masked") is True
                        ),
                        "is_real_comment": True,
                        "source_url": source_url,
                        "screenshot_path": str(
                            raw.get("screenshot_path") or ""
                        ).strip(),
                        "original_screenshot_path": str(
                            raw.get("original_screenshot_path") or ""
                        ).strip(),
                        "comment_slide_eligible": (
                            raw.get("comment_slide_eligible") is True
                        ),
                    }
                )

        for body in article_bodies:
            for unit in _split_evidence_units(body):
                if unit not in evidence_points:
                    evidence_points.append(unit)
        evidence_points = [
            point
            for point in evidence_points
            if not (
                re.fullmatch(r"\[[^\]:]{1,24}\]", point)
                or re.fullmatch(
                    r"먼저 .{1,24} 기자의 .*보도입니다[.]?",
                    point,
                )
            )
        ]

        for position, media in enumerate(media_rows, start=1):
            raw = media.get("raw_source_asset")
            raw = raw if isinstance(raw, Mapping) else {}
            source_url = str(media.get("source_url") or "").strip()
            media_url = str(media.get("media_url") or "").strip()
            raw_type = str(media.get("media_type") or "").lower()
            artifact_role = str(media.get("operation_artifact_role") or "")
            if (
                raw.get("is_real_comment") is True
                or artifact_role == "real_comment"
            ):
                continue
            has_static_thumbnail = bool(
                str(raw.get("thumbnail_url") or raw.get("remote_url") or "").strip()
            )
            if (
                raw_type in {"image", "news_image", "open_image", "thumbnail"}
                or artifact_role in {"news_image", "open_image"}
                or (
                    has_static_thumbnail
                    and ("video" in raw_type or "video" in artifact_role)
                )
            ):
                media_type = "image"
            else:
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
                    "license": str(
                        media.get("license") or raw.get("license") or ""
                    ).strip(),
                    "license_name": str(
                        media.get("license_name")
                        or raw.get("license_name")
                        or media.get("license")
                        or raw.get("license")
                        or ""
                    ).strip(),
                    "attribution": str(
                        media.get("attribution") or raw.get("attribution") or ""
                    ).strip(),
                    "attribution_text": str(
                        media.get("attribution_text")
                        or raw.get("attribution_text")
                        or media.get("attribution")
                        or raw.get("attribution")
                        or ""
                    ).strip(),
                    "attribution_required": bool(
                        media.get("attribution_required")
                        if media.get("attribution_required") is not None
                        else raw.get("attribution_required")
                    ),
                    "role_hint": artifact_role or "source_context",
                    "reference_only": bool(media.get("reference_only")),
                }
            )
        source_summary = (
            summaries[0]
            if summaries
            else evidence_points[0]
            if evidence_points
            else str(candidate.get("summary") or "").strip()
        )
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
        story_spotlight: Dict[str, Any] = {}
        if str(candidate.get("account") or "").upper() == "B":
            eligible_paths = [
                Path(str(comment.get("screenshot_path") or "")).expanduser()
                for comment in comments
                if comment.get("comment_slide_eligible") is True
            ]
            output_path = (
                eligible_paths[0].parent / "story_comment_spotlight_cover.png"
                if eligible_paths
                else Path()
            )
            if eligible_paths and output_path.is_absolute():
                story_spotlight = build_story_comment_spotlight(
                    comments,
                    output_path,
                )
            if (
                story_spotlight.get("status") == "ready"
                and isinstance(plan.get("slide_plan"), list)
                and plan["slide_plan"]
            ):
                spotlight_comments = story_spotlight.get("spotlight_selected")
                spotlight_comments = (
                    spotlight_comments
                    if isinstance(spotlight_comments, list)
                    else []
                )
                quote_candidates = [
                    str(item.get("text") or "").strip()
                    for item in spotlight_comments
                    if isinstance(item, Mapping)
                    and str(item.get("text") or "").strip()
                ]
                quote_text = min(quote_candidates, key=len) if quote_candidates else ""
                excerpt = quote_text[:58].rstrip()
                if len(quote_text) > len(excerpt):
                    excerpt += "…"
                cover = plan["slide_plan"][0]
                cover["media_type"] = "image"
                cover["asset_refs"] = ["story-comment-spotlight-cover"]
                if excerpt:
                    cover["body"] = f"“{excerpt}”"
                plan["real_comment_evidence"] = copy.deepcopy(story_spotlight)
                plan["story_comment_spotlight"] = copy.deepcopy(story_spotlight)
        if (
            str(candidate.get("account") or "").upper() == "B"
            and isinstance(plan.get("slide_plan"), list)
            and plan["slide_plan"]
        ):
            plan["slide_plan"] = [
                plan["slide_plan"][0],
                *[
                    slide
                    for slide in plan["slide_plan"][1:]
                    if isinstance(slide, Mapping)
                    and (
                        str(slide.get("headline") or "").strip()
                        or str(slide.get("body") or "").strip()
                    )
                ],
            ]
            plan["slide_count"] = len(plan["slide_plan"])
        if (
            isinstance(plan.get("slide_plan"), list)
            and len(plan["slide_plan"]) > 1
            and str(plan["slide_plan"][1].get("body") or "").strip()
            == source_summary
        ):
            plan["slide_plan"].pop(1)
            plan["slide_count"] = len(plan["slide_plan"])
        editorial_target = candidate.get("editorial_target_slide_count")
        if (
            isinstance(editorial_target, int)
            and not isinstance(editorial_target, bool)
            and 1 <= editorial_target <= 20
            and isinstance(plan.get("slide_plan"), list)
            and editorial_target < len(plan["slide_plan"])
        ):
            plan["slide_plan"] = plan["slide_plan"][:editorial_target]
            if isinstance(plan.get("motion_plan"), list):
                plan["motion_plan"] = plan["motion_plan"][:editorial_target]
            plan["slide_count"] = editorial_target
            plan["editorial_target_slide_count"] = editorial_target
        profile_account = {
            "A": "news",
            "B": "story",
            "C": "beauty" if "beauty" in str(candidate.get("category") or "").lower() else "fashion",
        }.get(str(candidate.get("account") or "").upper(), "news")
        production_learning_profile = ProductionProfileCompiler().compile(
            {
                "account": profile_account,
                "topic": str(candidate.get("title") or ""),
                "formats": ["card_news"],
                "keywords": copy.deepcopy(candidate.get("keywords", [])),
                "season": str(candidate.get("season") or ""),
                "emotion": str(candidate.get("emotion") or ""),
            }
        )
        plan["production_learning_profile"] = production_learning_profile
        plan["reference_v2_required"] = True
        profile_registry = production_learning_profile.get("reference_v2_registry")
        profile_registry = (
            profile_registry if isinstance(profile_registry, Mapping) else {}
        )
        selectable_reference_ids = {
            str(value).strip()
            for value in profile_registry.get("selectable_reference_ids", [])
            if str(value).strip()
        }
        registry_specimens = [
            copy.deepcopy(dict(item))
            for item in profile_registry.get("specimens", [])
            if isinstance(item, Mapping)
            and str(item.get("reference_id") or "").strip()
            in selectable_reference_ids
        ]
        candidate_specimens = candidate.get("reference_specimens")
        candidate_blueprints = candidate.get("reference_blueprints")
        plan["reference_specimens"] = copy.deepcopy(
            candidate_specimens
            if isinstance(candidate_specimens, list) and candidate_specimens
            else registry_specimens
        )
        plan["reference_blueprints"] = copy.deepcopy(
            candidate_blueprints
            if isinstance(candidate_blueprints, Mapping) and candidate_blueprints
            else profile_registry.get("blueprints", {})
        )
        plan["reference_v2_registry_consumption"] = {
            "status": (
                "consumed"
                if plan["reference_specimens"] and plan["reference_blueprints"]
                else "unavailable"
            ),
            "source": (
                "candidate_payload"
                if isinstance(candidate_specimens, list) and candidate_specimens
                else "production_learning_profile_registry"
            ),
            "selectable_reference_ids": sorted(selectable_reference_ids),
            "consumed_reference_ids": [
                str(item.get("reference_id") or "").strip()
                for item in plan["reference_specimens"]
                if isinstance(item, Mapping)
                and str(item.get("reference_id") or "").strip()
            ],
            "auto_approval_performed": False,
        }
        plan["reference_v2_media"] = copy.deepcopy(
            candidate.get("reference_v2_media", {})
        )
        if (
            story_spotlight.get("status") == "ready"
            and isinstance(plan["reference_v2_media"], Mapping)
        ):
            slides = plan["reference_v2_media"].get("slides")
            if isinstance(slides, list) and slides:
                slides[0] = {
                    "primary_media": [
                        copy.deepcopy(story_spotlight["media_asset"])
                    ]
                }
        if (
            isinstance(plan["reference_v2_media"], Mapping)
            and isinstance(plan["reference_v2_media"].get("slides"), list)
        ):
            plan["reference_v2_media"]["slides"] = plan[
                "reference_v2_media"
            ]["slides"][: int(plan.get("slide_count") or 0)]
        reference_media = plan["reference_v2_media"]
        reference_media_slides = (
            reference_media.get("slides")
            if isinstance(reference_media, Mapping)
            else []
        )
        reference_assets: List[Dict[str, Any]] = []
        seen_reference_asset_ids = set()
        for media_slide in (
            reference_media_slides
            if isinstance(reference_media_slides, list)
            else []
        ):
            if not isinstance(media_slide, Mapping):
                continue
            for media_role, media_rows in media_slide.items():
                if not isinstance(media_rows, list):
                    continue
                for media_row in media_rows:
                    if not isinstance(media_row, Mapping):
                        continue
                    asset_id = str(media_row.get("asset_id") or "").strip()
                    locator = str(
                        media_row.get("local_path")
                        or media_row.get("path")
                        or ""
                    ).strip()
                    source_url = str(media_row.get("source_url") or "").strip()
                    if (
                        not asset_id
                        or not locator
                        or not source_url
                        or asset_id in seen_reference_asset_ids
                    ):
                        continue
                    seen_reference_asset_ids.add(asset_id)
                    reference_assets.append(
                        {
                            "asset_id": asset_id,
                            "media_type": "image",
                            "origin": "source",
                            "asset_class": "source_evidence",
                            "locator": locator,
                            "source_url": source_url,
                            "rights_status": str(
                                media_row.get("rights_status")
                                or "unrecorded"
                            ),
                            "license": str(
                                media_row.get("license") or ""
                            ).strip(),
                            "license_name": str(
                                media_row.get("license_name")
                                or media_row.get("license")
                                or ""
                            ).strip(),
                            "attribution": str(
                                media_row.get("attribution") or ""
                            ).strip(),
                            "attribution_text": str(
                                media_row.get("attribution_text")
                                or media_row.get("attribution")
                                or ""
                            ).strip(),
                            "attribution_required": bool(
                                media_row.get("attribution_required")
                            ),
                            "role_hint": str(media_role),
                            "product_gallery": False,
                        }
                    )
        if reference_assets:
            plan["asset_inventory"] = reference_assets
        asset_inventory = plan.get("asset_inventory")
        if isinstance(asset_inventory, list):
            for asset in asset_inventory:
                if not isinstance(asset, dict):
                    continue
                asset.setdefault("license", "")
                asset.setdefault("license_name", asset.get("license") or "")
                asset.setdefault("attribution", "")
                asset.setdefault(
                    "attribution_text",
                    asset.get("attribution") or "",
                )
                asset.setdefault("attribution_required", False)
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
            resolved_copy = _source_backed_resolved_copy(plan)
            rendered = render_input_builder(plan, resolved_copy)
            if isinstance(rendered, Mapping):
                rendered = copy.deepcopy(dict(rendered))
                specimens = plan.get("reference_specimens")
                blueprints = plan.get("reference_blueprints")
                media = plan.get("reference_v2_media")
                reference_slides: List[Dict[str, Any]] = []
                if isinstance(specimens, list) and specimens and isinstance(blueprints, Mapping) and blueprints:
                    slide_plan = _plans({"plans": [plan]})[0].get("slide_plan", [])
                    for index, slide_copy in enumerate(resolved_copy):
                        raw_slide = (
                            slide_plan[index]
                            if isinstance(slide_plan, list)
                            and index < len(slide_plan)
                            and isinstance(slide_plan[index], Mapping)
                            else {}
                        )
                        slide_media: Mapping[str, Any] = {}
                        if isinstance(media, Mapping):
                            per_slide_media = media.get("slides")
                            if (
                                isinstance(per_slide_media, list)
                                and index < len(per_slide_media)
                                and isinstance(per_slide_media[index], Mapping)
                            ):
                                slide_media = per_slide_media[index]
                            else:
                                slide_media = {
                                    key: value
                                    for key, value in media.items()
                                    if key != "slides"
                                }
                        media_count = sum(
                            len(value)
                            for value in slide_media.values()
                            if isinstance(value, list)
                        )
                        if media_count == 0 and (
                            str(raw_slide.get("media_type") or "").lower()
                            in {"image", "photo", "screenshot"}
                            or bool(raw_slide.get("asset_refs"))
                        ):
                            media_count = 1
                        result = produce_reference_driven_slide(
                            specimens=specimens,
                            blueprints=blueprints,
                            context={
                                "account": str(plan.get("account") or "").upper(),
                                "slide_role": str(
                                    raw_slide.get("canonical_role")
                                    or raw_slide.get("slide_role")
                                    or "card"
                                ),
                                "media_count": media_count,
                                "copy_char_count": len(slide_copy.get("headline", "")),
                            },
                            content={
                                "headline": slide_copy.get("headline", ""),
                                "body": slide_copy.get("body", ""),
                                "source_label": _display_source_label(
                                    plan.get("copy_plan")
                                ),
                            },
                            media=slide_media,
                        )
                        reference_slides.append(
                            {"page": index + 1, **copy.deepcopy(result)}
                        )
                    reference_status = (
                        "ready"
                        if reference_slides
                        and all(item.get("status") == "ready" for item in reference_slides)
                        else "blocked"
                    )
                    reference_reason = (
                        "all_reference_v2_slides_ready"
                        if reference_status == "ready"
                        else "one_or_more_reference_v2_slides_blocked"
                    )
                else:
                    reference_status = "blocked"
                    reference_reason = "owner_approved_reference_geometry_required"
                rendered["reference_v2_required"] = True
                rendered["reference_v2"] = {
                    "status": reference_status,
                    "reason_code": reference_reason,
                    "legacy_renderer_fallback_allowed": False,
                    "slides": reference_slides,
                }
                if reference_status != "ready":
                    rendered["status"] = "blocked"
                    rendered["reason_code"] = reference_reason
                    rendered["renderer_ready"] = False
                rendered["production_learning_profile"] = copy.deepcopy(
                    plan.get("production_learning_profile", {})
                )
            render_inputs.append(copy.deepcopy(dict(rendered)))
        except Exception as error:
            failures.append(
                {
                    "stage": "render_input_builder",
                    "candidate_id": str(plan.get("candidate_id", "")),
                    "error": str(error),
                }
            )

    ready_render_input_count = sum(
        1
        for item in render_inputs
        if item.get("renderer_ready") is True
        or item.get("status") in {"ready", "renderer_input_ready"}
    )
    blocked_render_input_count = len(render_inputs) - ready_render_input_count
    all_render_inputs_ready = bool(render_inputs) and blocked_render_input_count == 0

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "render_inputs_ready" if all_render_inputs_ready else "partial",
        "reason_code": (
            "selected_discovery_render_flow_completed"
            if all_render_inputs_ready
            else (
                "render_inputs_blocked"
                if render_inputs
                else "no_render_inputs_built"
            )
        ),
        "network_executed": bool(discovery.get("network_executed")),
        "normalized_selection": normalized_selection,
        "discovery": discovery,
        "bridge": copy.deepcopy(bridged),
        "production_plans": copy.deepcopy(plans),
        "render_inputs": render_inputs,
        "ready_render_input_count": ready_render_input_count,
        "blocked_render_input_count": blocked_render_input_count,
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
        discovery_bridge=run_discovery_result_render_bridge_with_supplements,
        production_plan_builder=_default_production_plans,
        render_input_builder=build_selected_candidate_render_inputs,
        max_per_account=max_per_account,
    )


__all__ = [
    "run_selected_candidate_production_flow",
    "run_default_selected_candidate_production_flow",
    "SCHEMA_VERSION",
]
