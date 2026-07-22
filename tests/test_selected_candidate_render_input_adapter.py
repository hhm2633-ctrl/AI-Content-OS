import unittest

from modules.card_news.selected_candidate_render_input_adapter import (
    build_selected_candidate_render_inputs,
)


def plan(slide_count=4, *, media_type="image"):
    slides = []
    assets = []
    for page in range(1, slide_count + 1):
        asset_id = f"asset-{page}"
        slides.append(
            {
                "slide_role": "cover" if page == 1 else "source_context",
                "media_type": media_type,
                "asset_refs": [asset_id],
                "copy_source": "deep_discovery_bundle",
            }
        )
        assets.append(
            {
                "asset_id": asset_id,
                "media_type": "image",
                "origin": "official",
                "asset_class": "source_evidence",
                "locator": f"C:/approved/asset-{page}.jpg",
            }
        )
    return {
        "schema_version": "selected_candidate_production_plan_v1",
        "status": "production_plan_ready",
        "candidate_id": "candidate-1",
        "account": "C",
        "title": "선정된 주제",
        "slide_plan": slides,
        "motion_plan": [],
        "copy_plan": {
            "feed_body": "피드 본문",
            "source_credit": ["https://official.example/source"],
        },
        "commerce": {"mode": "none", "required_for_readiness": False},
        "asset_inventory": assets,
    }


def resolved_copy(count):
    return [
        {"headline": f"제목 {page}", "body": f"본문 {page}"}
        for page in range(1, count + 1)
    ]


class SelectedCandidateRenderInputAdapterTests(unittest.TestCase):
    def test_malformed_and_blocked_plan_fail_safely(self):
        self.assertEqual(
            build_selected_candidate_render_inputs(None)["reason_code"],
            "malformed_production_plan",
        )
        value = plan()
        value["status"] = "blocked"
        self.assertEqual(
            build_selected_candidate_render_inputs(value)["reason_code"],
            "production_plan_not_ready",
        )

    def test_variable_plan_is_preserved_into_renderer_contract(self):
        value = plan(7)
        result = build_selected_candidate_render_inputs(value, resolved_copy(7))
        self.assertEqual(result["status"], "renderer_input_ready")
        self.assertTrue(result["renderer_ready"])
        self.assertEqual(len(result["current_renderer_input"]["content_result"]["slides"]), 7)
        self.assertEqual(len(result["current_renderer_input"]["image_generation_result"]["images"]), 7)
        self.assertFalse(result["current_renderer_input"]["image_strategy_result"]["need_ai_image"])
        self.assertFalse(result["render_executed"])

    def test_one_slide_news_is_preserved(self):
        result = build_selected_candidate_render_inputs(plan(1), resolved_copy(1))
        self.assertEqual(result["status"], "renderer_input_ready")
        self.assertEqual(len(result["current_renderer_input"]["content_result"]["slides"]), 1)

    def test_slide_count_over_limit_is_blocked(self):
        value = plan(21)
        result = build_selected_candidate_render_inputs(value, resolved_copy(21))
        self.assertEqual(result["reason_code"], "current_renderer_slide_count")
        self.assertEqual(result["planned_slide_count"], 21)
        self.assertFalse(result["renderer_ready"])

    def test_four_static_slides_build_current_renderer_inputs_and_sidecars(self):
        value = plan(4)
        value["motion_plan"] = [{"motion_id": "future-motion"}]
        result = build_selected_candidate_render_inputs(value, resolved_copy(4))
        self.assertEqual(result["status"], "renderer_input_ready")
        self.assertTrue(result["renderer_ready"])
        renderer = result["current_renderer_input"]
        self.assertEqual(len(renderer["content_result"]["slides"]), 4)
        self.assertEqual(len(renderer["image_generation_result"]["images"]), 4)
        self.assertFalse(renderer["image_generation_result"]["generated"])
        self.assertFalse(renderer["image_strategy_result"]["need_ai_image"])
        self.assertEqual(result["sidecars"]["motion_plan"][0]["motion_id"], "future-motion")
        self.assertEqual(
            result["sidecars"]["source_refs"],
            ["https://official.example/source"],
        )
        self.assertFalse(result["render_executed"])

    def test_video_slide_blocks_legacy_renderer_without_losing_plan(self):
        value = plan(4)
        value["slide_plan"][2]["media_type"] = "video"
        value["slide_plan"][2]["motion_ref"] = "motion-1"
        result = build_selected_candidate_render_inputs(value, resolved_copy(4))
        self.assertEqual(result["reason_code"], "current_renderer_media_limit")
        self.assertEqual(result["unsupported_slide_pages"], [3])
        self.assertEqual(result["required_renderer"], "variable_length_hybrid_renderer")

    def test_generated_source_evidence_is_blocked(self):
        value = plan(4)
        value["asset_inventory"][0]["origin"] = "generated"
        result = build_selected_candidate_render_inputs(value, resolved_copy(4))
        self.assertEqual(result["reason_code"], "generated_source_evidence_blocked")
        self.assertEqual(result["blocked_asset_ids"], ["asset-1"])

    def test_missing_resolved_copy_is_explicit(self):
        result = build_selected_candidate_render_inputs(plan(4), resolved_copy(3))
        self.assertEqual(result["reason_code"], "resolved_copy_missing")
        self.assertEqual(result["missing_copy_pages"], [4])


if __name__ == "__main__":
    unittest.main()
