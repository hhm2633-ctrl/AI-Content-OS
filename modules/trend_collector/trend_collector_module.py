import json
from datetime import datetime
from pathlib import Path


class TrendCollectorModule:
    def __init__(self, config=None):
        self.config = config or {}
        self.output_dir = Path("storage/trends")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        print("Trend Collector Module Started")

        trend_sources = self.config.get("trend_sources", [])

        if not trend_sources:
            trend_sources = [
                "AI 자동화",
                "인스타 카드뉴스",
                "부업 자동화",
                "콘텐츠 자동화",
                "스마트스토어 자동화",
                "AI 이미지 생성",
                "블로그 자동화",
                "쇼츠 자동화"
            ]

        max_trends = self.config.get("topic", {}).get("max_trends", 10)
        selected_sources = trend_sources[:max_trends]

        trends = []

        for index, keyword in enumerate(selected_sources, start=1):
            trends.append({
                "rank": index,
                "keyword": keyword,
                "score": self._calculate_score(keyword, index),
                "source": "local_fallback_trend_source",
                "collected_at": datetime.now().isoformat()
            })

        result = {
            "status": "success",
            "message": "trend_collection_completed",
            "count": len(trends),
            "trends": trends
        }

        self._save_result(result)

        print("Trend Collector Module Finished")
        return result

    def _calculate_score(self, keyword, index):
        score = 100 - index

        bonus_keywords = [
            "AI",
            "자동화",
            "부업",
            "인스타",
            "카드뉴스",
            "콘텐츠",
            "쇼츠",
            "스마트스토어"
        ]

        for bonus in bonus_keywords:
            if bonus in keyword:
                score += 10

        return score

    def _save_result(self, result):
        file_path = self.output_dir / "trend_result.json"

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print(f"Trend Result Saved: {file_path}")