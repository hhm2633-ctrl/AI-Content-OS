"""Compose reviewed selected-candidate outputs into one production package.

The composer is deliberately side-effect free.  It validates and preserves an
existing production plan, render-input receipt, and story/copy output; it does
not discover evidence, write files, render media, issue links, or publish.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping

from modules.card_news.canvas_contract import (
    allowed_card_slide_count_label,
    is_allowed_card_slide_count,
)
from modules.media_intelligence.slide_asset_selector import SlideAssetSelector


SCHEMA_VERSION = "selected_candidate_production_package_v1"
EXPECTED_PLAN_SCHEMA = "selected_candidate_production_plan_v1"
EXPECTED_RENDER_SCHEMA = "selected_candidate_render_input_v1"
SUPPORTED_ACCOUNTS = {"A", "B", "C"}
RENDERABLE_RIGHTS = {
    "owned",
    "licensed",
    "public_domain",
    "official_reuse_allowed",
    "user_supplied_with_permission",
    "permission_granted",
    "source_editorial_usable",
    "source_attributed_review_only",
    "owner_approved",
    "license_verified",
    "creative_commons",
    "commons_license_confirmed",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _objects(value: Any) -> List[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _blocked(reason_code: str, reason: str, candidate_id: str = "") -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked",
        "reason_code": reason_code,
        "reason": reason,
        "candidate": {
            "candidate_id": candidate_id,
            "account": "",
            "category": "",
            "title": "",
        },
        "evidence": {"status": "blocked", "source_status": "missing", "sources": [], "assets": []},
        "story": {},
        "slides": [],
        "feed_caption": "",
        "media_plan": [],
        "commerce": None,
        "gates": {
            "package_approval": {"status": "blocked", "approved": False},
            "render": {"status": "blocked", "authorized": False},
            "publish": {"status": "blocked", "authorized": False},
        },
        "receipts": {
            "package_only": True,
            "render_executed": False,
            "publish_executed": False,
            "link_issuance_executed": False,
        },
    }


def _story_parts(story_output: Mapping[str, Any]) -> tuple[Mapping[str, Any], List[Mapping[str, Any]], str]:
    story = story_output.get("story")
    if not isinstance(story, Mapping):
        story = story_output.get("story_outline")
    story = story if isinstance(story, Mapping) else {}

    slides = story_output.get("slide_copy")
    if not isinstance(slides, list):
        slides = story_output.get("slides")
    caption = _text(story_output.get("feed_caption")) or _text(story_output.get("caption"))
    return story, _objects(slides), caption


def _copy_index(slides: List[Mapping[str, Any]]) -> Dict[int, Mapping[str, Any]]:
    indexed: Dict[int, Mapping[str, Any]] = {}
    for fallback_page, slide in enumerate(slides, start=1):
        raw_page = slide.get("page", fallback_page)
        try:
            page = int(raw_page)
        except (TypeError, ValueError):
            continue
        if page > 0 and page not in indexed:
            indexed[page] = slide
    return indexed


def _approval_gate(approval_receipt: Any, candidate_id: str) -> Dict[str, Any]:
    if not isinstance(approval_receipt, Mapping):
        return {
            "status": "pending",
            "approved": False,
            "scope": "production_package",
            "reason_code": "package_approval_required",
        }
    receipt_candidate = _text(approval_receipt.get("candidate_id"))
    scope = _text(approval_receipt.get("scope"))
    approved_by = _text(approval_receipt.get("approved_by"))
    receipt_id = _text(approval_receipt.get("receipt_id"))
    approved = (
        _text(approval_receipt.get("status")).lower() == "approved"
        and receipt_candidate == candidate_id
        and scope == "production_package"
        and bool(approved_by)
        and bool(receipt_id)
    )
    if not approved:
        return {
            "status": "blocked",
            "approved": False,
            "scope": "production_package",
            "reason_code": "invalid_package_approval_receipt",
        }
    return {
        "status": "approved",
        "approved": True,
        "scope": scope,
        "approved_by": approved_by,
        "receipt_id": receipt_id,
    }


def build_selected_candidate_production_package(
    production_plan: Any,
    render_input_receipt: Any,
    story_output: Any,
    approval_receipt: Any = None,
) -> Dict[str, Any]:
    """Return a strict account-aware, no-execution production package."""

    if not isinstance(production_plan, Mapping):
        return _blocked("malformed_production_plan", "production_plan must be an object")
    candidate_id = _text(production_plan.get("candidate_id"))
    if production_plan.get("schema_version") != EXPECTED_PLAN_SCHEMA:
        return _blocked("unsupported_plan_schema", f"expected {EXPECTED_PLAN_SCHEMA}", candidate_id)
    if production_plan.get("status") != "production_plan_ready":
        return _blocked("production_plan_not_ready", "production plan must be ready", candidate_id)

    account = _text(production_plan.get("account")).upper()
    category = _text(production_plan.get("category"))
    title = _text(production_plan.get("title"))
    if not candidate_id or account not in SUPPORTED_ACCOUNTS or not category or not title:
        return _blocked(
            "candidate_identity_incomplete",
            "candidate_id, supported account, category, and title are required",
            candidate_id,
        )

    if not isinstance(render_input_receipt, Mapping):
        return _blocked("malformed_render_receipt", "render_input_receipt must be an object", candidate_id)
    if render_input_receipt.get("schema_version") != EXPECTED_RENDER_SCHEMA:
        return _blocked("unsupported_render_receipt_schema", f"expected {EXPECTED_RENDER_SCHEMA}", candidate_id)
    if render_input_receipt.get("render_executed") is True or render_input_receipt.get("publish_executed") is True:
        return _blocked("execution_already_observed", "package input must be a no-render/no-publish receipt", candidate_id)
    preserved_plan = render_input_receipt.get("full_plan_preserved")
    if not isinstance(preserved_plan, Mapping) or _text(preserved_plan.get("candidate_id")) != candidate_id:
        return _blocked("render_receipt_candidate_mismatch", "render receipt must preserve the same candidate plan", candidate_id)
    if (
        preserved_plan.get("schema_version") != EXPECTED_PLAN_SCHEMA
        or _text(preserved_plan.get("account")).upper() != account
        or _text(preserved_plan.get("category")) != category
        or preserved_plan.get("slide_count") != production_plan.get("slide_count")
        or copy.deepcopy(preserved_plan.get("slide_plan"))
        != copy.deepcopy(production_plan.get("slide_plan"))
    ):
        return _blocked(
            "render_receipt_plan_mismatch",
            "render receipt must preserve the same account, category, and variable slide plan",
            candidate_id,
        )

    if not isinstance(story_output, Mapping):
        return _blocked("malformed_story_output", "story_output must be an object", candidate_id)
    if _text(story_output.get("candidate_id")) != candidate_id:
        return _blocked("story_candidate_mismatch", "story output must identify the same candidate", candidate_id)
    story_account = _text(story_output.get("account")).upper()
    if story_account and story_account != account:
        return _blocked("story_account_mismatch", "story output cannot cross account boundaries", candidate_id)
    story, supplied_slides, feed_caption = _story_parts(story_output)
    story_summary = _text(story.get("summary")) or _text(story.get("narrative"))
    if not story_summary:
        return _blocked("story_missing", "a source-bound story summary or narrative is required", candidate_id)
    if not feed_caption:
        return _blocked("feed_caption_missing", "feed caption must be separate from slide copy", candidate_id)

    copy_plan = production_plan.get("copy_plan")
    if not isinstance(copy_plan, Mapping):
        return _blocked("copy_plan_missing", "production plan copy metadata is required", candidate_id)
    sources = [
        value.strip()
        for value in copy_plan.get("source_credit", [])
        if isinstance(value, str) and value.strip()
    ] if isinstance(copy_plan.get("source_credit"), list) else []
    if not sources:
        return _blocked("evidence_sources_missing", "at least one recorded evidence source is required", candidate_id)

    slide_plan = _objects(production_plan.get("slide_plan"))
    if not slide_plan or production_plan.get("slide_count") != len(slide_plan):
        return _blocked("slide_plan_malformed", "variable slide plan and slide_count must agree", candidate_id)
    if not is_allowed_card_slide_count(len(slide_plan)):
        return _blocked(
            "slide_count_out_of_bounds",
            f"production package requires {allowed_card_slide_count_label()} slides",
            candidate_id,
        )

    assets = _objects(production_plan.get("asset_inventory"))
    source_only_editorial = bool(slide_plan) and all(
        _text(slide.get("media_type")).lower() == "editorial"
        for slide in slide_plan
    )
    if not assets and not source_only_editorial:
        return _blocked("evidence_assets_missing", "at least one evidence asset is required", candidate_id)
    invalid_assets: List[str] = []
    non_renderable_assets: List[str] = []
    for position, asset in enumerate(assets, start=1):
        asset_id = _text(asset.get("asset_id")) or f"asset-{position}"
        if (
            not _text(asset.get("locator"))
            or not _text(asset.get("source_url"))
            or (
                _text(asset.get("origin")).lower() == "generated"
                and _text(asset.get("asset_class")).lower() == "source_evidence"
            )
        ):
            invalid_assets.append(asset_id)
        elif _text(asset.get("rights_status")).lower() not in RENDERABLE_RIGHTS:
            # Reference-only source material may remain in a complete planning
            # package.  It must not silently become a renderer input.
            non_renderable_assets.append(asset_id)
    if invalid_assets:
        result = _blocked(
            "evidence_not_renderable",
            "every packaged evidence asset needs a source locator and source URL and generated media cannot masquerade as evidence",
            candidate_id,
        )
        result["invalid_asset_ids"] = invalid_assets
        return result

    slide_asset_selection = SlideAssetSelector().select(
        slide_plan,
        assets,
        topic=title,
        emotion=_text(production_plan.get("emotion")),
        source_urls=sources,
    )
    selected_slide_plan = slide_asset_selection.get("slides")
    if (
        isinstance(selected_slide_plan, list)
        and len(selected_slide_plan) == len(slide_plan)
        and all(isinstance(item, Mapping) for item in selected_slide_plan)
    ):
        slide_plan = [copy.deepcopy(item) for item in selected_slide_plan]

    assets_by_id = {
        _text(asset.get("asset_id")): copy.deepcopy(dict(asset))
        for asset in assets
        if _text(asset.get("asset_id"))
    }
    supplied_by_page = _copy_index(supplied_slides)
    if len(supplied_by_page) != len(slide_plan):
        return _blocked("slide_copy_incomplete", "every planned slide needs one copy result", candidate_id)

    slides: List[Dict[str, Any]] = []
    media_plan: List[Dict[str, Any]] = []
    for page, planned in enumerate(slide_plan, start=1):
        supplied = supplied_by_page.get(page, {})
        headline = _text(planned.get("headline")) or _text(supplied.get("headline"))
        body = _text(planned.get("body")) or _text(supplied.get("body"))
        media_type = _text(planned.get("media_type"))
        if not headline or not body or not media_type:
            return _blocked("slide_copy_or_media_missing", f"slide {page} is incomplete", candidate_id)
        role = _text(planned.get("canonical_role")) or _text(planned.get("slide_role")) or "card"
        asset_refs = copy.deepcopy(planned.get("asset_refs")) if isinstance(planned.get("asset_refs"), list) else []
        referenced_assets = [
            copy.deepcopy(assets_by_id[asset_id])
            for asset_id in asset_refs
            if isinstance(asset_id, str) and asset_id in assets_by_id
        ]
        visual_spec = (
            copy.deepcopy(dict(planned.get("visual_spec")))
            if isinstance(planned.get("visual_spec"), Mapping)
            else {}
        )
        if referenced_assets and not isinstance(
            visual_spec.get("source_media_candidate"), Mapping
        ):
            source_media_candidate = referenced_assets[0]
            if not _text(source_media_candidate.get("local_path")):
                source_media_candidate["local_path"] = _text(
                    source_media_candidate.get("locator")
                )
            visual_spec["source_media_candidate"] = source_media_candidate
        slide = {"page": page, "role": role, "headline": headline, "body": body}
        if visual_spec:
            slide["visual_spec"] = visual_spec
        slides.append(slide)
        media_plan.append(
            {
                "page": page,
                "slide_role": role,
                "media_type": media_type,
                "asset_refs": asset_refs,
                "motion_ref": _text(planned.get("motion_ref")) or None,
                "source_credit": copy.deepcopy(sources),
                "source_media_candidates": referenced_assets,
            }
        )

    approval_gate = _approval_gate(approval_receipt, candidate_id)
    package_approved = approval_gate["approved"] is True
    package_status = (
        "production_package_ready"
        if package_approved
        else "production_package_pending_approval"
    )
    package_reason_code = (
        "strict_package_composed"
        if package_approved
        else _text(approval_gate.get("reason_code")) or "package_approval_required"
    )
    reference_v2_required = render_input_receipt.get("reference_v2_required") is True
    reference_v2 = (
        copy.deepcopy(dict(render_input_receipt.get("reference_v2")))
        if isinstance(render_input_receipt.get("reference_v2"), Mapping)
        else {}
    )
    reference_v2_ready = reference_v2.get("status") == "ready"
    renderer_ready = (
        render_input_receipt.get("renderer_ready") is True
        and (not reference_v2_required or reference_v2_ready)
    )
    render_gate_status = (
        "ready"
        if approval_gate["approved"] and renderer_ready and not non_renderable_assets
        else "blocked"
    )
    render_reason = (
        "execution_requires_explicit_runner"
        if render_gate_status == "ready"
        else (
            "reference_assets_require_replacement_or_reuse_confirmation"
            if non_renderable_assets
            else (
                _text(reference_v2.get("reason_code"))
                if reference_v2_required and not reference_v2_ready
                else _text(render_input_receipt.get("reason_code"))
            )
            or "package_approval_required"
        )
    )
    commerce = production_plan.get("commerce")
    commerce_value = copy.deepcopy(commerce) if isinstance(commerce, Mapping) else None

    return {
        "schema_version": SCHEMA_VERSION,
        "status": package_status,
        "reason_code": package_reason_code,
        "candidate": {
            "candidate_id": candidate_id,
            "account": account,
            "category": category,
            "title": title,
        },
        "evidence": {
            "status": "ready",
            "source_status": "recorded",
            "sources": copy.deepcopy(sources),
            "assets": copy.deepcopy(assets),
            "rights_status": (
                "source_only_editorial"
                if not assets and source_only_editorial
                else "renderable" if not non_renderable_assets else "reference_only_present"
            ),
            "non_renderable_asset_ids": non_renderable_assets,
        },
        "story": copy.deepcopy(dict(story)),
        "slides": slides,
        "feed_caption": feed_caption,
        "media_plan": media_plan,
        "commerce": commerce_value,
        "reference_v2_required": reference_v2_required,
        "reference_v2": reference_v2,
        "production_learning_profile": copy.deepcopy(
            render_input_receipt.get("production_learning_profile", {})
        ),
        "slide_asset_selection": copy.deepcopy(slide_asset_selection),
        "real_comment_evidence": copy.deepcopy(
            production_plan.get("real_comment_evidence", {})
        ),
        "story_comment_spotlight": copy.deepcopy(
            production_plan.get("story_comment_spotlight", {})
        ),
        "gates": {
            "package_approval": approval_gate,
            "render": {
                "status": render_gate_status,
                "authorized": False,
                "renderer_input_ready": renderer_ready,
                "reason_code": render_reason,
            },
            "publish": {
                "status": "blocked",
                "authorized": False,
                "reason_code": "separate_publish_approval_required",
            },
        },
        "receipts": {
            "package_only": True,
            "render_executed": False,
            "publish_executed": False,
            "link_issuance_executed": False,
            "production_plan_schema": EXPECTED_PLAN_SCHEMA,
            "render_input_schema": EXPECTED_RENDER_SCHEMA,
            "render_input_status": _text(render_input_receipt.get("status")),
            "reference_v2_status": _text(reference_v2.get("status")),
        },
    }


__all__ = ["build_selected_candidate_production_package", "SCHEMA_VERSION"]
