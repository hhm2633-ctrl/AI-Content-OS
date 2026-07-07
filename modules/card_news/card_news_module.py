import os
from typing import Any, Dict, List, Optional

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    from modules.base_module import BaseModule
except ImportError:
    from src.base_module import BaseModule


class CardNewsModule(BaseModule):
    """
    CardNewsModule

    역할:
    - ContentModule 결과와 ImageGenerationModule 결과를 받아 카드뉴스 PNG 파일 생성
    - 현재는 안정적인 기본 카드뉴스 이미지 생성 구조
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.output_dir = (
            self.config.get("output_dir")
            or self.config.get("card_news_output_dir")
            or os.path.join("storage", "card_news")
        )

        self.width = int(self.config.get("width", 1080))
        self.height = int(self.config.get("height", 1080))

        os.makedirs(self.output_dir, exist_ok=True)

    def run(
        self,
        content_result: Optional[Dict[str, Any]] = None,
        image_generation_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Card News Module Started")

        if Image is None:
            raise ImportError(
                "Pillow가 설치되어 있지 않습니다. PowerShell에서 py -m pip install pillow 실행 후 다시 시도하세요."
            )

        content_result = content_result or {}
        image_generation_result = image_generation_result or {}

        title = content_result.get("title", "AI Content OS")
        slides = content_result.get("slides", [])

        if not slides:
            slides = self._fallback_slides(title)

        card_news_files = []

        for slide in slides:
            page = int(slide.get("page", len(card_news_files) + 1))
            headline = str(slide.get("headline", f"{page}장 제목"))
            body = str(slide.get("body", ""))

            file_path = os.path.join(self.output_dir, f"card_news_{page}.png")

            self._create_card_image(
                file_path=file_path,
                page=page,
                title=title,
                headline=headline,
                body=body,
            )

            card_news_files.append(
                {
                    "page": page,
                    "file_path": file_path,
                    "status": "created",
                }
            )

            print(f"Card News Saved: {file_path}")

        result = {
            "title": title,
            "card_news_files": card_news_files,
            "caption": content_result.get("caption", ""),
            "hashtags": content_result.get("hashtags", []),
            "status": "card_news_created",
        }

        print("Card News Module Finished")
        return result

    def _create_card_image(
        self,
        file_path: str,
        page: int,
        title: str,
        headline: str,
        body: str,
    ) -> None:
        image = Image.new("RGB", (self.width, self.height), color=(248, 248, 248))
        draw = ImageDraw.Draw(image)

        title_font = self._load_font(46)
        headline_font = self._load_font(72)
        body_font = self._load_font(40)
        page_font = self._load_font(30)

        margin = 90

        draw.rectangle(
            [(0, 0), (self.width, 150)],
            fill=(28, 28, 28),
        )

        draw.text(
            (margin, 48),
            self._safe_text(title, 28),
            font=title_font,
            fill=(255, 255, 255),
        )

        draw.text(
            (self.width - 170, 52),
            f"{page}/4",
            font=page_font,
            fill=(255, 255, 255),
        )

        headline_lines = self._wrap_text(headline, max_chars=12)
        y = 260

        for line in headline_lines[:3]:
            draw.text(
                (margin, y),
                line,
                font=headline_font,
                fill=(20, 20, 20),
            )
            y += 90

        y += 40

        body_lines = self._wrap_text(body, max_chars=21)

        for line in body_lines[:8]:
            draw.text(
                (margin, y),
                line,
                font=body_font,
                fill=(60, 60, 60),
            )
            y += 58

        draw.rectangle(
            [(margin, self.height - 120), (self.width - margin, self.height - 112)],
            fill=(28, 28, 28),
        )

        draw.text(
            (margin, self.height - 85),
            "AI-Content-OS",
            font=page_font,
            fill=(80, 80, 80),
        )

        image.save(file_path)

    def _load_font(self, size: int):
        font_candidates = [
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/malgunbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]

        for font_path in font_candidates:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
            except Exception:
                pass

        return ImageFont.load_default()

    def _wrap_text(self, text: str, max_chars: int) -> List[str]:
        text = str(text).replace("\n", " ").strip()

        if not text:
            return [""]

        words = text.split(" ")
        lines = []
        current = ""

        for word in words:
            if len(current) + len(word) + 1 <= max_chars:
                current = f"{current} {word}".strip()
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        final_lines = []
        for line in lines:
            if len(line) <= max_chars:
                final_lines.append(line)
            else:
                for i in range(0, len(line), max_chars):
                    final_lines.append(line[i:i + max_chars])

        return final_lines

    def _safe_text(self, text: str, max_chars: int) -> str:
        text = str(text).replace("\n", " ").strip()
        if len(text) <= max_chars:
            return text
        return text[:max_chars - 3] + "..."

    def _fallback_slides(self, title: str) -> List[Dict[str, Any]]:
        return [
            {
                "page": 1,
                "headline": "콘텐츠 자동화 시작",
                "body": "AI를 활용하면 카드뉴스 제작 과정을 더 빠르고 안정적으로 만들 수 있습니다.",
            },
            {
                "page": 2,
                "headline": "핵심은 구조입니다",
                "body": "리서치, 글쓰기, 이미지, 카드뉴스, 발행 단계를 나누어야 오류를 줄일 수 있습니다.",
            },
            {
                "page": 3,
                "headline": "처음은 작게",
                "body": "처음부터 완전 자동화를 목표로 하기보다 카드뉴스 한 세트를 정확히 만드는 것이 중요합니다.",
            },
            {
                "page": 4,
                "headline": "반복하며 개선",
                "body": "출력물을 확인하고 문구와 디자인을 조금씩 개선하면 운영 가능한 시스템이 됩니다.",
            },
        ]