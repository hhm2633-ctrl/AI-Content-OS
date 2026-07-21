import json
import tempfile
import unittest
from pathlib import Path

from modules.commerce.audit_logger import AuditLogger


class AuditLoggerTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.logger = AuditLogger(audit_dir=Path(self.tmp_dir.name))

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _read_last_entry(self, path):
        with open(path, "r", encoding="utf-8") as file:
            lines = [line for line in file if line.strip()]
        return json.loads(lines[-1])

    def test_log_writes_jsonl_entry(self):
        path = self.logger.log({"type": "test_entry", "value": 1})
        self.assertIsNotNone(path)
        entry = self._read_last_entry(path)
        self.assertEqual(entry["type"], "test_entry")
        self.assertEqual(entry["mode"], "dry_run")
        self.assertIn("timestamp", entry)

    def test_forbidden_key_is_redacted(self):
        path = self.logger.log({"type": "test_entry", "api_key": "sk-real-secret-value"})
        entry = self._read_last_entry(path)
        self.assertEqual(entry["api_key"], "***REDACTED***")

    def test_forbidden_key_redacted_case_insensitive(self):
        path = self.logger.log({"type": "test_entry", "API_KEY": "sk-real-secret-value"})
        entry = self._read_last_entry(path)
        self.assertEqual(entry["API_KEY"], "***REDACTED***")

    def test_nested_dict_is_sanitized_recursively(self):
        path = self.logger.log({"type": "test_entry", "nested": {"client_secret": "shhh"}})
        entry = self._read_last_entry(path)
        self.assertEqual(entry["nested"]["client_secret"], "***REDACTED***")

    def test_high_entropy_unlabeled_string_is_redacted(self):
        secret_looking = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
        path = self.logger.log({"type": "test_entry", "note": secret_looking})
        entry = self._read_last_entry(path)
        self.assertEqual(entry["note"], "***REDACTED***")

    def test_normal_free_text_is_not_redacted(self):
        path = self.logger.log({"type": "test_entry", "note": "this is a normal audit message"})
        entry = self._read_last_entry(path)
        self.assertEqual(entry["note"], "this is a normal audit message")

    def test_log_submit_blocked_records_no_real_call(self):
        path = self.logger.log_submit_blocked("smartstore", "blocked by design")
        entry = self._read_last_entry(path)
        self.assertEqual(entry["type"], "submit_blocked")
        self.assertFalse(entry["real_api_call_attempted"])

    def test_log_never_raises_on_malformed_entry(self):
        path = self.logger.log("not a dict")  # type: ignore[arg-type]
        self.assertIsNotNone(path)
        entry = self._read_last_entry(path)
        self.assertEqual(entry["type"], "malformed_entry")

    def test_log_never_raises_when_dir_uncreatable(self):
        # Point at a path that collides with an existing file, not a directory.
        blocker_file = Path(self.tmp_dir.name) / "blocker"
        blocker_file.write_text("x", encoding="utf-8")
        broken_logger = AuditLogger(audit_dir=blocker_file / "audit")
        result = broken_logger.log({"type": "test_entry"})
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
