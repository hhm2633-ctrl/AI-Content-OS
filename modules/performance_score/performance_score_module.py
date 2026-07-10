from datetime import datetime
from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.performance_score.performance_score_calculator import PerformanceScoreCalculator
from modules.performance_score.performance_score_history import PerformanceScoreHistory
from modules.performance_score.performance_score_interface import PerformanceScoreInterface
from modules.performance_score.performance_score_storage import PerformanceScoreStorage


class PerformanceScoreModule(BaseModule):
    """
    Performance Score Engine v1.

    Hook/CTA/Layout/Brand/Image 5개 도메인 점수를 하나의 표준 Performance Score로
    합산한다. 이 Engine은 외부 네트워크/LLM을 호출하지 않는 순수 계산 Engine이므로
    별도 Retry 로직은 없으며, 계산 실패 시 안전한 기본 점수(0.5)로 대체하는 것이
    이 Engine의 Fallback 전략이다.

    Audit Engine / Learning Engine / Analytics Engine이 공통으로 참조하는 하위
    Engine이며, WorkflowEngine에서는 CardNews/Publishing 이후, Audit/Learning/
    Analytics 이전에 실행된다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.calculator = PerformanceScoreCalculator(self.config)
        self.storage = PerformanceScoreStorage()
        self.history = PerformanceScoreHistory()
        self.interface = PerformanceScoreInterface(self.storage)

    def run(
        self,
        content_result: Optional[Dict[str, Any]] = None,
        card_news_result: Optional[Dict[str, Any]] = None,
        image_strategy_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Performance Score Module Started")

        try:
            result = self._build_result(content_result, card_news_result, image_strategy_result)
        except Exception as error:
            print(f"Performance Score Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"performance_score_exception: {error}")

        print("Performance Score Module Finished")
        return result

    def _build_result(
        self,
        content_result: Optional[Dict[str, Any]],
        card_news_result: Optional[Dict[str, Any]],
        image_strategy_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        scores = self.calculator.calculate(
            content_result=content_result or {},
            card_news_result=card_news_result or {},
            image_strategy_result=image_strategy_result or {},
        )

        result = {
            "status": "performance_score_completed",
            **scores,
            "fallback_used": False,
            "created_at": datetime.now().isoformat(),
        }

        self.storage.save(result)
        self.storage.update_statistics(scores)
        self.history.record(scores)

        return result

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        scores = {
            "hook_score": 0.5,
            "cta_score": 0.5,
            "layout_score": 0.5,
            "brand_score": 0.5,
            "image_score": 0.5,
            "overall_performance_score": 0.5,
        }

        try:
            self.storage.save({"status": "performance_score_completed", **scores, "fallback_used": True})
            self.storage.update_statistics(scores)
            self.history.record(scores)
        except Exception as error:
            print(f"Performance Score Fallback Persist Failed: {error}")

        return {
            "status": "performance_score_completed",
            **scores,
            "fallback_used": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }
