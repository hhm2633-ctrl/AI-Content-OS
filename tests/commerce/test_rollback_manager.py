import json
import tempfile
import unittest
from pathlib import Path

from modules.commerce.audit_logger import AuditLogger
from modules.commerce.rollback_manager import RollbackManager


class RollbackManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.audit_logger = AuditLogger(audit_dir=Path(self.tmp_dir.name))
        self.manager = RollbackManager(audit_logger=self.audit_logger)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _read_last_entry(self, path):
        with open(path, "r", encoding="utf-8") as file:
            lines = [line for line in file if line.strip()]
        return json.loads(lines[-1])

    def test_coupang_rollback_capability_confirmed(self):
        capability = self.manager.rollback_capability("coupang")
        self.assertTrue(capability["confirmed"])
        self.assertIn("stop-sales", capability["mechanism"])

    def test_smartstore_rollback_capability_unconfirmed(self):
        capability = self.manager.rollback_capability("smartstore")
        self.assertFalse(capability["confirmed"])
        self.assertIsNone(capability["mechanism"])

    def test_unknown_platform_rollback_capability_defaults_unconfirmed(self):
        capability = self.manager.rollback_capability("gmarket")
        self.assertFalse(capability["confirmed"])
        self.assertEqual(capability["evidence"], "unknown platform")

    def test_request_rollback_never_executes(self):
        result = self.manager.request_rollback("coupang", "listing-123", "policy rejection")
        self.assertFalse(result["executed"])
        self.assertEqual(result["mode"], "dry_run")

    def test_request_rollback_returns_capability_snapshot(self):
        result = self.manager.request_rollback("coupang", "listing-123", "policy rejection")
        self.assertTrue(result["capability"]["confirmed"])

    def test_request_rollback_smartstore_still_never_executes(self):
        # Even though smartstore's rollback mechanism is UNKNOWN, Phase 2A
        # never actually rolls back anything for either platform.
        result = self.manager.request_rollback("smartstore", "listing-456", "policy rejection")
        self.assertFalse(result["executed"])
        self.assertFalse(result["capability"]["confirmed"])

    def test_request_rollback_logs_audit_entry(self):
        self.manager.request_rollback("coupang", "listing-123", "policy rejection")
        log_files = list(Path(self.tmp_dir.name).glob("*.jsonl"))
        self.assertEqual(len(log_files), 1)
        entry = self._read_last_entry(log_files[0])
        self.assertEqual(entry["type"], "rollback_requested")
        self.assertFalse(entry["executed"])
        self.assertTrue(entry["capability_confirmed"])

    def test_request_rollback_includes_reason_and_reference(self):
        result = self.manager.request_rollback("coupang", "listing-789", "price mismatch")
        self.assertEqual(result["listing_reference"], "listing-789")
        self.assertEqual(result["reason"], "price mismatch")


if __name__ == "__main__":
    unittest.main()
