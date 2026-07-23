import unittest

from modules.card_news.learning_design_compiler import (
    compile_learning_driven_blueprint,
)
from modules.card_news.learning_driven_production_bridge import (
    build_learning_driven_production_package,
)


class LearningDesignCompilerTests(unittest.TestCase):
    def _topic(self):
        return {
            "candidate_id": "topic:cluster:0192",
            "account_id": "account_a_news_incident",
            "primary_category": "economy_market",
            "title": "1인 가구도 '예금 탈출'…주식·ETF로 돈 옮겼다[1인가구 보고서]③",
            "link": "https://www.news1.kr/finance/general-finance/6230638",
            "key_points": [
                "예·적금 20대 10.6%p↓ 30대 9.9%p↓…머니무브 30·40세대 견인",
                "국내주식·ETF 가입 의향 2년새 18.7%p↑…'빚투'도 증가세",
            ],
        }

    def _plan(self):
        guidance = {
            role: {"pattern_id": f"pattern.owner.{role}"}
            for role in (
                "hook_strategy",
                "story_structure",
                "visual_direction",
                "cta_strategy",
            )
        }
        guidance["visual_direction"].update(
            {
                "recommended_action": "금융 이동의 긴장감과 경각심을 우선한다.",
                "emotion": "urgent_caution",
                "palette_intent": "high-contrast financial warning",
                "palette": {
                    "background": "#f7efe7",
                    "ink": "#211714",
                    "accent": "#d6402f",
                },
                "visual_relevance_labels": {
                    "target": {
                        "ko": ["예금", "주식", "ETF", "금융 이동"],
                        "en": ["deposit", "stock", "ETF", "money movement"],
                    },
                    "distractor": {
                        "ko": ["반려동물", "음식"],
                        "en": ["pet", "food"],
                    },
                },
            }
        )
        return {
            "status": "planned_with_fallback",
            "candidate_id": "topic:cluster:0192",
            "slides": [
                {
                    "semantic_role": "cover",
                    "learning_guidance": [guidance["visual_direction"]],
                },
                {
                    "semantic_role": "evidence",
                    "learning_guidance": [guidance["visual_direction"]],
                },
                {
                    "semantic_role": "conclusion",
                    "learning_guidance": [guidance["visual_direction"]],
                },
            ],
            "learning_guidance": guidance,
            "learning_guidance_consumed": True,
        }

    def test_compiles_facts_into_visible_visual_specs_and_caption(self):
        blueprint = compile_learning_driven_blueprint(
            self._topic(),
            self._plan(),
        )

        self.assertEqual("ready", blueprint["status"])
        self.assertEqual(3, blueprint["slide_count"])
        self.assertEqual(
            "delta_comparison",
            blueprint["slides"][1]["visual_spec"]["visual_type"],
        )
        self.assertEqual(
            [
                {"label": "20대", "value": "10.6%p", "direction": "↓"},
                {"label": "30대", "value": "9.9%p", "direction": "↓"},
            ],
            blueprint["slides"][1]["visual_spec"]["metrics"],
        )
        self.assertEqual(
            "cta_prompt",
            blueprint["slides"][2]["visual_spec"]["visual_type"],
        )
        self.assertIn("자산 비중", blueprint["feed_caption"])
        self.assertIn("NEWS1", blueprint["design_system"]["source_label"])
        self.assertEqual(4, len(blueprint["learning_trace"]["pattern_ids"]))
        self.assertEqual(
            "learned_guidance_over_account_default",
            blueprint["design_system"]["theme_priority"],
        )
        self.assertEqual(
            "#d6402f",
            blueprint["design_system"]["palette"]["accent"],
        )
        self.assertEqual(
            "urgent_caution",
            blueprint["design_system"]["learned_visual_guidance"]["emotion"],
        )
        self.assertEqual(
            "consumed",
            blueprint["learning_trace"]["design_guidance"]["status"],
        )
        self.assertEqual(
            "supplied",
            blueprint["slides"][1]["visual_spec"][
                "visual_relevance_labels_status"
            ],
        )
        self.assertEqual(
            ["deposit", "stock", "ETF", "money movement"],
            blueprint["slides"][1]["visual_spec"]["visual_relevance_labels"][
                "target"
            ]["en"],
        )

    def test_learning_claim_without_design_consumption_is_not_ready(self):
        plan = self._plan()
        plan["learning_guidance"]["visual_direction"] = {
            "pattern_id": "pattern.owner.visual_direction"
        }
        for slide in plan["slides"]:
            slide["learning_guidance"] = []

        blueprint = compile_learning_driven_blueprint(self._topic(), plan)

        self.assertEqual("design_guidance_not_consumed", blueprint["status"])
        self.assertEqual(
            "learning_guidance_claimed_without_design_consumption",
            blueprint["reason_code"],
        )
        self.assertEqual(
            "not_consumed",
            blueprint["learning_trace"]["design_guidance"]["status"],
        )

    def test_missing_visual_relevance_labels_are_explicit(self):
        plan = self._plan()
        plan["learning_guidance"]["visual_direction"].pop(
            "visual_relevance_labels"
        )
        for slide in plan["slides"]:
            slide["learning_guidance"][0].pop(
                "visual_relevance_labels",
                None,
            )

        blueprint = compile_learning_driven_blueprint(self._topic(), plan)

        self.assertTrue(
            all(
                slide["visual_spec"]["visual_relevance_labels_status"]
                == "missing"
                for slide in blueprint["slides"]
            )
        )
        self.assertNotIn(
            "visual_relevance_labels",
            blueprint["slides"][0]["visual_spec"],
        )

    def test_package_stays_pending_until_explicit_approval(self):
        blueprint = compile_learning_driven_blueprint(
            self._topic(),
            self._plan(),
        )

        pending = build_learning_driven_production_package(blueprint)
        ready = build_learning_driven_production_package(
            blueprint,
            {
                "status": "approved",
                "candidate_id": blueprint["candidate_id"],
                "scope": "production_package",
                "approved_by": "owner",
                "receipt_id": "owner-approved-learning-package",
            },
        )

        self.assertEqual("production_package_pending_approval", pending["status"])
        self.assertEqual("production_package_ready", ready["status"])
        self.assertEqual(
            blueprint["slides"][1]["visual_spec"],
            ready["slides"][1]["visual_spec"],
        )
        self.assertFalse(ready["gates"]["publish"]["authorized"])

    def test_blueprint_and_package_preserve_source_editorial_media_candidate(self):
        topic = self._topic()
        topic["assets"] = [
            {
                "asset_id": "news-image-1",
                "type": "news_image",
                "url": "https://cdn.example.com/news-image.jpg",
                "source_url": topic["link"],
                "usable_in_production": True,
                "reference_only": False,
                "rights_status": "source_editorial_usable",
                "topic_relevant": True,
                "attribution_required": True,
                "publish_authorized": False,
            },
            {
                "asset_id": "ap-image",
                "type": "news_image",
                "url": "https://cdn.example.com/ap-image.jpg",
                "source_url": topic["link"],
                "usable_in_production": False,
                "reference_only": True,
                "rights_status": "reference_only",
                "topic_relevant": True,
                "attribution_required": True,
                "publish_authorized": False,
            },
        ]
        blueprint = compile_learning_driven_blueprint(topic, self._plan())
        ready = build_learning_driven_production_package(
            blueprint,
            {
                "status": "approved",
                "candidate_id": blueprint["candidate_id"],
                "scope": "production_package",
                "approved_by": "owner",
                "receipt_id": "owner-approved-source-editorial-package",
            },
        )

        self.assertEqual(
            ["news-image-1"],
            [asset["asset_id"] for asset in blueprint["source_media_candidates"]],
        )
        candidate = blueprint["source_media_candidates"][0]
        self.assertEqual(candidate, blueprint["slides"][0]["visual_spec"]["source_media_candidate"])
        self.assertEqual(candidate, ready["evidence"]["assets"][0])
        self.assertEqual(candidate, ready["media_plan"][0]["source_media_candidate"])
        self.assertFalse(candidate["publish_authorized"])
        self.assertNotIn("ap-image", str(blueprint))


if __name__ == "__main__":
    unittest.main()
