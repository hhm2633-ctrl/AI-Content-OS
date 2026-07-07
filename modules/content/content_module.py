"""
Content Module
AI-Content-OS
"""

import json
from pathlib import Path

from modules.base_module import BaseModule


class ContentModule(BaseModule):
    def __init__(self, config):
        super().__init__(config)

        self.output_dir = Path("storage/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, research_result):
        print("Content Module Started")

        title = research_result.get("topic", "Untitled")

        body = [
            "1장: 문제 제기",
            "2장: 핵심 정보 설명",
            "3장: 사람들이 관심 가질 포인트",
            "4장: 요약 및 행동 유도"
        ]

        result = {
            "title": title,
            "body": body,
            "status": "draft_created"
        }

        output_path = self.output_dir / "content_result.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print("Content Result Saved:", output_path)

        return result