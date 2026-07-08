import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.base_module import BaseModule


class TopicEngineModule(BaseModule):
    """
    TopicEngineModule

    역할
    - TrendCollector 결과를 점수화
    - 최종 주제 선택
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        self.config = config or {}

        self.topic_dir = Path("storage/topics")
        self.topic_dir.mkdir(parents=True, exist_ok=True)

    def _score_topic(self, topic: Dict[str, Any]) -> int:
        return int(topic.get("raw_score", 50))

    def run(self, trend_result: Dict[str, Any]) -> Dict[str, Any]:
        print("Topic Engine Started")

        selected_topics = []

        for item in trend_result.get("raw_topics", []):
            score = self._score_topic(item)

            selected_topics.append({
                "topic": item["title"],
                "category": "AI",
                "reason": "Highest Score",
                "score": score,
                "risk_level": "low",
                "content_angle": item.get("summary", ""),
                "target_account": "account_1",
                "status": "selected",
            })

        selected_topics.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        result = {
            "module": "TopicEngineModule",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "selected_topics": selected_topics[:3],
            "status": "topic_selection_completed",
        }

        output = self.topic_dir / "topic_selection_result.json"

        with open(output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"Topic Result Saved : {output}")
        print("Topic Engine Finished")

        return result