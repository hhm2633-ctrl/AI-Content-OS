import json
import os
import unittest

from modules.source_intake.source_capability_map import (
    ACCESS_BLOCKED,
    ACCESS_OK,
    DEFAULT_SOURCE_CAPABILITIES,
    SourceCapabilityMap,
)
from modules.trend_collector.bobaedream_collector import BobaedreamCollector
from modules.trend_collector.fmkorea_collector import FMKoreaCollector
from modules.trend_collector.nate_pann_collector import NatePannCollector


class TestSourceCapabilityMap(unittest.TestCase):
    def setUp(self):
        self.capability_map = SourceCapabilityMap()

    def test_ok_sources_from_access_check_are_collectable(self):
        for source_id in [
            "naver_news", "daum_news", "nate_news_rank",
            "yonhap", "newsis", "news1",
            "hankyung_economy", "mk_economy", "moneytoday", "edaily",
            "nate_pann", "fmkorea", "bobaedream", "dcinside",
            "theqoo", "ppomppu", "ruliweb", "dogdrip",
            "fashionn", "fashionbiz", "apparelnews", "cosin",
        ]:
            self.assertTrue(
                self.capability_map.is_collector_allowed(source_id),
                f"{source_id} should be collectable",
            )

    def test_owner_excluded_sources_are_not_active_or_collectable(self):
        for source_id in ["google_news_kr", "ap_world", "bbc_world", "reuters_world", "instiz"]:
            entry = self.capability_map.get(source_id)
            self.assertEqual(entry["access_status"], ACCESS_BLOCKED)
            self.assertFalse(self.capability_map.is_collector_allowed(source_id))
            self.assertEqual(entry["blocked_reason"], "unknown_source")

    def test_blocked_source_skip_is_not_a_workflow_failure(self):
        report = self.capability_map.skip_report("reuters_world")
        self.assertTrue(report["skipped"])
        self.assertFalse(report["attempted"])
        self.assertEqual(report["workflow_impact"], "none")

    def test_unknown_source_returns_safe_blocked_entry(self):
        entry = self.capability_map.get("does_not_exist")
        self.assertEqual(entry["access_status"], ACCESS_BLOCKED)
        self.assertFalse(self.capability_map.is_collector_allowed("does_not_exist"))

    def test_community_sources_declare_visible_metrics(self):
        for source_id in ["nate_pann", "bobaedream", "ppomppu"]:
            expected = self.capability_map.expected_metrics(source_id)
            self.assertIn("views", expected)
            self.assertIn("comments", expected)

        fmkorea_expected = self.capability_map.expected_metrics("fmkorea")
        self.assertNotIn("views", fmkorea_expected)
        self.assertIn("comments", fmkorea_expected)

    def test_ppomppu_declares_dislikes(self):
        self.assertIn("dislikes", self.capability_map.expected_metrics("ppomppu"))

    def test_account_c_specialists_are_rank_only_and_not_universal_market_claims(self):
        for source_id in ["fashionn", "musinsa_monthly_ranking", "oliveyoung_ranking"]:
            entry = self.capability_map.get(source_id)
            self.assertEqual(entry["expected_metrics"], ["rank_position"])
            self.assertFalse(entry["universal_trend_claimed"])
            self.assertEqual(entry["channel_candidates"], ["style_weather"])

        self.assertTrue(self.capability_map.get("oliveyoung_ranking")["promotion_sensitive"])

    def test_oliveyoung_live_403_is_excluded_without_deleting_collector_contract(self):
        entry = self.capability_map.get("oliveyoung_ranking")
        self.assertEqual(entry["access_status"], ACCESS_BLOCKED)
        self.assertFalse(self.capability_map.is_collector_allowed("oliveyoung_ranking"))
        self.assertEqual(entry["blocked_reason"], "http_403_live_check_2026_07_16")

    def test_beautynury_tls_block_is_recorded_without_daily_retry(self):
        entry = self.capability_map.get("beautynury")
        self.assertEqual(entry["access_status"], ACCESS_BLOCKED)
        self.assertFalse(self.capability_map.is_collector_allowed("beautynury"))
        self.assertEqual(
            entry["blocked_reason"],
            "python_tls_handshake_failed_2026_07_16",
        )

    def test_client_rendered_account_c_sources_are_dormant_not_retried_daily(self):
        expected_reasons = {
            "musinsa_monthly_ranking": "public_shell_without_product_metadata",
            "musinsa_boutique": "public_shell_without_product_metadata",
            "musinsa_beauty": "public_shell_without_product_metadata",
            "glowpick_ranking": "nextjs_stream_without_parseable_product_metadata",
        }
        for source_id, reason in expected_reasons.items():
            entry = self.capability_map.get(source_id)
            self.assertEqual(entry["access_status"], ACCESS_BLOCKED)
            self.assertFalse(self.capability_map.is_collector_allowed(source_id))
            self.assertEqual(entry["blocked_reason"], reason)

    def test_account_c_sources_separate_editorial_and_commercial_roles(self):
        fashionn = self.capability_map.get("fashionn")
        self.assertEqual(fashionn["account_c_vertical"], "fashion")
        self.assertEqual(fashionn["topic_selection_role"], "primary_editorial")
        self.assertTrue(fashionn["editorial_topic_eligible"])

        for source_id in ["musinsa_monthly_ranking", "oliveyoung_ranking"]:
            entry = self.capability_map.get(source_id)
            self.assertFalse(entry["editorial_topic_eligible"])
            self.assertTrue(entry["supporting_topic_signal"])
            self.assertIn(entry["commercial_influence"], {"medium", "high"})

        boutique = self.capability_map.get("musinsa_boutique")
        self.assertTrue(boutique["post_selection_only"])
        self.assertFalse(boutique["supporting_topic_signal"])
        self.assertEqual(boutique["account_c_source_role"], "luxury_reference")

        glowpick = self.capability_map.get("glowpick_ranking")
        self.assertEqual(glowpick["account_c_vertical"], "beauty")
        self.assertEqual(glowpick["account_c_source_role"], "consumer_review_evidence")
        self.assertTrue(glowpick["experience_review_sensitive"])

    def test_account_c_direct_replacements_are_primary_editorial_only(self):
        expected_verticals = {
            "fashionbiz": "fashion",
            "apparelnews": "fashion",
            "cosin": "beauty",
        }
        for source_id, vertical in expected_verticals.items():
            entry = self.capability_map.get(source_id)
            self.assertEqual(entry["account_c_vertical"], vertical)
            self.assertEqual(entry["topic_selection_role"], "primary_editorial")
            self.assertTrue(entry["editorial_topic_eligible"])
            self.assertEqual(entry["commercial_influence"], "low")
            self.assertFalse(entry["universal_trend_claimed"])

    def test_missing_config_falls_back_to_defaults(self):
        capability_map = SourceCapabilityMap(config_path="config/nonexistent_sources.json")
        self.assertTrue(capability_map.is_collector_allowed("nate_pann"))
        self.assertFalse(capability_map.is_collector_allowed("instiz"))

    def test_config_file_matches_default_source_ids(self):
        config_path = os.path.join("config", "source_intake_sources.json")
        self.assertTrue(os.path.exists(config_path))
        with open(config_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        config_ids = {entry["source_id"] for entry in data["sources"]}
        default_ids = {entry["source_id"] for entry in DEFAULT_SOURCE_CAPABILITIES}
        self.assertEqual(config_ids, default_ids)

    def test_no_ad_image_capability_declared_anywhere(self):
        for entry in DEFAULT_SOURCE_CAPABILITIES:
            for metric in entry.get("expected_metrics", []):
                self.assertNotIn("image", metric)
                self.assertNotIn("ad", metric)


class TestCollectorShallowExtension(unittest.TestCase):
    """Existing collector items keep their fields and gain optional
    visible_metrics / media_flags without any fabricated values."""

    EXISTING_FIELDS = [
        "keyword", "link", "summary", "publisher", "published_at",
        "source_id", "source_name", "source_type", "tier", "weight",
        "base_score", "trend_reason", "collection_method",
        "is_fallback", "collected_at",
    ]

    def build_items(self, collector, source):
        articles = [
            {"title": "커뮤니티 인기글 제목 하나", "link": "https://example.com/1", "summary": ""},
            {"title": "커뮤니티 인기글 제목 둘", "link": "https://example.com/2", "summary": "",
             "visible_metrics": {"views": 1200, "comments": 34},
             "media_flags": {"has_image": True, "image_count": 2}},
        ]
        return collector._build_items(articles=articles, source=source, collection_method="test")

    def assert_extended(self, items):
        self.assertEqual(len(items), 2)

        for item in items:
            for field in self.EXISTING_FIELDS:
                self.assertIn(field, item)
            self.assertIn("visible_metrics", item)
            self.assertIn("media_flags", item)

        # article without parsed metrics -> all null, never fabricated
        plain = items[0]["visible_metrics"]
        self.assertTrue(all(value is None for value in plain.values()))
        self.assertTrue(all(value is None for value in items[0]["media_flags"].values()))

        # article with parsed metrics -> passed through as ints
        rich = items[1]["visible_metrics"]
        self.assertEqual(rich["views"], 1200)
        self.assertEqual(rich["comments"], 34)
        self.assertIsNone(rich["likes"])
        self.assertEqual(items[1]["media_flags"]["has_image"], True)
        self.assertEqual(items[1]["media_flags"]["image_count"], 2)

    def test_nate_pann_items_extended(self):
        collector = NatePannCollector()
        items = self.build_items(collector, {"name": "네이트판", "type": "community"})
        self.assert_extended(items)

    def test_fmkorea_items_extended(self):
        collector = FMKoreaCollector()
        items = self.build_items(collector, {"name": "FM코리아", "type": "community"})
        self.assert_extended(items)

    def test_bobaedream_items_extended(self):
        collector = BobaedreamCollector()
        items = self.build_items(collector, {"name": "보배드림", "type": "community"})
        self.assert_extended(items)


if __name__ == "__main__":
    unittest.main()
