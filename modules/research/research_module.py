import json
from datetime import datetime
from pathlib import Path


class ResearchModule:
    def __init__(self, config=None):
        self.config = config or {}
        self.output_dir = Path("storage/research")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, topic_result=None):
        print("Research Module Started")

        topic_result = topic_result or {}
        selected_topic = topic_result.get("selected_topic", {})

        keyword = selected_topic.get("keyword", "AI content automation")
        title = selected_topic.get("title", f"{keyword} 카드뉴스 주제")

        result = {
            "status": "success",
            "message": "research_completed",
            "keyword": keyword,
            "title": title,
            "summary": f"{keyword} 주제는 카드뉴스, 블로그, 쇼츠로 확장하기 좋은 자동화 콘텐츠 주제입니다.",
            "key_points": [
                f"{keyword}는 초보자도 관심을 가질 수 있는 주제입니다.",
                "카드뉴스 형식으로 짧고 명확하게 전달하기 좋습니다.",
                "인스타그램 다계정 운영과 연결하기 좋습니다.",
                "향후 블로그, 쇼츠, 상품 연결 콘텐츠로 확장할 수 있습니다."
            ],
            "topic_angle": selected_topic.get("angle", ""),
            "target": selected_topic.get("target", ""),
            "source": selected_topic.get("source", "local"),
            "created_at": datetime.now().isoformat()
        }

        self._save_result(result)

        print("Research Module Finished")
        return result

    def _save_result(self, result):
        file_path = self.output_dir / "research_result.json"

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print(f"Research Result Saved: {file_path}")