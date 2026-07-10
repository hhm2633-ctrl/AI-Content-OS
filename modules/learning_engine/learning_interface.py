from typing import Any, Dict, List, Optional

from modules.learning_engine.learning_storage import LearningStorage


class LearningInterface(object):
    """
    Learning Engine - Interface.

    Pattern Engine/Content/CardNews가 향후 "반복적으로 검증된 고성과 Hook/CTA/
    Pattern/Layout/Brand"를 조회할 수 있는 읽기 전용 API. 실패 시 빈 리스트를 반환한다.
    """

    def __init__(self, storage: Optional[LearningStorage] = None):
        self.storage = storage or LearningStorage()

    def get_top_memory(self, knowledge_type: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            records = self.storage.load_memory()

            if knowledge_type:
                records = [record for record in records if record.get("type") == knowledge_type]

            records.sort(key=lambda record: float(record.get("memory_score", 0.0)), reverse=True)
            return records[:limit]
        except Exception as error:
            print(f"Learning Interface get_top_memory Failed: {error}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_statistics()
        except Exception as error:
            print(f"Learning Interface get_statistics Failed: {error}")
            return {}
