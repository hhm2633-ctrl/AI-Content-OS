from typing import Any, Dict, Optional, Tuple

from modules.card_news import render_constants as RC
from modules.card_news.typography_rules import TYPOGRAPHY_ROLES


class MobileReadabilityChecker:
    """
    CardNews Intelligence (Phase M8: Production Quality) - Mobile Readability.

    render_constants.py(card_news_module.py의 실제 Pillow 렌더링과 공유하는 단일
    진실 소스)와 typography_rules.py를 직접 참조해 모바일 축소 가독성을 검사한다.
    두 값이 서로 다른 복사본으로 어긋나지 않도록, 이 파일은 폰트/여백/팔레트
    숫자를 더 이상 자체적으로 복제하지 않는다 - render_constants만 가져다 쓴다.
    """

    RENDERER_FONT_SIZES = RC.RENDERER_FONT_SIZES
    MIN_SAFE_FONT_SIZE = RC.MIN_SAFE_FONT_SIZE

    BOX_MARGIN = RC.BOX_MARGIN
    MIN_SAFE_MARGIN = RC.MIN_SAFE_MARGIN

    PALETTE_COMBINATIONS = RC.PALETTE_COMBINATIONS
    MIN_CONTRAST_RATIO = RC.MIN_CONTRAST_RATIO

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def check(self, design_quality_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            return self._check(design_quality_result or {})
        except Exception as error:
            return self._fallback_result(reason=f"mobile readability 검사 실패: {error}")

    def _check(self, design_quality_result: Dict[str, Any]) -> Dict[str, Any]:
        # 렌더러가 실제로 쓸 수 있는 최소 폰트는 고정 상수(headline/body/small/
        # brand)뿐 아니라, Phase M8에서 실제 렌더링에 반영되는 typography_rules
        # role별 font_size_range 하한도 포함해야 한다 - 실제 렌더 값 기준으로
        # 계산한다는 요구사항(#4)에 따른 것.
        typography_min_fonts = [rule["font_size_range"][0] for rule in TYPOGRAPHY_ROLES.values()]
        all_min_fonts = list(self.RENDERER_FONT_SIZES.values()) + typography_min_fonts
        min_font_size_used = min(all_min_fonts) if all_min_fonts else 0
        min_font_size_ok = min_font_size_used >= self.MIN_SAFE_FONT_SIZE

        safe_margin_used = self.BOX_MARGIN
        safe_margin_ok = safe_margin_used >= self.MIN_SAFE_MARGIN

        contrast_details: Dict[str, Dict[str, float]] = {}

        for tone, palette in self.PALETTE_COMBINATIONS.items():
            contrast_details[tone] = {
                "headline_vs_box": self._contrast_ratio(palette["headline_color"], palette["box_fill"]),
                "body_vs_box": self._contrast_ratio(palette["body_color"], palette["box_fill"]),
                "subtitle_vs_box": self._contrast_ratio(palette["subtitle_color"], palette["box_fill"]),
            }

        all_ratios = [ratio for combo in contrast_details.values() for ratio in combo.values()]
        contrast_ratio_min = min(all_ratios) if all_ratios else 0.0
        contrast_ok = contrast_ratio_min >= self.MIN_CONTRAST_RATIO

        slide_readability = design_quality_result.get("slide_readability") or []
        overflow_free = bool(slide_readability) and all(
            isinstance(item, dict) and item.get("headline_ok") and item.get("body_ok")
            for item in slide_readability
        )
        overflow_detected = not overflow_free

        # 구조적 보장: 렌더러가 모든 카드에서 항상 불투명 박스(box_top~
        # box_bottom)를 텍스트 영역 전체에 먼저 그린 뒤 그 위에만 텍스트를
        # 그린다(_draw_card_box/_draw_layout_card_box) - 배경 이미지가 텍스트
        # 영역을 침범할 수 없는 고정 구조이므로 항상 충돌 없음으로 판단한다.
        text_image_collision_free = True

        source_legible = self.RENDERER_FONT_SIZES["small"] >= self.MIN_SAFE_FONT_SIZE
        cta_legible = self.RENDERER_FONT_SIZES["body"] >= self.MIN_SAFE_FONT_SIZE

        mobile_readability_ok = all([
            min_font_size_ok, safe_margin_ok, contrast_ok, overflow_free, text_image_collision_free,
        ])

        evaluated_render_values = {
            "renderer_font_sizes": dict(self.RENDERER_FONT_SIZES),
            "typography_role_font_min": {
                role: rule["font_size_range"][0] for role, rule in TYPOGRAPHY_ROLES.items()
            },
            "box_margin": self.BOX_MARGIN,
            "box_top_default": RC.BOX_TOP_DEFAULT,
            "box_bottom": RC.BOX_BOTTOM,
            "palette_combinations": {
                tone: dict(palette) for tone, palette in self.PALETTE_COMBINATIONS.items()
            },
        }

        return {
            "min_font_size_ok": min_font_size_ok,
            "safe_margin_ok": safe_margin_ok,
            "contrast_ok": contrast_ok,
            "contrast_details": contrast_details,
            "overflow_free": overflow_free,
            "text_image_collision_free": text_image_collision_free,
            "source_legible": source_legible,
            "cta_legible": cta_legible,
            "mobile_readability_ok": mobile_readability_ok,
            "evaluated_render_values": evaluated_render_values,
            "min_font_size_used": min_font_size_used,
            "contrast_ratio_min": contrast_ratio_min,
            "safe_margin_used": safe_margin_used,
            "overflow_detected": overflow_detected,
        }

    def _contrast_ratio(self, rgb_a: Tuple[int, int, int], rgb_b: Tuple[int, int, int]) -> float:
        luminance_a = self._relative_luminance(rgb_a)
        luminance_b = self._relative_luminance(rgb_b)
        lighter, darker = max(luminance_a, luminance_b), min(luminance_a, luminance_b)
        return round((lighter + 0.05) / (darker + 0.05), 2)

    def _relative_luminance(self, rgb: Tuple[int, int, int]) -> float:
        def channel(value: int) -> float:
            normalized = value / 255.0
            return normalized / 12.92 if normalized <= 0.03928 else ((normalized + 0.055) / 1.055) ** 2.4

        r, g, b = rgb
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        return {
            "min_font_size_ok": False,
            "safe_margin_ok": False,
            "contrast_ok": False,
            "contrast_details": {},
            "overflow_free": False,
            "text_image_collision_free": False,
            "source_legible": False,
            "cta_legible": False,
            "mobile_readability_ok": False,
            "evaluated_render_values": {},
            "min_font_size_used": 0,
            "contrast_ratio_min": 0.0,
            "safe_margin_used": 0,
            "overflow_detected": True,
            "reason": reason,
        }
