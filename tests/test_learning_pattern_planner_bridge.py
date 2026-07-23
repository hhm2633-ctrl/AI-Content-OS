import unittest

from modules.card_news.account_variable_slide_planner import (
    run_account_variable_slide_planner,
)
from modules.source_intake.account_instagram_pattern_binder import (
    run_account_instagram_pattern_binder,
)
from modules.source_intake.multi_account_card_news_discovery_pipeline import (
    _binding_for_topic,
    _build_deep_discovery_requests,
    _merge_deep_discovery,
)


class LearningPatternPlannerBridgeTest(unittest.TestCase):
    def _topic(self):
        return {
            "account_id": "account_a_news_incident",
            "candidate_id": "topic:cluster:1",
            "cluster_id": "cluster:1",
            "primary_category": "economy_market",
            "title": "예금에서 ETF로 이동한 1인 가구",
            "requested_slide_count": 4,
        }

    def _binder_result(self):
        topic = self._topic()
        return {
            "bindings_by_account": {
                topic["account_id"]: [
                    {
                        **topic,
                        "production_planning_eligible": False,
                        "roles": {
                            "hook_strategy": {
                                "bound": True,
                                "pattern_id": "pattern.owner.hook",
                                "pattern_name": "인용 반전 훅",
                                "pattern_status": "CANDIDATE",
                                "binding_tier": "reference_only",
                                "recommended_action": "인용과 반전을 사용해 첫 화면을 구성한다.",
                                "prohibited_actions": ["검증된 성과로 표현하지 않는다."],
                            },
                            "story_structure": {
                                "bound": True,
                                "pattern_id": "pattern.owner.story",
                                "pattern_name": "원자료 형식 보존",
                                "pattern_status": "CANDIDATE",
                                "binding_tier": "reference_only",
                                "recommended_action": "원자료의 사실 순서를 보존한다.",
                                "prohibited_actions": ["사실을 바꾸지 않는다."],
                            },
                        },
                    }
                ]
            }
        }

    def test_reference_tier_guidance_crosses_bridge_without_promotion(self):
        binding, reference = _binding_for_topic(self._topic(), self._binder_result())

        self.assertIsNotNone(binding)
        self.assertTrue(binding["reference_only"])
        self.assertFalse(binding["production_planning_eligible"])
        self.assertEqual("reference_guidance_supplied", reference["planner_bridge_status"])
        self.assertEqual(
            ["hook_strategy", "story_structure"],
            reference["planner_guidance_roles"],
        )

    def test_planner_applies_guidance_to_configured_structure(self):
        binding, _ = _binding_for_topic(self._topic(), self._binder_result())

        plan = run_account_variable_slide_planner(
            self._topic(),
            instagram_pattern_binding=binding,
        )

        self.assertEqual("planned_with_fallback", plan["status"])
        self.assertTrue(plan["learning_guidance_consumed"])
        self.assertEqual(
            "configured_structure_with_reference_guidance",
            plan["selected_pattern"]["source"],
        )
        self.assertEqual(
            "pattern.owner.hook",
            plan["slides"][0]["learning_guidance"][0]["pattern_id"],
        )
        self.assertIn(
            "pattern.owner.story",
            {
                item["pattern_id"]
                for slide in plan["slides"][1:]
                for item in slide["learning_guidance"]
            },
        )

    def test_visual_guidance_and_bilingual_labels_cross_planner_unchanged(self):
        binder_result = self._binder_result()
        roles = binder_result["bindings_by_account"][
            "account_a_news_incident"
        ][0]["roles"]
        labels = {
            "target": {
                "ko": ["예금", "ETF"],
                "en": ["deposit", "ETF"],
            },
            "distractor": {
                "ko": ["고양이"],
                "en": ["cat"],
            },
        }
        roles["visual_direction"] = {
            "bound": True,
            "pattern_id": "pattern.owner.visual",
            "pattern_name": "금융 경각심",
            "pattern_status": "CANDIDATE",
            "binding_tier": "reference_only",
            "recommended_action": "금융 이동의 경각심을 강한 대비로 표현한다.",
            "emotion": "urgent_caution",
            "palette_intent": "high-contrast financial warning",
            "visual_relevance_labels": labels,
        }
        binding, _ = _binding_for_topic(self._topic(), binder_result)

        plan = run_account_variable_slide_planner(
            self._topic(),
            instagram_pattern_binding=binding,
        )

        self.assertEqual(
            labels,
            plan["slides"][0]["visual_relevance_labels"],
        )
        self.assertEqual(
            "supplied",
            plan["slides"][0]["visual_relevance_labels_status"],
        )
        visual_guidance = next(
            item
            for item in plan["slides"][0]["learning_guidance"]
            if item["guidance_role"] == "visual_direction"
        )
        self.assertEqual("urgent_caution", visual_guidance["emotion"])
        self.assertEqual(labels, visual_guidance["visual_relevance_labels"])

    def test_planner_marks_missing_visual_relevance_labels(self):
        binding, _ = _binding_for_topic(self._topic(), self._binder_result())

        plan = run_account_variable_slide_planner(
            self._topic(),
            instagram_pattern_binding=binding,
        )

        self.assertTrue(
            all(
                slide["visual_relevance_labels_status"] == "missing"
                for slide in plan["slides"]
            )
        )

    def test_local_registry_supplies_all_four_roles_for_each_account(self):
        topics = {
            "account_a_news_incident": {
                "primary_category": "economy_market",
                "title": "경제 이슈",
            },
            "account_b_issue_story": {
                "primary_category": "community_buzz",
                "title": "커뮤니티 이슈",
            },
            "account_c_beauty_fashion": {
                "primary_category": "beauty_fashion",
                "title": "여름 패션",
            },
        }
        top_by_account = {}
        for index, (account_id, fields) in enumerate(topics.items(), start=1):
            top_by_account[account_id] = [
                {
                    "account_id": account_id,
                    "candidate_id": f"topic:cluster:{index}",
                    "cluster_id": f"cluster:{index}",
                    "rank": 1,
                    "selection_score": {"score": 0.8, "signal_coverage": 1.0},
                    **fields,
                }
            ]

        result = run_account_instagram_pattern_binder(
            {
                "status": "selected",
                "reason_code": "ok",
                "top_by_account": top_by_account,
                "backup_by_account": {
                    account_id: [] for account_id in top_by_account
                },
            }
        )

        self.assertEqual("bound", result["status"])
        for account_id, bindings in result["bindings_by_account"].items():
            with self.subTest(account_id=account_id):
                roles = bindings[0]["roles"]
                self.assertEqual(
                    {
                        "hook_strategy",
                        "story_structure",
                        "visual_direction",
                        "cta_strategy",
                    },
                    {
                        role
                        for role, binding in roles.items()
                        if binding["bound"]
                    },
                )

    def test_existing_deep_result_supplies_body_and_usable_media_to_planner(self):
        topic = self._topic()
        selection = {
            "status": "selected",
            "top_by_account": {
                topic["account_id"]: [topic],
                "account_b_issue_story": [],
                "account_c_beauty_fashion": [],
            },
        }
        requests = _build_deep_discovery_requests(selection)
        self.assertEqual(1, requests["request_count"])
        self.assertEqual("A", requests["requests"][0]["account"])

        deep_result = {
            "schema_version": "account_deep_discovery_result_v1",
            "status": "completed",
            "accounts": {
                "A": {
                    "results": [
                        {
                            "candidate_id": topic["candidate_id"],
                            "operations": [
                                {
                                    "artifact_role": "article_body",
                                    "assets": [
                                        {
                                            "body": "첫 번째 확인 문단입니다.\n두 번째 확인 문단입니다.",
                                            "url": "https://example.com/article",
                                        }
                                    ],
                                },
                                {
                                    "artifact_role": "news_image",
                                    "assets": [
                                        {
                                            "url": "https://example.com/usable.jpg",
                                            "usable_in_production": True,
                                            "reference_only": False,
                                        },
                                        {
                                            "url": "https://example.com/ap.jpg",
                                            "usable_in_production": False,
                                            "reference_only": True,
                                        },
                                    ],
                                },
                            ],
                        }
                    ]
                }
            },
        }

        enriched, status = _merge_deep_discovery(selection, deep_result)
        enriched_topic = enriched["top_by_account"][topic["account_id"]][0]

        self.assertEqual("merged", status["status"])
        self.assertEqual(2, len(enriched_topic["key_points"]))
        self.assertEqual(1, len(enriched_topic["assets"]))
        self.assertEqual(
            "https://example.com/usable.jpg",
            enriched_topic["assets"][0]["url"],
        )

    def test_three_slide_news_reduction_preserves_evidence_role(self):
        topic = {
            **self._topic(),
            "requested_slide_count": 3,
        }
        binding, _ = _binding_for_topic(topic, self._binder_result())

        plan = run_account_variable_slide_planner(
            topic,
            instagram_pattern_binding=binding,
        )

        self.assertEqual("planned_with_fallback", plan["status"])
        self.assertEqual(3, plan["slide_count"])
        self.assertEqual(
            ["cover", "evidence", "conclusion"],
            [slide["semantic_role"] for slide in plan["slides"]],
        )


if __name__ == "__main__":
    unittest.main()
