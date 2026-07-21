import json
import os
import shutil
import uuid
import unittest

from modules.source_intake.naver_news_fallback_diagnostic import (
    DIAGNOSTIC_VERSION,
    DEFAULT_SOURCE_ID,
    STATUS_FALLBACK_ONLY,
    STATUS_NOT_IMPLEMENTED,
    STATUS_OK,
    STATUS_FAILED,
    build_naver_news_fallback_diagnostic,
)


class TestNaverNewsFallbackDiagnostic(unittest.TestCase):
    def setUp(self):
        self.today = "2099-01-02"
        self.root = os.path.join("source_intake_naver_diag_tmp", uuid.uuid4().hex)
        os.makedirs(os.path.join(self.root, self.today), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_json(self, filename, payload):
        path = os.path.join(self.root, self.today, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

    def test_build_diagnostic_with_parser_fallback_payload(self):
        self._write_json(
            "daily_shallow_collection.json",
            {
                "source_results": [
                    {
                        "source_id": DEFAULT_SOURCE_ID,
                        "attempted": True,
                        "success": True,
                        "skipped": False,
                        "count": 2,
                        "lane_id": "news_society_economy",
                    }
                ],
                "items": [
                    {
                        "source_id": DEFAULT_SOURCE_ID,
                        "collection_method": "settings_keyword_fallback",
                        "trend_reason": "Naver News settings fallback: parse_failed",
                        "is_fallback": True,
                    },
                    {
                        "source_id": DEFAULT_SOURCE_ID,
                        "collection_method": "settings_keyword_fallback",
                        "trend_reason": "Naver News settings fallback: parse_failed",
                        "is_fallback": True,
                    },
                ],
            },
        )
        self._write_json(
            "collection_gap_report.json",
            {
                "status_summary": {
                    STATUS_FALLBACK_ONLY: [
                        {"source_id": DEFAULT_SOURCE_ID, "item_count": 2},
                    ]
                }
            },
        )
        self._write_json(
            "daily_collection_plan.json",
            {
                "lanes": [
                    {"lane_id": "news_society_economy"},
                    {"lane_id": "lifestyle_knowledge"},
                ]
            },
        )

        diagnostic = build_naver_news_fallback_diagnostic(today=self.today, root=self.root)

        self.assertEqual(diagnostic["schema_version"], DIAGNOSTIC_VERSION)
        self.assertEqual(diagnostic["source_id"], DEFAULT_SOURCE_ID)
        self.assertEqual(diagnostic["status"], STATUS_FALLBACK_ONLY)
        self.assertEqual(diagnostic["coverage"]["item_count"], 2)
        self.assertEqual(diagnostic["coverage"]["fallback_item_count"], 2)
        self.assertEqual(diagnostic["coverage"]["fallback_methods"], ["settings_keyword_fallback"])
        self.assertEqual(diagnostic["diagnostic"]["parser_failure_count"], 4)
        self.assertIn("parser_failed", diagnostic["diagnostic"]["primary_reason"])
        self.assertIn("parse_failed", diagnostic["diagnostic"]["explanation"])
        self.assertIn("news_society_economy", diagnostic["plan_lanes"])
        self.assertTrue(diagnostic["artifacts_present"]["collection_gap_report.json"])
        self.assertNotIn("commerce_detail", json.dumps(diagnostic))

    def test_build_diagnostic_not_implemented_when_not_attempted(self):
        self._write_json(
            "daily_shallow_collection.json",
            {
                "source_results": [
                    {
                        "source_id": DEFAULT_SOURCE_ID,
                        "attempted": False,
                        "success": False,
                        "skipped": False,
                        "count": 0,
                        "lane_id": "news_society_economy",
                    }
                ],
                "items": [],
            },
        )

        diagnostic = build_naver_news_fallback_diagnostic(today=self.today, root=self.root)

        self.assertEqual(diagnostic["status"], STATUS_NOT_IMPLEMENTED)
        self.assertFalse(diagnostic["raw_collection_status"]["attempted"])
        self.assertEqual(diagnostic["coverage"]["item_count"], 0)
        self.assertEqual(diagnostic["coverage"]["fallback_item_count"], 0)
        self.assertEqual(diagnostic["diagnostic"]["primary_reason"], "collector_not_invoked")
        self.assertNotIn("parse_failed", diagnostic["diagnostic"]["primary_reason"])
        self.assertIn("not attempted", diagnostic["diagnostic"]["explanation"].lower())

    def test_smoke_current_storage_artifact_if_available(self):
        today = "2026-07-14"
        base = os.path.join("storage", "source_intake", today)
        path = os.path.join(base, "daily_shallow_collection.json")
        if not os.path.exists(path):
            self.skipTest("storage/source_intake/2026-07-14/daily_shallow_collection.json is not available")

        diagnostic = build_naver_news_fallback_diagnostic(today=today, root=os.path.join("storage", "source_intake"))

        self.assertEqual(diagnostic["source_id"], DEFAULT_SOURCE_ID)
        self.assertIn(diagnostic["status"], [STATUS_FALLBACK_ONLY, STATUS_OK, STATUS_FAILED, STATUS_NOT_IMPLEMENTED])
        self.assertGreaterEqual(diagnostic["coverage"]["item_count"], 1)
        self.assertIn(diagnostic["diagnostic"]["primary_reason"], {
            "parser_failed_and_fallback_used",
            "fallback_collected_without_parser_marker",
            "fallback_unknown",
            "direct_collection",
            "collection_failed",
            "collector_not_invoked",
            "status_unknown",
        })


if __name__ == "__main__":
    unittest.main()
