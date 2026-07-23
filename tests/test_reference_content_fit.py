import unittest

from modules.card_news.reference_content_fit import (
    FIT_OUTCOMES,
    ReferenceContentFitChecker,
)


def make_blueprint():
    return {
        "reference_id": "reference:owner:101",
        "blueprint_id": "blueprint:owner:101",
        "blueprint_version": 1,
        "geometry_hash": "geometry-101",
        "canvas": {
            "width": 1080,
            "height": 1350,
            "mobile_safe_area_norm": [0.04, 0.04, 0.04, 0.04],
        },
        "slide_role_fit": ["hook"],
        "regions": [
            {
                "region_id": "media",
                "role": "primary_media",
                "box_norm": [0.04, 0.04, 0.92, 0.56],
                "required": True,
            },
            {
                "region_id": "title",
                "role": "headline",
                "box_norm": [0.08, 0.64, 0.84, 0.16],
                "required": True,
                "max_lines": 2,
            },
            {
                "region_id": "body",
                "role": "body",
                "box_norm": [0.08, 0.81, 0.84, 0.10],
                "required": False,
            },
            {
                "region_id": "source",
                "role": "source_label",
                "box_norm": [0.08, 0.92, 0.84, 0.04],
                "required": True,
            },
        ],
        "media_requirements": {
            "primary_media": {
                "min_count": 1,
                "max_count": 1,
                "aspect_ratio": 1.314286,
                "aspect_tolerance": 0.1,
            }
        },
        "fit_constraints": {
            "source_label_required": True,
            "headline": {
                "max_chars": 24,
                "max_lines": 2,
                "chars_per_line": 12,
                "reduction_limit": 1.25,
            },
            "body": {
                "max_chars": 80,
                "max_lines": 4,
                "chars_per_line": 20,
                "reduction_limit": 1.25,
            },
        },
    }


class ReferenceContentFitCheckerTests(unittest.TestCase):
    def setUp(self):
        self.checker = ReferenceContentFitChecker()
        self.content = {
            "headline": "지금 확인해야 할 핵심 변화",
            "body": "출처가 확인된 핵심 내용입니다.",
            "source_label": "자료: 공식 발표",
        }
        self.media = {
            "primary_media": [
                {
                    "asset_id": "asset-1",
                    "aspect_ratio": 1.314286,
                    "crop_allowed": False,
                }
            ]
        }

    def test_fit_returns_identity_and_all_contract_checks(self):
        result = self.checker.evaluate(
            make_blueprint(),
            self.content,
            self.media,
            slide_role="hook",
        )

        self.assertEqual("fit", result["outcome"])
        self.assertTrue(result["fit"])
        self.assertEqual("reference:owner:101", result["reference_id"])
        self.assertEqual("geometry-101", result["geometry_hash"])
        self.assertTrue(all(check["passed"] for check in result["checks"]))

    def test_invalid_normalized_geometry_is_blocked_not_repaired(self):
        blueprint = make_blueprint()
        blueprint["regions"][0]["box_norm"] = [0.7, 0.04, 0.6, 0.5]

        result = self.checker.evaluate(blueprint, self.content, self.media)

        self.assertEqual("blocked", result["outcome"])
        self.assertIn(
            "invalid_geometry",
            {reason["code"] for reason in result["reasons"]},
        )
        self.assertEqual([0.7, 0.04, 0.6, 0.5], blueprint["regions"][0]["box_norm"])

    def test_missing_required_source_label_is_blocked(self):
        content = dict(self.content)
        content.pop("source_label")

        result = self.checker.evaluate(make_blueprint(), content, self.media)

        self.assertEqual("blocked", result["outcome"])
        self.assertIn(
            "source_label_missing",
            {reason["code"] for reason in result["reasons"]},
        )

    def test_media_aspect_mismatch_selects_alternative_reference(self):
        media = {
            "primary_media": [
                {
                    "asset_id": "asset-wide",
                    "aspect_ratio": 2.0,
                    "crop_allowed": False,
                }
            ]
        }

        result = self.checker.evaluate(make_blueprint(), self.content, media)

        self.assertEqual("select_alternative_reference", result["outcome"])

    def test_moderate_copy_overflow_requests_copy_reduction(self):
        content = dict(self.content)
        content["headline"] = "가" * 28

        result = self.checker.evaluate(make_blueprint(), content, self.media)

        self.assertEqual("reduce_nonessential_copy", result["outcome"])

    def test_large_body_overflow_requests_an_additional_slide(self):
        content = dict(self.content)
        content["body"] = "나" * 130

        result = self.checker.evaluate(make_blueprint(), content, self.media)

        self.assertEqual("split_content_into_additional_slide", result["outcome"])

    def test_slide_role_mismatch_selects_alternative_reference(self):
        result = self.checker.evaluate(
            make_blueprint(),
            self.content,
            self.media,
            slide_role="quote",
        )

        self.assertEqual("select_alternative_reference", result["outcome"])

    def test_supported_outcomes_are_exactly_the_v2_contract(self):
        self.assertEqual(
            (
                "fit",
                "select_alternative_reference",
                "split_content_into_additional_slide",
                "reduce_nonessential_copy",
                "blocked",
            ),
            FIT_OUTCOMES,
        )


if __name__ == "__main__":
    unittest.main()
