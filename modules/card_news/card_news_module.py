import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from modules.base_module import BaseModule
from modules.card_news.card_news_quality_checker import CardNewsQualityChecker
from modules.card_news.card_news_text_optimizer import CardNewsTextOptimizer
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
        self.quality_checker = CardNewsQualityChecker(self.config)
        self.text_optimizer = CardNewsTextOptimizer(self.config)

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
        layout_context: Optional[Dict[str, Any]] = None,
    ) -> "tuple[str, bool]":
        if layout_context:
            try:
                path = self._create_card_with_layout(
                    page_number=page_number,
                    title=title,
                    slide=slide,
                    image_path=image_path,
                    layout_context=layout_context,
                )
                return path, True
            except Exception as error:
                print(
                    f"Layout-aware card rendering failed for page {page_number}: {error}. "
                    "Falling back to default CardNews rendering."
                )

        image = self._create_background(image_path, page_number)
        image = self._draw_card(image, page_number, title, slide)

        output_path = self.card_dir / f"card_news_{page_number}.png"
        image.save(output_path)

        print(f"Card News Saved: {output_path}")

        return str(output_path).replace("\\", "/"), False

    # ------------------------------------------------------------------
    # Sprint 7: Layout-aware rendering (opt-in, additive only).
    #
    # Every method below is only ever reached through _create_card's
    # try/except above. If anything here raises, _create_card silently
    # falls back to the original _create_background/_draw_card path that
    # existed before Sprint 7, so the base CardNews rendering can never
    # be broken by this layer.
    # ------------------------------------------------------------------

    def _create_card_with_layout(
        self,
        page_number: int,
        title: str,
        slide: Dict[str, Any],
        image_path: Optional[str],
        layout_context: Dict[str, Any],
    ) -> str:
        rule = layout_context.get("rule", {}) or {}
        background_tone = str(rule.get("background_tone", ""))

        slide_design = layout_context.get("slide_designs_by_page", {}).get(page_number, {})
        slide_highlight = layout_context.get("slide_highlights_by_page", {}).get(page_number, {})

        image = self._create_background(image_path, page_number)
        image = self._apply_background_tone(image, background_tone)

        palette = self._resolve_box_palette(background_tone)

        if str(rule.get("title_style", "")) == "alert_bold":
            palette = dict(palette)
            palette["headline_color"] = (214, 40, 40)

        image = self._draw_layout_card(
            image=image,
            page_number=page_number,
            title=title,
            slide=slide,
            rule=rule,
            slide_design=slide_design,
            slide_highlight=slide_highlight,
            palette=palette,
        )

        output_path = self.card_dir / f"card_news_{page_number}.png"
        image.save(output_path)

        print(
            f"Card News Saved (layout-aware, {rule.get('layout_type', 'unknown')}): {output_path}"
        )

        return str(output_path).replace("\\", "/")

    def _apply_background_tone(self, image, background_tone: str):
        tone_overlays = {
            "dark": (10, 10, 15, 70),
            "dark_gradient": (10, 10, 20, 80),
            "split_light_dark": (15, 15, 25, 55),
            "light_paper": (255, 250, 240, 35),
            "pastel": (255, 235, 240, 35),
            "light_clean": (255, 255, 255, 25),
            "light_gradient": (255, 245, 230, 30),
            "warning_light": (255, 230, 230, 40),
        }

        overlay_color = tone_overlays.get(background_tone)

        if not overlay_color:
            return image

        rgba_image = image.convert("RGBA")
        overlay = Image.new("RGBA", (self.width, self.height), overlay_color)
        rgba_image.alpha_composite(overlay)

        return rgba_image.convert("RGB")

    def _resolve_box_palette(self, background_tone: str) -> Dict[str, Any]:
        dark_tones = {"dark", "dark_gradient", "split_light_dark"}

        if background_tone in dark_tones:
            return {
                "box_fill": (26, 26, 30),
                "headline_color": (245, 245, 245),
                "body_color": (210, 210, 210),
                "subtitle_color": (170, 170, 170),
            }

        return {
            "box_fill": (255, 255, 255),
            "headline_color": (18, 18, 18),
            "body_color": (45, 45, 45),
            "subtitle_color": (120, 120, 120),
        }

    def _hex_to_rgb(self, hex_color: str):
        hex_color = str(hex_color or "").lstrip("#")

        if len(hex_color) != 6:
            raise ValueError(f"invalid hex color: {hex_color}")

        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    def _draw_layout_card_box(self, draw, box_fill):
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

        draw.rounded_rectangle([box_left, box_top, box_right, box_bottom], radius=45, fill=box_fill)

        return box_left, box_top, box_right, box_bottom

    def _draw_highlight_tags(self, draw, highlights: List[Dict[str, Any]], highlight_color: str):
        if not highlights:
            return

        try:
            color = self._hex_to_rgb(highlight_color)
        except Exception:
            color = (255, 214, 10)

        tag_font = self._get_font(24, bold=True)

        x = 70
        y = 150
        max_x = self.width - 70
        max_tags = 3
        seen_text = set()

        for item in highlights:
            if len(seen_text) >= max_tags:
                break

            text = str(item.get("text", "")).strip()

            if not text or text in seen_text:
                continue

            seen_text.add(text)
            label = text[:10]

            text_width = self._text_width(label, tag_font)
            tag_width = text_width + 30
            tag_height = 42

            if x + tag_width > max_x:
                break

            draw.rounded_rectangle([x, y, x + tag_width, y + tag_height], radius=14, fill=color)
            draw.text((x + 15, y + 9), label, font=tag_font, fill=(20, 20, 20))

            x += tag_width + 14

    def _draw_highlight_accent(self, draw, box_left, box_top, box_right, box_bottom, highlight_color: str):
        try:
            color = self._hex_to_rgb(highlight_color)
        except Exception:
            color = (230, 57, 70)

        draw.rounded_rectangle(
            [box_left, box_top, box_left + 14, box_bottom],
            radius=8,
            fill=color,
        )

    def _draw_cta_area(self, draw, box_left, box_top, box_right, box_bottom, cta_position: str, highlight_color: str):
        try:
            color = self._hex_to_rgb(highlight_color)
        except Exception:
            color = (255, 214, 10)

        bar_width = 220
        bar_height = 12

        if cta_position == "bottom_right":
            x1 = box_right - bar_width - 40
        elif cta_position == "bottom_left":
            x1 = box_left + 40
        else:
            x1 = ((box_left + box_right) // 2) - (bar_width // 2)

        y1 = box_bottom - 20
        x2 = x1 + bar_width
        y2 = y1 + bar_height

        draw.rounded_rectangle([x1, y1, x2, y2], radius=6, fill=color)

    def _draw_layout_text_content(
        self,
        draw,
        title: str,
        headline: str,
        body: str,
        box_left: int,
        box_top: int,
        box_right: int,
        box_bottom: int,
        palette: Dict[str, Any],
        title_position: str,
        body_position: str,
        body_prefix: str,
    ):
        small_font = self._get_font(28)
        headline_font = self._get_font(60, bold=True)
        body_font = self._get_font(39)
        brand_font = self._get_font(26, bold=True)

        max_width = box_right - box_left - 80

        title_position_offsets = {"top": 0, "center": 20, "bottom": 30}
        body_position_offsets = {"below_title": 0, "middle": 10, "bottom": 20}

        title_text = title[:38]
        draw.text(
            (box_left + 40, box_top + 34),
            title_text,
            font=small_font,
            fill=palette["subtitle_color"],
        )

        headline_lines = self._wrap_text(headline, headline_font, max_width)
        body_text = f"{body_prefix}{body}" if body_prefix else body
        body_lines = self._wrap_text(body_text, body_font, max_width)

        y = box_top + 88 + title_position_offsets.get(title_position, 0)

        for line in headline_lines[:2]:
            draw.text((box_left + 40, y), line, font=headline_font, fill=palette["headline_color"])
            y += 73

        y += 24 + body_position_offsets.get(body_position, 0)

        for line in body_lines[:4]:
            draw.text((box_left + 40, y), line, font=body_font, fill=palette["body_color"])
            y += 53

        draw.text(
            (box_left + 40, box_bottom - 55),
            "AI-Content-OS",
            font=brand_font,
            fill=palette["subtitle_color"],
        )

    def _draw_layout_card(
        self,
        image,
        page_number: int,
        title: str,
        slide: Dict[str, Any],
        rule: Dict[str, Any],
        slide_design: Dict[str, Any],
        slide_highlight: Dict[str, Any],
        palette: Dict[str, Any],
    ):
        draw = ImageDraw.Draw(image)

        role = slide.get("role", "card")
        headline = slide.get("headline", f"{page_number}장 제목")
        body = slide.get("body", f"{page_number}장 본문")

        self._draw_top_badge(draw, page_number, role)

        highlights = (slide_highlight or {}).get("highlights", []) or []
        self._draw_highlight_tags(draw, highlights, rule.get("highlight_color", "#ffd60a"))

        box_left, box_top, box_right, box_bottom = self._draw_layout_card_box(draw, palette["box_fill"])

        body_style_prefixes = {
            "checklist_items": "✓ ",
            "step_by_step": "→ ",
            "warning_box": "[주의] ",
            "timeline_marker": "● ",
        }
        body_prefix = body_style_prefixes.get(str(rule.get("body_style", "")), "")

        title_position = str((slide_design or {}).get("title_position", "top"))
        body_position = str((slide_design or {}).get("body_position", "middle"))

        self._draw_layout_text_content(
            draw=draw,
            title=title,
            headline=headline,
            body=body,
            box_left=box_left,
            box_top=box_top,
            box_right=box_right,
            box_bottom=box_bottom,
            palette=palette,
            title_position=title_position,
            body_position=body_position,
            body_prefix=body_prefix,
        )

        if (slide_design or {}).get("highlight_box"):
            self._draw_highlight_accent(
                draw, box_left, box_top, box_right, box_bottom, rule.get("highlight_color", "#e63946")
            )

        if (slide_design or {}).get("cta_area") or role == "cta":
            cta_position = str(rule.get("cta_position", "bottom_center"))
            self._draw_cta_area(
                draw, box_left, box_top, box_right, box_bottom, cta_position, rule.get("highlight_color", "#ffd60a")
            )

        self._draw_bottom_line(draw)

        return image

    def run(
        self,
        content_result: Dict[str, Any],
        image_generation_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        print("Card News Module Started")

        title = self._extract_title(content_result)
        slides = self._extract_slides(content_result)
        image_paths = self._extract_image_paths(image_generation_result)

        layout_result = self._build_layout_result(content_result, slides)
        layout_context, rendering_notes = self._build_layout_context(layout_result)

        optimized = self._optimize_slides_for_rendering(slides)
        rendering_slides = optimized.get("slides") or slides
        design_quality_result = self._build_design_quality_result(optimized)
        self._apply_layout_quality_score(layout_result, design_quality_result)

        cards = []
        layout_applied_count = 0

        for index in range(4):
            slide = rendering_slides[index] if index < len(rendering_slides) else {
                "page": index + 1,
                "role": "card",
                "headline": f"{index + 1}장 제목",
                "body": f"{index + 1}장 본문",
            }

            image_path = image_paths[index] if index < len(image_paths) else None

            card_path, used_layout = self._create_card(
                page_number=index + 1,
                title=title,
                slide=slide,
                image_path=image_path,
                layout_context=layout_context,
            )

            if used_layout:
                layout_applied_count += 1

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

        result["layout_result"] = layout_result
        result["rendering_result"] = self._build_rendering_result(
            layout_result=layout_result,
            layout_applied_count=layout_applied_count,
            total_cards=len(cards),
            rendering_notes=rendering_notes,
        )
        result["design_quality_result"] = design_quality_result
        result["card_news_quality"] = self._build_card_news_quality(result)

        print("Card News Module Finished")
        return result

    def _optimize_slides_for_rendering(self, slides: List[Dict[str, Any]]) -> Dict[str, Any]:
        fallback_result = {
            "slides": list(slides or []),
            "text_optimized": False,
            "headline_trimmed_count": 0,
            "body_trimmed_count": 0,
            "duplicate_removed_count": 0,
            "cta_optimized": False,
            "readability_warnings": [],
            "fallback_used": True,
        }

        try:
            optimized = self.text_optimizer.optimize(slides)
        except Exception as error:
            print(f"CardNews Text Optimizer Failed, using original slide text: {error}")
            fallback_result["readability_warnings"] = [f"Text Optimizer 호출 실패: {error}"]
            return fallback_result

        if not isinstance(optimized, dict) or not isinstance(optimized.get("slides"), list):
            print("CardNews Text Optimizer returned an invalid result, using original slide text.")
            fallback_result["readability_warnings"] = [
                "Text Optimizer가 올바른 결과를 반환하지 않아 원본 slide로 대체함."
            ]
            return fallback_result

        return optimized

    def _build_design_quality_result(self, optimized: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "text_optimized": bool(optimized.get("text_optimized", False)),
            "headline_trimmed_count": int(optimized.get("headline_trimmed_count", 0) or 0),
            "body_trimmed_count": int(optimized.get("body_trimmed_count", 0) or 0),
            "duplicate_removed_count": int(optimized.get("duplicate_removed_count", 0) or 0),
            "cta_optimized": bool(optimized.get("cta_optimized", False)),
            "readability_warnings": list(optimized.get("readability_warnings", []) or []),
            "fallback_used": bool(optimized.get("fallback_used", False)),
            "ratio_adjusted_count": int(optimized.get("ratio_adjusted_count", 0) or 0),
            "readability_score": float(optimized.get("readability_score", 0.0) or 0.0),
            "slide_readability": list(optimized.get("slide_readability", []) or []),
        }

    def _apply_layout_quality_score(
        self,
        layout_result: Dict[str, Any],
        design_quality_result: Dict[str, Any],
    ) -> None:
        """
        Layout Score(Layout 적합도) + Highlight Score(Highlight 적합도) +
        Readability Score를 하나의 layout_quality_score로 합산해 layout_result에
        추가한다 (additive, 기존 필드는 건드리지 않음). 실패해도 layout_result는
        _compute_layout_result/_default_layout_result가 이미 채운 기본값을 유지한다.
        """
        try:
            readability_score = float(design_quality_result.get("readability_score", 0.0) or 0.0)
            layout_score = float(layout_result.get("layout_score", 0.0) or 0.0)
            highlight_score = float(layout_result.get("highlight_score", 0.0) or 0.0)

            layout_result["readability_score"] = round(readability_score, 4)
            layout_result["layout_quality_score"] = round(
                (layout_score + highlight_score + readability_score) / 3, 4
            )
        except Exception as error:
            print(f"Layout Quality Score Merge Failed: {error}")
            layout_result.setdefault("readability_score", 0.0)
            layout_result.setdefault("layout_quality_score", 0.0)

    def _build_card_news_quality(self, card_news_result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            quality_result = self.quality_checker.check(card_news_result)
        except Exception as error:
            print(f"CardNews QA Failed: {error}")
            quality_result = {
                "qa_score": 0.0,
                "passed": False,
                "checks": {},
                "warnings": [f"QA 모듈 호출 실패: {error}"],
                "recommendations": ["QA 모듈 호출 실패 - 수동 확인이 필요합니다."],
            }

        if not isinstance(quality_result, dict):
            quality_result = {
                "qa_score": 0.0,
                "passed": False,
                "checks": {},
                "warnings": ["QA 모듈이 dict를 반환하지 않아 안전 값으로 대체함."],
                "recommendations": ["QA 모듈 반환값을 확인하세요."],
            }

        try:
            self._save_quality_result(quality_result)
        except Exception as error:
            print(f"Card News Quality Save Failed: {error}")

        return quality_result

    def _save_quality_result(self, quality_result: Dict[str, Any]) -> None:
        path = self.card_dir / "card_news_quality.json"

        with open(path, "w", encoding="utf-8") as file:
            json.dump(quality_result, file, ensure_ascii=False, indent=2)

        print(f"Card News Quality Saved: {path}")

    def _build_layout_context(
        self,
        layout_result: Optional[Dict[str, Any]],
    ) -> "tuple[Optional[Dict[str, Any]], List[str]]":
        notes: List[str] = []

        try:
            if not isinstance(layout_result, dict):
                notes.append("layout_result가 없어 레이아웃 인지 렌더링을 적용하지 않음.")
                return None, notes

            layout_type = layout_result.get("layout_type")
            slide_designs = layout_result.get("slide_designs") or []

            if not layout_type or not slide_designs:
                notes.append("layout_type 또는 slide_designs 정보가 부족해 레이아웃 인지 렌더링을 적용하지 않음.")
                return None, notes

            rule = self.layout_rule_engine.get_rule(layout_type)

            slide_designs_by_page: Dict[Any, Dict[str, Any]] = {}
            for design in slide_designs:
                if isinstance(design, dict) and design.get("page") is not None:
                    slide_designs_by_page[design.get("page")] = design

            slide_highlights_by_page: Dict[Any, Dict[str, Any]] = {}
            for item in layout_result.get("slide_highlights") or []:
                if isinstance(item, dict) and item.get("page") is not None:
                    slide_highlights_by_page[item.get("page")] = item

            context = {
                "rule": rule,
                "slide_designs_by_page": slide_designs_by_page,
                "slide_highlights_by_page": slide_highlights_by_page,
            }

            notes.append(f"'{layout_type}' 레이아웃을 카드뉴스 렌더링에 적용함.")
            return context, notes

        except Exception as error:
            notes.append(f"레이아웃 컨텍스트 구성 실패로 기본 렌더링을 사용함: {error}")
            return None, notes

    def _build_rendering_result(
        self,
        layout_result: Optional[Dict[str, Any]],
        layout_applied_count: int,
        total_cards: int,
        rendering_notes: List[str],
    ) -> Dict[str, Any]:
        layout_result = layout_result if isinstance(layout_result, dict) else {}
        layout_applied = layout_applied_count > 0

        slide_designs = layout_result.get("slide_designs") or []
        cta_area_applied = layout_applied and any(
            isinstance(design, dict) and design.get("cta_area") for design in slide_designs
        )
        highlight_applied = layout_applied and bool(layout_result.get("highlight_keywords"))

        notes = list(rendering_notes or [])

        if layout_applied and layout_applied_count < total_cards:
            notes.append(
                f"{total_cards}장 중 {layout_applied_count}장만 레이아웃 인지 렌더링에 성공, "
                "나머지는 기본 CardNews 렌더링으로 대체됨."
            )

        rendering_fallback_used = layout_applied_count < total_cards

        return {
            "layout_applied": bool(layout_applied),
            "layout_type": str(layout_result.get("layout_type", "") or ""),
            "highlight_applied": bool(highlight_applied),
            "cta_area_applied": bool(cta_area_applied),
            "fallback_used": bool(rendering_fallback_used),
            "rendering_notes": notes,
        }

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
            "layout_score": float(selection.get("layout_score", 0.0) or 0.0),
            "layout_score_reason": selection.get("layout_score_reason", ""),
            "highlight_score": float(highlight_result.get("highlight_score", 0.0) or 0.0),
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
            "layout_score": 0.0,
            "layout_score_reason": "Layout Intelligence 계산 실패로 0.0 처리함.",
            "highlight_score": 0.0,
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
