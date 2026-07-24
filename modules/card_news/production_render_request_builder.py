"""Build a bounded Satori render request from an approved CardNews package."""

from __future__ import annotations

import copy
import base64
import io
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping

from modules.card_news.reference_v2_satori_adapter import (
    build_reference_v2_satori_tree,
)
from modules.design_learning.reference_specimen_registry import (
    is_visual_gate_pass_receipt,
)
from urllib.parse import urlparse

from PIL import Image, ImageOps

from modules.card_news.canvas_contract import (
    DEFAULT_CARD_CANVAS_SIZE,
    DEFAULT_CARD_NEWS_PROFILE_ID,
    get_card_canvas_profile,
)


SCHEMA_VERSION = "cardnews_renderer_request_v1"
PROFILE_ID = DEFAULT_CARD_NEWS_PROFILE_ID
MAX_SLIDES = 20
VISUAL_TYPES = {
    "cover_editorial",
    "delta_comparison",
    "flow_summary",
    "evidence_card",
    "cta_prompt",
}
LEARNED_RENDER_FIELDS = (
    "first_screen",
    "layout_family",
    "composition",
    "palette",
    "typography",
    "image_grammar",
    "text_density",
    "emotional_tone",
    "account_identity",
)
LEARNED_FIELD_ALIASES = {
    "first_screen": ("first_screen", "first_frame", "opening_frame", "cover_strategy"),
    "layout_family": ("layout_family", "layout", "layout_profile"),
    "composition": ("composition", "composition_rule", "visual_composition"),
    "palette": ("palette", "color_palette", "palette_intent"),
    "typography": ("typography", "type_system", "font_direction"),
    "image_grammar": ("image_grammar", "media_grammar", "visual_grammar"),
    "text_density": ("text_density", "copy_density", "content_density"),
    "emotional_tone": ("emotional_tone", "emotion", "mood", "tone"),
    "account_identity": ("account_identity", "account_label", "brand_identity"),
}
ACCOUNT_THEMES = {
    "A": {
        "cover_kicker": "MONEY / DATA BRIEF",
        "detail_kicker": "MARKET SHIFT",
        "footer": "AI-CONTENT-OS / NEWS",
        "source_label": "SOURCE · ORIGINAL REPORT",
        "cover_panel": "rgba(245,248,240,0.94)",
        "cover_ink": "#142018",
        "cover_muted": "#647267",
        "cover_accent": "#b7d63f",
        "detail_palettes": (
            ("#eef3e8", "#1b291f", "#91aa35"),
            ("#e8eef3", "#172833", "#4a90b8"),
            ("#f4eee2", "#342b20", "#d18b39"),
        ),
    },
    "B": {
        "cover_kicker": "DOPAMINE / STORY NOTE",
        "detail_kicker": "STORY TURN",
        "footer": "AI-CONTENT-OS / STORY",
        "source_label": "SOURCE · ORIGINAL CONTEXT",
        "cover_panel": "rgba(255,248,235,0.94)",
        "cover_ink": "#33252a",
        "cover_muted": "#8a6872",
        "cover_accent": "#f07191",
        "detail_palettes": (
            ("#fff1e1", "#3a2928", "#ed896f"),
            ("#f9e9ed", "#38252d", "#d96d8c"),
            ("#eee9f5", "#2d2938", "#9680bd"),
        ),
    },
    "C": {
        "cover_kicker": "STYLE / BEAUTY FILE",
        "detail_kicker": "STYLE DETAIL",
        "footer": "AI-CONTENT-OS / STYLE",
        "source_label": "SOURCE · OFFICIAL / EDITORIAL",
        "cover_panel": "rgba(246,248,243,0.94)",
        "cover_ink": "#17201a",
        "cover_muted": "#758078",
        "cover_accent": "#b7c8a8",
        "detail_palettes": (
            ("#eef1e9", "#233128", "#9ead8f"),
            ("#e6eceb", "#1d3031", "#8fa9a7"),
            ("#f2ece5", "#352b25", "#c3a98f"),
        ),
    },
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _reference_text_role(value: Any) -> str:
    role = _text(value).casefold()
    if role in {"headline", "title", "hook", "hook_headline"}:
        return "headline"
    if role in {
        "body",
        "description",
        "supporting_text",
        "summary",
        "caption",
        "detail",
    }:
        return "body"
    return role


def _rebind_reference_copy(
    adapted_slide: Mapping[str, Any],
    current_slide: Mapping[str, Any],
) -> Dict[str, Any]:
    rebound = copy.deepcopy(dict(adapted_slide))
    regions = rebound.get("regions")
    bindings = rebound.get("content_bindings")
    if not isinstance(regions, list) or not isinstance(bindings, list):
        return rebound
    role_by_region = {
        _text(region.get("region_id")): _reference_text_role(region.get("role"))
        for region in regions
        if isinstance(region, Mapping) and _text(region.get("region_id"))
    }
    final_copy = {
        "headline": _text(current_slide.get("headline")),
        "body": _text(current_slide.get("body")),
    }
    rebound["content_bindings"] = [
        {
            **copy.deepcopy(dict(binding)),
            "content": final_copy.get(
                role_by_region.get(_text(binding.get("region_id")), ""),
                _text(binding.get("content")),
            ),
        }
        if isinstance(binding, Mapping)
        else copy.deepcopy(binding)
        for binding in bindings
    ]
    nested_slide = (
        copy.deepcopy(dict(rebound.get("slide")))
        if isinstance(rebound.get("slide"), Mapping)
        else {}
    )
    nested_slide.update(copy.deepcopy(dict(current_slide)))
    rebound["slide"] = nested_slide
    return rebound


def _source_display_label(value: Any) -> str:
    host = (urlparse(_text(value)).hostname or "").casefold().removeprefix("www.")
    labels = {
        "news1.kr": "SOURCE · NEWS1",
        "youtube.com": "SOURCE · YOUTUBE",
        "youtu.be": "SOURCE · YOUTUBE",
        "commons.wikimedia.org": "SOURCE · WIKIMEDIA COMMONS",
    }
    return labels.get(host, f"SOURCE · {host.upper()}" if host else "SOURCE RECORDED")


def _source_attribution_label(candidate: Any) -> str:
    if not isinstance(candidate, Mapping):
        return ""
    attribution = _text(
        candidate.get("attribution_text") or candidate.get("attribution")
    )
    license_name = _text(
        candidate.get("license_name") or candidate.get("license")
    )
    parts = [value for value in (attribution, license_name) if value]
    if parts:
        label = " · ".join(dict.fromkeys(parts))
        return label if len(label) <= 96 else f"{label[:95].rstrip()}…"
    return _source_display_label(candidate.get("source_url"))


def _safe_path_segment(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z._-]+", "-", value).strip("-.")
    return normalized[:96] or "candidate"


def _blocked(reason: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked",
        "reason_code": reason,
        "render_request": None,
    }


def _image_data_uri(
    path: Path,
    *,
    fit_cover: bool = True,
    target_size: tuple[int, int] = DEFAULT_CARD_CANVAS_SIZE,
) -> tuple[str, int, int]:
    with Image.open(path) as source:
        source = ImageOps.exif_transpose(source).convert("RGB")
        source_width, source_height = source.size
        prepared = (
            ImageOps.fit(
                source,
                target_size,
                method=Image.Resampling.LANCZOS,
                centering=(0.62, 0.46),
            )
            if fit_cover
            else source
        )
        buffer = io.BytesIO()
        prepared.save(buffer, format="JPEG", quality=82, optimize=True, progressive=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}", source_width, source_height


def _node(node_type: str, *, style: Mapping[str, Any] | None = None, children: Any = None, **props: Any) -> Dict[str, Any]:
    node_props: Dict[str, Any] = dict(props)
    normalized_style = dict(style or {})
    if (
        node_type == "div"
        and isinstance(children, list)
        and len(children) > 1
        and "display" not in normalized_style
    ):
        normalized_style["display"] = "flex"
        normalized_style.setdefault("flexDirection", "column")
    if normalized_style:
        node_props["style"] = normalized_style
    if children is not None:
        node_props["children"] = children
    return {"type": node_type, "props": node_props}


def _short_heading(body: str, fallback: str) -> str:
    for marker in (".", "!", "?", "。", "！", "？"):
        first = body.split(marker, 1)[0].strip()
        if first and len(first) <= 42:
            return first
    return body[:38].rstrip() + ("…" if len(body) > 38 else "") or fallback


def _heading_and_remainder(body: str, fallback: str) -> tuple[str, str]:
    first = body
    consumed = len(body)
    sentence_boundary = re.search(r"(?<!\d)[.!?。！？](?!\d)|…", body)
    if sentence_boundary is not None:
        position = sentence_boundary.start()
        first = body[:position].strip()
        consumed = sentence_boundary.end()
    if len(first) <= 42:
        return first or fallback, body[consumed:].lstrip()

    cut = first.rfind(" ", 0, 39)
    if cut < 18:
        cut = 38
    heading = first[:cut].rstrip() + "…"
    remainder = body[cut:].lstrip()
    return heading, remainder


def _theme(account: str) -> Mapping[str, Any]:
    return ACCOUNT_THEMES.get(account, ACCOUNT_THEMES["A"])


def _design_system(account: str, supplied: Any) -> Dict[str, Any]:
    theme = _theme(account)
    raw = supplied if isinstance(supplied, Mapping) else {}
    palette = raw.get("palette") if isinstance(raw.get("palette"), Mapping) else {}
    fallback_background, fallback_ink, fallback_accent = theme["detail_palettes"][0]
    return {
        "account_id": _text(raw.get("account_id")) or account,
        "background": _text(palette.get("background")) or fallback_background,
        "ink": _text(palette.get("ink")) or fallback_ink,
        "accent": _text(palette.get("accent")) or fallback_accent,
        "muted": _text(palette.get("muted")) or theme["cover_muted"],
        "panel": _text(palette.get("panel")) or theme["cover_panel"],
        "cover_kicker": _text(raw.get("cover_kicker")) or theme["cover_kicker"],
        "detail_kicker": _text(raw.get("detail_kicker")) or theme["detail_kicker"],
        "footer_label": _text(raw.get("footer_label")) or theme["footer"],
        "source_label": _text(raw.get("source_label")) or theme["source_label"],
    }


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _learned_render_contract(
    supplied: Any,
    learning_trace: Any,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    raw = supplied if isinstance(supplied, Mapping) else {}
    trace = learning_trace if isinstance(learning_trace, Mapping) else {}
    trace_design = (
        trace.get("design_guidance")
        if isinstance(trace.get("design_guidance"), Mapping)
        else {}
    )
    profile_containers: List[tuple[str, Mapping[str, Any]]] = []
    for key in (
        "learned_profile",
        "learned_design_profile",
        "learned_visual_guidance",
        "design_profile",
    ):
        value = raw.get(key)
        if isinstance(value, Mapping) and value:
            profile_containers.append((f"design_system.{key}", value))

    profile_present = bool(profile_containers) or (
        _text(raw.get("theme_priority")) == "learned_guidance_over_account_default"
    ) or trace_design.get("available") is True
    search_sources = list(profile_containers)
    for source_name, container in list(profile_containers):
        visual_direction = container.get("visual_direction")
        if isinstance(visual_direction, Mapping) and visual_direction:
            search_sources.append(
                (f"{source_name}.visual_direction", visual_direction)
            )

    learned_design: Dict[str, Any] = {}
    consumed_paths: Dict[str, str] = {}
    consumed_source_keys: set[str] = set()
    for target_field, aliases in LEARNED_FIELD_ALIASES.items():
        for source_name, container in reversed(search_sources):
            matched_alias = next(
                (alias for alias in aliases if _present(container.get(alias))),
                "",
            )
            if not matched_alias:
                continue
            learned_design[target_field] = container[matched_alias]
            consumed_paths[target_field] = f"{source_name}.{matched_alias}"
            consumed_source_keys.add(f"{source_name}.{matched_alias}")
            break

    # A scalar learned visual direction is preserved as image grammar rather
    # than silently disappearing between the compiler and renderer.
    if "image_grammar" not in learned_design:
        for source_name, container in reversed(profile_containers):
            visual_direction = container.get("visual_direction")
            if _present(visual_direction) and not isinstance(visual_direction, Mapping):
                learned_design["image_grammar"] = visual_direction
                consumed_paths["image_grammar"] = f"{source_name}.visual_direction"
                consumed_source_keys.add(f"{source_name}.visual_direction")
                break

    available_paths: set[str] = set()
    for source_name, container in search_sources:
        for key, value in container.items():
            if not str(key).startswith("_") and _present(value):
                available_paths.add(f"{source_name}.{key}")
    ignored_fields = sorted(available_paths - consumed_source_keys)
    missing_fields = [
        field for field in LEARNED_RENDER_FIELDS if field not in learned_design
    ]
    receipt = {
        "profile_present": profile_present,
        "status": (
            "consumed"
            if learned_design
            else "not_consumed" if profile_present else "not_supplied"
        ),
        "consumed_fields": sorted(learned_design),
        "consumed_paths": consumed_paths,
        "ignored_fields": ignored_fields,
        "missing_fields": missing_fields,
        "core_consumed_count": len(learned_design),
    }
    return learned_design, receipt


def _applied_render_style(
    learned_design: Mapping[str, Any],
    candidate_receipt: Mapping[str, Any],
    design: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    style: Dict[str, Any] = {
        "font_family": "Pretendard",
        "cover_panel_width": 470,
        "cover_panel_left": 54,
        "cover_text_align": "left",
        "cover_headline_size": 58,
        "cover_headline_line_height": 1.18,
        "detail_headline_size": 60,
        "detail_headline_line_height": 1.18,
        "detail_body_size": 31,
        "detail_body_line_height": 1.62,
        "detail_text_align": "left",
        "detail_gap": 44,
        "media_height": 300,
        "media_fit": "contain",
    }
    applied: Dict[str, Any] = {}

    palette = learned_design.get("palette")
    if isinstance(palette, Mapping):
        updates = {
            key: _text(palette.get(key))
            for key in ("background", "ink", "accent", "muted", "panel")
            if _text(palette.get(key))
        }
        if updates:
            design.update(updates)
            applied["palette"] = dict(palette)

    first_screen = learned_design.get("first_screen")
    first_screen_text = str(first_screen).casefold()
    if _present(first_screen) and any(
        token in first_screen_text
        for token in (
            "split",
            "left",
            "right",
            "center",
            "full",
            "분할",
            "왼쪽",
            "오른쪽",
            "중앙",
            "전면",
        )
    ):
        if "center" in first_screen_text or "중앙" in first_screen_text:
            style["cover_panel_width"] = 760
            style["cover_panel_left"] = 160
            style["cover_text_align"] = "center"
        elif "right" in first_screen_text or "오른쪽" in first_screen_text:
            style["cover_panel_left"] = 556
        elif "full" in first_screen_text or "전면" in first_screen_text:
            style["cover_panel_width"] = 972
        applied["first_screen"] = first_screen

    layout_family = _text(learned_design.get("layout_family")).casefold()
    if layout_family in {"editorial_split", "split", "split_screen"}:
        style["cover_panel_width"] = min(style["cover_panel_width"], 440)
        style["detail_text_align"] = "left"
        applied["layout_family"] = learned_design["layout_family"]
    elif layout_family in {"centered_panel", "centered", "magazine_center"}:
        style["cover_panel_width"] = 760
        style["cover_panel_left"] = 160
        style["cover_text_align"] = "center"
        style["detail_text_align"] = "center"
        applied["layout_family"] = learned_design["layout_family"]
    elif layout_family in {"full_bleed", "full_bleed_editorial"}:
        style["cover_panel_width"] = 972
        style["cover_panel_left"] = 54
        applied["layout_family"] = learned_design["layout_family"]

    composition = learned_design.get("composition")
    if isinstance(composition, Mapping):
        changed = False
        image_ratio = composition.get("image_ratio")
        if isinstance(image_ratio, (int, float)) and 0.3 <= image_ratio <= 0.8:
            style["cover_panel_width"] = int(972 * (1.0 - float(image_ratio)))
            style["media_height"] = int(520 * float(image_ratio))
            changed = True
        copy_anchor = _text(composition.get("copy_anchor")).casefold()
        if copy_anchor in {"left", "center", "right"}:
            style["cover_text_align"] = copy_anchor
            style["detail_text_align"] = copy_anchor
            if copy_anchor == "right":
                style["cover_panel_left"] = 1080 - 54 - style["cover_panel_width"]
            changed = True
        if changed:
            applied["composition"] = dict(composition)

    typography = learned_design.get("typography")
    if isinstance(typography, Mapping):
        changed = False
        family = _text(typography.get("font_family"))
        if family:
            style["font_family"] = family
            changed = True
        headline = _text(typography.get("headline")).casefold()
        if headline == "bold_condensed":
            style["cover_headline_size"] = 62
            style["detail_headline_size"] = 64
            style["headline_weight"] = 850
            changed = True
        body = _text(typography.get("body")).casefold()
        if body == "short_korean":
            style["detail_body_size"] = 33
            style["detail_body_line_height"] = 1.52
            changed = True
        if changed:
            applied["typography"] = dict(typography)

    density = _text(learned_design.get("text_density")).casefold()
    if density == "low":
        style["cover_headline_size"] += 4
        style["detail_headline_size"] += 4
        style["detail_body_size"] += 2
        style["detail_gap"] = 52
        applied["text_density"] = learned_design["text_density"]
    elif density == "medium":
        applied["text_density"] = learned_design["text_density"]
    elif density == "high":
        style["cover_headline_size"] -= 6
        style["detail_headline_size"] -= 6
        style["detail_body_size"] -= 3
        style["detail_gap"] = 34
        applied["text_density"] = learned_design["text_density"]

    tone = _text(learned_design.get("emotional_tone")).casefold()
    tone_palettes = {
        "urgent_warm": {"background": "#fff3df", "accent": "#df4b32"},
        "warning": {"background": "#fff1df", "accent": "#d63d2f"},
        "calm": {"background": "#edf3ef", "accent": "#4f7e6b"},
        "bright": {"background": "#fff8df", "accent": "#ef8b2c"},
        "romantic": {"background": "#fff0f1", "accent": "#d95e7e"},
    }
    if tone in tone_palettes:
        design.update(tone_palettes[tone])
        applied["emotional_tone"] = learned_design["emotional_tone"]

    grammar = learned_design.get("image_grammar")
    grammar_values = (
        [grammar]
        if isinstance(grammar, str)
        else list(grammar) if isinstance(grammar, (list, tuple)) else []
    )
    supported_treatments = {
        "contain": "contain",
        "cover": "cover",
        "full_bleed": "cover",
        "source_editorial": "contain",
    }
    selected_treatment = next(
        (
            supported_treatments[_text(value).casefold()]
            for value in grammar_values
            if _text(value).casefold() in supported_treatments
        ),
        "",
    )
    if selected_treatment:
        style["media_fit"] = selected_treatment
        applied["image_grammar"] = grammar

    consumed_fields = sorted(applied)
    consumed_paths = {
        field: candidate_receipt.get("consumed_paths", {}).get(field, "")
        for field in consumed_fields
    }
    ignored_fields = set(candidate_receipt.get("ignored_fields", []))
    for field, path in candidate_receipt.get("consumed_paths", {}).items():
        if field not in applied and path:
            ignored_fields.add(path)
    receipt = {
        "profile_present": candidate_receipt.get("profile_present") is True,
        "status": (
            "consumed"
            if consumed_fields
            else "not_consumed"
            if candidate_receipt.get("profile_present") is True
            else "not_supplied"
        ),
        "consumed_fields": consumed_fields,
        "consumed_paths": consumed_paths,
        "ignored_fields": sorted(ignored_fields),
        "missing_fields": list(candidate_receipt.get("missing_fields", [])),
        "core_consumed_count": len(consumed_fields),
    }
    return applied, style, receipt


def _visual_spec(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    visual_type = _text(value.get("visual_type"))
    return dict(value) if visual_type in VISUAL_TYPES else {}


def _strip_visible_source_labels(
    tree: Any,
    *,
    labels: tuple[str, ...] = (),
) -> Any:
    """Remove source/credit copy from image trees while preserving metadata."""
    blocked = {_text(label).casefold() for label in labels if _text(label)}
    if isinstance(tree, Mapping):
        return {
            key: _strip_visible_source_labels(value, labels=labels)
            for key, value in tree.items()
        }
    if isinstance(tree, list):
        return [
            _strip_visible_source_labels(value, labels=labels)
            for value in tree
        ]
    if isinstance(tree, str):
        normalized = _text(tree).casefold()
        if (
            normalized in blocked
            or normalized.startswith("source")
            or normalized.startswith("출처")
            or normalized.startswith("참고:")
            or normalized.startswith("http://")
            or normalized.startswith("https://")
        ):
            return ""
    return tree


def _cover_tree(
    title: str,
    body: str,
    image_uri: str,
    account: str,
    design: Mapping[str, str],
    render_style: Mapping[str, Any],
    source_label: str = "",
) -> Dict[str, Any]:
    configured_title_size = int(render_style.get("cover_headline_size", 58))
    title_size = (
        f"{min(configured_title_size, 48)}px"
        if len(title) > 42
        else f"{configured_title_size}px"
    )
    return _node(
        "div",
        style={
            "width": "1080px",
            "height": f"{DEFAULT_CARD_CANVAS_SIZE[1]}px",
            "display": "flex",
            "position": "relative",
            "overflow": "hidden",
            "backgroundColor": design["background"],
            "fontFamily": render_style.get("font_family", "Pretendard"),
        },
        children=[
            _node(
                "img",
                src=image_uri,
                style={
                    "position": "absolute",
                    "inset": "0px",
                    "width": "1080px",
                    "height": f"{DEFAULT_CARD_CANVAS_SIZE[1]}px",
                    "objectFit": "cover",
                },
            ),
            _node(
                "div",
                style={
                    "position": "absolute",
                    "left": f"{int(render_style.get('cover_panel_left', 54))}px",
                    "top": "54px",
                    "bottom": "54px",
                    "width": f"{int(render_style.get('cover_panel_width', 470))}px",
                    "display": "flex",
                    "flexDirection": "column",
                    "justifyContent": "space-between",
                    "padding": "0px",
                    "backgroundColor": "transparent",
                    "borderRadius": "0px",
                    "textShadow": "0 3px 18px rgba(0,0,0,0.72)",
                },
                children=[
                    _node(
                        "div",
                        style={"display": "flex", "flexDirection": "column", "gap": "18px"},
                        children=[
                            _node(
                                "div",
                                style={
                                    "fontSize": "22px",
                                    "fontWeight": 700,
                                    "letterSpacing": "3px",
                                    "color": design["muted"],
                                },
                                children=design["cover_kicker"],
                            ),
                            _node(
                                "div",
                                style={
                                    "width": "68px",
                                    "height": "8px",
                                    "backgroundColor": design["accent"],
                                    "borderRadius": "8px",
                                },
                            ),
                        ],
                    ),
                    _node(
                        "div",
                        style={
                            "fontSize": title_size,
                            "fontWeight": int(render_style.get("headline_weight", 800)),
                            "lineHeight": float(render_style.get("cover_headline_line_height", 1.18)),
                            "letterSpacing": "-2.6px",
                            "color": design["ink"],
                            "wordBreak": "keep-all",
                            "textAlign": render_style.get("cover_text_align", "left"),
                        },
                        children=title,
                    ),
                    _node(
                        "div",
                        style={
                            "fontSize": "19px",
                            "fontWeight": 600,
                            "letterSpacing": "1px",
                            "color": design["muted"],
                        },
                        children=[
                            _node("div", children=design["footer_label"]),
                        ],
                    ),
                ],
            ),
        ],
    )


def _metric_cards(metrics: Any, design: Mapping[str, str]) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    for raw in metrics if isinstance(metrics, list) else []:
        if not isinstance(raw, Mapping):
            continue
        label = _text(raw.get("label"))
        value = _text(raw.get("value"))
        direction = _text(raw.get("direction"))
        if not label and not value and not direction:
            continue
        text_children = []
        for text, size, weight, color in (
            (label, "23px", 650, design["muted"]),
            (value, "46px", 850, design["ink"]),
            (direction, "21px", 750, design["accent"]),
        ):
            if text:
                text_children.append(
                    _node(
                        "div",
                        style={"fontSize": size, "fontWeight": weight, "color": color},
                        children=text,
                    )
                )
        cards.append(
            _node(
                "div",
                style={
                    "display": "flex",
                    "flex": 1,
                    "minHeight": "190px",
                    "flexDirection": "column",
                    "justifyContent": "space-between",
                    "padding": "28px",
                    "backgroundColor": design["panel"],
                    "borderRadius": "24px",
                    "borderTop": f"10px solid {design['accent']}",
                },
                children=text_children,
            )
        )
    return cards


def _flow_graphic(visual_spec: Mapping[str, Any], design: Mapping[str, str]) -> Dict[str, Any]:
    from_label = _text(visual_spec.get("from_label"))
    to_label = _text(visual_spec.get("to_label"))
    delta_label = _text(visual_spec.get("delta_label"))
    nodes = []
    for label in (from_label, to_label):
        if label:
            nodes.append(
                _node(
                    "div",
                    style={
                        "display": "flex",
                        "flex": 1,
                        "minHeight": "150px",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "padding": "28px",
                        "backgroundColor": design["panel"],
                        "borderRadius": "30px",
                        "border": f"4px solid {design['accent']}",
                        "fontSize": "30px",
                        "fontWeight": 800,
                        "textAlign": "center",
                    },
                    children=label,
                )
            )
    flow_children: List[Dict[str, Any]] = []
    if nodes:
        flow_children.append(
            _node(
                "div",
                style={"display": "flex", "alignItems": "center", "gap": "24px"},
                children=[
                    nodes[0],
                    _node(
                        "div",
                        style={
                            "width": "90px",
                            "height": "12px",
                            "backgroundColor": design["accent"],
                            "borderRadius": "12px",
                        },
                    ),
                    *(nodes[1:2]),
                ],
            )
        )
    if delta_label:
        flow_children.append(
            _node(
                "div",
                style={
                    "alignSelf": "center",
                    "padding": "16px 28px",
                    "backgroundColor": design["accent"],
                    "color": design["background"],
                    "borderRadius": "999px",
                    "fontSize": "24px",
                    "fontWeight": 800,
                },
                children=delta_label,
            )
        )
    return _node(
        "div",
        style={"display": "flex", "flexDirection": "column", "gap": "22px"},
        children=flow_children,
    )


def _detail_visual(visual_spec: Mapping[str, Any], design: Mapping[str, str]) -> Dict[str, Any] | None:
    visual_type = _text(visual_spec.get("visual_type"))
    if visual_type == "delta_comparison":
        cards = _metric_cards(visual_spec.get("metrics"), design)
        if cards:
            return _node(
                "div",
                style={"display": "flex", "gap": "22px", "width": "100%"},
                children=cards,
            )
    if visual_type == "flow_summary":
        return _flow_graphic(visual_spec, design)
    if visual_type == "evidence_card":
        return None
    if visual_type == "cta_prompt":
        question = _text(visual_spec.get("question"))
        question_panel = _node(
            "div",
            style={
                "display": "flex",
                "width": "100%",
                "minHeight": "138px",
                "alignItems": "center",
                "justifyContent": "center",
                "padding": "28px",
                "backgroundColor": design["panel"],
                "borderRadius": "30px",
                "border": f"4px solid {design['accent']}",
                "fontSize": "32px",
                "fontWeight": 800,
                "textAlign": "center",
            },
            children=question or None,
        )
        cards = _metric_cards(visual_spec.get("metrics"), design)
        if not cards:
            return question_panel
        return _node(
            "div",
            style={"display": "flex", "flexDirection": "column", "gap": "24px", "width": "100%"},
            children=[
                _node(
                    "div",
                    style={"display": "flex", "gap": "22px", "width": "100%"},
                    children=cards,
                ),
                question_panel,
            ],
        )
    return None


def _detail_tree(
    page: int,
    total: int,
    title: str,
    body: str,
    account: str,
    visual_spec: Mapping[str, Any],
    design: Mapping[str, str],
    supplied_design: bool,
    media_uri: str = "",
    media_width: int = 0,
    media_height: int = 0,
    source_label: str = "",
    render_style: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    render_style = render_style or {}
    theme = _theme(account)
    if supplied_design:
        background, ink, accent = design["background"], design["ink"], design["accent"]
    else:
        palettes = theme["detail_palettes"]
        background, ink, accent = palettes[(page - 2) % len(palettes)]
    visual_type = _text(visual_spec.get("visual_type"))
    source_fact = _text(visual_spec.get("source_fact"))
    if visual_type in {"delta_comparison", "flow_summary", "evidence_card", "cta_prompt"} and title:
        heading = title
        remainder = source_fact or body
        if "…" in remainder:
            remainder = remainder.split("…", 1)[1].strip()
        question = _text(visual_spec.get("question"))
        if question and remainder.endswith(question):
            remainder = remainder[: -len(question)].rstrip()
    else:
        heading, remainder = _heading_and_remainder(body, title)
    copy_children = [
        _node(
            "div",
            style={
                "fontSize": f"{int(render_style.get('detail_headline_size', 60))}px",
                "fontWeight": int(render_style.get("headline_weight", 800)),
                "lineHeight": float(render_style.get("detail_headline_line_height", 1.18)),
                "letterSpacing": "-2.4px",
                "wordBreak": "keep-all",
                "textAlign": render_style.get("detail_text_align", "left"),
            },
            children=heading,
        ),
        _node(
            "div",
            style={
                "width": "100%",
                "height": "2px",
                "backgroundColor": accent,
            },
        ),
    ]
    if remainder:
        copy_children.append(
            _node(
                "div",
                style={
                    "fontSize": f"{int(render_style.get('detail_body_size', 31))}px",
                    "fontWeight": 500,
                    "lineHeight": float(render_style.get("detail_body_line_height", 1.62)),
                    "letterSpacing": "-0.7px",
                    "wordBreak": "keep-all",
                    "textAlign": render_style.get("detail_text_align", "left"),
                },
                children=remainder[:330],
            )
        )
    visual = _detail_visual(visual_spec, design)
    if media_uri:
        copy_density = len(heading) + len(remainder)
        media_box_height = (
            120
            if visual_type == "cta_prompt"
            else 220
            if copy_density > 180
            else int(render_style.get("media_height", 300))
        )
        media_box_height_px = f"{media_box_height}px"
        media_fit = (
            render_style.get("media_fit", "contain")
            if render_style.get("media_fit")
            else "cover"
            if media_width > 0 and media_height > 0 and media_width / media_height >= 1.2
            else "contain"
        )
        copy_children.append(
            _node(
                "div",
                style={
                    "display": "flex",
                    "position": "relative",
                    "width": "908px",
                    "height": media_box_height_px,
                    "overflow": "hidden",
                    "borderRadius": "26px",
                    "backgroundColor": design["panel"],
                },
                children=_node(
                    "img",
                    src=media_uri,
                    style={
                        "position": "absolute",
                        "inset": "0px",
                        "width": "908px",
                        "height": media_box_height_px,
                        "objectFit": media_fit,
                    },
                ),
            )
        )
    if visual is not None:
        copy_children.append(visual)
    return _node(
        "div",
        style={
            "width": "1080px",
            "height": f"{DEFAULT_CARD_CANVAS_SIZE[1]}px",
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "space-between",
            "padding": "86px",
            "backgroundColor": background,
            "color": ink,
            "fontFamily": render_style.get("font_family", "Pretendard"),
        },
        children=[
            _node(
                "div",
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                children=[
                    _node(
                        "div",
                        style={
                            "fontSize": "21px",
                            "fontWeight": 750,
                            "letterSpacing": "3px",
                        },
                        children=design["detail_kicker"],
                    ),
                    _node(
                        "div",
                        style={"fontSize": "21px", "fontWeight": 700, "color": accent},
                        children=f"{page:02d} / {total:02d}",
                    ),
                ],
            ),
            _node(
                "div",
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": f"{int(render_style.get('detail_gap', 44))}px",
                },
                children=[
                    _node(
                        "div",
                        style={
                            "fontSize": "112px",
                            "fontWeight": 800,
                            "lineHeight": 1,
                            "color": accent,
                        },
                        children=f"{page - 1:02d}",
                    ),
                    *copy_children,
                ],
            ),
            _node(
                "div",
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "fontSize": "19px",
                    "fontWeight": 650,
                    "letterSpacing": "1px",
                },
                children=[
                    _node("div", children=design["footer_label"]),
                ],
            ),
        ],
    )


def build_production_render_request(
    package: Any,
    authorization: Any,
    owned_asset_path: str | Path,
    package_path: str | Path | None = None,
) -> Dict[str, Any]:
    if not isinstance(package, Mapping) or package.get("status") != "production_package_ready":
        return _blocked("production_package_not_ready")
    if not isinstance(authorization, Mapping) or authorization.get("authorized") is not True:
        return _blocked("render_authorization_required")

    candidate = package.get("candidate") if isinstance(package.get("candidate"), Mapping) else {}
    candidate_id = _text(candidate.get("candidate_id"))
    account = _text(candidate.get("account")).upper()
    slides = package.get("slides")
    if (
        not candidate_id
        or account not in ACCOUNT_THEMES
        or not isinstance(slides, list)
        or not 1 <= len(slides) <= MAX_SLIDES
    ):
        return _blocked("candidate_or_slide_count_invalid")

    asset_path = Path(owned_asset_path).resolve()
    if not asset_path.is_file():
        return _blocked("owned_asset_missing")
    profile_id = _text(package.get("canvas_profile_id")) or PROFILE_ID
    central_profile = get_card_canvas_profile(profile_id)
    if central_profile is None:
        return _blocked("canvas_profile_invalid")
    profile = dict(central_profile)
    target_size = (int(profile["width"]), int(profile["height"]))
    image_uri, source_width, source_height = _image_data_uri(
        asset_path,
        target_size=target_size,
    )
    reference_v2_required = package.get("reference_v2_required") is True
    reference_v2 = package.get("reference_v2")
    reference_v2 = reference_v2 if isinstance(reference_v2, Mapping) else {}
    reference_v2_rows = reference_v2.get("slides")
    reference_v2_rows = (
        [item for item in reference_v2_rows if isinstance(item, Mapping)]
        if isinstance(reference_v2_rows, list)
        else []
    )
    if reference_v2_required and reference_v2.get("status") != "ready":
        blocked = _blocked(
            _text(reference_v2.get("reason_code"))
            or "owner_approved_reference_geometry_required"
        )
        blocked["reference_v2"] = dict(reference_v2)
        return blocked
    reference_v2_by_page = {
        int(item.get("page") or index): item
        for index, item in enumerate(reference_v2_rows, start=1)
    }
    selection = package.get("slide_asset_selection")
    selection_receipts = (
        selection.get("selection_receipts", [])
        if isinstance(selection, Mapping)
        and isinstance(selection.get("selection_receipts"), list)
        else []
    )
    selected_asset_by_page = {
        int(item.get("page")): _text(item.get("asset_id"))
        for item in selection_receipts
        if isinstance(item, Mapping)
        and isinstance(item.get("page"), int)
        and _text(item.get("asset_id"))
    }
    title = _text(candidate.get("title"))
    supplied_design = isinstance(package.get("design_system"), Mapping)
    design = _design_system(account, package.get("design_system"))
    learned_candidates, candidate_receipt = _learned_render_contract(
        package.get("design_system"),
        package.get("learning_trace"),
    )
    learned_design, render_style, learning_receipt = _applied_render_style(
        learned_candidates,
        candidate_receipt,
        design,
    )
    if (
        learning_receipt["profile_present"]
        and learning_receipt["core_consumed_count"] == 0
    ):
        blocked = _blocked("learned_design_profile_not_consumed")
        blocked["learning_consumption_receipt"] = learning_receipt
        return blocked
    upstream_consumption = package.get(
        "learning_pipeline_consumption_receipt"
    )
    upstream_consumption = (
        copy.deepcopy(dict(upstream_consumption))
        if isinstance(upstream_consumption, Mapping)
        else {}
    )
    if upstream_consumption.get("auto_approval_performed") is True:
        return _blocked("reference_registry_auto_approval_forbidden")
    expected_profile_fields = {
        _text(field)
        for field in upstream_consumption.get(
            "profile_consumed_fields", []
        )
        if _text(field)
    }
    actual_profile_fields = set(learning_receipt["consumed_fields"])
    missing_profile_fields = sorted(
        expected_profile_fields - actual_profile_fields
    )
    if missing_profile_fields:
        blocked = _blocked(
            "production_profile_render_consumption_mismatch"
        )
        blocked["learning_consumption_mismatch"] = {
            "expected_fields": sorted(expected_profile_fields),
            "actual_fields": sorted(actual_profile_fields),
            "missing_fields": missing_profile_fields,
        }
        return blocked
    total = len(slides)
    request_slides: List[Dict[str, Any]] = []
    attribution_receipts: List[Dict[str, Any]] = []
    rendered_asset_ids: Dict[str, List[str]] = {}
    rendered_reference_ids: set[str] = set()
    for index, raw in enumerate(slides, start=1):
        if not isinstance(raw, Mapping):
            return _blocked("slide_invalid")
        page = int(raw.get("page") or index)
        body = _text(raw.get("body"))
        headline = _text(raw.get("headline")) or title
        if not body or not headline:
            return _blocked("slide_copy_missing")
        is_cover = index == 1
        visual_spec = _visual_spec(raw.get("visual_spec"))
        source_candidate = visual_spec.get("source_media_candidate")
        source_candidate = source_candidate if isinstance(source_candidate, Mapping) else {}
        attribution_candidate: Mapping[str, Any] = source_candidate
        source_path = Path(_text(source_candidate.get("local_path"))).resolve() if _text(
            source_candidate.get("local_path")
        ) else None
        source_editorial = (
            source_path is not None
            and source_path.is_file()
            and _text(source_candidate.get("rights_status")) in {
                "source_editorial_usable",
                "public_domain",
                "open_license",
            }
            and source_candidate.get("topic_relevant") is True
            and source_candidate.get("attribution_required") is True
            and source_candidate.get("publish_authorized") is False
        )
        slide_asset_path = source_path if source_editorial else asset_path
        rendered_asset_id = (
            _text(source_candidate.get("asset_id"))
            if source_editorial
            else f"{candidate_id}-owned-editorial-1"
        )
        slide_image_uri, slide_source_width, slide_source_height = _image_data_uri(
            slide_asset_path,
            fit_cover=not source_editorial,
            target_size=target_size,
        )
        reference_tree = None
        reference_receipt = {}
        if reference_v2_required and page in reference_v2_by_page:
            reference_result = reference_v2_by_page.get(page, {})
            visual_gate_receipt = reference_result.get(
                "geometry_visual_gate_receipt"
            )
            adapted_slide = reference_result.get("adapted_slide")
            adapted_slide = (
                adapted_slide if isinstance(adapted_slide, Mapping) else {}
            )
            adapted_slide = _rebind_reference_copy(adapted_slide, raw)
            selection = reference_result.get("selection")
            selection = selection if isinstance(selection, Mapping) else {}
            reference_geometry_hash = (
                _text(reference_result.get("geometry_hash"))
                or _text(adapted_slide.get("geometry_hash"))
            )
            if not is_visual_gate_pass_receipt(
                visual_gate_receipt,
                reference_id=_text(
                    selection.get("primary_reference_id")
                ),
                geometry_hash=reference_geometry_hash,
            ):
                blocked = _blocked(
                    "reference_visual_gate_pass_receipt_missing"
                )
                blocked["reference_v2"] = dict(reference_result)
                return blocked
            reference_media_bindings = adapted_slide.get("media_bindings")
            reference_media_bindings = (
                reference_media_bindings
                if isinstance(reference_media_bindings, list)
                else []
            )
            for media_binding in reference_media_bindings:
                if not isinstance(media_binding, Mapping):
                    continue
                bound_asset = media_binding.get("asset")
                if not isinstance(bound_asset, Mapping):
                    continue
                bound_path_text = _text(
                    bound_asset.get("local_path") or bound_asset.get("path")
                )
                bound_rights = _text(bound_asset.get("rights_status")).lower()
                bound_source_url = _text(bound_asset.get("source_url"))
                if not bound_path_text and not bound_rights and not bound_source_url:
                    continue
                bound_path = Path(bound_path_text).resolve() if bound_path_text else None
                if (
                    bound_path is None
                    or not bound_path.is_file()
                    or not bound_source_url
                    or bound_rights
                    not in {
                        "owned",
                        "licensed",
                        "public_domain",
                        "official_reuse_allowed",
                        "user_supplied_with_permission",
                        "permission_granted",
                        "source_editorial_usable",
                        "source_attributed_review_only",
                        "open_license",
                    }
                    or bound_asset.get("publish_authorized") is True
                ):
                    blocked = _blocked("reference_v2_media_not_renderable")
                    blocked["reference_v2"] = dict(reference_result)
                    return blocked
                slide_image_uri, slide_source_width, slide_source_height = (
                    _image_data_uri(bound_path, target_size=target_size)
                )
                attribution_candidate = bound_asset
                rendered_asset_id = _text(bound_asset.get("asset_id"))
                break
            reference_tree_result = build_reference_v2_satori_tree(
                adapted_slide,
                fallback_image_uri=slide_image_uri,
                page=page,
            )
            if reference_tree_result.get("status") != "ready":
                blocked = _blocked(
                    reference_tree_result.get("reason_code")
                    or "reference_v2_tree_not_ready"
                )
                blocked["reference_v2"] = dict(reference_result)
                return blocked
            reference_tree = reference_tree_result["tree"]
            reference_receipt = reference_tree_result.get(
                "reference_consumption_receipt", {}
            )
            rendered_reference_id = _text(
                reference_receipt.get("reference_id")
                or reference_receipt.get("primary_reference_id")
            )
            if rendered_reference_id:
                rendered_reference_ids.add(rendered_reference_id)
        selected_asset_id = selected_asset_by_page.get(page, "")
        if selected_asset_id and selected_asset_id != rendered_asset_id:
            blocked = _blocked("selected_asset_render_mismatch")
            blocked["asset_mismatch"] = {
                "page": page,
                "selected_asset_id": selected_asset_id,
                "rendered_asset_id": rendered_asset_id,
            }
            return blocked
        rendered_asset_ids[str(page)] = (
            [rendered_asset_id]
            if rendered_asset_id and (is_cover or source_editorial)
            else []
        )
        request_slides.append(
            {
                "page": page,
                "width": profile["width"],
                "height": profile["height"],
                "tree": _strip_visible_source_labels(
                    reference_tree or (
                        _cover_tree(
                            headline,
                            body,
                            slide_image_uri,
                            account,
                            design,
                            render_style,
                        )
                        if is_cover
                        else _detail_tree(
                            page,
                            total,
                            headline,
                            body,
                            account,
                            visual_spec,
                            design,
                            supplied_design,
                            slide_image_uri if source_editorial else "",
                            slide_source_width if source_editorial else 0,
                            slide_source_height if source_editorial else 0,
                            "",
                            render_style,
                        )
                    ),
                    labels=(
                        design["source_label"],
                        _source_attribution_label(attribution_candidate),
                    ),
                ),
                "media_classification": (
                    "source_editorial" if source_editorial else "generated_editorial"
                ),
                "display_label": (
                    design["source_label"]
                    if source_editorial
                    else "AI 연출 이미지" if is_cover else "편집 디자인"
                ),
                "learned_design": dict(learned_design),
                "learning_consumption": {
                    "consumed_fields": list(learning_receipt["consumed_fields"]),
                    "ignored_fields": list(learning_receipt["ignored_fields"]),
                },
                "reference_v2_consumption_receipt": copy.deepcopy(
                    reference_receipt
                ),
                "geometry_visual_gate_receipt": copy.deepcopy(
                    visual_gate_receipt
                    if reference_v2_required
                    and page in reference_v2_by_page
                    else {}
                ),
                "assets": (
                    [
                        {
                            "asset_id": (
                                rendered_asset_id
                            ),
                            "source_width": slide_source_width,
                            "source_height": slide_source_height,
                            "target_bounds": {
                                "x": 0,
                                "y": 0,
                                "width": profile["width"],
                                "height": profile["height"],
                            },
                            "focus_bounds": {"x": 0.36, "y": 0.14, "width": 0.6, "height": 0.72},
                            "crop_strategy": "contain",
                            "protected_subjects": (
                                [
                                    {
                                        "kind": "outfit",
                                        "source_bounds": {"x": 0.36, "y": 0.14, "width": 0.6, "height": 0.72},
                                        "canvas_bounds": {"x": 560, "y": 220, "width": 390, "height": 390},
                                    }
                                ]
                                if account == "C"
                                else []
                            ),
                        }
                    ]
                    if is_cover or source_editorial
                    else []
                ),
            }
        )
        attribution_label = _source_attribution_label(attribution_candidate)
        attribution_receipts.append(
            {
                "page": page,
                "asset_id": _text(attribution_candidate.get("asset_id")),
                "source_url": _text(attribution_candidate.get("source_url")),
                "license": _text(attribution_candidate.get("license")),
                "license_name": _text(
                    attribution_candidate.get("license_name")
                    or attribution_candidate.get("license")
                ),
                "attribution": _text(attribution_candidate.get("attribution")),
                "attribution_text": _text(
                    attribution_candidate.get("attribution_text")
                    or attribution_candidate.get("attribution")
                ),
                "attribution_required": (
                    attribution_candidate.get("attribution_required") is True
                ),
                "display_label": attribution_label,
                "rendered_in_footer": False,
                "delivery": "feed_caption_or_internal_source_record",
            }
        )

    expected_reference_ids = {
        _text(reference_id)
        for reference_id in upstream_consumption.get(
            "reference_consumed_ids", []
        )
        if _text(reference_id)
    }
    missing_reference_ids = sorted(
        expected_reference_ids - rendered_reference_ids
    )
    if missing_reference_ids:
        blocked = _blocked("reference_render_consumption_mismatch")
        blocked["reference_consumption_mismatch"] = {
            "expected_reference_ids": sorted(expected_reference_ids),
            "rendered_reference_ids": sorted(rendered_reference_ids),
            "missing_reference_ids": missing_reference_ids,
        }
        return blocked
    final_consumption_receipt = {
        **upstream_consumption,
        "status": "satori_render_contract_consumption_verified",
        "actual_profile_consumed_fields": sorted(actual_profile_fields),
        "rendered_reference_ids": sorted(rendered_reference_ids),
        "rendered_asset_ids": copy.deepcopy(rendered_asset_ids),
        "render_execution_claimed": False,
    }

    hashes = authorization.get("local_media_receipt_hashes")
    candidate_hashes = hashes.get(candidate_id) if isinstance(hashes, Mapping) else None
    if not isinstance(candidate_hashes, list) or not candidate_hashes:
        return _blocked("local_media_receipt_hashes_missing")
    output_root = (
        Path(_text(authorization.get("output_root")))
        / _safe_path_segment(candidate_id)
    )
    request = {
        "schema_version": SCHEMA_VERSION,
        "render_request_id": f"request-{candidate_id}-{authorization.get('authorization_id')}",
        "candidate_id": candidate_id,
        "mode": _text(authorization.get("mode")) or "representative",
        "output_set_id": _text(authorization.get("authorization_id")),
        "input_sha256": _text(authorization.get("input_sha256")),
        "output_root": str(output_root),
        "local_media_receipt_hashes": list(candidate_hashes),
        "canvas_profile": profile,
        "learned_design": dict(learned_design),
        "learning_consumption_receipt": learning_receipt,
        "reference_v2_required": reference_v2_required,
        "reference_v2": copy.deepcopy(dict(reference_v2)),
        "attribution_receipt": copy.deepcopy(attribution_receipts),
        "asset_selection_receipts": copy.deepcopy(selection_receipts),
        "rendered_asset_ids": copy.deepcopy(rendered_asset_ids),
        "learning_pipeline_consumption_receipt": (
            final_consumption_receipt
        ),
        "slides": request_slides,
    }
    if package_path is not None:
        request["package_path"] = str(Path(package_path).resolve())
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ready",
        "reason_code": "source_bound_satori_request_built",
        "learning_consumption_receipt": learning_receipt,
        "attribution_receipt": attribution_receipts,
        "asset_selection_receipts": copy.deepcopy(selection_receipts),
        "rendered_asset_ids": copy.deepcopy(rendered_asset_ids),
        "learning_pipeline_consumption_receipt": (
            final_consumption_receipt
        ),
        "render_request": request,
    }


__all__ = ["build_production_render_request", "SCHEMA_VERSION", "PROFILE_ID", "MAX_SLIDES"]
