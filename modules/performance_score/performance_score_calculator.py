from typing import Any, Dict, Optional


class PerformanceScoreCalculator(object):
    """
    Performance Score - Score.

    Hook/CTA/Layout/Brand/Image 5개 도메인 점수를 계산한다. 각 점수는 새로 계산하지
    않고, 이미 파이프라인 각 단계가 만들어 둔 신호(Content Intelligence의
    hook_score/cta_score, CardNews layout_result.layout_quality_score /
    card_news_quality.qa_score, Content brand_rule_passed, Image Strategy의
    need_ai_image/fallback_used)를 그대로 재사용해 조합한다 (중복 재계산 없음).

    필요한 입력이 없거나 계산 중 예외가 발생해도 각 점수는 안전한 기본값(0.5)으로
    떨어지며 예외를 던지지 않는다.
    """

    DEFAULT_SCORE = 0.5

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def calculate(
        self,
        content_result: Optional[Dict[str, Any]] = None,
        card_news_result: Optional[Dict[str, Any]] = None,
        image_strategy_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        content_result = content_result or {}
        card_news_result = card_news_result or {}
        image_strategy_result = image_strategy_result or {}

        hook_score = self._safe(lambda: self._hook_score(content_result))
        cta_score = self._safe(lambda: self._cta_score(content_result))
        layout_score = self._safe(lambda: self._layout_score(card_news_result))
        brand_score = self._safe(lambda: self._brand_score(content_result))
        image_score = self._safe(lambda: self._image_score(image_strategy_result))

        overall = round(
            (hook_score * 0.25) + (cta_score * 0.2) + (layout_score * 0.2)
            + (brand_score * 0.2) + (image_score * 0.15),
            4,
        )

        return {
            "hook_score": round(hook_score, 4),
            "cta_score": round(cta_score, 4),
            "layout_score": round(layout_score, 4),
            "brand_score": round(brand_score, 4),
            "image_score": round(image_score, 4),
            "overall_performance_score": overall,
        }

    def _safe(self, func) -> float:
        try:
            value = float(func())
            return max(0.0, min(1.0, value))
        except Exception:
            return self.DEFAULT_SCORE

    def _hook_score(self, content_result: Dict[str, Any]) -> float:
        prompt_meta = content_result.get("pattern_prompt_meta") or {}
        hook_score = prompt_meta.get("hook_score")

        if isinstance(hook_score, (int, float)):
            return float(hook_score)

        checks = ((content_result.get("content_intelligence") or {}).get("details") or {}).get("quality") or {}
        if checks.get("checks", {}).get("hook_present"):
            return 1.0

        return self.DEFAULT_SCORE

    def _cta_score(self, content_result: Dict[str, Any]) -> float:
        prompt_meta = content_result.get("pattern_prompt_meta") or {}
        cta_score = prompt_meta.get("cta_score")

        if isinstance(cta_score, (int, float)):
            return float(cta_score)

        checks = ((content_result.get("content_intelligence") or {}).get("details") or {}).get("quality") or {}
        if checks.get("checks", {}).get("cta_present"):
            return 1.0

        return self.DEFAULT_SCORE

    def _layout_score(self, card_news_result: Dict[str, Any]) -> float:
        layout_result = card_news_result.get("layout_result") or {}
        layout_quality_score = layout_result.get("layout_quality_score")

        if isinstance(layout_quality_score, (int, float)):
            return float(layout_quality_score)

        card_news_quality = card_news_result.get("card_news_quality") or {}
        qa_score = card_news_quality.get("qa_score")

        if isinstance(qa_score, (int, float)):
            return float(qa_score)

        return self.DEFAULT_SCORE

    def _brand_score(self, content_result: Dict[str, Any]) -> float:
        content_intelligence = content_result.get("content_intelligence") or {}

        if "brand_rule_passed" in content_intelligence:
            return 1.0 if content_intelligence.get("brand_rule_passed") else 0.2

        return self.DEFAULT_SCORE

    def _image_score(self, image_strategy_result: Dict[str, Any]) -> float:
        if not image_strategy_result:
            return self.DEFAULT_SCORE

        if image_strategy_result.get("fallback_used"):
            return 0.3

        if image_strategy_result.get("need_ai_image") is False:
            return 0.9

        return 0.6
