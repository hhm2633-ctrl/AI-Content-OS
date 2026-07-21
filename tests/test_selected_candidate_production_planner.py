import unittest

from modules.card_news.selected_candidate_production_planner import (
    build_selected_candidate_production_plan,
)


def image(asset_id, *, origin="news", gallery=False):
    return {
        "asset_id": asset_id,
        "media_type": "image",
        "origin": origin,
        "asset_class": "source_evidence",
        "source_url": f"https://example.com/{asset_id}.jpg",
        "product_gallery": gallery,
    }


class SelectedCandidateProductionPlannerTests(unittest.TestCase):
    def test_blocks_malformed_and_incomplete_inputs(self):
        self.assertEqual(
            build_selected_candidate_production_plan(None, None)["reason_code"],
            "malformed_candidate",
        )
        result = build_selected_candidate_production_plan(
            {"id": "a1", "account": "A", "title": "뉴스"},
            {"status": "waiting"},
        )
        self.assertEqual(result["reason_code"], "deep_dive_not_complete")

    def test_news_is_asset_driven_without_forced_timeline_grammar(self):
        result = build_selected_candidate_production_plan(
            {"id": "a1", "account": "A", "category": "국내뉴스", "title": "현장 뉴스"},
            {
                "status": "completed",
                "summary": "공개된 기사 내용을 짧게 정리했다.",
                "source_refs": ["https://news.example/article"],
                "assets": [image("lead"), image("scene")],
            },
        )
        self.assertEqual(result["status"], "production_plan_ready")
        self.assertEqual(result["slide_count"], 2)
        self.assertNotIn(
            "timeline",
            {slide["slide_role"] for slide in result["slide_plan"]},
        )
        self.assertFalse(result["render_executed"])

    def test_story_uses_emotion_arc_and_real_comments_only(self):
        result = build_selected_candidate_production_plan(
            {"id": "b1", "account": "B", "title": "연애 갈등"},
            {
                "status": "complete",
                "summary": "원문에서 확인된 갈등 이야기다.",
                "source_refs": ["https://community.example/post"],
                "reconstruction_scenes": [
                    {"scene_id": "s1"},
                    {"scene_id": "s2"},
                    {"scene_id": "s3"},
                ],
                "comments": [
                    {"comment_id": "real", "text": "이건 좀 이상하다", "is_real_comment": True},
                    {"comment_id": "fake", "text": "AI가 쓴 말", "is_real_comment": False},
                ],
            },
        )
        scene_slides = [s for s in result["slide_plan"] if s["slide_role"] == "story_scene"]
        self.assertEqual([s["emotion_stage"] for s in scene_slides], ["관심", "의심", "결심"])
        self.assertEqual(result["real_comment_count"], 1)
        self.assertEqual(
            len([s for s in result["slide_plan"] if s["slide_role"] == "real_comment"]),
            1,
        )

    def test_style_product_gallery_becomes_one_motion_role(self):
        assets = [
            image("product-cover", origin="official"),
            image("gallery-1", origin="official", gallery=True),
            image("gallery-2", origin="official", gallery=True),
            image("gallery-3", origin="official", gallery=True),
        ]
        result = build_selected_candidate_production_plan(
            {"id": "c1", "account": "C", "category": "뷰티", "title": "새 향수"},
            {
                "status": "complete",
                "summary": "공식 제품 이미지와 향 노트를 정리했다.",
                "source_refs": ["https://brand.example/product"],
                "assets": assets,
            },
            {"status": "matched", "fit": "natural", "product_id": "p1"},
        )
        self.assertEqual(len(result["motion_plan"]), 1)
        self.assertEqual(result["motion_plan"][0]["motion_type"], "source_image_montage")
        self.assertEqual(
            len([s for s in result["slide_plan"] if s["slide_role"] == "product_gallery_motion"]),
            1,
        )
        self.assertEqual(result["commerce"]["mode"], "optional_match")
        self.assertFalse(result["commerce"]["required_for_readiness"])

    def test_runway_editorial_is_ready_without_commerce(self):
        result = build_selected_candidate_production_plan(
            {"id": "c2", "account": "C", "category": "패션", "title": "시즌 런웨이"},
            {
                "status": "complete",
                "content_type": "runway",
                "summary": "공식 시즌 콘셉트를 대표 룩으로 설명한다.",
                "source_refs": ["https://brand.example/show"],
                "assets": [image("look-1", origin="official")],
            },
        )
        self.assertEqual(result["status"], "production_plan_ready")
        self.assertEqual(result["commerce"]["mode"], "not_applicable")
        self.assertFalse(result["commerce"]["required_for_readiness"])


if __name__ == "__main__":
    unittest.main()
