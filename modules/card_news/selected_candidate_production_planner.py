"""Build a reviewable CardNews production plan from completed discovery data.

The planner is deliberately data-only.  It does not search, download, render,
publish, or call the protected WorkflowEngine.  Its job is to preserve the
owner-selected topic and discovered assets while deciding which production
roles are actually supported by the available material.
"""

from __future__ import annotations

import copy
from difflib import SequenceMatcher
import re
from typing import Any, Dict, List, Mapping, Sequence

from modules.card_news.canvas_contract import (
    DEFAULT_CARD_NEWS_PROFILE_ID,
    allowed_card_slide_count_label,
    is_allowed_card_slide_count,
)


SCHEMA_VERSION = "selected_candidate_production_plan_v1"
SUPPORTED_ACCOUNTS = {"A", "B", "C"}
COMPLETE_STATUSES = {"complete", "completed", "ready", "evidence_ready"}
BLOCKED_ASSET_STATUSES = {"blocked", "rejected", "invalid", "reference_only"}
EDITORIAL_CONTENT_TYPES = {"runway", "season_collection", "brand_editorial"}
EMOTION_ARC = ("관심", "불편함", "의심", "대립", "충격", "결심")
NEWS_BASIC_KEY_POINT_LIMIT = 5
NEWS_RICH_EVIDENCE_THRESHOLD = 3
NEWS_AGREEMENT_PATTERN = re.compile(
    r"협약|MOU|투자\s*양해각서|투자양해각서|양해각서|"
    r"투자\s*협정|투자협정|체결",
    re.IGNORECASE,
)
NEWS_TOKEN_SUFFIXES = (
    "으로",
    "에서",
    "에게",
    "까지",
    "부터",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "와",
    "과",
    "의",
    "에",
    "로",
    "도",
)


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

        raw_source_asset = (
            raw.get("raw_source_asset")
            if isinstance(raw.get("raw_source_asset"), Mapping)
            else {}
        )
        production_source_locator = ""
        if (
            raw_source_asset.get("usable_in_production") is True
            and raw_source_asset.get("reference_only") is not True
        ):
            production_source_locator = (
                _text(raw_source_asset.get("screenshot_path"))
                or _text(raw_source_asset.get("local_path"))
                or _text(raw_source_asset.get("path"))
            )
        locator = (
            production_source_locator
            or _text(raw.get("local_path"))
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
                "source_url": (
                    _text(raw.get("source_url"))
                    or _text(raw_source_asset.get("source_url"))
                ),
                "rights_status": (
                    "source_editorial_usable"
                    if production_source_locator
                    else _text(raw_source_asset.get("rights_status"))
                    or _text(raw.get("rights_status"))
                    or "unrecorded"
                ),
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


def _comment_display_excerpt(text: str, limit: int = 170) -> str:
    """Keep comment cards readable while retaining the full source separately."""

    normalized = " ".join(_text(text).split())
    if len(normalized) <= limit:
        return normalized
    boundary = max(
        normalized.rfind(marker, 0, limit + 1)
        for marker in (". ", "? ", "! ", "… ", "요. ", "다. ")
    )
    if boundary >= max(60, limit // 2):
        return normalized[: boundary + 1].rstrip()
    return normalized[:limit].rstrip() + "…"


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


def _news_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[가-힣A-Za-z0-9%]+", value.lower()):
        token = raw
        for suffix in NEWS_TOKEN_SUFFIXES:
            if len(token) > len(suffix) + 1 and token.endswith(suffix):
                token = token[: -len(suffix)]
                break
        if len(token) >= 2:
            tokens.add(token)
    return tokens


def _news_point_signals(value: str) -> set[str]:
    signals: set[str] = set()
    if re.search(r"\d|%|억|조|만\s*명|원", value):
        signals.add("number")
    if re.search(r"말했|밝혔|설명했|강조했|전했|언급했|발언|인터뷰", value):
        signals.add("statement")
    if re.search(r"대비|보다|증가|감소|상승|하락|차이|비교|전년|지난해", value):
        signals.add("comparison")
    if re.search(r"향후|앞으로|예정|계획|추진|후속|착수|완료|목표", value):
        signals.add("follow_up")
    if re.search(r"배경|이유|때문|계기|기존|그동안", value):
        signals.add("background")
    return signals


def _news_point_score(value: str) -> int:
    signals = _news_point_signals(value)
    return (
        1
        + (2 if "number" in signals else 0)
        + (3 if "statement" in signals else 0)
        + (3 if "comparison" in signals else 0)
        + (3 if "follow_up" in signals else 0)
        + (1 if "background" in signals else 0)
    )


def _simple_investment_agreement(title: str, points: Sequence[str]) -> bool:
    combined = " ".join([title, *points])
    title_has_investment_context = bool(
        re.search(r"투자|재투자|\d[\d,.]*\s*(?:억|조)\s*원", title)
    )
    points_have_investment_context = any(
        re.search(r"투자|재투자|\d[\d,.]*\s*(?:억|조)\s*원", point)
        for point in points
    )
    agreement_signal = any(
        NEWS_AGREEMENT_PATTERN.search(point)
        for point in points
    ) or bool(NEWS_AGREEMENT_PATTERN.search(title))
    if not (
        agreement_signal
        and (title_has_investment_context or points_have_investment_context)
    ):
        return False
    if re.search(
        r"여러\s*(?:기업|지역|협약)|복수\s*(?:기업|지역|협약)|"
        r"\d+\s*개\s*(?:기업|지역|협약)|각각\s*(?:투자|협약|체결)",
        combined,
    ):
        return False
    investment_amounts = {
        re.sub(r"\s+", "", value)
        for value in re.findall(
            r"\d[\d,.]*\s*(?:억|조)\s*원",
            combined,
        )
    }
    if len(investment_amounts) > 1:
        return False
    investor_subjects = {
        subject
        for subject in re.findall(
            r"([가-힣A-Za-z0-9·]{2,20})(?:은|는)"
            r"[^.!?]{0,80}?(?:재투자|투자)"
            r"[^.!?]{0,50}?(?:결정|계획|투입|진행|신설|증설)",
            combined,
        )
        if not subject.endswith(("시", "도", "군", "구"))
    }
    return len(investor_subjects) <= 1


def _agreement_priority(value: str) -> tuple[str, int]:
    if NEWS_AGREEMENT_PATTERN.search(value) or re.search(r"체결|맺었", value):
        return "agreement", 50 + _news_point_score(value)
    if re.search(r"고용|일자리|채용", value):
        return "employment", 40 + _news_point_score(value)
    if re.search(
        r"\d[\d,.]*\s*(?:억|조)\s*원|"
        r"\d{4}\s*년|기간|시설|공장|산업단지|증설|신설|투입",
        value,
    ):
        return "investment_detail", 45 + _news_point_score(value)
    if re.search(r"지원|인허가|행정|재정|약속|밝혔|말했|시장|도지사", value):
        return "support_statement", 35 + _news_point_score(value)
    if re.search(r"이유|배경|수요|공급망|입지|인프라|결정", value):
        return "reason_background", 30 + _news_point_score(value)
    return "other", _news_point_score(value)


def _select_simple_agreement_points(points: Sequence[str]) -> List[str]:
    selected_indexes: List[int] = []
    priority_groups = (
        "agreement",
        "investment_detail",
        "employment",
        "reason_background",
        "support_statement",
    )
    classified = [
        (index, *_agreement_priority(point))
        for index, point in enumerate(points)
    ]
    for group in priority_groups:
        candidates = [
            (score, len(points[index]), -index, index)
            for index, point_group, score in classified
            if point_group == group and index not in selected_indexes
        ]
        if candidates:
            selected_indexes.append(max(candidates)[-1])
    if len(selected_indexes) < NEWS_BASIC_KEY_POINT_LIMIT:
        remaining = [
            (_agreement_priority(points[index])[1], len(points[index]), -index, index)
            for index in range(len(points))
            if index not in selected_indexes
        ]
        for _, _, _, index in sorted(remaining, reverse=True):
            selected_indexes.append(index)
            if len(selected_indexes) == NEWS_BASIC_KEY_POINT_LIMIT:
                break
    return [points[index] for index in selected_indexes]


def _news_fact_markers(value: str) -> Dict[str, set[str]]:
    compact = value.lower()
    return {
        "numbers": set(
            re.findall(r"\d[\d,.]*(?:%|억|조|만|원|명|건|개)?", compact)
        ),
        "ordinals": set(
            re.findall(
                r"(?:첫|두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s*번째",
                compact,
            )
        ),
        "times": set(
            re.findall(
                r"(?:오늘|내일|이번\s*(?:달|주|분기|해)|"
                r"다음\s*(?:달|주|분기|해)|향후|앞으로|"
                r"\d{1,4}\s*(?:년|월|일|분기))",
                compact,
            )
        ),
        "actions": set(
            re.findall(
                r"(?:체결|투자|증설|착공|완공|고용|지원|심의|"
                r"점검|발표|시작|추진|확대|축소|인상|인하|"
                r"증가|감소|상승|하락|개선|협의)",
                compact,
            )
        ),
    }


def _meaningfully_repeats(left: str, right: str) -> bool:
    left_compact = re.sub(r"\W+", "", left.lower())
    right_compact = re.sub(r"\W+", "", right.lower())
    if not left_compact or not right_compact:
        return False
    if left_compact in right_compact or right_compact in left_compact:
        return min(len(left_compact), len(right_compact)) >= 8
    left_markers = _news_fact_markers(left)
    right_markers = _news_fact_markers(right)
    for marker_type in ("numbers", "ordinals", "times", "actions"):
        left_values = left_markers[marker_type]
        right_values = right_markers[marker_type]
        if left_values and right_values and left_values.isdisjoint(right_values):
            return False
    ratio = SequenceMatcher(None, left_compact, right_compact).ratio()
    left_tokens = _news_tokens(left)
    right_tokens = _news_tokens(right)
    union = left_tokens | right_tokens
    overlap = len(left_tokens & right_tokens) / len(union) if union else 0.0
    shared_fact_marker = any(
        left_markers[marker_type] & right_markers[marker_type]
        for marker_type in ("numbers", "times", "actions")
    )
    return (
        ratio >= 0.84
        or overlap >= 0.80
        or (shared_fact_marker and ratio >= 0.70 and overlap >= 0.62)
    )


def _consolidate_news_key_points(
    title: str,
    key_points: Sequence[str],
) -> List[str]:
    simple_agreement = _simple_investment_agreement(title, key_points)
    consolidated: List[str] = []
    for point in key_points:
        if _meaningfully_repeats(title, point):
            continue
        duplicate_index = next(
            (
                index
                for index, existing in enumerate(consolidated)
                if _meaningfully_repeats(existing, point)
            ),
            None,
        )
        if duplicate_index is None:
            consolidated.append(point)
            continue
        existing = consolidated[duplicate_index]
        if (_news_point_score(point), len(point)) > (
            _news_point_score(existing),
            len(existing),
        ):
            consolidated[duplicate_index] = point

    if simple_agreement:
        return _select_simple_agreement_points(consolidated)

    independent_evidence = [
        point
        for point in consolidated
        if _news_point_signals(point)
        & {"statement", "comparison", "follow_up"}
    ]
    independent_signal_types = set().union(
        *(
            _news_point_signals(point)
            & {"statement", "comparison", "follow_up"}
            for point in independent_evidence
        )
    ) if independent_evidence else set()
    evidence_signatures = {
        (
            tuple(sorted(_news_point_signals(point))),
            tuple(sorted(_news_fact_markers(point)["numbers"])),
            tuple(sorted(_news_fact_markers(point)["times"])),
            tuple(sorted(_news_fact_markers(point)["actions"])),
        )
        for point in independent_evidence
    }
    rich_evidence = (
        len(independent_evidence) >= NEWS_RICH_EVIDENCE_THRESHOLD
        and len(independent_signal_types) >= 2
    ) or (
        len(independent_evidence) >= 4
        and len(evidence_signatures) == len(independent_evidence)
    )
    limit = (
        19
        if rich_evidence
        else NEWS_BASIC_KEY_POINT_LIMIT
    )
    if len(consolidated) <= limit:
        return consolidated

    ranked_indexes = sorted(
        range(len(consolidated)),
        key=lambda index: (
            _news_point_score(consolidated[index]),
            len(consolidated[index]),
            -index,
        ),
        reverse=True,
    )[:limit]
    return [consolidated[index] for index in sorted(ranked_indexes)]


def _news_slides(
    title: str,
    assets: Sequence[Mapping[str, Any]],
    key_points: Sequence[str],
) -> List[Dict[str, Any]]:
    slides = [_cover(title, assets)]
    remaining_assets = list(assets[1:])
    closing_index = len(key_points) - 1
    closing_candidates = [
        index
        for index, point in enumerate(key_points)
        if _news_point_signals(point) & {"follow_up", "comparison", "background"}
    ]
    if closing_candidates:
        closing_index = closing_candidates[-1]
    ordered_points = [
        point
        for index, point in enumerate(key_points)
        if index != closing_index
    ]
    if key_points:
        ordered_points.append(key_points[closing_index])
    # Deep discovery may provide distinct visuals from related reporting,
    # official video, and open-media sources. Expand only as far as those
    # post-discovery visuals support; never fill the gap with text-only cards.
    supported_points = ordered_points[: min(19, len(remaining_assets))]
    for position, key_point in enumerate(supported_points, start=1):
        asset = remaining_assets.pop(0)
        signals = _news_point_signals(key_point)
        if position == len(ordered_points):
            slide_role = "meaning_next_action"
        elif "number" in signals:
            slide_role = "key_number"
        elif "background" in signals:
            slide_role = "background"
        elif "statement" in signals:
            slide_role = "person_statement"
        elif "comparison" in signals:
            slide_role = "comparison"
        else:
            slide_role = "key_fact"
        slides.append(
            {
                "slide_role": slide_role,
                "media_type": asset["media_type"],
                "asset_refs": [asset["asset_id"]],
                "copy_source": "deep_discovery_bundle.key_points",
                "body": key_point,
                "content_unit": position,
            }
        )
    for asset in remaining_assets[: max(0, 20 - len(slides))]:
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
    for position, scene in enumerate(scenes[:19]):
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
        for asset in assets[1:20]:
            slides.append(
                {
                    "slide_role": asset["role_hint"] or "story_context",
                    "media_type": asset["media_type"],
                    "asset_refs": [asset["asset_id"]],
                    "copy_source": "deep_discovery_bundle",
                }
            )
    for comment in comments[: max(0, 20 - len(slides))]:
        comment_text = _text(comment.get("text"))
        display_text = _comment_display_excerpt(comment_text)
        comment_headline = comment_text
        if len(comment_headline) > 34:
            comment_headline = comment_headline[:34].rstrip() + "…"
        slides.append(
            {
                "slide_role": "real_comment",
                "media_type": "screenshot" if comment["source_url"] else "editorial",
                "comment_ref": comment["comment_id"],
                "identity_masked": comment["identity_masked"],
                "copy_source": "real_comment_only",
                "headline": comment_headline or "실제 댓글 반응",
                "body": display_text,
                "source_comment_text": comment_text,
            }
        )
    return slides


def _style_slides(
    title: str,
    assets: Sequence[Mapping[str, Any]],
    key_points: Sequence[str],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    slides = [_cover(title, assets)]
    motion_plan: List[Dict[str, Any]] = []
    primary_asset_refs = list(slides[0].get("asset_refs") or [])
    for position, key_point in enumerate(key_points[:19], start=1):
        slides.append(
            {
                "slide_role": "source_context",
                "media_type": "editorial",
                "asset_refs": primary_asset_refs,
                "copy_source": "deep_discovery_bundle.key_points",
                "body": key_point,
                "content_unit": position,
            }
        )
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
    news_key_points = (
        _consolidate_news_key_points(title, key_points)
        if account == "A"
        else key_points
    )
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
        slide_plan = _news_slides(title, assets, news_key_points)
        content_kind = "news"
    elif account == "B":
        slide_plan = _story_slides(title, assets, scenes, comments)
        content_kind = "story_relationship_dopamine_entertainment"
    else:
        slide_plan, motion_plan = _style_slides(title, assets, key_points)
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
        "key_points": news_key_points if account == "A" else key_points,
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
        "canvas_profile_id": DEFAULT_CARD_NEWS_PROFILE_ID,
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
