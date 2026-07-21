import os
import unittest

from modules.source_intake.collection_gap_report import (
    STATUS_FALLBACK_ONLY,
    STATUS_FAILED,
    STATUS_NOT_IMPLEMENTED,
    STATUS_OK,
)
from modules.source_intake.lane_collection_summary import (
    READINESS_BLOCKED,
    READINESS_PARTIAL,
    READINESS_READY_SHALLOW,
    build_lane_collection_summary,
)


class TestLaneCollectionSummary(unittest.TestCase):
    def _extract_lane(self, summary, lane_id):
        lane_summary = summary["lane_summary"]
        self.assertIn(lane_id, lane_summary)
        return lane_summary[lane_id]

    def test_fake_gap_report_builds_counts_readiness_and_ordering(self):
        gap_report = {
            "status_summary": {
                STATUS_NOT_IMPLEMENTED: [
                    {
                        "source_id": "news_a",
                        "lane_impact": ["news_lane", "daily_lane"],
                        "status": STATUS_NOT_IMPLEMENTED,
                    },
                    {
                        "source_id": "news_b",
                        "lane_impact": ["daily_lane"],
                        "status": STATUS_NOT_IMPLEMENTED,
                    },
                ],
                STATUS_FALLBACK_ONLY: [
                    {
                        "source_id": "news_c",
                        "lane_impact": ["news_lane"],
                        "status": STATUS_FALLBACK_ONLY,
                    }
                ],
                STATUS_FAILED: [
                    {
                        "source_id": "news_d",
                        "lane_impact": ["daily_lane"],
                        "status": STATUS_FAILED,
                    },
                ],
                STATUS_OK: [
                    {
                        "source_id": "nate_pann",
                        "lane_impact": ["news_lane"],
                        "status": STATUS_OK,
                    }
                ],
            },
            "recommended_implementation_order": [
                {"source_id": "news_b", "status": STATUS_NOT_IMPLEMENTED, "lane_impact": ["daily_lane"]},
                {"source_id": "news_x", "status": STATUS_FAILED, "lane_impact": ["news_lane"]},
                {"source_id": "news_a", "status": STATUS_NOT_IMPLEMENTED, "lane_impact": ["news_lane", "daily_lane"]},
                {"source_id": "news_c", "status": STATUS_FALLBACK_ONLY, "lane_impact": ["news_lane"]},
            ],
            "all_lanes": ["news_lane", "daily_lane", "clean_lane"],
        }

        summary = build_lane_collection_summary(gap_report)
        news = self._extract_lane(summary, "news_lane")
        daily = self._extract_lane(summary, "daily_lane")
        clean = self._extract_lane(summary, "clean_lane")

        self.assertEqual(news["counts_by_status"], {
            STATUS_NOT_IMPLEMENTED: 1,
            STATUS_FALLBACK_ONLY: 1,
            STATUS_FAILED: 0,
            STATUS_OK: 1,
        })
        self.assertEqual(daily["counts_by_status"], {
            STATUS_NOT_IMPLEMENTED: 2,
            STATUS_FALLBACK_ONLY: 0,
            STATUS_FAILED: 1,
            STATUS_OK: 0,
        })
        self.assertEqual(clean["counts_by_status"], {
            STATUS_NOT_IMPLEMENTED: 0,
            STATUS_FALLBACK_ONLY: 0,
            STATUS_FAILED: 0,
            STATUS_OK: 0,
        })

        self.assertEqual(news["lane_readiness"], READINESS_PARTIAL)
        self.assertEqual(daily["lane_readiness"], READINESS_BLOCKED)
        self.assertEqual(clean["lane_readiness"], READINESS_BLOCKED)
        self.assertEqual(summary["weak_lanes"], ["news_lane", "daily_lane", "clean_lane"])

        self.assertEqual(
            news["top_missing_sources"],
            ["news_x", "news_a", "news_c"],
        )
        self.assertEqual(
            daily["top_missing_sources"],
            ["news_b", "news_a"],
        )

    def test_no_commerce_detail_is_not_emitted(self):
        gap_report = {
            "status_summary": {
                STATUS_NOT_IMPLEMENTED: [],
                STATUS_FALLBACK_ONLY: [],
                STATUS_FAILED: [],
                STATUS_OK: [
                    {"source_id": "nate_pann", "lane_impact": ["ok_lane"], "status": STATUS_OK}
                ],
            },
            "recommended_implementation_order": [],
            "all_lanes": ["ok_lane"],
        }

        summary = build_lane_collection_summary(gap_report)
        ok_lane = self._extract_lane(summary, "ok_lane")

        self.assertNotIn("commerce_detail", ok_lane)
        self.assertEqual(ok_lane["counts_by_status"][STATUS_OK], 1)
        self.assertEqual(ok_lane["lane_readiness"], READINESS_READY_SHALLOW)

    def test_smoke_with_current_collection_gap_report_if_present(self):
        path = os.path.join("storage", "source_intake", "2026-07-14", "collection_gap_report.json")
        if not os.path.exists(path):
            self.skipTest("collection_gap_report.json not present")
        summary = build_lane_collection_summary(path)

        self.assertGreater(summary["lane_count"], 0)
        self.assertIn("lane_summary", summary)
        for lane_id, lane_summary in summary["lane_summary"].items():
            self.assertIn("counts_by_status", lane_summary)
            self.assertIn("lane_readiness", lane_summary)
            self.assertIn(lane_summary["lane_readiness"], [READINESS_BLOCKED, READINESS_PARTIAL, READINESS_READY_SHALLOW])
            self.assertNotIn("commerce_detail", lane_summary)


if __name__ == "__main__":
    unittest.main()
