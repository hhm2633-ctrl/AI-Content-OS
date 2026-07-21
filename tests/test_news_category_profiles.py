"""Tests for the News Category Profiles V1 layer."""

import unittest

from modules.source_intake.news_category_profiles import (
    DEFAULT_NEWS_CATEGORY_PROFILES,
    NewsCategoryProfiles,
    SCAN_DEPTH_SHALLOW,
)

EXPECTED_PROFILE_IDS = [
    "domestic_news",
    "incident_accident",
    "entertainment_news",
    "world_news",
    "economy_news",
    "society_policy",
]

COMMUNITY_SOURCES = {
    "nate_pann", "fmkorea", "bobaedream", "dcinside", "theqoo",
    "ppomppu", "ruliweb", "dogdrip",
}

PORTAL_NEWS_SOURCES = {"naver_news", "daum_news", "nate_news_rank"}
WIRE_SOURCES = {"yonhap", "newsis", "news1"}


class TestNewsCategoryProfiles(unittest.TestCase):

    def setUp(self):
        self.profiles = NewsCategoryProfiles()

    # --- registry ---

    def test_six_profiles_exist(self):
        listed = self.profiles.list_profiles()
        self.assertEqual(sorted(listed), sorted(EXPECTED_PROFILE_IDS))
        self.assertEqual(len(listed), 6)

    def test_domestic_is_portal_news_centric(self):
        sources = self.profiles.sources_for("domestic_news")
        self.assertTrue(sources)
        self.assertTrue(set(sources).issubset(PORTAL_NEWS_SOURCES))
        self.assertFalse(set(sources) & COMMUNITY_SOURCES)

    def test_incident_includes_community_support(self):
        sources = set(self.profiles.sources_for("incident_accident"))
        self.assertIn("bobaedream", sources)
        self.assertIn("fmkorea", sources)
        # community is support, not the majority
        community = sources & COMMUNITY_SOURCES
        news = sources - COMMUNITY_SOURCES
        self.assertGreater(len(news), len(community))

    def test_entertainment_has_rumor_and_minor_risks(self):
        risks = self.profiles.risk_flags_for("entertainment_news")
        self.assertIn("rumor", risks)
        self.assertIn("minor", risks)

    def test_world_uses_only_approved_korean_news_sources(self):
        sources = set(self.profiles.sources_for("world_news"))
        self.assertTrue({"naver_news", "daum_news", "nate_news_rank"}.issubset(sources))
        self.assertTrue(WIRE_SOURCES.issubset(sources))
        self.assertFalse(
            sources & {"google_news_kr", "ap_world", "bbc_world", "reuters_world", "instiz"}
        )

    def test_economy_targets_commerce_signal_not_detail(self):
        channels = self.profiles.channels_for("economy_news")
        self.assertIn("commerce_signal", channels)
        self.assertNotIn("commerce_detail", channels)

    def test_society_policy_prefers_official_wire_sources(self):
        sources = set(self.profiles.sources_for("society_policy"))
        self.assertTrue(WIRE_SOURCES.issubset(sources))
        self.assertFalse(sources & COMMUNITY_SOURCES)

    # --- shallow-first invariant ---

    def test_all_profiles_are_shallow_first_no_auto_deep_dive(self):
        for profile_id in self.profiles.list_profiles():
            profile = self.profiles.get_profile(profile_id)
            self.assertEqual(profile.get("scan_depth"), SCAN_DEPTH_SHALLOW)
            self.assertFalse(profile.get("deep_dive_auto"))

    def test_defaults_are_shallow_first_too(self):
        for entry in DEFAULT_NEWS_CATEGORY_PROFILES:
            self.assertEqual(entry["scan_depth"], SCAN_DEPTH_SHALLOW)
            self.assertFalse(entry["deep_dive_auto"])

    # --- collection plan (selective mode) ---

    def test_plan_deduplicates_sources_across_profiles(self):
        plan = self.profiles.build_collection_plan(["domestic_news", "society_policy"])
        sources = plan["sources"]
        self.assertEqual(len(sources), len(set(sources)))
        self.assertEqual(sources.count("naver_news"), 1)
        self.assertEqual(plan["status"], "ok")

    def test_plan_excludes_blocked_sources(self):
        plan = self.profiles.build_collection_plan(EXPECTED_PROFILE_IDS)
        self.assertNotIn("reuters_world", plan["sources"])
        self.assertNotIn("instiz", plan["sources"])

    def test_plan_records_blocked_source_exclusion_non_fatally(self):
        registry = NewsCategoryProfiles()
        # force a blocked source into a profile copy to exercise exclusion
        registry.profiles["world_news"]["sources"] = (
            registry.profiles["world_news"]["sources"] + ["reuters_world"]
        )
        plan = registry.build_collection_plan(["world_news"])
        self.assertNotIn("reuters_world", plan["sources"])
        excluded_ids = [entry["source_id"] for entry in plan["excluded_sources"]]
        self.assertIn("reuters_world", excluded_ids)
        for entry in plan["excluded_sources"]:
            self.assertTrue(entry["skipped"])
            self.assertEqual(entry["workflow_impact"], "none")

    def test_unknown_profile_fails_closed(self):
        plan = self.profiles.build_collection_plan(["no_such_profile"])
        self.assertEqual(plan["sources"], [])
        self.assertEqual(plan["profiles"], [])
        self.assertEqual(plan["unknown_profiles"], ["no_such_profile"])
        self.assertEqual(plan["status"], "empty_plan")
        self.assertIsNone(self.profiles.get_profile("no_such_profile"))
        self.assertEqual(self.profiles.sources_for("no_such_profile"), [])
        self.assertEqual(self.profiles.channels_for("no_such_profile"), [])
        self.assertEqual(self.profiles.risk_flags_for("no_such_profile"), [])

    def test_unknown_profile_mixed_with_known_still_plans(self):
        plan = self.profiles.build_collection_plan(["domestic_news", "ghost"])
        self.assertEqual(plan["unknown_profiles"], ["ghost"])
        self.assertTrue(plan["sources"])
        self.assertEqual(plan["status"], "ok")

    def test_empty_input_yields_empty_plan_not_error(self):
        for empty_input in ([], None):
            plan = self.profiles.build_collection_plan(empty_input)
            self.assertEqual(plan["sources"], [])
            self.assertEqual(plan["status"], "empty_plan")
            self.assertEqual(plan["workflow_impact"], "none")

    def test_plan_is_selective_and_shallow(self):
        plan = self.profiles.build_collection_plan(["economy_news"])
        self.assertEqual(plan["mode"], "selective")
        self.assertEqual(plan["scan_depth"], SCAN_DEPTH_SHALLOW)
        self.assertFalse(plan["deep_dive_auto"])
        for profile_plan in plan["profiles"]:
            self.assertEqual(profile_plan["scan_depth"], SCAN_DEPTH_SHALLOW)
            self.assertFalse(profile_plan["deep_dive_auto"])
        # selective: only the requested profile's sources are planned
        self.assertNotIn("yonhap", plan["sources"])

    def test_config_defaults_match(self):
        """Config file and in-code defaults must describe the same profiles."""
        config_ids = sorted(NewsCategoryProfiles().list_profiles())
        default_ids = sorted(e["profile_id"] for e in DEFAULT_NEWS_CATEGORY_PROFILES)
        self.assertEqual(config_ids, default_ids)


if __name__ == "__main__":
    unittest.main()
