from typing import Any, Dict, List


class TopicCluster:
    """
    카테고리를 더 구체적인 콘텐츠 클러스터로 세분화한다.
    알 수 없는 카테고리는 안전하게 general_trend_cluster로 대체한다.
    """

    CATEGORY_CLUSTER_MAP = {
        "AI": "ai_automation_cluster",
        "부업": "side_income_cluster",
        "경제": "living_cost_cluster",
        "생활": "daily_life_cluster",
        "쇼핑": "shopping_saving_cluster",
        "트렌드": "general_trend_cluster",
    }

    def __init__(self, config=None):
        self.config = config or {}

    def assign_cluster(
        self,
        category: str,
        keywords: List[str],
        selected_topic: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            cluster = self.CATEGORY_CLUSTER_MAP.get(str(category), "general_trend_cluster")
            reason = f"category '{category}' 기준으로 '{cluster}'에 배정함."

            return {"cluster": cluster, "reason": reason}
        except Exception:
            return {
                "cluster": "general_trend_cluster",
                "reason": "클러스터 계산 실패로 기본 클러스터로 대체함.",
            }
