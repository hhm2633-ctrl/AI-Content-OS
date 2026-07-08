import json
from pathlib import Path
from typing import Any, Dict, List

from modules.base_module import BaseModule


class PublishingModule(BaseModule):
    def __init__(self, config=None):
        super().__init__(config)

        self.publishing_dir = Path("storage/publishing")
        self.publishing_dir.mkdir(parents=True, exist_ok=True)

    def _extract_card_paths(self, card_news_result: Dict[str, Any]) -> List[str]:
        card_paths = []

        if isinstance(card_news_result, dict):
            cards = card_news_result.get("cards", [])

            if isinstance(cards, list):
                for item in cards:
                    if isinstance(item, dict):
                        card_path = item.get("card_path")

                        if card_path:
                            card_paths.append(card_path)

        return card_paths

    def _create_caption(self) -> str:
        caption = (
            "오늘의 AI 카드뉴스\n\n"
            "AI-Content-OS가 자동으로 생성한 카드뉴스입니다.\n\n"
            "#AI #자동화 #콘텐츠자동화 #카드뉴스 #인스타그램 #부업 #수익화"
        )

        return caption

    def run(self, card_news_result: Dict[str, Any]) -> Dict[str, Any]:
        print("Publishing Module Started")

        card_paths = self._extract_card_paths(card_news_result)
        caption = self._create_caption()

        result = {
            "module": "PublishingModule",
            "status": "publishing_ready",
            "platform": "instagram_manual_upload",
            "card_count": len(card_paths),
            "card_paths": card_paths,
            "caption": caption,
            "next_action": "카드뉴스 이미지를 확인한 뒤 인스타그램에 수동 업로드",
        }

        result_path = self.publishing_dir / "publishing_result.json"
        caption_path = self.publishing_dir / "caption.txt"

        with open(result_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        with open(caption_path, "w", encoding="utf-8") as file:
            file.write(caption)

        print(f"Publishing Result Saved: {result_path}")
        print(f"Caption Saved: {caption_path}")
        print("Publishing Module Finished")

        return result