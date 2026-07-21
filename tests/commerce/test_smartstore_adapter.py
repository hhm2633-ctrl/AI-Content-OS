import unittest

from modules.commerce.schema_validator import ValidationResult
from modules.commerce.smartstore_adapter import SmartStoreAdapter
from tests.commerce.fixtures import sample_commerce_result


class SmartStoreAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = SmartStoreAdapter()
        self.commerce_result = sample_commerce_result()

    def test_platform_name(self):
        self.assertEqual(self.adapter.platform_name, "smartstore")

    def test_dry_run_includes_platform_notes(self):
        result = self.adapter.dry_run(self.commerce_result)
        self.assertIn("platform_notes", result)
        self.assertTrue(len(result["platform_notes"]) >= 3)

    def test_platform_notes_mention_no_dedicated_price_stock_endpoint(self):
        result = self.adapter.dry_run(self.commerce_result)
        joined = " ".join(result["platform_notes"]).lower()
        self.assertIn("no dedicated price/stock", joined)

    def test_platform_notes_mention_major_vs_leaf_category(self):
        result = self.adapter.dry_run(self.commerce_result)
        joined = " ".join(result["platform_notes"])
        self.assertIn("MAJOR", joined)
        self.assertIn("leaf", joined)

    def test_dry_run_never_makes_network_call(self):
        result = self.adapter.dry_run(self.commerce_result)
        self.assertFalse(result["network_call_made"])

    def test_category_and_notice_both_ready_adds_warning(self):
        payload = {
            "fields": {
                "category": {"status": "ready", "value": "leaf-123"},
                "notice_information": {"status": "ready", "value": {"manufacturer": "X"}},
            }
        }
        result = ValidationResult()
        checked = self.adapter._platform_specific_checks(payload, result)
        self.assertEqual(len(checked.warnings), 1)
        self.assertIn("DIFFERENT category-id levels", checked.warnings[0])

    def test_category_missing_does_not_add_warning(self):
        payload = {
            "fields": {
                "category": {"status": "missing", "value": None},
                "notice_information": {"status": "ready", "value": {"manufacturer": "X"}},
            }
        }
        result = ValidationResult()
        checked = self.adapter._platform_specific_checks(payload, result)
        self.assertEqual(len(checked.warnings), 0)

    def test_notice_missing_does_not_add_warning(self):
        payload = {
            "fields": {
                "category": {"status": "ready", "value": "leaf-123"},
                "notice_information": {"status": "missing", "value": None},
            }
        }
        result = ValidationResult()
        checked = self.adapter._platform_specific_checks(payload, result)
        self.assertEqual(len(checked.warnings), 0)

    def test_platform_specific_checks_never_raises_on_empty_payload(self):
        result = ValidationResult()
        checked = self.adapter._platform_specific_checks({}, result)
        self.assertEqual(checked.warnings, [])

    def test_real_commerce_result_dry_run_does_not_trigger_dual_status_warning(self):
        # CONFIRMED Phase 1 gap: category is never exposed, so this warning
        # cannot fire from a real sample_commerce_result() today.
        result = self.adapter.dry_run(self.commerce_result)
        warnings = result["validation"]["warnings"]
        self.assertFalse(any("DIFFERENT category-id levels" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
