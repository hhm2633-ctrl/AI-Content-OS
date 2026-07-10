from typing import Any, Dict, Optional

from modules.performance_score.performance_score_storage import PerformanceScoreStorage


class PerformanceScoreInterface(object):
    """
    Performance Score - Interface.

    Audit Engine / Learning Engine / Analytics Engine이 최신 Performance Score와
    누적 통계를 조회할 수 있는 읽기 전용 API. 실패 시 빈 dict를 반환한다.
    """

    def __init__(self, storage: Optional[PerformanceScoreStorage] = None):
        self.storage = storage or PerformanceScoreStorage()

    def get_latest(self) -> Dict[str, Any]:
        try:
            return self.storage.load_latest()
        except Exception as error:
            print(f"Performance Score Interface get_latest Failed: {error}")
            return {}

    def get_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_statistics()
        except Exception as error:
            print(f"Performance Score Interface get_statistics Failed: {error}")
            return {}
