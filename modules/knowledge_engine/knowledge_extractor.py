import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional


class KnowledgeExtractor(object):
    """
    Knowledge Engine - Extractor.

    WorkflowEngine의 각 단계 결과(Pattern/Research/Content/ImageStrategy/CardNews/
    Publishing)에서 재사용 가능한 Knowledge 후보를 추출한다.

    추출 대상: Hook, CTA, Pattern, Layout, Brand, Workflow, Prompt Pattern, Tool,
    Image Strategy, Funnel.

    입력이 비어 있거나 특정 추출 단계에서 예외가 발생해도 전체 추출이 중단되지
    않도록 각 추출 단계를 개별적으로 보호하고, 실패한 단계는 빈 목록으로 취급한다.
    """

    KNOWLEDGE_TYPES = (
        "hook",
        "cta",
        "pattern",
        "layout",
        "brand",
        "workflow",
        "prompt_pattern",
        "tool",
        "image_strategy",
        "funnel",
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def extract(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        context = context if isinstance(context, dict) else {}
        items: List[Dict[str, Any]] = []

        extractors = (
            self._extract_hook,
            self._extract_cta,
            self._extract_pattern,
            self._extract_layout,
            self._extract_brand,
            self._extract_workflow,
            self._extract_prompt_pattern,
            self._extract_tool,
            self._extract_image_strategy,
            self._extract_funnel,
        )

        for extractor in extractors:
            try:
                extracted = extractor(context)
            except Exception as error:
                print(f"Knowledge Extractor Step Failed ({extractor.__name__}): {error}")
                extracted = []

            for item in extracted or []:
                if item:
                    items.append(item)

        return items

    # ---- shared helpers ----

    def _make_item(
        self,
        knowledge_type: str,
        title: str,
        content: Dict[str, Any],
        source_module: str,
        source_reason: str = "",
        fallback_used: bool = False,
    ) -> Dict[str, Any]:
        title = str(title or "").strip()

        if not title:
            return {}

        return {
            "knowledge_id": self._build_id(knowledge_type, title, content),
            "type": knowledge_type,
            "title": title,
            "content": content or {},
            "source_module": source_module,
            "source_reason": str(source_reason or ""),
            "fallback_used": bool(fallback_used),
            "extracted_at": datetime.now().isoformat(),
        }

    def _build_id(self, knowledge_type: str, title: str, content: Dict[str, Any]) -> str:
        try:
            content_signature = str(sorted((content or {}).items(), key=lambda pair: str(pair[0])))
        except Exception:
            content_signature = str(content)

        raw = f"{knowledge_type}:{title}:{content_signature}"
        return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]

    def _pattern_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pattern_result = context.get("pattern_result") or {}
        plan = pattern_result.get("pattern_plan")
        return plan if isinstance(plan, dict) else {}

    # ---- Hook / CTA (ContentModule slides + Pattern Engine plan) ----

    def _extract_hook(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._extract_role_slide(
            context=context,
            role="hook",
            knowledge_type="hook",
            plan_field="hook_type",
        )

    def _extract_cta(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._extract_role_slide(
            context=context,
            role="cta",
            knowledge_type="cta",
            plan_field="cta_type",
        )

    def _extract_role_slide(
        self,
        context: Dict[str, Any],
        role: str,
        knowledge_type: str,
        plan_field: str,
    ) -> List[Dict[str, Any]]:
        content_result = context.get("content_result") or {}
        pattern_plan = self._pattern_plan(context)
        slides = content_result.get("slides", [])
        items = []

        if not isinstance(slides, list):
            return items

        for slide in slides:
            if not isinstance(slide, dict) or slide.get("role") != role:
                continue

            headline = str(slide.get("headline", "")).strip()
            body = str(slide.get("body", "")).strip()

            if not headline and not body:
                continue

            item = self._make_item(
                knowledge_type=knowledge_type,
                title=headline or body[:40],
                content={
                    "headline": headline,
                    "body": body,
                    plan_field: pattern_plan.get(plan_field, ""),
                },
                source_module="content_module",
                source_reason=f"content_result.slides[role={role}]",
                fallback_used=bool(content_result.get("fallback_used", False)),
            )

            if item:
                items.append(item)

        return items

    # ---- Pattern (Pattern Engine) ----

    def _extract_pattern(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        pattern_result = context.get("pattern_result") or {}
        pattern_plan = self._pattern_plan(context)
        topic_intelligence = pattern_result.get("topic_intelligence") or {}

        pattern_type = str(pattern_plan.get("pattern_type", "") or "")

        if not pattern_type:
            return []

        item = self._make_item(
            knowledge_type="pattern",
            title=f"pattern:{pattern_type}",
            content={
                "pattern_type": pattern_type,
                "category": topic_intelligence.get("category", ""),
                "cluster": topic_intelligence.get("cluster", ""),
                "confidence_score": topic_intelligence.get("confidence_score", 0.0),
                "reason": pattern_plan.get("reason", ""),
            },
            source_module="pattern_engine",
            source_reason="pattern_result.pattern_plan",
            fallback_used=bool(pattern_result.get("fallback_used", False)),
        )

        return [item] if item else []

    # ---- Layout (CardNews Layout Intelligence) ----

    def _extract_layout(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        card_news_result = context.get("card_news_result") or {}
        layout_result = card_news_result.get("layout_result") or {}

        layout_type = str(layout_result.get("layout_type", "") or "")

        if not layout_type:
            return []

        item = self._make_item(
            knowledge_type="layout",
            title=f"layout:{layout_type}",
            content={
                "layout_type": layout_type,
                "slide_count": layout_result.get("slide_count", 0),
                "title_style": layout_result.get("title_style", ""),
                "body_style": layout_result.get("body_style", ""),
                "image_ratio": layout_result.get("image_ratio", ""),
                "cta_position": layout_result.get("cta_position", ""),
                "layout_quality_score": layout_result.get("layout_quality_score", 0.0),
            },
            source_module="card_news_module",
            source_reason="card_news_result.layout_result",
            fallback_used=bool(layout_result.get("fallback_used", False)),
        )

        return [item] if item else []

    # ---- Brand (Content brand rule evaluation) ----

    def _extract_brand(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        content_result = context.get("content_result") or {}
        content_intelligence = content_result.get("content_intelligence") or {}
        details = content_intelligence.get("details") or {}
        brand_detail = details.get("brand_rule") or {}

        if not brand_detail:
            return []

        passed = bool(
            content_intelligence.get("brand_rule_passed", brand_detail.get("brand_rule_passed", False))
        )
        title = "brand_rule:passed" if passed else "brand_rule:violation_detected"

        item = self._make_item(
            knowledge_type="brand",
            title=title,
            content={
                "brand_rule_passed": passed,
                "details": brand_detail,
            },
            source_module="content_module",
            source_reason="content_result.content_intelligence.details.brand_rule",
            fallback_used=False,
        )

        return [item] if item else []

    # ---- Workflow (aggregate fallback signature for this run) ----

    def _extract_workflow(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        stage_results = {
            "trend": context.get("trend_result"),
            "topic": context.get("topic_result"),
            "pattern": context.get("pattern_result"),
            "research": context.get("research_result"),
            "content": context.get("content_result"),
            "image_strategy": context.get("image_strategy_result"),
            "card_news": context.get("card_news_result"),
            "publishing": context.get("publishing_result"),
        }

        fallback_stages = [
            name for name, result in stage_results.items()
            if isinstance(result, dict) and result.get("fallback_used")
        ]

        title = "workflow_run:" + ("with_fallback" if fallback_stages else "clean_run")

        item = self._make_item(
            knowledge_type="workflow",
            title=title,
            content={
                "fallback_stages": fallback_stages,
                "stage_count": len([result for result in stage_results.values() if result]),
            },
            source_module="workflow_engine",
            source_reason="aggregate fallback_used flags across pipeline stages",
            fallback_used=bool(fallback_stages),
        )

        return [item] if item else []

    # ---- Prompt Pattern (Content prompt builder) ----

    def _extract_prompt_pattern(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        content_result = context.get("content_result") or {}
        prompt_source = str(content_result.get("prompt_source", "") or "")

        if not prompt_source:
            return []

        item = self._make_item(
            knowledge_type="prompt_pattern",
            title=f"prompt_pattern:{prompt_source}",
            content={
                "prompt_source": prompt_source,
                "meta": content_result.get("pattern_prompt_meta") or {},
            },
            source_module="content_module",
            source_reason="content_result.prompt_source / pattern_prompt_meta",
            fallback_used=bool(content_result.get("fallback_used", False)),
        )

        return [item] if item else []

    # ---- Tool (Image Strategy real-image source selection) ----

    def _extract_tool(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        image_strategy_result = context.get("image_strategy_result") or {}
        image_source = str(image_strategy_result.get("image_source", "") or "")

        if not image_source:
            return []

        item = self._make_item(
            knowledge_type="tool",
            title=f"tool:{image_source}",
            content={
                "image_source": image_source,
                "content_type": image_strategy_result.get("content_type", ""),
                "priority": image_strategy_result.get("priority", []),
            },
            source_module="image_strategy_module",
            source_reason="image_strategy_result.image_source",
            fallback_used=bool(image_strategy_result.get("fallback_used", False)),
        )

        return [item] if item else []

    # ---- Image Strategy (content type -> image usage plan) ----

    def _extract_image_strategy(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        image_strategy_result = context.get("image_strategy_result") or {}
        content_type = str(image_strategy_result.get("content_type", "") or "")

        if not content_type:
            return []

        item = self._make_item(
            knowledge_type="image_strategy",
            title=f"image_strategy:{content_type}",
            content={
                "content_type": content_type,
                "need_ai_image": image_strategy_result.get("need_ai_image", True),
                "image_usage_plan": image_strategy_result.get("image_usage_plan", {}),
            },
            source_module="image_strategy_module",
            source_reason="image_strategy_result",
            fallback_used=bool(image_strategy_result.get("fallback_used", False)),
        )

        return [item] if item else []

    # ---- Funnel (topic -> content -> publish channel) ----

    def _extract_funnel(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        research_result = context.get("research_result") or {}
        publishing_result = context.get("publishing_result") or {}

        keyword = str(research_result.get("keyword", "") or "")

        if not keyword:
            return []

        item = self._make_item(
            knowledge_type="funnel",
            title=f"funnel:{keyword}",
            content={
                "keyword": keyword,
                "target": research_result.get("target", ""),
                "topic_angle": research_result.get("topic_angle", ""),
                "publish_platform": publishing_result.get("platform", ""),
                "publish_status": publishing_result.get("status", ""),
            },
            source_module="research_module+publishing_module",
            source_reason="research_result.keyword + publishing_result.platform/status",
            fallback_used=False,
        )

        return [item] if item else []
