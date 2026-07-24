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
                "license": "CC BY-SA 4.0",
                "license_name": "CC BY-SA 4.0",
                "attribution": "Example Photographer",
                "attribution_text": "Photo: Example Photographer",
                "attribution_required": True,
                "quality_gate": {
                    "passed": True,
                    "relevant_score": 0.9,
                },
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
        plan["real_comment_evidence"] = {
            "status": "ready",
            "selected": [{"comment_id": "comment-1"}],
        }
        plan["story_comment_spotlight"] = {
            "status": "ready",
            "output_path": "C:/approved/spotlight.png",
        }
        result = build_selected_candidate_production_package(
            plan, _render_receipt(plan), _story()
        )

        self.assertEqual(result["status"], "production_package_pending_approval")
        self.assertEqual(result["reason_code"], "package_approval_required")
        source_candidate = result["slides"][0]["visual_spec"]["source_media_candidate"]
        self.assertEqual(source_candidate["asset_id"], "asset-1")
        self.assertEqual(source_candidate["local_path"], "C:/approved/news.jpg")
        self.assertEqual(
            source_candidate["attribution_text"], "Photo: Example Photographer"
        )
        self.assertEqual(source_candidate["license_name"], "CC BY-SA 4.0")
        self.assertEqual(result["candidate"]["account"], "A")
        self.assertEqual(len(result["slides"]), 5)
        self.assertEqual(result["media_plan"][2]["media_type"], "video")
        self.assertEqual(result["feed_caption"], "슬라이드 문구와 분리된 피드 캡션")
        self.assertEqual(result["evidence"]["source_status"], "recorded")
        self.assertEqual(
            result["real_comment_evidence"]["selected"][0]["comment_id"],
            "comment-1",
        )
        self.assertEqual(
            result["story_comment_spotlight"]["status"],
            "ready",
        )
        self.assertEqual(result["gates"]["package_approval"]["status"], "pending")
        self.assertEqual(result["gates"]["render"]["status"], "blocked")
        self.assertFalse(result["receipts"]["render_executed"])
        self.assertFalse(result["receipts"]["publish_executed"])

    def test_story_slide_copy_is_the_single_final_copy_source(self):
        plan = _plan(1)
        plan["slide_plan"][0]["headline"] = "플래너의 긴 제목"
        plan["slide_plan"][0]["body"] = "플래너의 긴 원문 본문"
        story = _story(1)

        result = build_selected_candidate_production_package(
            plan, _render_receipt(plan), story
        )

        self.assertEqual("제목 1", result["slides"][0]["headline"])
        self.assertEqual("본문 1", result["slides"][0]["body"])

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
        self.assertEqual(result["status"], "production_package_ready")
        self.assertEqual(result["reason_code"], "strict_package_composed")
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
        self.assertEqual(result["status"], "production_package_pending_approval")
        self.assertEqual(result["evidence"]["rights_status"], "reference_only_present")
        self.assertEqual(result["evidence"]["non_renderable_asset_ids"], ["asset-1"])
        self.assertEqual(
            result["gates"]["render"]["reason_code"],
            "reference_assets_require_replacement_or_reuse_confirmation",
        )
        self.assertFalse(result["receipts"]["render_executed"])

    def test_source_only_editorial_package_does_not_require_media_asset(self):
        plan = _plan(3)
        plan["asset_inventory"] = []
        for slide in plan["slide_plan"]:
            slide["media_type"] = "editorial"
            slide["asset_refs"] = []
            slide["motion_ref"] = None
        render = _render_receipt(plan)
        render.update({
            "status": "renderer_input_ready",
            "renderer_ready": True,
            "reason_code": "legacy_static_contract_satisfied",
        })

        result = build_selected_candidate_production_package(
            plan, render, _story(3)
        )

        self.assertEqual(result["status"], "production_package_pending_approval")
        self.assertEqual(result["evidence"]["rights_status"], "source_only_editorial")
        self.assertEqual(result["evidence"]["sources"], ["https://news.example/source"])
        self.assertEqual(result["evidence"]["assets"], [])

    def test_approval_requires_identity_candidate_scope_and_receipt_fields(self):
        plan = _plan(4)
        render = _render_receipt(plan)
        render.update({"status": "renderer_input_ready", "renderer_ready": True})
        valid_receipt = {
            "status": "approved",
            "scope": "production_package",
            "candidate_id": "A-1",
            "approved_by": "owner_delegate",
            "receipt_id": "approval-1",
        }

        invalid_receipts = {
            "missing_receipt_id": {**valid_receipt, "receipt_id": ""},
            "missing_approved_by": {**valid_receipt, "approved_by": ""},
            "candidate_mismatch": {**valid_receipt, "candidate_id": "B-OTHER"},
            "scope_mismatch": {**valid_receipt, "scope": "render"},
        }
        for case, receipt in invalid_receipts.items():
            with self.subTest(case=case):
                result = build_selected_candidate_production_package(
                    plan, render, _story(4), receipt
                )
                self.assertEqual(
                    result["status"], "production_package_pending_approval"
                )
                self.assertEqual(
                    result["reason_code"], "invalid_package_approval_receipt"
                )
                self.assertFalse(result["gates"]["package_approval"]["approved"])
                self.assertEqual(result["gates"]["render"]["status"], "blocked")

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

    def test_package_accepts_twenty_slides_and_rejects_twenty_one(self):
        accepted_plan = _plan(20)
        accepted = build_selected_candidate_production_package(
            accepted_plan, _render_receipt(accepted_plan), _story(20)
        )
        rejected_plan = _plan(21)
        rejected = build_selected_candidate_production_package(
            rejected_plan, _render_receipt(rejected_plan), _story(21)
        )

        self.assertEqual("production_package_pending_approval", accepted["status"])
        self.assertEqual(20, len(accepted["slides"]))
        self.assertEqual("blocked", rejected["status"])
        self.assertEqual("slide_count_out_of_bounds", rejected["reason_code"])

    def test_nested_blueprint_learning_contract_reaches_package_receipt(self):
        plan = _plan(1)
        plan["production_blueprint"] = {
            "design_system": {
                "learned_profile": {
                    "layout_family": "editorial_split",
                    "palette": {"accent": "#d63d2f"},
                }
            },
            "learning_trace": {
                "production_profile": {
                    "profile_id": "production-profile:nested",
                    "render_contract_receipt": {
                        "consumed_fields": ["layout_family", "palette"],
                        "ignored_fields": ["image_grammar"],
                    },
                    "reference_v2_registry": {
                        "status": "no_owner_approved_references",
                        "selectable_reference_ids": [],
                        "auto_approval_performed": False,
                    },
                }
            },
        }
        render = _render_receipt(plan)

        result = build_selected_candidate_production_package(
            plan, render, _story(1)
        )

        self.assertEqual(1, len(result["slides"]))
        self.assertEqual(
            "editorial_split",
            result["design_system"]["learned_profile"]["layout_family"],
        )
        receipt = result["learning_pipeline_consumption_receipt"]
        self.assertEqual(
            ["layout_family", "palette"],
            receipt["profile_consumed_fields"],
        )
        self.assertEqual(
            "no_owner_approved_references",
            receipt["registry_status"],
        )
        self.assertFalse(receipt["render_execution_claimed"])


if __name__ == "__main__":
    unittest.main()
