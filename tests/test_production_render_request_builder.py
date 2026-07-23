import copy
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.card_news.production_render_request_builder import (
    _heading_and_remainder,
    build_production_render_request,
)
from modules.tool_adapters.cardnews_renderer_runtime import CANVAS_PROFILES, MAX_SLIDES


class ProductionRenderRequestBuilderTests(unittest.TestCase):
    @staticmethod
    def _authorization(candidate_id):
        return {
            "authorized": True,
            "authorization_id": "render-news-visual",
            "mode": "representative",
            "input_sha256": "a" * 64,
            "output_root": r"F:\AI-Content-OS-Data\cardnews\rendered",
            "local_media_receipt_hashes": {candidate_id: ["b" * 64]},
        }

    def test_builds_source_bound_variable_request_with_one_embedded_cover(self):
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "owned.png"
            Image.new("RGB", (1200, 1500), "#aab7aa").save(asset)
            candidate_id = "C-1"
            package = {
                "status": "production_package_ready",
                "candidate": {
                    "candidate_id": candidate_id,
                    "account": "C",
                    "title": "장마철 앞머리",
                },
                "slides": [
                    {"page": page, "headline": "장마철 앞머리", "body": f"근거 문장 {page}"}
                    for page in range(1, 9)
                ],
            }
            authorization = {
                "authorized": True,
                "authorization_id": "render-test",
                "mode": "representative",
                "input_sha256": "a" * 64,
                "output_root": r"F:\AI-Content-OS-Data\cardnews\rendered",
                "local_media_receipt_hashes": {candidate_id: ["b" * 64]},
            }

            result = build_production_render_request(
                package, authorization, asset, package_path=Path(temp) / "package.json"
            )
            request = result["render_request"]

            self.assertEqual(result["status"], "ready")
            self.assertEqual(len(request["slides"]), 8)
            self.assertIn("attribution_receipt", request)
            self.assertEqual(
                result["attribution_receipt"], request["attribution_receipt"]
            )
            self.assertEqual(request["canvas_profile"], CANVAS_PROFILES["instagram_portrait_4_5"])
            self.assertTrue(
                request["slides"][0]["tree"]["props"]["children"][0]["props"]["src"].startswith(
                    "data:image/jpeg;base64,"
                )
            )
            self.assertEqual(request["slides"][1]["assets"], [])
            self.assertTrue(request["package_path"].endswith("package.json"))
            self.assertNotIn("https://", str(request["slides"]))

    def test_open_license_cover_renders_attribution_in_footer_and_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "commons.png"
            Image.new("RGB", (1200, 800), "#9aa9b3").save(asset)
            candidate_id = "A-commons-cover"
            source_candidate = {
                "asset_id": "commons-rain",
                "local_path": str(asset),
                "source_url": "https://commons.wikimedia.org/wiki/File:rain.jpg",
                "rights_status": "open_license",
                "topic_relevant": True,
                "attribution_required": True,
                "publish_authorized": False,
                "license_name": "CC BY-SA 4.0",
                "attribution_text": "Example Photographer",
            }
            package = {
                "status": "production_package_ready",
                "candidate": {
                    "candidate_id": candidate_id,
                    "account": "A",
                    "title": "서울 장마 풍경",
                },
                "slides": [
                    {
                        "page": 1,
                        "headline": "서울 장마 풍경",
                        "body": "공개 라이선스 사진으로 확인한 장마철 서울입니다.",
                        "visual_spec": {
                            "visual_type": "cover_editorial",
                            "source_media_candidate": source_candidate,
                        },
                    }
                ],
            }

            result = build_production_render_request(
                package,
                self._authorization(candidate_id),
                asset,
            )

            self.assertEqual("ready", result["status"])
            receipt = result["attribution_receipt"][0]
            self.assertEqual("Example Photographer", receipt["attribution_text"])
            self.assertEqual("CC BY-SA 4.0", receipt["license_name"])
            self.assertTrue(receipt["rendered_in_footer"])
            self.assertIn(
                "Example Photographer · CC BY-SA 4.0",
                str(result["render_request"]["slides"][0]["tree"]),
            )

    def test_reference_v2_geometry_replaces_legacy_tree_and_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "owned.png"
            Image.new("RGB", (1080, 1350), "#d8d2c4").save(asset)
            candidate_id = "A-v2"
            adapted_slide = {
                "status": "adapted",
                "geometry_hash": "geometry-v2",
                "regions": [
                    {
                        "region_id": "photo",
                        "role": "primary_media",
                        "box_norm": [0.0, 0.0, 1.0, 0.62],
                        "z_index": 1,
                    },
                    {
                        "region_id": "title",
                        "role": "headline",
                        "box_norm": [0.08, 0.68, 0.84, 0.18],
                        "z_index": 2,
                    },
                ],
                "media_bindings": [
                    {"region_id": "photo", "asset": {}}
                ],
                "content_bindings": [
                    {"region_id": "title", "content": "승인 레이아웃 제목"}
                ],
                "reference_consumption_receipt": {
                    "geometry_hash": "geometry-v2",
                    "geometry_modified": False,
                    "owner_approval_receipt_id": "owner-receipt-v2",
                },
            }
            package = {
                "status": "production_package_ready",
                "candidate": {
                    "candidate_id": candidate_id,
                    "account": "A",
                    "title": "승인 레이아웃 제목",
                },
                "slides": [
                    {
                        "page": 1,
                        "headline": "승인 레이아웃 제목",
                        "body": "확인된 본문",
                    }
                ],
                "reference_v2_required": True,
                "reference_v2": {
                    "status": "ready",
                    "slides": [
                        {
                            "page": 1,
                            "status": "ready",
                            "adapted_slide": adapted_slide,
                        }
                    ],
                },
            }

            result = build_production_render_request(
                package,
                self._authorization(candidate_id),
                asset,
            )

            self.assertEqual("ready", result["status"])
            slide = result["render_request"]["slides"][0]
            self.assertEqual(
                "62.000000%",
                slide["tree"]["props"]["children"][0]["props"]["style"]["height"],
            )
            self.assertEqual(
                "owner-receipt-v2",
                slide["reference_v2_consumption_receipt"][
                    "owner_approval_receipt_id"
                ],
            )
            self.assertFalse(
                slide["reference_v2_consumption_receipt"]["geometry_modified"]
            )

    def test_renderer_and_builder_share_twenty_slide_limit(self):
        self.assertEqual(MAX_SLIDES, 20)

    def test_decimal_points_do_not_split_financial_headings(self):
        heading, remainder = _heading_and_remainder(
            "20대 10.6%p↓, 30대 9.9%p↓. 머니무브가 이어졌다.",
            "fallback",
        )

        self.assertEqual("20대 10.6%p↓, 30대 9.9%p↓", heading)
        self.assertEqual("머니무브가 이어졌다.", remainder)

    def test_news_request_uses_news_visual_grammar_not_beauty_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "owned.png"
            Image.new("RGB", (1200, 1500), "#dfe8cf").save(asset)
            candidate_id = "A-1"
            package = {
                "status": "production_package_ready",
                "candidate": {
                    "candidate_id": candidate_id,
                    "account": "A",
                    "title": "1인 가구 머니무브",
                },
                "slides": [
                    {
                        "page": 1,
                        "headline": "1인 가구 머니무브",
                        "body": "예금에서 ETF로 자금이 이동했습니다.",
                    },
                    {
                        "page": 2,
                        "headline": "숫자로 본 변화",
                        "body": "투자 의향도 함께 증가했습니다.",
                    },
                ],
            }
            authorization = {
                "authorized": True,
                "authorization_id": "render-news",
                "mode": "representative",
                "input_sha256": "a" * 64,
                "output_root": r"F:\AI-Content-OS-Data\cardnews\rendered",
                "local_media_receipt_hashes": {candidate_id: ["b" * 64]},
            }

            result = build_production_render_request(package, authorization, asset)
            request_text = str(result["render_request"]["slides"])

            self.assertIn("MONEY / DATA BRIEF", request_text)
            self.assertIn("MARKET SHIFT", request_text)
            self.assertNotIn("RAIN-PROOF HAIR", request_text)
            self.assertNotIn("ALLURE KOREA", request_text)

            colon_package = copy.deepcopy(package)
            colon_candidate = "topic:cluster:0192"
            colon_package["candidate"]["candidate_id"] = colon_candidate
            colon_authorization = copy.deepcopy(authorization)
            colon_authorization["local_media_receipt_hashes"] = {
                colon_candidate: ["b" * 64]
            }
            colon_result = build_production_render_request(
                colon_package,
                colon_authorization,
                asset,
            )
            self.assertTrue(
                colon_result["render_request"]["output_root"].endswith(
                    "topic-cluster-0192"
                )
            )

    def test_news_delta_tree_consumes_supplied_design_and_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "owned.png"
            Image.new("RGB", (1200, 1500), "#dfe8cf").save(asset)
            candidate_id = "A-delta"
            package = {
                "status": "production_package_ready",
                "candidate": {
                    "candidate_id": candidate_id,
                    "account": "A",
                    "title": "세대별 자금 이동",
                },
                "design_system": {
                    "account_id": "A",
                    "palette": {
                        "background": "#f4f1e8",
                        "ink": "#12231a",
                        "accent": "#d44a2f",
                        "muted": "#687269",
                        "panel": "#fffaf0",
                    },
                    "cover_kicker": "NEWS DESK",
                    "detail_kicker": "DATA CHANGE",
                    "footer_label": "ECONOMY FILE",
                    "source_label": "SOURCE DATA",
                },
                "slides": [
                    {
                        "page": 1,
                        "headline": "세대별 자금 이동",
                        "body": "세대별 변화를 비교했습니다.",
                        "visual_spec": {"visual_type": "cover_editorial"},
                    },
                    {
                        "page": 2,
                        "headline": "변화 폭",
                        "body": "세대별 수치입니다.",
                        "visual_spec": {
                            "visual_type": "delta_comparison",
                            "metrics": [
                                {"label": "20대", "value": "10.6%p", "direction": "하락"},
                                {"label": "30대", "value": "9.9%p", "direction": "상승"},
                            ],
                        },
                    },
                ],
            }

            result = build_production_render_request(
                package, self._authorization(candidate_id), asset
            )
            request_text = str(result["render_request"]["slides"])

            self.assertEqual(result["status"], "ready")
            for supplied in (
                "NEWS DESK",
                "DATA CHANGE",
                "ECONOMY FILE",
                "SOURCE DATA",
                "20대",
                "10.6%p",
                "하락",
                "30대",
                "9.9%p",
                "상승",
                "#d44a2f",
                "#fffaf0",
            ):
                self.assertIn(supplied, request_text)
            self.assertNotIn("STYLE / BEAUTY FILE", request_text)
            self.assertNotIn("STYLE DETAIL", request_text)
            self.assertNotIn("ALLURE KOREA", request_text)

    def test_news_flow_tree_contains_only_supplied_flow_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "owned.png"
            Image.new("RGB", (1200, 1500), "#dfe8cf").save(asset)
            candidate_id = "A-flow"
            package = {
                "status": "production_package_ready",
                "candidate": {
                    "candidate_id": candidate_id,
                    "account": "A",
                    "title": "자금 이동 경로",
                },
                "design_system": {
                    "account_id": "A",
                    "palette": {
                        "background": "#eef2ed",
                        "ink": "#17251c",
                        "accent": "#3f7c58",
                        "muted": "#667168",
                        "panel": "#ffffff",
                    },
                    "cover_kicker": "NEWS FLOW",
                    "detail_kicker": "MONEY ROUTE",
                    "footer_label": "FLOW FILE",
                    "source_label": "SOURCE REPORT",
                },
                "slides": [
                    {
                        "page": 1,
                        "headline": "자금 이동 경로",
                        "body": "이동 경로를 정리했습니다.",
                        "visual_spec": {"visual_type": "cover_editorial"},
                    },
                    {
                        "page": 2,
                        "headline": "어디로 이동했나",
                        "body": "흐름이 달라졌습니다.",
                        "visual_spec": {
                            "visual_type": "flow_summary",
                            "from_label": "정기예금",
                            "to_label": "ETF",
                            "delta_label": "이동 확대",
                        },
                    },
                ],
            }

            result = build_production_render_request(
                package, self._authorization(candidate_id), asset
            )
            detail_text = str(result["render_request"]["slides"][1]["tree"])

            self.assertEqual(result["status"], "ready")
            self.assertIn("정기예금", detail_text)
            self.assertIn("ETF", detail_text)
            self.assertIn("이동 확대", detail_text)
            self.assertIn("12px", detail_text)
            self.assertNotIn("STYLE DETAIL", detail_text)
            self.assertNotIn("STYLE / BEAUTY FILE", detail_text)

    def test_preserves_learned_profile_fields_on_every_render_slide(self):
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "owned.png"
            Image.new("RGB", (1200, 1500), "#dfe8cf").save(asset)
            candidate_id = "B-learned"
            learned_profile = {
                "first_screen": {"hook": "reaction-led split screen"},
                "layout_family": "editorial_split",
                "composition": {"image_ratio": 0.62, "copy_anchor": "left"},
                "palette": {
                    "background": "#fff5df",
                    "accent": "#e34b32",
                },
                "typography": {"headline": "bold_condensed", "body": "short_korean"},
                "image_grammar": ["reaction", "context_capture", "comment"],
                "text_density": "low",
                "emotional_tone": "urgent_warm",
                "account_identity": "issue_story_dopamine",
                "unused_note": "must remain visible in ignored receipt",
            }
            package = {
                "status": "production_package_ready",
                "candidate": {
                    "candidate_id": candidate_id,
                    "account": "B",
                    "title": "학습 디자인 전달",
                },
                "design_system": {
                    "theme_priority": "learned_guidance_over_account_default",
                    "palette": {
                        "background": "#fff5df",
                        "ink": "#28201f",
                        "accent": "#e34b32",
                        "muted": "#725f59",
                        "panel": "#fffaf0",
                    },
                    "learned_profile": learned_profile,
                },
                "learning_trace": {
                    "design_guidance": {"available": True, "consumed": True}
                },
                "slides": [
                    {
                        "page": 1,
                        "headline": "학습 디자인 전달",
                        "body": "첫 화면 규칙을 전달합니다.",
                    },
                    {
                        "page": 2,
                        "headline": "두 번째 화면",
                        "body": "구성과 이미지 문법도 전달합니다.",
                    },
                ],
            }

            result = build_production_render_request(
                package, self._authorization(candidate_id), asset
            )

            self.assertEqual(result["status"], "ready")
            receipt = result["learning_consumption_receipt"]
            self.assertEqual(
                receipt["consumed_fields"],
                [
                    "composition",
                    "emotional_tone",
                    "first_screen",
                    "layout_family",
                    "palette",
                    "text_density",
                    "typography",
                ],
            )
            self.assertIn(
                "design_system.learned_profile.unused_note",
                receipt["ignored_fields"],
            )
            self.assertIn(
                "design_system.learned_profile.image_grammar",
                receipt["ignored_fields"],
            )
            self.assertIn(
                "design_system.learned_profile.account_identity",
                receipt["ignored_fields"],
            )
            for slide in result["render_request"]["slides"]:
                self.assertEqual(
                    set(slide["learned_design"]),
                    {
                        "composition",
                        "emotional_tone",
                        "first_screen",
                        "layout_family",
                        "palette",
                        "text_density",
                        "typography",
                    },
                )
                self.assertNotIn("unused_note", slide["learned_design"])
            request_text = str(result["render_request"]["slides"])
            self.assertIn("#df4b32", request_text)
            self.assertIn("66px", request_text)
            self.assertIn("68px", request_text)
            self.assertIn("textAlign", request_text)

    def test_blocks_when_claimed_learned_profile_consumes_no_core_field(self):
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "owned.png"
            Image.new("RGB", (1200, 1500), "#dfe8cf").save(asset)
            candidate_id = "A-unconsumed"
            package = {
                "status": "production_package_ready",
                "candidate": {
                    "candidate_id": candidate_id,
                    "account": "A",
                    "title": "소비되지 않은 학습",
                },
                "design_system": {
                    "theme_priority": "learned_guidance_over_account_default",
                    "learned_profile": {"unmapped_owner_rule": "preserve this"},
                },
                "learning_trace": {
                    "design_guidance": {"available": True, "consumed": True}
                },
                "slides": [
                    {
                        "page": 1,
                        "headline": "소비되지 않은 학습",
                        "body": "핵심 필드가 없습니다.",
                    }
                ],
            }

            result = build_production_render_request(
                package, self._authorization(candidate_id), asset
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(
                result["reason_code"], "learned_design_profile_not_consumed"
            )
            self.assertEqual(
                result["learning_consumption_receipt"]["core_consumed_count"], 0
            )
