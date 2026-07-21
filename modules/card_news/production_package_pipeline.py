"""Package one completed Agent Console result without rendering or publishing."""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Mapping

from modules.card_news.selected_candidate_production_package import (
    build_selected_candidate_production_package,
)
from modules.card_news.selected_candidate_production_planner import (
    build_selected_candidate_production_plan,
)
from modules.card_news.selected_candidate_render_input_adapter import (
    build_selected_candidate_render_inputs,
)


SCHEMA_VERSION = "cardnews_production_package_pipeline_v1"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _outputs(handoff: Mapping[str, Any]) -> Mapping[str, Any]:
    outputs = handoff.get("outputs")
    outputs = outputs if isinstance(outputs, Mapping) else {}
    spark = outputs.get("spark_receipt")
    if isinstance(spark, Mapping) and isinstance(spark.get("outputs"), Mapping):
        return spark["outputs"]
    return outputs


def _source_urls(candidate: Mapping[str, Any], outputs: Mapping[str, Any]) -> List[str]:
    urls: List[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str) and value.strip().startswith(("http://", "https://")):
            if value.strip() not in urls:
                urls.append(value.strip())
        elif isinstance(value, Mapping):
            add(value.get("url") or value.get("source_url"))
        elif isinstance(value, list):
            for item in value:
                add(item)

    add(candidate.get("source_urls"))
    article = outputs.get("article_analysis")
    if isinstance(article, Mapping):
        add(article.get("source_url"))
    add(outputs.get("sources"))
    return urls


def _split_copy(value: str) -> tuple[str, str]:
    cleaned = re.sub(r"^\s*\d+\s*[^:：]*[:：]\s*", "", value).strip()
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if len(lines) >= 2:
        return lines[0], " ".join(lines[1:])
    if not lines:
        return "", ""
    sentence = lines[0]
    return sentence, sentence


def _planned_slides(outputs: Mapping[str, Any]) -> List[Dict[str, Any]]:
    plan = outputs.get("cardnews_plan")
    if not isinstance(plan, Mapping):
        return []
    structured = plan.get("slide_script")
    rows: List[Dict[str, Any]] = []
    if isinstance(structured, list):
        for position, raw in enumerate(structured, start=1):
            if not isinstance(raw, Mapping):
                continue
            headline, body = _split_copy(_text(raw.get("copy")))
            if headline and body:
                rows.append(
                    {
                        "page": position,
                        "role": _text(raw.get("role")) or ("cover" if position == 1 else "source_context"),
                        "media_type": "editorial",
                        "headline": headline,
                        "body": body,
                    }
                )
        return rows
    plain = plan.get("slides")
    if isinstance(plain, list):
        for position, raw in enumerate(plain, start=1):
            headline, body = _split_copy(_text(raw))
            if headline and body:
                rows.append(
                    {
                        "page": position,
                        "role": "cover" if position == 1 else "source_context",
                        "media_type": "editorial",
                        "headline": headline,
                        "body": body,
                    }
                )
    return rows


def normalize_completed_handoff(
    candidate: Mapping[str, Any], handoff: Mapping[str, Any]
) -> Dict[str, Any]:
    """Adapt completed local output into evidence/story inputs without invention."""

    outputs = _outputs(handoff)
    urls = _source_urls(candidate, outputs)
    slides = _planned_slides(outputs)
    summary = _text(handoff.get("summary")) or _text(outputs.get("brief"))
    article = outputs.get("article_analysis")
    key_points = article.get("key_points") if isinstance(article, Mapping) else []
    key_points = [item for item in key_points if isinstance(item, str) and item.strip()]
    caption = _text(outputs.get("caption_draft"))
    plan = outputs.get("cardnews_plan")
    if isinstance(plan, Mapping):
        caption = _text(plan.get("caption_draft")) or caption
    candidate_id = _text(candidate.get("candidate_id"))
    account = _text(candidate.get("account")).upper()
    assets = [
        {
            "asset_id": f"{candidate_id}-source-{position}",
            "media_type": "editorial",
            "origin": "source",
            "asset_class": "source_reference",
            "remote_url": url,
            "source_url": url,
            "rights_status": "reference_only",
            "role_hint": "source_context",
        }
        for position, url in enumerate(urls, start=1)
    ]
    return {
        "deep_bundle": {
            "schema_version": "normalized_completed_deep_bundle_v1",
            "status": "completed",
            "candidate_id": candidate_id,
            "account": account,
            "title": _text(candidate.get("title")),
            "summary": summary,
            "feed_body": caption,
            "key_points": key_points,
            "source_refs": urls,
            "assets": assets,
            "planned_slides": copy.deepcopy(slides),
            "comments": [],
            "reconstruction_scenes": [],
            "content_type": _text(candidate.get("category")),
        },
        "story_output": {
            "candidate_id": candidate_id,
            "account": account,
            "story": {"summary": summary},
            "slide_copy": copy.deepcopy(slides),
            "feed_caption": caption,
        },
    }


def build_package_from_completed_handoff(
    candidate: Mapping[str, Any],
    handoff: Mapping[str, Any],
    approval_receipt: Mapping[str, Any],
) -> Dict[str, Any]:
    normalized = normalize_completed_handoff(candidate, handoff)
    deep_bundle = normalized["deep_bundle"]
    plan = build_selected_candidate_production_plan(candidate, deep_bundle)
    render_receipt = build_selected_candidate_render_inputs(plan, normalized["story_output"]["slide_copy"])
    package = build_selected_candidate_production_package(
        plan,
        render_receipt,
        normalized["story_output"],
        approval_receipt,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": _text(candidate.get("candidate_id")),
        "account": _text(candidate.get("account")).upper(),
        "normalization": normalized,
        "production_plan": plan,
        "render_input_receipt": render_receipt,
        "package": package,
        "render_executed": False,
        "publish_executed": False,
        "link_issuance_executed": False,
    }


__all__ = [
    "normalize_completed_handoff",
    "build_package_from_completed_handoff",
    "SCHEMA_VERSION",
]
