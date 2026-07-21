import unittest

from modules.commerce.credential_manager import CredentialManager


class CredentialManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = CredentialManager()

    def test_has_credentials_always_false(self):
        self.assertFalse(self.manager.has_credentials("smartstore"))
        self.assertFalse(self.manager.has_credentials("coupang"))

    def test_has_credentials_rejects_unsupported_platform(self):
        with self.assertRaises(ValueError):
            self.manager.has_credentials("gmarket")

    def test_get_credential_status_never_configured(self):
        status = self.manager.get_credential_status("smartstore")
        self.assertFalse(status["configured"])
        self.assertEqual(status["source"], "dummy_credential_manager")

    def test_redact_always_returns_fixed_marker_never_partial_value(self):
        self.assertEqual(self.manager.redact("sk-super-secret-real-key-12345"), "***REDACTED***")
        self.assertEqual(self.manager.redact(""), "***REDACTED***")
        self.assertEqual(self.manager.redact(None), "***REDACTED***")

    def test_never_reads_environment(self):
        import os
        os.environ["COUPANG_ACCESS_KEY"] = "should_never_be_read"
        try:
            status = self.manager.get_credential_status("coupang")
            self.assertNotIn("should_never_be_read", str(status))
        finally:
            del os.environ["COUPANG_ACCESS_KEY"]


if __name__ == "__main__":
    unittest.main()
