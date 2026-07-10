from typing import Any, Dict, List, Optional


class AuditChecks(object):
    """
    Content Audit Engine - 개별 검사 항목 (Sprint 13 강화).

    Hook/CTA/Pattern/Layout/Image Strategy/중복 위험/저장 유도/댓글 유도 + Brand
    (보너스) 검사를 수행한다. 각 검사는 새로운 판정 로직을 처음부터 만들지 않고,
    이미 파이프라인이 계산해 둔 실제 신호(Performance Score, Content
    Intelligence, Pattern Plan, Image Sourcing Status, Knowledge DB, Trend
    Memory)를 실제로 읽어 pass/fail과 세부 사유를 만든다.

    각 검사는 독립적으로 보호되어 하나가 실패해도 나머지 검사에 영향을 주지 않는다.
    """

    PASS_THRESHOLD = 0.6

    SAVE_KEYWORDS = ("저장",)
    COMMENT_KEYWORDS = ("댓글", "궁금", "생각")

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def run_all(self, context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        checks = {}

        for name, func in (
            ("hook_check", self._hook_check),
            ("cta_check", self._cta_check),
            ("pattern_check", self._pattern_check),
            ("layout_check", self._layout_check),
            ("brand_check", self._brand_check),
            ("image_strategy_check", self._image_strategy_check),
            ("duplicate_check", self._duplicate_check),
            ("save_inducement_check", self._save_inducement_check),
            ("comment_inducement_check", self._comment_inducement_check),
        ):
            try:
                checks[name] = func(context)
            except Exception as error:
                checks[name] = {
                    "passed": False,
                    "score": 0.0,
                    "reason": f"{name} 계산 실패: {error}",
                }

        return checks

    # ---- Hook 강도 ----

    def _hook_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        content_result = context["content_result"]
        performance_score_result = context["performance_score_result"]

        score = float(performance_score_result.get("hook_score", 0.5))
        content_intelligence = content_result.get("content_intelligence") or {}
        hook_present = ((content_intelligence.get("details") or {}).get("quality") or {}).get("checks", {}).get("hook_present", True)

        passed = bool(hook_present) and score >= self.PASS_THRESHOLD

        return {
            "passed": passed,
            "score": round(score, 4),
            "reason": "hook 슬라이드 존재 및 hook_score 기준 충족." if passed else "hook 슬라이드가 없거나 hook_score가 낮음.",
        }

    # ---- CTA 존재 여부 ----

    def _cta_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        content_result = context["content_result"]
        performance_score_result = context["performance_score_result"]

        score = float(performance_score_result.get("cta_score", 0.5))
        content_intelligence = content_result.get("content_intelligence") or {}
        cta_present = ((content_intelligence.get("details") or {}).get("quality") or {}).get("checks", {}).get("cta_present", True)

        passed = bool(cta_present) and score >= self.PASS_THRESHOLD

        return {
            "passed": passed,
            "score": round(score, 4),
            "reason": "CTA 슬라이드 존재 및 cta_score 기준 충족." if passed else "CTA 슬라이드가 없거나 cta_score가 낮음.",
        }

    # ---- Pattern 일치 (Sprint 13 신규) ----

    def _pattern_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        content_result = context["content_result"]
        pattern_result = context["pattern_result"]

        prompt_source = content_result.get("prompt_source", "")

        if prompt_source != "pattern_aware":
            return {
                "passed": True,
                "score": 0.5,
                "reason": "prompt_source가 pattern_aware가 아니어서 pattern 일치 여부를 판단할 수 없음(중립 처리).",
            }

        prompt_meta = content_result.get("pattern_prompt_meta") or {}
        content_pattern_type = str(prompt_meta.get("pattern_type", ""))
        plan_pattern_type = str((pattern_result.get("pattern_plan") or {}).get("pattern_type", ""))

        matched = bool(content_pattern_type) and content_pattern_type == plan_pattern_type

        return {
            "passed": matched,
            "score": 1.0 if matched else 0.3,
            "reason": (
                f"Content의 pattern_type('{content_pattern_type}')이 Pattern Engine 계획"
                f"('{plan_pattern_type}')과 일치함." if matched else
                f"Content의 pattern_type('{content_pattern_type}')이 Pattern Engine 계획"
                f"('{plan_pattern_type}')과 불일치함."
            ),
        }

    # ---- Layout 일치 ----

    def _layout_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        card_news_result = context["card_news_result"]
        pattern_result = context["pattern_result"]
        performance_score_result = context["performance_score_result"]

        score = float(performance_score_result.get("layout_score", 0.5))
        layout_result = card_news_result.get("layout_result") or {}
        layout_fallback = bool(layout_result.get("fallback_used", False))

        rendered_layout_type = str(layout_result.get("layout_type", ""))
        planned_layout_type = str((pattern_result.get("pattern_plan") or {}).get("layout_type", ""))
        layout_matches_plan = bool(rendered_layout_type) and rendered_layout_type == planned_layout_type

        passed = (not layout_fallback) and score >= self.PASS_THRESHOLD

        reason = "layout_result 정상 반영, layout_score 기준 충족." if passed else "layout fallback 사용 또는 layout_score가 낮음."
        reason += (
            f" Pattern 계획 layout('{planned_layout_type}')과 실제 렌더링('{rendered_layout_type}')이 "
            + ("일치함." if layout_matches_plan else "다름(레이아웃 재선택 로직에 의한 정상적인 차이일 수 있음).")
        )

        return {
            "passed": passed,
            "score": round(score, 4),
            "layout_matches_plan": layout_matches_plan,
            "reason": reason,
        }

    # ---- Brand (보너스) ----

    def _brand_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        content_result = context["content_result"]
        performance_score_result = context["performance_score_result"]

        content_intelligence = content_result.get("content_intelligence") or {}
        brand_rule_passed = bool(content_intelligence.get("brand_rule_passed", True))
        score = float(performance_score_result.get("brand_score", 0.5))

        return {
            "passed": brand_rule_passed,
            "score": round(score, 4),
            "reason": "브랜드 규칙 통과." if brand_rule_passed else "브랜드 금지 표현 또는 톤 위반 감지됨.",
        }

    # ---- Image Strategy 일치 (Sprint 13 강화: 계획 대비 실제 이행 여부 확인) ----

    def _image_strategy_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        card_news_result = context["card_news_result"]
        performance_score_result = context["performance_score_result"]

        score = float(performance_score_result.get("image_score", 0.5))
        image_sourcing_status = card_news_result.get("image_sourcing_status") or {}
        manual_image_required = bool(image_sourcing_status.get("manual_image_required", False))

        passed = (not manual_image_required) and score >= self.PASS_THRESHOLD

        if manual_image_required:
            reason = (
                f"Image Strategy가 실제 이미지({image_sourcing_status.get('recommended_source', '')})를 "
                "권장했지만 아직 소싱되지 않아 계획과 실제가 불일치함 (manual_image_required)."
            )
        else:
            reason = "Image Strategy 계획과 실제 렌더링 결과가 일치함."

        return {
            "passed": passed,
            "score": round(score, 4),
            "manual_image_required": manual_image_required,
            "reason": reason,
        }

    # ---- 중복 위험 (Sprint 13: Knowledge DB + Trend Memory까지 함께 반영) ----

    def _duplicate_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        content_result = context["content_result"]
        knowledge_result = context["knowledge_result"]
        trend_memory_result = context["trend_memory_result"]

        content_intelligence = content_result.get("content_intelligence") or {}
        content_duplicate_risk = str(content_intelligence.get("duplicate_risk", "low"))

        top_knowledge = knowledge_result.get("top_knowledge", [])
        if not isinstance(top_knowledge, list):
            top_knowledge = []

        knowledge_high_risk_count = sum(
            1 for item in top_knowledge
            if str((self._load_knowledge_duplicate_risk(item))) == "high"
        )

        topic_repeat_risk = str(trend_memory_result.get("topic_repeat_risk", "low"))

        risk_levels = {"low": 0, "medium": 1, "high": 2}
        worst_level = max(
            risk_levels.get(content_duplicate_risk, 0),
            risk_levels.get(topic_repeat_risk, 0),
            2 if knowledge_high_risk_count else 0,
        )
        worst_risk = {0: "low", 1: "medium", 2: "high"}[worst_level]

        risk_score = {"low": 1.0, "medium": 0.5, "high": 0.0}[worst_risk]
        passed = worst_risk != "high"

        return {
            "passed": passed,
            "score": round(risk_score, 4),
            "content_duplicate_risk": content_duplicate_risk,
            "topic_repeat_risk": topic_repeat_risk,
            "knowledge_high_risk_count": knowledge_high_risk_count,
            "reason": (
                f"content_intelligence.duplicate_risk='{content_duplicate_risk}', "
                f"trend_memory.topic_repeat_risk='{topic_repeat_risk}', "
                f"knowledge 상위 항목 중 high risk {knowledge_high_risk_count}건 -> 최종 '{worst_risk}'."
            ),
        }

    def _load_knowledge_duplicate_risk(self, item: Dict[str, Any]) -> str:
        return str(item.get("duplicate_risk", "low"))

    # ---- 저장 유도 가능성 (Sprint 13 신규) ----

    def _save_inducement_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        content_result = context["content_result"]
        pattern_result = context["pattern_result"]

        cta_type = str((pattern_result.get("pattern_plan") or {}).get("cta_type", ""))
        cta_text = self._extract_cta_text(content_result)

        save_signal = cta_type == "save" or any(keyword in cta_text for keyword in self.SAVE_KEYWORDS)

        return {
            "passed": save_signal,
            "score": 1.0 if save_signal else 0.4,
            "reason": "CTA가 저장을 유도함." if save_signal else "CTA에서 저장 유도 신호를 찾지 못함.",
        }

    # ---- 댓글 유도 가능성 (Sprint 13 신규) ----

    def _comment_inducement_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        content_result = context["content_result"]
        pattern_result = context["pattern_result"]

        cta_type = str((pattern_result.get("pattern_plan") or {}).get("cta_type", ""))
        cta_text = self._extract_cta_text(content_result)

        comment_signal = cta_type == "comment" or any(keyword in cta_text for keyword in self.COMMENT_KEYWORDS)

        return {
            "passed": comment_signal,
            "score": 1.0 if comment_signal else 0.4,
            "reason": "CTA가 댓글을 유도함." if comment_signal else "CTA에서 댓글 유도 신호를 찾지 못함 (저장/공유 등 다른 목적일 수 있음).",
        }

    def _extract_cta_text(self, content_result: Dict[str, Any]) -> str:
        slides = content_result.get("slides", [])

        if not isinstance(slides, list):
            return ""

        for slide in slides:
            if isinstance(slide, dict) and slide.get("role") == "cta":
                return f"{slide.get('headline', '')} {slide.get('body', '')}"

        return ""
