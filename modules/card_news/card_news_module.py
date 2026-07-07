"""
Card News Module
AI-Content-OS

AI 생성 이미지 위에 카드뉴스용 텍스트를 합성하여
최종 업로드용 PNG 이미지를 만든다.
"""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from modules.base_module import BaseModule


class CardNewsModule(BaseModule):
    def __init__(self, config):
        super().__init__(config)

        self.output_dir = Path("storage/outputs")
        self.card_news_dir = Path("storage/card_news")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.card_news_dir.mkdir(parents=True, exist_ok=True)

        self.canvas_size = (1024, 1024)

    def get_font(self, size):
        font_candidates = [
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/malgunbd.ttf",
            "C:/Windows/Fonts/arial.ttf"
        ]

        for font_path in font_candidates:
            if Path(font_path).exists():
                return ImageFont.truetype(font_path, size)

        return ImageFont.load_default()

    def wrap_text(self, draw, text, font, max_width):
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            test_width = bbox[2] - bbox[0]

            if test_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines

    def draw_text_box(self, image, title, body_text):
        draw = ImageDraw.Draw(image, "RGBA")

        title_font = self.get_font(54)
        body_font = self.get_font(42)

        box_x = 70
        box_y = 690
        box_width = 884
        box_height = 260

        draw.rounded_rectangle(
            (box_x, box_y, box_x + box_width, box_y + box_height),
            radius=35,
            fill=(255, 255, 255, 230)
        )

        title_lines = self.wrap_text(draw, title, title_font, 760)
        body_lines = self.wrap_text(draw, body_text, body_font, 780)

        y = box_y + 35

        for line in title_lines[:1]:
            draw.text((box_x + 45, y), line, font=title_font, fill=(20, 20, 20, 255))
            y += 70

        for line in body_lines[:2]:
            draw.text((box_x + 45, y), line, font=body_font, fill=(50, 50, 50, 255))
            y += 55

        return image

    def run(self, content_result, image_generation_result):
        print("Card News Module Started")

        title = content_result.get("title", "AI-Content-OS")
        body = content_result.get("body", [])
        generated_images = image_generation_result.get("generated_images", [])

        card_news_items = []

        for item in generated_images:
            slide_number = item.get("slide")
            image_path = Path(item.get("image_path"))

            if not image_path.exists():
                print(f"Image not found: {image_path}")
                continue

            body_text = body[slide_number - 1] if slide_number - 1 < len(body) else ""

            base_image = Image.open(image_path).convert("RGB")
            base_image = base_image.resize(self.canvas_size)

            card_image = self.draw_text_box(
                image=base_image,
                title=title,
                body_text=body_text
            )

            output_filename = f"card_news_{slide_number}.png"
            output_path = self.card_news_dir / output_filename

            card_image.save(output_path)

            card_news_items.append({
                "slide": slide_number,
                "card_news_path": str(output_path),
                "status": "card_news_created"
            })

            print(f"Card News Saved: {output_path}")

        result = {
            "title": title,
            "card_news": card_news_items,
            "status": "card_news_completed"
        }

        output_path = self.output_dir / "card_news_result.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print("Card News Result Saved:", output_path)

        return result