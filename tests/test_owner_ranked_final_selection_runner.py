import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_owner_ranked_final_selection import execute


class OwnerRankedFinalSelectionRunnerTests(unittest.TestCase):
    def test_cached_function_relations_reach_matching_and_story_briefs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue_path = root / "queue.json"
            catalog_path = root / "catalog.json"
            output_path = root / "result.json"
            queue_path.write_text(json.dumps({
                "schema_version": "owner_ranked_deep_dive_queue_v1",
                "requests": [
                    {
                        "request_id": "owner_review:shampoo",
                        "candidate_id": "shampoo",
                        "account": "C",
                        "category": "뷰티",
                        "title": "마트 샴푸도 괜찮을까?",
                        "grade": "1",
                        "source_urls": ["https://example.com/shampoo"],
                    },
                    {
                        "request_id": "owner_review:bangs",
                        "candidate_id": "bangs",
                        "account": "C",
                        "category": "뷰티·헤어",
                        "title": "비 올 때 축 처진 앞머리 복구합니다",
                        "grade": "1",
                        "source_urls": ["https://example.com/bangs"],
                    },
                ],
            }, ensure_ascii=False), encoding="utf-8")
            catalog_path.write_text(json.dumps({"products": [
                {"product_id": "S", "name": "데일리 두피 샴푸", "category": "화장품/미용"},
                {"product_id": "B", "name": "앞머리 픽서 뿌리볼륨 헤어스프레이", "category": "화장품/미용"},
            ]}, ensure_ascii=False), encoding="utf-8")

            result = execute(
                repository_root=Path(__file__).resolve().parents[1],
                queue_path=queue_path,
                catalog_path=catalog_path,
                console_root=root / "console",
                output_path=output_path,
            )
            annotations = {
                item["candidate_id"]: item
                for item in result["selection"]["accounts"]["C"]["selected"]
            }
            self.assertEqual(annotations["shampoo"]["commerce"]["commerce_status"], "matched")
            self.assertEqual(annotations["bangs"]["commerce"]["commerce_status"], "matched")
            self.assertTrue(annotations["bangs"]["commerce"]["relation_signals_used"])
            self.assertTrue(result["brandconnect_summary"]["relation_index_supplied"])
            self.assertTrue(result["brandconnect_summary"]["relation_index_connected"])
            self.assertGreater(
                result["brandconnect_summary"]["relation_signal_annotation_count"],
                0,
            )
            briefs = {
                item["candidate_id"]: item
                for item in result["commerce_story_stage"]["story_briefs"]["candidates"]
            }
            self.assertEqual(briefs["shampoo"]["status"], "ready")
            self.assertEqual(briefs["bangs"]["status"], "ready")
            self.assertFalse(result["commerce_story_stage"]["network_used"])
            self.assertTrue(output_path.exists())

    def test_ungraded_queue_reaches_production_handoff_without_publish_or_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue_path = root / "queue.json"
            catalog_path = root / "catalog.json"
            output_path = root / "result.json"
            queue_path.write_text(json.dumps({
                "schema_version": "owner_ranked_deep_dive_queue_v1",
                "requests": [{
                    "request_id": "candidate_review:ungraded",
                    "candidate_id": "ungraded",
                    "account": "A",
                    "category": "국내뉴스",
                    "title": "등급 없이 자동 선정되는 후보",
                    "grade": None,
                    "selection_status": "TOP",
                    "production_eligible": True,
                    "selection_score": {"score": 0.91},
                    "source_urls": ["https://example.com/ungraded"],
                }],
            }, ensure_ascii=False), encoding="utf-8")
            catalog_path.write_text(
                json.dumps({"products": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            result = execute(
                repository_root=Path(__file__).resolve().parents[1],
                queue_path=queue_path,
                catalog_path=catalog_path,
                console_root=root / "console",
                output_path=output_path,
            )
            self.assertEqual(result["selection"]["selected_count"], 1)
            self.assertEqual(result["production_handoff"]["status"], "ready")
            self.assertFalse(result["production_handoff"]["owner_grade_required"])
            self.assertTrue(
                result["production_handoff"]["automatic_selection_is_not_owner_approval"]
            )
            self.assertEqual(
                result["production_handoff"]["owner_approval_required_at"],
                "pre_upload_manual_upload_ready",
            )
            self.assertFalse(result["manual_upload_ready"])
            self.assertFalse(result["actual_publish"])
            self.assertFalse(result["upload_executed"])
            self.assertFalse(result["agent_console"]["owner_review_gate_used"])


if __name__ == "__main__":
    unittest.main()
