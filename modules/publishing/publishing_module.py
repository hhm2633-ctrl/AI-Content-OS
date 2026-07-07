"""
Publishing Module
AI-Content-OS

카드뉴스 결과물을 실제 업로드 직전 상태로 정리한다.
현재 단계에서는 Instagram API를 호출하지 않고,
게시 준비용 JSON 파일을 생성한다.
"""

import json
from pathlib import Path

from modules.base_module import BaseModule


class PublishingModule(BaseModule):
    def __init__(self, config):
        super().__init__(config)

        self.output_dir = Path("storage/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, content_result, card_news_result):
        print("Publishing Module Started")

        title = content_result.get("title", "")
        body = content_result.get("body", [])
        card_news = card_news_result.get("card_news", [])

        caption_lines = []
        caption_lines.append(title)
        caption_lines.append("")
        caption_lines.extend(body)
        caption_lines.append("")
        caption_lines.append("#AI #콘텐츠자동화 #카드뉴스 #인스타그램 #부업")

        result = {
            "platform": "instagram",
            "title": title,
            "caption": "\n".join(caption_lines),
            "images": [item.get("card_news_path") for item in card_news],
            "status": "publishing_ready"
        }

        output_path = self.output_dir / "publishing_result.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print("Publishing Result Saved:", output_path)

        return result