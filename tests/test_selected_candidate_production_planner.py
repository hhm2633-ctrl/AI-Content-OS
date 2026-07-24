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

    def test_news_with_one_image_keeps_details_in_feed_caption(self):
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
        self.assertEqual(result["slide_count"], 1)
        self.assertEqual(len(result["slide_plan"]), 1)
        self.assertEqual(
            ["첫 번째 핵심", "두 번째 핵심", "세 번째 핵심"],
            result["copy_plan"]["key_points"],
        )

    def test_simple_agreement_news_keeps_one_visual_and_caption_details(self):
        title = "기업과 지자체, 2600억원 투자협약 체결"
        result = build_selected_candidate_production_plan(
            {
                "id": "agreement-news",
                "account": "A",
                "category": "경제",
                "title": title,
            },
            {
                "status": "completed",
                "summary": "한 기업의 지역 투자협약 내용을 정리했다.",
                "source_refs": ["https://news.example/agreement"],
                "assets": [image("agreement")],
                "key_points": [
                    "기업과 지자체가 2600억원 규모 투자협약을 체결했다.",
                    "이번 협약의 투자 규모는 총 2600억원이다.",
                    "기업은 지역 산업단지에 생산시설을 증설한다.",
                    "생산시설 증설은 단계적으로 진행된다.",
                    "투자가 완료되면 신규 고용이 늘어날 전망이다.",
                    "지자체는 인허가와 기반시설을 지원한다.",
                    "사업은 관련 절차를 거쳐 순차적으로 추진할 예정이다.",
                    "협약은 지역 산업 경쟁력 강화가 목표다.",
                ],
            },
        )

        self.assertEqual("production_plan_ready", result["status"])
        self.assertEqual(result["slide_count"], 1)
        self.assertEqual("cover", result["slide_plan"][0]["slide_role"])
        self.assertGreater(len(result["copy_plan"]["key_points"]), 0)

    def test_real_single_investment_agreement_uses_one_visual(self):
        key_points = [
            "구미시는 월덱스의 대규모 투자를 유치하며 반도체 특화단지 입지를 강화했습니다.",
            "세 기관은 시청에서 반도체 공정 부품 생산시설 증설을 위한 양해각서를 체결했습니다.",
            "월덱스는 구미국가5산업단지에 실리콘 파츠 등 핵심 부품 생산공장을 신설할 계획입니다.",
            "이번 투자 과정에서 370명 이상의 신규 고용이 창출될 전망입니다.",
            "월덱스는 공급망 안정과 글로벌 수요 대응을 위해 구미 재투자를 결정했습니다.",
            "기존 사업장 인프라와 구미시의 신속한 인허가 지원이 투자 결정에 영향을 줬습니다.",
            "김장호 시장은 안정적인 성장을 위한 행정·재정 지원을 이어가겠다고 밝혔습니다.",
        ]
        result = build_selected_candidate_production_plan(
            {
                "id": "single-investment-agreement",
                "account": "A",
                "category": "경제",
                "title": "구미에 2600억원 반도체 투자",
            },
            {
                "status": "completed",
                "summary": "단일 기업의 생산시설 증설 투자협약이다.",
                "source_refs": ["https://news.example/investment-agreement"],
                "assets": [image("investment-agreement")],
                "key_points": key_points,
            },
        )

        self.assertEqual("production_plan_ready", result["status"])
        self.assertEqual(1, result["slide_count"])
        self.assertEqual(
            "구미에 2600억원 반도체 투자",
            result["title"],
        )
        self.assertEqual(5, len(result["copy_plan"]["key_points"]))
        self.assertTrue(
            any(
                "양해각서" in point
                for point in result["copy_plan"]["key_points"]
            )
        )
        self.assertTrue(
            any("370명" in point for point in result["copy_plan"]["key_points"])
        )
        self.assertEqual(
            1,
            sum(
                any(marker in point for marker in ("입지", "공급망", "인프라"))
                for point in result["copy_plan"]["key_points"]
            ),
        )

    def test_news_with_many_evidence_types_does_not_create_text_only_slides(self):
        key_points = [
            "감사 결과에서 첫 번째 수치가 전년 대비 12% 증가했다.",
            "두 번째 지표는 지난해보다 9% 감소한 것으로 확인됐다.",
            "책임자는 첫 번째 개선 계획을 다음 달 시작한다고 밝혔다.",
            "현장 관계자는 별도 지원책이 필요하다고 말했다.",
            "기관은 후속 점검을 오는 9월 추진할 예정이다.",
            "세 지역의 결과를 비교하면 격차가 각각 다르게 나타났다.",
            "추가 예산안은 다음 회의에서 심의할 계획이다.",
        ]
        result = build_selected_candidate_production_plan(
            {"id": "evidence-rich", "account": "A", "title": "감사 결과 발표"},
            {
                "status": "completed",
                "summary": "독립된 수치와 발언, 후속 조치가 함께 공개됐다.",
                "source_refs": ["https://news.example/audit"],
                "assets": [image("audit")],
                "key_points": key_points,
            },
        )

        self.assertEqual("production_plan_ready", result["status"])
        self.assertEqual(result["slide_count"], 1)
        self.assertEqual(len(key_points), len(result["copy_plan"]["key_points"]))

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

    def test_long_real_comment_is_excerpted_but_full_source_is_preserved(self):
        original = ("이 문장은 실제 댓글 원문입니다. " * 20).strip()
        result = build_selected_candidate_production_plan(
            {"id": "b-long", "account": "B", "title": "후기"},
            {
                "status": "complete",
                "summary": "원문 후기",
                "source_refs": ["https://community.example/post"],
                "assets": [image("story-source", origin="current_source")],
                "comments": [
                    {
                        "comment_id": "real-long",
                        "text": original,
                        "is_real_comment": True,
                        "identity_masked": True,
                    }
                ],
            },
        )
        comment_slide = next(
            slide for slide in result["slide_plan"] if slide["slide_role"] == "real_comment"
        )
        self.assertLessEqual(len(comment_slide["body"]), 171)
        self.assertEqual(comment_slide["source_comment_text"], original)

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
