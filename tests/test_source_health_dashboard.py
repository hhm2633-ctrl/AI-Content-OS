import json
import os
import shutil
import uuid
import unittest

from modules.source_intake.collection_gap_report import (
    STATUS_FALLBACK_ONLY,
    STATUS_NOT_IMPLEMENTED,
    STATUS_OK,
)
from modules.source_intake.lane_collection_summary import (
    READINESS_READY_SHALLOW,
)
from modules.source_intake.source_health_dashboard import (
    DASHBOARD_STATUS_BLOCKED,
    DASHBOARD_STATUS_READY,
    build_source_health_dashboard,
)
from scripts.build_source_health_dashboard import build_dashboard_result


class TestSourceHealthDashboard(unittest.TestCase):
    def setUp(self):
        self.today = "2099-01-02"
        self.root = os.path.join(".", "source_health_dashboard_tmp", uuid.uuid4().hex)
        os.makedirs(self.root, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_json(self, filename: str, payload: dict) -> str:
        path = os.path.join(self.root, self.today, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return path

    def test_build_dashboard_ready_with_optional_artifacts(self):
        status_bundle = self._write_json(
            "source_intake_status_bundle.json",
            {"weak_lanes": ["news_society_economy"]},
        )
        gap_report = self._write_json(
            "collection_gap_report.json",
            {
                "schema_version": "collection_gap_report_v1",
                "source_count": 2,
                "status_counts": {
                    STATUS_NOT_IMPLEMENTED: 0,
                    STATUS_FALLBACK_ONLY: 0,
                    "FAILED": 0,
                    STATUS_OK: 2,
                },
                "status_summary": {
                    STATUS_OK: [
                        {
                            "source_id": "daum_news",
                            "status": STATUS_OK,
                            "lane_impact": ["news_society_economy"],
                            "item_count": 4,
                            "fallback_item_count": 0,
                        },
                        {
                            "source_id": "news1",
                            "status": STATUS_OK,
                            "lane_impact": ["lifestyle_knowledge"],
                            "item_count": 3,
                            "fallback_item_count": 0,
                        },
                    ],
                },
                "all_lanes": ["news_society_economy", "lifestyle_knowledge"],
            },
        )
        lane_summary = self._write_json(
            "lane_collection_summary.json",
            {
                "lane_summary": {
                    "news_society_economy": {
                        "counts_by_status": {
                            STATUS_NOT_IMPLEMENTED: 0,
                            STATUS_FALLBACK_ONLY: 0,
                            "FAILED": 0,
                            STATUS_OK: 1,
                        },
                        "top_missing_sources": [],
                        "lane_readiness": READINESS_READY_SHALLOW,
                    },
                    "lifestyle_knowledge": {
                        "counts_by_status": {
                            STATUS_NOT_IMPLEMENTED: 0,
                            STATUS_FALLBACK_ONLY: 0,
                            "FAILED": 0,
                            STATUS_OK: 1,
                        },
                        "top_missing_sources": [],
                        "lane_readiness": READINESS_READY_SHALLOW,
                    },
                },
                "lane_count": 2,
                "weak_lanes": [],
            },
        )
        source_health = self._write_json(
            "source_health.json",
            {
                "updated_at": "2026-07-14T19:57:47.084903",
                "latest": {
                    "daum_news": {
                        "attempted": True,
                        "success": True,
                        "count": 4,
                        "used_cache": False,
                    },
                    "news1": {
                        "attempted": True,
                        "success": True,
                        "count": 3,
                        "used_cache": False,
                    },
                },
            },
        )
        collector_statistics = self._write_json(
            "collector_statistics.json",
            {
                "updated_at": "2026-07-14T19:57:47.084903",
                "sources": [
                    {"source": "daum_news", "total_attempts": 10, "total_success": 10, "total_failures": 0, "total_fallback_used": 0},
                    {"source": "news1", "total_attempts": 3, "total_success": 3, "total_failures": 0, "total_fallback_used": 0},
                ],
            },
        )

        dashboard = build_source_health_dashboard(
            status_bundle_path=status_bundle,
            gap_report_path=gap_report,
            lane_summary_path=lane_summary,
            source_health_path=source_health,
            collector_statistics_path=collector_statistics,
        )

        self.assertEqual(dashboard["schema_version"], "source_health_dashboard_v1")
        self.assertEqual(dashboard["evidence_scope"], "artifact_reported")
        self.assertEqual(dashboard["dashboard_status"], DASHBOARD_STATUS_READY)
        self.assertEqual(dashboard["source_summary"]["sources_total"], 2)
        self.assertEqual(dashboard["source_summary"]["status_counts"][STATUS_OK], 2)
        self.assertEqual(dashboard["source_health"]["present"], True)
        self.assertEqual(dashboard["collector_statistics"]["present"], True)
        self.assertEqual(len(dashboard["lane_summaries"]), 2)
        self.assertEqual(len(dashboard["source_rows"]), 2)

        daum_row = next(row for row in dashboard["source_rows"] if row["source_id"] == "daum_news")
        self.assertEqual(daum_row["reported_status"], STATUS_OK)
        self.assertIn("source_health", daum_row)
        self.assertIn("collector_statistics", daum_row)

    def test_fail_closed_when_gap_report_is_malformed(self):
        status_bundle = self._write_json(
            "source_intake_status_bundle.json",
            {"weak_lanes": ["news_society_economy"]},
        )
        gap_path = os.path.join(self.root, self.today, "collection_gap_report.json")
        os.makedirs(os.path.dirname(gap_path), exist_ok=True)
        with open(gap_path, "w", encoding="utf-8") as handle:
            handle.write("{")
        lane_summary = self._write_json(
            "lane_collection_summary.json",
            {
                "lane_summary": {},
                "lane_count": 0,
                "weak_lanes": [],
            },
        )

        dashboard = build_source_health_dashboard(
            status_bundle_path=status_bundle,
            gap_report_path=gap_path,
            lane_summary_path=lane_summary,
        )

        self.assertEqual(dashboard["dashboard_status"], DASHBOARD_STATUS_BLOCKED)
        self.assertEqual(dashboard["source_summary"]["sources_total"], 0)
        self.assertEqual(dashboard["source_rows"], [])
        malformed = [item["path"] for item in dashboard["data_quality"]["malformed_artifacts"]]
        self.assertIn(gap_path, malformed)
        self.assertIn("required_artifact", [blocker["type"] for blocker in dashboard["blockers"]])

    def test_optional_absence_degrades_to_partial_without_required_blockers(self):
        status_bundle = self._write_json(
            "source_intake_status_bundle.json",
            {"weak_lanes": []},
        )
        gap_report = self._write_json(
            "collection_gap_report.json",
            {
                "status_counts": {
                    STATUS_NOT_IMPLEMENTED: 1,
                    STATUS_FALLBACK_ONLY: 0,
                    "FAILED": 0,
                    STATUS_OK: 1,
                },
                "status_summary": {
                    STATUS_NOT_IMPLEMENTED: [
                        {
                            "source_id": "daum_news",
                            "status": STATUS_NOT_IMPLEMENTED,
                            "lane_impact": ["news_society_economy"],
                            "item_count": 0,
                            "fallback_item_count": 0,
                        }
                    ],
                    STATUS_OK: [
                        {
                            "source_id": "news1",
                            "status": STATUS_OK,
                            "lane_impact": ["news_society_economy"],
                            "item_count": 2,
                            "fallback_item_count": 0,
                        }
                    ],
                },
                "source_count": 2,
                "all_lanes": ["news_society_economy"],
            },
        )
        lane_summary = self._write_json(
            "lane_collection_summary.json",
            {
                "lane_summary": {
                    "news_society_economy": {
                        "counts_by_status": {
                            STATUS_NOT_IMPLEMENTED: 1,
                            STATUS_FALLBACK_ONLY: 0,
                            "FAILED": 0,
                            STATUS_OK: 1,
                        },
                        "top_missing_sources": ["daum_news"],
                        "lane_readiness": "PARTIAL",
                    }
                },
                "lane_count": 1,
                "weak_lanes": ["news_society_economy"],
            },
        )

        dashboard = build_source_health_dashboard(
            status_bundle_path=status_bundle,
            gap_report_path=gap_report,
            lane_summary_path=lane_summary,
        )

        self.assertEqual(dashboard["source_health"]["present"], False)
        self.assertEqual(dashboard["collector_statistics"]["present"], False)
        self.assertNotEqual(dashboard["blockers"], [])

    def test_cli_prints_compact_json_result(self):
        status_bundle = self._write_json("source_intake_status_bundle.json", {"weak_lanes": []})
        gap_report = self._write_json("collection_gap_report.json", {
            "status_counts": {
                STATUS_NOT_IMPLEMENTED: 0,
                STATUS_FALLBACK_ONLY: 0,
                "FAILED": 0,
                STATUS_OK: 1,
            },
            "status_summary": {
                STATUS_OK: [
                    {
                        "source_id": "daum_news",
                        "status": STATUS_OK,
                        "lane_impact": ["news_society_economy"],
                    }
                ],
                "NOT_IMPLEMENTED": [],
            },
            "source_count": 1,
            "all_lanes": ["news_society_economy"],
        })
        lane_summary = self._write_json("lane_collection_summary.json", {
            "lane_summary": {
                "news_society_economy": {
                    "counts_by_status": {
                        STATUS_NOT_IMPLEMENTED: 0,
                        STATUS_FALLBACK_ONLY: 0,
                        "FAILED": 0,
                        STATUS_OK: 1,
                    },
                    "top_missing_sources": [],
                    "lane_readiness": READINESS_READY_SHALLOW,
                }
            },
            "lane_count": 1,
            "weak_lanes": [],
        })
        output_path = os.path.join(self.root, self.today, "dashboard.json")

        result = build_dashboard_result(
            status_bundle=status_bundle,
            gap_report=gap_report,
            lane_summary=lane_summary,
            output=output_path,
            source_health=None,
            collector_statistics=None,
        )
        self.assertEqual(result["status"], "written")
        with open(output_path, "r", encoding="utf-8") as handle:
            on_disk = json.load(handle)
        self.assertIn("schema_version", on_disk)
        self.assertEqual(on_disk["source_summary"]["sources_total"], 1)


if __name__ == "__main__":
    unittest.main()
