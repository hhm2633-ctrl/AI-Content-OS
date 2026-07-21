import unittest

from modules.commerce.payload_builder import build_payload
from modules.commerce.schema_validator import ValidationResult, validate_payload
from tests.commerce.fixtures import sample_commerce_result


class ValidationResultTests(unittest.TestCase):
    def test_add_missing_required_blocks(self):
        result = ValidationResult()
        result.add_missing("category", required=True, reason_code="missing_required_field", message="missing")
        self.assertFalse(result.valid)
        self.assertEqual(len(result.blocked_reasons), 1)

    def test_add_missing_optional_does_not_block(self):
        result = ValidationResult()
        result.add_missing("search_keywords", required=False, reason_code=None, message="missing")
        self.assertTrue(result.valid)
        self.assertEqual(len(result.blocked_reasons), 0)

    def test_to_dict_shape(self):
        result = ValidationResult()
        result.add_warning("heads up")
        as_dict = result.to_dict()
        self.assertEqual(set(as_dict), {"valid", "missing_fields", "blocked_reasons", "warnings"})
        self.assertEqual(as_dict["warnings"], ["heads up"])


class ValidatePayloadTests(unittest.TestCase):
    def setUp(self):
        self.commerce_result = sample_commerce_result()

    def test_smartstore_payload_invalid_due_to_known_phase1_gaps(self):
        # category/price/stock/shipping/images/return_address are all
        # required and structurally unavailable from Phase 1 today.
        payload = build_payload("smartstore", self.commerce_result)
        result = validate_payload("smartstore", payload)
        self.assertFalse(result.valid)
        blocked_fields = {entry["field"] for entry in result.blocked_reasons}
        self.assertIn("category", blocked_fields)
        self.assertIn("price", blocked_fields)

    def test_pending_confirmation_never_counts_as_present(self):
        payload = build_payload("coupang", self.commerce_result)
        result = validate_payload("coupang", payload)
        missing_field_names = {entry["field"] for entry in result.missing_fields}
        self.assertIn("detail_description", missing_field_names)

    def test_conditional_field_not_blocking_when_condition_not_triggered(self):
        payload = build_payload("smartstore", self.commerce_result)
        result = validate_payload("smartstore", payload)
        # options is conditional and empty (no variants) -- present in
        # missing_fields (informational) but must not appear as blocking.
        blocked_fields = {entry["field"] for entry in result.blocked_reasons}
        self.assertNotIn("options", blocked_fields)

    def test_contract_load_failure_fails_closed(self):
        result = validate_payload("unsupported_platform", {"fields": {}})
        self.assertFalse(result.valid)
        self.assertEqual(result.blocked_reasons[0]["code"], "contract_load_failed")

    def test_empty_payload_adds_warning(self):
        result = validate_payload("smartstore", {"fields": {}})
        self.assertIn("Payload contains no fields at all -- likely an empty or malformed Phase 1 result.", result.warnings)


if __name__ == "__main__":
    unittest.main()
