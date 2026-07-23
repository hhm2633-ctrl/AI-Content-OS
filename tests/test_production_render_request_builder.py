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
            self.assertEqual(request["canvas_profile"], CANVAS_PROFILES["instagram_portrait_4_5"])
            self.assertTrue(
                request["slides"][0]["tree"]["props"]["children"][0]["props"]["src"].startswith(
                    "data:image/jpeg;base64,"
                )
            )
            self.assertEqual(request["slides"][1]["assets"], [])
            self.assertTrue(request["package_path"].endswith("package.json"))
            self.assertNotIn("https://", str(request["slides"]))

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
