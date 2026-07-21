import unittest

from modules.source_intake.daily_collection_plan import (
    DEFAULT_LANES,
    SCHEMA_VERSION,
    build_daily_collection_plan,
)
from modules.source_intake.source_intake_schema import (
    SOURCE_INTAKE_STORAGE_ROOT,
    source_data_root,
)


class TestDailySourceCollectionPlan(unittest.TestCase):
    def setUp(self):
        self.account_profiles = [
            "news_society_economy",
            "entertainment_news",
            "dopamine_community",
            "beauty_fashion",
            "lifestyle_knowledge",
        ]
        self.today = "2026-07-14"

    def test_schema_and_known_lanes(self):
        plan = build_daily_collection_plan(self.account_profiles, today=self.today)
        self.assertEqual(plan["schema_version"], SCHEMA_VERSION)
        self.assertEqual(len(plan["lanes"]), len(self.account_profiles))
        self.assertEqual([lane["lane_id"] for lane in plan["lanes"]], self.account_profiles)

        for lane in plan["lanes"]:
            self.assertEqual(lane["shallow_only"], True)
            self.assertEqual(lane["deep_dive_enabled"], False)
            self.assertIn(lane["lane_id"], DEFAULT_LANES)
            self.assertTrue(lane["storage_policy"]["shallow_only_index"]["small_index_path"])
            self.assertEqual(
                lane["storage_policy"]["shallow_only_index"]["small_index_root"],
                SOURCE_INTAKE_STORAGE_ROOT,
            )

    def test_unknown_lane_fails_closed(self):
        plan = build_daily_collection_plan(["ghost_lane"], today=self.today)
        self.assertEqual(plan["unknown_lanes"], ["ghost_lane"])
        self.assertEqual(plan["lanes"][0]["lane_id"], "ghost_lane")
        self.assertEqual(plan["lanes"][0]["shallow_profiles"], [])
        self.assertEqual(plan["lanes"][0]["plan_status"], "lane_unknown")
        self.assertEqual(plan["plan_status"], "empty_plan")

    def test_storage_policy_uses_c_and_external_f_root(self):
        plan = build_daily_collection_plan(["news_society_economy"], today=self.today)
        storage_policy = plan["lanes"][0]["storage_policy"]
        self.assertEqual(
            storage_policy["shallow_only_index"]["small_index_root"],
            SOURCE_INTAKE_STORAGE_ROOT,
        )
        self.assertEqual(
            storage_policy["shallow_only_index"]["small_index_path"].replace("\\", "/"),
            "storage/source_intake/2026-07-14/shallow_index",
        )
        self.assertEqual(
            storage_policy["deep_dive_raw_artifacts"]["raw_artifacts_root"],
            source_data_root(),
        )

    def test_owner_excluded_sources_are_absent_from_active_lanes(self):
        plan = build_daily_collection_plan(self.account_profiles, today=self.today)
        active_sources = {
            source_id
            for lane in plan["lanes"]
            for source_id in lane["shallow_profiles"]
        }
        self.assertFalse(
            active_sources
            & {"google_news_kr", "ap_world", "bbc_world", "reuters_world", "instiz"}
        )

    def test_account_c_plan_includes_specialist_sources_before_general_communities(self):
        plan = build_daily_collection_plan(["beauty_fashion"], today=self.today)
        sources = plan["lanes"][0]["shallow_profiles"]
        self.assertEqual(
            sources[:7],
            [
                "fashionn",
                "fashionbiz",
                "apparelnews",
                "allure_beauty",
                "vogue_beauty",
                "wkorea_beauty",
                "gq_grooming",
            ],
        )
        self.assertNotIn("cosin", sources)
        self.assertNotIn("beautynury", sources)
        self.assertNotIn("musinsa_monthly_ranking", sources)
        self.assertNotIn("glowpick_ranking", sources)
        self.assertNotIn("musinsa_beauty", sources)
        self.assertNotIn("musinsa_boutique", sources)
        excluded = {
            entry["source_id"]: entry for entry in plan["lanes"][0]["excluded_sources"]
        }
        self.assertEqual(
            excluded["oliveyoung_ranking"]["skip_reason"],
            "http_403_live_check_2026_07_16",
        )
        for source_id in [
            "musinsa_monthly_ranking",
            "musinsa_beauty",
            "musinsa_boutique",
        ]:
            self.assertEqual(
                excluded[source_id]["skip_reason"],
                "public_shell_without_product_metadata",
            )
        self.assertEqual(
            excluded["glowpick_ranking"]["skip_reason"],
            "nextjs_stream_without_parseable_product_metadata",
        )
        self.assertNotIn("beautynury", excluded)
        self.assertNotIn("theqoo", sources)
        self.assertNotIn("nate_pann", sources)
        self.assertNotIn("fmkorea", sources)

    def test_deep_dive_trigger_policy_has_numeric_gate_and_repeat_requirement(self):
        plan = build_daily_collection_plan(self.account_profiles, today=self.today)
        for lane in plan["lanes"]:
            policy = lane["deep_dive_trigger_policy"]
            self.assertIn("score_threshold", policy)
            self.assertGreater(policy["score_threshold"], 0)
            self.assertIn("repeat_source_min_hits", policy)
            self.assertIsInstance(policy["repeat_source_min_hits"], int)
            self.assertGreaterEqual(policy["repeat_source_min_hits"], 2)

    def test_commerce_signal_only_in_text(self):
        # no accidental commerce_detail wording in the planner output
        plan = build_daily_collection_plan(self.account_profiles, today=self.today)
        serialized = str(plan)
        self.assertNotIn("commerce_detail", serialized)
