import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from modules.base_module import BaseModule
from modules.card_news.highlight_engine import HighlightEngine
from modules.card_news.layout_rule_engine import LayoutRuleEngine
from modules.card_news.layout_selector import LayoutSelector
from modules.card_news.slide_designer import SlideDesigner


class CardNewsModule(BaseModule):
    def __init__(self, config=None):
        super().__init__(config)

        self.card_dir = Path("storage/card_news")
        self.card_dir.mkdir(parents=True, exist_ok=True)

        self.width = 1080
        self.height = 1080

        self.layout_selector = LayoutSelector(self.config)
        self.layout_rule_engine = LayoutRuleEngine(self.config)
        self.slide_designer = SlideDesigner(self.config)
        self.highlight_engine = HighlightEngine(self.config)

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

    def _text_width(self, text: str, font) -> int:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

    def _wrap_text(self, text: str, font, max_width: int) -> List[str]:
        text = str(text).replace("\n", " ").strip()

        if not text:
            return []

        words = text.split(" ")
        lines = []
        current_line = ""

        for word in words:
            test_line = word if not current_line else current_line + " " + word

            if self._text_width(test_line, font) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        final_lines = []

        for line in lines:
            if self._text_width(line, font) <= max_width:
                final_lines.append(line)
            else:
                current = ""
                for char in line:
                    test = current + char
                    if self._text_width(test, font) <= max_width:
                        current = test
                    else:
                        if current:
                            final_lines.append(current)
                        current = char
                if current:
                    final_lines.append(current)

        return final_lines

    def _extract_slides(self, content_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        if isinstance(content_result, dict):
            slides = content_result.get("slides", [])

            if isinstance(slides, list) and slides:
                clean_slides = []

                for index, slide in enumerate(slides[:4]):
                    if isinstance(slide, dict):
                        clean_slides.append({
                            "page": slide.get("page", index + 1),
                            "role": slide.get("role", "card"),
                            "headline": str(slide.get("headline", f"{index + 1}장 제목")),
                            "body": str(slide.get("body", f"{index + 1}장 본문")),
                        })

                if clean_slides:
                    return clean_slides

        return [
            {
                "page": 1,
                "role": "hook",
                "headline": "콘텐츠, 아직 손으로만 만드세요?",
                "body": "반복 작업을 줄이고 카드뉴스 제작 속도를 높이는 구조가 필요합니다.",
            },
            {
                "page": 2,
                "role": "problem",
                "headline": "문제는 시간이 너무 많이 든다는 것",
                "body": "주제 찾기, 글쓰기, 이미지 만들기, 발행 준비를 매번 손으로 하면 금방 지칩니다.",
            },
            {
                "page": 3,
                "role": "solution",
                "headline": "그래서 흐름을 나눠야 합니다",
                "body": "주제 선택, 리서치, 문안 작성, 이미지 생성, 카드뉴스 제작을 모듈로 나누면 안정적으로 반복할 수 있습니다.",
            },
            {
                "page": 4,
                "role": "cta",
                "headline": "작게 만들고 계속 개선하세요",
                "body": "처음 목표는 완벽한 자동화가 아니라 매일 돌아가는 구조입니다.",
            },
        ]

    def _extract_title(self, content_result: Dict[str, Any]) -> str:
        if isinstance(content_result, dict) and content_result.get("title"):
            return str(content_result.get("title"))

        return "AI-Content-OS 카드뉴스"

    def _extract_image_paths(self, image_generation_result: Dict[str, Any]) -> List[str]:
        image_paths = []

        if isinstance(image_generation_result, dict):
            images = image_generation_result.get("images", [])

            if isinstance(images, list):
                for item in images:
                    if isinstance(item, dict):
                        image_path = item.get("image_path") or item.get("path")

                        if image_path and Path(image_path).exists():
                            image_paths.append(image_path)

                    elif isinstance(item, str) and Path(item).exists():
                        image_paths.append(item)

        return image_paths

    def _create_background(self, image_path: Optional[str], page_number: int):
        if image_path and Path(image_path).exists():
            image = Image.open(image_path).convert("RGB")
            image = image.resize((self.width, self.height))
            image = image.filter(ImageFilter.GaussianBlur(radius=1.2))
        else:
            base_colors = [
                (226, 233, 240),
                (235, 235, 228),
                (226, 238, 232),
                (238, 232, 226),
            ]
            image = Image.new("RGB", (self.width, self.height), base_colors[(page_number - 1) % 4])

        image = image.convert("RGBA")

        overlay = Image.new(
            "RGBA",
            (self.width, self.height),
            (0, 0, 0, 75),
        )
        image.alpha_composite(overlay)

        light_layer = Image.new(
            "RGBA",
            (self.width, self.height),
            (255, 255, 255, 35),
        )
        image.alpha_composite(light_layer)

        return image.convert("RGB")

    def _draw_top_badge(self, draw, page_number: int, role: str):
        badge_font = self._get_font(30, bold=True)

        role_labels = {
            "hook": "HOOK",
            "problem": "PROBLEM",
            "solution": "SOLUTION",
            "cta": "SAVE",
        }

        label = role_labels.get(role, "CARD")
        badge_text = f"{page_number:02d}  {label}"

        x1, y1 = 70, 65
        x2, y2 = 360, 125

        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=30,
            fill=(255, 255, 255),
        )

        draw.text(
            (x1 + 28, y1 + 13),
            badge_text,
            font=badge_font,
            fill=(30, 30, 30),
        )

    def _draw_card_box(self, draw):
        box_left = 65
        box_top = 555
        box_right = self.width - 65
        box_bottom = 990

        shadow_offset = 10

        draw.rounded_rectangle(
            [
                box_left + shadow_offset,
                box_top + shadow_offset,
                box_right + shadow_offset,
                box_bottom + shadow_offset,
            ],
            radius=45,
            fill=(0, 0, 0),
        )

        draw.rounded_rectangle(
            [box_left, box_top, box_right, box_bottom],
            radius=45,
            fill=(255, 255, 255),
        )

        return box_left, box_top, box_right, box_bottom

    def _draw_text_content(
        self,
        draw,
        title: str,
        headline: str,
        body: str,
        box_left: int,
        box_top: int,
        box_right: int,
        box_bottom: int,
    ):
        small_font = self._get_font(28)
        headline_font = self._get_font(60, bold=True)
        body_font = self._get_font(39)
        brand_font = self._get_font(26, bold=True)

        max_width = box_right - box_left - 80

        title_text = title[:38]
        draw.text(
            (box_left + 40, box_top + 34),
            title_text,
            font=small_font,
            fill=(120, 120, 120),
        )

        headline_lines = self._wrap_text(headline, headline_font, max_width)
        body_lines = self._wrap_text(body, body_font, max_width)

        y = box_top + 88

        for line in headline_lines[:2]:
            draw.text(
                (box_left + 40, y),
                line,
                font=headline_font,
                fill=(18, 18, 18),
            )
            y += 73

        y += 24

        for line in body_lines[:4]:
            draw.text(
                (box_left + 40, y),
                line,
                font=body_font,
                fill=(45, 45, 45),
            )
            y += 53

        draw.text(
            (box_left + 40, box_bottom - 55),
            "AI-Content-OS",
            font=brand_font,
            fill=(120, 120, 120),
        )

    def _draw_bottom_line(self, draw):
        draw.rounded_rectangle(
            [70, 1015, 1010, 1025],
            radius=5,
            fill=(255, 255, 255),
        )

    def _draw_card(
        self,
        image,
        page_number: int,
        title: str,
        slide: Dict[str, Any],
    ):
        draw = ImageDraw.Draw(image)

        role = slide.get("role", "card")
        headline = slide.get("headline", f"{page_number}장 제목")
        body = slide.get("body", f"{page_number}장 본문")

        self._draw_top_badge(draw, page_number, role)
        box_left, box_top, box_right, box_bottom = self._draw_card_box(draw)

        self._draw_text_content(
            draw=draw,
            title=title,
            headline=headline,
            body=body,
            box_left=box_left,
            box_top=box_top,
            box_right=box_right,
            box_bottom=box_bottom,
        )

        self._draw_bottom_line(draw)

        return image

    def _create_card(
        self,
        page_number: int,
        title: str,
        slide: Dict[str, Any],
        image_path: Optional[str],
    ) -> str:
        image = self._create_background(image_path, page_number)
        image = self._draw_card(image, page_number, title, slide)

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

        title = self._extract_title(content_result)
        slides = self._extract_slides(content_result)
        image_paths = self._extract_image_paths(image_generation_result)

        cards = []

        for index in range(4):
            slide = slides[index] if index < len(slides) else {
                "page": index + 1,
                "role": "card",
                "headline": f"{index + 1}장 제목",
                "body": f"{index + 1}장 본문",
            }

            image_path = image_paths[index] if index < len(image_paths) else None

            card_path = self._create_card(
                page_number=index + 1,
                title=title,
                slide=slide,
                image_path=image_path,
            )

            cards.append({
                "index": index + 1,
                "card_path": card_path,
                "source_image": image_path,
                "headline": slide.get("headline", ""),
                "status": "created",
            })

        result = {
            "module": "CardNewsModule",
            "status": "card_news_completed",
            "title": title,
            "cards": cards,
        }

        result["layout_result"] = self._build_layout_result(content_result, slides)

        print("Card News Module Finished")
        return result

    def _build_layout_result(
        self,
        content_result: Dict[str, Any],
        slides: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        try:
            return self._compute_layout_result(content_result or {}, slides or [])
        except Exception as error:
            print(f"Layout Intelligence Failed, using default layout: {error}")
            return self._default_layout_result(slides)

    def _compute_layout_result(
        self,
        content_result: Dict[str, Any],
        slides: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        topic_intelligence = self._load_topic_intelligence()
        brand_profile = self._load_brand_profile()
        content_intelligence = content_result.get("content_intelligence") or {}
        pattern_meta = content_result.get("pattern_prompt_meta") or {}

        selection = self.layout_selector.select(
            pattern_meta=pattern_meta,
            topic_intelligence=topic_intelligence,
            brand_profile=brand_profile,
            content_intelligence=content_intelligence,
        )
        layout_type = selection.get("layout_type", "bold_ai")

        rule = self.layout_rule_engine.get_rule(layout_type)
        slide_designs = self.slide_designer.design(slides, rule)
        highlight_result = self.highlight_engine.highlight(content_result, topic_intelligence)

        return {
            "layout_type": layout_type,
            "slide_count": len(slides),
            "highlight_keywords": highlight_result.get("highlight_keywords", []),
            "title_style": rule.get("title_style"),
            "body_style": rule.get("body_style"),
            "image_ratio": rule.get("image_ratio"),
            "cta_position": rule.get("cta_position"),
            "selection_reason": selection.get("reason", ""),
            "slide_designs": slide_designs,
            "slide_highlights": highlight_result.get("slide_highlights", []),
            "fallback_used": bool(selection.get("fallback_used", False)) or bool(rule.get("fallback_used", False)),
        }

    def _default_layout_result(self, slides: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        slides = slides or []

        try:
            default_rule = self.layout_rule_engine.get_rule(LayoutSelector.DEFAULT_LAYOUT)
        except Exception:
            default_rule = {}

        return {
            "layout_type": LayoutSelector.DEFAULT_LAYOUT,
            "slide_count": len(slides),
            "highlight_keywords": [],
            "title_style": default_rule.get("title_style", "sans_black_bold"),
            "body_style": default_rule.get("body_style", "sans_white_medium"),
            "image_ratio": default_rule.get("image_ratio", "1:1"),
            "cta_position": default_rule.get("cta_position", "bottom_center"),
            "selection_reason": "Layout Intelligence 계산 실패로 기존 CardNews 기본 레이아웃을 사용함.",
            "slide_designs": [],
            "slide_highlights": [],
            "fallback_used": True,
        }

    def _load_topic_intelligence(self) -> Dict[str, Any]:
        path = Path("storage/research/research_result.json")

        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                topic_intelligence = data.get("topic_intelligence")

                if isinstance(topic_intelligence, dict):
                    return topic_intelligence
        except Exception as error:
            print(f"Topic Intelligence Load Failed: {error}")

        return {}

    def _load_brand_profile(self) -> Dict[str, Any]:
        path = Path("config/brand_profile.json")

        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception as error:
            print(f"Brand Profile Load Failed: {error}")

        return {}
