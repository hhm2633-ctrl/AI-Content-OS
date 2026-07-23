"""Prepare learned references and source media before the production gate."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from modules.card_news.reference_driven_production import (
    produce_reference_driven_slide,
)
from modules.design_learning.production_profile_compiler import (
    ProductionProfileCompiler,
)
from modules.source_intake.workflow_media_discovery_bridge import (
    WorkflowMediaDiscoveryBridge,
)


SCHEMA_VERSION = "workflow_card_news_production_preparation_v1"


def _mapping(value: Any) -> dict[str, Any]:
    return copy.deepcopy(dict(value)) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _selected_topic(topic_result: Any) -> dict[str, Any]:
    result = _mapping(topic_result)
    selected = result.get("selected_topic")
    return _mapping(selected) if isinstance(selected, Mapping) else result


def _account(topic: Mapping[str, Any]) -> str:
    explicit = _text(topic.get("account") or topic.get("account_id")).upper()
    if explicit in {"A", "B", "C"}:
        return explicit
    category = _text(topic.get("category") or topic.get("primary_category")).lower()
    if any(token in category for token in ("fashion", "beauty", "패션", "뷰티")):
        return "C"
    if any(token in category for token in ("story", "community", "썰", "연예")):
        return "B"
    return "A"


def _content(content_result: Any, topic: Mapping[str, Any]) -> dict[str, Any]:
    result = _mapping(content_result)
    title = _text(result.get("title") or topic.get("title") or topic.get("keyword"))
    body = _text(
        result.get("body")
        or result.get("content")
        or result.get("summary")
        or topic.get("summary")
    )
    source = _text(topic.get("publisher") or topic.get("source_name") or topic.get("source"))
    return {
        "headline": title,
        "body": body,
        "source_label": f"자료: {source}" if source else "",
    }


def _media_for_reference(media_result: Mapping[str, Any]) -> dict[str, Any]:
    assets = media_result.get("render_assets")
    rows = [copy.deepcopy(item) for item in assets if isinstance(item, Mapping)] if isinstance(assets, list) else []
    return {"primary_media": rows[:1], "secondary_media": rows[1:]}


class WorkflowProductionPreparation:
    """Connect learning, media discovery and Reference V2 without rendering."""

    def __init__(
        self,
        *,
        profile_compiler: Any = None,
        media_bridge: Any = None,
    ) -> None:
        self.profile_compiler = profile_compiler or ProductionProfileCompiler()
        self.media_bridge = media_bridge or WorkflowMediaDiscoveryBridge()

    def prepare(
        self,
        topic_result: Any,
        content_result: Any,
        *,
        reference_specimens: Any = None,
        reference_blueprints: Any = None,
    ) -> dict[str, Any]:
        topic = _selected_topic(topic_result)
        account = _account(topic)
        title = _text(topic.get("title") or topic.get("keyword"))
        context = {
            "account": {"A": "news", "B": "story", "C": "fashion"}.get(account, "news"),
            "topic": title,
            "formats": ["card_news"],
            "keywords": copy.deepcopy(topic.get("keywords", [])),
            "season": _text(topic.get("season")),
            "emotion": _text(topic.get("emotion")),
        }
        try:
            profile = self.profile_compiler.compile(context)
        except Exception as error:
            profile = {
                "status": "fallback",
                "reason_code": "production_profile_compile_failed",
                "error": str(error),
                "reference_candidates": [],
            }
        try:
            media = self.media_bridge.discover(
                {
                    "title": title,
                    "category": _text(topic.get("category") or topic.get("primary_category")),
                    "source_url": _text(topic.get("link") or topic.get("url")),
                },
                account=account,
            )
        except Exception as error:
            media = {
                "status": "fallback",
                "reason_code": "workflow_media_discovery_failed",
                "fallback_used": True,
                "assets": [],
                "render_assets": [],
                "error": str(error),
            }

        specimens = (
            [copy.deepcopy(item) for item in reference_specimens if isinstance(item, Mapping)]
            if isinstance(reference_specimens, list)
            else []
        )
        blueprints = (
            copy.deepcopy(dict(reference_blueprints))
            if isinstance(reference_blueprints, Mapping)
            else {}
        )
        if specimens and blueprints:
            reference_v2 = produce_reference_driven_slide(
                specimens=specimens,
                blueprints=blueprints,
                context={
                    "account": account,
                    "slide_role": "hook",
                    "media_count": len(media.get("render_assets", [])),
                    "copy_char_count": len(_content(content_result, topic)["headline"]),
                },
                content=_content(content_result, topic),
                media=_media_for_reference(media),
            )
        else:
            reference_v2 = {
                "schema_version": "reference-driven-production.v2",
                "status": "blocked",
                "outcome": "blocked",
                "reason_code": "owner_approved_reference_geometry_required",
                "legacy_renderer_fallback_allowed": False,
            }

        return {
            "schema_version": SCHEMA_VERSION,
            "status": "prepared",
            "render_executed": False,
            "publish_executed": False,
            "account": account,
            "topic": title,
            "production_learning_profile": profile,
            "media_discovery": media,
            "reference_v2": reference_v2,
            "production_ready": reference_v2.get("status") == "ready",
        }


def prepare_workflow_card_news_production(
    topic_result: Any,
    content_result: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    return WorkflowProductionPreparation().prepare(topic_result, content_result, **kwargs)


__all__ = [
    "SCHEMA_VERSION",
    "WorkflowProductionPreparation",
    "prepare_workflow_card_news_production",
]
