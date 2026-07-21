"""Independent coverage for modules/common/service_diagnostic.py.

Priority-2 gap-fill test (long autonomous maintainability task): this file was
previously untested anywhere in the repo despite being pure, zero-network,
zero-dependency logic (per the "highest ROI free test target" finding in the
codebase-wide test-coverage audit). No existing module or test file is
modified.
"""

import json
import unittest
from unittest.mock import patch

from modules.common.service_diagnostic import ServiceDiagnostic


class FakeError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class ServiceDiagnosticClassifyErrorTests(unittest.TestCase):
    def setUp(self):
        self.diag = ServiceDiagnostic()

    def test_missing_api_key_takes_priority_over_error_content(self):
        self.assertEqual(self.diag.classify_error(FakeError("anything"), api_key_present=False), "missing_api_key")

    def test_status_code_401_is_auth_failed(self):
        self.assertEqual(self.diag.classify_error(FakeError("boom", status_code=401), api_key_present=True), "auth_failed")

    def test_status_code_403_is_auth_failed(self):
        self.assertEqual(self.diag.classify_error(FakeError("boom", status_code=403), api_key_present=True), "auth_failed")

    def test_status_code_429_is_rate_limited(self):
        self.assertEqual(self.diag.classify_error(FakeError("boom", status_code=429), api_key_present=True), "rate_limited")

    def test_message_text_unauthorized_is_auth_failed(self):
        self.assertEqual(self.diag.classify_error(FakeError("401 Unauthorized"), api_key_present=True), "auth_failed")

    def test_message_text_rate_limit_is_rate_limited(self):
        self.assertEqual(self.diag.classify_error(FakeError("Rate limit exceeded"), api_key_present=True), "rate_limited")

    def test_message_text_connection_refused(self):
        self.assertEqual(self.diag.classify_error(FakeError("Connection refused (10061)"), api_key_present=True), "connection_refused")

    def test_message_text_timeout(self):
        self.assertEqual(self.diag.classify_error(FakeError("Request timed out"), api_key_present=True), "timeout")

    def test_unrecognized_error_is_unknown(self):
        self.assertEqual(self.diag.classify_error(FakeError("something weird happened"), api_key_present=True), "unknown_error")

    def test_classify_error_never_raises_on_pathological_input(self):
        class ExplodingError:
            def __str__(self):
                raise RuntimeError("cannot stringify")

        result = self.diag.classify_error(ExplodingError(), api_key_present=True)
        self.assertEqual(result, "unknown_error")

    def test_classify_error_handles_none(self):
        self.assertEqual(self.diag.classify_error(None, api_key_present=True), "unknown_error")


class ServiceDiagnosticSecretMaskingTests(unittest.TestCase):
    def setUp(self):
        self.diag = ServiceDiagnostic()

    def test_openai_style_key_is_masked(self):
        secret = "sk-abcdefgh12345678"
        masked = self.diag.mask_secrets(f"error calling API with key {secret}")
        self.assertNotIn(secret, masked)
        self.assertIn("***MASKED***", masked)

    def test_bearer_token_is_masked(self):
        masked = self.diag.mask_secrets("Authorization: Bearer abcdefgh12345678")
        self.assertNotIn("abcdefgh12345678", masked)
        self.assertIn("***MASKED***", masked)

    def test_api_key_equals_pattern_is_masked_but_key_name_preserved(self):
        masked = self.diag.mask_secrets("failed with api_key=verysecretvalue123")
        self.assertNotIn("verysecretvalue123", masked)
        self.assertIn("api_key", masked)
        self.assertIn("***MASKED***", masked)

    def test_password_pattern_is_masked(self):
        masked = self.diag.mask_secrets("password: hunter2ishere")
        self.assertNotIn("hunter2ishere", masked)

    def test_plain_text_without_secret_shape_is_unchanged(self):
        text = "connection refused while calling the trend collector"
        self.assertEqual(self.diag.mask_secrets(text), text)

    def test_mask_secrets_never_raises_on_pathological_input(self):
        class ExplodingStr:
            def __str__(self):
                raise RuntimeError("boom")

        result = self.diag.mask_secrets(ExplodingStr())
        self.assertEqual(result, "***error_message_unavailable***")

    def test_safe_error_text_used_by_classify_error_also_masks_secrets(self):
        # classify_error's message-based branches must never leak a raw secret
        # even when the exception text happens to contain one.
        error = FakeError("timeout while using api_key=supersecrettoken1234")
        result = self.diag.classify_error(error, api_key_present=True)
        self.assertEqual(result, "timeout")  # still classified correctly
        # And the underlying masking helper independently proves no leak:
        self.assertNotIn("supersecrettoken1234", self.diag.mask_secrets(str(error)))


class ServiceDiagnosticBuildTests(unittest.TestCase):
    def setUp(self):
        self.diag = ServiceDiagnostic()

    def test_missing_env_key_short_circuits_to_missing_api_key(self):
        with patch.object(ServiceDiagnostic, "check_env_key", return_value=False):
            result = self.diag.build_service_diagnostic("openai", "OPENAI_API_KEY", error=FakeError("irrelevant"))

        self.assertEqual(result["error_type"], "missing_api_key")
        self.assertFalse(result["api_key_present"])
        self.assertEqual(result["safe_message"], ServiceDiagnostic.SAFE_MESSAGES["missing_api_key"])

    def test_no_error_and_key_present_yields_empty_error_type(self):
        with patch.object(ServiceDiagnostic, "check_env_key", return_value=True):
            result = self.diag.build_service_diagnostic("openai", "OPENAI_API_KEY", error=None, status="ok")

        self.assertEqual(result["error_type"], "")
        self.assertEqual(result["safe_message"], "")
        self.assertTrue(result["api_key_present"])

    def test_error_with_key_present_is_classified(self):
        with patch.object(ServiceDiagnostic, "check_env_key", return_value=True):
            result = self.diag.build_service_diagnostic("openai", "OPENAI_API_KEY", error=FakeError("timed out"))

        self.assertEqual(result["error_type"], "timeout")
        self.assertEqual(result["safe_message"], ServiceDiagnostic.SAFE_MESSAGES["timeout"])

    def test_build_service_diagnostic_never_raises(self):
        with patch.object(ServiceDiagnostic, "check_env_key", side_effect=RuntimeError("boom")):
            result = self.diag.build_service_diagnostic("openai", "OPENAI_API_KEY")

        self.assertEqual(result["error_type"], "unknown_error")
        self.assertFalse(result["api_key_present"])

    def test_build_diagnostic_from_reason_ok_status(self):
        result = self.diag.build_diagnostic_from_reason("naver_news", reason="", status="ok")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["error_type"], "")

    def test_build_diagnostic_from_reason_maps_known_reason(self):
        result = self.diag.build_diagnostic_from_reason("naver_news", reason="http_429")
        self.assertEqual(result["error_type"], "rate_limited")

    def test_build_diagnostic_from_reason_unknown_reason_falls_back(self):
        result = self.diag.build_diagnostic_from_reason("naver_news", reason="some_brand_new_reason_code")
        self.assertEqual(result["error_type"], "unknown_error")

    def test_map_reason_to_error_type_never_raises(self):
        self.assertEqual(self.diag.map_reason_to_error_type(None), "unknown_error")


class ServiceDiagnosticRecordTests(unittest.TestCase):
    def setUp(self):
        self.diag = ServiceDiagnostic()

    def test_record_persists_and_reloads_via_real_tmp_path(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_path = Path(tmp_dir) / "service_diagnostic.json"
            with patch.object(ServiceDiagnostic, "DIAGNOSTIC_PATH", fake_path):
                self.diag.record({"service": "openai", "status": "fallback_used", "error_type": "timeout"})
                self.diag.record({"service": "naver_news", "status": "ok", "error_type": ""})

            with open(fake_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            self.assertEqual(len(data["records"]), 2)
            self.assertEqual(data["records"][0]["diagnostic"]["service"], "openai")

    def test_record_bounds_history_to_max_records(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_path = Path(tmp_dir) / "service_diagnostic.json"
            with patch.object(ServiceDiagnostic, "DIAGNOSTIC_PATH", fake_path), \
                 patch.object(ServiceDiagnostic, "MAX_RECORDS", 3):
                for index in range(5):
                    self.diag.record({"service": f"svc-{index}"})

            with open(fake_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            self.assertEqual(len(data["records"]), 3)
            # Oldest two records were dropped; the most recent 3 remain.
            services = [record["diagnostic"]["service"] for record in data["records"]]
            self.assertEqual(services, ["svc-2", "svc-3", "svc-4"])

    def test_record_never_raises_on_unwritable_path(self):
        from pathlib import Path

        # A path whose parent cannot be created (a file, not a directory) --
        # `record()` must swallow the failure, never propagate it.
        with patch.object(ServiceDiagnostic, "DIAGNOSTIC_PATH", Path("this/path/does/not/exist/at/all.json")), \
             patch.object(Path, "mkdir", side_effect=OSError("cannot create")):
            try:
                self.diag.record({"service": "openai"})
            except Exception as error:  # pragma: no cover - defensive
                self.fail(f"record() must never raise, got: {error}")

    def test_record_with_empty_diagnostic_is_a_no_op(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_path = Path(tmp_dir) / "service_diagnostic.json"
            with patch.object(ServiceDiagnostic, "DIAGNOSTIC_PATH", fake_path):
                self.diag.record({})
            self.assertFalse(fake_path.exists())


if __name__ == "__main__":
    unittest.main()
