import unittest

from modules.design_learning.reference_specimen_registry import (
    ReferenceSpecimenRegistry,
    ReferenceSpecimenValidationError,
    is_production_selectable,
    validate_reference_specimen,
)


def specimen(
    reference_id="ref-owner-001",
    approval_status="owner_approved",
    receipt="owner-receipt-001",
):
    return {
        "reference_id": reference_id,
        "source_claim_ids": ["claim-001"],
        "source_relative_path": "owner_source/batch/reference-001.png",
        "analysis_record_ids": ["analysis-001"],
        "account_fit": ["news"],
        "format_fit": ["card_news"],
        "slide_role_fit": ["hook"],
        "topic_fit": ["finance"],
        "emotion_fit": ["warning"],
        "media_requirements": {"required_count": 1, "aspect_ratios": ["4:5"]},
        "blueprint_id": "bp-owner-001",
        "approval_status": approval_status,
        "owner_approval_receipt_id": receipt,
        "reference_only": False,
        "measured_performance_claimed": False,
    }


class ReferenceSpecimenRegistryTests(unittest.TestCase):
    def test_owner_approved_with_receipt_is_selectable(self):
        registry = ReferenceSpecimenRegistry([specimen()])
        self.assertEqual(
            [item["reference_id"] for item in registry.selectable()],
            ["ref-owner-001"],
        )
        self.assertEqual(
            registry.require_selectable("ref-owner-001")["blueprint_id"],
            "bp-owner-001",
        )

    def test_unapproved_record_is_registered_but_not_selectable(self):
        registry = ReferenceSpecimenRegistry(
            [specimen(approval_status="candidate", receipt=None)]
        )
        self.assertEqual(registry.selectable(), [])
        with self.assertRaises(ReferenceSpecimenValidationError):
            registry.require_selectable("ref-owner-001")

    def test_reference_only_record_is_not_production_selectable(self):
        record = specimen()
        record["reference_only"] = True
        registry = ReferenceSpecimenRegistry([record])

        self.assertFalse(is_production_selectable(record))
        self.assertEqual([], registry.selectable())
        with self.assertRaises(ReferenceSpecimenValidationError):
            registry.require_selectable("ref-owner-001")

    def test_owner_approved_without_receipt_fails_closed(self):
        record = specimen(receipt=None)
        self.assertFalse(is_production_selectable(record))
        with self.assertRaises(ReferenceSpecimenValidationError):
            validate_reference_specimen(record)

    def test_invalid_schema_and_performance_claim_fail_closed(self):
        missing = specimen()
        del missing["source_claim_ids"]
        with self.assertRaises(ReferenceSpecimenValidationError):
            validate_reference_specimen(missing)

        claimed = specimen()
        claimed["measured_performance_claimed"] = True
        with self.assertRaises(ReferenceSpecimenValidationError):
            validate_reference_specimen(claimed)

    def test_registry_keeps_immutable_copies_and_rejects_duplicate_id(self):
        source = specimen()
        registry = ReferenceSpecimenRegistry([source])
        source["account_fit"].append("story")
        returned = registry.get("ref-owner-001")
        returned["account_fit"].append("beauty")
        self.assertEqual(registry.get("ref-owner-001")["account_fit"], ["news"])
        with self.assertRaises(ReferenceSpecimenValidationError):
            registry.register(specimen())

    def test_no_image_bytes_are_accepted(self):
        record = specimen()
        record["media_requirements"]["image_bytes"] = b"not-allowed"
        with self.assertRaises(ReferenceSpecimenValidationError):
            validate_reference_specimen(record)


if __name__ == "__main__":
    unittest.main()
