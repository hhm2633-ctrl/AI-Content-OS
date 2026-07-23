"""Build a bounded Satori render request from an approved CardNews package."""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping
from urllib.parse import urlparse

from PIL import Image, ImageOps

from modules.tool_adapters.cardnews_renderer_runtime import CANVAS_PROFILES


SCHEMA_VERSION = "cardnews_renderer_request_v1"
PROFILE_ID = "instagram_portrait_4_5"
MAX_SLIDES = 20
VISUAL_TYPES = {
    "cover_editorial",
    "delta_comparison",
    "flow_summary",
    "evidence_card",
    "cta_prompt",
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


def _source_display_label(value: Any) -> str:
    host = (urlparse(_text(value)).hostname or "").casefold().removeprefix("www.")
    labels = {
        "news1.kr": "SOURCE · NEWS1",
        "youtube.com": "SOURCE · YOUTUBE",
        "youtu.be": "SOURCE · YOUTUBE",
        "commons.wikimedia.org": "SOURCE · WIKIMEDIA COMMONS",
    }
    return labels.get(host, f"SOURCE · {host.upper()}" if host else "SOURCE RECORDED")


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


def _image_data_uri(path: Path, *, fit_cover: bool = True) -> tuple[str, int, int]:
    with Image.open(path) as source:
        source = ImageOps.exif_transpose(source).convert("RGB")
        source_width, source_height = source.size
        prepared = (
            ImageOps.fit(
                source,
                (1080, 1350),
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


def _design_system(account: str, supplied: Any) -> Dict[str, str]:
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


def _visual_spec(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    visual_type = _text(value.get("visual_type"))
    return dict(value) if visual_type in VISUAL_TYPES else {}


def _cover_tree(
    title: str,
    body: str,
    image_uri: str,
    account: str,
    design: Mapping[str, str],
) -> Dict[str, Any]:
    title_size = "48px" if len(title) > 42 else "58px"
    return _node(
        "div",
        style={
            "width": "1080px",
            "height": "1350px",
            "display": "flex",
            "position": "relative",
            "overflow": "hidden",
            "backgroundColor": design["background"],
            "fontFamily": "Pretendard",
        },
        children=[
            _node(
                "img",
                src=image_uri,
                style={
                    "position": "absolute",
                    "inset": "0px",
                    "width": "1080px",
                    "height": "1350px",
                    "objectFit": "cover",
                },
            ),
            _node(
                "div",
                style={
                    "position": "absolute",
                    "left": "54px",
                    "top": "54px",
                    "bottom": "54px",
                    "width": "470px",
                    "display": "flex",
                    "flexDirection": "column",
                    "justifyContent": "space-between",
                    "padding": "52px",
                    "backgroundColor": design["panel"],
                    "borderRadius": "28px",
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
                            "fontWeight": 800,
                            "lineHeight": 1.18,
                            "letterSpacing": "-2.6px",
                            "color": design["ink"],
                            "wordBreak": "keep-all",
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
                            _node("div", children=design["source_label"]),
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
) -> Dict[str, Any]:
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
                "fontSize": "60px",
                "fontWeight": 800,
                "lineHeight": 1.18,
                "letterSpacing": "-2.4px",
                "wordBreak": "keep-all",
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
                    "fontSize": "31px",
                    "fontWeight": 500,
                    "lineHeight": 1.62,
                    "letterSpacing": "-0.7px",
                    "wordBreak": "keep-all",
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
            else 220 if copy_density > 180 else 300
        )
        media_box_height_px = f"{media_box_height}px"
        media_fit = (
            "cover"
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
            "height": "1350px",
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "space-between",
            "padding": "86px",
            "backgroundColor": background,
            "color": ink,
            "fontFamily": "Pretendard",
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
                style={"display": "flex", "flexDirection": "column", "gap": "44px"},
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
                    _node("div", children=source_label or design["source_label"]),
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
    image_uri, source_width, source_height = _image_data_uri(asset_path)
    title = _text(candidate.get("title"))
    supplied_design = isinstance(package.get("design_system"), Mapping)
    design = _design_system(account, package.get("design_system"))
    profile = dict(CANVAS_PROFILES[PROFILE_ID])
    total = len(slides)
    request_slides: List[Dict[str, Any]] = []
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
        source_path = Path(_text(source_candidate.get("local_path"))).resolve() if _text(
            source_candidate.get("local_path")
        ) else None
        source_editorial = (
            not is_cover
            and
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
        slide_image_uri, slide_source_width, slide_source_height = _image_data_uri(
            slide_asset_path,
            fit_cover=not source_editorial,
        )
        request_slides.append(
            {
                "page": page,
                "width": profile["width"],
                "height": profile["height"],
                "tree": (
                    _cover_tree(headline, body, slide_image_uri, account, design)
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
                        (
                            _source_display_label(source_candidate.get("source_url"))
                            if source_editorial
                            else ""
                        ),
                    )
                ),
                "media_classification": (
                    "source_editorial" if source_editorial else "generated_editorial"
                ),
                "display_label": (
                    design["source_label"]
                    if source_editorial
                    else "AI 연출 이미지" if is_cover else "편집 디자인"
                ),
                "assets": (
                    [
                        {
                            "asset_id": (
                                _text(source_candidate.get("asset_id"))
                                if source_editorial
                                else f"{candidate_id}-owned-editorial-1"
                            ),
                            "source_width": slide_source_width,
                            "source_height": slide_source_height,
                            "target_bounds": {"x": 0, "y": 0, "width": 1080, "height": 1350},
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
        "slides": request_slides,
    }
    if package_path is not None:
        request["package_path"] = str(Path(package_path).resolve())
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ready",
        "reason_code": "source_bound_satori_request_built",
        "render_request": request,
    }


__all__ = ["build_production_render_request", "SCHEMA_VERSION", "PROFILE_ID", "MAX_SLIDES"]
