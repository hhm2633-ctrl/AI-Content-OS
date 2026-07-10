from typing import Any, Dict, List, Optional

from modules.trend_memory.trend_memory_storage import TrendMemoryStorage


class TrendMemoryInterface(object):
    """
    Trend Memory - Interface.

    Trend Collector/Topic Engine/Pattern Engine이 향후 "최근에 이미 쓴 조합인지"를
    조회할 수 있는 읽기 전용 API. 실패 시 빈 리스트를 반환한다.
    """

    def __init__(self, storage: Optional[TrendMemoryStorage] = None):
        self.storage = storage or TrendMemoryStorage()

    def get_recent(self, limit: int = 30) -> List[Dict[str, Any]]:
        try:
            return self.storage.load_recent(limit)
        except Exception as error:
            print(f"Trend Memory Interface get_recent Failed: {error}")
            return []
