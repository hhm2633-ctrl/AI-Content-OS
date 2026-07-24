import unittest

from modules.source_intake.multi_account_card_news_discovery_pipeline import (
    _build_slide_plans,
)


class _ProfileCompiler:
    def compile(self, topic_context):
        return {
            "schema_version": "production_profile_compiler_v1",
            "profile_id": "production-profile:test-news-warning",
            "status": "compiled",
            "context": dict(topic_context),
            "production_profile": {
                "first_screen": "왼쪽 이미지와 오른쪽 경고 제목의 분할 화면",
                "layout_family": "editorial_split",
                "palette": {
                    "background": "#fff1df",
                    "ink": "#241714",
                    "accent": "#d63d2f",
                    "panel": "#fff8ef",
                },
                "typography": {
                    "headline": "bold_condensed",
                    "body": "short_korean",
                },
                "image_grammar": ["source_editorial"],
                "text_density": "low",
                "emotional_tone": "warning",
                "account_identity": "news",
            },
            "production_profile_provenance": {
                "layout_family": ["learning-layout-001"],
                "palette": ["learning-color-001"],
            },
            "inference_used": False,
        }


class ProductionProfilePipelineBridgeTest(unittest.TestCase):
    def test_existing_learning_profile_reaches_blueprint_without_field_loss(self):
        topic = {
            "account_id": "account_a_news_incident",
            "candidate_id": "topic:learning:1",
            "cluster_id": "cluster:learning:1",
            "primary_category": "economy_market",
            "title": "금융 경고 신호",
            "requested_slide_count": 3,
            "key_points": [
                "예금 비중이 감소했다.",
                "투자 비중이 증가했다.",
            ],
            "link": "https://example.com/news",
        }
        result = _build_slide_plans(
            {
                "top_by_account": {
                    "account_a_news_incident": [topic],
                    "account_b_issue_story": [],
                    "account_c_beauty_fashion": [],
                }
            },
            None,
            _ProfileCompiler(),
        )

        plan = result["account_a_news_incident"][0]
        blueprint = plan["production_blueprint"]
        self.assertEqual(
            "production-profile:test-news-warning",
            plan["production_learning_profile"]["profile_id"],
        )
        self.assertEqual("ready", blueprint["status"])
        self.assertEqual(
            "editorial_split",
            blueprint["design_system"]["learned_profile"][
                "layout_family"
            ],
        )
        self.assertEqual(
            "#d63d2f",
            blueprint["design_system"]["learned_profile"]["palette"][
                "accent"
            ],
        )
        self.assertEqual(
            [
                "emotional_tone",
                "first_screen",
                "layout_family",
                "palette",
                "text_density",
                "typography",
            ],
            blueprint["learning_trace"]["production_profile"][
                "consumed_fields"
            ],
        )
        self.assertEqual(
            ["account_identity", "image_grammar"],
            blueprint["learning_trace"]["production_profile"][
                "ignored_fields"
            ],
        )
        self.assertFalse(
            blueprint["learning_trace"]["production_profile"][
                "render_contract_receipt"
            ]["render_execution_claimed"]
        )
        self.assertEqual(
            ["learning-layout-001"],
            blueprint["learning_trace"]["production_profile"]["provenance"][
                "layout_family"
            ],
        )


if __name__ == "__main__":
    unittest.main()
