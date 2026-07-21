import json
import tempfile
import unittest
from pathlib import Path

from modules.agent_console.owner_feedback_bridge import record_owner_grade


class OwnerFeedbackBridgeTests(unittest.TestCase):
    def test_grade_is_recorded_as_example_with_execution_trace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            feedback = root / "feedback.jsonl"
            index = root / "index.json"
            state = root / "state.json"
            state.write_text(json.dumps({
                "jobs": [{
                    "job_id": "job-C-1",
                    "candidate_id": "C-1",
                    "status": "completed",
                    "handoff_path": "handoffs/job-C-1.json",
                    "dispatch": {"education_receipt": {
                        "prompt_pack_sha256": "pack-hash",
                        "owner_learning_ids": ["rule-1"],
                    }},
                }],
            }), encoding="utf-8")
            result = record_owner_grade(
                candidate_id="C-1",
                grade="1",
                category="뷰티",
                title="헤어 후보",
                account="C",
                feedback_path=feedback,
                index_path=index,
                console_state_path=state,
            )
            self.assertEqual(result["learning_record"]["stage"], "CLASSIFIED_EXAMPLE")
            self.assertEqual(result["event"]["execution_trace"]["job_id"], "job-C-1")
            self.assertEqual(result["event"]["execution_trace"]["prompt_pack_sha256"], "pack-hash")
            self.assertFalse(result["event"]["is_performance_evidence"])


if __name__ == "__main__":
    unittest.main()
