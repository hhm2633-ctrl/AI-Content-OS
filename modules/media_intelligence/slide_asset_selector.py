"""Deterministic, rights-aware slide asset selection.

This module consumes already-localized assets only. It never downloads media,
approves rights, mutates Reference V2, or treats OCR/OpenCLIP as rights evidence.
"""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "slide_asset_selector_v1"
RENDERABLE_RIGHTS = frozenset(
    {
        "owned",
        "owner_approved",
        "licensed",
        "license_verified",
        "public_domain",
        "creative_commons",
        "commons_license_confirmed",
        "official_reuse_allowed",
        "user_supplied_with_permission",
        "permission_granted",
        "source_editorial_usable",
        "source_attributed_review_only",
    }
)
REACTION_PROVIDERS = frozenset(
    {"local_reaction_library", "giphy", "tenor", "gifer"}
)
OPEN_MEDIA_PROVIDERS = frozenset(
    {"wikimedia_commons", "commons", "google_cse", "google"}
)
ROLE_ALIASES = {
    "hook": {"hook", "cover", "first_screen", "opening"},
    "evidence": {"evidence", "source_context", "fact", "detail"},
    "transition": {"transition", "emotional_transition", "reaction"},
    "conclusion": {"conclusion", "debate_cta", "cta", "ending"},
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _tokens(value: Any) -> set[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        value = " ".join(_text(item) for item in value)
    return {
        token.casefold()
        for token in re.findall(r"[0-9A-Za-z가-힣]{2,}", _text(value))
    }


def _local_path(asset: Mapping[str, Any]) -> str:
    value = _text(asset.get("local_path") or asset.get("locator"))
    if value.lower().startswith(("http://", "https://")):
        return ""
    return value


def _source_tier(
    asset: Mapping[str, Any],
    topic_source_urls: set[str],
) -> tuple[int, str]:
    provider = _text(asset.get("source_provider")).casefold()
    origin = _text(asset.get("origin")).casefold()
    role = _text(asset.get("role_hint")).casefold()
    source_url = _text(asset.get("source_url")).casefold()
    if provider in REACTION_PROVIDERS or "reaction" in role:
        return 2, "reaction"
    if source_url and source_url in topic_source_urls:
        return 0, "direct_topic"
    if provider in OPEN_MEDIA_PROVIDERS:
        return 1, "official_or_open_media"
    if (
        origin in {"official", "publisher", "source", "direct"}
        or role in {"primary", "topic_primary", "source_editorial"}
    ):
        return 0, "direct_topic"
    return 1, "official_or_open_media"


def _quality_score(asset: Mapping[str, Any]) -> float:
    gate = asset.get("quality_gate")
    gate = gate if isinstance(gate, Mapping) else {}
    for value in (
        gate.get("relevant_score"),
        asset.get("openclip_score"),
        asset.get("topic_score"),
    ):
        if isinstance(value, (int, float)):
            return max(-1.0, min(1.0, float(value)))
    return 0.0


def _resolution_score(asset: Mapping[str, Any]) -> float:
    width = asset.get("width")
    height = asset.get("height")
    if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
        return 0.0
    return min(1.0, max(0.0, float(width) * float(height)) / 2_000_000.0)


def _identity(asset: Mapping[str, Any]) -> str:
    gate = asset.get("quality_gate")
    gate = gate if isinstance(gate, Mapping) else {}
    for value in (
        asset.get("sha256"),
        asset.get("content_sha256"),
        gate.get("perceptual_hash"),
        asset.get("local_path"),
        asset.get("locator"),
        asset.get("source_url"),
        asset.get("asset_id"),
    ):
        text = _text(value)
        if text:
            return hashlib.sha256(text.casefold().encode("utf-8")).hexdigest()
    return hashlib.sha256(repr(sorted(asset.items())).encode("utf-8")).hexdigest()


def _eligible(asset: Mapping[str, Any]) -> tuple[bool, str]:
    if not _local_path(asset):
        return False, "local_path_required"
    if _text(asset.get("rights_status")).casefold() not in RENDERABLE_RIGHTS:
        return False, "rights_not_renderable"
    if asset.get("render_allowed") is False:
        return False, "render_explicitly_blocked"
    if asset.get("usable_in_production") is False:
        return False, "production_use_explicitly_blocked"
    gate = asset.get("quality_gate")
    if isinstance(gate, Mapping) and gate.get("passed") is False:
        return False, _text(gate.get("reason_code")) or "quality_gate_blocked"
    return True, ""


class SlideAssetSelector:
    """Choose one local asset per slide with strict source-tier priority."""

    def select(
        self,
        slides: Sequence[Mapping[str, Any]],
        assets: Sequence[Mapping[str, Any]],
        *,
        topic: str = "",
        emotion: str = "",
        source_urls: Sequence[str] = (),
    ) -> dict[str, Any]:
        normalized_assets: list[dict[str, Any]] = []
        rejected: list[dict[str, str]] = []
        for index, raw in enumerate(assets):
            if not isinstance(raw, Mapping):
                continue
            asset = copy.deepcopy(dict(raw))
            asset_id = _text(asset.get("asset_id")) or f"asset-{index + 1}"
            asset["asset_id"] = asset_id
            asset["local_path"] = _local_path(asset)
            allowed, reason = _eligible(asset)
            if not allowed:
                rejected.append({"asset_id": asset_id, "reason_code": reason})
                continue
            normalized_assets.append(asset)

        topic_tokens = _tokens(topic)
        emotion_tokens = _tokens(emotion)
        topic_source_urls = {_text(url).casefold() for url in source_urls if _text(url)}
        used: set[str] = set()
        selected_slides: list[dict[str, Any]] = []
        receipts: list[dict[str, Any]] = []

        for page, raw_slide in enumerate(slides, start=1):
            slide = copy.deepcopy(dict(raw_slide))
            role = _text(
                slide.get("slide_role")
                or slide.get("semantic_role")
                or slide.get("role")
            ).casefold()
            role_tokens = _tokens(role)
            for canonical, aliases in ROLE_ALIASES.items():
                if role in aliases:
                    role_tokens.add(canonical)
            ranked: list[tuple[tuple[Any, ...], dict[str, Any], dict[str, Any]]] = []
            for asset in normalized_assets:
                tier, tier_name = _source_tier(asset, topic_source_urls)
                asset_tokens = _tokens(
                    [
                        asset.get("title"),
                        asset.get("keywords"),
                        asset.get("emotion"),
                        asset.get("narrative_role"),
                        asset.get("role_hint"),
                    ]
                )
                topic_overlap = len(topic_tokens & asset_tokens)
                emotion_overlap = len(emotion_tokens & asset_tokens)
                role_overlap = len(role_tokens & asset_tokens)
                openclip = _quality_score(asset)
                resolution = _resolution_score(asset)
                score = round(
                    topic_overlap * 0.22
                    + emotion_overlap * 0.14
                    + role_overlap * 0.16
                    + max(0.0, openclip) * 0.34
                    + resolution * 0.14,
                    6,
                )
                identity = _identity(asset)
                receipt = {
                    "asset_id": asset["asset_id"],
                    "source_tier": tier_name,
                    "source_priority": tier,
                    "score": score,
                    "topic_overlap": topic_overlap,
                    "emotion_overlap": emotion_overlap,
                    "role_overlap": role_overlap,
                    "openclip_score": openclip,
                    "resolution_score": resolution,
                    "duplicate_reuse": identity in used,
                }
                ranked.append(
                    ((tier, identity in used, -score, asset["asset_id"]), asset, receipt)
                )
            ranked.sort(key=lambda row: row[0])
            chosen = ranked[0] if ranked else None
            if chosen is not None:
                _, asset, receipt = chosen
                used.add(_identity(asset))
                slide["asset_refs"] = [asset["asset_id"]]
                slide["source_media_candidate"] = copy.deepcopy(asset)
                receipt["page"] = int(slide.get("page") or page)
                receipt["slide_role"] = role
                receipts.append(receipt)
            else:
                slide["asset_refs"] = []
                receipts.append(
                    {
                        "page": int(slide.get("page") or page),
                        "slide_role": role,
                        "asset_id": None,
                        "reason_code": "no_eligible_local_asset",
                    }
                )
            selected_slides.append(slide)

        selected_count = sum(1 for row in receipts if _text(row.get("asset_id")))
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "selected" if selected_count else "no_eligible_assets",
            "slides": selected_slides,
            "selection_receipts": receipts,
            "rejected_assets": rejected,
            "eligible_asset_count": len(normalized_assets),
            "selected_slide_count": selected_count,
            "source_priority": [
                "direct_topic",
                "official_or_open_media",
                "reaction",
            ],
            "rights_are_external_evidence": False,
        }


def select_slide_assets(
    slides: Sequence[Mapping[str, Any]],
    assets: Sequence[Mapping[str, Any]],
    **context: Any,
) -> dict[str, Any]:
    return SlideAssetSelector().select(slides, assets, **context)


__all__ = [
    "RENDERABLE_RIGHTS",
    "SCHEMA_VERSION",
    "SlideAssetSelector",
    "select_slide_assets",
]
