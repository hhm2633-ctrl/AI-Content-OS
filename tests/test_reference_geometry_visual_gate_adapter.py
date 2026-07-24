import json
import tempfile
import unittest
from pathlib import Path

from modules.design_learning.reference_specimen_registry import (
    adapt_reference_geometry_draft_for_visual_gate,
)


def nested_draft():
    return {
        "schema_version": "owner_reference_v2_geometry_draft_v1",
        "reference_id": "owner-ref-001",
        "geometry_contract_valid": True,
        "confidence": 0.999,
        "blueprint_draft": {
            "blueprint_id": "bp-owner-001",
            "geometry_hash": "geometry-001",
            "canvas": {"width": 1080, "height": 1350},
            "regions": [
                {
                    "region_id": "headline",
                    "role": "headline",
                    "recognized_text": "장마철 헤어 관리법",
                    "box_norm": [0.08, 0.10, 0.84, 0.15],
                }
            ],
            "provenance": {
                "reference_id": "owner-ref-001",
                "crop_box_original_px": {
                    "x": 0,
                    "y": 100,
                    "width": 1080,
                    "height": 1350,
                },
                "crop_method": "explicit_owner_reference_crop",
            },
        },
    }


class ReferenceGeometryVisualGateAdapterTests(unittest.TestCase):
    def test_nested_schema_maps_and_confidence_does_not_grant_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt_path = Path(temp) / "receipt.json"
            receipt = {
                "schema_version": "reference_geometry_independent_revalidation_v1",
                "auto_approval_performed": False,
            }
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            result = adapt_reference_geometry_draft_for_visual_gate(
                nested_draft(),
                independent_receipt=receipt,
                independent_item={
                    "reference_id": "owner-ref-001",
                    "visual_status": "rework_required",
                    "production_selectable": False,
                },
                independent_receipt_path=receipt_path,
            )
        self.assertEqual(result["gate_result"]["status"], "pass")
        self.assertEqual(result["status"], "rework_required")
        self.assertIsNone(result["geometry_visual_gate_receipt"])
        self.assertFalse(
            result["adapter_receipt"]["silent_flattening_used"]
        )
        self.assertFalse(
            result["adapter_receipt"]["confidence_used_as_pass"]
        )

    def test_independent_visual_pass_creates_candidate_receipt_not_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt_path = Path(temp) / "receipt.json"
            receipt = {
                "schema_version": "reference_geometry_independent_revalidation_v1",
                "auto_approval_performed": False,
            }
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            result = adapt_reference_geometry_draft_for_visual_gate(
                nested_draft(),
                independent_receipt=receipt,
                independent_item={
                    "reference_id": "owner-ref-001",
                    "visual_status": "visual_geometry_pass",
                    "production_selectable": False,
                },
                independent_receipt_path=receipt_path,
            )
        self.assertEqual(result["status"], "pass")
        visual = result["geometry_visual_gate_receipt"]
        self.assertEqual(visual["visual_status"], "visual_geometry_pass")
        self.assertFalse(visual["confidence_used_as_pass"])
        self.assertFalse(visual["auto_owner_approval"])
        self.assertFalse(visual["production_approval_granted"])
        self.assertFalse(result["production_selectable"])


if __name__ == "__main__":
    unittest.main()
