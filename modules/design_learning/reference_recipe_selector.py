"""Select one complete owner-approved reference recipe per CardNews slide.

V2 intentionally ranks whole reference specimens. It never assembles layout,
palette, typography, or geometry from independent learning records.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "reference_recipe_selector_v2"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _strings(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value.strip().casefold()} if value.strip() else set()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return {
            text.casefold()
            for item in value
            if (text := _text(item))
        }
    return set()


def _tokens(value: Any) -> set[str]:
    values = _strings(value)
    tokens: set[str] = set()
    for text in values:
        tokens.update(
            token
            for token in text.replace("/", " ").replace("_", " ").split()
            if len(token) > 1
        )
    return tokens


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _blueprint_complete(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    canvas = value.get("canvas")
    regions = value.get("regions")
    return bool(
        _text(value.get("blueprint_id"))
        and _text(value.get("blueprint_version"))
        and _text(value.get("geometry_hash"))
        and isinstance(canvas, Mapping)
        and int(canvas.get("width") or 0) > 0
        and int(canvas.get("height") or 0) > 0
        and isinstance(regions, list)
        and regions
        and all(
            isinstance(region, Mapping)
            and _text(region.get("region_id"))
            and _text(region.get("role"))
            and isinstance(region.get("box_norm"), list)
            and len(region["box_norm"]) == 4
            for region in regions
        )
    )


class ReferenceRecipeSelector:
    """Deterministically choose a whole approved reference and blueprint."""

    def select(
        self,
        *,
        specimens: Sequence[Mapping[str, Any]],
        blueprints: Mapping[str, Mapping[str, Any]],
        context: Mapping[str, Any],
    ) -> dict[str, Any]:
        account = _text(context.get("account")).casefold()
        slide_role = _text(context.get("slide_role")).casefold()
        emotion = _text(context.get("emotion")).casefold()
        season = _text(context.get("season")).casefold()
        required_media_count = max(0, int(context.get("media_count") or 0))
        media_aspect = _text(context.get("media_aspect")).casefold()
        topic_tokens = _tokens(
            context.get("topic_tokens")
            or context.get("keywords")
            or context.get("topic")
        )
        copy_size = max(0, int(context.get("copy_char_count") or 0))

        ranked: list[dict[str, Any]] = []
        rejected: list[dict[str, str]] = []
        for raw in specimens:
            specimen = dict(raw) if isinstance(raw, Mapping) else {}
            reference_id = _text(specimen.get("reference_id"))
            blueprint_id = _text(specimen.get("blueprint_id"))
            reason = ""
            if not reference_id:
                reason = "reference_id_required"
            elif specimen.get("approval_status") != "owner_approved":
                reason = "owner_approval_required"
            elif not _text(specimen.get("owner_approval_receipt_id")):
                reason = "owner_approval_receipt_required"
            elif specimen.get("reference_only") is True:
                reason = "reference_only_not_production_selectable"
            elif specimen.get("measured_performance_claimed") is True:
                reason = "measured_performance_claim_not_allowed"
            elif not blueprint_id:
                reason = "blueprint_id_required"
            elif not _blueprint_complete(blueprints.get(blueprint_id)):
                reason = "complete_geometry_blueprint_required"
            if reason:
                rejected.append(
                    {"reference_id": reference_id or "unknown", "reason_code": reason}
                )
                continue

            account_fit = _strings(specimen.get("account_fit"))
            role_fit = _strings(specimen.get("slide_role_fit"))
            emotion_fit = _strings(specimen.get("emotion_fit"))
            season_fit = _strings(specimen.get("season_fit"))
            topic_fit = _tokens(specimen.get("topic_fit"))
            media = (
                specimen.get("media_requirements")
                if isinstance(specimen.get("media_requirements"), Mapping)
                else {}
            )
            min_media = max(0, int(media.get("min_count") or 0))
            max_media = max(min_media, int(media.get("max_count") or min_media))
            aspects = _strings(media.get("aspects"))
            max_copy = max(0, int(specimen.get("max_copy_char_count") or 0))

            components = {
                "account_match": 1.0 if account and account in account_fit else 0.0,
                "slide_role_match": 1.0 if slide_role and slide_role in role_fit else 0.0,
                "media_fit": (
                    1.0
                    if min_media <= required_media_count <= max_media
                    and (not media_aspect or not aspects or media_aspect in aspects)
                    else 0.0
                ),
                "copy_fit": 1.0 if not max_copy or copy_size <= max_copy else 0.0,
                "topic_fit": (
                    len(topic_tokens & topic_fit) / max(1, len(topic_tokens))
                    if topic_tokens
                    else 0.0
                ),
                "emotion_fit": 1.0 if emotion and emotion in emotion_fit else 0.0,
                "season_fit": 1.0 if season and season in season_fit else 0.0,
            }
            if components["account_match"] == 0.0:
                rejected.append(
                    {
                        "reference_id": reference_id,
                        "reason_code": "account_incompatible",
                    }
                )
                continue
            if components["slide_role_match"] == 0.0:
                rejected.append(
                    {
                        "reference_id": reference_id,
                        "reason_code": "slide_role_incompatible",
                    }
                )
                continue
            if components["media_fit"] == 0.0:
                rejected.append(
                    {
                        "reference_id": reference_id,
                        "reason_code": "media_contract_incompatible",
                    }
                )
                continue
            if components["copy_fit"] == 0.0:
                rejected.append(
                    {
                        "reference_id": reference_id,
                        "reason_code": "copy_contract_incompatible",
                    }
                )
                continue

            weights = {
                "account_match": 0.24,
                "slide_role_match": 0.24,
                "media_fit": 0.18,
                "copy_fit": 0.12,
                "topic_fit": 0.10,
                "emotion_fit": 0.08,
                "season_fit": 0.04,
            }
            score = round(
                sum(components[key] * weights[key] for key in weights),
                6,
            )
            ranked.append(
                {
                    "reference_id": reference_id,
                    "blueprint_id": blueprint_id,
                    "score": score,
                    "components": components,
                    "blueprint_version": blueprints[blueprint_id]["blueprint_version"],
                    "geometry_hash": blueprints[blueprint_id]["geometry_hash"],
                }
            )

        ranked.sort(key=lambda row: (-row["score"], row["reference_id"]))
        if not ranked:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "blocked",
                "reason_code": "no_compatible_owner_approved_reference",
                "primary_reference_id": None,
                "primary_blueprint_id": None,
                "ranked_alternatives": [],
                "rejection_reasons": rejected,
                "selection_hash": _stable_hash(
                    {"context": dict(context), "rejections": rejected}
                ),
            }

        primary = ranked[0]
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "selected",
            "reason_code": "complete_reference_selected",
            "primary_reference_id": primary["reference_id"],
            "primary_blueprint_id": primary["blueprint_id"],
            "blueprint_version": primary["blueprint_version"],
            "geometry_hash": primary["geometry_hash"],
            "selection_reasons": primary["components"],
            "ranked_alternatives": ranked[1:],
            "rejection_reasons": rejected,
            "field_mixing_allowed": False,
        }
        result["selection_hash"] = _stable_hash(result)
        return result


__all__ = ["ReferenceRecipeSelector", "SCHEMA_VERSION"]
