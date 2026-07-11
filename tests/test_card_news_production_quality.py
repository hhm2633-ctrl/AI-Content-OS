import re
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.card_news import render_constants as RC
from modules.card_news.card_news_module import CardNewsModule
from modules.card_news.card_news_quality_checker import CardNewsQualityChecker
from modules.card_news.card_news_text_optimizer import CardNewsTextOptimizer
from modules.card_news.debate_question_selector import DebateQuestionSelector
from modules.card_news.evidence_selector import EvidenceSelector
from modules.card_news.mobile_readability_checker import MobileReadabilityChecker
from modules.card_news.social_proof_selector import SocialProofSelector
from modules.card_news.story_flow_planner import StoryFlowPlanner
from modules.card_news.typography_rules import resolve_typography_role
from modules.card_news.visual_rhythm_selector import VisualRhythmSelector


# ---- A. Evidence ----------------------------------------------------------

class TestEvidenceSelectorGuards(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="evidence_selector_test_"))
        self.screenshot_path = self.tmp_dir / "shot.png"
        Image.new("RGB", (10, 10)).save(self.screenshot_path)
        self.selector = EvidenceSelector({})

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _select_with(self, research_result, posts):
        self.selector._load_research_result = lambda: research_result
        self.selector._load_posts = lambda: posts
        return self.selector.select({}, [])

    def test_file_exists_but_topic_irrelevant_not_applied(self):
        research_result = {
            "keyword": "부동산 청약 규제", "title": "부동산 정책 발표", "key_points": ["청약 자격 강화"],
        }
        posts = [{
            "screenshot_path": str(self.screenshot_path),
            "caption_text": "오늘 점심 메뉴 추천 파스타 맛집",
            "hashtags": ["맛집", "파스타"],
            "account_handle": "food_acc",
        }]
        result = self._select_with(research_result, posts)
        asset = result["evidence_assets"][0]
        self.assertTrue(asset["candidate_found"])
        self.assertFalse(asset["topic_relevant"])
        self.assertFalse(asset["available"])
        self.assertEqual(asset["selection_status"], "rejected_irrelevant")

    def test_competitor_reference_never_becomes_topic_evidence(self):
        research_result = {
            "keyword": "부동산 청약 규제", "title": "부동산 정책 발표", "key_points": ["청약 자격 강화"],
        }
        posts = [{
            "screenshot_path": str(self.screenshot_path),
            "caption_text": "부동산 청약 규제 정책 발표 청약 자격 강화 논란",
            "hashtags": ["부동산", "청약"],
            "account_handle": "news_acc",
        }]
        result = self._select_with(research_result, posts)
        asset = result["evidence_assets"][0]
        self.assertTrue(asset["topic_relevant"])
        self.assertEqual(asset["asset_role"], "competitor_reference")
        self.assertFalse(asset["available"])
        self.assertEqual(asset["selection_status"], "rejected_competitor_reference")

    def test_render_allowed_only_for_allowed_copyright_statuses(self):
        for status in EvidenceSelector.RENDER_BLOCKED_COPYRIGHT_STATUSES:
            self.assertNotIn(status, EvidenceSelector.RENDER_ALLOWED_COPYRIGHT_STATUSES)

        research_result = {"keyword": "부동산 청약 규제"}
        posts = [{
            "screenshot_path": str(self.screenshot_path),
            "caption_text": "부동산 청약 규제",
            "hashtags": [],
            "account_handle": "a",
        }]
        result = self._select_with(research_result, posts)
        asset = result["evidence_assets"][0]
        self.assertIn(asset["copyright_status"], EvidenceSelector.RENDER_BLOCKED_COPYRIGHT_STATUSES)
        self.assertFalse(asset["render_allowed"])


class TestCardNewsModuleEvidenceGuards(unittest.TestCase):
    def setUp(self):
        self.module = CardNewsModule({})

    def test_apply_evidence_asset_blocks_unlicensed(self):
        evidence_result = {
            "top_evidence_asset": {
                "available": True, "asset_role": "topic_evidence", "render_allowed": False,
                "candidate_found": True, "asset_path": "nonexistent.png",
            }
        }
        story_flow_result = {"applied_roles": [{"page": 3, "role": "solution", "narrative_role": "evidence"}]}
        paths, applied = self.module._apply_evidence_asset(
            [None, None, None, None], evidence_result, story_flow_result
        )
        self.assertFalse(applied)

    def test_apply_evidence_asset_blocks_competitor_reference(self):
        evidence_result = {
            "top_evidence_asset": {
                "available": True, "asset_role": "competitor_reference", "render_allowed": True,
                "candidate_found": True, "asset_path": "nonexistent.png",
            }
        }
        story_flow_result = {"applied_roles": [{"page": 3, "role": "solution", "narrative_role": "evidence"}]}
        paths, applied = self.module._apply_evidence_asset(
            [None, None, None, None], evidence_result, story_flow_result
        )
        self.assertFalse(applied)

    def test_attribution_hidden_when_not_render_allowed(self):
        evidence_result = {
            "top_evidence_asset": {
                "render_allowed": False, "applied": True, "source_name": "acc", "asset_type": "social_screenshot",
            }
        }
        story_flow_result = {"applied_roles": [{"page": 3, "narrative_role": "evidence"}]}
        attribution = self.module._build_attribution_by_page(evidence_result, story_flow_result, evidence_applied=True)
        self.assertEqual(attribution, {})

    def test_attribution_shown_only_for_actually_applied_asset(self):
        evidence_result = {
            "top_evidence_asset": {
                "render_allowed": True, "applied": True, "source_name": "acc_handle", "asset_type": "social_screenshot",
            }
        }
        story_flow_result = {"applied_roles": [{"page": 3, "narrative_role": "evidence"}]}
        attribution = self.module._build_attribution_by_page(evidence_result, story_flow_result, evidence_applied=True)
        self.assertIn(3, attribution)
        self.assertEqual(attribution[3]["source_name"], "acc_handle")


# ---- B. Social Proof --------------------------------------------------------

class TestSocialProofSelectorGuards(unittest.TestCase):
    def setUp(self):
        self.selector = SocialProofSelector({})

    def test_no_real_comment_text_available_false(self):
        self.selector._load_posts = lambda: [{"caption_text": "오늘 점심 맛집", "visible_comment_text": "댓글 12개"}]
        self.selector._load_json = lambda path, default: default
        result = self.selector.select()
        self.assertFalse(result["available"])
        self.assertEqual(result["candidate_count"], 0)

    def test_caption_and_visible_counts_excluded_from_real_text_fields(self):
        self.assertNotIn("caption_text", SocialProofSelector.REAL_TEXT_FIELDS)
        self.assertNotIn("visible_comment_text", SocialProofSelector.REAL_TEXT_FIELDS)
        self.assertNotIn("visible_like_text", SocialProofSelector.REAL_TEXT_FIELDS)
        self.assertNotIn("visible_repost_text", SocialProofSelector.REAL_TEXT_FIELDS)

    def test_account_handle_masking_contract(self):
        masked = self.selector._mask_account_handle("longhandle123")
        self.assertTrue(masked.startswith("lo"))
        self.assertTrue(masked.endswith("3"))
        self.assertIn("*", masked)

    def test_pii_scrub_masks_email_and_phone_without_changing_rest(self):
        text = "연락처는 test@example.com 이고 010-1234-5678 입니다 정말 좋아요"
        scrubbed = self.selector._scrub_sensitive_info(text)
        self.assertNotIn("test@example.com", scrubbed)
        self.assertNotIn("010-1234-5678", scrubbed)
        self.assertIn("정말 좋아요", scrubbed)

    def test_selected_items_labeled_as_opinion_with_masked_handle(self):
        self.selector._load_posts = lambda: [{
            "comment_text": "완전 제 얘기 같아요 공감됩니다",
            "account_handle": "user_handle_1",
            "post_url": "https://example.com/p/1",
            "visible_like_text": "100",
            "visible_comment_text": "5",
        }]
        self.selector._load_json = lambda path, default: default
        result = self.selector.select()
        self.assertTrue(result["available"])
        item = result["selected"][0]
        self.assertTrue(item["is_opinion"])
        self.assertEqual(item["label"], "커뮤니티 반응")
        self.assertNotEqual(item["masked_account_handle"], item["account_handle"])


class TestSocialProofRenderGuard(unittest.TestCase):
    def test_apply_social_proof_only_appends_text_and_preserves_original_cta(self):
        module = CardNewsModule({})
        slides = [
            {"page": 1, "role": "hook", "headline": "h", "body": "b"},
            {"page": 4, "role": "cta", "headline": "h4", "body": "기존 CTA 문구"},
        ]
        social_proof_result = {"selected": [{
            "text": "정말 공감돼요", "masked_account_handle": "us***1", "label": "커뮤니티 반응",
        }]}
        story_flow_result = {"applied_roles": [{"page": 4, "narrative_role": "social_proof"}]}
        updated_slides, applied = module._apply_social_proof_quote(slides, social_proof_result, story_flow_result)

        self.assertTrue(applied)
        body = updated_slides[1]["body"]
        self.assertIn("[커뮤니티 반응]", body)
        self.assertIn("정말 공감돼요", body)
        self.assertIn("기존 CTA 문구", body)
        self.assertNotIn("image_path", updated_slides[1])
        self.assertNotIn("screenshot_path", updated_slides[1])


# ---- C. Story / Debate -----------------------------------------------------

class TestStoryFlowGuards(unittest.TestCase):
    def test_applied_roles_never_exceed_slide_count(self):
        planner = StoryFlowPlanner({})
        slides = [{"page": 1, "role": "hook"}, {"page": 2, "role": "problem"}]
        result = planner.plan(slides, evidence_available=True, social_proof_available=True, debate_will_apply=True)
        self.assertLessEqual(len(result["applied_roles"]), len(slides))


class TestDebateQuestionSelectionGuards(unittest.TestCase):
    def setUp(self):
        self.selector = DebateQuestionSelector({})

    def test_comment_cta_skips_debate(self):
        result = self.selector.select("story", "comment")
        self.assertFalse(result["should_apply"])

    def test_non_comment_cta_allows_debate(self):
        result = self.selector.select("story", "save")
        self.assertTrue(result["should_apply"])


class TestDebateApplyGuards(unittest.TestCase):
    def test_over_budget_debate_not_applied_and_cta_preserved(self):
        module = CardNewsModule({})
        long_body = "가" * 100
        slides = [{"page": 4, "role": "cta", "headline": "h", "body": long_body}]
        debate_result = {"should_apply": True, "question": "여러분 생각은 어떠세요?"}
        updated_slides, final_debate = module._apply_debate_question(slides, debate_result)
        self.assertFalse(final_debate["applied"])
        self.assertEqual(updated_slides[0]["body"], long_body)

    def test_within_budget_debate_appends_without_replacing_cta(self):
        module = CardNewsModule({})
        slides = [{"page": 4, "role": "cta", "headline": "h", "body": "저장하세요"}]
        debate_result = {"should_apply": True, "question": "여러분 생각은?"}
        updated_slides, final_debate = module._apply_debate_question(slides, debate_result)
        self.assertTrue(final_debate["applied"])
        self.assertIn("저장하세요", updated_slides[0]["body"])
        self.assertIn("여러분 생각은?", updated_slides[0]["body"])


# ---- D. Typography / Renderer ---------------------------------------------

class TestFitLinesGuards(unittest.TestCase):
    def test_fit_lines_never_drops_content_when_hard_max_lines_allows(self):
        module = CardNewsModule({})
        text = "문장이 여러 개 있어도 필요한 만큼만 남기고 정리합니다. 두 번째 문장은 제거될 수도 있습니다."
        lines, _font_size = module._fit_lines(
            text, font_size_range=(32, 39), max_lines=1, max_width=800, bold=False, hard_max_lines=4,
        )
        joined = "".join(lines).replace(" ", "")
        self.assertIn("남기고정리합니다", joined)


class TestCoverOptimizationGuard(unittest.TestCase):
    def test_cover_body_capped_to_one_sentence(self):
        optimizer = CardNewsTextOptimizer({})
        slides = [{
            "page": 1, "role": "hook", "headline": "제목",
            "body": "첫 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다.",
        }]
        result = optimizer.optimize(slides)
        self.assertTrue(result["cover_optimized"])
        body = result["slides"][0]["body"]
        sentence_count = len([s for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()])
        self.assertLessEqual(sentence_count, 1)


class TestTypographyRoleResolutionGuards(unittest.TestCase):
    def test_cover_headline_uses_cover_title_role(self):
        self.assertEqual(resolve_typography_role("hook", "cover", True), "cover_title")

    def test_cta_body_uses_cta_role(self):
        self.assertEqual(resolve_typography_role("cta", "debate_cta", False), "cta")


class TestVisualRhythmApplicationGuards(unittest.TestCase):
    def setUp(self):
        self.module = CardNewsModule({})

    def test_quote_card_falls_back_without_real_social_proof(self):
        visual_rhythm_result = {
            "assignments": [{"page": 4, "role": "cta", "narrative_role": "social_proof", "visual_style": "quote_card"}]
        }
        story_flow_result = {"applied_roles": [{"page": 4, "narrative_role": "social_proof"}]}
        resolved = self.module._resolve_visual_rhythm_application(
            visual_rhythm_result, [None, None, None, None],
            evidence_applied=False, social_proof_applied=False, story_flow_result=story_flow_result,
        )
        self.assertEqual(resolved[4]["applied_style"], VisualRhythmSelector.DEFAULT_STYLE)
        self.assertTrue(resolved[4]["fallback_used"])

    def test_comparison_always_falls_back(self):
        visual_rhythm_result = {
            "assignments": [{"page": 2, "role": "problem", "narrative_role": "counterpoint", "visual_style": "comparison"}]
        }
        resolved = self.module._resolve_visual_rhythm_application(
            visual_rhythm_result, [None, None, None, None],
            evidence_applied=False, social_proof_applied=False, story_flow_result={},
        )
        self.assertEqual(resolved[2]["applied_style"], VisualRhythmSelector.DEFAULT_STYLE)
        self.assertTrue(resolved[2]["fallback_used"])

    def test_quote_card_applied_when_real_social_proof_present(self):
        visual_rhythm_result = {
            "assignments": [{"page": 4, "role": "cta", "narrative_role": "social_proof", "visual_style": "quote_card"}]
        }
        story_flow_result = {"applied_roles": [{"page": 4, "narrative_role": "social_proof"}]}
        resolved = self.module._resolve_visual_rhythm_application(
            visual_rhythm_result, [None, None, None, None],
            evidence_applied=False, social_proof_applied=True, story_flow_result=story_flow_result,
        )
        self.assertEqual(resolved[4]["applied_style"], "quote_card")
        self.assertFalse(resolved[4]["fallback_used"])


class TestRendererSafeFallbackGuard(unittest.TestCase):
    def test_create_card_falls_back_when_layout_aware_path_raises(self):
        module = CardNewsModule({})
        tmp_dir = Path(tempfile.mkdtemp(prefix="card_news_render_test_"))
        try:
            module.card_dir = tmp_dir
            slide = {"page": 1, "role": "hook", "headline": "제목", "body": "본문"}
            # layout_context가 dict가 아니면(list) layout-aware 경로(.get 호출)에서
            # 예외가 나야 정상이다 - 기존 안전 fallback이 여전히 동작하는지 확인.
            broken_layout_context = ["not", "a", "dict"]
            card_path, used_layout = module._create_card(
                page_number=1, title="타이틀", slide=slide, image_path=None,
                layout_context=broken_layout_context,
            )
            self.assertFalse(used_layout)
            self.assertTrue(Path(card_path).exists())
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ---- E. Mobile / Contrast ---------------------------------------------------

class TestSharedRenderConstantsGuards(unittest.TestCase):
    def test_checker_and_module_share_same_constants_object(self):
        self.assertIs(MobileReadabilityChecker.PALETTE_COMBINATIONS, RC.PALETTE_COMBINATIONS)
        self.assertIs(MobileReadabilityChecker.RENDERER_FONT_SIZES, RC.RENDERER_FONT_SIZES)

    def test_light_subtitle_contrast_meets_wcag_aa(self):
        checker = MobileReadabilityChecker({})
        result = checker.check({"slide_readability": [{"page": 1, "headline_ok": True, "body_ok": True}]})
        self.assertGreaterEqual(result["contrast_details"]["light"]["subtitle_vs_box"], 4.5)
        self.assertTrue(result["contrast_ok"])

    def test_min_font_and_safe_margin_maintained(self):
        checker = MobileReadabilityChecker({})
        result = checker.check({"slide_readability": [{"page": 1, "headline_ok": True, "body_ok": True}]})
        self.assertTrue(result["min_font_size_ok"])
        self.assertTrue(result["safe_margin_ok"])

    def test_overflow_detected_reflects_actual_input(self):
        checker = MobileReadabilityChecker({})
        bad_result = checker.check({"slide_readability": [{"page": 1, "headline_ok": False, "body_ok": True}]})
        self.assertTrue(bad_result["overflow_detected"])
        good_result = checker.check({"slide_readability": [{"page": 1, "headline_ok": True, "body_ok": True}]})
        self.assertFalse(good_result["overflow_detected"])


# ---- F. QA -------------------------------------------------------------------

class TestQualityCheckerContractGuards(unittest.TestCase):
    def setUp(self):
        self.checker = CardNewsQualityChecker({})

    def test_check_points_sum_to_100(self):
        self.assertEqual(sum(CardNewsQualityChecker.CHECK_POINTS.values()), 100)

    def test_missing_evidence_data_not_penalized(self):
        result = self.checker.check({
            "cards": [],
            "evidence_result": {"evidence_available": False},
            "evidence_applied": False,
        })
        self.assertTrue(self.checker._conditional_ok(result["checks"], "evidence_applied"))

    def test_available_but_not_applied_is_penalized(self):
        result = self.checker.check({
            "cards": [],
            "evidence_result": {"evidence_available": True},
            "evidence_applied": False,
        })
        self.assertFalse(self.checker._conditional_ok(result["checks"], "evidence_applied"))

    def test_unlicensed_asset_not_rendered_flags_violation(self):
        result = self.checker.check({
            "cards": [],
            "evidence_result": {"evidence_assets": [{"applied": True, "render_allowed": False}]},
        })
        self.assertFalse(result["checks"]["unlicensed_asset_not_rendered"])

    def test_prohibited_fake_screenshot_absent_flags_violation(self):
        result = self.checker.check({
            "cards": [],
            "evidence_applied": True,
            "evidence_result": {"top_evidence_asset": {"asset_role": "competitor_reference"}},
        })
        self.assertFalse(result["checks"]["prohibited_fake_screenshot_absent"])

    def test_layout_selection_fallback_is_not_reported_as_rendering_fallback(self):
        result = self.checker.check({
            "cards": [],
            "layout_result": {"fallback_used": True},
            "rendering_result": {"fallback_used": False},
        })
        self.assertTrue(result["checks"]["layout_fallback_used"])
        self.assertFalse(result["checks"]["rendering_fallback_used"])
        self.assertIn(
            "layout_result.fallback_used=True (안전한 기존 레이아웃으로 대체 선택됨).",
            result["warnings"],
        )
        self.assertNotIn(
            "rendering_result.fallback_used=True (레이아웃 인지 렌더링이 일부/전부 fallback됨).",
            result["warnings"],
        )

    def test_intentional_debate_skip_is_not_penalized(self):
        result = self.checker.check({
            "cards": [],
            "debate_result": {
                "should_apply": True,
                "applied": False,
                "skip_reason": "CTA 슬라이드 글자 수 예산을 초과해 추가하지 않음.",
            },
        })
        self.assertFalse(result["checks"]["debate_required"])
        self.assertTrue(self.checker._conditional_ok(result["checks"], "debate_applied"))
        self.assertNotIn("debate 질문이 적용 대상이었는데 실제로 추가되지 않았습니다.", result["warnings"])

    def test_unexplained_debate_miss_remains_a_warning(self):
        result = self.checker.check({
            "cards": [],
            "debate_result": {"should_apply": True, "applied": False, "skip_reason": ""},
        })
        self.assertTrue(result["checks"]["debate_required"])
        self.assertFalse(self.checker._conditional_ok(result["checks"], "debate_applied"))
        self.assertIn("debate 질문이 적용 대상이었는데 실제로 추가되지 않았습니다.", result["warnings"])


if __name__ == "__main__":
    unittest.main()
