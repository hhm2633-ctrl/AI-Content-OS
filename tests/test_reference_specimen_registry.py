import json
import tempfile
import unittest
from pathlib import Path

from modules.design_learning.reference_specimen_registry import (
    ReferenceSpecimenRegistry,
    ReferenceSpecimenValidationError,
    audit_existing_reference_v2_material,
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
        "geometry_visual_gate_receipt": {
            "schema_version": "reference_geometry_visual_gate.v1",
            "adapter_schema_version": "reference_geometry_visual_gate_adapter_v1",
            "independent_revalidation_schema_version": "reference_geometry_independent_revalidation_v1",
            "status": "pass",
            "visual_status": "visual_geometry_pass",
            "receipt_id": "visual-gate-001",
            "source_receipt_path": "F:/qa/independent_visual_revalidation_receipt.json",
            "source_receipt_sha256": "a" * 64,
            "reference_id": reference_id,
            "blueprint_id": "bp-owner-001",
            "geometry_hash": "geometry-hash-001",
            "gate_result_hash": "b" * 64,
            "confidence_used_as_pass": False,
            "auto_owner_approval": False,
            "production_approval_granted": False,
        },
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

    def test_visual_gate_pass_receipt_is_required(self):
        record = specimen()
        record["geometry_visual_gate_receipt"] = {}
        self.assertFalse(is_production_selectable(record))
        with self.assertRaises(ReferenceSpecimenValidationError):
            validate_reference_specimen(record)

    def test_confidence_is_not_visual_gate_pass_evidence(self):
        record = specimen()
        record["geometry_visual_gate_receipt"] = {
            "status": "pass",
            "confidence": 0.999,
        }
        self.assertFalse(is_production_selectable(record))

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

    def test_existing_analysis_creates_candidate_evidence_without_fake_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root = root / "owner_source"
            batch = source_root / "batch_001"
            batch.mkdir(parents=True)
            (batch / "reference.jpg").write_bytes(b"fixture")
            analysis_path = root / "knowledge" / "analysis.json"
            analysis_path.parent.mkdir(parents=True)
            analysis_path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_no": 1,
                                "design_learning": "large hook over primary media",
                                "format_use": ["card_news"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            taxonomy = {
                "records": [
                    {
                        "learning_id": "claim:1",
                        "source_file": "knowledge/analysis.json",
                        "source_item_id": "item_0001",
                        "accounts": ["news"],
                        "formats": ["card_news"],
                        "learning_layers": ["layout", "hook"],
                        "owner_confirmed": True,
                    }
                ]
            }
            result = audit_existing_reference_v2_material(
                source_root=source_root,
                taxonomy_payload=taxonomy,
                repository_root=root,
            )
            candidate = result["candidate_evidence"][0]
            self.assertEqual(
                candidate["source_relative_path"],
                "owner_source/batch_001/reference.jpg",
            )
            self.assertEqual(candidate["approval_status"], "candidate")
            self.assertIsNone(candidate["owner_approval_receipt_id"])
            self.assertTrue(candidate["reference_only"])
            self.assertFalse(candidate["production_selectable"])
            self.assertEqual(result["selectable_reference_ids"], [])
            self.assertFalse(result["auto_approval_performed"])
            self.assertIn(
                "owner_approval_receipts_missing",
                {item["code"] for item in result["blockers"]},
            )

    def test_explicit_legacy_approval_is_preserved_but_geometry_still_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root = root / "owner_source"
            batch = source_root / "batch_001"
            batch.mkdir(parents=True)
            (batch / "reference.jpg").write_bytes(b"fixture")
            analysis_path = root / "analysis.json"
            analysis_path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_no": 1,
                                "design_learning": "approved observation",
                                "approval": {
                                    "status": "OWNER_APPROVED",
                                    "owner_feedback_event_id": "owner-event-1",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = audit_existing_reference_v2_material(
                source_root=source_root,
                taxonomy_payload={
                    "records": [
                        {
                            "learning_id": "claim:approved",
                            "source_file": "analysis.json",
                            "source_item_id": "item_0001",
                            "accounts": ["story"],
                            "formats": ["card_news"],
                            "learning_layers": ["layout"],
                            "owner_confirmed": True,
                        }
                    ]
                },
                repository_root=root,
            )
            candidate = result["candidate_evidence"][0]
            self.assertEqual(candidate["approval_status"], "owner_approved")
            self.assertEqual(
                candidate["owner_approval_receipt_id"],
                "owner-event-1",
            )
            self.assertTrue(candidate["reference_only"])
            self.assertFalse(candidate["production_selectable"])
            self.assertIn(
                "complete_v2_geometry_blueprints_missing",
                {item["code"] for item in result["blockers"]},
            )


if __name__ == "__main__":
    unittest.main()
