"""Convert an adapted Reference V2 slide into a Satori-compatible tree."""

from __future__ import annotations

import copy
from collections.abc import Mapping
import hashlib
import math
import re
from typing import Any


CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350
SAFE_LEFT = 64 / CANVAS_WIDTH
SAFE_RIGHT = 1.0 - SAFE_LEFT
SAFE_TOP = 64 / CANVAS_HEIGHT
SAFE_BOTTOM = 1.0 - (84 / CANVAS_HEIGHT)
DETAIL_SAFE_LEFT = 72 / CANVAS_WIDTH
DETAIL_SAFE_RIGHT = 1008 / CANVAS_WIDTH
DETAIL_SAFE_TOP = 72 / CANVAS_HEIGHT
DETAIL_SAFE_BOTTOM = 1278 / CANVAS_HEIGHT
DETAIL_BACKGROUND = "#0B1F24"
DETAIL_ACCENT = "#E5B04A"
DETAIL_HEADLINE_COLOR = "#FFFFFF"
DETAIL_BODY_CARD = "#F4EFE5"
DETAIL_BODY_COLOR = "#102B30"
DETAIL_FOOTER_COLOR = "#8FA3A8"
DETAIL_FOOTER_RULE = "#607477"
DETAIL_FAMILIES = (
    "key-fact",
    "evidence-brief",
    "quote",
    "progression",
)
DETAIL_ACCENTS = ("#E5B04A", "#65C7D0", "#EE8B68", "#8FCB9B")
DETAIL_SAFE_PALETTES = {
    "key-fact": {
        "background": "#0B1F24",
        "accent": "#E5B04A",
        "headline": "#FFFFFF",
        "body": "#102B30",
        "body_card": "#F4EFE5",
    },
    "evidence-brief": {
        "background": "#0B1F24",
        "accent": "#E5B04A",
        "headline": "#FFFFFF",
        "body": "#102B30",
        "body_card": "#F4EFE5",
    },
    "quote": {
        "background": "#F4EFE5",
        "accent": "#B16D00",
        "headline": "#0B1F24",
        "body": "#FFFFFF",
        "body_card": "#102B30",
    },
    "progression": {
        "background": "#F4EFE5",
        "accent": "#276D70",
        "headline": "#0B1F24",
        "body": "#0B1F24",
        "body_card": "#DDEAE5",
    },
}


def _text(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("text", "")
    return str(value or "").strip()


def _semantic_text_role(role: str) -> str:
    normalized = role.strip().casefold()
    if normalized in {"headline", "title", "hook", "hook_headline"}:
        return "headline"
    if normalized in {
        "body",
        "description",
        "supporting_text",
        "summary",
        "caption",
        "detail",
    }:
        return "body"
    return normalized


def _normalized_copy(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.casefold(), flags=re.UNICODE)


def _normalize_input_copy(value: str, *, headline: bool = False) -> str:
    normalized = " ".join(str(value or "").replace("\n", " ").split())
    normalized = re.sub(r"(?:\.{3,}|…{2,})", "…", normalized)
    normalized = re.sub(r"\s*…\s*", "…", normalized)
    if headline:
        normalized = re.sub(r"^[.…\s]+", "", normalized)
        normalized = re.sub(r"(?<=\S)…(?=\S)", " ", normalized)
        normalized = " ".join(normalized.split())
    return normalized


def _without_line_leading_ellipsis(value: str) -> str:
    return re.sub(r"^[.…\s]+(?=\S)", "", value).strip()


def _balance_headline_lines(value: str, *, maximum_lines: int = 3) -> str:
    current = [
        _without_line_leading_ellipsis(item)
        for item in value.splitlines()
        if _without_line_leading_ellipsis(item)
    ]
    if len(current) >= 2 or not current:
        return "\n".join(current[:maximum_lines])
    source = current[0]
    if len(source) < 14:
        return source
    target_lines = 3 if len(source) >= 34 else 2
    target_lines = min(maximum_lines, target_lines)
    lines: list[str] = []
    remaining = source
    while remaining and len(lines) < target_lines - 1:
        lines_left = target_lines - len(lines)
        ideal = max(1, math.ceil(len(remaining) / lines_left))
        candidates = [
            index
            for index, character in enumerate(remaining)
            if character in {" ", ",", "·", ":", "—", "-"}
            and max(3, ideal - 8) <= index <= min(len(remaining) - 3, ideal + 8)
        ]
        cut = min(candidates, key=lambda index: abs(index - ideal)) if candidates else ideal
        line = _without_line_leading_ellipsis(remaining[:cut].rstrip(" ,·:—-"))
        if line:
            lines.append(line)
        remaining = remaining[cut:].lstrip(" ,·:—-.…")
    if remaining:
        lines.append(_without_line_leading_ellipsis(remaining))
    return "\n".join(item for item in lines if item)


def _is_duplicate_copy(value: str, emitted: list[str]) -> bool:
    candidate = _normalized_copy(value)
    if not candidate:
        return True
    for previous in emitted:
        if candidate == previous:
            return True
        shorter, longer = sorted((candidate, previous), key=len)
        if (
            len(shorter) >= 14
            and shorter in longer
            and len(shorter) / max(1, len(longer)) >= 0.8
        ):
            return True
    return False


def _bounded_box(
    value: Any,
    *,
    text_region: bool,
) -> tuple[float, float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        x, y, width, height = (float(item) for item in value)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in (x, y, width, height)):
        return None
    if width <= 0 or height <= 0:
        return None
    left_limit = SAFE_LEFT if text_region else 0.0
    right_limit = SAFE_RIGHT if text_region else 1.0
    top_limit = SAFE_TOP if text_region else 0.0
    bottom_limit = SAFE_BOTTOM if text_region else 1.0
    left = max(left_limit, x)
    top = max(top_limit, y)
    right = min(right_limit, x + width)
    bottom = min(bottom_limit, y + height)
    if right <= left or bottom <= top:
        return None
    return left, top, right - left, bottom - top


def _wrap_korean(
    value: str,
    *,
    characters_per_line: int,
    maximum_lines: int,
) -> tuple[str, bool]:
    """Wrap Korean/Latin copy deterministically and mark hard-limit ellipsis."""

    characters_per_line = max(4, characters_per_line)
    maximum_lines = max(1, maximum_lines)
    lines: list[str] = []
    for paragraph in value.splitlines() or [value]:
        remaining = " ".join(paragraph.split())
        if not remaining:
            continue
        while remaining:
            if len(remaining) <= characters_per_line:
                lines.append(_without_line_leading_ellipsis(remaining))
                break
            cut = characters_per_line
            whitespace = remaining.rfind(" ", 0, characters_per_line + 1)
            if whitespace >= max(2, characters_per_line // 2):
                cut = whitespace
            lines.append(
                _without_line_leading_ellipsis(remaining[:cut].rstrip())
            )
            remaining = remaining[cut:].lstrip(" .…")
    if not lines:
        return "", False
    truncated = len(lines) > maximum_lines
    lines = lines[:maximum_lines]
    if truncated:
        last = lines[-1].rstrip(" .,…")
        lines[-1] = f"{last}…"
    return "\n".join(lines), truncated


def _fit_text_to_region(
    value: str,
    *,
    width_px: float,
    height_px: float,
    requested_font_size: int,
    minimum_font_size: int,
    line_height: float,
    maximum_lines: int,
    hard_character_limit: int | None = None,
) -> tuple[str, int, int, bool]:
    source = _normalize_input_copy(value)
    hard_limited = False
    if hard_character_limit and len(source) > hard_character_limit:
        source = f"{source[: max(1, hard_character_limit - 1)].rstrip()}…"
        hard_limited = True
    minimum = max(16, min(minimum_font_size, requested_font_size))
    sizes = list(range(requested_font_size, minimum - 1, -2))
    if not sizes or sizes[-1] != minimum:
        sizes.append(minimum)
    last_result = (source, minimum, 1, hard_limited)
    for font_size in sizes:
        characters_per_line = max(4, int(width_px / max(1.0, font_size * 0.96)))
        physical_lines = max(
            1,
            int(height_px / max(1.0, font_size * line_height)),
        )
        line_limit = max(1, min(maximum_lines, physical_lines))
        wrapped, truncated = _wrap_korean(
            source,
            characters_per_line=characters_per_line,
            maximum_lines=line_limit,
        )
        last_result = (
            wrapped,
            font_size,
            len(wrapped.splitlines()) or 1,
            hard_limited or truncated,
        )
        if not truncated:
            return last_result
    return last_result


def _detail_family_context(
    adapted_slide: Mapping[str, Any],
    *,
    page_number: int,
    content_by_region: Mapping[str, Any],
) -> tuple[str, str]:
    """Choose a family from explicit semantic evidence without forced quoting."""

    copy_values = [
        _text(item.get("content"))
        for item in content_by_region.values()
        if isinstance(item, Mapping)
    ]
    combined = " ".join(value for value in copy_values if value)
    if re.search(r"[“”‘’\"'][^“”‘’\"']+[“”‘’\"']", combined):
        semantic_family = "quote"
    elif (
        re.search(r"\d[\d,.]*\s*(?:만\s*)?명", combined)
        or (
            re.search(r"(?:고용|일자리|채용|인원)", combined)
            and re.search(r"\d[\d,.]*", combined)
        )
    ):
        semantic_family = "key-fact"
    elif (
        re.search(
            r"\d[\d,.]*\s*(?:억\s*원|억원|%|배|건|곳)",
            combined,
        )
        and not (
            re.search(r"(?:19|20)\d{2}\s*년", combined)
            and re.search(r"\d[\d,.]*\s*(?:억\s*원|억원)", combined)
            and re.search(
                r"(?:기간|과정|단계|이후|부터|까지|년간|개월)",
                combined,
            )
        )
    ):
        semantic_family = "key-fact"
    elif re.search(
        r"(?:\d+\s*(?:일|주|개월|년|단계|차|번째))|"
        r"(?:이후|다음|순서|과정|기간|부터|까지)",
        combined,
    ):
        semantic_family = "progression"
    elif re.search(
        r"\d[\d,.]*\s*(?:만\s*)?"
        r"(?:명|억\s*원|억원|%|배|건|곳)",
        combined,
    ):
        semantic_family = "key-fact"
    else:
        semantic_family = "evidence-brief"
    return semantic_family, semantic_family


def _extract_key_fact_value(
    content_by_region: Mapping[str, Any],
) -> str:
    combined = " ".join(
        _text(item.get("content"))
        for item in content_by_region.values()
        if isinstance(item, Mapping)
    )
    match = re.search(
        r"\d[\d,.]*\s*(?:만\s*)?"
        r"(?:명|억\s*원|억원|%|배|건|곳)",
        combined,
    )
    return re.sub(r"\s+", "", match.group(0)) if match else ""


def _detail_family_box(
    family: str,
    semantic_role: str,
) -> tuple[float, float, float, float]:
    boxes = {
        "key-fact": {
            "headline": (112, 470, 856, 170),
            "body": (112, 810, 856, 210),
        },
        "quote": {
            "headline": (130, 245, 810, 395),
            "body": (140, 790, 800, 180),
        },
        "progression": {
            "headline": (220, 215, 740, 310),
            "body": (220, 610, 740, 420),
        },
        "evidence-brief": {
            "headline": (112, 230, 856, 350),
            "body": (112, 720, 856, 350),
        },
    }
    x, y, width, height = boxes.get(
        family,
        boxes["evidence-brief"],
    ).get(semantic_role, boxes["evidence-brief"]["body"])
    return (
        x / CANVAS_WIDTH,
        y / CANVAS_HEIGHT,
        width / CANVAS_WIDTH,
        height / CANVAS_HEIGHT,
    )


def _detail_family_scaffold(
    family: str,
    *,
    account_label: str,
    page_number: int,
    accent: str,
    key_fact_value: str = "",
    key_fact_headline: str = "",
    has_body_content: bool = True,
) -> list[dict[str, Any]]:
    palette = DETAIL_SAFE_PALETTES.get(
        family,
        DETAIL_SAFE_PALETTES["evidence-brief"],
    )
    accent = str(palette["accent"])
    children: list[dict[str, Any]] = [
        {
            "type": "div",
            "props": {
                "style": {
                    "position": "absolute",
                    "inset": "0px",
                    "display": "flex",
                    "backgroundColor": palette["background"],
                    "zIndex": 0,
                },
                "children": [],
            },
        },
        {
            "type": "div",
            "props": {
                "style": {
                    "position": "absolute",
                    "left": "6.666667%",
                    "top": "5.333333%",
                    "width": "86.666667%",
                    "height": "5.333333%",
                    "display": "flex",
                    "alignItems": "center",
                    "color": accent,
                    "fontSize": 24,
                    "fontWeight": 800,
                    "letterSpacing": "0.08em",
                    "zIndex": 3,
                },
                "children": account_label,
            },
        },
    ]
    if family == "key-fact":
        giant_value = key_fact_value or key_fact_headline
        giant_copy, giant_font_size, _, _ = _fit_text_to_region(
            giant_value,
            width_px=856,
            height_px=250,
            requested_font_size=162,
            minimum_font_size=130,
            line_height=0.96,
            maximum_lines=2,
            hard_character_limit=42,
        )
        children.extend(
            [
                {
                    "type": "div",
                    "props": {
                        "style": {
                            "position": "absolute",
                            "left": "6.666667%",
                            "top": "15.555556%",
                            "width": "1.111111%",
                            "height": "30.370370%",
                            "display": "flex",
                            "backgroundColor": accent,
                            "borderRadius": "8px",
                            "zIndex": 1,
                        },
                        "children": [],
                    },
                },
                {
                    "type": "div",
                    "props": {
                        "dataRole": "key-fact-giant",
                        "style": {
                            "position": "absolute",
                            "left": "10.370370%",
                            "top": "14.074074%",
                            "width": "79.259259%",
                            "height": "18.518519%",
                            "display": "flex",
                            "alignItems": "center",
                            "color": accent,
                            "fontSize": giant_font_size,
                            "fontWeight": 900,
                            "lineHeight": 0.96,
                            "whiteSpace": "pre-wrap",
                            "wordBreak": "keep-all",
                            "overflow": "hidden",
                            "zIndex": 3,
                        },
                        "children": giant_copy,
                    },
                },
                {
                    "type": "div",
                    "props": {
                        "dataRole": "detail-body-card",
                        "style": {
                            "position": "absolute",
                            "left": "10.370370%",
                            "top": "57.037037%",
                            "width": "79.259259%",
                            "height": "20.740741%",
                            "display": "flex",
                            "backgroundColor": palette["body_card"],
                            "borderRadius": "20px",
                            "zIndex": 1,
                        },
                        "children": [],
                    },
                },
            ]
        )
    elif family == "quote":
        children.extend(
            [
                {
                    "type": "div",
                    "props": {
                        "dataRole": "quote-body-card",
                        "style": {
                            "position": "absolute",
                            "left": "6.666667%",
                            "top": "12.592593%",
                            "display": "flex",
                            "color": accent,
                            "fontSize": 132,
                            "fontWeight": 900,
                            "lineHeight": 0.8,
                            "zIndex": 1,
                        },
                        "children": "“",
                    },
                },
                {
                    "type": "div",
                    "props": {
                        "dataRole": "detail-body-card",
                        "style": {
                            "position": "absolute",
                            "left": "10.370370%",
                            "top": "54.814815%",
                            "width": "79.259259%",
                            "height": "22.222222%",
                            "display": "flex",
                            "borderTop": f"2px solid {accent}",
                            "backgroundColor": palette["body_card"],
                            "borderRadius": "20px",
                            "zIndex": 1,
                        },
                        "children": [],
                    },
                },
            ]
        )
    elif family == "progression":
        children.extend(
            [
                {
                    "type": "div",
                    "props": {
                        "style": {
                            "position": "absolute",
                            "left": "6.666667%",
                            "top": "15.925926%",
                            "width": "11.111111%",
                            "height": "60.740741%",
                            "display": "flex",
                            "alignItems": "flex-start",
                            "justifyContent": "center",
                            "borderRight": f"3px solid {accent}",
                            "color": accent,
                            "fontSize": 58,
                            "fontWeight": 900,
                            "zIndex": 2,
                        },
                        "children": f"{max(1, page_number):02d}",
                    },
                },
                {
                    "type": "div",
                    "props": {
                        "dataRole": "detail-body-card",
                        "style": {
                            "position": "absolute",
                            "left": "20.370370%",
                            "top": "45.185185%",
                            "width": "68.518519%",
                            "height": "31.111111%",
                            "display": "flex",
                            "backgroundColor": palette["body_card"],
                            "borderRadius": "20px",
                            "zIndex": 1,
                        },
                        "children": [],
                    },
                },
            ]
        )
    else:
        children.extend(
            [
                {
                    "type": "div",
                    "props": {
                        "dataRole": "detail-body-card",
                        "style": {
                            "position": "absolute",
                            "left": "6.666667%",
                            "top": "14.074074%",
                            "width": "86.666667%",
                            "height": "31.851852%",
                            "display": "flex",
                            "borderTop": f"4px solid {accent}",
                            "backgroundColor": "#102B30",
                            "borderRadius": "20px",
                            "zIndex": 1,
                        },
                        "children": [],
                    },
                },
                {
                    "type": "div",
                    "props": {
                        "style": {
                            "position": "absolute",
                            "left": "6.666667%",
                            "top": "50.370370%",
                            "width": "86.666667%",
                            "height": "31.851852%",
                            "display": "flex",
                            "backgroundColor": palette["body_card"],
                            "borderRadius": "20px",
                            "zIndex": 1,
                        },
                        "children": [],
                    },
                },
            ]
        )
    if not has_body_content:
        children = [
            child
            for child in children
            if child.get("props", {}).get("dataRole") != "detail-body-card"
        ]
    children.append(
        {
            "type": "div",
            "props": {
                "style": {
                    "position": "absolute",
                    "left": "6.666667%",
                    "top": "88.148148%",
                    "width": "86.666667%",
                    "height": "6.518519%",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "borderTop": f"1px solid {DETAIL_FOOTER_RULE}",
                    "paddingTop": "18px",
                    "color": DETAIL_FOOTER_COLOR,
                    "fontSize": 22,
                    "fontWeight": 700,
                    "letterSpacing": "0.04em",
                    "zIndex": 3,
                },
                "children": [
                    {
                        "type": "span",
                        "props": {"children": "SOURCE RECORDED"},
                    },
                    {
                        "type": "span",
                        "props": {
                            "children": f"{max(1, page_number):02d}"
                        },
                    },
                ],
            },
        }
    )
    return children


def build_reference_v2_satori_tree(
    adapted_slide: Any,
    *,
    fallback_image_uri: str = "",
    page: int | None = None,
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
    sorted_regions = sorted(
        (item for item in regions if isinstance(item, Mapping)),
        key=lambda item: int(item.get("z_index") or 0),
    )
    has_media_region = any(
        str(item.get("role") or "") in {"primary_media", "secondary_media"}
        for item in sorted_regions
    )
    slide_payload = adapted_slide.get("slide")
    slide_payload = (
        slide_payload if isinstance(slide_payload, Mapping) else adapted_slide
    )
    asset_refs = slide_payload.get("asset_refs")
    if not isinstance(asset_refs, list):
        asset_refs = adapted_slide.get("asset_refs")
    visual_spec = slide_payload.get("visual_spec")
    if not isinstance(visual_spec, Mapping):
        visual_spec = adapted_slide.get("visual_spec")
    visual_spec = visual_spec if isinstance(visual_spec, Mapping) else {}
    source_media_candidate = visual_spec.get("source_media_candidate")
    source_media_candidate = (
        source_media_candidate
        if isinstance(source_media_candidate, Mapping)
        else {}
    )
    has_actual_assets = (
        (
            isinstance(asset_refs, list)
            and any(
                bool(item)
                for item in asset_refs
                if isinstance(item, (Mapping, str))
            )
        )
        or any(
            bool(item)
            for item in (
                source_media_candidate.get("local_path"),
                source_media_candidate.get("asset_id"),
            )
        )
    )
    image_dominant_geometry = (
        not has_media_region and len(sorted_regions) <= 6 and bool(fallback_image_uri)
    )
    slide_role = str(
        adapted_slide.get("slide_role")
        or adapted_slide.get("page_role")
        or adapted_slide.get("role")
        or ""
    ).casefold()
    explicit_page = page is not None
    page_value = page
    if page_value is None:
        page_value = slide_payload.get("page")
    if page_value in (None, ""):
        page_value = adapted_slide.get("page")
    try:
        page_number = int(page_value)
    except (TypeError, ValueError):
        page_number = 0
    cover_or_source_role = (
        slide_role
        in {
            "cover",
            "hook",
            "opening",
            "first",
            "source",
            "source_slide",
            "source_context",
        }
        or page_number == 1
    )
    if explicit_page:
        cover_image_branch = page_number == 1 and bool(fallback_image_uri)
        image_branch_allowed = cover_image_branch
        is_cover = cover_image_branch
        media_free_detail = page_number > 1
        legacy_image_branch = False
    else:
        image_branch_allowed = image_dominant_geometry
        cover_image_branch = False
        legacy_image_branch = image_dominant_geometry
        is_cover = image_dominant_geometry
        media_free_detail = False
    image_background_branch = cover_image_branch or legacy_image_branch
    legacy_mode = not explicit_page
    detail_family = ""
    detail_semantic_signal = ""
    detail_accent = DETAIL_ACCENT
    if media_free_detail:
        detail_family, detail_semantic_signal = _detail_family_context(
            adapted_slide,
            page_number=page_number,
            content_by_region=content_by_region,
        )
        accent_seed = repr(
            sorted(dict(tokens).items())
        ) + _text(adapted_slide.get("primary_reference_id"))
        detail_accent = DETAIL_ACCENTS[
            int(
                hashlib.sha256(accent_seed.encode("utf-8")).hexdigest()[:8],
                16,
            )
            % len(DETAIL_ACCENTS)
        ]
        detail_accent = str(
            DETAIL_SAFE_PALETTES[detail_family]["accent"]
        )
    key_fact_value = (
        _extract_key_fact_value(content_by_region)
        if detail_family == "key-fact"
        else ""
    )
    children = []
    if image_background_branch:
        children.extend(
            [
                {
                    "type": "img",
                    "props": {
                        "src": fallback_image_uri,
                        "style": {
                            "position": "absolute",
                            "inset": "0px",
                            "width": "100%",
                            "height": "100%",
                            "objectFit": "cover",
                            "zIndex": 0,
                        },
                    },
                },
            ]
        )

    if legacy_image_branch:
        children.append(
            {
                "type": "div",
                "props": {
                    "style": {
                        "position": "absolute",
                        "inset": "0px",
                        "display": "flex",
                        "backgroundImage": (
                            "linear-gradient(180deg, rgba(0,0,0,0.04) 35%, "
                            "rgba(0,0,0,0.88) 100%)"
                        ),
                        "zIndex": 1,
                    },
                    "children": [],
                },
            }
        )

    if cover_image_branch:
        children.extend(
            [
                {
                    "type": "div",
                    "props": {
                        "style": {
                            "position": "absolute",
                            "inset": "0px",
                            "display": "flex",
                            "backgroundImage": (
                                "linear-gradient(180deg, rgba(0,0,0,0.08) 28%, "
                                "rgba(0,0,0,0.96) 100%)"
                            ),
                            "zIndex": 1,
                        },
                        "children": [],
                    },
                },
                {
                    "type": "div",
                    "props": {
                        "style": {
                            "position": "absolute",
                            "left": "4.444444%",
                            "top": "64.444444%",
                            "width": "91.111111%",
                            "height": "28.888889%",
                            "display": "flex",
                            "backgroundColor": "rgba(11,31,36,0.90)",
                            "borderRadius": "18px",
                            "zIndex": 2,
                        },
                        "children": [],
                    },
                },
                {
                    "type": "div",
                    "props": {
                        "style": {
                            "position": "absolute",
                            "left": "7.037037%",
                            "top": "89.629630%",
                            "width": "85.925926%",
                            "height": "3.333333%",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "space-between",
                            "borderTop": "1px solid rgba(229,176,74,0.62)",
                            "paddingTop": "10px",
                            "color": "#C9D3D1",
                            "fontSize": 20,
                            "fontWeight": 700,
                            "letterSpacing": "0.04em",
                            "zIndex": 4,
                        },
                        "children": [
                            {
                                "type": "span",
                                "props": {"children": "SOURCE RECORDED"},
                            },
                            {
                                "type": "span",
                                "props": {
                                    "children": f"{max(1, page_number):02d}"
                                },
                            },
                        ],
                    },
                },
            ]
        )

    if media_free_detail:
        account_label = _text(
            adapted_slide.get("account_label")
            or adapted_slide.get("account")
            or adapted_slide.get("section_label")
            or adapted_slide.get("category")
            or "EDITORIAL BRIEF"
        )
        available_content_roles = {
            _semantic_text_role(str(region.get("role") or ""))
            for region in sorted_regions
            if _text(
                (
                    content_by_region.get(
                        str(region.get("region_id") or ""),
                        {},
                    )
                    or {}
                ).get("content")
            )
        }
        children.extend(
            _detail_family_scaffold(
                detail_family,
                account_label=account_label,
                page_number=page_number,
                accent=detail_accent,
                key_fact_value=key_fact_value,
                has_body_content="body" in available_content_roles,
                key_fact_headline=next(
                    (
                        _text(item.get("content"))
                        for region_id, item in content_by_region.items()
                        if isinstance(item, Mapping)
                        and _semantic_text_role(
                            str(
                                next(
                                    (
                                        region.get("role")
                                        for region in sorted_regions
                                        if str(region.get("region_id") or "")
                                        == region_id
                                    ),
                                    "",
                                )
                            )
                        )
                        == "headline"
                    ),
                    "",
                ),
            )
        )

    text_candidates = []
    for raw in sorted_regions:
        role = str(raw.get("role") or "")
        if role in {"primary_media", "secondary_media", "accent"}:
            continue
        binding = content_by_region.get(str(raw.get("region_id") or ""), {})
        value = _normalize_input_copy(
            _text(binding.get("content") if isinstance(binding, Mapping) else ""),
            headline=_semantic_text_role(role) == "headline",
        )
        box = raw.get("box_norm")
        area = (
            float(box[2]) * float(box[3])
            if isinstance(box, (list, tuple)) and len(box) == 4
            else 0.0
        )
        text_candidates.append(
            (raw, role, _semantic_text_role(role), value, area)
        )
    selected_text_ids: set[str] = set()
    for semantic_role in {item[2] for item in text_candidates}:
        role_rows = [
            item
            for item in text_candidates
            if item[2] == semantic_role and item[3]
        ]
        if not role_rows:
            continue
        best = max(role_rows, key=lambda item: item[4])
        selected_text_ids.add(str(best[0].get("region_id") or ""))

    emitted_copy: list[str] = []
    for raw in sorted_regions:
        box = raw.get("box_norm")
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            return {"status": "blocked", "reason_code": "reference_region_invalid"}
        region_id = str(raw.get("region_id") or "")
        role = str(raw.get("role") or "")
        semantic_role = _semantic_text_role(role)
        if media_free_detail and role in {
            "primary_media",
            "secondary_media",
            "accent",
        }:
            continue
        if (
            role not in {"primary_media", "secondary_media", "accent"}
            and region_id not in selected_text_ids
        ):
            continue
        if (
            media_free_detail
            and detail_family == "key-fact"
            and semantic_role == "headline"
            and not key_fact_value
        ):
            continue
        if legacy_mode:
            bounded = tuple(float(item) for item in box)
        elif cover_image_branch and semantic_role == "headline":
            bounded = (
                76 / CANVAS_WIDTH,
                915 / CANVAS_HEIGHT,
                928 / CANVAS_WIDTH,
                160 / CANVAS_HEIGHT,
            )
        elif cover_image_branch and semantic_role == "body":
            bounded = (
                76 / CANVAS_WIDTH,
                1080 / CANVAS_HEIGHT,
                928 / CANVAS_WIDTH,
                105 / CANVAS_HEIGHT,
            )
        else:
            bounded = _bounded_box(
                box,
                text_region=role
                not in {"primary_media", "secondary_media", "accent"},
            )
        if bounded is None:
            return {
                "status": "blocked",
                "reason_code": "reference_region_outside_safe_area",
            }
        if media_free_detail and semantic_role == "headline":
            bounded = _detail_family_box(detail_family, "headline")
        elif media_free_detail and semantic_role == "body":
            bounded = _detail_family_box(detail_family, "body")
        style = {
            "position": "absolute",
            "left": f"{bounded[0] * 100:.6f}%",
            "top": f"{bounded[1] * 100:.6f}%",
            "width": f"{bounded[2] * 100:.6f}%",
            "height": f"{bounded[3] * 100:.6f}%",
            "zIndex": int(raw.get("z_index") or 0),
            "display": "flex",
        }
        if legacy_mode:
            style["overflow"] = "hidden"
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
                    "style": {
                        **style,
                        "overflow": "hidden",
                        "objectFit": str(raw.get("object_fit") or "cover"),
                    },
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
            value = _normalize_input_copy(
                _text(binding.get("content") if isinstance(binding, Mapping) else ""),
                headline=semantic_role == "headline",
            )
            if not value:
                continue
            if _is_duplicate_copy(value, emitted_copy):
                continue
            if media_free_detail:
                family_palette = DETAIL_SAFE_PALETTES.get(
                    detail_family,
                    DETAIL_SAFE_PALETTES["evidence-brief"],
                )
                color = str(
                    family_palette[
                        "headline" if semantic_role == "headline" else "body"
                    ]
                )
            else:
                color = str(
                    raw.get("color")
                    or (
                        "#FFFFFF"
                        if image_background_branch
                        else tokens.get("text_color")
                        or tokens.get("ink")
                        or "#111111"
                    )
                )
            if legacy_mode:
                requested_font_size = int(
                    raw.get("font_size")
                    or (
                        48
                        if semantic_role == "headline"
                        and image_dominant_geometry
                        else 30
                        if image_dominant_geometry
                        else tokens.get("font_size")
                        or 44
                    )
                )
            else:
                requested_font_size = int(
                    raw.get("font_size")
                    or (
                        52 if semantic_role == "headline" and is_cover
                        else 32 if is_cover
                        else (
                            48
                            if detail_family == "key-fact"
                            else 62
                            if detail_family == "quote"
                            else 56
                            if detail_family == "progression"
                            else 58
                        )
                        if semantic_role == "headline"
                        else (
                            32
                            if detail_family == "key-fact"
                            else max(30, int(tokens.get("font_size") or 34))
                        )
                    )
                )
            line_height = float(
                raw.get("line_height")
                or (1.08 if semantic_role == "headline" else 1.25)
            )
            if semantic_role == "headline":
                maximum_lines = 3
                minimum_font_size = 50
                hard_character_limit = 96 if is_cover else 110
            else:
                maximum_lines = 2 if is_cover else 6
                minimum_font_size = 30
                hard_character_limit = 84 if is_cover else 320
            fitted_value, font_size, _, _ = (
                _fit_text_to_region(
                    value,
                    width_px=bounded[2] * CANVAS_WIDTH,
                    height_px=bounded[3] * CANVAS_HEIGHT,
                    requested_font_size=requested_font_size,
                    minimum_font_size=minimum_font_size,
                    line_height=line_height,
                    maximum_lines=maximum_lines,
                    hard_character_limit=hard_character_limit,
                )
            )
            if not fitted_value:
                continue
            if semantic_role == "headline":
                fitted_value = _balance_headline_lines(
                    fitted_value,
                    maximum_lines=maximum_lines,
                )
            emitted_copy.append(_normalized_copy(value))
            text_z_index = int(raw.get("z_index") or 0)
            if cover_image_branch:
                text_z_index = max(
                    text_z_index,
                    4 if semantic_role == "headline" else 3,
                )
            elif (
                media_free_detail
                and detail_family == "quote"
                and semantic_role == "body"
            ):
                text_z_index = max(text_z_index, 3)
            child = {
                "type": "div",
                "props": {
                    "dataTextRole": semantic_role,
                    "style": {
                        **style,
                        "zIndex": text_z_index,
                        "color": color,
                        "fontSize": font_size,
                        "fontWeight": int(
                            raw.get("font_weight")
                            or (
                                700
                                if legacy_mode
                                else 800
                                if semantic_role == "headline"
                                else 500
                            )
                        ),
                        "lineHeight": line_height,
                        "alignItems": str(raw.get("align_items") or "flex-start"),
                        "whiteSpace": "pre-wrap",
                        "wordBreak": "keep-all",
                        "overflowWrap": "anywhere",
                    },
                    "children": fitted_value,
                },
            }
        children.append(child)

    return {
        "status": "ready",
        "reason_code": "reference_geometry_tree_built",
        "geometry_hash": adapted_slide.get("geometry_hash"),
        "detail_family": detail_family or None,
        "detail_semantic_signal": detail_semantic_signal or None,
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
                    "backgroundColor": (
                        str(
                            DETAIL_SAFE_PALETTES[detail_family][
                                "background"
                            ]
                        )
                        if media_free_detail
                        else str(tokens.get("background") or "#F5F1E8")
                    ),
                },
                "children": children,
            },
        },
    }


__all__ = ["build_reference_v2_satori_tree"]
