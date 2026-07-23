import copy
import unittest

from modules.card_news.reference_blueprint_adapter import ReferenceBlueprintAdapter


def make_blueprint():
    return {
        "reference_id": "reference:owner:202",
        "blueprint_id": "blueprint:owner:202",
        "blueprint_version": 3,
        "geometry_hash": "geometry-202-v3",
        "canvas": {"width": 1080, "height": 1350},
        "regions": [
            {
                "region_id": "photo",
                "role": "primary_media",
                "box_norm": [0.0, 0.0, 1.0, 0.68],
                "z_index": 1,
                "required": True,
            },
            {
                "region_id": "title",
                "role": "headline",
                "box_norm": [0.07, 0.72, 0.86, 0.14],
                "z_index": 2,
                "required": True,
            },
            {
                "region_id": "source",
                "role": "source_label",
                "box_norm": [0.07, 0.92, 0.86, 0.04],
                "z_index": 2,
                "required": True,
            },
        ],
        "style_tokens": {
            "background": "#111111",
            "headline_color": "#FFFFFF",
        },
    }


class ReferenceBlueprintAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = ReferenceBlueprintAdapter()
        self.content = {
            "headline": "원본 구조를 그대로 소비합니다",
            "source_label": "자료: 공식 발표",
        }
        self.media = {
            "primary_media": [
                {
                    "asset_id": "asset-202",
                    "path": "F:/media/asset-202.jpg",
                    "aspect_ratio": 1.2,
                }
            ]
        }

    def test_adapter_preserves_identity_and_geometry_exactly(self):
        blueprint = make_blueprint()
        original = copy.deepcopy(blueprint)

        result = self.adapter.adapt(
            blueprint,
            self.content,
            self.media,
            selection={
                "primary_reference_id": "reference:owner:202",
                "primary_blueprint_id": "blueprint:owner:202",
            },
            fit_result={"fit": True, "outcome": "fit"},
        )

        self.assertEqual("adapted", result["status"])
        self.assertEqual("reference:owner:202", result["primary_reference_id"])
        self.assertEqual("blueprint:owner:202", result["blueprint_id"])
        self.assertEqual(3, result["blueprint_version"])
        self.assertEqual("geometry-202-v3", result["geometry_hash"])
        self.assertEqual(original["regions"], result["regions"])
        self.assertEqual(original, blueprint)
        self.assertFalse(
            result["reference_consumption_receipt"]["geometry_modified"]
        )

    def test_adapter_produces_explicit_content_and_media_bindings(self):
        result = self.adapter.adapt(
            make_blueprint(),
            self.content,
            self.media,
            fit_result={"fit": True, "outcome": "fit"},
        )

        self.assertEqual(
            {"title", "source"},
            {binding["region_id"] for binding in result["content_bindings"]},
        )
        self.assertEqual("photo", result["media_bindings"][0]["region_id"])
        self.assertEqual(
            "asset-202",
            result["media_bindings"][0]["asset"]["asset_id"],
        )

    def test_adapter_blocks_when_fit_did_not_pass(self):
        result = self.adapter.adapt(
            make_blueprint(),
            self.content,
            self.media,
            fit_result={
                "fit": False,
                "outcome": "select_alternative_reference",
            },
        )

        self.assertEqual("blocked", result["status"])
        self.assertIn(
            "content_fit_not_passed",
            {error["code"] for error in result["errors"]},
        )

    def test_adapter_never_invents_missing_geometry(self):
        blueprint = make_blueprint()
        blueprint["regions"][0].pop("box_norm")

        result = self.adapter.adapt(
            blueprint,
            self.content,
            self.media,
            fit_result={"fit": True, "outcome": "fit"},
        )

        self.assertEqual("blocked", result["status"])
        self.assertNotIn("box_norm", result["regions"][0])
        self.assertIn(
            "invalid_geometry",
            {error["code"] for error in result["errors"]},
        )

    def test_adapter_blocks_reference_identity_mismatch(self):
        result = self.adapter.adapt(
            make_blueprint(),
            self.content,
            self.media,
            selection={
                "primary_reference_id": "reference:owner:other",
                "primary_blueprint_id": "blueprint:owner:202",
            },
            fit_result={"fit": True, "outcome": "fit"},
        )

        self.assertEqual("blocked", result["status"])
        self.assertIn(
            "reference_identity_mismatch",
            {error["code"] for error in result["errors"]},
        )

    def test_adapter_blocks_missing_required_binding(self):
        result = self.adapter.adapt(
            make_blueprint(),
            {"headline": self.content["headline"]},
            self.media,
            fit_result={"fit": True, "outcome": "fit"},
        )

        self.assertEqual("blocked", result["status"])
        self.assertIn(
            "missing_required_content_binding",
            {error["code"] for error in result["errors"]},
        )


if __name__ == "__main__":
    unittest.main()
