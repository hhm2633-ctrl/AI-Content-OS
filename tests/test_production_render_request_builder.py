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
            self.assertEqual(request["canvas_profile"], CANVAS_PROFILES["instagram_portrait_3_4"])
            self.assertTrue(
                request["slides"][0]["tree"]["props"]["children"][0]["props"]["src"].startswith(
                    "data:image/jpeg;base64,"
                )
            )
            self.assertEqual(request["slides"][1]["assets"], [])
            self.assertTrue(request["package_path"].endswith("package.json"))
            self.assertNotIn("https://", str(request["slides"]))

    def test_open_license_cover_keeps_attribution_out_of_image_tree_and_in_receipt(self):
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
            self.assertFalse(receipt["rendered_in_footer"])
            self.assertEqual(
                "feed_caption_or_internal_source_record",
                receipt["delivery"],
            )
            self.assertNotIn(
                "Example Photographer · CC BY-SA 4.0",
                str(result["render_request"]["slides"][0]["tree"]),
            )

    def test_reference_v2_page_one_builds_full_canvas_cover_lower_third_and_preserves_receipt(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "owned.png"
            Image.new("RGB", (1080, 1440), "#d8d2c4").save(asset)
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
                    {"region_id": "title", "content": "오래된 플래너 제목"}
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
                            "geometry_hash": "geometry-v2",
                            "geometry_visual_gate_receipt": {
                                "schema_version": "reference_geometry_visual_gate.v1",
                                "adapter_schema_version": "reference_geometry_visual_gate_adapter_v1",
                                "independent_revalidation_schema_version": "reference_geometry_independent_revalidation_v1",
                                "status": "pass",
                                "visual_status": "visual_geometry_pass",
                                "receipt_id": "visual-gate-v2",
                                "source_receipt_path": "F:/qa/independent_visual_revalidation_receipt.json",
                                "source_receipt_sha256": "a" * 64,
                                "reference_id": "owner-ref-v2",
                                "blueprint_id": "bp-owner-v2",
                                "geometry_hash": "geometry-v2",
                                "gate_result_hash": "b" * 64,
                                "confidence_used_as_pass": False,
                                "auto_owner_approval": False,
                                "production_approval_granted": False,
                            },
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
            children = slide["tree"]["props"]["children"]
            cover_image = children[0]
            self.assertEqual("img", cover_image["type"])
            self.assertTrue(
                cover_image["props"]["src"].startswith("data:image/")
            )
            self.assertIn("승인 레이아웃 제목", str(slide["tree"]))
            self.assertNotIn("오래된 플래너 제목", str(slide["tree"]))
            self.assertEqual("100%", cover_image["props"]["style"]["width"])
            self.assertEqual("100%", cover_image["props"]["style"]["height"])

            lower_third = next(
                child
                for child in children
                if child.get("type") == "div"
                and child.get("props", {})
                .get("style", {})
                .get("backgroundColor")
                == "rgba(11,31,36,0.90)"
            )
            lower_third_style = lower_third["props"]["style"]
            self.assertEqual("4.444444%", lower_third_style["left"])
            self.assertEqual("64.444444%", lower_third_style["top"])
            self.assertEqual("91.111111%", lower_third_style["width"])
            self.assertEqual("28.888889%", lower_third_style["height"])
            self.assertEqual("18px", lower_third_style["borderRadius"])
            self.assertEqual(
                "owner-receipt-v2",
                slide["reference_v2_consumption_receipt"][
                    "owner_approval_receipt_id"
                ],
            )
            self.assertFalse(
                slide["reference_v2_consumption_receipt"]["geometry_modified"]
            )

    def test_reference_v2_without_visual_gate_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "owned.png"
            Image.new("RGB", (1080, 1440), "#d8d2c4").save(asset)
            candidate_id = "A-v2-no-visual"
            package = {
                "status": "production_package_ready",
                "candidate": {
                    "candidate_id": candidate_id,
                    "account": "A",
                    "title": "시각 검증 누락",
                },
                "slides": [
                    {
                        "page": 1,
                        "headline": "시각 검증 누락",
                        "body": "visual gate receipt가 없습니다.",
                    }
                ],
                "reference_v2_required": True,
                "reference_v2": {
                    "status": "ready",
                    "slides": [
                        {
                            "page": 1,
                            "status": "ready",
                            "geometry_hash": "geometry-missing",
                            "adapted_slide": {
                                "geometry_hash": "geometry-missing",
                            },
                        }
                    ],
                },
            }
            result = build_production_render_request(
                package,
                self._authorization(candidate_id),
                asset,
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(
                result["reason_code"],
                "reference_visual_gate_pass_receipt_missing",
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
            self.assertNotIn("SOURCE DATA", request_text)
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

    def test_blocks_when_selected_asset_is_replaced_before_render(self):
        with tempfile.TemporaryDirectory() as temp:
            owned = Path(temp) / "owned.png"
            Image.new("RGB", (1200, 1500), "#eeeeee").save(owned)
            candidate_id = "B-asset-mismatch"
            package = {
                "status": "production_package_ready",
                "candidate": {
                    "candidate_id": candidate_id,
                    "account": "B",
                    "title": "선택 이미지 대조",
                },
                "slides": [
                    {
                        "page": 1,
                        "headline": "선택 이미지 대조",
                        "body": "선택된 이미지와 렌더 이미지가 달라졌습니다.",
                        "asset_refs": ["selected-1"],
                    }
                ],
                "slide_asset_selection": {
                    "selection_receipts": [
                        {
                            "page": 1,
                            "asset_id": "selected-1",
                            "selection_receipt_id": "receipt-1",
                        }
                    ]
                },
            }

            result = build_production_render_request(
                package,
                self._authorization(candidate_id),
                owned,
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(
                result["reason_code"], "selected_asset_render_mismatch"
            )
            self.assertEqual(
                result["asset_mismatch"]["rendered_asset_id"],
                f"{candidate_id}-owned-editorial-1",
            )

    def test_blocks_when_upstream_profile_field_is_not_in_render_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            owned = Path(temp) / "owned.png"
            Image.new("RGB", (1200, 1500), "#eeeeee").save(owned)
            candidate_id = "A-profile-mismatch"
            package = {
                "status": "production_package_ready",
                "candidate": {
                    "candidate_id": candidate_id,
                    "account": "A",
                    "title": "프로필 소비 대조",
                },
                "design_system": {
                    "learned_profile": {
                        "palette": {
                            "background": "#f4f1e8",
                            "accent": "#d44a2f",
                        }
                    }
                },
                "learning_pipeline_consumption_receipt": {
                    "profile_consumed_fields": [
                        "palette",
                        "typography",
                    ],
                    "reference_consumed_ids": [],
                    "auto_approval_performed": False,
                },
                "slides": [
                    {
                        "page": 1,
                        "headline": "프로필 소비 대조",
                        "body": "상류 소비 기록과 실제 렌더 입력을 비교합니다.",
                    }
                ],
            }

            result = build_production_render_request(
                package,
                self._authorization(candidate_id),
                owned,
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(
                result["reason_code"],
                "production_profile_render_consumption_mismatch",
            )
            self.assertEqual(
                result["learning_consumption_mismatch"]["missing_fields"],
                ["typography"],
            )
