import json
from typing import Any, Dict, List, Optional

from modules.knowledge_engine.knowledge_index import KnowledgeIndex
from modules.knowledge_engine.knowledge_storage import KnowledgeStorage


class KnowledgeInterface(object):
    """
    Knowledge Engine - Interface.

    Pattern Engine / Research / Content / Image Strategy / CardNews 등 다른
    Engine이 향후 재사용 가능한 Knowledge를 조회할 수 있도록 준비하는 읽기 전용
    API다.

    이번 Chapter(Knowledge Intelligence v1)에서는 API만 준비하고, 다른 Engine이
    실제로 이 인터페이스를 호출하도록 연결하지는 않는다. 연결은 각 Engine 쪽에서
    별도 Sprint로 명시적 승인 후 진행한다.

    모든 조회 메서드는 예외를 던지지 않고 실패 시 빈 결과(빈 리스트 / 빈 dict)를
    반환한다.
    """

    def __init__(
        self,
        storage: Optional[KnowledgeStorage] = None,
        index: Optional[KnowledgeIndex] = None,
    ):
        self.storage = storage or KnowledgeStorage()
        self.index = index or KnowledgeIndex()

    def get_by_type(self, knowledge_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            records = self.storage.load_all()
            matched = [
                record for record in records
                if isinstance(record, dict) and record.get("type") == knowledge_type
            ]
            matched.sort(key=self._overall_score, reverse=True)
            return matched[:limit]
        except Exception as error:
            print(f"Knowledge Interface get_by_type Failed: {error}")
            return []

    def get_by_keyword(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            index = self.index.load()
            ids = index.get("by_tag", {}).get(str(keyword), [])

            records = self.storage.load_all()
            records_by_id = {
                record.get("knowledge_id"): record
                for record in records
                if isinstance(record, dict)
            }

            matched = [records_by_id[knowledge_id] for knowledge_id in ids if knowledge_id in records_by_id]
            matched.sort(key=self._overall_score, reverse=True)
            return matched[:limit]
        except Exception as error:
            print(f"Knowledge Interface get_by_keyword Failed: {error}")
            return []

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Knowledge Search: title/content 텍스트에 query가 포함된 항목을 overall_score
        순으로 반환한다 (단순 substring 검색, 대소문자 무시). 실패 시 빈 리스트를 반환한다.
        """
        try:
            query_normalized = str(query or "").strip().lower()

            if not query_normalized:
                return []

            records = self.storage.load_all()
            matched = []

            for record in records:
                if not isinstance(record, dict):
                    continue

                try:
                    content_text = json.dumps(record.get("content", {}), ensure_ascii=False)
                except Exception:
                    content_text = str(record.get("content", ""))

                haystack = f"{record.get('title', '')} {content_text}".lower()

                if query_normalized in haystack:
                    matched.append(record)

            matched.sort(key=self._overall_score, reverse=True)
            return matched[:limit]
        except Exception as error:
            print(f"Knowledge Interface search Failed: {error}")
            return []

    def get_top_hooks(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_by_type("hook", limit)

    def get_top_ctas(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_by_type("cta", limit)

    def get_pattern_knowledge(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_by_type("pattern", limit)

    def get_layout_knowledge(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_by_type("layout", limit)

    def get_brand_knowledge(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_by_type("brand", limit)

    def get_prompt_pattern_knowledge(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_by_type("prompt_pattern", limit)

    def get_tool_knowledge(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_by_type("tool", limit)

    def get_image_strategy_knowledge(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_by_type("image_strategy", limit)

    def get_funnel_knowledge(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_by_type("funnel", limit)

    def get_workflow_knowledge(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_by_type("workflow", limit)

    def get_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_statistics()
        except Exception as error:
            print(f"Knowledge Interface get_statistics Failed: {error}")
            return {}

    def _overall_score(self, record: Dict[str, Any]) -> float:
        score = record.get("score") or {}

        try:
            return float(score.get("overall_score", 0.0))
        except Exception:
            return 0.0
