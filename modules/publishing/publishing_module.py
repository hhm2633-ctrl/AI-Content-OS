import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from modules.base_module import BaseModule
except ImportError:
    from src.base_module import BaseModule


class PublishingModule(BaseModule):
    """
    PublishingModule

    역할:
    - 카드뉴스 결과물을 실제 발행 전 단계로 정리
    - caption, hashtags, 파일 경로를 JSON으로 저장
    - 나중에 Instagram, 블로그, 쇼츠 업로드 모듈로 확장 가능
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.output_dir = (
            self.config.get("output_dir")
            or self.config.get("publishing_output_dir")
            or os.path.join("storage", "publishing")
        )

        os.makedirs(self.output_dir, exist_ok=True)

    def run(self, card_news_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        print("Publishing Module Started")

        card_news_result = card_news_result or {}

        title = card_news_result.get("title", "AI Content OS")
        card_news_files = card_news_result.get("card_news_files", [])
        caption = card_news_result.get("caption", "")
        hashtags = card_news_result.get("hashtags", [])

        publishing_result = {
            "title": title,
            "platform": "manual_ready",
            "card_news_files": card_news_files,
            "caption": caption,
            "hashtags": hashtags,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "publishing_ready",
        }

        file_path = os.path.join(self.output_dir, "publishing_result.json")

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(publishing_result, file, ensure_ascii=False, indent=2)

        publishing_result["result_file"] = file_path

        print(f"Publishing Result Saved: {file_path}")
        print("Publishing Module Finished")

        return publishing_result