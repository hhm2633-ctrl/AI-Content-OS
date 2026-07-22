"""Build a reviewable CardNews production plan from completed discovery data.

The planner is deliberately data-only.  It does not search, download, render,
publish, or call the protected WorkflowEngine.  Its job is to preserve the
owner-selected topic and discovered assets while deciding which production
roles are actually supported by the available material.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Sequence

from modules.card_news.canvas_contract import (
    allowed_card_slide_count_label,
    is_allowed_card_slide_count,
)


SCHEMA_VERSION = "selected_candidate_production_plan_v1"
SUPPORTED_ACCOUNTS = {"A", "B", "C"}
COMPLETE_STATUSES = {"complete", "completed", "ready", "evidence_ready"}
BLOCKED_ASSET_STATUSES = {"blocked", "rejected", "invalid", "reference_only"}
EDITORIAL_CONTENT_TYPES = {"runway", "season_collection", "brand_editorial"}
EMOTION_ARC = ("관심", "불편함", "의심", "대립", "충격", "결심")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _objects(value: Any) -> List[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, Mapping)]


def _strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]


def _blocked(reason_code: str, reason: str, candidate_id: str = "") -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked",
        "reason_code": reason_code,
        "reason": reason,
        "candidate_id": candidate_id,
        "execution_enabled": False,
        "render_executed": False,
        "publish_executed": False,
        "slide_plan": [],
        "motion_plan": [],
        "copy_plan": {},
        "warnings": [],
    }


def _asset_id(asset: Mapping[str, Any], position: int) -> str:
    return _text(asset.get("asset_id")) or _text(asset.get("id")) or f"asset-{position}"


def _normalize_assets(bundle: Mapping[str, Any]) -> tuple[List[Dict[str, Any]], List[str]]:
    raw_assets = bundle.get("assets")
    if raw_assets is None:
        raw_assets = bundle.get("media")

    assets: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for position, raw in enumerate(_objects(raw_assets), start=1):
        status = _text(raw.get("status")).lower()
        agency = _text(raw.get("agency")).lower()
        publisher = _text(raw.get("publisher")).lower()
        if status in BLOCKED_ASSET_STATUSES or raw.get("reference_only") is True:
            warnings.append(f"asset {position} excluded: {status or 'reference_only'}")
            continue
        if raw.get("ap_source") is True or agency in {"ap", "associated press"} or publisher in {
            "ap",
            "associated press",
        }:
            warnings.append(f"asset {position} excluded: AP reference only")
            continue

        locator = (
            _text(raw.get("local_path"))
            or _text(raw.get("remote_url"))
            or _text(raw.get("source_url"))
        )
        if not locator:
            warnings.append(f"asset {position} excluded: no source locator")
            continue

        media_type = _text(raw.get("media_type")).lower() or "image"
        origin = _text(raw.get("origin")).lower() or "unknown"
        asset_class = _text(raw.get("asset_class")).lower() or "auxiliary"
        if asset_class == "source_evidence" and (
            origin == "generated" or media_type == "motion_graphic"
        ):
            warnings.append(f"asset {position} excluded: generated media cannot be evidence")
            continue

        assets.append(
            {
                "asset_id": _asset_id(raw, position),
                "media_type": media_type,
                "origin": origin,
                "asset_class": asset_class,
                "locator": locator,
                "source_url": _text(raw.get("source_url")),
                "rights_status": _text(raw.get("rights_status")) or "unrecorded",
                "role_hint": _text(raw.get("role_hint")) or _text(raw.get("slide_role")),
                "product_gallery": raw.get("product_gallery") is True
                or _text(raw.get("group")).lower() == "product_gallery",
            }
        )
    return assets, warnings


def _real_comments(bundle: Mapping[str, Any]) -> List[Dict[str, Any]]:
    comments: List[Dict[str, Any]] = []
    for position, raw in enumerate(_objects(bundle.get("comments")), start=1):
        text = _text(raw.get("text"))
        if not text or raw.get("is_real_comment") is not True:
            continue
        comments.append(
            {
                "comment_id": _text(raw.get("comment_id")) or f"comment-{position}",
                "text": text,
                "identity_masked": raw.get("identity_masked") is True,
                "source_url": _text(raw.get("source_url")),
            }
        )
    return comments


def _emotion_for(position: int, total: int) -> str:
    if total <= 1:
        return EMOTION_ARC[-1]
    index = round(position * (len(EMOTION_ARC) - 1) / (total - 1))
    return EMOTION_ARC[index]


def _cover(title: str, assets: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    asset_refs = [assets[0]["asset_id"]] if assets else []
    media_type = assets[0]["media_type"] if assets else "editorial"
    return {
        "slide_role": "cover",
        "media_type": media_type,
        "asset_refs": asset_refs,
        "copy_source": "candidate_title",
        "headline": title,
    }


def _news_slides(
    title: str,
    assets: Sequence[Mapping[str, Any]],
    key_points: Sequence[str],
) -> List[Dict[str, Any]]:
    slides = [_cover(title, assets)]
    remaining_assets = list(assets[1:])
    for position, key_point in enumerate(key_points, start=1):
        asset = remaining_assets.pop(0) if remaining_assets else None
        slides.append(
            {
                "slide_role": "source_context",
                "media_type": asset["media_type"] if asset else "editorial",
                "asset_refs": [asset["asset_id"]] if asset else [],
                "copy_source": "deep_discovery_bundle.key_points",
                "body": key_point,
                "content_unit": position,
            }
        )
    for asset in remaining_assets:
        slides.append(
            {
                "slide_role": asset["role_hint"] or "source_context",
                "media_type": asset["media_type"],
                "asset_refs": [asset["asset_id"]],
                "copy_source": "deep_discovery_bundle",
            }
        )
    return slides


def _story_slides(
    title: str,
    assets: Sequence[Mapping[str, Any]],
    scenes: Sequence[Mapping[str, Any]],
    comments: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    slides = [_cover(title, assets)]
    scene_total = len(scenes)
    for position, scene in enumerate(scenes):
        slides.append(
            {
                "slide_role": "story_scene",
                "media_type": _text(scene.get("media_type")) or "editorial",
                "scene_id": _text(scene.get("scene_id")) or f"scene-{position + 1}",
                "scene_source": "deep_discovery_bundle",
                "emotion_stage": _emotion_for(position, scene_total),
                "copy_source": "verified_story_scene",
            }
        )
    if not scenes:
        for asset in assets[1:]:
            slides.append(
                {
                    "slide_role": asset["role_hint"] or "story_context",
                    "media_type": asset["media_type"],
                    "asset_refs": [asset["asset_id"]],
                    "copy_source": "deep_discovery_bundle",
                }
            )
    for comment in comments:
        slides.append(
            {
                "slide_role": "real_comment",
                "media_type": "screenshot" if comment["source_url"] else "editorial",
                "comment_ref": comment["comment_id"],
                "identity_masked": comment["identity_masked"],
                "copy_source": "real_comment_only",
            }
        )
    return slides


def _style_slides(
    title: str,
    assets: Sequence[Mapping[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    slides = [_cover(title, assets)]
    motion_plan: List[Dict[str, Any]] = []
    gallery_images = [
        asset
        for asset in assets
        if asset["media_type"] == "image" and asset["product_gallery"]
    ]
    gallery_ids = {asset["asset_id"] for asset in gallery_images}

    if len(gallery_images) >= 3:
        motion_id = "motion-product-gallery-1"
        motion_plan.append(
            {
                "motion_id": motion_id,
                "motion_type": "source_image_montage",
                "asset_refs": [asset["asset_id"] for asset in gallery_images],
                "direction": "short zoom, pan and crossfade sequence",
                "generated_source_footage": False,
            }
        )
        slides.append(
            {
                "slide_role": "product_gallery_motion",
                "media_type": "video",
                "motion_ref": motion_id,
                "asset_refs": [asset["asset_id"] for asset in gallery_images],
                "copy_source": "product_facts_or_editorial_notes",
            }
        )

    for asset in assets[1:]:
        if asset["asset_id"] in gallery_ids:
            continue
        slides.append(
            {
                "slide_role": asset["role_hint"] or "official_visual",
                "media_type": asset["media_type"],
                "asset_refs": [asset["asset_id"]],
                "copy_source": "official_source_or_editorial_notes",
            }
        )
    return slides, motion_plan


def _planned_slides(bundle: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Preserve source-bound story/copy work already completed upstream.

    Packaging must not collapse a reviewed variable slide script back to the
    number of discovered images.  Only explicit slide rows with complete copy
    are accepted; this helper never invents copy.
    """

    planned: List[Dict[str, Any]] = []
    for position, raw in enumerate(_objects(bundle.get("planned_slides")), start=1):
        headline = _text(raw.get("headline")) or _text(raw.get("title"))
        body = _text(raw.get("body")) or _text(raw.get("copy"))
        if not headline or not body:
            continue
        refs = raw.get("asset_refs")
        planned.append(
            {
                "slide_role": _text(raw.get("slide_role"))
                or _text(raw.get("role"))
                or ("cover" if position == 1 else "source_context"),
                "media_type": _text(raw.get("media_type")) or "editorial",
                "asset_refs": copy.deepcopy(refs) if isinstance(refs, list) else [],
                "motion_ref": _text(raw.get("motion_ref")) or None,
                "copy_source": _text(raw.get("copy_source")) or "completed_story_output",
                "headline": headline,
                "body": body,
            }
        )
    return planned


def build_selected_candidate_production_plan(
    candidate: Any,
    deep_dive_bundle: Any,
    product_match: Any = None,
) -> Dict[str, Any]:
    """Return a variable, evidence-bound production plan for one selected item."""

    if not isinstance(candidate, Mapping):
        return _blocked("malformed_candidate", "candidate must be an object")
    candidate_id = _text(candidate.get("candidate_id")) or _text(candidate.get("id"))
    if not candidate_id:
        return _blocked("missing_candidate_id", "candidate id is required")
    if not isinstance(deep_dive_bundle, Mapping):
        return _blocked(
            "malformed_deep_dive_bundle",
            "deep_dive_bundle must be an object",
            candidate_id,
        )

    account = _text(candidate.get("account")).upper()
    if account not in SUPPORTED_ACCOUNTS:
        return _blocked("unsupported_account", "account must be A, B, or C", candidate_id)

    bundle_status = _text(deep_dive_bundle.get("status")).lower()
    if bundle_status not in COMPLETE_STATUSES:
        return _blocked(
            "deep_dive_not_complete",
            "completed discovery data is required before production planning",
            candidate_id,
        )

    title = _text(candidate.get("title")) or _text(deep_dive_bundle.get("title"))
    summary = _text(deep_dive_bundle.get("summary")) or _text(candidate.get("context"))
    if not title or not summary:
        return _blocked(
            "missing_copy_source",
            "title and source-backed summary are required",
            candidate_id,
        )

    source_refs = copy.deepcopy(deep_dive_bundle.get("source_refs"))
    if not isinstance(source_refs, list):
        source_refs = []
    if account == "A" and not source_refs:
        return _blocked(
            "news_source_missing",
            "news production requires at least one recorded source",
            candidate_id,
        )

    assets, warnings = _normalize_assets(deep_dive_bundle)
    completed_slides = _planned_slides(deep_dive_bundle)
    scenes = _objects(deep_dive_bundle.get("reconstruction_scenes"))
    comments = _real_comments(deep_dive_bundle)
    key_points = _strings(deep_dive_bundle.get("key_points"))
    if not assets and not completed_slides and not key_points and not (account == "B" and scenes):
        result = _blocked(
            "usable_media_missing",
            "no usable discovered asset or verified story scene is available",
            candidate_id,
        )
        result["warnings"] = warnings
        return result

    motion_plan: List[Dict[str, Any]] = []
    if completed_slides:
        slide_plan = completed_slides
        content_kind = {
            "A": "news",
            "B": "story_relationship_dopamine_entertainment",
            "C": "fashion_beauty_entertainment",
        }[account]
    elif account == "A":
        slide_plan = _news_slides(title, assets, key_points)
        content_kind = "news"
    elif account == "B":
        slide_plan = _story_slides(title, assets, scenes, comments)
        content_kind = "story_relationship_dopamine_entertainment"
    else:
        slide_plan, motion_plan = _style_slides(title, assets)
        content_kind = "fashion_beauty_entertainment"

    if not is_allowed_card_slide_count(len(slide_plan)):
        result = _blocked(
            "slide_count_out_of_bounds",
            f"production plan must contain {allowed_card_slide_count_label()} slides without truncation",
            candidate_id,
        )
        result["planned_slide_count"] = len(slide_plan)
        result["warnings"] = warnings
        return result

    content_type = _text(deep_dive_bundle.get("content_type")).lower()
    editorial_only = content_type in EDITORIAL_CONTENT_TYPES
    natural_match = isinstance(product_match, Mapping) and (
        _text(product_match.get("fit")).lower() == "natural"
        or _text(product_match.get("status")).lower() in {"matched", "ready"}
    )
    commerce = {
        "mode": "not_applicable" if editorial_only else ("optional_match" if natural_match else "none"),
        "required_for_readiness": False,
        "product_match": copy.deepcopy(product_match) if natural_match else None,
    }

    copy_plan = {
        "headline_source": "candidate_title",
        "summary_source": "deep_discovery_bundle",
        "card_footer": _text(deep_dive_bundle.get("card_footer")),
        "feed_body": _text(deep_dive_bundle.get("feed_body")) or summary,
        "key_points": _strings(deep_dive_bundle.get("key_points")),
        "source_credit": source_refs,
        "source_credit_placement": "caption_end" if account in {"A", "C"} else "internal_record",
        "final_human_copy_review_required": True,
    }

    if account == "B" and not source_refs:
        warnings.append("community/story original URL should remain in the internal record")
    if comments and any(not comment["identity_masked"] for comment in comments):
        warnings.append("real comments require identity masking before rendering")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "production_plan_ready",
        "reason_code": "asset_driven_plan_ready",
        "candidate_id": candidate_id,
        "account": account,
        "category": _text(candidate.get("category")),
        "content_kind": content_kind,
        "title": title,
        "execution_enabled": False,
        "render_executed": False,
        "publish_executed": False,
        "slide_count": len(slide_plan),
        "slide_count_bounds": {"min": 1, "max": 20},
        "slide_plan": slide_plan,
        "motion_plan": motion_plan,
        "copy_plan": copy_plan,
        "commerce": commerce,
        "asset_inventory": assets,
        "real_comment_count": len(comments),
        "warnings": warnings,
    }


__all__ = ["build_selected_candidate_production_plan", "SCHEMA_VERSION"]
