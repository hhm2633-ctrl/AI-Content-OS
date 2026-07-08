import json
from datetime import datetime
from pathlib import Path


class TopicEngineModule:
    def __init__(self, config=None):
        self.config = config or {}
        self.output_dir = Path("storage/topics")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, trend_result=None):
        print("Topic Engine Module Started")

        trend_result = trend_result or {}
        trend_selected_topic = trend_result.get("selected_topic", {})
        trends = trend_result.get("trends", [])

        if trend_selected_topic:
            selected_topic = self._from_trend_selected_topic(trend_selected_topic)
        elif trends:
            selected_topic = self._select_best_topic(trends)
        else:
            selected_topic = self._fallback_topic()

        result = {
            "status": "success",
            "message": "topic_selection_completed",
            "selected_topic": selected_topic,
            "created_at": datetime.now().isoformat()
        }

        self._save_result(result)

        print("Topic Engine Module Finished")
        return result

    def _from_trend_selected_topic(self, trend_selected_topic):
        title = trend_selected_topic.get("title", "AI content automation")

        return {
            "keyword": title,
            "title": f"{title} 지금 시작해야 하는 이유",
            "angle": "quality_score 기반으로 자동 선택된 카드뉴스 주제",
            "target": "AI 자동화와 콘텐츠 운영에 관심 있는 사람",
            "reason": trend_selected_topic.get("picked_reason", ""),
            "score": trend_selected_topic.get("quality_score", 0),
            "quality_score": trend_selected_topic.get("quality_score", 0),
            "selection_reason": trend_selected_topic.get("selection_reason", ""),
            "collection_method": trend_selected_topic.get("collection_method", ""),
            "source": trend_selected_topic.get("source", "unknown")
        }

    def _select_best_topic(self, trends):
        sorted_trends = sorted(
            trends,
            key=lambda item: item.get("score", 0),
            reverse=True
        )

        best_trend = sorted_trends[0]
        keyword = best_trend.get("keyword", "AI content automation")

        return {
            "keyword": keyword,
            "title": f"{keyword} 지금 시작해야 하는 이유",
            "angle": "초보자도 이해할 수 있는 실전형 카드뉴스",
            "target": "부업, 자동화, 콘텐츠 수익화에 관심 있는 사람",
            "reason": "현재 프로젝트 방향과 수익화 가능성이 높은 주제",
            "score": best_trend.get("score", 0),
            "source": best_trend.get("source", "unknown")
        }

    def _fallback_topic(self):
        keyword = self.config.get("topic", {}).get(
            "default_keyword",
            "AI content automation"
        )

        return {
            "keyword": keyword,
            "title": f"{keyword} 지금 시작해야 하는 이유",
            "angle": "fallback 기반 안전 주제",
            "target": "AI 자동화 입문자",
            "reason": "트렌드 수집 실패 시 workflow 중단 방지",
            "score": 50,
            "source": "fallback"
        }

    def _save_result(self, result):
        file_path = self.output_dir / "topic_result.json"

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print(f"Topic Result Saved: {file_path}")
