import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.base_module import BaseModule


class TrendCollectorModule(BaseModule):
    """
    TrendCollectorModule

    역할:
    - 오늘 사용할 주제 후보를 수집한다.
    - Day 2 MVP에서는 안정적인 fallback 데이터를 먼저 사용한다.
    - 이후 뉴스, 커뮤니티, 검색 트렌드 수집기로 교체 가능하게 만든다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        self.config = config or {}
        self.trend_dir = Path("storage/trends")
        self.trend_dir.mkdir(parents=True, exist_ok=True)

    def _get_fallback_topics(self) -> List[Dict[str, Any]]:
        return [
            {
                "title": "AI로 인스타 카드뉴스 자동화하는 방법",
                "source": "fallback",
                "source_name": "AI-Content-OS",
                "url": "",
                "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "summary": "AI를 활용해 카드뉴스 제작 시간을 줄이는 방법",
                "keywords": ["AI", "카드뉴스", "자동화", "인스타그램"],
                "raw_score": 80,
                "status": "collected",
            },
            {
                "title": "초보자가 부업 콘텐츠를 자동으로 만드는 구조",
                "source": "fallback",
                "source_name": "AI-Content-OS",
                "url": "",
                "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "summary": "콘텐츠 부업을 시작할 때 자동화 구조를 먼저 만드는 방법",
                "keywords": ["부업", "콘텐츠", "자동화", "수익화"],
                "raw_score": 78,
                "status": "collected",
            },
            {
                "title": "하루 1개 카드뉴스를 꾸준히 만드는 시스템",
                "source": "fallback",
                "source_name": "AI-Content-OS",
                "url": "",
                "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "summary": "지속 가능한 콘텐츠 생산 루틴과 자동화 흐름",
                "keywords": ["콘텐츠", "루틴", "카드뉴스", "자동화"],
                "raw_score": 76,
                "status": "collected",
            },
        ]

    def run(self) -> Dict[str, Any]:
        print("Trend Collector Module Started")

        raw_topics = self._get_fallback_topics()

        result = {
            "module": "TrendCollectorModule",
            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_count": 1,
            "raw_topics": raw_topics,
            "status": "trend_collection_completed",
        }

        output_path = self.trend_dir / "trend_raw_result.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print(f"Trend Raw Result Saved: {output_path}")
        print("Trend Collector Module Finished")

        return result