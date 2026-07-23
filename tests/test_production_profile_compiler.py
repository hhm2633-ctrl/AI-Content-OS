import json
import tempfile
import unittest
from pathlib import Path

from modules.design_learning.production_profile_compiler import (
    MAX_REFERENCE_CANDIDATES,
    PROFILE_FIELDS,
    ProductionProfileCompiler,
)


class ProductionProfileCompilerTest(unittest.TestCase):
    def _write(self, path: Path, payload: dict) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _compiler(self, root: Path) -> ProductionProfileCompiler:
        return ProductionProfileCompiler(
            feedback_root=root,
            taxonomy_path=root / "owner_learning_taxonomy_v1.json",
            index_path=root / "cardnews_owner_learning_index.json",
        )

    def test_compiles_existing_fields_and_preserves_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write(
                root / "owner_learning_taxonomy_v1.json",
                {
                    "records": [
                        {
                            "learning_id": "taxonomy-news-layout",
                            "accounts": ["news"],
                            "formats": ["card_news"],
                            "learning_layers": ["hook", "layout", "color", "typography"],
                            "owner_confirmed": True,
                            "title": "경고형 첫 화면",
                            "summary": "강한 첫 화면과 비대칭 레이아웃",
                            "palette": ["warning-red", "paper-white"],
                            "typography": "굵은 한글 제목과 짧은 본문",
                        },
                        {
                            "learning_id": "taxonomy-news-media",
                            "accounts": ["news"],
                            "formats": ["card_news", "reels"],
                            "learning_layers": ["image_media"],
                            "owner_confirmed": True,
                            "image_grammar": "실제 보도 이미지와 문서 캡처를 교차",
                            "body_density": "슬라이드당 한두 문장",
                            "issue_intensity": "high",
                        },
                    ],
                    "candidate_patterns": [],
                    "owner_rule_payloads": [],
                },
            )
            self._write(
                root / "cardnews_owner_learning_index.json",
                {
                    "records": [
                        {
                            "learning_id": "index-carousel",
                            "categories": ["news"],
                            "applies_to": ["card_news", "reels"],
                            "formats": ["card_news", "reels"],
                            "rule": "캐러셀과 릴스에서 실제 프레임을 재사용",
                            "active": True,
                        },
                        {
                            "learning_id": "inactive-rule",
                            "categories": ["news"],
                            "rule": "사용하면 안 되는 비활성 규칙",
                            "active": False,
                        },
                    ]
                },
            )
            self._write(
                root / "account_ai_presenter_identity_rule_v1.json",
                {
                    "rule_id": "analysis-ai-presenter",
                    "account": "news",
                    "ai_presenter": "뉴스 계정 전용 동일 AI 진행자",
                    "commerce": "상품 연결은 자연스러운 경우만",
                    "emotion": "긴장과 경각심",
                    "season": "장마철",
                },
            )

            result = self._compiler(root).compile(
                {
                    "account": "news",
                    "topic": "장마철 안전 이슈",
                    "formats": ["card_news", "reels"],
                }
            )

            self.assertEqual(set(result["fields"]), set(PROFILE_FIELDS))
            self.assertFalse(result["inference_used"])
            self.assertIn(
                "warning-red",
                result["fields"]["palette"]["values"],
            )
            self.assertIn(
                "뉴스 계정 전용 동일 AI 진행자",
                result["fields"]["ai_presenter"]["values"],
            )
            self.assertIn(
                "taxonomy-news-layout",
                result["fields"]["layout"]["provenance_source_ids"],
            )
            self.assertIn(
                "analysis-ai-presenter",
                result["fields"]["ai_presenter"]["provenance_source_ids"],
            )
            self.assertIn(
                "index-carousel",
                result["fields"]["carousel_reels"]["provenance_source_ids"],
            )
            self.assertNotIn("inactive-rule", result["provenance"]["source_ids"])
            self.assertEqual(
                "editorial_split",
                result["production_profile"]["layout_family"],
            )
            self.assertEqual(
                "warning",
                result["production_profile"]["emotional_tone"],
            )
            self.assertEqual(
                ["source_editorial"],
                result["production_profile"]["image_grammar"],
            )
            self.assertEqual(
                "low",
                result["production_profile"]["text_density"],
            )
            self.assertFalse(
                result["production_profile_normalization"][
                    "source_reanalysis"
                ]
            )
            self.assertEqual(
                "bounded_ranked_reference_candidates_with_legacy_first_value_profile",
                result["reference_candidate_receipt"]["selection_mode"],
            )
            self.assertTrue(result["reference_candidates"])
            candidate = result["reference_candidates"][0]
            self.assertTrue(candidate["approval"]["owner_approved"])
            self.assertIn("source_id", candidate["source"])
            self.assertIn("accounts", candidate["scope"])
            self.assertIn("roles", candidate["scope"])

    def test_missing_fields_remain_missing_without_inference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write(
                root / "owner_learning_taxonomy_v1.json",
                {
                    "records": [
                        {
                            "learning_id": "layout-only",
                            "accounts": ["fashion"],
                            "learning_layers": ["layout"],
                            "summary": "제품 전신과 디테일을 번갈아 배치",
                            "owner_confirmed": True,
                        }
                    ],
                    "candidate_patterns": [],
                    "owner_rule_payloads": [],
                },
            )
            self._write(
                root / "cardnews_owner_learning_index.json",
                {"records": []},
            )

            result = self._compiler(root).compile(
                {"account": "fashion", "topic": "신규 브랜드 소개"}
            )

            self.assertEqual(result["fields"]["layout"]["status"], "compiled")
            self.assertEqual(result["fields"]["season"]["status"], "missing")
            self.assertEqual(result["fields"]["emotion"]["status"], "missing")
            self.assertEqual(result["fields"]["palette"]["status"], "missing")
            self.assertIn("season", result["missing_fields"])
            self.assertFalse(result["inference_used"])

    def test_output_is_deterministic_for_identical_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write(
                root / "owner_learning_taxonomy_v1.json",
                {
                    "records": [
                        {
                            "learning_id": "b-rule",
                            "accounts": ["story"],
                            "learning_layers": ["image_media"],
                            "summary": "감정에 맞는 짤과 실제 댓글을 혼합",
                            "owner_confirmed": True,
                        },
                        {
                            "learning_id": "a-rule",
                            "accounts": ["story"],
                            "learning_layers": ["hook"],
                            "summary": "첫 화면에서 관계 갈등을 명확히 제시",
                            "owner_confirmed": True,
                        },
                    ],
                    "candidate_patterns": [],
                    "owner_rule_payloads": [],
                },
            )
            self._write(
                root / "cardnews_owner_learning_index.json",
                {"records": []},
            )
            compiler = self._compiler(root)
            context = {
                "account": "story",
                "topic": "연애 갈등",
                "formats": ["card_news"],
            }

            first = compiler.compile(context)
            second = compiler.compile(context)

            self.assertEqual(first, second)
            self.assertEqual(
                first["profile_id"],
                f"production-profile:{first['deterministic_fingerprint'][:20]}",
            )

    def test_compile_many_has_stable_context_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write(
                root / "owner_learning_taxonomy_v1.json",
                {"records": [], "candidate_patterns": [], "owner_rule_payloads": []},
            )
            self._write(
                root / "cardnews_owner_learning_index.json",
                {"records": []},
            )
            contexts = [
                {"account": "story", "topic": "두 번째"},
                {"account": "news", "topic": "첫 번째"},
            ]

            first = self._compiler(root).compile_many(contexts)
            second = self._compiler(root).compile_many(reversed(contexts))

            self.assertEqual(first, second)

    def test_reference_candidates_are_bounded_and_reference_only_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = [
                {
                    "learning_id": f"approved-{index:02d}",
                    "accounts": ["news"],
                    "formats": ["card_news"],
                    "learning_layers": ["layout"],
                    "owner_confirmed": True,
                    "layout": f"뉴스 레이아웃 {index:02d}",
                }
                for index in range(MAX_REFERENCE_CANDIDATES + 5)
            ]
            records.append(
                {
                    "learning_id": "reference-only",
                    "accounts": ["news"],
                    "formats": ["card_news"],
                    "learning_layers": ["layout"],
                    "owner_confirmed": True,
                    "reference_only": True,
                    "layout": "제작 선택 금지 레퍼런스",
                }
            )
            self._write(
                root / "owner_learning_taxonomy_v1.json",
                {
                    "records": records,
                    "candidate_patterns": [],
                    "owner_rule_payloads": [],
                },
            )
            self._write(
                root / "cardnews_owner_learning_index.json",
                {"records": []},
            )

            result = self._compiler(root).compile(
                {
                    "account": "news",
                    "topic": "오늘의 뉴스",
                    "formats": ["card_news"],
                }
            )

            candidates = result["reference_candidates"]
            counts = result["reference_candidate_receipt"]["counts"]
            self.assertEqual(MAX_REFERENCE_CANDIDATES, len(candidates))
            self.assertEqual(1, counts["reference_only_excluded"])
            self.assertEqual(5, counts["truncated"])
            self.assertNotIn(
                "reference-only",
                {item["source"]["source_id"] for item in candidates},
            )
            self.assertTrue(
                all(item["reference_only"] is False for item in candidates)
            )
            self.assertEqual(
                "first_normalizable_value_per_render_field",
                result["reference_candidate_receipt"][
                    "legacy_profile_selection_mode"
                ],
            )

    def test_reference_candidate_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write(
                root / "owner_learning_taxonomy_v1.json",
                {
                    "records": [
                        {
                            "learning_id": "approved-layout",
                            "accounts": ["fashion"],
                            "formats": ["card_news"],
                            "learning_layers": ["layout", "color"],
                            "owner_approved": True,
                            "layout": "비대칭 분할",
                            "palette": ["cream", "black"],
                        }
                    ],
                    "candidate_patterns": [],
                    "owner_rule_payloads": [],
                },
            )
            self._write(
                root / "cardnews_owner_learning_index.json",
                {"records": []},
            )
            compiler = self._compiler(root)
            context = {
                "account": "fashion",
                "topic": "브랜드 소개",
                "formats": ["card_news"],
            }

            first = compiler.compile(context)
            second = compiler.compile(context)

            self.assertEqual(
                first["reference_candidates"],
                second["reference_candidates"],
            )
            self.assertEqual(
                first["reference_candidate_receipt"],
                second["reference_candidate_receipt"],
            )


if __name__ == "__main__":
    unittest.main()
