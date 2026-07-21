import copy
import unittest

from modules.card_news.selected_candidate_production_package import (
    build_selected_candidate_production_package,
)


def _plan(slide_count=5):
    slides = []
    for page in range(1, slide_count + 1):
        slides.append(
            {
                "slide_role": "cover" if page == 1 else "source_context",
                "media_type": "image" if page != 3 else "video",
                "asset_refs": ["asset-1"],
                "motion_ref": "motion-1" if page == 3 else None,
            }
        )
    return {
        "schema_version": "selected_candidate_production_plan_v1",
        "status": "production_plan_ready",
        "candidate_id": "A-1",
        "account": "A",
        "category": "국내뉴스",
        "title": "선정 뉴스",
        "slide_count": slide_count,
        "slide_plan": slides,
        "copy_plan": {
            "source_credit": ["https://news.example/source"],
            "feed_body": "계획 단계의 본문",
        },
        "asset_inventory": [
            {
                "asset_id": "asset-1",
                "origin": "news",
                "asset_class": "source_evidence",
                "locator": "C:/approved/news.jpg",
                "source_url": "https://news.example/source",
                "rights_status": "licensed",
            }
        ],
        "commerce": {"mode": "none", "required_for_readiness": False},
    }


def _render_receipt(plan):
    return {
        "schema_version": "selected_candidate_render_input_v1",
        "status": "blocked",
        "reason_code": "current_renderer_slide_limit",
        "renderer_ready": False,
        "render_executed": False,
        "publish_executed": False,
        "full_plan_preserved": copy.deepcopy(plan),
    }


def _story(slide_count=5):
    return {
        "candidate_id": "A-1",
        "story": {"summary": "확인된 기사 근거를 순서대로 설명한다."},
        "slide_copy": [
            {"page": page, "headline": f"제목 {page}", "body": f"본문 {page}"}
            for page in range(1, slide_count + 1)
        ],
        "feed_caption": "슬라이드 문구와 분리된 피드 캡션",
    }


class SelectedCandidateProductionPackageTests(unittest.TestCase):
    def test_composes_variable_hybrid_package_without_rendering(self):
        plan = _plan()
        result = build_selected_candidate_production_package(
            plan, _render_receipt(plan), _story()
        )

        self.assertEqual(result["status"], "production_package_ready")
        self.assertEqual(result["candidate"]["account"], "A")
        self.assertEqual(len(result["slides"]), 5)
        self.assertEqual(result["media_plan"][2]["media_type"], "video")
        self.assertEqual(result["feed_caption"], "슬라이드 문구와 분리된 피드 캡션")
        self.assertEqual(result["evidence"]["source_status"], "recorded")
        self.assertEqual(result["gates"]["package_approval"]["status"], "pending")
        self.assertEqual(result["gates"]["render"]["status"], "blocked")
        self.assertFalse(result["receipts"]["render_executed"])
        self.assertFalse(result["receipts"]["publish_executed"])

    def test_valid_package_approval_does_not_execute_or_authorize_publish(self):
        plan = _plan(4)
        render = _render_receipt(plan)
        render.update({"status": "renderer_input_ready", "renderer_ready": True, "reason_code": "legacy_static_contract_satisfied"})
        story = _story(4)
        result = build_selected_candidate_production_package(
            plan,
            render,
            story,
            {
                "status": "approved",
                "scope": "production_package",
                "candidate_id": "A-1",
                "approved_by": "owner_delegate",
                "receipt_id": "approval-1",
            },
        )

        self.assertTrue(result["gates"]["package_approval"]["approved"])
        self.assertEqual(result["gates"]["render"]["status"], "ready")
        self.assertFalse(result["gates"]["render"]["authorized"])
        self.assertEqual(result["gates"]["publish"]["status"], "blocked")
        self.assertFalse(result["receipts"]["render_executed"])

    def test_missing_evidence_fails_closed_and_reference_only_blocks_render(self):
        plan = _plan()
        plan["copy_plan"]["source_credit"] = []
        result = build_selected_candidate_production_package(
            plan, _render_receipt(plan), _story()
        )
        self.assertEqual(result["reason_code"], "evidence_sources_missing")
        self.assertFalse(result["gates"]["render"]["authorized"])

        plan = _plan()
        plan["asset_inventory"][0]["rights_status"] = "unrecorded"
        result = build_selected_candidate_production_package(
            plan, _render_receipt(plan), _story()
        )
        self.assertEqual(result["status"], "production_package_ready")
        self.assertEqual(result["evidence"]["rights_status"], "reference_only_present")
        self.assertEqual(result["evidence"]["non_renderable_asset_ids"], ["asset-1"])
        self.assertEqual(
            result["gates"]["render"]["reason_code"],
            "reference_assets_require_replacement_or_reuse_confirmation",
        )
        self.assertFalse(result["receipts"]["render_executed"])

    def test_mismatched_outputs_and_incomplete_slide_copy_are_blocked(self):
        plan = _plan()
        story = _story()
        story["candidate_id"] = "B-OTHER"
        result = build_selected_candidate_production_package(
            plan, _render_receipt(plan), story
        )
        self.assertEqual(result["reason_code"], "story_candidate_mismatch")

        story = _story()
        story["slide_copy"].pop()
        result = build_selected_candidate_production_package(
            plan, _render_receipt(plan), story
        )
        self.assertEqual(result["reason_code"], "slide_copy_incomplete")

        render = _render_receipt(plan)
        render["full_plan_preserved"]["account"] = "B"
        result = build_selected_candidate_production_package(plan, render, _story())
        self.assertEqual(result["reason_code"], "render_receipt_plan_mismatch")

    def test_commerce_is_optional_and_preserved_without_link_issuance(self):
        plan = _plan()
        plan["commerce"] = {
            "mode": "optional_match",
            "required_for_readiness": False,
            "product_match": {"product_id": "P-1", "fit": "natural"},
        }
        result = build_selected_candidate_production_package(
            plan, _render_receipt(plan), _story()
        )
        self.assertEqual(result["commerce"]["mode"], "optional_match")
        self.assertFalse(result["receipts"]["link_issuance_executed"])


if __name__ == "__main__":
    unittest.main()
