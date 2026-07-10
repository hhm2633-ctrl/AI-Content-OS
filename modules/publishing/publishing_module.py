import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from modules.base_module import BaseModule


class PublishingModule(BaseModule):
    def __init__(self, config=None):
        super().__init__(config)

        self.config = config or {}
        self.publishing_dir = Path("storage/publishing")
        self.publishing_dir.mkdir(parents=True, exist_ok=True)

        self.publishing_config = self._load_publishing_config()

    def _load_publishing_config(self) -> Dict[str, Any]:
        config_path = Path("config/publishing.json")

        if not config_path.exists():
            return self._fallback_publishing_config()

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return self._fallback_publishing_config()

    def _fallback_publishing_config(self) -> Dict[str, Any]:
        return {
            "platform": "instagram",
            "upload_mode": "manual",
            "default_account": "account_01",
            "accounts": [
                {
                    "account_id": "account_01",
                    "account_name": "AI 카드뉴스 계정",
                    "enabled": True
                }
            ],
            "schedule": {
                "enabled": False,
                "default_time": "09:00"
            },
            "hashtags": [
                "#AI",
                "#자동화",
                "#콘텐츠자동화",
                "#카드뉴스",
                "#인스타그램",
                "#부업",
                "#수익화"
            ]
        }

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

    def _extract_title(self, card_news_result: Dict[str, Any]) -> str:
        if isinstance(card_news_result, dict):
            title = card_news_result.get("title")

            if title:
                return str(title)

        return "오늘의 AI 카드뉴스"

    def _create_caption(self, title: str) -> str:
        caption = (
            f"{title}\n\n"
            "AI-Content-OS가 자동으로 생성한 카드뉴스입니다.\n\n"
            "저장해두고 하나씩 따라가면 콘텐츠 자동화 흐름을 이해할 수 있습니다.\n\n"
            "더 좋은 자동화 구조를 계속 테스트하고 개선합니다."
        )

        return caption

    def _create_hashtags(self) -> List[str]:
        hashtags = self.publishing_config.get("hashtags", [])

        if not hashtags:
            hashtags = [
                "#AI",
                "#자동화",
                "#콘텐츠자동화",
                "#카드뉴스",
                "#인스타그램",
                "#부업",
                "#수익화"
            ]

        clean_hashtags = []

        for tag in hashtags:
            tag = str(tag).strip()

            if not tag:
                continue

            if not tag.startswith("#"):
                tag = "#" + tag

            clean_hashtags.append(tag)

        return clean_hashtags[:20]

    def _create_full_caption(self, caption: str, hashtags: List[str]) -> str:
        return caption + "\n\n" + " ".join(hashtags)

    def _get_default_account(self) -> Dict[str, Any]:
        accounts = self.publishing_config.get("accounts", [])

        if isinstance(accounts, list):
            for account in accounts:
                if account.get("enabled", True):
                    return account

        return {
            "account_id": "account_01",
            "account_name": "AI 카드뉴스 계정",
            "enabled": True
        }

    def _resolve_image_sourcing_status(self, card_news_result: Dict[str, Any]) -> Dict[str, Any]:
        status = card_news_result.get("image_sourcing_status") if isinstance(card_news_result, dict) else None

        if isinstance(status, dict) and status:
            return status

        return {
            "manual_image_required": False,
            "recommended_source": "",
            "real_image_used_count": 0,
            "checklist": [],
            "reason": "card_news_result에 image_sourcing_status가 없어 수동 이미지 체크리스트를 생략함.",
        }

    def _create_publish_queue(
        self,
        title: str,
        card_paths: List[str],
        caption: str,
        hashtags: List[str],
        image_sourcing_status: Dict[str, Any],
    ) -> Dict[str, Any]:
        account = self._get_default_account()
        schedule = self.publishing_config.get("schedule", {})
        manual_image_required = bool(image_sourcing_status.get("manual_image_required", False))

        next_action = "카드뉴스 이미지와 캡션을 확인한 뒤 인스타그램에 수동 업로드"
        if manual_image_required:
            next_action = (
                "manual_image_required 체크리스트(image_checklist)를 먼저 완료한 뒤, "
                "카드뉴스 이미지와 캡션을 확인하고 인스타그램에 수동 업로드"
            )

        queue_item = {
            "queue_id": f"publish_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "platform": self.publishing_config.get("platform", "instagram"),
            "upload_mode": self.publishing_config.get("upload_mode", "manual"),
            "account_id": account.get("account_id", "account_01"),
            "account_name": account.get("account_name", "AI 카드뉴스 계정"),
            "title": title,
            "card_paths": card_paths,
            "caption": caption,
            "hashtags": hashtags,
            "full_caption": self._create_full_caption(caption, hashtags),
            "schedule_enabled": schedule.get("enabled", False),
            "scheduled_time": schedule.get("default_time", "09:00"),
            "status": "ready_for_manual_upload",
            "manual_image_required": manual_image_required,
            "image_checklist": image_sourcing_status.get("checklist", []),
            "created_at": datetime.now().isoformat(),
            "next_action": next_action,
        }

        return {
            "status": "queue_ready",
            "count": 1,
            "items": [queue_item]
        }

    def _save_json(self, path: Path, data: Dict[str, Any]):
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _save_text(self, path: Path, text: str):
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)

    def run(self, card_news_result: Dict[str, Any]) -> Dict[str, Any]:
        print("Publishing Module Started")

        title = self._extract_title(card_news_result)
        card_paths = self._extract_card_paths(card_news_result)
        caption = self._create_caption(title)
        hashtags = self._create_hashtags()
        full_caption = self._create_full_caption(caption, hashtags)
        image_sourcing_status = self._resolve_image_sourcing_status(card_news_result)

        publish_queue = self._create_publish_queue(
            title=title,
            card_paths=card_paths,
            caption=caption,
            hashtags=hashtags,
            image_sourcing_status=image_sourcing_status,
        )

        manual_image_required = bool(image_sourcing_status.get("manual_image_required", False))
        next_action = "카드뉴스 이미지와 캡션을 확인한 뒤 인스타그램에 수동 업로드"
        if manual_image_required:
            next_action = (
                "manual_image_required 체크리스트를 먼저 완료한 뒤, "
                "카드뉴스 이미지와 캡션을 확인하고 인스타그램에 수동 업로드"
            )

        result = {
            "module": "PublishingModule",
            "status": "publishing_ready",
            "platform": self.publishing_config.get("platform", "instagram"),
            "upload_mode": self.publishing_config.get("upload_mode", "manual"),
            "card_count": len(card_paths),
            "card_paths": card_paths,
            "caption": caption,
            "hashtags": hashtags,
            "full_caption": full_caption,
            "publish_queue_path": "storage/publishing/publish_queue.json",
            "image_sourcing_status": image_sourcing_status,
            "manual_image_required": manual_image_required,
            "next_action": next_action,
            "created_at": datetime.now().isoformat()
        }

        self._save_json(self.publishing_dir / "publishing_result.json", result)
        self._save_json(self.publishing_dir / "publish_queue.json", publish_queue)
        self._save_text(self.publishing_dir / "caption.txt", full_caption)
        self._save_text(self.publishing_dir / "hashtags.txt", " ".join(hashtags))

        print(f"Publishing Result Saved: {self.publishing_dir / 'publishing_result.json'}")
        print(f"Publish Queue Saved: {self.publishing_dir / 'publish_queue.json'}")
        print(f"Caption Saved: {self.publishing_dir / 'caption.txt'}")
        print(f"Hashtags Saved: {self.publishing_dir / 'hashtags.txt'}")
        print("Publishing Module Finished")

        return result