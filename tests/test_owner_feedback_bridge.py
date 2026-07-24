import tempfile
import unittest
from pathlib import Path

from modules.agent_console.owner_feedback_bridge import record_owner_grade


class OwnerFeedbackBridgeTests(unittest.TestCase):
    def test_grade_is_recorded_as_optional_reference_not_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = record_owner_grade(
                candidate_id="candidate-1",
                grade="1",
                category="news",
                title="후보",
                account="A",
                feedback_path=root / "feedback.jsonl",
                index_path=root / "index.json",
                console_state_path=root / "state.json",
            )
            event = result["event"]
            self.assertEqual(result["learning_record"]["stage"], "CLASSIFIED_EXAMPLE")
            self.assertIn("optional_reference_signal", event["applies_to"])
            self.assertIn("not_selection_gate", event["applies_to"])
            self.assertIn("not_production_gate", event["applies_to"])
            self.assertFalse(result["signal_contract"]["selection_gate"])
            self.assertFalse(result["signal_contract"]["production_gate"])
            self.assertFalse(result["signal_contract"]["upload_approval"])
            self.assertEqual(
                result["signal_contract"]["approval_gate_stage"],
                "pre_upload_manual_upload_ready",
            )


if __name__ == "__main__":
    unittest.main()
