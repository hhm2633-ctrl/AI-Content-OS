import copy
import json
import unittest

from modules.card_news.reference_driven_production import (
    produce_reference_driven_slide,
)
from modules.design_learning.layout_blueprint_contract import with_geometry_hash
from modules.design_learning.reference_specimen_registry import (
    INDEPENDENT_REVALIDATION_SCHEMA_VERSION,
    VISUAL_GATE_ADAPTER_SCHEMA_VERSION,
    VISUAL_GATE_SCHEMA_VERSION,
)


def make_blueprint():
    return with_geometry_hash(
        {
            "blueprint_id": "bp-owner-001",
            "blueprint_version": 1,
            "canvas": {"width": 1080, "height": 1350},
            "layout_family": "owner_reference",
            "regions": [
                {
                    "region_id": "media-1",
                    "role": "primary_media",
                    "box_norm": [0.04, 0.04, 0.92, 0.56],
                    "z_index": 0,
                    "alignment": "center",
                    "padding_norm": 0.0,
                    "background": {"color": "#000000"},
                    "border": None,
                    "radius_norm": 0.0,
                    "overlap_policy": "none",
                    "required": True,
                },
                {
                    "region_id": "headline-1",
                    "role": "headline",
                    "box_norm": [0.08, 0.64, 0.84, 0.16],
                    "z_index": 2,
                    "alignment": "left",
                    "padding_norm": [0.02, 0.03],
                    "background": None,
                    "border": None,
                    "radius_norm": 0.01,
                    "overlap_policy": "none",
                    "required": True,
                    "max_lines": 2,
                },
                {
                    "region_id": "source-1",
                    "role": "source_label",
                    "box_norm": [0.08, 0.88, 0.84, 0.05],
                    "z_index": 2,
                    "alignment": "left",
                    "padding_norm": 0.0,
                    "background": None,
                    "border": None,
                    "radius_norm": 0.0,
                    "overlap_policy": "none",
                    "required": True,
                },
            ],
            "style_tokens": {"background": "#ffffff", "ink": "#111111"},
            "slide_role_fit": ["hook"],
            "media_requirements": {
                "primary_media": {
                    "min_count": 1,
                    "max_count": 1,
                    "aspect_ratio": 1.314286,
                    "aspect_tolerance": 0.1,
                }
            },
            "fit_constraints": {
                "required_roles": [
                    "primary_media",
                    "headline",
                    "source_label",
                ],
                "source_label_required": True,
                "headline": {
                    "max_chars": 24,
                    "max_lines": 2,
                    "chars_per_line": 12,
                    "reduction_limit": 1.25,
                },
            },
            "provenance": {
                "reference_id": "ref-owner-001",
                "analysis_record_ids": ["analysis-001"],
            },
            "geometry_hash": "",
        }
    )


def make_visual_gate_receipt(geometry_hash):
    return {
        "schema_version": VISUAL_GATE_SCHEMA_VERSION,
        "adapter_schema_version": VISUAL_GATE_ADAPTER_SCHEMA_VERSION,
        "independent_revalidation_schema_version": (
            INDEPENDENT_REVALIDATION_SCHEMA_VERSION
        ),
        "status": "pass",
        "visual_status": "visual_geometry_pass",
        "receipt_id": "visual-gate-fixture-001",
        "source_receipt_path": "tests/fixtures/visual-gate-fixture-001.json",
        "source_receipt_sha256": "fixture-source-receipt-sha256",
        "reference_id": "ref-owner-001",
        "blueprint_id": "bp-owner-001",
        "geometry_hash": geometry_hash,
        "gate_result_hash": "fixture-gate-result-hash",
        "confidence_used_as_pass": False,
        "auto_owner_approval": False,
        "production_approval_granted": False,
    }


def make_specimen(reference_only=False, geometry_hash=None):
    if geometry_hash is None:
        geometry_hash = make_blueprint()["geometry_hash"]
    return {
        "reference_id": "ref-owner-001",
        "source_claim_ids": ["claim-001"],
        "source_relative_path": "owner_source/reference-001.png",
        "analysis_record_ids": ["analysis-001"],
        "account_fit": ["news"],
        "format_fit": ["card_news"],
        "slide_role_fit": ["hook"],
        "topic_fit": ["금융"],
        "emotion_fit": ["warning"],
        "season_fit": ["summer"],
        "media_requirements": {
            "min_count": 1,
            "max_count": 1,
            "aspects": ["portrait"],
        },
        "max_copy_char_count": 42,
        "blueprint_id": "bp-owner-001",
        "approval_status": "owner_approved",
        "owner_approval_receipt_id": "owner-receipt-001",
        "reference_only": reference_only,
        "measured_performance_claimed": False,
        "geometry_visual_gate_receipt": make_visual_gate_receipt(geometry_hash),
    }


def make_request():
    blueprint = make_blueprint()
    return {
        "specimens": [make_specimen(geometry_hash=blueprint["geometry_hash"])],
        "blueprints": {"bp-owner-001": blueprint},
        "context": {
            "account": "news",
            "slide_role": "hook",
            "emotion": "warning",
            "season": "summer",
            "topic": "금융",
            "media_count": 1,
            "media_aspect": "portrait",
            "copy_char_count": 12,
        },
        "content": {
            "headline": "지금 확인할 핵심 변화",
            "source_label": "자료: 공식 발표",
        },
        "media": {
            "primary_media": [
                {
                    "asset_id": "asset-001",
                    "aspect_ratio": 1.314286,
                    "crop_allowed": False,
                }
            ]
        },
    }


class ReferenceDrivenProductionTests(unittest.TestCase):
    def test_ready_preserves_one_reference_geometry_and_receipts(self):
        request = make_request()
        result = produce_reference_driven_slide(**request)

        self.assertEqual("ready", result["status"])
        self.assertEqual("fit", result["outcome"])
        self.assertFalse(result["legacy_renderer_fallback_allowed"])
        self.assertEqual(
            "ref-owner-001",
            result["selection"]["primary_reference_id"],
        )
        self.assertEqual(
            request["blueprints"]["bp-owner-001"]["geometry_hash"],
            result["geometry_hash"],
        )
        receipt = result["adapted_slide"]["reference_consumption_receipt"]
        self.assertEqual(result["geometry_hash"], receipt["geometry_hash"])
        self.assertEqual(
            "owner-receipt-001",
            receipt["owner_approval_receipt_id"],
        )
        json.dumps(result, ensure_ascii=False, allow_nan=False)

    def test_reference_only_specimen_is_blocked(self):
        request = make_request()
        request["specimens"] = [make_specimen(reference_only=True)]

        result = produce_reference_driven_slide(**request)

        self.assertEqual("blocked", result["status"])
        self.assertEqual(
            "no_owner_approved_production_specimen",
            result["reason_code"],
        )
        self.assertFalse(result["legacy_renderer_fallback_allowed"])

    def test_invalid_geometry_hash_is_blocked_before_selection(self):
        request = make_request()
        request["blueprints"]["bp-owner-001"]["geometry_hash"] = "tampered"

        result = produce_reference_driven_slide(**request)

        self.assertEqual("blocked", result["status"])
        self.assertEqual(
            "no_compatible_owner_approved_reference",
            result["reason_code"],
        )
        self.assertEqual(
            "blueprint_invalid",
            result["blueprint_errors"][0]["code"],
        )

    def test_media_mismatch_requests_alternative_without_fallback(self):
        request = make_request()
        request["media"]["primary_media"][0]["aspect_ratio"] = 0.5

        result = produce_reference_driven_slide(**request)

        self.assertEqual("select_alternative_reference", result["status"])
        self.assertEqual("select_alternative_reference", result["outcome"])
        self.assertFalse(result["legacy_renderer_fallback_allowed"])
        self.assertNotIn("adapted_slide", result)

    def test_non_json_input_is_blocked(self):
        request = make_request()
        request["context"]["bad"] = {object()}

        result = produce_reference_driven_slide(**request)

        self.assertEqual("blocked", result["status"])
        self.assertEqual("input_not_json_safe", result["reason_code"])

    def test_long_headline_requests_copy_reduction(self):
        request = make_request()
        request["content"]["headline"] = "가" * 28
        request["context"]["copy_char_count"] = 28
        request["specimens"][0]["max_copy_char_count"] = 40

        result = produce_reference_driven_slide(**request)

        self.assertEqual("reduce_nonessential_copy", result["status"])
        self.assertEqual("reduce_nonessential_copy", result["outcome"])
        self.assertFalse(result["legacy_renderer_fallback_allowed"])


if __name__ == "__main__":
    unittest.main()
