from datetime import datetime
from typing import Any, Dict, List, Optional

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

        planner_summary = self._build_planner_summary(
            content_result=content_result or {},
            card_news_result=card_news_result or {},
            image_strategy_result=image_strategy_result or {},
            overall_performance_score=float(scores.get("overall_performance_score", 0.0) or 0.0),
        )

        result = {
            "status": "performance_score_completed",
            **scores,
            **planner_summary,
            "measurement_class": "internal_proxy",
            "performance_provenance": {
                "source": "pre_publish_quality_signals",
                "external_measured": False,
                "eligible_for_pattern_promotion": False,
            },
            "fallback_used": False,
            "created_at": datetime.now().isoformat(),
        }

        self.storage.save(result)
        self.storage.update_statistics(scores)
        self.history.record(scores)

        return result

    # Planner 적용 여부와 최종 품질 분리 기록 (Sprint 16-0, 절대 규칙: Planner는
    # Hint Layer일 뿐이므로, "Planner를 썼다"와 "그 결과 품질이 좋았다"는 서로
    # 다른 사실이다 - 하나로 뭉뚱그리지 않는다).
    PLANNER_HELPFUL_THRESHOLD = 0.7

    def _build_planner_summary(
        self,
        content_result: Dict[str, Any],
        card_news_result: Dict[str, Any],
        image_strategy_result: Dict[str, Any],
        overall_performance_score: float,
    ) -> Dict[str, Any]:
        try:
            content_consumption = (content_result.get("planner_consumption") or {}).get("content", {}) or {}
            image_consumption = (image_strategy_result.get("planner_consumption") or {}).get(
                "image_strategy", {}
            ) or {}

            entries: List[Dict[str, Any]] = [
                entry for entry in content_consumption.values() if isinstance(entry, dict)
            ]
            if isinstance(image_consumption, dict) and image_consumption:
                entries.append(image_consumption)

            planner_available = any(bool(entry.get("planner_available")) for entry in entries)
            applied_entries = [entry for entry in entries if entry.get("planner_applied")]
            rejected_entries = [
                entry for entry in entries
                if entry.get("planner_available") and not entry.get("planner_applied")
            ]

            planner_used = bool(applied_entries)
            planner_rejected = bool(rejected_entries)

            # planner_helpful: 이번 실행 하나에서 "Hint가 적용됐다"와 "최종 품질
            # 점수가 높았다"가 같은 실행에서 함께 관찰됐다는 상관관계일 뿐,
            # Planner가 그 품질을 실제로 유발했다는 인과 증명이 아니다 - 그렇게
            # 오해되지 않도록 reason에 명시한다.
            planner_helpful = (
                planner_used and overall_performance_score >= self.PLANNER_HELPFUL_THRESHOLD
            )

            if not planner_available:
                reason = "이번 실행에는 AI Planner 결과가 없어(planner_available=False) 비교할 대상이 없음."
            elif planner_used and planner_helpful:
                reason = (
                    f"Planner Hint가 적용됐고 이번 실행 overall_performance_score="
                    f"{round(overall_performance_score, 4)}(기준 {self.PLANNER_HELPFUL_THRESHOLD} 이상) - "
                    "같은 실행 내 상관관계일 뿐 인과관계 증명은 아님."
                )
            elif planner_used:
                reason = (
                    f"Planner Hint가 적용됐지만 이번 실행 overall_performance_score="
                    f"{round(overall_performance_score, 4)}(기준 {self.PLANNER_HELPFUL_THRESHOLD} 미만)."
                )
            elif planner_rejected:
                reasons = [entry.get("reason", "") for entry in rejected_entries if entry.get("reason")]
                reason = "Planner Hint가 거부되어 기존 Engine 기본값을 사용함: " + "; ".join(reasons[:3])
            else:
                reason = "Planner 결과는 있었으나 적용/거부 판정이 기록되지 않음."

            return {
                "planner_used": planner_used,
                "planner_helpful": planner_helpful,
                "planner_rejected": planner_rejected,
                "planner_reason": reason,
            }
        except Exception as error:
            return {
                "planner_used": False,
                "planner_helpful": False,
                "planner_rejected": False,
                "planner_reason": f"planner_summary 계산 실패: {error}",
            }

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
            "planner_used": False,
            "planner_helpful": False,
            "planner_rejected": False,
            "planner_reason": "Performance Score 계산 실패로 Planner 적용 여부를 판정하지 않음.",
            "measurement_class": "internal_proxy",
            "performance_provenance": {
                "source": "pre_publish_quality_signals",
                "external_measured": False,
                "eligible_for_pattern_promotion": False,
            },
            "fallback_used": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }
