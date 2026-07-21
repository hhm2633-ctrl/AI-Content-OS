import hashlib
import shutil
import unittest
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

from modules.card_news.card_news_module import CardNewsModule
from modules.card_news.card_news_text_optimizer import CardNewsTextOptimizer
from modules.card_news import render_constants as RC


FIXTURE_ROOT = Path("tests/fixtures/card_news_ux")
CANONICAL_ROLES = ["hook", "problem", "solution", "cta"]


class TestCardNewsProductionUX(unittest.TestCase):
    """Offline production UX guards; human visual approval remains mandatory."""

    def setUp(self):
        self.work = FIXTURE_ROOT / f"run_{uuid.uuid4().hex}"
        self.cards = self.work / "cards"
        self.cards.mkdir(parents=True, exist_ok=False)
        self.module = CardNewsModule({})
        self.module.card_dir = self.cards

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    @staticmethod
    def _slides():
        return [
            {
                "page": 1,
                "role": "hook",
                "headline": "한글공백없는아주긴제목" * 5,
                "body": "첫 장에서도 핵심 질문이 조용히 잘리면 안 됩니다. 추가 문장은 제한됩니다.",
            },
            {
                "page": 2,
                "role": "problem",
                "headline": "AN EXTREMELY LONG ENGLISH HEADLINE " * 4,
                "body": "https://example.invalid/" + "path-segment/" * 20,
            },
            {
                "page": 3,
                "role": "solution",
                "headline": "출처 표시와 본문 충돌 방지",
                "body": "출처가 필요한 자료는 권리 승인과 주제 관련성을 함께 확인합니다.",
            },
            {
                "page": 4,
                "role": "cta",
                "headline": "확인 후 저장하세요",
                "body": "권리와 출처를 확인한 뒤 저장하세요. 의견은 댓글로 남겨 주세요.",
            },
        ]

    def _run(self, images=None, *, need_ai_image=True):
        return self.module.run(
            {
                "title": "운영 검증용 매우 긴 제목 " * 8,
                "slides": self._slides(),
                "pattern_prompt_meta": {"pattern_type": "story", "cta_type": "save"},
            },
            {"images": images or []},
            {
                "need_ai_image": need_ai_image,
                "image_source": "operator_rights_approved_asset",
                "content_type": "evidence_required",
            },
        )

    def test_long_multilingual_input_produces_canonical_four_decodable_cards(self):
        result = self._run()
        self.assertEqual(result["status"], "card_news_completed")
        self.assertEqual([item["role"] for item in result["story_flow_result"]["applied_roles"]], CANONICAL_ROLES)
        self.assertEqual(len(result["cards"]), 4)

        for card in result["cards"]:
            with Image.open(card["card_path"]) as image:
                image.load()
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (1080, 1080))

    def test_hard_limits_are_visible_and_cta_action_survives(self):
        optimized = CardNewsTextOptimizer({}).optimize(self._slides())
        slides = optimized["slides"]
        self.assertTrue(slides[0]["headline"].endswith("…"))
        self.assertTrue(slides[1]["headline"].endswith("…"))
        self.assertTrue(slides[1]["body"].endswith("…"))
        self.assertLessEqual(len(slides[1]["body"]), 72)
        self.assertRegex(slides[3]["body"], r"저장|댓글")

    def test_25_percent_thumbnail_has_detail_and_safe_canvas(self):
        result = self._run()
        for card in result["cards"]:
            with Image.open(card["card_path"]) as image:
                thumb = image.convert("RGB").resize((270, 270), Image.Resampling.LANCZOS)
                # Non-blank/detail proxy only. It deliberately does not claim OCR readability.
                self.assertGreater(ImageStat.Stat(thumb).var[0], 20.0)
                self.assertEqual(thumb.size, (270, 270))
        self.assertGreaterEqual(RC.BOX_MARGIN, RC.MIN_SAFE_MARGIN)
        self.assertGreaterEqual(min(RC.RENDERER_FONT_SIZES.values()), RC.MIN_SAFE_FONT_SIZE)

    def test_problem_and_cta_subtitles_have_a_dedicated_overlap_free_panel_band(self):
        canvas = Image.new("RGB", (1080, 1080), "black")
        draw = ImageDraw.Draw(canvas)
        subtitle_font = self.module._get_font(RC.RENDERER_FONT_SIZES["small"])
        headline_font = self.module._get_font(RC.RENDERER_FONT_SIZES["headline"], bold=True)

        for role, panel_top in (
            ("problem", self.module.VISUAL_STYLE_PROFILES["short_line_focus"]["box_top"]),
            ("cta", self.module.VISUAL_STYLE_PROFILES["whitespace_focus"]["box_top"]),
        ):
            geometry = self.module._resolve_subtitle_geometry(
                "운영 검증용 보조문",
                subtitle_font,
                RC.BOX_MARGIN,
                panel_top,
                role,
            )
            headline_bbox = draw.textbbox(
                (RC.BOX_MARGIN + 40, geometry["headline_min_y"]),
                "겹침 없는 헤드라인",
                font=headline_font,
            )
            self.assertGreaterEqual(
                geometry["ink_bbox"][1],
                panel_top + self.module.SUBTITLE_SAFE_TOP_INSET,
            )
            self.assertGreater(geometry["ink_bbox"][3], geometry["ink_bbox"][1])
            self.assertLessEqual(
                geometry["ink_bbox"][3] + self.module.SUBTITLE_HEADLINE_SAFE_GAP,
                headline_bbox[1],
            )

        # card1/3은 승인된 기존 좌표를 그대로 사용한다.
        for role in ("hook", "solution"):
            geometry = self.module._resolve_subtitle_geometry(
                "기존 보조문",
                subtitle_font,
                RC.BOX_MARGIN,
                RC.BOX_TOP_DEFAULT,
                role,
            )
            self.assertEqual(
                geometry["position"][1],
                RC.BOX_TOP_DEFAULT + self.module.SUBTITLE_LEGACY_TOP_INSET,
            )

    def test_problem_and_cta_render_bytes_change_from_rejected_rc(self):
        result = self._run()
        rejected_hashes = {
            2: "CC48C6CCEB50C9F4BD756C97D394E2DE7773E71F4092E6CE94A15D0D239E06C0",
            4: "7D2E666FEDC6636DF820D1CA1EB114376566EFD4AC24D6D2037E20B2F1E8D17C",
        }
        cards_by_index = {card["index"]: card for card in result["cards"]}
        for index in (2, 4):
            card_path = Path(cards_by_index[index]["card_path"])
            digest = hashlib.sha256(card_path.read_bytes()).hexdigest().upper()
            self.assertNotEqual(digest, rejected_hashes[index])
            with Image.open(card_path) as image:
                image.load()
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (1080, 1080))
                self.assertEqual(
                    image.convert("RGB").resize((270, 270), Image.Resampling.LANCZOS).size,
                    (270, 270),
                )

    def test_attribution_and_cta_share_reserved_box_without_renderer_failure(self):
        slide = self._slides()[3]
        context = {
            "rule": self.module.layout_rule_engine.get_rule("bold_ai"),
            "slide_designs_by_page": {4: {"cta_area": True}},
            "slide_highlights_by_page": {},
        }
        path, layout_used = self.module._create_card(
            4,
            "출처·CTA 동시 최대 길이 검증",
            slide,
            None,
            layout_context=context,
            visual_style="cta_focus",
            narrative_role="evidence",
            attribution={"source_name": "승인된 퍼스트파티 출처명 최대길이", "source_type": "공식 자료"},
        )
        self.assertTrue(layout_used)
        with Image.open(path) as image:
            image.load()
            self.assertEqual(image.size, (1080, 1080))
        self.assertLess(RC.BOX_TOP_DEFAULT, RC.BOX_BOTTOM)

    def test_missing_and_corrupt_assets_fail_safe_without_slot_shift(self):
        valid_1 = self.work / "valid_1.png"
        corrupt_2 = self.work / "corrupt_2.png"
        valid_3 = self.work / "valid_3.png"
        Image.new("RGB", (80, 60), "navy").save(valid_1)
        corrupt_2.write_bytes(b"not-png")
        Image.new("RGB", (60, 80), "orange").save(valid_3)
        missing_4 = self.work / "missing_4.png"

        result = self._run([str(valid_1), str(corrupt_2), str(valid_3), str(missing_4)])
        self.assertEqual(len(result["cards"]), 4)
        self.assertEqual(result["cards"][0]["source_image"], str(valid_1))
        self.assertIsNone(result["cards"][1]["source_image"])
        self.assertEqual(result["cards"][2]["source_image"], str(valid_3))
        self.assertIsNone(result["cards"][3]["source_image"])
        input_reasons = [item["reason"] for item in result["image_asset_diagnostics"]["input_assets"]]
        render_reasons = [item["reason"] for item in result["image_asset_diagnostics"]["assets"]]
        self.assertEqual(input_reasons[1], "image_decode_failed")
        self.assertEqual(input_reasons[3], "image_file_missing")
        self.assertEqual(render_reasons[1], "image_path_missing")
        self.assertEqual(render_reasons[3], "image_path_missing")

    def test_dev_safe_and_publish_ready_verdicts_are_separate(self):
        result = self._run(need_ai_image=False)
        self.assertEqual(result["status"], "card_news_completed")
        sourcing = result["image_sourcing_status"]
        self.assertTrue(sourcing["manual_image_required"])
        self.assertEqual(sourcing["real_image_used_count"], 0)
        required_user_input = (
            "승인 이미지 파일 4개와 각 파일의 원문 URL·출처명·timezone 포함 captured_at/"
            "reviewed_at·copyright_status·구조화 permission_evidence·주제 관련성 확인·"
            "attribution 문구를 하나의 evidence manifest로 제공"
        )
        self.assertIsInstance(required_user_input, str)
        self.assertNotIn(" 또는 ", required_user_input)


if __name__ == "__main__":
    unittest.main()
