"""Convert an adapted Reference V2 slide into a Satori-compatible tree."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any


def _text(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("text", "")
    return str(value or "").strip()


def build_reference_v2_satori_tree(
    adapted_slide: Any,
    *,
    fallback_image_uri: str = "",
) -> dict[str, Any]:
    if not isinstance(adapted_slide, Mapping) or adapted_slide.get("status") != "adapted":
        return {"status": "blocked", "reason_code": "adapted_reference_slide_required"}
    regions = adapted_slide.get("regions")
    if not isinstance(regions, list) or not regions:
        return {"status": "blocked", "reason_code": "reference_geometry_missing"}

    content_by_region = {
        str(item.get("region_id")): item
        for item in adapted_slide.get("content_bindings", [])
        if isinstance(item, Mapping)
    }
    media_by_region = {
        str(item.get("region_id")): item
        for item in adapted_slide.get("media_bindings", [])
        if isinstance(item, Mapping)
    }
    tokens = adapted_slide.get("style_tokens")
    tokens = dict(tokens) if isinstance(tokens, Mapping) else {}
    children = []
    for raw in sorted(
        (item for item in regions if isinstance(item, Mapping)),
        key=lambda item: int(item.get("z_index") or 0),
    ):
        box = raw.get("box_norm")
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            return {"status": "blocked", "reason_code": "reference_region_invalid"}
        region_id = str(raw.get("region_id") or "")
        role = str(raw.get("role") or "")
        style = {
            "position": "absolute",
            "left": f"{float(box[0]) * 100:.6f}%",
            "top": f"{float(box[1]) * 100:.6f}%",
            "width": f"{float(box[2]) * 100:.6f}%",
            "height": f"{float(box[3]) * 100:.6f}%",
            "zIndex": int(raw.get("z_index") or 0),
            "overflow": "hidden",
            "display": "flex",
        }
        if role in {"primary_media", "secondary_media"}:
            binding = media_by_region.get(region_id, {})
            asset = binding.get("asset") if isinstance(binding, Mapping) else {}
            asset = asset if isinstance(asset, Mapping) else {}
            source = _text(
                asset.get("data_uri")
                or asset.get("remote_url")
                or asset.get("thumbnail_url")
                or fallback_image_uri
            )
            if not source:
                return {"status": "blocked", "reason_code": "reference_media_source_missing"}
            child = {
                "type": "img",
                "props": {
                    "src": source,
                    "style": {**style, "objectFit": str(raw.get("object_fit") or "cover")},
                },
            }
        elif role == "accent":
            child = {
                "type": "div",
                "props": {
                    "style": {
                        **style,
                        "backgroundColor": str(raw.get("color") or tokens.get("accent") or "#111111"),
                    },
                    "children": [],
                },
            }
        else:
            binding = content_by_region.get(region_id, {})
            value = _text(binding.get("content") if isinstance(binding, Mapping) else "")
            child = {
                "type": "div",
                "props": {
                    "style": {
                        **style,
                        "color": str(
                            raw.get("color")
                            or tokens.get("text_color")
                            or tokens.get("ink")
                            or "#111111"
                        ),
                        "fontSize": int(raw.get("font_size") or tokens.get("font_size") or 44),
                        "fontWeight": int(raw.get("font_weight") or 700),
                        "lineHeight": float(raw.get("line_height") or 1.2),
                        "alignItems": str(raw.get("align_items") or "flex-start"),
                    },
                    "children": value,
                },
            }
        children.append(child)

    return {
        "status": "ready",
        "reason_code": "reference_geometry_tree_built",
        "geometry_hash": adapted_slide.get("geometry_hash"),
        "reference_consumption_receipt": copy.deepcopy(
            adapted_slide.get("reference_consumption_receipt", {})
        ),
        "tree": {
            "type": "div",
            "props": {
                "style": {
                    "position": "relative",
                    "display": "flex",
                    "width": "100%",
                    "height": "100%",
                    "overflow": "hidden",
                    "backgroundColor": str(tokens.get("background") or "#F5F1E8"),
                },
                "children": children,
            },
        },
    }


__all__ = ["build_reference_v2_satori_tree"]
