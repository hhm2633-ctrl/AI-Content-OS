from typing import Any, Dict, Optional

from modules.analytics_engine.analytics_storage import AnalyticsStorage


class AnalyticsInterface(object):
    """
    Analytics Engine - Interface (Skeleton).

    Learning Engine/Audit Engine이 향후 실제 성과 데이터를 조회할 수 있도록
    준비된 읽기 전용 API. 실패 시 빈 dict를 반환한다.
    """

    def __init__(self, storage: Optional[AnalyticsStorage] = None):
        self.storage = storage or AnalyticsStorage()

    def get_latest(self) -> Dict[str, Any]:
        try:
            return self.storage.load_latest()
        except Exception as error:
            print(f"Analytics Interface get_latest Failed: {error}")
            return {}

    def get_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_statistics()
        except Exception as error:
            print(f"Analytics Interface get_statistics Failed: {error}")
            return {}
