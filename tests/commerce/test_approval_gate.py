import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from modules.commerce.approval_gate import CAPABILITIES, ApprovalGate


class ApprovalGateTests(unittest.TestCase):
    def test_missing_config_file_fails_closed(self):
        gate = ApprovalGate(approval_path=Path("this/path/does/not/exist.json"))
        for capability in CAPABILITIES:
            self.assertFalse(gate.is_capability_approved(capability))

    def test_malformed_config_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "approval.json"
            path.write_text("{not valid json", encoding="utf-8")
            gate = ApprovalGate(approval_path=path)
            self.assertFalse(gate.is_capability_approved("listing_creation"))

    def test_gate_not_satisfied_blocks_even_if_capability_flagged_true(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "approval.json"
            path.write_text(json.dumps({
                "phase_2_cto_gate_satisfied": False,
                "approved_capabilities": {"listing_creation": True},
            }), encoding="utf-8")
            gate = ApprovalGate(approval_path=path)
            self.assertFalse(gate.is_capability_approved("listing_creation"))

    def test_gate_satisfied_and_capability_true_approves(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "approval.json"
            path.write_text(json.dumps({
                "phase_2_cto_gate_satisfied": True,
                "approved_capabilities": {"listing_creation": True, "order_actions": False},
                "approval_identity": {
                    "platform": "smartstore",
                    "product_id": "P-1",
                    "payload_hash": "a" * 64,
                    "approval_id": "AP-1",
                    "issued_at": "2026-07-22T00:00:00+00:00",
                    "expires_at": "2026-07-23T00:00:00+00:00",
                },
            }), encoding="utf-8")
            gate = ApprovalGate(approval_path=path)
            target = {
                "platform": "smartstore",
                "product_id": "P-1",
                "payload_hash": "a" * 64,
                "approval_id": "AP-1",
                "now": datetime(2026, 7, 22, 12, tzinfo=timezone.utc),
            }
            self.assertTrue(gate.is_capability_approved("listing_creation", **target))
            self.assertFalse(gate.is_capability_approved("order_actions", **target))

    def test_unknown_capability_fails_closed_without_raising(self):
        gate = ApprovalGate(approval_path=Path("this/path/does/not/exist.json"))
        self.assertFalse(gate.is_capability_approved("delete_everything"))

    def test_check_returns_explainable_reason_never_bare_bool(self):
        gate = ApprovalGate(approval_path=Path("this/path/does/not/exist.json"))
        result = gate.check("listing_creation")
        self.assertIn("capability", result)
        self.assertIn("approved", result)
        self.assertIn("reason", result)
        self.assertFalse(result["approved"])

    def test_check_unknown_capability_does_not_raise(self):
        gate = ApprovalGate(approval_path=Path("this/path/does/not/exist.json"))
        result = gate.check("delete_everything")
        self.assertFalse(result["approved"])

    def test_real_config_file_starts_closed(self):
        real_path = Path("config/commerce/approval.json")
        self.assertTrue(real_path.exists(), "config/commerce/approval.json must exist after this Sprint")
        gate = ApprovalGate(approval_path=real_path)
        for capability in CAPABILITIES:
            self.assertFalse(gate.is_capability_approved(capability))


if __name__ == "__main__":
    unittest.main()
