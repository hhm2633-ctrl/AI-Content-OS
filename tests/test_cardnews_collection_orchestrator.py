import json
import tempfile
import unittest
from pathlib import Path

from modules.source_intake.cardnews_collection_orchestrator import (
    run_cardnews_collection_orchestrator,
)


class Manager:
    config = {}


class CardnewsCollectionOrchestratorTest(unittest.TestCase):
    def test_stops_at_pending_owner_review(self):
        with tempfile.TemporaryDirectory() as root:
            day_root = Path(root) / "2099-01-01"

            def collection_runner(**_kwargs):
                return {
                    "schema_version": "daily_shallow_collection_v1",
                    "status": "completed",
                    "date": "2099-01-01",
                    "plan": {"date": "2099-01-01", "lanes": []},
                    "source_results": [{"source_id": "daum_news", "success": True}],
                    "items": [
                        {
                            "source_id": "daum_news",
                            "title": "후보",
                            "link": "https://example.com/item",
                        }
                    ],
                    "item_count": 1,
                }

            def gap_runner(**_kwargs):
                gap = {
                    "source_status_by_readiness": {
                        "ready": [{"source_id": "daum_news"}],
                        "partial": [],
                        "blocked": [],
                        "external_blocked": [],
                    }
                }
                (day_root / "collection_gap_report.json").write_text(json.dumps(gap), encoding="utf-8")
                (day_root / "collector_implementation_queue.json").write_text(
                    json.dumps({"implementation_queue": []}), encoding="utf-8"
                )
                return {"status": "completed"}

            def lane_runner(**_kwargs):
                (day_root / "lane_collection_summary.json").write_text(json.dumps({}), encoding="utf-8")
                return {"status": "written"}

            def spark_runner(**kwargs):
                Path(kwargs["output_path"]).write_text(
                    json.dumps({"task_count": 0, "spark_task_queue": []}), encoding="utf-8"
                )
                return {"status": "completed"}

            def bundle_runner(**_kwargs):
                return {"status": "written", "bundle": {"status_counts": {}}}

            def rc_runner(**_kwargs):
                return {
                    "status": "GO",
                    "eligible_collection": collection_runner(),
                    "isolated_source_ids": [],
                }

            def discovery_runner(_collection):
                return {
                    "status": "top_topics_ready",
                    "top_topics": {
                        "account_a_news_incident": [
                            {
                                "candidate_id": "candidate-1",
                                "title": "검토 후보",
                                "primary_category": "major_news_policy",
                                "source_refs": [{"url": "https://example.com/item"}],
                            }
                        ],
                        "account_b_issue_story": [],
                        "account_c_beauty_fashion": [],
                    },
                    "watch_review_queue": {
                        "queue_by_account": {
                            "account_a_news_incident": [],
                            "account_b_issue_story": [
                                {
                                    "candidate_id": "candidate-b-watch",
                                    "title": "B 검토 후보",
                                    "primary_category": "community_buzz",
                                    "source_refs": [{"url": "https://example.com/b"}],
                                }
                            ],
                            "account_c_beauty_fashion": [
                                {
                                    "candidate_id": "candidate-c-watch",
                                    "title": "C 검토 후보",
                                    "primary_category": "beauty_fashion",
                                    "source_refs": [{"url": "https://example.com/c"}],
                                }
                            ],
                        }
                    },
                }

            result = run_cardnews_collection_orchestrator(
                today="2099-01-01",
                output_root=root,
                source_manager=Manager(),
                collection_runner=collection_runner,
                gap_runner=gap_runner,
                lane_runner=lane_runner,
                spark_runner=spark_runner,
                bundle_runner=bundle_runner,
                rc_runner=rc_runner,
                discovery_runner=discovery_runner,
            )

            self.assertEqual(result["status"], "owner_review_ready")
            request = result["owner_review_queue"]["requests"][0]
            self.assertIsNone(request["grade"])
            self.assertEqual(request["review_state"], "pending_owner_grade")
            self.assertEqual(
                {item["account"] for item in result["owner_review_queue"]["requests"]},
                {"A", "B", "C"},
            )
            watch_requests = [
                item
                for item in result["owner_review_queue"]["requests"]
                if item["review_track"] == "watch_promotion"
            ]
            self.assertEqual(len(watch_requests), 2)
            self.assertTrue(all(item["watch_promotion_required"] for item in watch_requests))
            self.assertTrue(all(not item["production_eligible"] for item in watch_requests))
            self.assertFalse(result["owner_selection_performed"])
            self.assertFalse(result["deep_discovery_performed"])
            self.assertFalse(result["production_performed"])
            self.assertTrue(Path(result["owner_queue_path"]).exists())


if __name__ == "__main__":
    unittest.main()
