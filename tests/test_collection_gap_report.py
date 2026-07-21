import json
import os
import unittest

from modules.source_intake.collection_gap_report import (
    STATUS_FALLBACK_ONLY,
    STATUS_FAILED,
    STATUS_NOT_IMPLEMENTED,
    build_collection_gap_report,
)


class TestCollectionGapReport(unittest.TestCase):
    def test_fake_collection_report_detects_not_implemented_fallback_and_failed(self):
        sample = {
            "plan": {
                "lanes": [
                    {
                        "lane_id": "news_society_economy",
                        "shallow_profiles": ["news_a", "news_b", "news_c"],
                        "excluded_sources": [
                            {
                                "source_id": "blocked_news",
                                "skip_reason": "http_403 (blocked)",
                            }
                        ],
                    },
                    {
                        "lane_id": "entertainment_news",
                        "shallow_profiles": ["news_b", "community_d"],
                        "excluded_sources": [],
                    },
                ]
            },
            "source_results": [
                {
                    "source_id": "news_a",
                    "attempted": True,
                    "success": True,
                    "skipped": False,
                    "count": 2,
                },
                {
                    "source_id": "news_b",
                    "attempted": True,
                    "success": False,
                    "skipped": False,
                    "count": 0,
                    "error": "timeout",
                },
                {
                    "source_id": "news_c",
                    "lane_id": "news_society_economy",
                    "attempted": False,
                    "success": False,
                    "skipped": True,
                    "skip_reason": "collector_not_implemented",
                    "count": 0,
                },
                {
                    "source_id": "community_d",
                    "attempted": False,
                    "success": False,
                    "skipped": True,
                    "skip_reason": "collector_not_implemented",
                    "count": 0,
                },
            ],
            "items": [
                {
                    "source_id": "news_a",
                    "source_type": "news",
                    "collection_method": "settings_keyword_fallback",
                    "is_fallback": True,
                },
                {
                    "source_id": "news_a",
                    "source_type": "news",
                    "collection_method": "settings_keyword_fallback",
                    "is_fallback": True,
                },
            ],
        }

        report = build_collection_gap_report(sample)
        sources = {entry["source_id"]: entry for entry in report["status_summary"][STATUS_NOT_IMPLEMENTED]}

        self.assertEqual(report["source_count"], 5)
        self.assertEqual(report["status_counts"][STATUS_NOT_IMPLEMENTED], 2)
        self.assertEqual(report["status_counts"][STATUS_FALLBACK_ONLY], 1)
        self.assertEqual(report["status_counts"][STATUS_FAILED], 2)
        self.assertEqual(sources["news_c"]["status"], STATUS_NOT_IMPLEMENTED)
        self.assertEqual(next(entry["status"] for entry in report["status_summary"][STATUS_NOT_IMPLEMENTED] if entry["source_id"] == "community_d"), STATUS_NOT_IMPLEMENTED)
        self.assertIn("blocked_news", {entry["source_id"] for entry in report["status_summary"][STATUS_FAILED]})

        status_lookup = {entry["source_id"]: entry["status"] for group in report["source_status_by_status"].values() for entry in group}
        self.assertEqual(status_lookup["news_a"], STATUS_FALLBACK_ONLY)
        self.assertEqual(status_lookup["news_b"], STATUS_FAILED)
        self.assertEqual(next(entry["lane_impact"] for entry in report["status_summary"][STATUS_NOT_IMPLEMENTED] if entry["source_id"] == "news_c"), ["news_society_economy"])
        order = [entry["source_id"] for entry in report["recommended_implementation_order"]]
        self.assertEqual(order[0], "news_a")
        self.assertIn("blocked_news", order)

    def test_report_works_on_current_file_if_present(self):
        path = os.path.join("storage", "source_intake", "2026-07-14", "daily_shallow_collection.json")
        if not os.path.exists(path):
            self.skipTest("daily_shallow_collection.json not present")

        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        report = build_collection_gap_report(payload)
        self.assertGreater(report["source_count"], 0)
        for block in [STATUS_NOT_IMPLEMENTED, STATUS_FALLBACK_ONLY]:
            for entry in report["status_summary"][block]:
                self.assertTrue(entry["lane_impact"])


if __name__ == "__main__":
    unittest.main()
