import unittest

from modules.commerce.payload_builder import PENDING_MARKER, build_payload, summarize_gaps
from tests.commerce.fixtures import sample_commerce_result


class PayloadBuilderTests(unittest.TestCase):
    def setUp(self):
        self.commerce_result = sample_commerce_result()

    def test_build_payload_resolves_real_product_name(self):
        payload = build_payload("smartstore", self.commerce_result)
        self.assertEqual(payload["fields"]["product_name"]["value"], "TestBrand Electric Kettle TB-100")
        self.assertEqual(payload["fields"]["product_name"]["status"], "ready")

    def test_build_payload_resolves_notice_information_dict(self):
        payload = build_payload("smartstore", self.commerce_result)
        self.assertEqual(payload["fields"]["notice_information"]["value"]["manufacturer"], "TestManufacturer Co.")

    def test_build_payload_resolves_nested_country_of_origin(self):
        payload = build_payload("smartstore", self.commerce_result)
        self.assertEqual(payload["fields"]["country_of_origin"]["value"], "Korea")

    def test_build_payload_never_invents_category(self):
        # CONFIRMED Phase 1 output gap: category is not exposed anywhere.
        payload = build_payload("smartstore", self.commerce_result)
        self.assertIsNone(payload["fields"]["category"]["value"])
        self.assertEqual(payload["fields"]["category"]["status"], "missing")

    def test_build_payload_marks_unknown_platform_field_pending(self):
        # coupang detail_description has a real Phase 1 value but an UNKNOWN
        # platform_field -- must be pending_confirmation, never guessed.
        payload = build_payload("coupang", self.commerce_result)
        entry = payload["fields"]["detail_description"]
        self.assertEqual(entry["status"], PENDING_MARKER)
        self.assertIsNotNone(entry["value"])

    def test_build_payload_workflow_control_coupang_forced_false(self):
        payload = build_payload("coupang", self.commerce_result)
        self.assertIs(payload["workflow_control"]["requested"], False)

    def test_build_payload_never_raises_on_empty_commerce_result(self):
        payload = build_payload("smartstore", {})
        self.assertTrue(all(entry["status"] == "missing" for entry in payload["fields"].values()))

    def test_build_payload_never_raises_on_none_commerce_result(self):
        payload = build_payload("smartstore", None)
        self.assertTrue(all(entry["status"] == "missing" for entry in payload["fields"].values()))

    def test_summarize_gaps_partitions_correctly(self):
        payload = build_payload("coupang", self.commerce_result)
        gaps = summarize_gaps(payload)
        self.assertIn("product_name", gaps["ready"])
        self.assertIn("category", gaps["missing"])
        self.assertIn("detail_description", gaps["pending_confirmation"])

    def test_composite_manufacturer_field_resolves(self):
        payload = build_payload("smartstore", self.commerce_result)
        self.assertEqual(payload["fields"]["brand_manufacturer"]["value"], "TestManufacturer Co.")

    def test_benefits_resolves_from_detail_page_root(self):
        result = sample_commerce_result()
        result["detail_page"]["benefits"]["items"] = ["10% off this week"]
        payload = build_payload("smartstore", result)
        self.assertEqual(payload["fields"]["benefits"]["value"], ["10% off this week"])


if __name__ == "__main__":
    unittest.main()
