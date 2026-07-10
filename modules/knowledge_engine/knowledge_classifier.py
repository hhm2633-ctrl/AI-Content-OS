from typing import Any, Dict, List, Optional


class KnowledgeClassifier(object):
    """
    Knowledge Engine - Classifier.

    추출된 Knowledge 항목에 category/cluster/tags를 부여해 향후 검색과 색인이
    가능한 형태로 만든다. 분류에 필요한 topic_intelligence가 없거나 개별 항목
    분류가 실패해도 안전한 기본값을 채워 항목 자체는 유지한다 (항목 유실 없음).
    """

    DEFAULT_CATEGORY = "trend"
    DEFAULT_CLUSTER = "general_trend_cluster"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def classify(
        self,
        items: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        context = context if isinstance(context, dict) else {}
        pattern_result = context.get("pattern_result") or {}
        topic_intelligence = pattern_result.get("topic_intelligence") or {}

        category = str(topic_intelligence.get("category", "") or self.DEFAULT_CATEGORY)
        cluster = str(topic_intelligence.get("cluster", "") or self.DEFAULT_CLUSTER)
        keywords = topic_intelligence.get("keywords", [])

        if not isinstance(keywords, list):
            keywords = []

        classified = []

        for item in items or []:
            try:
                classified.append(self._classify_item(item, category, cluster, keywords))
            except Exception as error:
                print(f"Knowledge Classifier Item Failed: {error}")
                safe_item = dict(item) if isinstance(item, dict) else {}
                safe_item.setdefault("category", self.DEFAULT_CATEGORY)
                safe_item.setdefault("cluster", self.DEFAULT_CLUSTER)
                safe_item.setdefault("tags", [])
                classified.append(safe_item)

        return classified

    def _classify_item(
        self,
        item: Dict[str, Any],
        category: str,
        cluster: str,
        keywords: List[Any],
    ) -> Dict[str, Any]:
        item = dict(item)

        item["category"] = category
        item["cluster"] = cluster

        tags = [str(item.get("type", ""))]
        tags.extend(str(keyword) for keyword in keywords[:5] if keyword)

        item["tags"] = sorted({tag for tag in tags if tag})

        return item
