from datetime import datetime
from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.analytics_engine.analytics_history import AnalyticsHistory
from modules.analytics_engine.analytics_interface import AnalyticsInterface
from modules.analytics_engine.analytics_predictor import AnalyticsPredictor
from modules.analytics_engine.analytics_storage import AnalyticsStorage
from modules.common.metadata_standard import (
    SOURCE_ESTIMATED,
    SOURCE_HISTORICAL,
    SOURCE_LOCAL_QUALITY,
    build_standard_metadata,
)
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
        sample_size = trend_result.get("sample_size", 0)

        result = {
            "status": "analytics_completed",
            "current_performance_score": trend_result.get("current_performance_score", 0.0),
            "current_audit_score": trend_result.get("current_audit_score", 0.0),
            "historical_average_performance_score": trend_result.get("historical_average_performance_score"),
            "sample_size": sample_size,
            "quality_trend": trend_result.get("quality_trend", "insufficient_history"),
            "reason": trend_result.get("reason", ""),
            "fallback_used": False,
            # Analytics 검증 (Sprint 16-0): 실제 측정값/로컬 품질/추정값을 명확히
            # 구분한다 - 이 필드들이 실제 SNS 실측처럼 보이면 안 된다는 Sprint 13
            # Offline-First 원칙을 Metadata 수준에서 다시 한번 강제한다.
            "measurement_metadata": {
                # 이번 실행에서 실제로 계산된 내부 품질 대리 지표 - 실제 외부
                # 성과 지표가 아니다.
                "current_performance_score": build_standard_metadata(
                    source=SOURCE_LOCAL_QUALITY,
                    confidence=None,
                    note="Performance Score Engine이 이번 실행에서 실제로 계산한 내부 품질 점수 (실제 SNS 성과 아님).",
                ),
                "current_audit_score": build_standard_metadata(
                    source=SOURCE_LOCAL_QUALITY,
                    confidence=None,
                    note="Audit Engine이 이번 실행에서 실제로 계산한 내부 품질 점수 (실제 SNS 성과 아님).",
                ),
                # storage/performance_score/에 실제로 누적된 과거 평균 - 이번
                # 실행 값이 아니다.
                "historical_average_performance_score": build_standard_metadata(
                    source=SOURCE_HISTORICAL,
                    confidence=None,
                    sample_size=sample_size,
                    note="storage/performance_score/performance_score_statistics.json에 실제로 누적된 과거 평균.",
                ),
                # 위 두 실측/이력 값을 비교해 추론한 판단 - 그 자체는 측정값이
                # 아니라 추정치다.
                "quality_trend": build_standard_metadata(
                    source=SOURCE_ESTIMATED,
                    confidence=None,
                    sample_size=sample_size,
                    note="local_quality 값과 historical 평균을 비교해 추론한 추세 - 실측값이 아님.",
                ),
            },
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
            "measurement_metadata": {
                "current_performance_score": build_standard_metadata(
                    source=SOURCE_LOCAL_QUALITY, confidence=None, note="계산 실패로 안전한 기본값(0.0) 사용."
                ),
                "current_audit_score": build_standard_metadata(
                    source=SOURCE_LOCAL_QUALITY, confidence=None, note="계산 실패로 안전한 기본값(0.0) 사용."
                ),
                "historical_average_performance_score": build_standard_metadata(
                    source=SOURCE_HISTORICAL, confidence=None, sample_size=0, note="계산 실패로 이력을 읽지 못함."
                ),
                "quality_trend": build_standard_metadata(
                    source=SOURCE_ESTIMATED, confidence=None, sample_size=0, note="계산 실패로 추세를 판단하지 않음."
                ),
            },
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
