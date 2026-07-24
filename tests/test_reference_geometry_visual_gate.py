import unittest

from modules.design_learning.reference_geometry_visual_gate import (
    ReferenceGeometryVisualGate,
)


def valid_draft(**overrides):
    value = {
        "geometry_contract_valid": True,
        "recognized_text": ["장마철 헤어 관리법", "@editorial_handle"],
        "crop_provenance": {
            "source_asset_id": "owner-reference-17",
            "crop_box": {"x": 10, "y": 20, "width": 900, "height": 1100},
            "method": "owner_reference_crop",
        },
        "canvas": {"width": 1080, "height": 1350},
        "text_regions": [
            {
                "role": "headline",
                "text": "장마철 헤어 관리법",
                "box": {"x": 80, "y": 120, "width": 920, "height": 180},
            }
        ],
    }
    value.update(overrides)
    return value


class ReferenceGeometryVisualGateTests(unittest.TestCase):
    def setUp(self):
        self.gate = ReferenceGeometryVisualGate()

    def assertBlocked(self, draft, code):
        result = self.gate.evaluate(draft)
        self.assertEqual(result["status"], "rework_required")
        self.assertNotIn("production_selectable", result)
        self.assertIn(code, [item["code"] for item in result["diagnostics"]])
        return result

    def test_valid_draft_passes_without_production_selection_grant(self):
        result = self.gate.evaluate(valid_draft())
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("production_selectable", result)

    def test_carousel_badge_is_blocked(self):
        self.assertBlocked(
            valid_draft(recognized_text=["2 / 8", "장마철 헤어 관리법"]),
            "carousel_ui_badge_detected",
        )

    def test_explicit_instagram_ui_is_blocked(self):
        self.assertBlocked(
            valid_draft(recognized_text=["@brand", "팔로우", "메시지 보내기"]),
            "instagram_ui_text_detected",
        )

    def test_content_handle_alone_is_diagnostic_not_blocking(self):
        result = self.gate.evaluate(
            valid_draft(recognized_text=["@brand_editorial", "장마철 헤어 관리법"])
        )
        self.assertEqual(result["status"], "pass")
        diagnostics = {item["code"]: item for item in result["diagnostics"]}
        self.assertFalse(diagnostics["content_handle_present_not_blocked"]["blocked"])

    def test_crop_provenance_is_required(self):
        self.assertBlocked(
            valid_draft(crop_provenance=None),
            "crop_provenance_missing_or_incomplete",
        )

    def test_headline_is_required(self):
        self.assertBlocked(
            valid_draft(text_regions=[]),
            "headline_missing",
        )

    def test_multiple_headlines_are_blocked(self):
        draft = valid_draft()
        draft["text_regions"].append(
            {
                "role": "headline",
                "text": "두 번째 제목",
                "box": {"x": 80, "y": 320, "width": 920, "height": 150},
            }
        )
        self.assertBlocked(draft, "headline_multiple")

    def test_long_prompt_paragraph_is_not_a_headline(self):
        prompt = (
            "Prompt: create an image showing a rainy Seoul morning with dramatic "
            "lighting, camera angle from above, composition centered on a model, "
            "style: editorial photography with detailed skin texture and background. "
            "Generate an image that preserves every instruction in this paragraph."
        )
        draft = valid_draft()
        draft["text_regions"][0]["text"] = prompt
        self.assertBlocked(draft, "headline_prompt_paragraph")

    def test_abnormal_headline_box_is_blocked(self):
        draft = valid_draft()
        draft["text_regions"][0]["box"] = {
            "x": 100,
            "y": 1300,
            "width": 40,
            "height": 400,
        }
        self.assertBlocked(draft, "headline_box_abnormal")

    def test_false_geometry_contract_is_blocked(self):
        self.assertBlocked(
            valid_draft(geometry_contract_valid=False),
            "geometry_contract_invalid",
        )


if __name__ == "__main__":
    unittest.main()
