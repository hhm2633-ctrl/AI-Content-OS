from datetime import datetime
from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.analytics_engine.analytics_history import AnalyticsHistory
from modules.analytics_engine.analytics_interface import AnalyticsInterface
from modules.analytics_engine.analytics_predictor import AnalyticsPredictor
from modules.analytics_engine.analytics_storage import AnalyticsStorage
from modules.performance_score.performance_score_interface import PerformanceScoreInterface


class AnalyticsEngineModule(BaseModule):
    """
    Analytics Engine v2 (Sprint 13, Offline-First).

    실제 Instagram Graph API 등 SNS 성과 데이터 연동은 절대 시도하지 않는다.
    Sprint 12의 조회수/저장수/댓글/공유/CTR/팔로우전환/DM "예측치"는 존재하지
    않는 성과를 만들어내는 것과 같아 제거했다.

    대신 이미 로컬에서 실제로 계산되는 Performance Score의 누적 이력
    (`storage/performance_score/performance_score_statistics.json`, 진짜 데이터)과
    이번 실행의 Performance/Audit Score를 비교해 내부 품질이 개선/유지/하락
    추세인지만 판단한다. 외부 API도, 허구의 값도 없다.

    이 Engine은 외부 네트워크/LLM을 호출하지 않으며, 실패 시 추세 없음
    (`insufficient_history`)으로 안전하게 처리한다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.predictor = AnalyticsPredictor(self.config)
        self.storage = AnalyticsStorage()
        self.history = AnalyticsHistory()
        self.interface = AnalyticsInterface(self.storage)

        # Performance Score Engine의 Interface를 재사용해 실제 누적 통계를 읽는다.
        self.performance_score_interface = PerformanceScoreInterface()

    def run(
        self,
        performance_score_result: Optional[Dict[str, Any]] = None,
        audit_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Analytics Engine Module Started")

        try:
            result = self._build_result(performance_score_result or {}, audit_result or {})
        except Exception as error:
            print(f"Analytics Engine Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"analytics_engine_exception: {error}")

        print("Analytics Engine Module Finished")
        return result

    def _build_result(
        self,
        performance_score_result: Dict[str, Any],
        audit_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        performance_statistics = self.performance_score_interface.get_statistics()

        trend_result = self.predictor.compute(performance_score_result, audit_result, performance_statistics)

        result = {
            "status": "analytics_completed",
            "current_performance_score": trend_result.get("current_performance_score", 0.0),
            "current_audit_score": trend_result.get("current_audit_score", 0.0),
            "historical_average_performance_score": trend_result.get("historical_average_performance_score"),
            "sample_size": trend_result.get("sample_size", 0),
            "quality_trend": trend_result.get("quality_trend", "insufficient_history"),
            "reason": trend_result.get("reason", ""),
            "fallback_used": False,
            "created_at": datetime.now().isoformat(),
        }

        self.storage.save(result)
        self.storage.update_statistics(result.get("quality_trend", "insufficient_history"))
        self.history.record(result)

        return result

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        result = {
            "status": "analytics_completed",
            "current_performance_score": 0.0,
            "current_audit_score": 0.0,
            "historical_average_performance_score": None,
            "sample_size": 0,
            "quality_trend": "insufficient_history",
            "reason": reason,
            "fallback_used": True,
            "created_at": datetime.now().isoformat(),
        }

        try:
            self.storage.save(result)
            self.storage.update_statistics(result.get("quality_trend", "insufficient_history"))
            self.history.record(result)
        except Exception as error:
            print(f"Analytics Fallback Persist Failed: {error}")

        return result
