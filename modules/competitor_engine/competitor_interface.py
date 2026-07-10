from typing import Any, Dict, List, Optional

from modules.competitor_engine.competitor_storage import CompetitorStorage


class CompetitorInterface(object):
    """
    Competitor Engine - Interface.

    Audit Engine(Competitor Comparison 단계)/Content/Pattern Engine이 향후
    최신 경쟁 프로필, 계정별 프로필, 통계를 조회할 수 있는 읽기 전용 API.
    실패 시 빈 dict/리스트를 반환한다.
    """

    def __init__(self, storage: Optional[CompetitorStorage] = None):
        self.storage = storage or CompetitorStorage()

    def get_profile(self) -> Dict[str, Any]:
        try:
            return self.storage.load_latest()
        except Exception as error:
            print(f"Competitor Interface get_profile Failed: {error}")
            return {}

    def get_account_profiles(self, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            profiles = self.storage.load_profiles()

            if priority:
                profiles = [item for item in profiles if item.get("priority") == priority]

            return profiles
        except Exception as error:
            print(f"Competitor Interface get_account_profiles Failed: {error}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_statistics()
        except Exception as error:
            print(f"Competitor Interface get_statistics Failed: {error}")
            return {}
