from typing import Any, Dict, List, Optional


class LearningPerformanceAnalyzer(object):
    """
    Learning Engine 확장 (Instagram Intelligence Phase 2) - Performance History
    분석.

    storage/history/content_performance_history.json에 이미 누적된 quality_score를
    정렬/평균만 한다 - 새로운 선택 알고리즘이 아니라 기존에 다른 Engine이 이미
    계산해 둔 값에 대한 순수 집계다. 실패해도 예외를 던지지 않고 빈 결과를
    반환한다.
    """

    RECENT_WINDOW = 30
    TOP_N = 3
    WORST_N = 3

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def analyze(self, records: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        try:
            return self._analyze(records or [])
        except Exception as error:
            return {
                "sample_size": 0,
                "average_quality_score": None,
                "top_performance": [],
                "worst_performance": [],
                "top_performing_pattern": "",
                "weakest_pattern": "",
                "reason": f"performance history 분석 실패: {error}",
            }

    def _analyze(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        recent = [record for record in records if isinstance(record, dict)][-self.RECENT_WINDOW:]
        scored = [
            record for record in recent
            if isinstance(record.get("quality_score"), (int, float))
        ]

        if not scored:
            return {
                "sample_size": len(recent),
                "average_quality_score": None,
                "top_performance": [],
                "worst_performance": [],
                "top_performing_pattern": "",
                "weakest_pattern": "",
                "reason": "quality_score가 기록된 History가 아직 없어 계산하지 않음.",
            }

        ranked = sorted(scored, key=lambda record: record["quality_score"], reverse=True)
        average_quality_score = round(sum(record["quality_score"] for record in scored) / len(scored), 4)

        top_performance = ranked[: self.TOP_N]
        worst_performance = list(reversed(ranked[-self.WORST_N:]))

        top_performing_pattern = str(top_performance[0].get("pattern", "")) if top_performance else ""
        weakest_pattern = str(worst_performance[0].get("pattern", "")) if worst_performance else ""

        return {
            "sample_size": len(scored),
            "average_quality_score": average_quality_score,
            "top_performance": top_performance,
            "worst_performance": worst_performance,
            "top_performing_pattern": top_performing_pattern,
            "weakest_pattern": weakest_pattern,
            "reason": (
                f"최근 {len(scored)}건 기준 평균 quality_score={average_quality_score}, "
                f"top_performing_pattern='{top_performing_pattern}', weakest_pattern='{weakest_pattern}'."
            ),
        }
