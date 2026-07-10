from typing import Any, Dict, Optional


class AnalyticsPredictor(object):
    """
    Analytics Engine - Internal Quality Trend (Sprint 13 rewrite).

    Sprint 12에서는 실제 SNS 지표(조회수/저장수/댓글/공유/CTR/팔로우전환/DM)가
    없는 상태에서 Performance/Audit Score 기반 "예측치"를 채워 넣었다
    (`is_measured: false`). 이는 존재하지 않는 성과 데이터를 만들어내는 것과
    같아 Sprint 13 원칙(Instagram/Meta API 없이 가짜 성과를 만들지 않는다)에
    위배된다.

    대신 이 클래스는 이미 실제로 로컬에서 계산된 값만 비교한다: 이번 실행의
    Performance Score/Audit Score를, `storage/performance_score/`에 실제로
    누적된 과거 평균과 비교해 품질이 개선/유지/하락 추세인지만 판단한다.
    전부 로컬에서 실제로 계산된 숫자이며, 외부 API도 필요 없고 허구의 값도 없다.
    """

    IMPROVEMENT_THRESHOLD = 0.02

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def compute(
        self,
        performance_score_result: Dict[str, Any],
        audit_result: Dict[str, Any],
        performance_statistics: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            return self._compute(performance_score_result or {}, audit_result or {}, performance_statistics or {})
        except Exception as error:
            return self._empty(reason=f"analytics_predictor 실패: {error}")

    def _compute(
        self,
        performance_score_result: Dict[str, Any],
        audit_result: Dict[str, Any],
        performance_statistics: Dict[str, Any],
    ) -> Dict[str, Any]:
        current_performance_score = float(performance_score_result.get("overall_performance_score", 0.0) or 0.0)
        current_audit_score = float(audit_result.get("audit_score", 0.0) or 0.0)

        average = performance_statistics.get("average", {})
        if not isinstance(average, dict):
            average = {}

        historical_average = average.get("overall_performance_score")
        sample_size = int(performance_statistics.get("total_runs", 0) or 0)

        if historical_average is None or sample_size < 2:
            return {
                "current_performance_score": round(current_performance_score, 4),
                "current_audit_score": round(current_audit_score, 4),
                "historical_average_performance_score": historical_average,
                "sample_size": sample_size,
                "quality_trend": "insufficient_history",
                "reason": "비교할 과거 실행 기록이 충분하지 않아(2회 미만) 추세를 판단하지 않음.",
            }

        historical_average = float(historical_average)
        delta = round(current_performance_score - historical_average, 4)

        if delta > self.IMPROVEMENT_THRESHOLD:
            trend = "improving"
        elif delta < -self.IMPROVEMENT_THRESHOLD:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "current_performance_score": round(current_performance_score, 4),
            "current_audit_score": round(current_audit_score, 4),
            "historical_average_performance_score": round(historical_average, 4),
            "sample_size": sample_size,
            "quality_trend": trend,
            "reason": (
                f"이번 실행 overall_performance_score={round(current_performance_score, 4)}, "
                f"과거 {sample_size}회 평균={round(historical_average, 4)} "
                f"(차이 {delta:+.4f}) 기준으로 '{trend}' 판정."
            ),
        }

    def _empty(self, reason: str) -> Dict[str, Any]:
        return {
            "current_performance_score": 0.0,
            "current_audit_score": 0.0,
            "historical_average_performance_score": None,
            "sample_size": 0,
            "quality_trend": "insufficient_history",
            "reason": reason,
        }
