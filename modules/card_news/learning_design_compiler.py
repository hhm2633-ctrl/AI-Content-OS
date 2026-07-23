"""Compile learned CardNews guidance into concrete production blueprints.

The compiler converts source-backed topic facts, variable slide roles, and
bound owner-learning guidance into slide copy, visual specifications, an
account design system, and a separate feed caption. It performs no rendering,
network access, publishing, or pattern promotion.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlparse


SCHEMA_VERSION = "learning_driven_cardnews_blueprint_v1"
ACCOUNT_DESIGN_SYSTEMS = {
    "account_a_news_incident": {
        "account": "A",
        "account_label": "NOW BRIEF",
        "cover_kicker": "MONEY / DATA BRIEF",
        "detail_kicker": "MARKET SHIFT",
        "footer_label": "NOW BRIEF / NEWS",
        "palette": {
            "background": "#eef3e8",
            "ink": "#17241c",
            "accent": "#a5c52f",
            "secondary_accent": "#4594c2",
            "muted": "#68756b",
            "panel": "#f5f8f0",
        },
    },
    "account_b_issue_story": {
        "account": "B",
        "account_label": "DOPAMINE NOTE",
        "cover_kicker": "STORY / ISSUE NOTE",
        "detail_kicker": "STORY TURN",
        "footer_label": "DOPAMINE NOTE / STORY",
        "palette": {
            "background": "#fff1e1",
            "ink": "#36272b",
            "accent": "#ed6f91",
            "secondary_accent": "#8d79bd",
            "muted": "#896b73",
            "panel": "#fff8eb",
        },
    },
    "account_c_beauty_fashion": {
        "account": "C",
        "account_label": "STYLE FILE",
        "cover_kicker": "STYLE / BEAUTY FILE",
        "detail_kicker": "STYLE DETAIL",
        "footer_label": "STYLE FILE / EDIT",
        "palette": {
            "background": "#f2efe8",
            "ink": "#242722",
            "accent": "#c18e62",
            "secondary_accent": "#7f9c8b",
            "muted": "#74786f",
            "panel": "#faf8f2",
        },
    },
}

_METRIC_RE = re.compile(
    r"(?P<label>[0-9A-Za-z가-힣·]+)\s+"
    r"(?P<value>[0-9]+(?:\.[0-9]+)?%p)\s*(?P<direction>[↑↓])"
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _source_urls(topic: Mapping[str, Any]) -> List[str]:
    urls: List[str] = []
    for value in (topic.get("link"), topic.get("url")):
        text = _text(value)
        if text and text not in urls:
            urls.append(text)
    for reference in topic.get("source_refs", []):
        if not isinstance(reference, Mapping):
            continue
        text = _text(reference.get("link") or reference.get("url"))
        if text and text not in urls:
            urls.append(text)
    for body in topic.get("article_bodies", []):
        if not isinstance(body, Mapping):
            continue
        text = _text(body.get("url"))
        if text and text not in urls:
            urls.append(text)
    for related in topic.get("related_sources", []):
        if not isinstance(related, Mapping):
            continue
        text = _text(related.get("url"))
        if text and text not in urls:
            urls.append(text)
    return urls


def _source_label(urls: List[str]) -> str:
    if not urls:
        return "SOURCE RECORDED IN CAPTION"
    host = (urlparse(urls[0]).hostname or "").lower()
    host = host.removeprefix("www.")
    labels = {
        "news1.kr": "NEWS1",
        "yna.co.kr": "YONHAP NEWS",
        "newsis.com": "NEWSIS",
        "hankyung.com": "HANKYUNG",
    }
    return f"SOURCE · {labels.get(host, host.upper() or 'ORIGINAL REPORT')}"


def _source_media_candidates(topic: Mapping[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for position, raw in enumerate(topic.get("assets", []), start=1):
        if not isinstance(raw, Mapping):
            continue
        locator = _text(raw.get("remote_url") or raw.get("url"))
        if (
            not locator
            or raw.get("usable_in_production") is not True
            or raw.get("reference_only") is True
            or _text(raw.get("rights_status")) not in {
                "source_editorial_usable",
                "public_domain",
                "open_license",
            }
            or raw.get("topic_relevant") is not True
        ):
            continue
        candidates.append(
            {
                "asset_id": _text(raw.get("asset_id")) or f"source-editorial-{position}",
                "media_type": _text(raw.get("type")) or "news_image",
                "remote_url": locator,
                "source_url": _text(raw.get("source_url")),
                "title": _text(raw.get("title")),
                "description": _text(raw.get("description")),
                "channel": _text(raw.get("channel")),
                "publisher": _text(raw.get("publisher")),
                "source_api": _text(
                    raw.get("source_api") or raw.get("source_provider")
                ),
                "rights_status": _text(raw.get("rights_status")),
                "license_name": _text(raw.get("license_name")),
                "license_filter": _text(raw.get("license_filter")),
                "attribution_text": _text(raw.get("attribution_text")),
                "usage_scope": "attributed_news_editorial_excerpt",
                "topic_relevant": True,
                "attribution_required": True,
                "manual_visual_review_required": True,
                "publish_authorized": False,
            }
        )
    return candidates


def _cover_headline(title: str) -> str:
    clean = re.sub(r"\[[^\]]+\]\s*[①-⑳0-9]*\s*$", "", title).strip()
    clean = re.sub(r"\s+", " ", clean)
    if "…" in clean:
        left, right = clean.split("…", 1)
        if len(left) <= 20:
            clean = left
    return clean[:34].rstrip()


def _first_clause(value: str) -> str:
    clause = re.split(r"…|(?<!\d)[.!?。！？](?!\d)", value, maxsplit=1)[0]
    return clause.strip()


def _metrics(value: str) -> List[Dict[str, str]]:
    return [
        {
            "label": match.group("label"),
            "value": match.group("value"),
            "direction": match.group("direction"),
        }
        for match in _METRIC_RE.finditer(value)
    ]


def _headline_for_point(point: str) -> str:
    if "예·적금" in point and len(_metrics(point)) >= 2:
        return "예·적금 비중은 줄었다"
    if "가입 의향" in point and any(
        item["direction"] == "↑" for item in _metrics(point)
    ):
        return "투자 의향은 늘었다"
    clause = _first_clause(point)
    return clause[:32].rstrip()


def _question(account_id: str, title: str) -> str:
    if account_id == "account_a_news_incident" and any(
        token in title for token in ("예금", "주식", "ETF", "투자")
    ):
        return "여러분이라면 자산 비중을 어떻게 나눌 건가요?"
    if account_id == "account_b_issue_story":
        return "여러분은 이 상황을 어떻게 보나요?"
    if account_id == "account_c_beauty_fashion":
        return "여러분이라면 어떤 선택을 할 건가요?"
    return "이 변화, 여러분은 어떻게 보나요?"


def _visual_spec(
    point: str,
    *,
    is_conclusion: bool,
    question: str,
) -> Dict[str, Any]:
    metrics = _metrics(point)
    if is_conclusion:
        return {
            "visual_type": "cta_prompt",
            "metrics": metrics,
            "question": question,
            "source_fact": point,
        }
    if len(metrics) >= 2:
        return {
            "visual_type": "delta_comparison",
            "metrics": metrics,
            "source_fact": point,
        }
    if metrics and any(
        token in point for token in ("이동", "머니무브", "주식", "ETF", "가입 의향")
    ):
        return {
            "visual_type": "flow_summary",
            "from_label": "예·적금",
            "to_label": "국내주식·ETF",
            "delta_label": " ".join(
                f"{item['label']} {item['value']}{item['direction']}"
                for item in metrics
            ),
            "source_fact": point,
        }
    return {
        "visual_type": "evidence_card",
        "metrics": metrics,
        "source_fact": point,
    }


def _is_present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _visual_guidance_sources(
    plan: Mapping[str, Any],
    pattern_reference: Optional[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []

    def add(value: Any, *, visual_role: bool = False) -> None:
        if not isinstance(value, Mapping):
            return
        copied = copy.deepcopy(dict(value))
        if visual_role:
            copied["_visual_role"] = True
        sources.append(copied)

    learning_guidance = plan.get("learning_guidance")
    if isinstance(learning_guidance, Mapping):
        add(learning_guidance.get("visual_direction"), visual_role=True)
    for slide in plan.get("slides", []):
        if not isinstance(slide, Mapping):
            continue
        for guidance in slide.get("learning_guidance", []):
            if not isinstance(guidance, Mapping):
                continue
            add(
                guidance,
                visual_role=_text(guidance.get("guidance_role"))
                == "visual_direction",
            )

    reference = pattern_reference if isinstance(pattern_reference, Mapping) else {}
    add(reference.get("visual_direction"), visual_role=True)
    for container_name in ("role_guidance", "roles", "learning_guidance"):
        container = reference.get(container_name)
        if isinstance(container, Mapping):
            add(container.get("visual_direction"), visual_role=True)
    return sources


def _apply_learned_design_guidance(
    design: Mapping[str, Any],
    plan: Mapping[str, Any],
    pattern_reference: Optional[Mapping[str, Any]],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    design_system = copy.deepcopy(dict(design))
    sources = _visual_guidance_sources(plan, pattern_reference)
    consumed: Dict[str, Any] = {}
    palette_updates: Dict[str, str] = {}

    for source in sources:
        for field in (
            "visual_direction",
            "emotion",
            "mood",
            "palette_intent",
            "color_palette",
        ):
            value = source.get(field)
            if _is_present(value):
                consumed[field] = copy.deepcopy(value)
        palette = source.get("palette")
        if isinstance(palette, Mapping):
            palette_updates.update(
                {
                    str(key): value
                    for key, value in palette.items()
                    if isinstance(value, str) and value.strip()
                }
            )
            if palette_updates:
                consumed["palette"] = copy.deepcopy(palette_updates)
        elif _is_present(palette):
            consumed["palette_intent"] = copy.deepcopy(palette)
        if source.get("_visual_role") and _is_present(
            source.get("recommended_action")
        ):
            consumed["visual_direction"] = copy.deepcopy(
                source["recommended_action"]
            )

    if palette_updates:
        design_system["palette"] = {
            **copy.deepcopy(design_system.get("palette", {})),
            **palette_updates,
        }
    if consumed:
        design_system["learned_visual_guidance"] = copy.deepcopy(consumed)
        design_system["theme_priority"] = "learned_guidance_over_account_default"
        if "palette_intent" in consumed:
            design_system["palette_intent"] = copy.deepcopy(
                consumed["palette_intent"]
            )
        elif "palette" in consumed:
            design_system["palette_intent"] = {
                "source": "learned_visual_guidance",
                "overrides": sorted(consumed["palette"]),
            }

    return design_system, {
        "available": bool(sources),
        "consumed": bool(consumed),
        "consumed_fields": sorted(consumed),
        "status": "consumed" if consumed else "not_consumed",
    }


def _visual_relevance_labels(planned: Mapping[str, Any]) -> tuple[Any, str]:
    direct = planned.get("visual_relevance_labels")
    if _is_present(direct):
        return copy.deepcopy(direct), "supplied"
    for guidance in planned.get("learning_guidance", []):
        if not isinstance(guidance, Mapping):
            continue
        labels = guidance.get("visual_relevance_labels")
        if _is_present(labels):
            return copy.deepcopy(labels), "supplied"
    return None, "missing"


def _attach_visual_relevance_labels(
    visual_spec: Dict[str, Any],
    planned: Mapping[str, Any],
) -> None:
    labels, status = _visual_relevance_labels(planned)
    visual_spec["visual_relevance_labels_status"] = status
    if status == "supplied":
        visual_spec["visual_relevance_labels"] = labels


def compile_learning_driven_blueprint(
    topic: Any,
    plan: Any,
    pattern_reference: Optional[Mapping[str, Any]] = None,
    production_profile: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(topic, Mapping) or not isinstance(plan, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "reason_code": "topic_and_plan_required",
            "slides": [],
        }
    account_id = _text(topic.get("account_id"))
    design = ACCOUNT_DESIGN_SYSTEMS.get(account_id)
    planned_slides = plan.get("slides")
    if (
        design is None
        or not isinstance(planned_slides, list)
        or not planned_slides
        or not _text(topic.get("candidate_id"))
    ):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "reason_code": "account_or_planned_slides_unavailable",
            "slides": [],
        }

    points = [
        _text(value)
        for value in topic.get("key_points", [])
        if _text(value)
    ]
    if not points:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "reason_code": "source_backed_key_points_required",
            "slides": [],
        }
    title = _text(topic.get("title"))
    question = _question(account_id, title)
    urls = _source_urls(topic)
    source_label = _source_label(urls)
    source_media = _source_media_candidates(topic)
    slides: List[Dict[str, Any]] = []
    point_index = 0
    total = len(planned_slides)
    for index, planned in enumerate(planned_slides, start=1):
        if not isinstance(planned, Mapping):
            continue
        semantic_role = _text(planned.get("semantic_role"))
        if index == 1:
            cover_spec: Dict[str, Any] = {
                "visual_type": "cover_editorial",
                "semantic_prompt": (
                    f"{title}; source-backed editorial metaphor; "
                    "account-specific first screen; no unrelated person"
                ),
            }
            _attach_visual_relevance_labels(cover_spec, planned)
            if source_media:
                cover_spec["source_media_candidate"] = copy.deepcopy(source_media[0])
                cover_spec["preferred_media_mode"] = "source_editorial"
            slides.append(
                {
                    "page": index,
                    "role": "hook",
                    "semantic_role": "cover",
                    "headline": _cover_headline(title),
                    "body": _first_clause(points[0]),
                    "visual_spec": cover_spec,
                }
            )
            continue

        is_conclusion = index == total or semantic_role in {
            "conclusion",
            "debate_cta",
        }
        point = points[min(point_index, len(points) - 1)]
        point_index += 1
        body = point
        if is_conclusion:
            body = f"{point} {question}".strip()
        visual_spec = _visual_spec(
            point,
            is_conclusion=is_conclusion,
            question=question,
        )
        _attach_visual_relevance_labels(visual_spec, planned)
        if source_media:
            visual_spec["source_media_candidate"] = copy.deepcopy(
                source_media[(index - 1) % len(source_media)]
            )
            visual_spec["preferred_media_mode"] = "source_editorial"
        slides.append(
            {
                "page": index,
                "role": "conclusion" if is_conclusion else semantic_role or "evidence",
                "semantic_role": "conclusion" if is_conclusion else semantic_role or "evidence",
                "headline": _headline_for_point(point),
                "body": body,
                "visual_spec": visual_spec,
            }
        )

    pattern_ids = sorted(
        {
            _text(value.get("pattern_id"))
            for value in plan.get("learning_guidance", {}).values()
            if isinstance(value, Mapping) and _text(value.get("pattern_id"))
        }
    )
    caption_lines = [title, "", *[f"• {point}" for point in points], "", question]
    if urls:
        caption_lines.extend(["", *[f"출처: {url}" for url in urls]])
    design_system, design_consumption = _apply_learned_design_guidance(
        design,
        plan,
        pattern_reference,
    )
    compiled_profile = (
        production_profile.get("production_profile")
        if isinstance(production_profile, Mapping)
        and isinstance(production_profile.get("production_profile"), Mapping)
        else {}
    )
    compiled_profile = copy.deepcopy(dict(compiled_profile))
    supported_layouts = {
        "editorial_split",
        "split",
        "split_screen",
        "centered_panel",
        "centered",
        "magazine_center",
        "full_bleed",
        "full_bleed_editorial",
    }
    supported_grammar = {"contain", "cover", "full_bleed", "source_editorial"}
    supported_tones = {"urgent_warm", "warning", "calm", "bright", "romantic"}
    executable_profile: Dict[str, Any] = {}
    ignored_profile_fields: List[str] = []
    for field, value in compiled_profile.items():
        accepted = False
        if field in {"palette", "typography", "composition"}:
            accepted = isinstance(value, Mapping) and bool(value)
        elif field == "layout_family":
            accepted = _text(value).casefold() in supported_layouts
        elif field == "image_grammar":
            values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
            accepted = any(_text(item).casefold() in supported_grammar for item in values)
        elif field == "emotional_tone":
            accepted = _text(value).casefold() in supported_tones
        elif field == "first_screen":
            text = _text(value).casefold()
            accepted = any(
                token in text
                for token in (
                    "left",
                    "right",
                    "center",
                    "full",
                    "왼쪽",
                    "오른쪽",
                    "중앙",
                    "전면",
                )
            )
        elif field == "text_density":
            accepted = bool(_text(value) or isinstance(value, Mapping))
        if accepted:
            executable_profile[field] = copy.deepcopy(value)
        else:
            ignored_profile_fields.append(field)
    if executable_profile:
        design_system["learned_profile"] = executable_profile
        design_system["theme_priority"] = (
            "learned_guidance_over_account_default"
        )
    design_system["source_label"] = source_label
    learning_claimed = bool(
        plan.get("learning_guidance_consumed")
        or plan.get("learning_guidance")
        or pattern_reference
        or production_profile
    )
    status = "ready"
    reason_code = "source_facts_and_learning_guidance_compiled"
    profile_consumed = bool(executable_profile)
    if learning_claimed and not (
        design_consumption["consumed"] or profile_consumed
    ):
        status = "design_guidance_not_consumed"
        reason_code = "learning_guidance_claimed_without_design_consumption"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reason_code": reason_code,
        "candidate_id": _text(topic.get("candidate_id")),
        "account_id": account_id,
        "account": design["account"],
        "category": _text(topic.get("primary_category")),
        "title": title,
        "slide_count": len(slides),
        "design_system": design_system,
        "slides": slides,
        "feed_caption": "\n".join(caption_lines),
        "source_refs": urls,
        "source_media_candidates": source_media,
        "learning_trace": {
            "pattern_ids": pattern_ids,
            "pattern_reference": copy.deepcopy(dict(pattern_reference or {})),
            "reference_guidance_only": True,
            "measured_performance_claimed": False,
            "design_guidance": design_consumption,
            "production_profile": {
                "profile_id": (
                    production_profile.get("profile_id")
                    if isinstance(production_profile, Mapping)
                    else None
                ),
                "status": (
                    production_profile.get("status")
                    if isinstance(production_profile, Mapping)
                    else "not_supplied"
                ),
                "consumed": profile_consumed,
                "consumed_fields": sorted(executable_profile),
                "ignored_fields": sorted(ignored_profile_fields),
                "role_top_k": copy.deepcopy(
                    production_profile.get("role_top_k", {})
                    if isinstance(production_profile, Mapping)
                    else {}
                ),
                "provenance": copy.deepcopy(
                    production_profile.get(
                        "production_profile_provenance",
                        {},
                    )
                    if isinstance(production_profile, Mapping)
                    else {}
                ),
                "reference_candidates": copy.deepcopy(
                    production_profile.get("reference_candidates", [])
                    if isinstance(production_profile, Mapping)
                    else []
                ),
                "approved_reference_specimen_candidates": copy.deepcopy(
                    production_profile.get(
                        "approved_reference_specimen_candidates",
                        [],
                    )
                    if isinstance(production_profile, Mapping)
                    else []
                ),
                "reference_v2_selectable_candidates": copy.deepcopy(
                    production_profile.get(
                        "reference_v2_selectable_candidates",
                        [],
                    )
                    if isinstance(production_profile, Mapping)
                    else []
                ),
                "reference_candidate_receipt": copy.deepcopy(
                    production_profile.get("reference_candidate_receipt", {})
                    if isinstance(production_profile, Mapping)
                    else {}
                ),
            },
        },
        "render_executed": False,
        "publishing_executed": False,
    }


__all__ = [
    "SCHEMA_VERSION",
    "ACCOUNT_DESIGN_SYSTEMS",
    "compile_learning_driven_blueprint",
]
