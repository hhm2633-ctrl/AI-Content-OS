import copy
import unittest

from modules.design_learning.layout_blueprint_contract import (
    LayoutBlueprintValidationError,
    compute_geometry_hash,
    validate_layout_blueprint,
    with_geometry_hash,
)


def valid_blueprint():
    blueprint = {
        "blueprint_id": "bp-owner-001",
        "blueprint_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "layout_family": "owner_reference",
        "regions": [
            {
                "region_id": "media-1",
                "role": "primary_media",
                "box_norm": [0.0, 0.0, 1.0, 0.62],
                "z_index": 0,
                "alignment": "center",
                "padding_norm": 0.0,
                "background": {"color": "#000000"},
                "border": None,
                "radius_norm": 0.0,
                "overlap_policy": "allow_headline",
                "required": True,
            },
            {
                "region_id": "headline-1",
                "role": "headline",
                "box_norm": [0.08, 0.66, 0.84, 0.18],
                "z_index": 2,
                "alignment": "left",
                "padding_norm": [0.02, 0.03],
                "background": None,
                "border": None,
                "radius_norm": 0.01,
                "overlap_policy": "none",
                "required": True,
            },
        ],
        "style_tokens": {"background": "#ffffff", "ink": "#111111"},
        "fit_constraints": {
            "required_roles": ["primary_media", "headline"],
            "headline_max_lines": 3,
        },
        "provenance": {
            "reference_id": "ref-owner-001",
            "analysis_record_ids": ["analysis-001"],
        },
        "geometry_hash": "",
    }
    return with_geometry_hash(blueprint)


class LayoutBlueprintContractTests(unittest.TestCase):
    def test_valid_blueprint_passes_and_hash_is_deterministic(self):
        first = valid_blueprint()
        reordered = {
            key: copy.deepcopy(first[key])
            for key in reversed(list(first.keys()))
        }
        self.assertEqual(compute_geometry_hash(first), compute_geometry_hash(reordered))
        self.assertEqual(
            validate_layout_blueprint(first)["geometry_hash"],
            first["geometry_hash"],
        )

    def test_box_must_stay_inside_normalized_canvas(self):
        blueprint = valid_blueprint()
        blueprint["regions"][0]["box_norm"] = [0.8, 0.0, 0.3, 0.5]
        blueprint = with_geometry_hash(blueprint)
        with self.assertRaises(LayoutBlueprintValidationError):
            validate_layout_blueprint(blueprint)

    def test_required_role_must_have_required_region(self):
        blueprint = valid_blueprint()
        blueprint["regions"][1]["required"] = False
        blueprint = with_geometry_hash(blueprint)
        with self.assertRaises(LayoutBlueprintValidationError):
            validate_layout_blueprint(blueprint)

    def test_unsupported_role_fails_closed(self):
        blueprint = valid_blueprint()
        blueprint["regions"][0]["role"] = "decorative_guess"
        blueprint = with_geometry_hash(blueprint)
        with self.assertRaises(LayoutBlueprintValidationError):
            validate_layout_blueprint(blueprint)

    def test_geometry_mutation_invalidates_hash(self):
        blueprint = valid_blueprint()
        blueprint["regions"][0]["box_norm"][2] = 0.9
        with self.assertRaisesRegex(LayoutBlueprintValidationError, "geometry_hash mismatch"):
            validate_layout_blueprint(blueprint)

    def test_missing_schema_field_and_image_bytes_fail_closed(self):
        missing = valid_blueprint()
        del missing["provenance"]
        with self.assertRaises(LayoutBlueprintValidationError):
            validate_layout_blueprint(missing)

        binary = valid_blueprint()
        binary["provenance"]["image_bytes"] = b"not-allowed"
        with self.assertRaises(LayoutBlueprintValidationError):
            compute_geometry_hash(binary)


if __name__ == "__main__":
    unittest.main()
