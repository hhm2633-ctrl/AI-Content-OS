import unittest

from modules.commerce.coupang_adapter import CoupangAdapter
from modules.commerce.schema_validator import ValidationResult
from tests.commerce.fixtures import sample_commerce_result


class CoupangAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = CoupangAdapter()
        self.commerce_result = sample_commerce_result()

    def test_platform_name(self):
        self.assertEqual(self.adapter.platform_name, "coupang")

    def test_dry_run_includes_platform_notes(self):
        result = self.adapter.dry_run(self.commerce_result)
        self.assertIn("platform_notes", result)
        self.assertTrue(len(result["platform_notes"]) >= 4)

    def test_dry_run_reports_workflow_control_forced_false(self):
        result = self.adapter.dry_run(self.commerce_result)
        joined = " ".join(result["platform_notes"])
        self.assertIn("requested", joined)
        self.assertIn("True", joined)  # forced_requested_false is True (i.e. correctly forced)

    def test_dry_run_workflow_control_is_always_false(self):
        result = self.adapter.dry_run(self.commerce_result)
        self.assertIs(result["payload"]["workflow_control"]["requested"], False)

    def test_dry_run_never_makes_network_call(self):
        result = self.adapter.dry_run(self.commerce_result)
        self.assertFalse(result["network_call_made"])

    def test_dry_run_fulfillment_model_warning_present_for_sample_result(self):
        # Phase 1 has no fulfillment_model concept -- this must always warn.
        result = self.adapter.dry_run(self.commerce_result)
        warnings = result["validation"]["warnings"]
        self.assertTrue(any("fulfillment_model" in warning for warning in warnings))

    def test_workflow_control_requested_true_is_blocking(self):
        payload = {
            "fields": {"fulfillment_model": {"status": "ready", "value": "marketplace"}},
            "workflow_control": {"requested": True},
        }
        result = ValidationResult()
        checked = self.adapter._platform_specific_checks(payload, result)
        self.assertFalse(checked.valid)
        codes = {reason["code"] for reason in checked.blocked_reasons}
        self.assertIn("workflow_control_unsafe_default", codes)

    def test_workflow_control_missing_is_blocking(self):
        payload = {"fields": {}, "workflow_control": {}}
        result = ValidationResult()
        checked = self.adapter._platform_specific_checks(payload, result)
        self.assertFalse(checked.valid)

    def test_workflow_control_requested_false_is_not_blocking(self):
        payload = {
            "fields": {"fulfillment_model": {"status": "ready", "value": "marketplace"}},
            "workflow_control": {"requested": False},
        }
        result = ValidationResult()
        checked = self.adapter._platform_specific_checks(payload, result)
        self.assertTrue(checked.valid)
        self.assertEqual(checked.blocked_reasons, [])

    def test_fulfillment_model_undetermined_adds_warning(self):
        payload = {
            "fields": {"fulfillment_model": {"status": "missing", "value": None}},
            "workflow_control": {"requested": False},
        }
        result = ValidationResult()
        checked = self.adapter._platform_specific_checks(payload, result)
        self.assertTrue(any("fulfillment_model" in warning for warning in checked.warnings))

    def test_fulfillment_model_determined_does_not_add_warning(self):
        payload = {
            "fields": {"fulfillment_model": {"status": "ready", "value": "marketplace"}},
            "workflow_control": {"requested": False},
        }
        result = ValidationResult()
        checked = self.adapter._platform_specific_checks(payload, result)
        self.assertFalse(any("fulfillment_model" in warning for warning in checked.warnings))

    def test_platform_specific_checks_never_raises_on_empty_payload(self):
        result = ValidationResult()
        checked = self.adapter._platform_specific_checks({}, result)
        self.assertFalse(checked.valid)  # workflow_control.requested missing -> not False -> blocking


if __name__ == "__main__":
    unittest.main()
