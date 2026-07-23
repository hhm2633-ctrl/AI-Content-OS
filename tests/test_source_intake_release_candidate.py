import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from modules.source_intake.source_intake_release_candidate import (
    RC_STATUS_GO,
    RC_STATUS_NO_GO,
    _extract_readiness_status_by_source,
    run_source_intake_release_candidate,
)


class TestSourceIntakeReleaseCandidate(unittest.TestCase):
    def setUp(self):
        self.today = "2099-12-31"
        self.root = tempfile.mkdtemp(prefix="source-intake-rc-")
        self.day_root = os.path.join(self.root, self.today)
        os.makedirs(self.day_root, exist_ok=True)
        self.status_bundle_path = os.path.join(self.day_root, "source_intake_status_bundle.json")
        self.gap_path = os.path.join(self.day_root, "collection_gap_report.json")
        self.shallow_path = os.path.join(self.day_root, "daily_shallow_collection.json")
        self.plan_path = os.path.join(self.day_root, "daily_collection_plan.json")
        self.lane_summary_path = os.path.join(self.day_root, "lane_collection_summary.json")
        self.queue_path = os.path.join(self.day_root, "spark_task_queue.json")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_gap_status_summary_maps_to_readiness_contract(self):
        result = _extract_readiness_status_by_source(
            {
                "status_summary": {
                    "OK": [{"source_id": "ready_source"}],
                    "FALLBACK_ONLY": [{"source_id": "partial_source"}],
                    "FAILED": [{"source_id": "blocked_source"}],
                    "NOT_IMPLEMENTED": [{"source_id": "external_source"}],
                }
            }
        )

        self.assertEqual(
            result,
            {
                "ready_source": "ready",
                "partial_source": "partial",
                "blocked_source": "blocked",
                "external_source": "external_blocked",
            },
        )

    @staticmethod
    def _write_json(path: str, payload) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _extract_sources(readiness_by_readiness):
        ordered = []
        for key in ("ready", "partial", "blocked", "external_blocked"):
            for item in readiness_by_readiness.get(key, []):
                source_id = item["source_id"]
                if isinstance(source_id, str) and source_id not in ordered:
                    ordered.append(source_id)
        return ordered

    def _write_artifacts(self, readiness_by_readiness):
        source_ids = self._extract_sources(readiness_by_readiness)
        readiness_counts = {
            "ready": len(readiness_by_readiness.get("ready", [])),
            "partial": len(readiness_by_readiness.get("partial", [])),
            "blocked": len(readiness_by_readiness.get("blocked", [])),
            "external_blocked": len(readiness_by_readiness.get("external_blocked", [])),
        }
        status_count = len(source_ids)
        status_counts = {
            "NOT_IMPLEMENTED": 0,
            "FALLBACK_ONLY": 0,
            "FAILED": 0,
            "OK": status_count,
        }

        self._write_json(
            self.plan_path,
            {
                "date": self.today,
                "plan_status": "ok",
                "lanes": [
                    {"lane_id": "lane_release_candidate", "shallow_profiles": source_ids},
                ],
            },
        )
        self._write_json(
            self.shallow_path,
            {
                "schema_version": "daily_shallow_collection_v1",
                "date": self.today,
                "source_results": [
                    {
                        "source_id": source_id,
                        "lane_id": "lane_release_candidate",
                        "attempted": True,
                        "success": True,
                        "skipped": False,
                        "count": 1,
                    }
                    for source_id in source_ids
                ],
                "items": [
                    {
                        "source_id": source_id,
                        "source_name": source_id,
                        "source_type": "news",
                        "keyword": f"{source_id} keyword",
                        "title": f"{source_id} title",
                        "published_at": "2099-12-31T00:00:00",
                        "link": f"https://example.com/{source_id}",
                        "collection_method": "release-candidate-fixture",
                        "base_score": 120,
                        "is_fallback": False,
                    }
                    for source_id in source_ids
                ],
                "item_count": len(source_ids),
            },
        )
        self._write_json(
            self.lane_summary_path,
            {
                "lane_count": 1,
                "lane_ids": ["lane_release_candidate"],
                "lane_summary": {"lane_release_candidate": {"top_missing_sources": []}},
            },
        )
        self._write_json(
            self.queue_path,
            {
                "task_count": len(source_ids),
                "spark_task_queue": [{"source_id": source_id} for source_id in source_ids],
            },
        )
        self._write_json(
            self.gap_path,
            {
                "source_status_by_readiness": readiness_by_readiness,
                "source_status_by_status": {"OK": [{"source_id": source_id} for source_id in source_ids]},
                "source_count": len(source_ids),
                "status_counts": status_counts,
            },
        )
        self._write_json(
            self.status_bundle_path,
            {
                "classification_source_count": status_count,
                "readiness_status_counts": readiness_counts,
                "status_counts": status_counts,
                "item_count": status_count,
            },
        )

    def run_release_candidate(self, source_manager=None, collection_gap_report_path=None):
        gap_path = collection_gap_report_path or self.gap_path
        return run_source_intake_release_candidate(
            today=self.today,
            source_manager=source_manager,
            source_intake_status_bundle_path=self.status_bundle_path,
            collection_gap_report_path=gap_path,
            daily_shallow_collection_path=self.shallow_path,
        )

    def test_direct_factory_sources_become_callable_and_candidates_are_composed(self):
        self._write_artifacts(
            {
                "ready": [{"source_id": "daum_news"}, {"source_id": "news1"}],
                "partial": [],
                "blocked": [],
                "external_blocked": [],
            }
        )

        result = self.run_release_candidate(source_manager=object())

        self.assertEqual(result["status"], RC_STATUS_GO)
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(len(result["candidates"]), 2)
        matrix_before = result["preflight"]["callability_matrix_before"]
        matrix_after = result["preflight"]["callability_matrix_after"]
        self.assertFalse(matrix_before["daum_news"]["callable"])
        self.assertFalse(matrix_before["news1"]["callable"])
        self.assertTrue(matrix_after["daum_news"]["callable"])
        self.assertTrue(matrix_after["news1"]["callable"])
        self.assertEqual(matrix_after["daum_news"]["path"], "direct_factory")
        self.assertEqual(matrix_after["news1"]["path"], "direct_factory")
        self.assertEqual(
            result["preflight"]["callability_delta"]["added_by_factory"],
            ["daum_news", "news1"],
        )

    def test_mapped_source_without_callable_path_is_fail_closed(self):
        self._write_artifacts(
            {
                "ready": [{"source_id": "naver_news"}],
                "partial": [],
                "blocked": [],
                "external_blocked": [],
            }
        )

        result = self.run_release_candidate(source_manager=object())

        self.assertEqual(result["status"], RC_STATUS_NO_GO)
        self.assertEqual(result["reason_code"], "readiness_callability_mismatch")
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["candidates"], [])
        self.assertIn("ready_source_not_callable:naver_news", result["preflight"].get("readiness_callability_mismatches", []))
        self.assertIn("naver_news", result["preflight"].get("mapped_unreachable", []))

    def test_non_ready_only_sources_are_fail_closed_preflight(self):
        self._write_artifacts(
            {
                "ready": [],
                "partial": [{"source_id": "daum_news"}],
                "blocked": [],
                "external_blocked": [],
            }
        )

        result = self.run_release_candidate(source_manager=object())

        self.assertEqual(result["status"], RC_STATUS_NO_GO)
        self.assertEqual(result["reason_code"], "no_ready_sources")
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["preflight"]["readiness_counts"]["partial"], 1)

    def test_non_ready_sources_are_isolated_while_ready_sources_continue(self):
        self._write_artifacts(
            {
                "ready": [{"source_id": "daum_news"}],
                "partial": [{"source_id": "news1"}],
                "blocked": [],
                "external_blocked": [],
            }
        )

        result = self.run_release_candidate(source_manager=object())

        self.assertEqual(result["status"], RC_STATUS_GO)
        self.assertEqual(result["ready_source_ids"], ["daum_news"])
        self.assertEqual(result["isolated_source_ids"], ["news1"])
        self.assertEqual(
            {item["source_id"] for item in result["eligible_collection"]["items"]},
            {"daum_news"},
        )

    def test_stale_and_malformed_artifacts_are_rejected(self):
        self._write_artifacts(
            {
                "ready": [{"source_id": "daum_news"}],
                "partial": [],
                "blocked": [],
                "external_blocked": [],
            }
        )
        with open(self.plan_path, "r", encoding="utf-8") as handle:
            stale_plan = json.load(handle)
        stale_plan["date"] = "2000-01-01"
        self._write_json(self.plan_path, stale_plan)

        stale_result = self.run_release_candidate(source_manager=object())
        self.assertEqual(stale_result["status"], RC_STATUS_NO_GO)
        self.assertEqual(stale_result["reason_code"], "consistency_failed")
        self.assertEqual(stale_result["candidate_count"], 0)
        self.assertEqual(stale_result["candidates"], [])

        self._write_json(
            self.plan_path,
            {
                "date": self.today,
                "plan_status": "ok",
                "lanes": [
                    {"lane_id": "lane_release_candidate", "shallow_profiles": ["daum_news"]},
                ],
            },
        )

        malformed_gap_path = os.path.join(self.day_root, "collection_gap_report_bad.json")
        with open(malformed_gap_path, "w", encoding="utf-8") as handle:
            handle.write("{ malformed")

        malformed_result = self.run_release_candidate(
            source_manager=object(),
            collection_gap_report_path=malformed_gap_path,
        )
        self.assertEqual(malformed_result["status"], RC_STATUS_NO_GO)
        self.assertEqual(malformed_result["reason_code"], "gap_report_load_failed")
        self.assertEqual(malformed_result["candidate_count"], 0)
        self.assertEqual(malformed_result["candidates"], [])

    def test_explicit_sibling_path_mismatch_rejects_fast(self):
        sibling_root = tempfile.mkdtemp(prefix="source-intake-rc-gap-")
        sibling_day_root = os.path.join(sibling_root, self.today)
        os.makedirs(sibling_day_root, exist_ok=True)
        try:
            self._write_artifacts(
                {
                    "ready": [{"source_id": "daum_news"}],
                    "partial": [],
                    "blocked": [],
                    "external_blocked": [],
                }
            )
            sibling_gap_path = os.path.join(sibling_day_root, "collection_gap_report.json")
            shutil.copyfile(self.gap_path, sibling_gap_path)

            result = run_source_intake_release_candidate(
                today=self.today,
                source_intake_status_bundle_path=self.status_bundle_path,
                collection_gap_report_path=sibling_gap_path,
                daily_shallow_collection_path=self.shallow_path,
                source_manager=object(),
            )
            self.assertEqual(result["status"], RC_STATUS_NO_GO)
            self.assertEqual(result["reason_code"], "gap_path_sibling_mismatch")
            self.assertEqual(result["candidate_count"], 0)
            self.assertEqual(result["candidates"], [])
        finally:
            shutil.rmtree(sibling_root, ignore_errors=True)

    def test_pipeline_exception_is_caught_as_fail_closed(self):
        self._write_artifacts(
            {
                "ready": [{"source_id": "daum_news"}],
                "partial": [],
                "blocked": [],
                "external_blocked": [],
            }
        )

        with mock.patch(
            "modules.source_intake.source_intake_release_candidate.run_validated_topic_candidate_pipeline",
            side_effect=RuntimeError("pipeline failure"),
        ):
            result = self.run_release_candidate(source_manager=object())

        self.assertEqual(result["status"], RC_STATUS_NO_GO)
        self.assertEqual(result["reason_code"], "pipeline_exception")
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["candidates"], [])


if __name__ == "__main__":
    unittest.main()
