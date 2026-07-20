import json
import re
from inspect import Parameter, signature
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from modules.base_module import BaseModule
from modules.card_news import render_constants as RC
from modules.card_news.card_news_quality_checker import CardNewsQualityChecker
from modules.card_news.card_news_text_optimizer import CardNewsTextOptimizer
from modules.card_news.debate_question_selector import DebateQuestionSelector
from modules.card_news.evidence_selector import EvidenceSelector
from modules.card_news.highlight_engine import HighlightEngine
from modules.card_news.layout_rule_engine import LayoutRuleEngine
from modules.card_news.layout_selector import LayoutSelector
from modules.card_news.mobile_readability_checker import MobileReadabilityChecker
from modules.card_news.slide_designer import SlideDesigner
from modules.card_news.social_proof_selector import SocialProofSelector
from modules.card_news.story_flow_planner import StoryFlowPlanner
from modules.card_news.typography_rules import TYPOGRAPHY_ROLES, check_text_against_role, resolve_typography_role
from modules.card_news.visual_rhythm_selector import VisualRhythmSelector
from modules.common.external_storage import resolve_external_path
from modules.knowledge_engine.knowledge_interface import KnowledgeInterface


class CardNewsModule(BaseModule):
    # problem/CTA 카드의 흰 패널 상단은 270px 썸네일에서 보조문이 패널
    # 경계와 붙어 보이지 않도록 전용 세로 영역을 확보한다. hook/solution은
    # 기존 좌표를 유지해 이미 승인된 card1/3 시각 리듬을 보존한다.
    SUBTITLE_CONFLICT_ROLES = frozenset({"problem", "cta"})
    SUBTITLE_LEGACY_TOP_INSET = 34
    SUBTITLE_SAFE_TOP_INSET = 50
    SUBTITLE_HEADLINE_SAFE_GAP = 10

    # CardNews Intelligence (Phase M8: Production Quality) - Human Visual
    # Rhythm 실제 렌더링 반영. 완전히 새로운 Renderer가 아니라, 기존
    # _draw_layout_card/_draw_layout_text_content가 이미 쓰는 box_top(박스
    # 시작 y좌표)/줄 수 상한/여백만 스타일별로 다르게 준다. box_bottom(990)과
    # box_left/right(좌우 여백)는 모든 스타일에서 동일하게 유지한다 - CTA
    # 바/하단 라인 등 기존 고정 요소와의 정렬이 깨지지 않게 하기 위함이다.
    # 각 수치는 실제 4종 샘플 PNG 렌더 확인(#48)으로 텍스트 잘림/겹침이
    # 없는지 검증했다.
    VISUAL_STYLE_PROFILES: Dict[str, Dict[str, Any]] = {
        "title_focus": {
            "box_top": 555, "headline_max_lines": 2, "body_max_lines": 1, "body_position_offset": 16,
        },
        "short_line_focus": {
            "box_top": 610, "headline_max_lines": 1, "body_max_lines": 2, "body_position_offset": 30,
        },
        "image_focus": {
            "box_top": 650, "headline_max_lines": 1, "body_max_lines": 1, "body_position_offset": 14,
        },
        "quote_card": {
            "box_top": 610, "headline_max_lines": 1, "body_max_lines": 3, "body_position_offset": 10,
            "quote_mark": True,
        },
        "comparison": {
            # 실제 A/B 비교 구조 데이터가 없어 항상 기본값으로 fallback된다
            # (_resolve_visual_rhythm_application 참고) - 정의만 남겨 둔다.
            "box_top": 555, "headline_max_lines": 2, "body_max_lines": 4, "body_position_offset": 24,
        },
        "whitespace_focus": {
            "box_top": 650, "headline_max_lines": 1, "body_max_lines": 1, "body_position_offset": 40,
        },
        "cta_focus": {
            "box_top": 640, "headline_max_lines": 1, "body_max_lines": 2, "body_position_offset": 14,
        },
    }
    DEFAULT_VISUAL_STYLE_PROFILE: Dict[str, Any] = {
        "box_top": RC.BOX_TOP_DEFAULT, "headline_max_lines": 2, "body_max_lines": 4, "body_position_offset": 24,
    }

    # Evidence Source Attribution(Phase M8 #5/#7) 표시용 라벨. 긴 URL이나
    # 원본 asset_type 코드를 그대로 노출하지 않고 짧은 한글 라벨로만 보여준다.
    ASSET_TYPE_LABELS: Dict[str, str] = {
        "social_screenshot": "SNS 게시물 캡처",
        "article_screenshot": "기사 캡처",
        "news": "뉴스 자료",
        "official": "공식 자료",
        "real_photo": "실제 사진",
        "statistic": "통계 자료",
    }

    def __init__(self, config=None):
        super().__init__(config)

        explicit_card_dir = self.config.get("card_news_output_dir")
        self._default_card_dir = (
            Path(explicit_card_dir)
            if explicit_card_dir
            else resolve_external_path("card_news", "renders")
        )
        self.card_dir = self._default_card_dir

        self.width = 1080
        self.height = 1080

        self.layout_selector = LayoutSelector(self.config)
        self.layout_rule_engine = LayoutRuleEngine(self.config)
        self.slide_designer = SlideDesigner(self.config)
        self.highlight_engine = HighlightEngine(self.config)
        self.quality_checker = CardNewsQualityChecker(self.config)
        self.text_optimizer = CardNewsTextOptimizer(self.config)

        # CardNews Intelligence (Phase M7): 새 Workflow/Renderer를 만들지 않고
        # CardNews 단계에만 Intelligence를 추가한다. 아래 4개는 전부 읽기 전용
        # 조회/라벨링 계층이며, 기존 슬라이드 개수/렌더링 파이프라인/CTA 선택
        # 로직을 대체하지 않는다.
        self.evidence_selector = EvidenceSelector(self.config)
        self.social_proof_selector = SocialProofSelector(self.config)
        self.story_flow_planner = StoryFlowPlanner(self.config)
        self.debate_question_selector = DebateQuestionSelector(self.config)

        # CardNews Intelligence (Phase M8: Production Quality): 기존 렌더링
        # 파이프라인은 바꾸지 않고, 이미 계산된 story_flow_result/design_quality_result를
        # 검증/라벨링만 하는 읽기 전용 계층을 추가한다.
        self.visual_rhythm_selector = VisualRhythmSelector(self.config)
        self.mobile_readability_checker = MobileReadabilityChecker(self.config)

        # Knowledge Interface 실제 연결(Sprint 12): 레이아웃 선택/렌더링 로직은 그대로
        # 두고, 축적된 Knowledge DB의 상위 layout 참고 정보만 결과에 덧붙인다.
        self.knowledge_interface = KnowledgeInterface()

    def _ensure_card_dir(self) -> None:
        if self.card_dir == self._default_card_dir and not self.config.get(
            "card_news_output_dir"
        ):
            self.card_dir = resolve_external_path(
                "card_news", "renders", create=True
            )
        else:
            self.card_dir.mkdir(parents=True, exist_ok=True)

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

    def _extract_image_paths(self, image_generation_result: Dict[str, Any]) -> List[Optional[str]]:
        """Return decode-safe image slots without changing their slide order."""
        image_paths: List[Optional[str]] = []
        diagnostics: List[Dict[str, Any]] = []

        if isinstance(image_generation_result, dict):
            images = image_generation_result.get("images", [])

            if isinstance(images, list):
                for index, item in enumerate(images):
                    image_path = None

                    if isinstance(item, dict):
                        image_path = item.get("image_path") or item.get("path")
                    elif isinstance(item, str):
                        image_path = item

                    safe_path, diagnostic = self._validate_image_asset(image_path, index + 1)
                    image_paths.append(safe_path)
                    diagnostics.append(diagnostic)

        self._image_asset_diagnostics = diagnostics

        return image_paths

    def _validate_image_asset(
        self,
        image_path: Any,
        slot: int,
    ) -> "tuple[Optional[str], Dict[str, Any]]":
        diagnostic: Dict[str, Any] = {
            "slot": slot,
            "image_path": str(image_path) if image_path else None,
            "status": "fallback",
            "reason": "image_path_missing",
        }

        if not image_path:
            return None, diagnostic

        path = Path(str(image_path))
        if not path.is_file():
            diagnostic["reason"] = "image_file_missing"
            return None, diagnostic

        try:
            # Force pixel decoding before layout rendering. A corrupt file must be
            # downgraded here rather than retried by both renderer paths.
            with Image.open(path) as candidate:
                candidate.load()
                candidate.convert("RGB")
        except (OSError, ValueError, SyntaxError) as error:
            diagnostic["reason"] = "image_decode_failed"
            diagnostic["error_type"] = type(error).__name__
            return None, diagnostic

        diagnostic["status"] = "validated"
        diagnostic["reason"] = ""
        return str(image_path), diagnostic

    def _create_background(self, image_path: Optional[str], page_number: int):
        image = None

        if image_path:
            try:
                with Image.open(image_path) as source_image:
                    source_image.load()
                    image = source_image.convert("RGB")
                image = image.resize((self.width, self.height))
                image = image.filter(ImageFilter.GaussianBlur(radius=1.2))
            except (OSError, ValueError, SyntaxError) as error:
                # The file may change after preflight. Fall back here instead of
                # raising into _create_card, which would reopen the same bad file.
                self._mark_runtime_image_fallback(image_path, page_number, error)

        if image is None:
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
        box_left = RC.BOX_MARGIN
        box_top = RC.BOX_TOP_DEFAULT
        box_right = self.width - RC.BOX_MARGIN
        box_bottom = RC.BOX_BOTTOM

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
        canonical_role: str = "",
    ):
        # 기존 하드코딩 폰트 값(Phase M8 이전과 동일) - layout-aware 경로가
        # 실패했을 때 쓰이는 안전한 기본 fallback이므로 의도적으로 그대로
        # 유지한다(render_constants.RENDERER_FONT_SIZES와 동일한 값을 공유).
        small_font = self._get_font(RC.RENDERER_FONT_SIZES["small"])
        headline_font = self._get_font(RC.RENDERER_FONT_SIZES["headline"], bold=True)
        body_font = self._get_font(RC.RENDERER_FONT_SIZES["body"])
        brand_font = self._get_font(RC.RENDERER_FONT_SIZES["brand"], bold=True)

        max_width = box_right - box_left - 80

        title_text = self._truncate_with_ellipsis(title, 38)
        subtitle_geometry = self._resolve_subtitle_geometry(
            title_text,
            small_font,
            box_left,
            box_top,
            canonical_role,
        )
        draw.text(
            subtitle_geometry["position"],
            title_text,
            font=small_font,
            fill=RC.PALETTE_COMBINATIONS["light"]["subtitle_color"],
        )

        headline_lines = self._wrap_text(headline, headline_font, max_width)
        body_lines = self._wrap_text(body, body_font, max_width)

        y = box_top + 88
        if self._uses_safe_subtitle_band(canonical_role):
            y = max(y, subtitle_geometry["headline_min_y"])

        light_palette = RC.PALETTE_COMBINATIONS["light"]

        for line in headline_lines[:2]:
            draw.text(
                (box_left + 40, y),
                line,
                font=headline_font,
                fill=light_palette["headline_color"],
            )
            y += 73

        y += 24

        for line in body_lines[:4]:
            draw.text(
                (box_left + 40, y),
                line,
                font=body_font,
                fill=light_palette["body_color"],
            )
            y += 53

        draw.text(
            (box_left + 40, box_bottom - 55),
            "AI-Content-OS",
            font=brand_font,
            fill=light_palette["subtitle_color"],
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
            canonical_role=str(role),
        )

        self._draw_bottom_line(draw)

        return image

    def _mark_runtime_image_fallback(self, image_path: str, page_number: int, error: Exception) -> None:
        diagnostics = getattr(self, "_render_image_diagnostics", [])
        for diagnostic in diagnostics:
            if diagnostic.get("slot") == page_number:
                diagnostic.update({
                    "image_path": image_path,
                    "status": "fallback",
                    "reason": "image_decode_failed_during_render",
                    "error_type": type(error).__name__,
                })
                break

    @staticmethod
    def _truncate_with_ellipsis(text: Any, hard_limit: int) -> str:
        value = str(text or "")
        if hard_limit <= 0:
            return ""
        if len(value) <= hard_limit:
            return value
        if hard_limit == 1:
            return "…"
        return f"{value[: hard_limit - 1].rstrip()}…"

    @classmethod
    def _uses_safe_subtitle_band(cls, canonical_role: Any) -> bool:
        return str(canonical_role or "").strip().lower() in cls.SUBTITLE_CONFLICT_ROLES

    def _resolve_subtitle_geometry(
        self,
        title_text: str,
        font,
        box_left: int,
        box_top: int,
        canonical_role: str,
    ) -> Dict[str, Any]:
        """Return the subtitle ink box and the first overlap-safe headline y."""
        top_inset = (
            self.SUBTITLE_SAFE_TOP_INSET
            if self._uses_safe_subtitle_band(canonical_role)
            else self.SUBTITLE_LEGACY_TOP_INSET
        )
        position = (box_left + 40, box_top + top_inset)
        left, top, right, bottom = font.getbbox(title_text)
        ink_bbox = (
            position[0] + left,
            position[1] + top,
            position[0] + right,
            position[1] + bottom,
        )
        return {
            "position": position,
            "ink_bbox": ink_bbox,
            "headline_min_y": ink_bbox[3] + self.SUBTITLE_HEADLINE_SAFE_GAP,
            "top_inset": top_inset,
        }

    def _create_card(
        self,
        page_number: int,
        title: str,
        slide: Dict[str, Any],
        image_path: Optional[str],
        layout_context: Optional[Dict[str, Any]] = None,
        visual_style: Optional[str] = None,
        narrative_role: str = "",
        attribution: Optional[Dict[str, Any]] = None,
    ) -> "tuple[str, bool]":
        if layout_context:
            try:
                path = self._create_card_with_layout(
                    page_number=page_number,
                    title=title,
                    slide=slide,
                    image_path=image_path,
                    layout_context=layout_context,
                    visual_style=visual_style,
                    narrative_role=narrative_role,
                    attribution=attribution,
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
        visual_style: Optional[str] = None,
        narrative_role: str = "",
        attribution: Optional[Dict[str, Any]] = None,
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
            visual_style=visual_style,
            narrative_role=narrative_role,
            attribution=attribution,
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
        tone = "dark" if background_tone in dark_tones else "light"

        # render_constants.PALETTE_COMBINATIONS를 직접 참조한다(단일 진실
        # 소스) - dict()로 복사해 반환해 호출부가 팔레트를 덮어써도
        # (_create_card_with_layout의 alert_bold 분기) 공용 상수가 오염되지
        # 않게 한다.
        return dict(RC.PALETTE_COMBINATIONS[tone])

    def _hex_to_rgb(self, hex_color: str):
        hex_color = str(hex_color or "").lstrip("#")

        if len(hex_color) != 6:
            raise ValueError(f"invalid hex color: {hex_color}")

        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    def _draw_layout_card_box(self, draw, box_fill, box_top: Optional[int] = None):
        box_left = RC.BOX_MARGIN
        box_top = box_top if box_top is not None else RC.BOX_TOP_DEFAULT
        box_right = self.width - RC.BOX_MARGIN
        box_bottom = RC.BOX_BOTTOM

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

    def _fit_lines(
        self,
        text: str,
        font_size_range: "tuple[int, int]",
        max_lines: int,
        max_width: int,
        bold: bool = False,
        hard_max_lines: Optional[int] = None,
    ) -> "tuple[List[str], int]":
        """
        CardNews Intelligence (Phase M8: Production Quality) - Typography 글자 수
        초과 처리. 요구된 순서를 그대로 따른다:

        1. 반복·군더더기 제거(인접 중복 문장 제거)
        2~4. 문장 수 축소 + 줄바꿈 재계산을 번갈아 반복(뒤쪽 보조 문장부터
             제거하면서 매번 실제 wrap 결과를 다시 계산)
        5. 그래도 넘치면 허용 범위(font_size_range) 안에서 폰트를 축소
        6. 그래도 안 되면 최소 폰트에서 실제 줄바꿈된 내용을 그대로 사용한다

        max_lines는 Visual Rhythm 스타일이 선호하는(더 타이트할 수 있는) 줄
        수이고, hard_max_lines는 typography_rules role 자체의 원래 줄 수
        상한이다(기본값 = max_lines). 문장이 1개뿐이라 더는 줄일 수 없는데
        최소 폰트에서도 style이 원하는 max_lines를 넘기면, 임의로 뒷부분을
        잘라 의미를 바꾸는 대신 hard_max_lines까지는 그대로 보여준다 -
        "텍스트를 잘라 의미가 달라지게 하지 않는다"는 요구사항이 줄 수
        선호보다 우선한다. hard_max_lines마저 넘는 경우에만(사실상 발생하지
        않는 극단적 예외) 그 상한에서 자른다.
        """
        text = str(text or "").strip()
        hard_max_lines = hard_max_lines if hard_max_lines is not None else max_lines

        if not text:
            return [], font_size_range[1]

        # 숫자 바로 뒤의 종결 부호("1." "2." 같은 번호 목록)는 문장 경계로
        # 보지 않는다 - card_news_text_optimizer.SENTENCE_SPLIT_PATTERN과
        # 동일한 이유(번호만 남고 내용이 잘려나가는 결함 방지).
        raw_parts = re.split(r"(?<=[^\d][.!?。!?])\s+|\n+", text)
        sentences = [part.strip() for part in raw_parts if part and part.strip()]

        deduped: List[str] = []
        seen = set()
        for sentence in sentences:
            key = re.sub(r"\s+", "", sentence).lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(sentence)

        if not deduped:
            deduped = [text]

        max_font, min_font = font_size_range[1], font_size_range[0]
        font = self._get_font(max_font, bold=bold)
        lines = self._wrap_text(" ".join(deduped), font, max_width)

        while len(lines) > max_lines and len(deduped) > 1:
            deduped = deduped[:-1]
            lines = self._wrap_text(" ".join(deduped), font, max_width)

        if len(lines) <= max_lines:
            return lines, max_font

        font_size = max_font - 2
        while font_size >= min_font:
            font = self._get_font(font_size, bold=bold)
            lines = self._wrap_text(" ".join(deduped), font, max_width)
            if len(lines) <= max_lines:
                return lines, font_size
            font_size -= 2

        font = self._get_font(min_font, bold=bold)
        lines = self._wrap_text(" ".join(deduped), font, max_width)

        if len(lines) <= hard_max_lines:
            return lines, min_font

        # 최소 폰트에서도 hard_max_lines를 넘는 극단적 예외(문장 경계가 전혀
        # 없는 매우 긴 한 덩어리 텍스트 등)에서만 도달한다. 이 경우에도 잘린
        # 사실 자체를 숨기지 않기 위해 마지막 줄에 말줄임표(…)를 붙인다 -
        # "조용히" 잘리지 않게 하는 최소한의 시각적 표시(Codex 리뷰 지적 반영).
        truncated_lines = lines[:hard_max_lines]

        if truncated_lines:
            last_line = truncated_lines[-1].rstrip()
            ellipsis_line = f"{last_line}…"

            while ellipsis_line and self._text_width(ellipsis_line, font) > max_width and len(last_line) > 1:
                last_line = last_line[:-1].rstrip()
                ellipsis_line = f"{last_line}…"

            truncated_lines[-1] = ellipsis_line or "…"

        return truncated_lines, min_font

    def _plan_text_layout(
        self,
        headline: str,
        body: str,
        canonical_role: str,
        narrative_role: str,
        style_profile: Dict[str, Any],
        body_prefix: str,
        max_width: int,
    ) -> Dict[str, Any]:
        """
        CardNews Intelligence (Phase M8: Production Quality) - 실제로 박스를
        그리기 전에 headline/body가 몇 줄이 될지 먼저 계산한다.

        Visual Rhythm 스타일이 선호하는 좁은 줄 수 예산(style_profile의
        headline_max_lines/body_max_lines)을 못 맞춰 `_fit_lines`가
        hard_max_lines(typography role 자체 상한)까지 늘어난 경우, 그
        스타일의 좁은 box_top을 그대로 쓰면 늘어난 텍스트가 하단 브랜드/출처
        표기와 겹칠 수 있다 - style_overflowed가 True면 box_top을 기본값
        (DEFAULT_VISUAL_STYLE_PROFILE)으로 안전하게 완화한다. 스타일이 원한
        것보다 실제 텍스트가 길 때만 발생하는 예외적 경로다.
        """
        headline_role = resolve_typography_role(canonical_role, narrative_role, True)
        body_role = resolve_typography_role(canonical_role, narrative_role, False)
        headline_rule = TYPOGRAPHY_ROLES.get(headline_role, TYPOGRAPHY_ROLES["slide_title"])
        body_rule = TYPOGRAPHY_ROLES.get(body_role, TYPOGRAPHY_ROLES["body"])

        headline_max_lines = max(1, min(headline_rule["max_lines"], style_profile.get("headline_max_lines", headline_rule["max_lines"])))
        body_max_lines = max(1, min(body_rule["max_lines"], style_profile.get("body_max_lines", body_rule["max_lines"])))

        # quote_card 스타일은 이미 _apply_social_proof_quote가 "[라벨] 텍스트
        # - @계정" 형태로 인용부호를 포함해 만들어 둔다 - 체크리스트/화살표 같은
        # body_prefix를 덧붙이면 인용 카드 형태가 깨지므로 적용하지 않는다.
        if style_profile.get("quote_mark"):
            body_prefix = ""

        body_text = f"{body_prefix}{body}" if body_prefix else body

        headline_lines, headline_font_size = self._fit_lines(
            headline, headline_rule["font_size_range"], headline_max_lines, max_width, bold=True,
            hard_max_lines=headline_rule["max_lines"],
        )
        body_lines, body_font_size = self._fit_lines(
            body_text, body_rule["font_size_range"], body_max_lines, max_width, bold=False,
            hard_max_lines=body_rule["max_lines"],
        )

        style_overflowed = len(headline_lines) > headline_max_lines or len(body_lines) > body_max_lines
        effective_box_top = (
            self.DEFAULT_VISUAL_STYLE_PROFILE["box_top"]
            if style_overflowed
            else style_profile.get("box_top", self.DEFAULT_VISUAL_STYLE_PROFILE["box_top"])
        )

        return {
            "headline_lines": headline_lines,
            "headline_font_size": headline_font_size,
            "headline_rule": headline_rule,
            "body_lines": body_lines,
            "body_font_size": body_font_size,
            "body_rule": body_rule,
            "style_overflowed": style_overflowed,
            "effective_box_top": effective_box_top,
        }

    def _draw_layout_text_content(
        self,
        draw,
        title: str,
        box_left: int,
        box_top: int,
        box_right: int,
        box_bottom: int,
        palette: Dict[str, Any],
        title_position: str,
        body_position: str,
        style_profile: Dict[str, Any],
        layout_plan: Dict[str, Any],
        canonical_role: str = "",
        attribution: Optional[Dict[str, Any]] = None,
    ):
        small_font = self._get_font(RC.RENDERER_FONT_SIZES["small"])
        brand_font = self._get_font(RC.RENDERER_FONT_SIZES["brand"], bold=True)

        title_position_offsets = {"top": 0, "center": 20, "bottom": 30}
        body_position_offsets = {"below_title": 0, "middle": 10, "bottom": 20}

        title_text = self._truncate_with_ellipsis(title, 38)
        subtitle_geometry = self._resolve_subtitle_geometry(
            title_text,
            small_font,
            box_left,
            box_top,
            canonical_role,
        )
        draw.text(
            subtitle_geometry["position"],
            title_text,
            font=small_font,
            fill=palette["subtitle_color"],
        )

        headline_lines = layout_plan["headline_lines"]
        headline_rule = layout_plan["headline_rule"]
        headline_font = self._get_font(layout_plan["headline_font_size"], bold=True)
        headline_line_height = max(1, int(round(layout_plan["headline_font_size"] * headline_rule["line_spacing"])))

        body_lines = layout_plan["body_lines"]
        body_rule = layout_plan["body_rule"]
        body_font = self._get_font(layout_plan["body_font_size"])
        body_line_height = max(1, int(round(layout_plan["body_font_size"] * body_rule["line_spacing"])))

        y = box_top + 88 + title_position_offsets.get(title_position, 0)
        if self._uses_safe_subtitle_band(canonical_role):
            y = max(y, subtitle_geometry["headline_min_y"])

        for line in headline_lines:
            draw.text((box_left + 40, y), line, font=headline_font, fill=palette["headline_color"])
            y += headline_line_height

        y += (
            headline_rule["paragraph_spacing"]
            + style_profile.get("body_position_offset", 24)
            + body_position_offsets.get(body_position, 0)
        )

        for line in body_lines:
            draw.text((box_left + 40, y), line, font=body_font, fill=palette["body_color"])
            y += body_line_height

        brand_y = box_bottom - 55

        # Source Attribution(Phase M8 #5/#7): render_allowed=True인 evidence가
        # 실제로 이 슬라이드에 적용됐을 때만 하단 안전영역에 짧게 표시한다.
        # source_url(긴 URL)은 절대 출력하지 않는다 - attribution이 없으면
        # (미적용/미허용) 이 블록 자체를 그리지 않는다.
        if attribution and attribution.get("source_name"):
            source_rule = TYPOGRAPHY_ROLES["source"]
            source_font = self._get_font(source_rule["font_size_range"][1])
            source_label = f"{attribution.get('source_type', '참고 자료')} · {attribution['source_name']}"
            source_label = source_label[: source_rule["max_chars"]]
            draw.text((box_left + 40, brand_y - 38), source_label, font=source_font, fill=palette["subtitle_color"])

        draw.text(
            (box_left + 40, brand_y),
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
        visual_style: Optional[str] = None,
        narrative_role: str = "",
        attribution: Optional[Dict[str, Any]] = None,
    ):
        draw = ImageDraw.Draw(image)

        role = slide.get("role", "card")
        headline = slide.get("headline", f"{page_number}장 제목")
        body = slide.get("body", f"{page_number}장 본문")

        self._draw_top_badge(draw, page_number, role)

        highlights = (slide_highlight or {}).get("highlights", []) or []
        self._draw_highlight_tags(draw, highlights, rule.get("highlight_color", "#ffd60a"))

        # Human Visual Rhythm(Phase M8 #1) 실제 반영: VisualRhythmSelector가
        # 고른(그리고 _resolve_visual_rhythm_application이 실제 데이터 유무로
        # 재확인한) 스타일의 box_top/줄 수 상한만 기존 draw 함수에 다르게
        # 넘긴다 - 새 Renderer가 아니라 같은 _draw_layout_card_box/
        # _draw_layout_text_content를 다른 파라미터로 재사용한다. 박스를
        # 그리기 전에 텍스트 줄 수를 먼저 계산해(_plan_text_layout), 실제
        # 텍스트가 스타일이 원하는 것보다 길면 box_top을 안전한 기본값으로
        # 완화한다 - 좁은 스타일 박스에 텍스트가 넘쳐 브랜드 표기와 겹치는
        # 것을 막기 위함이다.
        style_profile = self.VISUAL_STYLE_PROFILES.get(visual_style or "", self.DEFAULT_VISUAL_STYLE_PROFILE)

        body_style_prefixes = {
            "checklist_items": "✓ ",
            "step_by_step": "→ ",
            "warning_box": "[주의] ",
            "timeline_marker": "● ",
        }
        body_prefix = body_style_prefixes.get(str(rule.get("body_style", "")), "")

        box_left = RC.BOX_MARGIN
        box_right = self.width - RC.BOX_MARGIN
        max_width = box_right - box_left - 80

        layout_plan = self._plan_text_layout(
            headline=headline,
            body=body,
            canonical_role=str(role),
            narrative_role=narrative_role,
            style_profile=style_profile,
            body_prefix=body_prefix,
            max_width=max_width,
        )

        box_left, box_top, box_right, box_bottom = self._draw_layout_card_box(
            draw, palette["box_fill"], box_top=layout_plan["effective_box_top"]
        )

        title_position = str((slide_design or {}).get("title_position", "top"))
        body_position = str((slide_design or {}).get("body_position", "middle"))

        self._draw_layout_text_content(
            draw=draw,
            title=title,
            box_left=box_left,
            box_top=box_top,
            box_right=box_right,
            box_bottom=box_bottom,
            palette=palette,
            title_position=title_position,
            body_position=body_position,
            style_profile=style_profile,
            layout_plan=layout_plan,
            canonical_role=str(role),
            attribution=attribution,
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

    @staticmethod
    def _extract_cta_text(slides: List[Dict[str, Any]]) -> str:
        for slide in slides:
            if isinstance(slide, dict) and str(slide.get("role", "")).lower() == "cta":
                return " ".join(
                    part for part in (
                        str(slide.get("headline", "") or "").strip(),
                        str(slide.get("body", "") or "").strip(),
                    ) if part
                )
        return ""

    @staticmethod
    def _align_cta_slide_to_save(slides: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Keep the renderer's SAVE badge and CTA copy on one explicit action."""
        aligned = [dict(slide) if isinstance(slide, dict) else slide for slide in slides]
        diagnostics = {
            "status": "unchanged",
            "primary_intent": "",
            "detected_intents": [],
            "original_body": "",
        }
        for slide in aligned:
            if not isinstance(slide, dict) or str(slide.get("role", "")).lower() != "cta":
                continue
            headline = str(slide.get("headline", "") or "")
            body = str(slide.get("body", "") or "")
            text = f"{headline} {body}"
            detected = [
                intent
                for intent, pattern in DebateQuestionSelector.CTA_INTENT_PATTERNS.items()
                if pattern.search(text)
            ]
            diagnostics["detected_intents"] = detected
            diagnostics["original_body"] = body
            if "save" in detected and any(intent != "save" for intent in detected):
                slide["body"] = "나중에 다시 볼 수 있도록 저장해 두세요."
                diagnostics.update({
                    "status": "normalized",
                    "primary_intent": "save",
                    "reason": "SAVE 배지와 충돌하는 추가 CTA 행동을 제거함.",
                })
            elif detected:
                diagnostics["primary_intent"] = detected[0]
            break
        return aligned, diagnostics

    @staticmethod
    def _apply_evidence_safe_copy(
        slides: List[Dict[str, Any]],
        evidence_result: Dict[str, Any],
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Replace unsupported factual copy with an explicit pre-verification flow."""
        if evidence_result.get("evidence_available") is True:
            return slides, {"applied": False, "reason": "evidence_available"}
        safe_slides = [
            {
                "role": "hook",
                "headline": "이 주제, 바로 써도 될까요?",
                "body": "출처와 맥락 확인이 먼저입니다.",
            },
            {
                "role": "problem",
                "headline": "제목만으로는 판단 못 합니다",
                "body": "원문과 게시일이 없으면 의미를 단정하기 어렵습니다.",
            },
            {
                "role": "solution",
                "headline": "출처부터 다시 확인하세요",
                "body": "원문, 게시일, 실제 반응을 확인한 뒤 핵심만 정리하세요.",
            },
            {
                "role": "cta",
                "headline": "확인 전에는 발행하지 마세요",
                "body": "근거가 확보되면 저장하세요.",
            },
        ]
        return safe_slides, {
            "applied": True,
            "reason": "topic_evidence_unavailable",
            "claim_policy": "unsupported_factual_copy_replaced",
        }

    def _select_debate_question(self, pattern_type: Any, cta_type: Any, cta_text: str) -> Dict[str, Any]:
        """Use the optional CTA-text contract while accepting the legacy selector."""
        select = self.debate_question_selector.select
        try:
            parameters = signature(select).parameters.values()
            supports_cta_text = any(
                parameter.name == "cta_text" or parameter.kind == Parameter.VAR_KEYWORD
                for parameter in parameters
            )
        except (TypeError, ValueError):
            supports_cta_text = False

        if supports_cta_text:
            result = select(pattern_type, cta_type, cta_text=cta_text)
            detected = [
                intent
                for intent in result.get("detected_cta_intents", [])
                if intent != "comment"
            ] if isinstance(result, dict) else []
            source_cta_type = str(cta_type or "").strip().lower()
            if len(detected) == 1 and detected[0] != source_cta_type:
                effective_cta_type = detected[0]
                normalized = select(
                    pattern_type,
                    effective_cta_type,
                    cta_text=cta_text,
                )
                if isinstance(normalized, dict):
                    normalized["source_cta_type"] = source_cta_type
                    normalized["effective_cta_type"] = effective_cta_type
                    normalized["cta_type_normalized"] = True
                    normalized["cta_alignment_status"] = "aligned_to_explicit_text"
                    normalized["normalization_reason"] = (
                        "CTA 문안의 단일 명시 행동을 CardNews 표시 목적과 정렬함."
                    )
                    return normalized
            if isinstance(result, dict):
                result.setdefault("source_cta_type", source_cta_type)
                result.setdefault("effective_cta_type", source_cta_type)
                result.setdefault("cta_type_normalized", False)
                result.setdefault("cta_alignment_status", "unchanged")
            return result
        return select(pattern_type, cta_type)

    def _build_image_asset_diagnostics(self) -> Dict[str, Any]:
        candidates = [dict(item) for item in getattr(self, "_image_asset_diagnostics", [])]
        assets = [dict(item) for item in getattr(self, "_render_image_diagnostics", [])]
        validated_count = sum(1 for item in assets if item.get("status") == "validated")
        fallback_count = len(assets) - validated_count
        return {
            "input_count": len(candidates),
            "render_slot_count": len(assets),
            "validated_count": validated_count,
            "fallback_count": fallback_count,
            "fallback_used": fallback_count > 0,
            "assets": assets,
            "input_assets": candidates,
        }

    def _prepare_rendering_image_paths(
        self,
        image_paths: List[Optional[str]],
    ) -> List[Optional[str]]:
        prepared: List[Optional[str]] = []
        diagnostics: List[Dict[str, Any]] = []
        for index in range(4):
            image_path = image_paths[index] if index < len(image_paths) else None
            safe_path, diagnostic = self._validate_image_asset(image_path, index + 1)
            prepared.append(safe_path)
            diagnostics.append(diagnostic)
        self._render_image_diagnostics = diagnostics
        return prepared

    def _source_image_for_card(self, image_path: Optional[str], page_number: int) -> Optional[str]:
        if not image_path:
            return None
        for diagnostic in getattr(self, "_render_image_diagnostics", []):
            if diagnostic.get("slot") == page_number and diagnostic.get("status") != "validated":
                return None
        return image_path

    def run(
        self,
        content_result: Dict[str, Any],
        image_generation_result: Dict[str, Any],
        image_strategy_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Card News Module Started")
        self._ensure_card_dir()

        title = self._extract_title(content_result)
        slides = self._extract_slides(content_result)
        slides, cta_alignment_result = self._align_cta_slide_to_save(slides)
        image_paths = self._extract_image_paths(image_generation_result)

        # CardNews Intelligence (Phase M7): pattern_type/cta_type은 ContentModule이
        # 이미 계산해 content_result에 실어 둔 값(pattern_prompt_meta)을 그대로
        # 재사용한다 - _compute_layout_result()가 이미 쓰는 것과 동일한 소스.
        pattern_meta = content_result.get("pattern_prompt_meta") or {} if isinstance(content_result, dict) else {}
        pattern_type = pattern_meta.get("pattern_type", "")
        cta_type = pattern_meta.get("cta_type", "")

        valid_image_paths = [image_path for image_path in image_paths if image_path]
        evidence_result = self.evidence_selector.select(image_strategy_result, valid_image_paths)
        slides, evidence_copy_guard = self._apply_evidence_safe_copy(slides, evidence_result)
        slides, cta_alignment_result = self._align_cta_slide_to_save(slides)
        layout_result = self._build_layout_result(content_result, slides)
        layout_context, rendering_notes = self._build_layout_context(layout_result)
        social_proof_result = self.social_proof_selector.select()
        debate_result = self._select_debate_question(
            pattern_type,
            cta_type,
            self._extract_cta_text(slides),
        )
        story_flow_result = self.story_flow_planner.plan(
            slides,
            evidence_available=bool(evidence_result.get("evidence_available")),
            social_proof_available=bool(social_proof_result.get("available")),
            debate_will_apply=bool(debate_result.get("should_apply")),
        )

        optimized = self._optimize_slides_for_rendering(slides)
        rendering_slides = optimized.get("slides") or slides
        rendering_slides, debate_result = self._apply_debate_question(rendering_slides, debate_result)
        rendering_slides, social_proof_applied = self._apply_social_proof_quote(
            rendering_slides, social_proof_result, story_flow_result
        )
        design_quality_result = self._build_design_quality_result(optimized)
        self._apply_layout_quality_score(layout_result, design_quality_result)

        typography_result = self._build_typography_result(rendering_slides, story_flow_result)
        visual_rhythm_result = self.visual_rhythm_selector.select(story_flow_result.get("applied_roles"))
        mobile_readability_result = self.mobile_readability_checker.check(design_quality_result)

        rendering_image_paths, evidence_applied = self._apply_evidence_asset(
            list(image_paths), evidence_result, story_flow_result
        )
        rendering_image_paths = self._prepare_rendering_image_paths(rendering_image_paths)

        if evidence_applied:
            top_asset = evidence_result.get("top_evidence_asset") or {}
            evidence_path = top_asset.get("asset_path") if isinstance(top_asset, dict) else None
            if not evidence_path or evidence_path not in rendering_image_paths:
                evidence_applied = False
                if isinstance(top_asset, dict):
                    top_asset["applied"] = False
                    top_asset["render_rejection_reason"] = "image_decode_failed"

        # Phase M8 (Production Quality) 실제 렌더링 반영: 선택된 스타일이 실제
        # 이번 카드뉴스 데이터로 적용 가능한지 재확인하고(quote_card/comparison/
        # image_focus는 실제 데이터가 없으면 안전한 스타일로 대체), 어떤 페이지가
        # 실제 evidence 출처를 표시해도 되는지 계산한다.
        visual_rhythm_application = self._resolve_visual_rhythm_application(
            visual_rhythm_result, rendering_image_paths, evidence_applied, social_proof_applied, story_flow_result
        )
        visual_rhythm_result["applied_assignments"] = list(visual_rhythm_application.values())

        narrative_by_page = {
            item.get("page"): item.get("narrative_role")
            for item in (story_flow_result or {}).get("applied_roles") or []
            if isinstance(item, dict)
        }
        attribution_by_page = self._build_attribution_by_page(evidence_result, story_flow_result, evidence_applied)

        cards = []
        layout_applied_count = 0

        for index in range(4):
            page_number = index + 1
            slide = rendering_slides[index] if index < len(rendering_slides) else {
                "page": page_number,
                "role": "card",
                "headline": f"{page_number}장 제목",
                "body": f"{page_number}장 본문",
            }

            image_path = rendering_image_paths[index] if index < len(rendering_image_paths) else None

            style_info = visual_rhythm_application.get(page_number) or {}
            applied_style = style_info.get("applied_style", VisualRhythmSelector.DEFAULT_STYLE)
            narrative_role = str(narrative_by_page.get(page_number, "") or "")
            attribution = attribution_by_page.get(page_number)

            card_path, used_layout = self._create_card(
                page_number=page_number,
                title=title,
                slide=slide,
                image_path=image_path,
                layout_context=layout_context,
                visual_style=applied_style,
                narrative_role=narrative_role,
                attribution=attribution,
            )

            if used_layout:
                layout_applied_count += 1

            cards.append({
                "index": index + 1,
                "card_path": card_path,
                "source_image": self._source_image_for_card(image_path, page_number),
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
        result["evidence_result"] = evidence_result
        result["evidence_applied"] = evidence_applied
        result["evidence_copy_guard"] = evidence_copy_guard
        result["social_proof_result"] = social_proof_result
        result["social_proof_applied"] = social_proof_applied
        result["story_flow_result"] = story_flow_result
        result["debate_result"] = debate_result
        result["cta_alignment_result"] = cta_alignment_result
        result["typography_result"] = typography_result
        result["visual_rhythm_result"] = visual_rhythm_result
        result["mobile_readability_result"] = mobile_readability_result
        result["attribution_present"] = bool(evidence_applied or social_proof_applied)
        self._apply_knowledge_consumption(result)
        result["card_news_quality"] = self._build_card_news_quality(result)
        result["image_sourcing_status"] = self._build_image_sourcing_status(image_strategy_result or {}, cards)
        result["image_asset_diagnostics"] = self._build_image_asset_diagnostics()
        result["planner_influence"] = self._build_planner_influence(content_result, image_strategy_result)

        print("Card News Module Finished")
        return result

    def _build_planner_influence(
        self,
        content_result: Dict[str, Any],
        image_strategy_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        AI Planner Consumer Adapter 실제 연결(Sprint 15-3): CardNewsModule 자체는
        Planner Hint를 소비하지 않는다(고를 만한 새로운 선택지가 없음) - 대신
        이미 Content/Image Strategy 단계에서 기록된 `planner_consumption`을
        모아 "이번 카드뉴스에 Planner 영향이 실제로 있었는지"만 요약한다.
        렌더링 로직은 전혀 건드리지 않는다.
        """
        try:
            content_consumption = {}
            if isinstance(content_result, dict):
                content_consumption = (content_result.get("planner_consumption") or {}).get("content", {}) or {}

            image_strategy_consumption = {}
            if isinstance(image_strategy_result, dict):
                image_strategy_consumption = (
                    image_strategy_result.get("planner_consumption") or {}
                ).get("image_strategy", {}) or {}

            # content_consumption은 image_strategy_consumption과 달리 평평한 단일
            # 메타데이터 dict가 아니라 {"hook": {...}, "cta": {...},
            # "content_strategy": {...}} 형태로 중첩되어 있다(Content Engine이 세
            # 가지를 독립적으로 판정하므로) - 최상위에 "planner_applied" 키가 직접
            # 있는 게 아니라 각 하위 항목 안에 있다. Codex 검수에서 지적된 대로,
            # 하위 항목을 확인하지 않으면 Content가 실제로 Hint를 적용했어도
            # any_hint_applied가 항상 False로 잘못 계산된다.
            content_hint_applied = any(
                bool(item.get("planner_applied"))
                for item in content_consumption.values()
                if isinstance(item, dict)
            )

            any_hint_applied = content_hint_applied or bool(image_strategy_consumption.get("planner_applied"))

            return {
                "any_hint_applied": any_hint_applied,
                "content": content_consumption,
                "image_strategy": image_strategy_consumption,
            }
        except Exception as error:
            print(f"Card News Planner Influence Summary Failed: {error}")
            return {
                "any_hint_applied": False,
                "content": {},
                "image_strategy": {},
                "reason": f"planner_influence 계산 실패: {error}",
            }

    def _build_image_sourcing_status(
        self,
        image_strategy_result: Dict[str, Any],
        cards: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Image Strategy 후속 보강(Sprint 13): 실제 이미지 자동수집은 하지 않지만,
        Image Strategy가 만든 `image_usage_plan`을 실제로 읽어 이번 카드뉴스가
        그 계획대로 실제 이미지를 사용했는지 확인한다. 계획(real_image_required)과
        실제(사용된 이미지 없음)가 어긋나면 `manual_image_required` 체크리스트를
        남긴다 - 생성 자체를 막지는 않는다.
        """
        try:
            need_ai_image = image_strategy_result.get("need_ai_image", True)
            recommended_source = image_strategy_result.get("image_source", "")
            content_type = image_strategy_result.get("content_type", "")

            real_image_used_count = sum(1 for card in cards if card.get("source_image"))

            if need_ai_image:
                return {
                    "manual_image_required": False,
                    "recommended_source": recommended_source,
                    "real_image_used_count": real_image_used_count,
                    "checklist": [],
                    "reason": "Image Strategy가 AI 이미지 생성 경로를 선택함 - 수동 이미지 소싱 불필요.",
                }

            if real_image_used_count > 0:
                return {
                    "manual_image_required": False,
                    "recommended_source": recommended_source,
                    "real_image_used_count": real_image_used_count,
                    "checklist": [],
                    "reason": f"실제 이미지 {real_image_used_count}건이 이미 사용되어 수동 소싱이 필요 없음.",
                }

            return {
                "manual_image_required": True,
                "recommended_source": recommended_source,
                "real_image_used_count": 0,
                "checklist": [
                    f"권장 이미지 소스({recommended_source})를 수동으로 수집해 카드뉴스에 반영하세요.",
                    "실제 이미지가 없어 이번 렌더링은 solid-color 배경으로 대체되었습니다.",
                ],
                "reason": f"content_type '{content_type}'은 실제 이미지가 필요하지만 아직 소싱되지 않음.",
            }
        except Exception as error:
            print(f"Card News Image Sourcing Status Failed: {error}")
            return {
                "manual_image_required": False,
                "recommended_source": "",
                "real_image_used_count": 0,
                "checklist": [],
                "reason": f"image_sourcing_status 계산 실패: {error}",
            }

    def _apply_knowledge_consumption(self, result: Dict[str, Any]) -> None:
        """
        Knowledge DB 실제 소비(Sprint 13): 이번에 선택된 layout_type이 Knowledge DB
        상위 layout과 일치하면 layout_quality_score를 소폭 보정한다(+0.03, 최대 1.0).
        레이아웃 선택/렌더링 로직 자체는 바꾸지 않는다 - 이미 검증된 layout을 살짝
        더 신뢰하는 보정만 추가한다. 실패해도 result는 그대로 유지된다.
        """
        try:
            layout_result = result.get("layout_result") or {}
            layout_type = layout_result.get("layout_type", "")

            top_layouts = self.knowledge_interface.get_layout_knowledge(limit=5)
            matched = next(
                (
                    item for item in top_layouts
                    if (item.get("content") or {}).get("layout_type") == layout_type
                ),
                None,
            )

            if matched:
                old_score = float(layout_result.get("layout_quality_score", 0.0) or 0.0)
                boosted_score = min(1.0, round(old_score + 0.03, 4))
                layout_result["layout_quality_score"] = boosted_score
                influence = (
                    f"layout_type '{layout_type}'가 Knowledge DB 상위 layout과 일치해 "
                    f"layout_quality_score를 {old_score} -> {boosted_score}로 보정함."
                )
            else:
                influence = "Knowledge DB 상위 layout과 일치하는 항목이 없어 layout_quality_score는 그대로 둠."

            result["layout_result"] = layout_result
            result["knowledge_used"] = bool(top_layouts)
            result["knowledge_items"] = [
                {
                    "knowledge_id": item.get("knowledge_id"),
                    "type": item.get("type"),
                    "title": item.get("title"),
                }
                for item in top_layouts
            ]
            result["knowledge_influence"] = influence
        except Exception as error:
            print(f"Card News Knowledge Consumption Failed: {error}")
            result.setdefault("knowledge_used", False)
            result.setdefault("knowledge_items", [])
            result.setdefault("knowledge_influence", f"knowledge consumption 실패: {error}")

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

    def _apply_debate_question(
        self,
        slides: List[Dict[str, Any]],
        debate_result: Optional[Dict[str, Any]],
    ) -> "tuple[List[Dict[str, Any]], Dict[str, Any]]":
        """
        Debate Engine (Phase M7 - 실제 사용 연결): CTA 슬라이드의 body에 debate
        질문을 "추가"한다(CTA 문구를 대체하지 않음). `debate_result.
        should_apply`가 False면(redundant cta_type 등 이미 걸러진 경우) 아예
        시도하지 않는다. Text Optimizer가 이미 문장 수를 정리한 뒤
        (rendering_slides, 즉 최적화 이후 슬라이드)에 적용해 CTA_MAX_SENTENCES
        트림으로 질문이 잘려나가지 않도록 하되, 여기서 다시 한번 실제 글자 수
        예산(BODY_LINE_MAX_LENGTH * CTA_MAX_SENTENCES, Text Optimizer와 동일한
        기준 재사용)을 초과하면 질문을 넣지 않는다. 새 draw 로직을 추가하지
        않고 기존 `_draw_text_content`/`_draw_layout_text_content`가 그대로
        렌더링할 body 텍스트만 확장한다 - 기존 Renderer를 그대로 재사용한다.

        반환값의 debate_result는 실제로 적용됐는지(`applied`)를 최종 확정해
        되돌려준다 - Quality Checker가 "가능했는데 적용 안 함"과 "애초에
        적용 대상이 아니었음"을 구분할 수 있게 하기 위함이다.
        """
        debate_result = dict(debate_result or {})
        question = str(debate_result.get("question", "")).strip()

        if not debate_result.get("should_apply") or not question:
            debate_result["applied"] = False
            debate_result.setdefault(
                "skip_reason", debate_result.get("skip_reason") or "should_apply=False라 시도하지 않음."
            )
            return slides, debate_result

        try:
            max_budget = self.text_optimizer.BODY_LINE_MAX_LENGTH * self.text_optimizer.CTA_MAX_SENTENCES

            updated_slides: List[Dict[str, Any]] = []
            applied = False

            for slide in slides:
                if isinstance(slide, dict) and slide.get("role") == "cta" and not applied:
                    body = str(slide.get("body", "")).strip()
                    candidate_body = f"{body} {question}".strip() if body else question

                    if len(candidate_body) > max_budget:
                        updated_slides.append(slide)
                        debate_result["applied"] = False
                        debate_result["skip_reason"] = (
                            f"CTA 슬라이드 글자 수 예산({max_budget}자)을 초과해 debate 질문을 추가하지 않음."
                        )
                        applied = True  # 더 이상 다른 cta 슬라이드에 시도하지 않도록 루프만 종료
                        continue

                    new_slide = dict(slide)
                    new_slide["body"] = candidate_body
                    updated_slides.append(new_slide)
                    debate_result["applied"] = True
                    debate_result["skip_reason"] = ""
                    applied = True
                else:
                    updated_slides.append(slide)

            if not applied:
                debate_result["applied"] = False
                debate_result["skip_reason"] = "CTA 슬라이드를 찾지 못해 debate 질문을 추가하지 않음."

            return updated_slides, debate_result
        except Exception as error:
            print(f"Card News Debate Question Apply Failed: {error}")
            debate_result["applied"] = False
            debate_result["skip_reason"] = f"적용 중 예외 발생: {error}"
            return slides, debate_result

    def _apply_evidence_asset(
        self,
        image_paths: List[Optional[str]],
        evidence_result: Optional[Dict[str, Any]],
        story_flow_result: Optional[Dict[str, Any]],
    ) -> "tuple[List[Optional[str]], bool]":
        """
        Evidence Selection (Phase M7 - 실제 사용 연결): 실제로 디스크에 존재하는
        evidence 자산(evidence_result.top_evidence_asset, Path.exists()로 이미
        확인됨)이 있으면 StoryFlowPlanner가 "evidence" narrative_role을 부여한
        슬라이드의 배경 이미지로 그 자산을 사용한다. 새 렌더링 로직을 추가하지
        않는다 - 기존 `_create_background()`가 이미 image_path 유무/존재
        여부에 따라 실제 이미지 또는 solid-color로 안전하게 fallback하는
        로직을 그대로 재사용한다(이 메서드는 어떤 image_path를 넘길지만
        결정한다). evidence가 unavailable이면 기존 image_paths를 그대로
        둔다(AI 생성 이미지/None 유지) - 감점 대상이 아니다.
        """
        try:
            evidence_result = evidence_result or {}
            top_asset = evidence_result.get("top_evidence_asset")

            if not isinstance(top_asset, dict) or not top_asset.get("available"):
                return image_paths, False

            # 이중 방어(Phase M7 Evidence 오사용 방지 보정): available 플래그
            # 하나만 믿지 않고, 실제 렌더링에 반영하기 직전에 asset_role/
            # render_allowed/candidate_found를 다시 한번 명시적으로 확인한다.
            # "파일이 존재한다"와 "실제로 써도 된다"를 같은 값으로 취급하지
            # 않기 위한 안전장치다.
            if top_asset.get("asset_role") != "topic_evidence":
                return image_paths, False

            if not top_asset.get("render_allowed"):
                return image_paths, False

            if not top_asset.get("candidate_found"):
                return image_paths, False

            asset_path = top_asset.get("asset_path")

            if not asset_path or not Path(asset_path).exists():
                return image_paths, False

            evidence_page = self._find_narrative_page(story_flow_result, "evidence")

            if evidence_page is None:
                return image_paths, False

            updated_paths = list(image_paths)
            index = evidence_page - 1

            if 0 <= index < len(updated_paths):
                updated_paths[index] = asset_path
                top_asset["applied"] = True
                return updated_paths, True

            return image_paths, False
        except Exception as error:
            print(f"Card News Evidence Asset Apply Failed: {error}")
            return image_paths, False

    def _apply_social_proof_quote(
        self,
        slides: List[Dict[str, Any]],
        social_proof_result: Optional[Dict[str, Any]],
        story_flow_result: Optional[Dict[str, Any]],
    ) -> "tuple[List[Dict[str, Any]], bool]":
        """
        Social Proof Selection (Phase M7 - 실제 사용 연결): 실제 선정된 반응
        텍스트가 있으면(social_proof_result.selected, raw_text_preserved=True
        원본 그대로) 인용 카드 형태("문장" - @계정)로 StoryFlowPlanner가
        "social_proof" narrative_role을 부여한 슬라이드의 body에 덧붙인다.
        새 draw 로직을 추가하지 않고 기존 텍스트 렌더링 파이프라인만 확장한다.
        댓글 캡처를 조작해서 만들지 않는다 - 원본 텍스트를 그대로 인용하고
        출처(@계정)를 함께 표시해 "인용 카드"임을 명확히 한다.
        """
        try:
            social_proof_result = social_proof_result or {}
            selected = social_proof_result.get("selected") or []

            if not selected:
                return slides, False

            proof_page = self._find_narrative_page(story_flow_result, "social_proof")

            if proof_page is None:
                return slides, False

            top_quote = selected[0]
            quote_text = str(top_quote.get("text", "")).strip()
            # 계정 최소화 계약(Phase M7 보정): 원문 계정명이 아니라 마스킹된
            # 계정명을 렌더링에 사용한다. 라벨("커뮤니티 반응")을 함께 붙여
            # 실제 플랫폼 캡처가 아니라 텍스트 인용 카드임을 명확히 한다.
            masked_handle = str(top_quote.get("masked_account_handle", "") or "").strip()
            label = str(top_quote.get("label", "커뮤니티 반응"))

            if not quote_text:
                return slides, False

            quote_line = (
                f'[{label}] "{quote_text}" - @{masked_handle}'
                if masked_handle
                else f'[{label}] "{quote_text}"'
            )

            updated_slides: List[Dict[str, Any]] = []
            applied = False

            for slide in slides:
                if isinstance(slide, dict) and slide.get("page") == proof_page and not applied:
                    new_slide = dict(slide)
                    body = str(new_slide.get("body", "")).strip()
                    new_slide["body"] = f"{body} {quote_line}".strip() if body else quote_line
                    updated_slides.append(new_slide)
                    applied = True
                else:
                    updated_slides.append(slide)

            return updated_slides, applied
        except Exception as error:
            print(f"Card News Social Proof Apply Failed: {error}")
            return slides, False

    def _find_narrative_page(
        self,
        story_flow_result: Optional[Dict[str, Any]],
        narrative_role: str,
    ) -> Optional[int]:
        try:
            applied_roles = (story_flow_result or {}).get("applied_roles") or []

            for item in applied_roles:
                if isinstance(item, dict) and item.get("narrative_role") == narrative_role:
                    page = item.get("page")
                    return int(page) if page is not None else None

            return None
        except Exception:
            return None

    def _resolve_visual_rhythm_application(
        self,
        visual_rhythm_result: Dict[str, Any],
        rendering_image_paths: List[Optional[str]],
        evidence_applied: bool,
        social_proof_applied: bool,
        story_flow_result: Optional[Dict[str, Any]],
    ) -> Dict[int, Dict[str, Any]]:
        """
        Human Visual Rhythm(Phase M8 #1/#6): VisualRhythmSelector가 고른
        selected_style이 "이번 카드뉴스 실제 데이터"로 정말 적용 가능한지
        재확인한다. 실제 데이터가 없는데 스타일만 흉내내지 않는다:

        - quote_card: 실제 Social Proof 인용이 그 페이지에 적용됐을 때만.
        - comparison: 현재 slide 스키마에는 실제 A/B 비교 구조(라벨) 데이터가
          없으므로 항상 fallback한다 - 억지로 비교 레이아웃을 만들지 않는다.
        - image_focus: 그 페이지에 실제 이미지 경로가 있을 때만(없으면 이미지를
          부각할 대상 자체가 없다).

        위 조건에 걸리면 VisualRhythmSelector.DEFAULT_STYLE로 안전하게
        대체하고 fallback_used/fallback_reason에 그 이유를 정직하게 남긴다.
        """
        try:
            social_proof_page = self._find_narrative_page(story_flow_result, "social_proof")
            resolved: Dict[int, Dict[str, Any]] = {}

            for item in (visual_rhythm_result or {}).get("assignments") or []:
                if not isinstance(item, dict):
                    continue

                page = item.get("page")
                selected_style = str(item.get("visual_style") or VisualRhythmSelector.DEFAULT_STYLE)
                applied_style = selected_style
                fallback_used = False
                fallback_reason = ""

                index = (int(page) - 1) if isinstance(page, int) else None
                has_real_image = bool(
                    index is not None
                    and 0 <= index < len(rendering_image_paths)
                    and rendering_image_paths[index]
                )

                if selected_style == "quote_card" and not (social_proof_applied and page == social_proof_page):
                    applied_style = VisualRhythmSelector.DEFAULT_STYLE
                    fallback_used = True
                    fallback_reason = "실제 Social Proof 인용이 적용되지 않아 quote_card 대신 기본 스타일을 사용함."
                elif selected_style == "comparison":
                    applied_style = VisualRhythmSelector.DEFAULT_STYLE
                    fallback_used = True
                    fallback_reason = "실제 비교(A/B) 구조 데이터가 없어 일반 본문 렌더링으로 대체함."
                elif selected_style == "image_focus" and not has_real_image:
                    applied_style = VisualRhythmSelector.DEFAULT_STYLE
                    fallback_used = True
                    fallback_reason = "실제 이미지가 없어 image_focus 대신 기본 스타일을 사용함."

                resolved[page] = {
                    "page": page,
                    "selected_style": selected_style,
                    "applied_style": applied_style,
                    "applied": not fallback_used,
                    "fallback_used": fallback_used,
                    "fallback_reason": fallback_reason,
                }

            return resolved
        except Exception as error:
            print(f"Card News Visual Rhythm Resolve Failed: {error}")
            return {}

    def _build_attribution_by_page(
        self,
        evidence_result: Optional[Dict[str, Any]],
        story_flow_result: Optional[Dict[str, Any]],
        evidence_applied: bool,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Source Attribution(Phase M8 #5/#7): render_allowed=True인 evidence가
        실제로 카드 배경에 적용된 경우에만(_apply_evidence_asset이 이미
        top_asset["applied"]=True로 확정해 둔 경우) 그 페이지에 짧은 출처
        라벨을 표시할 수 있게 한다. render_allowed=False/applied=False면
        출처만 덩그러니 표시하지 않는다 - 빈 dict를 반환해 아무 것도 그리지
        않는다.
        """
        if not evidence_applied:
            return {}

        try:
            top_asset = (evidence_result or {}).get("top_evidence_asset") or {}

            if not top_asset.get("render_allowed") or not top_asset.get("applied"):
                return {}

            page = self._find_narrative_page(story_flow_result, "evidence")

            if page is None:
                return {}

            source_name = str(top_asset.get("source_name", "") or "").strip()

            if not source_name:
                return {}

            asset_type = str(top_asset.get("asset_type", ""))
            source_type = self.ASSET_TYPE_LABELS.get(asset_type, "참고 자료")

            return {page: {"source_name": source_name[:20], "source_type": source_type}}
        except Exception as error:
            print(f"Card News Attribution Resolve Failed: {error}")
            return {}

    def _build_design_quality_result(self, optimized: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "text_optimized": bool(optimized.get("text_optimized", False)),
            "headline_trimmed_count": int(optimized.get("headline_trimmed_count", 0) or 0),
            "body_trimmed_count": int(optimized.get("body_trimmed_count", 0) or 0),
            "duplicate_removed_count": int(optimized.get("duplicate_removed_count", 0) or 0),
            "cta_optimized": bool(optimized.get("cta_optimized", False)),
            "cover_optimized": bool(optimized.get("cover_optimized", False)),
            "readability_warnings": list(optimized.get("readability_warnings", []) or []),
            "fallback_used": bool(optimized.get("fallback_used", False)),
            "ratio_adjusted_count": int(optimized.get("ratio_adjusted_count", 0) or 0),
            "readability_score": float(optimized.get("readability_score", 0.0) or 0.0),
            "slide_readability": list(optimized.get("slide_readability", []) or []),
        }

    def _build_typography_result(
        self,
        rendering_slides: List[Dict[str, Any]],
        story_flow_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        CardNews Intelligence (Phase M8: Production Quality) - Typography 계층.

        이미 계산된 story_flow_result.applied_roles(narrative_role)와 렌더링 직전
        슬라이드 텍스트(headline/body)를 typography_rules 기준과 비교만 한다.
        새 렌더링 로직이나 슬라이드 구조 변경은 하지 않는다.
        """
        try:
            narrative_by_page = {
                item.get("page"): item.get("narrative_role")
                for item in (story_flow_result or {}).get("applied_roles") or []
                if isinstance(item, dict)
            }

            checks: List[Dict[str, Any]] = []

            for slide in rendering_slides:
                if not isinstance(slide, dict):
                    continue

                page = slide.get("page")
                canonical_role = str(slide.get("role", ""))
                narrative_role = str(narrative_by_page.get(page, "") or "")

                headline_role = resolve_typography_role(canonical_role, narrative_role, True)
                body_role = resolve_typography_role(canonical_role, narrative_role, False)

                headline_check = check_text_against_role(str(slide.get("headline", "")), headline_role)
                body_check = check_text_against_role(str(slide.get("body", "")), body_role)

                checks.append({
                    "page": page,
                    "headline_check": headline_check,
                    "body_check": body_check,
                    "ok": bool(headline_check["ok"] and body_check["ok"]),
                })

            typography_hierarchy_ok = bool(checks) and all(item["ok"] for item in checks)

            return {
                "checks": checks,
                "typography_hierarchy_ok": typography_hierarchy_ok,
            }
        except Exception as error:
            return {
                "checks": [],
                "typography_hierarchy_ok": False,
                "reason": f"typography 검증 실패: {error}",
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
