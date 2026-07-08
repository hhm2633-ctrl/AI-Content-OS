from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

from modules.base_module import BaseModule


class CardNewsModule(BaseModule):
    def __init__(self, config=None):
        super().__init__(config)

        self.card_dir = Path("storage/card_news")
        self.card_dir.mkdir(parents=True, exist_ok=True)

        self.width = 1080
        self.height = 1080

    def _get_font(self, size: int, bold: bool = False):
        font_candidates = [
            "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]

        for font_path in font_candidates:
            if Path(font_path).exists():
                return ImageFont.truetype(font_path, size)

        return ImageFont.load_default()

    def _wrap_text(self, text: str, font, max_width: int) -> List[str]:
        text = str(text).replace("\n", " ").strip()
        lines = []
        current_line = ""

        for char in text:
            test_line = current_line + char
            bbox = font.getbbox(test_line)
            test_width = bbox[2] - bbox[0]

            if test_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char

        if current_line:
            lines.append(current_line)

        return lines

    def _extract_title_and_body(self, content_result: Dict[str, Any]):
        title = "AI-Content-OS 카드뉴스"

        body = [
            "1장: 문제 제기",
            "2장: 핵심 정보 설명",
            "3장: 사람들이 관심 가질 포인트",
            "4장: 요약 및 행동 유도",
        ]

        if isinstance(content_result, dict):
            if content_result.get("title"):
                title = str(content_result.get("title"))

            if isinstance(content_result.get("body"), list):
                body = content_result.get("body")

            elif isinstance(content_result.get("cards"), list):
                body = content_result.get("cards")

            elif isinstance(content_result.get("content"), list):
                body = content_result.get("content")

        clean_body = []

        for item in body:
            if isinstance(item, str):
                clean_body.append(item)

            elif isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("body")
                    or item.get("content")
                    or item.get("description")
                    or str(item)
                )
                clean_body.append(text)

        return title, clean_body[:4]

    def _extract_image_paths(self, image_generation_result: Dict[str, Any]) -> List[str]:
        image_paths = []

        if isinstance(image_generation_result, dict):
            images = image_generation_result.get("images", [])

            if isinstance(images, list):
                for item in images:
                    if isinstance(item, dict):
                        image_path = item.get("image_path")

                        if image_path and Path(image_path).exists():
                            image_paths.append(image_path)

        return image_paths

    def _create_background(self, image_path: Optional[str]):
        if image_path and Path(image_path).exists():
            image = Image.open(image_path).convert("RGB")
            image = image.resize((self.width, self.height))
        else:
            image = Image.new("RGB", (self.width, self.height), (235, 235, 235))

        image = image.convert("RGBA")

        dark_overlay = Image.new(
            "RGBA",
            (self.width, self.height),
            (0, 0, 0, 65),
        )

        image.alpha_composite(dark_overlay)

        return image.convert("RGB")

    def _draw_card(self, image, page_number: int, title: str, body_text: str):
        draw = ImageDraw.Draw(image)

        page_font = self._get_font(36, bold=True)
        title_font = self._get_font(56, bold=True)
        body_font = self._get_font(42)
        brand_font = self._get_font(28)

        margin = 70
        box_top = 590
        box_bottom = 990
        box_left = margin
        box_right = self.width - margin

        draw.rounded_rectangle(
            [box_left, box_top, box_right, box_bottom],
            radius=42,
            fill=(255, 255, 255),
        )

        draw.text(
            (box_left + 40, box_top + 35),
            f"{page_number:02d}",
            font=page_font,
            fill=(100, 100, 100),
        )

        title_lines = self._wrap_text(
            title,
            title_font,
            box_right - box_left - 80,
        )

        body_lines = self._wrap_text(
            body_text,
            body_font,
            box_right - box_left - 80,
        )

        y = box_top + 90

        for line in title_lines[:2]:
            draw.text(
                (box_left + 40, y),
                line,
                font=title_font,
                fill=(20, 20, 20),
            )
            y += 68

        y += 20

        for line in body_lines[:3]:
            draw.text(
                (box_left + 40, y),
                line,
                font=body_font,
                fill=(45, 45, 45),
            )
            y += 56

        draw.text(
            (box_left + 40, box_bottom - 55),
            "AI-Content-OS",
            font=brand_font,
            fill=(130, 130, 130),
        )

        return image

    def _create_card(
        self,
        page_number: int,
        title: str,
        body_text: str,
        image_path: Optional[str],
    ) -> str:
        image = self._create_background(image_path)
        image = self._draw_card(image, page_number, title, body_text)

        output_path = self.card_dir / f"card_news_{page_number}.png"
        image.save(output_path)

        print(f"Card News Saved: {output_path}")

        return str(output_path).replace("\\", "/")

    def run(
        self,
        content_result: Dict[str, Any],
        image_generation_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        print("Card News Module Started")

        title, body_list = self._extract_title_and_body(content_result)
        image_paths = self._extract_image_paths(image_generation_result)

        cards = []

        for index in range(4):
            body_text = (
                body_list[index]
                if index < len(body_list)
                else f"{index + 1}장 카드뉴스 내용"
            )

            image_path = (
                image_paths[index]
                if index < len(image_paths)
                else None
            )

            card_path = self._create_card(
                page_number=index + 1,
                title=title,
                body_text=body_text,
                image_path=image_path,
            )

            cards.append({
                "index": index + 1,
                "card_path": card_path,
                "source_image": image_path,
                "status": "created",
            })

        result = {
            "module": "CardNewsModule",
            "status": "card_news_completed",
            "cards": cards,
        }

        print("Card News Module Finished")
        return result