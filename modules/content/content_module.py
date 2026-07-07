import json
from pathlib import Path

from modules.base_module import BaseModule


class ContentModule(BaseModule):

    def __init__(self):
        super().__init__("Content")

    def run(self, input_data=None):

        print()
        print("========== Content Module ==========")
        print("Generating content draft...")

        topic = input_data.get("topic", "No topic") if input_data else "No topic"

        result = {
            "title": f"{topic}에 대한 카드뉴스 초안",
            "body": [
                "1장: 문제 제기",
                "2장: 핵심 정보 설명",
                "3장: 사람들이 관심 가질 포인트",
                "4장: 요약 및 행동 유도"
            ],
            "status": "draft_created"
        }

        output_dir = Path("storage/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "content_result.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        print(f"Saved : {output_file}")

        print("Content Draft Complete")
        print()

        return result