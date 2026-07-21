import unittest

from modules.commerce.approval_gate import CAPABILITIES
from modules.commerce.marketplace_base import MarketplaceAdapterBase, RealApiCallBlockedError
from tests.commerce.fixtures import sample_commerce_result


class _FakeAdapter(MarketplaceAdapterBase):
    """Minimal concrete subclass -- exercises the base class only, never a
    real platform's `_platform_specific_checks()` override."""

    @property
    def platform_name(self) -> str:
        return "smartstore"


class MarketplaceAdapterBaseTests(unittest.TestCase):
    def setUp(self):
        self.adapter = _FakeAdapter()
        self.commerce_result = sample_commerce_result()

    def test_submit_always_raises(self):
        with self.assertRaises(RealApiCallBlockedError):
            self.adapter.submit()

    def test_submit_raises_regardless_of_arguments(self):
        with self.assertRaises(RealApiCallBlockedError):
            self.adapter.submit("anything", keyword="value")

    def test_build_payload_delegates_to_payload_builder(self):
        payload = self.adapter.build_payload(self.commerce_result)
        self.assertEqual(payload["platform"], "smartstore")
        self.assertIn("fields", payload)

    def test_validate_delegates_to_schema_validator(self):
        payload = self.adapter.build_payload(self.commerce_result)
        result = self.adapter.validate(payload)
        self.assertIn("valid", result)
        self.assertIn("blocked_reasons", result)

    def test_dry_run_never_makes_network_call(self):
        result = self.adapter.dry_run(self.commerce_result)
        self.assertFalse(result["network_call_made"])

    def test_dry_run_shape(self):
        result = self.adapter.dry_run(self.commerce_result)
        self.assertEqual(result["platform"], "smartstore")
        self.assertEqual(result["mode"], "dry_run")
        self.assertIn("payload", result)
        self.assertIn("validation", result)
        self.assertIn("credential_status", result)
        self.assertIn("approval_status", result)

    def test_dry_run_approval_status_covers_expected_capabilities(self):
        result = self.adapter.dry_run(self.commerce_result)
        expected = {"listing_creation", "listing_update", "inventory_update", "price_update"}
        self.assertEqual(set(result["approval_status"]), expected)
        self.assertTrue(expected.issubset(set(CAPABILITIES)))

    def test_dry_run_credential_status_reports_not_configured(self):
        result = self.adapter.dry_run(self.commerce_result)
        self.assertFalse(result["credential_status"]["configured"])

    def test_idempotency_key_deterministic_for_same_input(self):
        key_one = self.adapter._idempotency_key(self.commerce_result)
        key_two = self.adapter._idempotency_key(self.commerce_result)
        self.assertIsNotNone(key_one)
        self.assertEqual(key_one, key_two)
        self.assertTrue(key_one.startswith("sha256:"))

    def test_idempotency_key_differs_for_different_request_id(self):
        other = sample_commerce_result()
        other["request_id"] = "different_request"
        key_one = self.adapter._idempotency_key(self.commerce_result)
        key_two = self.adapter._idempotency_key(other)
        self.assertNotEqual(key_one, key_two)

    def test_idempotency_key_none_for_malformed_input(self):
        self.assertIsNone(self.adapter._idempotency_key(None))
        self.assertIsNone(self.adapter._idempotency_key({}))

    def test_idempotency_key_none_for_non_dict(self):
        self.assertIsNone(self.adapter._idempotency_key("not a dict"))

    def test_platform_specific_checks_default_is_noop(self):
        payload = self.adapter.build_payload(self.commerce_result)
        result = self.adapter.validate(payload)
        # Default hook returns the same validation outcome untouched.
        from modules.commerce.schema_validator import validate_payload
        expected = validate_payload("smartstore", payload).to_dict()
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
