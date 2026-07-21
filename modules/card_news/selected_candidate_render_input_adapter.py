"""Adapt a selected production plan to the current legacy renderer contract.

This module never renders.  It makes the current variable-length/static renderer
contract explicit instead of silently truncating a variable or hybrid plan.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Sequence

from modules.card_news.canvas_contract import is_allowed_card_slide_count


SCHEMA_VERSION = "selected_candidate_render_input_v1"
EXPECTED_PLAN_SCHEMA = "selected_candidate_production_plan_v1"
STATIC_MEDIA_TYPES = {"image", "screenshot", "editorial"}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _objects(value: Any) -> List[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, Mapping)]


def _blocked(reason_code: str, reason: str, plan: Any = None) -> Dict[str, Any]:
    preserved = copy.deepcopy(plan) if isinstance(plan, Mapping) else None
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked",
        "reason_code": reason_code,
        "reason": reason,
        "renderer_ready": False,
        "render_executed": False,
        "publish_executed": False,
        "current_renderer_input": None,
        "full_plan_preserved": preserved,
        "sidecars": {},
    }


def _copy_by_position(resolved_copy: Any) -> Dict[int, Mapping[str, Any]]:
    if isinstance(resolved_copy, list):
        return {
            index: value
            for index, value in enumerate(resolved_copy, start=1)
            if isinstance(value, Mapping)
        }
    if isinstance(resolved_copy, Mapping):
        result: Dict[int, Mapping[str, Any]] = {}
        for key, value in resolved_copy.items():
            if not isinstance(value, Mapping):
                continue
            try:
                position = int(key)
            except (TypeError, ValueError):
                continue
            if position > 0:
                result[position] = value
        return result
    return {}


def _resolved_slides(
    slide_plan: Sequence[Mapping[str, Any]],
    resolved_copy: Any,
) -> tuple[List[Dict[str, Any]], List[int]]:
    copy_index = _copy_by_position(resolved_copy)
    slides: List[Dict[str, Any]] = []
    missing: List[int] = []
    for position, planned in enumerate(slide_plan, start=1):
        supplied = copy_index.get(position, {})
        headline = _text(planned.get("headline")) or _text(supplied.get("headline"))
        body = _text(planned.get("body")) or _text(supplied.get("body"))
        if not headline or not body:
            missing.append(position)
        slides.append(
            {
                "page": position,
                "role": _text(planned.get("canonical_role"))
                or _text(planned.get("slide_role"))
                or "card",
                "headline": headline,
                "body": body,
                "media_type": _text(planned.get("media_type")) or "editorial",
                "asset_refs": copy.deepcopy(planned.get("asset_refs"))
                if isinstance(planned.get("asset_refs"), list)
                else [],
                "motion_ref": _text(planned.get("motion_ref")) or None,
                "copy_source": _text(planned.get("copy_source")),
            }
        )
    return slides, missing


def _asset_index(plan: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    indexed: Dict[str, Mapping[str, Any]] = {}
    for asset in _objects(plan.get("asset_inventory")):
        asset_id = _text(asset.get("asset_id"))
        if asset_id:
            indexed[asset_id] = asset
    return indexed


def _generated_evidence(plan: Mapping[str, Any]) -> List[str]:
    blocked: List[str] = []
    for asset in _objects(plan.get("asset_inventory")):
        if (
            _text(asset.get("origin")).lower() == "generated"
            and _text(asset.get("asset_class")).lower() == "source_evidence"
        ):
            blocked.append(_text(asset.get("asset_id")) or "unknown")
    return blocked


def _image_inputs(
    slides: Sequence[Mapping[str, Any]],
    assets: Mapping[str, Mapping[str, Any]],
) -> tuple[List[Dict[str, Any]], int]:
    images: List[Dict[str, Any]] = []
    local_count = 0
    for slide in slides:
        refs = slide.get("asset_refs") if isinstance(slide.get("asset_refs"), list) else []
        asset = assets.get(str(refs[0])) if refs else None
        locator = _text(asset.get("locator")) if isinstance(asset, Mapping) else ""
        is_remote = locator.lower().startswith(("http://", "https://"))
        is_static = _text(slide.get("media_type")).lower() in {"image", "screenshot"}
        image_path = locator if locator and not is_remote and is_static else None
        if image_path:
            local_count += 1
        images.append(
            {
                "image_path": image_path,
                "asset_id": _text(asset.get("asset_id")) if isinstance(asset, Mapping) else "",
                "source_locator": locator or None,
                "remote_reference_only": bool(locator and is_remote),
            }
        )
    return images, local_count


def build_selected_candidate_render_inputs(
    production_plan: Any,
    resolved_copy: Any = None,
) -> Dict[str, Any]:
    """Return current renderer inputs only when no plan information is lost."""

    if not isinstance(production_plan, Mapping):
        return _blocked("malformed_production_plan", "production_plan must be an object")
    if production_plan.get("schema_version") != EXPECTED_PLAN_SCHEMA:
        return _blocked(
            "unsupported_plan_schema",
            f"expected {EXPECTED_PLAN_SCHEMA}",
            production_plan,
        )
    if production_plan.get("status") != "production_plan_ready":
        return _blocked(
            "production_plan_not_ready",
            "production plan is not ready",
            production_plan,
        )

    generated_evidence = _generated_evidence(production_plan)
    if generated_evidence:
        result = _blocked(
            "generated_source_evidence_blocked",
            "generated assets cannot be renderer evidence",
            production_plan,
        )
        result["blocked_asset_ids"] = generated_evidence
        return result

    slide_plan = _objects(production_plan.get("slide_plan"))
    if not slide_plan:
        return _blocked("slide_plan_missing", "production plan has no slides", production_plan)

    slides, missing_copy = _resolved_slides(slide_plan, resolved_copy)
    sidecars = {
        "motion_plan": copy.deepcopy(production_plan.get("motion_plan"))
        if isinstance(production_plan.get("motion_plan"), list)
        else [],
        "caption_plan": copy.deepcopy(production_plan.get("copy_plan"))
        if isinstance(production_plan.get("copy_plan"), Mapping)
        else {},
        "commerce": copy.deepcopy(production_plan.get("commerce"))
        if isinstance(production_plan.get("commerce"), Mapping)
        else {},
        "source_refs": copy.deepcopy(
            (production_plan.get("copy_plan") or {}).get("source_credit", [])
        )
        if isinstance(production_plan.get("copy_plan"), Mapping)
        else [],
    }

    if not is_allowed_card_slide_count(len(slides)):
        result = _blocked(
            "current_renderer_slide_count",
            "current CardNewsModule supports 2-20 slides; full variable plan was preserved",
            production_plan,
        )
        result["planned_slide_count"] = len(slides)
        result["required_renderer"] = "variable_length_hybrid_renderer"
        result["sidecars"] = sidecars
        return result

    unsupported = [
        slide["page"]
        for slide in slides
        if _text(slide.get("media_type")).lower() not in STATIC_MEDIA_TYPES
        or slide.get("motion_ref")
    ]
    if unsupported:
        result = _blocked(
            "current_renderer_media_limit",
            "current CardNewsModule cannot render video or motion slides",
            production_plan,
        )
        result["unsupported_slide_pages"] = unsupported
        result["required_renderer"] = "variable_length_hybrid_renderer"
        result["sidecars"] = sidecars
        return result

    if missing_copy:
        result = _blocked(
            "resolved_copy_missing",
            "every renderer slide needs source-backed headline and body copy",
            production_plan,
        )
        result["missing_copy_pages"] = missing_copy
        result["sidecars"] = sidecars
        return result

    assets = _asset_index(production_plan)
    images, local_image_count = _image_inputs(slides, assets)
    content_result = {
        "title": _text(production_plan.get("title")),
        "slides": [
            {
                "page": slide["page"],
                "role": slide["role"],
                "headline": slide["headline"],
                "body": slide["body"],
            }
            for slide in slides
        ],
        "selected_candidate_id": _text(production_plan.get("candidate_id")),
        "selected_account": _text(production_plan.get("account")),
        "source_refs": copy.deepcopy(sidecars["source_refs"]),
        "production_plan_schema": EXPECTED_PLAN_SCHEMA,
    }
    image_generation_result = {
        "images": images,
        "generated": False,
        "source": "selected_candidate_asset_inventory",
    }
    image_strategy_result = {
        "need_ai_image": False,
        "manual_image_required": local_image_count < len(slides),
        "image_source": (
            "operator_rights_approved_asset"
            if local_image_count
            else "manual_source_asset_required"
        ),
        "selected_candidate_assets": copy.deepcopy(list(assets.values())),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "renderer_input_ready",
        "reason_code": "legacy_static_contract_satisfied",
        "renderer_ready": True,
        "render_executed": False,
        "publish_executed": False,
        "current_renderer_input": {
            "content_result": content_result,
            "image_generation_result": image_generation_result,
            "image_strategy_result": image_strategy_result,
        },
        "full_plan_preserved": copy.deepcopy(production_plan),
        "sidecars": sidecars,
    }


__all__ = ["build_selected_candidate_render_inputs", "SCHEMA_VERSION"]
