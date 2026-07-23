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

    def test_single_image_news_stays_one_slide(self):
        result = build_selected_candidate_production_plan(
            {"id": "a-single", "account": "A", "category": "국내뉴스", "title": "단신"},
            {
                "status": "completed",
                "summary": "한 장으로 충분한 기사 요약이다.",
                "source_refs": ["https://news.example/single"],
                "assets": [image("single")],
            },
        )
        self.assertEqual(result["status"], "production_plan_ready")
        self.assertEqual(result["slide_count"], 1)

    def test_news_with_one_image_and_multiple_content_units_expands(self):
        result = build_selected_candidate_production_plan(
            {"id": "a-rich", "account": "A", "category": "국내뉴스", "title": "설명이 필요한 뉴스"},
            {
                "status": "completed",
                "summary": "이미지는 한 장이지만 설명할 사실은 여러 개다.",
                "source_refs": ["https://news.example/rich"],
                "assets": [image("single-rich")],
                "key_points": ["첫 번째 핵심", "두 번째 핵심", "세 번째 핵심"],
            },
        )
        self.assertEqual(result["status"], "production_plan_ready")
        self.assertEqual(result["slide_count"], 4)
        self.assertEqual(len(result["slide_plan"]), 4)

    def test_twenty_completed_slides_are_preserved_and_twenty_one_are_blocked(self):
        def bundle(count):
            return {
                "status": "completed",
                "summary": "공식 시즌 자료를 기반으로 구성했다.",
                "source_refs": ["https://brand.example/show"],
                "planned_slides": [
                    {"headline": f"룩 {page}", "body": f"공식 설명 {page}"}
                    for page in range(1, count + 1)
                ],
            }

        candidate = {"id": "c-variable", "account": "C", "category": "패션", "title": "시즌 룩"}
        accepted = build_selected_candidate_production_plan(candidate, bundle(20))
        blocked = build_selected_candidate_production_plan(candidate, bundle(21))

        self.assertEqual(accepted["status"], "production_plan_ready")
        self.assertEqual(accepted["slide_count"], 20)
        self.assertEqual(blocked["reason_code"], "slide_count_out_of_bounds")
        self.assertEqual(blocked["planned_slide_count"], 21)

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

    def test_style_article_expands_by_source_backed_content_units(self):
        result = build_selected_candidate_production_plan(
            {"id": "c-article", "account": "C", "category": "뷰티", "title": "장마철 앞머리"},
            {
                "status": "complete",
                "summary": "습한 날 앞머리 관리법을 정리했다.",
                "source_refs": ["https://beauty.example/article"],
                "key_points": [
                    "헤어핀을 스타일 포인트로 활용한다.",
                    "고정 전 백콤이나 텍스처 스프레이를 가볍게 쓴다.",
                    "오일과 젤은 끝부분에 소량만 사용한다.",
                ],
            },
        )

        self.assertEqual(result["status"], "production_plan_ready")
        self.assertEqual(result["slide_count"], 4)
        self.assertEqual(
            [slide["slide_role"] for slide in result["slide_plan"][1:]],
            ["source_context", "source_context", "source_context"],
        )


if __name__ == "__main__":
    unittest.main()
