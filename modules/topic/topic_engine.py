import json
from datetime import datetime
from pathlib import Path


class TopicEngine:
    def __init__(self, config=None):
        self.config = config or {}
        self.output_dir = Path("storage/topics")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, trend_result=None):
        print("Topic Engine Started")

        trend_result = trend_result or {}
        trends = trend_result.get("trends", [])

        if not trends:
            selected_topic = self._fallback_topic()
        else:
            selected_topic = self._select_best_topic(trends)

        result = {
            "status": "success",
            "message": "topic_selection_completed",
            "selected_topic": selected_topic,
            "created_at": datetime.now().isoformat()
        }

        self._save_result(result)

        print("Topic Engine Finished")
        return result

    def _select_best_topic(self, trends):
        sorted_trends = sorted(
            trends,
            key=lambda item: item.get("score", 0),
            reverse=True
        )

        best = sorted_trends[0]

        keyword = best.get("keyword", "AI content automation")

        return {
            "keyword": keyword,
            "title": f"{keyword} 지금 시작해야 하는 이유",
            "angle": "초보자도 이해할 수 있는 실전형 카드뉴스",
            "target": "부업, 자동화, 콘텐츠 수익화에 관심 있는 사람",
            "reason": "현재 프로젝트 방향과 수익화 가능성이 높은 주제",
            "score": best.get("score", 0),
            "source": best.get("source", "unknown")
        }

    def _fallback_topic(self):
        default_keyword = (
            self.config
            .get("topic", {})
            .get("default_keyword", "AI content automation")
        )

        return {
            "keyword": default_keyword,
            "title": f"{default_keyword} 지금 시작해야 하는 이유",
            "angle": "fallback 기반 안전 주제",
            "target": "AI 자동화 입문자",
            "reason": "트렌드 수집 실패 시 workflow 중단 방지",
            "score": 50,
            "source": "fallback"
        }

    def _save_result(self, result):
        file_path = self.output_dir / "02_topic_result.json"

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print(f"Topic Result Saved: {file_path}")