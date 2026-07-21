import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.compliance.campaign_compliance_checker import CampaignComplianceChecker
from modules.compliance import CardNewsPublishGate


NOW = datetime(2026, 7, 12, 9, 0, 0, tzinfo=timezone.utc)


def iso(delta=timedelta()):
    return (NOW + delta).isoformat()


def requirement(requirement_id, requirement_type, **overrides):
    base = {
        "requirement_id": requirement_id,
        "requirement_type": requirement_type,
        "description": "",
        "required": True,
        "expected_value": None,
        "minimum_count": None,
        "maximum_count": None,
        "allowed_values": [],
        "prohibited_values": [],
        "verification_mode": "",
        "source_reference": None,
    }
    base.update(overrides)
    return base


def package(**overrides):
    base = {
        "package_id": "pkg-001",
        "channel": "instagram",
        "title": "테스트브랜드 신제품 소개",
        "body": "테스트브랜드의 신제품을 소개합니다. 유료광고 포함 콘텐츠입니다.",
        "caption": "테스트브랜드와 함께한 협찬 콘텐츠, 유료광고 포함",
        "hashtags": ["#테스트브랜드", "#협찬", "#유료광고"],
        "links": ["https://example.com/product/123"],
        "assets": [
            {"asset_id": "a1", "type": "image", "rights_status": "owned"},
            {"asset_id": "a2", "type": "image", "rights_status": "owned"},
        ],
        "publishing_time": iso(),
        "evidence_refs": [],
        "rights_status": "owned",
    }
    base.update(overrides)
    return base


def evidence(evidence_id="ev1", **overrides):
    base = {
        "evidence_id": evidence_id,
        "source_url": "https://merchant.example.com/sales-report",
        "locator": None,
        "captured_at": iso(timedelta(days=-2)),
        "verified_at": iso(timedelta(days=-1)),
        "rights_status": "owned",
    }
    base.update(overrides)
    return base


def campaign(requirements, campaign_id="campaign-001"):
    return {"campaign_id": campaign_id, "requirements": requirements}


def card_news_intake(**overrides):
    reviewed_at = "2026-07-12T08:00:00+00:00"
    base = {
        "package_id": "card-news-001",
        "output_set_id": "card-news-output-001",
        "final_cards": [
            {"path": f"assets/card_{index}.png", "output_set_id": "card-news-output-001"}
            for index in range(1, 5)
        ],
        "quality": {
            "output_set_id": "card-news-output-001",
            "passed": True,
        },
        "assets": [{
            "asset_id": "hero-1",
            "asset_path": "assets/hero.png",
            "classification": "publishable_asset",
            "origin": "first_party",
            "asset_role": "topic_evidence",
            "rights_status": "owned",
            "rights_evidence": {
                "type": "ownership_record",
                "reference": "https://example.com/rights/hero-1",
                "review_status": "approved",
                "reference_verified": True,
                "reviewed_at": reviewed_at,
                "asset_id": "hero-1",
                "asset_path": "assets/hero.png",
            },
            "topic_relevant": True,
            "topic_relevance_note": "The asset directly depicts the reviewed topic.",
            "attribution_required": False,
            "attribution_text": "",
        }],
        "evidence": [{
            "evidence_id": "ev-card-1",
            "asset_id": "hero-1",
            "asset_path": "assets/hero.png",
            "source_url": "https://example.com/source",
            "source_name": "Example source",
            "captured_at": "2026-07-12T07:00:00+00:00",
            "reviewed_at": reviewed_at,
            "topic_relevant": True,
            "topic_relevance_note": "The source directly supports the card topic.",
            "authenticity_status": "verified",
            "reference_verified": True,
        }],
        "claims": [{
            "claim_id": "claim-1",
            "text": "The reviewed event occurred.",
            "review_status": "approved",
            "evidence_ids": ["ev-card-1"],
        }],
        "campaign": {
            "is_advertising": False,
            "is_sponsored": False,
            "has_affiliate_link": False,
            "commercial_relationship_reviewed": True,
        },
        "disclosures": [],
        "operator_checklist": {
            "operator_id": "operator-1",
            "reviewed_at": reviewed_at,
            "checks": {
                "source_opened": True,
                "rights_reviewed": True,
                "claims_reviewed": True,
                "attribution_reviewed": True,
                "final_asset_reviewed": True,
            },
        },
    }
    base.update(overrides)
    return base


class CampaignComplianceCheckerTests(unittest.TestCase):
    def setUp(self):
        self.checker = CampaignComplianceChecker()

    def test_fully_valid_positive_path_is_publish_ready(self):
        requirements = [
            requirement("r1", "required_keyword", expected_value="테스트브랜드"),
            requirement("r2", "prohibited_keyword", prohibited_values=["과장광고금지어"]),
            requirement("r3", "disclosure_text", allowed_values=["유료광고"]),
            requirement("r4", "image_count", minimum_count=1, maximum_count=5),
            requirement("r5", "hashtag", expected_value="협찬"),
            requirement("r6", "link_required", minimum_count=1),
            requirement("r7", "brand_name", expected_value="테스트브랜드"),
        ]
        result = self.checker.check(campaign(requirements), package())

        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(result["manual_review_count"], 0)
        self.assertEqual(result["blocking_reasons"], [])
        self.assertTrue(result["publish_ready"])
        self.assertEqual(result["passed_count"], len(requirements))

    def test_required_keyword_missing_fails_and_blocks(self):
        requirements = [requirement("r1", "required_keyword", expected_value="없는키워드")]
        result = self.checker.check(campaign(requirements), package())

        self.assertEqual(result["requirement_results"][0]["status"], "fail")
        self.assertEqual(result["failed_count"], 1)
        self.assertFalse(result["publish_ready"])
        self.assertEqual(result["blocking_reasons"][0]["requirement_id"], "r1")

    def test_keyword_case_and_whitespace_are_normalized(self):
        content = package(title="TESTBRAND", body="  테스트브랜드   테스트  ", caption="")
        requirements = [requirement("r1", "required_keyword", expected_value="테스트브랜드")]
        result = self.checker.check(campaign(requirements), content)

        self.assertEqual(result["requirement_results"][0]["status"], "pass")

    def test_prohibited_keyword_found_reports_location(self):
        requirements = [requirement("r1", "prohibited_keyword", prohibited_values=["최고효능"])]
        content = package(body="이 제품은 최고효능을 자랑합니다.")
        result = self.checker.check(campaign(requirements), content)

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "fail")
        self.assertIn("body", entry["location"])
        self.assertFalse(result["publish_ready"])

    def test_disclosure_text_missing_blocks_even_if_marked_optional(self):
        requirements = [requirement("r1", "disclosure_text", allowed_values=["유료광고"], required=False)]
        content = package(body="테스트브랜드 제품 후기입니다.", caption="", hashtags=[])
        result = self.checker.check(campaign(requirements), content)

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "fail")
        # Disclosure is fail-closed regardless of `required` -- must still block.
        self.assertFalse(result["publish_ready"])
        blocking_ids = {reason["requirement_id"] for reason in result["blocking_reasons"]}
        self.assertIn("r1", blocking_ids)

    def test_image_count_below_minimum_fails(self):
        requirements = [requirement("r1", "image_count", minimum_count=3)]
        content = package(assets=[{"asset_id": "a1", "type": "image"}])
        result = self.checker.check(campaign(requirements), content)

        self.assertEqual(result["requirement_results"][0]["status"], "fail")

    def test_image_count_above_maximum_fails(self):
        requirements = [requirement("r1", "image_count", maximum_count=1)]
        content = package(assets=[
            {"asset_id": "a1", "type": "image"},
            {"asset_id": "a2", "type": "image"},
            {"asset_id": "a3", "type": "image"},
        ])
        result = self.checker.check(campaign(requirements), content)

        self.assertEqual(result["requirement_results"][0]["status"], "fail")

    def test_video_required_missing_fails(self):
        requirements = [requirement("r1", "video_required")]
        result = self.checker.check(campaign(requirements), package())

        self.assertEqual(result["requirement_results"][0]["status"], "fail")

    def test_video_required_present_passes(self):
        requirements = [requirement("r1", "video_required")]
        content = package(assets=[{"asset_id": "v1", "type": "video"}])
        result = self.checker.check(campaign(requirements), content)

        self.assertEqual(result["requirement_results"][0]["status"], "pass")

    def test_map_required_always_manual_review(self):
        requirements = [requirement("r1", "map_required")]
        result = self.checker.check(campaign(requirements), package())

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "manual_review")
        self.assertEqual(result["manual_review_count"], 1)
        self.assertFalse(result["publish_ready"])

    def test_link_required_missing_fails(self):
        requirements = [requirement("r1", "link_required", expected_value="required-domain.com")]
        content = package(links=["https://other-domain.com/x"])
        result = self.checker.check(campaign(requirements), content)

        self.assertEqual(result["requirement_results"][0]["status"], "fail")

    def test_hashtag_required_missing_fails(self):
        requirements = [requirement("r1", "hashtag", expected_value="필수태그")]
        content = package(hashtags=["#다른태그"])
        result = self.checker.check(campaign(requirements), content)

        self.assertEqual(result["requirement_results"][0]["status"], "fail")

    def test_publishing_window_before_start_fails(self):
        requirements = [requirement(
            "r1", "publishing_window",
            expected_value={"window_start": iso(timedelta(days=1)), "window_end": iso(timedelta(days=5))},
        )]
        content = package(publishing_time=iso())
        result = self.checker.check(campaign(requirements), content)

        self.assertEqual(result["requirement_results"][0]["status"], "fail")

    def test_publishing_window_after_end_fails(self):
        requirements = [requirement(
            "r1", "publishing_window",
            expected_value={"window_start": iso(timedelta(days=-5)), "window_end": iso(timedelta(days=-1))},
        )]
        content = package(publishing_time=iso())
        result = self.checker.check(campaign(requirements), content)

        self.assertEqual(result["requirement_results"][0]["status"], "fail")

    def test_publishing_window_within_range_passes(self):
        requirements = [requirement(
            "r1", "publishing_window",
            expected_value={"window_start": iso(timedelta(days=-1)), "window_end": iso(timedelta(days=1))},
        )]
        content = package(publishing_time=iso())
        result = self.checker.check(campaign(requirements), content)

        self.assertEqual(result["requirement_results"][0]["status"], "pass")

    def test_timezone_naive_publishing_time_is_rejected(self):
        requirements = [requirement("r1", "publishing_window", expected_value={})]
        content = package(publishing_time="2026-07-12T09:00:00")  # no offset
        result = self.checker.check(campaign(requirements), content)

        self.assertEqual(result["requirement_results"][0]["status"], "fail")

    def test_numeric_claim_without_evidence_blocks(self):
        requirements = [requirement(
            "r1", "numeric_claim", expected_value="지난달 매출 30% 증가", source_reference=None,
        )]
        content = package(body="지난달 매출 30% 증가를 기록했습니다.", evidence_refs=[])
        result = self.checker.check(campaign(requirements), content)

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "fail")
        self.assertFalse(result["publish_ready"])

    def test_numeric_claim_with_evidence_waits_for_manual_approval(self):
        requirements = [requirement(
            "r1", "numeric_claim", expected_value="지난달 판매량 1200개 돌파",
            source_reference="ev1",
        )]
        content = package(body="지난달 판매량 1200개 돌파! 감사합니다.", evidence_refs=[evidence("ev1")])
        result = self.checker.check(campaign(requirements), content)

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "manual_review")
        self.assertEqual(result["manual_review_count"], 1)
        # Never auto-publish even with proper evidence.
        self.assertFalse(result["publish_ready"])
        self.assertNotIn("r1", {reason["requirement_id"] for reason in result["blocking_reasons"]})

    def test_numeric_claim_not_applicable_when_no_claim_pattern_present(self):
        requirements = [requirement("r1", "numeric_claim", expected_value=None)]
        content = package(body="오늘 소개할 제품은 정말 좋아요.", evidence_refs=[])
        result = self.checker.check(campaign(requirements), content)

        self.assertEqual(result["requirement_results"][0]["status"], "not_applicable")

    def test_rights_status_missing_blocks_publish(self):
        content = package(rights_status="")
        result = self.checker.check(campaign([]), content)

        self.assertFalse(result["publish_ready"])
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("package_rights_status_invalid", codes)

    def test_rights_status_disallowed_value_blocks_publish(self):
        content = package(rights_status="unknown_third_party")
        result = self.checker.check(campaign([]), content)

        self.assertFalse(result["publish_ready"])

    def test_required_vs_optional_failure_difference(self):
        requirements = [
            requirement("r1", "required_keyword", expected_value="없는필수키워드", required=True),
            requirement("r2", "required_keyword", expected_value="없는선택키워드", required=False),
        ]
        result = self.checker.check(campaign(requirements), package())

        blocking_ids = {reason["requirement_id"] for reason in result["blocking_reasons"]}
        warning_ids = {warning.get("requirement_id") for warning in result["warnings"]}
        self.assertIn("r1", blocking_ids)
        self.assertIn("r2", warning_ids)
        self.assertNotIn("r2", blocking_ids)
        self.assertFalse(result["publish_ready"])

    def test_unknown_requirement_type_is_manual_review_never_pass(self):
        requirements = [requirement("r1", "unsupported_future_type")]
        result = self.checker.check(campaign(requirements), package())

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "manual_review")
        self.assertNotEqual(entry["status"], "pass")

    def test_duplicate_requirement_id_is_contract_blocker(self):
        # NO-GO fix: a duplicate requirement_id is a contract blocker, not a
        # silently-deduplicated warning -- the whole check must refuse to run.
        requirements = [
            requirement("r1", "required_keyword", expected_value="테스트브랜드"),
            requirement("r1", "hashtag", expected_value="협찬"),
        ]
        result = self.checker.check(campaign(requirements), package())

        self.assertEqual(result["requirement_results"], [])
        self.assertFalse(result["publish_ready"])
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("campaign_contract_invalid", codes)

    def test_empty_campaign_returns_neutral_result(self):
        result = self.checker.check(campaign([]), package())

        self.assertEqual(result["requirement_results"], [])
        self.assertEqual(result["passed_count"], 0)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(result["manual_review_count"], 0)
        self.assertTrue(result["publish_ready"])

    def test_input_objects_are_not_mutated(self):
        requirements = [requirement("r1", "required_keyword", expected_value="테스트브랜드")]
        campaign_input = campaign(requirements)
        content_input = package()
        campaign_snapshot = copy.deepcopy(campaign_input)
        content_snapshot = copy.deepcopy(content_input)

        self.checker.check(campaign_input, content_input)

        self.assertEqual(campaign_input, campaign_snapshot)
        self.assertEqual(content_input, content_snapshot)

    def test_result_is_json_serializable(self):
        requirements = [requirement("r1", "required_keyword", expected_value="테스트브랜드")]
        result = self.checker.check(campaign(requirements), package())

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIsInstance(serialized, str)
        self.assertEqual(json.loads(serialized)["schema_version"], result["schema_version"])

    def test_internal_error_returns_fail_closed_structured_result(self):
        with patch(
            "modules.compliance.campaign_compliance_checker.normalize_content_package",
            side_effect=RuntimeError("boom"),
        ):
            result = self.checker.check(campaign([]), package())

        self.assertFalse(result["publish_ready"])
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("compliance_check_internal_error", codes)
        self.assertEqual(result["schema_version"], "campaign_compliance_phase_1.v1")

    def test_single_requirement_exception_does_not_crash_whole_check(self):
        requirements = [
            requirement("r1", "required_keyword", expected_value="테스트브랜드"),
            requirement("r2", "hashtag", expected_value="협찬"),
        ]
        with patch.object(
            CampaignComplianceChecker, "_check_keyword_presence", side_effect=RuntimeError("boom")
        ):
            result = self.checker.check(campaign(requirements), package())

        statuses = {entry["requirement_id"]: entry["status"] for entry in result["requirement_results"]}
        self.assertEqual(statuses["r1"], "fail")
        self.assertEqual(statuses["r2"], "pass")

    def test_secret_like_string_never_leaks_into_result(self):
        secret_token = "a" * 40
        requirements = [requirement("r1", "link_required", expected_value="required-domain.com")]
        content = package(links=[f"https://tracking.example.com/x?token={secret_token}"])

        with patch(
            "modules.compliance.campaign_compliance_checker.normalize_content_package",
            side_effect=RuntimeError(f"failed while processing token={secret_token}"),
        ):
            result = self.checker.check(campaign(requirements), content)

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(secret_token, serialized)

    def test_engagement_bait_combined_with_financial_claim_blocks(self):
        content = package(
            body="댓글 남기면 매월 30% 수익 보장해드립니다!",
            evidence_refs=[],
        )
        result = self.checker.check(campaign([]), content)

        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("engagement_bait_financial_claim_combo", codes)
        self.assertFalse(result["publish_ready"])

    def test_financial_claim_without_bait_language_does_not_trigger_combo_rule(self):
        content = package(body="이번 달 매출이 30% 증가했습니다.", evidence_refs=[])
        result = self.checker.check(campaign([]), content)

        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertNotIn("engagement_bait_financial_claim_combo", codes)

    def test_deterministic_result_for_same_input(self):
        requirements = [
            requirement("r1", "required_keyword", expected_value="테스트브랜드"),
            requirement("r2", "map_required"),
        ]
        content = package()

        result_one = self.checker.check(campaign(requirements), content)
        result_two = self.checker.check(campaign(copy.deepcopy(requirements)), copy.deepcopy(content))

        result_one.pop("checked_at")
        result_two.pop("checked_at")
        self.assertEqual(result_one, result_two)

    # ------------------------------------------------------------------
    # Independent QA NO-GO fixes (this Sprint)
    # ------------------------------------------------------------------

    def test_campaign_int_is_contract_blocked(self):
        result = self.checker.check(123, package())

        self.assertEqual(result["requirement_results"], [])
        self.assertFalse(result["publish_ready"])
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("campaign_contract_invalid", codes)

    def test_campaign_none_is_contract_blocked(self):
        result = self.checker.check(None, package())

        self.assertEqual(result["requirement_results"], [])
        self.assertFalse(result["publish_ready"])
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("campaign_contract_invalid", codes)

    def test_campaign_dict_missing_requirements_key_is_contract_blocked(self):
        result = self.checker.check({"campaign_id": "campaign-001"}, package())

        self.assertEqual(result["requirement_results"], [])
        self.assertFalse(result["publish_ready"])
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("campaign_contract_invalid", codes)

    def test_campaign_requirements_as_string_is_contract_blocked(self):
        result = self.checker.check({"campaign_id": "campaign-001", "requirements": "not a list"}, package())

        self.assertEqual(result["requirement_results"], [])
        self.assertFalse(result["publish_ready"])
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("campaign_contract_invalid", codes)

    def test_bare_requirement_list_campaign_is_still_valid(self):
        # A bare list (no dict/campaign_id wrapper) remains a legitimate shape.
        requirements = [requirement("r1", "required_keyword", expected_value="테스트브랜드")]
        result = self.checker.check(requirements, package())

        self.assertEqual(len(result["requirement_results"]), 1)
        self.assertIsNone(result["campaign_id"])

    def test_publishing_window_unparseable_start_does_not_pass(self):
        requirements = [requirement(
            "r1", "publishing_window",
            expected_value={"window_start": "not-a-real-date", "window_end": iso(timedelta(days=5))},
        )]
        result = self.checker.check(campaign(requirements), package())

        entry = result["requirement_results"][0]
        self.assertNotEqual(entry["status"], "pass")
        self.assertEqual(entry["status"], "fail")

    def test_publishing_window_unparseable_end_does_not_pass(self):
        requirements = [requirement(
            "r1", "publishing_window",
            expected_value={"window_start": iso(timedelta(days=-5)), "window_end": "also-not-a-date"},
        )]
        result = self.checker.check(campaign(requirements), package())

        entry = result["requirement_results"][0]
        self.assertNotEqual(entry["status"], "pass")
        self.assertEqual(entry["status"], "fail")

    def test_publishing_window_start_after_end_is_blocked(self):
        requirements = [requirement(
            "r1", "publishing_window",
            expected_value={"window_start": iso(timedelta(days=5)), "window_end": iso(timedelta(days=1))},
        )]
        result = self.checker.check(campaign(requirements), package())

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "fail")

    def test_optional_requirement_internal_exception_still_blocks_publish(self):
        # NO-GO fix: an internal error blocks publishing regardless of `required`.
        requirements = [requirement("r1", "required_keyword", expected_value="테스트브랜드", required=False)]
        with patch.object(
            CampaignComplianceChecker, "_check_keyword_presence", side_effect=RuntimeError("boom")
        ):
            result = self.checker.check(campaign(requirements), package())

        self.assertFalse(result["publish_ready"])
        blocking_ids = {reason["requirement_id"] for reason in result["blocking_reasons"]}
        self.assertIn("r1", blocking_ids)

    def test_korean_amount_word_sipmanwon_combined_with_bait_blocks(self):
        content = package(body="댓글 남기면 수익 십만원 드립니다!", evidence_refs=[])
        result = self.checker.check(campaign([]), content)

        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("engagement_bait_financial_claim_combo", codes)
        self.assertFalse(result["publish_ready"])

    def test_korean_amount_word_baekmanwon_combined_with_bait_blocks(self):
        content = package(body="DM 주시면 백만원 정보 공개해드립니다.", evidence_refs=[])
        result = self.checker.check(campaign([]), content)

        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("engagement_bait_financial_claim_combo", codes)
        self.assertFalse(result["publish_ready"])

    def test_korean_quantity_word_baekgae_is_detected_as_claim_pattern(self):
        requirements = [requirement("r1", "numeric_claim", expected_value="선착순 백 개 한정")]
        content = package(body="선착순 백 개 한정 특가!", evidence_refs=[])
        result = self.checker.check(campaign(requirements), content)

        entry = result["requirement_results"][0]
        # No evidence reference supplied -- must block, never silently pass.
        self.assertEqual(entry["status"], "fail")

    def test_ocr_ambiguous_number_forces_manual_review(self):
        requirements = [requirement("r1", "numeric_claim", expected_value="매출 1O0만원 달성", source_reference="ev1")]
        content = package(body="매출 1O0만원 달성했습니다.", evidence_refs=[evidence("ev1")])
        result = self.checker.check(campaign(requirements), content)

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "manual_review")
        self.assertIn("OCR-ambiguous", entry["reason"])

    def test_arbitrary_evidence_string_is_not_accepted_as_evidence(self):
        # NO-GO fix: a bare string in evidence_refs must never count as
        # sufficient evidence, even though it matches source_reference exactly.
        requirements = [requirement(
            "r1", "numeric_claim", expected_value="지난달 매출 30% 증가", source_reference="ev1",
        )]
        content = package(body="지난달 매출 30% 증가를 기록했습니다.", evidence_refs=["ev1"])
        result = self.checker.check(campaign(requirements), content)

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "fail")
        self.assertFalse(result["publish_ready"])

    def test_evidence_missing_timestamps_and_rights_blocks_numeric_claim(self):
        requirements = [requirement(
            "r1", "numeric_claim", expected_value="지난달 매출 30% 증가", source_reference="ev1",
        )]
        incomplete_evidence = {
            "evidence_id": "ev1",
            "source_url": "https://merchant.example.com/report",
            "captured_at": None,
            "verified_at": None,
            "rights_status": "",
        }
        content = package(body="지난달 매출 30% 증가를 기록했습니다.", evidence_refs=[incomplete_evidence])
        result = self.checker.check(campaign(requirements), content)

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "fail")

    def test_fully_structured_evidence_numeric_claim_is_manual_review(self):
        requirements = [requirement(
            "r1", "numeric_claim", expected_value="지난달 매출 30% 증가", source_reference="ev1",
        )]
        content = package(body="지난달 매출 30% 증가를 기록했습니다.", evidence_refs=[evidence("ev1")])
        result = self.checker.check(campaign(requirements), content)

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "manual_review")
        self.assertNotIn("r1", {reason["requirement_id"] for reason in result["blocking_reasons"]})

    def test_asset_missing_rights_status_blocks_publish(self):
        content = package(assets=[{"asset_id": "a1", "type": "image"}])
        result = self.checker.check(campaign([]), content)

        self.assertFalse(result["publish_ready"])
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("asset_rights_status_missing", codes)

    def test_asset_rights_via_approved_upstream_manifest_passes(self):
        content = package(
            assets=[{"asset_id": "a1", "type": "image", "upstream_rights_manifest_id": "m1"}],
            rights_manifest={"m1": {"rights_status": "licensed"}},
        )
        result = self.checker.check(campaign([]), content)

        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertNotIn("asset_rights_status_missing", codes)

    def test_asset_with_unapproved_manifest_rights_still_blocks(self):
        content = package(
            assets=[{"asset_id": "a1", "type": "image", "upstream_rights_manifest_id": "m1"}],
            rights_manifest={"m1": {"rights_status": "unlicensed_third_party"}},
        )
        result = self.checker.check(campaign([]), content)

        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("asset_rights_status_missing", codes)

    def test_package_rights_alone_does_not_approve_every_asset(self):
        # Package-level rights_status is valid, but one asset still has none.
        content = package(
            rights_status="owned",
            assets=[
                {"asset_id": "a1", "type": "image", "rights_status": "owned"},
                {"asset_id": "a2", "type": "image"},
            ],
        )
        result = self.checker.check(campaign([]), content)

        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("asset_rights_status_missing", codes)

    def test_unknown_verification_mode_blocks_regardless_of_required(self):
        requirements = [requirement(
            "r1", "required_keyword", expected_value="테스트브랜드",
            required=False, verification_mode="trust_advertiser",
        )]
        result = self.checker.check(campaign(requirements), package())

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "fail")
        blocking_ids = {reason["requirement_id"] for reason in result["blocking_reasons"]}
        self.assertIn("r1", blocking_ids)
        self.assertFalse(result["publish_ready"])

    def test_verification_mode_automatic_behaves_like_unset(self):
        requirements = [requirement("r1", "required_keyword", expected_value="테스트브랜드", verification_mode="automatic")]
        result = self.checker.check(campaign(requirements), package())

        self.assertEqual(result["requirement_results"][0]["status"], "pass")

    def test_verification_mode_manual_forces_manual_review_on_passing_requirement(self):
        requirements = [requirement("r1", "required_keyword", expected_value="테스트브랜드", verification_mode="manual")]
        result = self.checker.check(campaign(requirements), package())

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "manual_review")
        self.assertEqual(result["manual_review_count"], 1)

    def test_verification_mode_manual_forces_manual_review_on_failing_requirement(self):
        requirements = [requirement("r1", "required_keyword", expected_value="없는키워드", verification_mode="manual")]
        result = self.checker.check(campaign(requirements), package())

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "manual_review")

    def test_verification_mode_evidence_required_without_evidence_blocks(self):
        requirements = [requirement(
            "r1", "required_keyword", expected_value="테스트브랜드", verification_mode="evidence_required",
        )]
        result = self.checker.check(campaign(requirements), package())

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "fail")
        blocking_ids = {reason["requirement_id"] for reason in result["blocking_reasons"]}
        self.assertIn("r1", blocking_ids)

    def test_verification_mode_evidence_required_with_complete_evidence_is_manual_review(self):
        requirements = [requirement(
            "r1", "required_keyword", expected_value="테스트브랜드",
            verification_mode="evidence_required", source_reference="ev1",
        )]
        content = package(evidence_refs=[evidence("ev1")])
        result = self.checker.check(campaign(requirements), content)

        entry = result["requirement_results"][0]
        self.assertEqual(entry["status"], "manual_review")
        self.assertNotIn("r1", {reason["requirement_id"] for reason in result["blocking_reasons"]})

    def test_duplicate_id_cannot_be_bypassed_by_differing_requirement_type(self):
        # Same reproduction as the contract-blocker test, phrased as an
        # explicit "bypass attempt" via two structurally different
        # requirements sharing one id.
        requirements = [
            requirement("dup", "disclosure_text", allowed_values=["유료광고"]),
            requirement("dup", "prohibited_keyword", prohibited_values=["금지어"]),
        ]
        result = self.checker.check(campaign(requirements), package())

        self.assertEqual(result["requirement_results"], [])
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("campaign_contract_invalid", codes)

    def test_regression_all_prior_positive_path_fields_present(self):
        requirements = [
            requirement("r1", "required_keyword", expected_value="테스트브랜드"),
            requirement("r2", "prohibited_keyword", prohibited_values=["과장광고금지어"]),
            requirement("r3", "disclosure_text", allowed_values=["유료광고"]),
            requirement("r4", "image_count", minimum_count=1, maximum_count=5),
            requirement("r5", "hashtag", expected_value="협찬"),
            requirement("r6", "link_required", minimum_count=1),
            requirement("r7", "brand_name", expected_value="테스트브랜드"),
        ]
        result = self.checker.check(campaign(requirements), package())

        for key in (
            "schema_version", "package_id", "campaign_id", "checked_at", "requirement_results",
            "passed_count", "failed_count", "manual_review_count", "blocking_reasons", "warnings",
            "manual_checklist", "publish_ready",
        ):
            self.assertIn(key, result)
        self.assertTrue(result["publish_ready"])


class CardNewsPublishGateAttackTests(unittest.TestCase):
    def setUp(self):
        self.image_check = patch(
            "modules.compliance.card_news_publish_gate._valid_image_file",
            return_value=True,
        )
        self.image_check.start()
        self.addCleanup(self.image_check.stop)
        self.gate = CardNewsPublishGate()

    def assert_blocked_with(self, intake, code):
        result = self.gate.check(intake)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["publish_ready"])
        self.assertIn(code, {item["code"] for item in result["blocking_reasons"]})
        self.assertEqual(result["operator_action"], "correct_intake_and_recheck")
        return result

    def assert_canonical_publishing_attestation(self, result, expected_card_count=4):
        attestation = result["pre_publish_attestation"]
        required = {
            "output_set_id", "cards", "rights", "evidence", "quality",
            "release_guard", "compliance_result", "assets", "manual_reviews", "blockers",
        }
        self.assertTrue(required.issubset(attestation))
        self.assertEqual(attestation["schema_version"], 1)
        self.assertEqual(attestation["contract"], "card_news_pre_publish_attestation_v1")
        self.assertEqual(len(attestation["cards"]), expected_card_count)
        self.assertTrue(all(isinstance(card, dict) and card.get("path") for card in attestation["cards"]))
        compliance = attestation["compliance_result"]
        self.assertEqual(compliance["schema_version"], "card_news_compliance.v1")
        self.assertEqual(compliance["package_id"], result["package_id"])
        self.assertEqual(compliance["output_set_id"], result["output_set_id"])
        self.assertEqual(compliance["asset_ids"], attestation["asset_ids"])
        self.assertEqual(
            compliance["render_allowed_asset_ids"],
            attestation["render_allowed_asset_ids"],
        )
        self.assertIn(compliance["status"], {"valid", "blocked"})
        self.assertIs(compliance["publish_ready"], result["publish_ready"])
        self.assertEqual(compliance["blocking_reasons"], result["blocking_reasons"])
        return attestation

    def test_valid_first_party_asset_is_immediately_consumable(self):
        result = self.gate.check(card_news_intake())

        self.assertEqual(result["status"], "valid")
        self.assertTrue(result["publish_ready"])
        self.assertEqual(result["render_allowed_asset_ids"], ["hero-1"])
        self.assertEqual(result["operator_action"], "consume_result")

    def test_output_set_id_is_required_and_ambiguous_values_fail_closed(self):
        for output_set_id in (None, "", "   ", 123, ["set-1"]):
            with self.subTest(output_set_id=output_set_id):
                intake = card_news_intake(output_set_id=output_set_id)
                self.assert_blocked_with(intake, "output_set_id_invalid")

    def test_valid_result_exposes_complete_pre_publish_attestation_contract(self):
        result = self.gate.check(card_news_intake())

        self.assertEqual(result["output_set_id"], "card-news-output-001")
        self.assertEqual(result["manual_reviews"], [])
        attestation = result["pre_publish_attestation"]
        self.assertEqual(attestation["schema_version"], 1)
        self.assertEqual(attestation["output_set_id"], result["output_set_id"])
        self.assertEqual(attestation["asset_ids"], ["hero-1"])
        self.assertEqual(attestation["render_allowed_asset_ids"], ["hero-1"])
        self.assertTrue(attestation["publish_ready"])
        self.assertEqual(attestation["blockers"], [])

        asset = result["asset_results"][0]
        for field in (
            "rights_status",
            "rights_evidence_status",
            "evidence_ids",
            "topic_relevant",
            "attribution_required",
            "attribution_text",
            "manual_review_required",
        ):
            self.assertIn(field, asset)
        self.assertEqual(asset["rights_status"], "owned")
        self.assertEqual(asset["rights_evidence_status"], "valid")
        self.assertEqual(asset["evidence_ids"], ["ev-card-1"])
        self.assertTrue(asset["topic_relevant"])
        self.assertFalse(asset["manual_review_required"])
        canonical = self.assert_canonical_publishing_attestation(result)
        self.assertIs(canonical["rights"]["ready"], True)
        self.assertEqual(canonical["rights"]["status"], "pass")
        self.assertIn(canonical["evidence"]["status"], {"applied", "unavailable"})
        self.assertIs(canonical["quality"]["passed"], True)
        self.assertIs(canonical["release_guard"]["ready"], True)

    def test_final_cards_use_allowed_slide_count_and_are_repo_relative_output_set_bound(self):
        self.assertFalse(self.gate.check(card_news_intake(final_cards=card_news_intake()["final_cards"][:1]))["publish_ready"])
        cases = {
            "missing": [],
            "absolute": [
                {"path": str((Path.cwd() / f"card_{index}.png").resolve()), "output_set_id": "card-news-output-001"}
                for index in range(1, 5)
            ],
            "traversal": [
                {"path": f"../card_{index}.png", "output_set_id": "card-news-output-001"}
                for index in range(1, 5)
            ],
            "output_set_mismatch": [
                {"path": f"assets/card_{index}.png", "output_set_id": "different-set"}
                for index in range(1, 5)
            ],
            "too_many": [
                {"path": f"assets/card_{index}.png", "output_set_id": "card-news-output-001"}
                for index in range(1, 22)
            ],
        }
        for label, final_cards in cases.items():
            with self.subTest(label=label):
                result = self.gate.check(card_news_intake(final_cards=final_cards))
                self.assertFalse(result["publish_ready"])
                codes = {item["code"] for item in result["blocking_reasons"]}
                self.assertTrue(codes & {"final_cards_invalid", "final_card_binding_invalid"})

        valid_3_cards = card_news_intake()["final_cards"][:3]
        result = self.gate.check(card_news_intake(final_cards=valid_3_cards))
        self.assertTrue(result["publish_ready"])

    def test_quality_must_be_explicitly_passed_and_output_set_bound(self):
        for quality in (
            None,
            {},
            {"output_set_id": "card-news-output-001", "passed": False},
            {"output_set_id": "different-set", "passed": True},
            {"output_set_id": "card-news-output-001", "passed": "true"},
        ):
            with self.subTest(quality=quality):
                self.assert_blocked_with(card_news_intake(quality=quality), "quality_attestation_invalid")

    def test_rights_evidence_status_is_self_consistent_in_result_and_attestation(self):
        valid = self.gate.check(card_news_intake())
        self.assertEqual(valid["asset_results"][0]["rights_evidence_status"], "valid")
        self.assertEqual(valid["pre_publish_attestation"]["assets"][0]["rights_evidence_status"], "valid")

        for rights_evidence in (None, {}, {"reference": "forged"}):
            with self.subTest(rights_evidence=rights_evidence):
                intake = card_news_intake()
                intake["assets"][0]["rights_evidence"] = rights_evidence
                result = self.gate.check(intake)
                self.assertFalse(result["publish_ready"])
                self.assertEqual(result["asset_results"][0]["rights_evidence_status"], "blocked")
                self.assertEqual(
                    result["pre_publish_attestation"]["assets"][0]["rights_evidence_status"],
                    "blocked",
                )

    def test_gate_does_not_fabricate_missing_cards_or_quality(self):
        result = self.gate.check(card_news_intake(final_cards=None, quality=None))
        self.assertFalse(result["publish_ready"])
        attestation = self.assert_canonical_publishing_attestation(result, expected_card_count=0)
        self.assertEqual(attestation["cards"], [])
        self.assertIs(attestation["quality"]["passed"], False)
        self.assertIs(attestation["release_guard"]["ready"], False)

    def test_blocked_result_attestation_cannot_be_consumed_as_card_news_pass(self):
        intake = card_news_intake(assets=[{
            "asset_id": "fixture-1",
            "classification": "technical_fixture",
        }])
        result = self.gate.check(intake)

        self.assertEqual(result["schema_version"], "card_news_compliance.v1")
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["publish_ready"])
        self.assertTrue(result["blocking_reasons"])
        self.assertEqual(result["operator_action"], "correct_intake_and_recheck")
        attestation = result["pre_publish_attestation"]
        self.assertEqual(attestation["schema_version"], 1)
        self.assertFalse(attestation["publish_ready"])
        self.assertTrue(attestation["blockers"])
        self.assertEqual(attestation["render_allowed_asset_ids"], [])

    def test_blocked_fixture_preserves_exact_committed_final_cards(self):
        intake = card_news_intake(assets=[{
            "asset_id": "fixture-1",
            "classification": "technical_fixture_not_publish_approved",
        }])
        committed_cards = copy.deepcopy(intake["final_cards"])

        result = self.gate.check(intake)
        attestation = result["pre_publish_attestation"]

        self.assertEqual(attestation["cards"], committed_cards)
        self.assertNotIn(
            "final_cards_invalid",
            {item["code"] for item in result["blocking_reasons"]},
        )
        self.assertFalse(result["publish_ready"])
        self.assertFalse(result["actual_publish"])
        self.assertFalse(attestation["publish_ready"])
        self.assertFalse(attestation["actual_publish"])
        self.assertTrue(attestation["technical_fixture_not_publish_approved"])

    def test_valid_user_supplied_asset_requires_written_permission(self):
        intake = card_news_intake()
        asset = intake["assets"][0]
        asset.update(origin="user_supplied", rights_status="user_supplied_with_permission")
        asset["rights_evidence"].update(type="written_permission")

        self.assertTrue(self.gate.check(intake)["publish_ready"])

    def test_valid_generated_asset_requires_generation_record(self):
        intake = card_news_intake()
        asset = intake["assets"][0]
        asset.update(origin="first_party", asset_role="decorative", rights_status="generated")
        asset["rights_evidence"].update(type="generation_record")

        self.assertTrue(self.gate.check(intake)["publish_ready"])

    def test_approved_external_asset_requires_approved_rights_and_attribution(self):
        intake = card_news_intake()
        asset = intake["assets"][0]
        asset.update(
            origin="approved_external",
            rights_status="licensed",
            attribution_required=True,
            attribution_text="Image courtesy of Example / licensed use",
        )
        asset["rights_evidence"].update(type="license_url")

        result = self.gate.check(intake)
        self.assertTrue(result["publish_ready"])
        self.assertEqual(result["attribution"], [{
            "asset_id": "hero-1",
            "text": "Image courtesy of Example / licensed use",
        }])

    def test_first_party_generated_cannot_masquerade_as_topic_evidence(self):
        intake = card_news_intake()
        asset = intake["assets"][0]
        asset.update(origin="first_party", asset_role="topic_evidence", rights_status="generated")
        asset["rights_evidence"].update(type="generation_record")

        self.assert_blocked_with(intake, "generated_topic_evidence_forbidden")

    def test_asset_rights_and_evidence_bind_to_exact_asset_file(self):
        for target, path in (
            ("rights_evidence", "assets/different.png"),
            ("evidence", "assets/different.png"),
        ):
            with self.subTest(target=target):
                intake = card_news_intake()
                if target == "rights_evidence":
                    intake["assets"][0]["rights_evidence"]["asset_path"] = path
                else:
                    intake["evidence"][0]["asset_path"] = path
                self.assert_blocked_with(intake, "asset_file_binding_mismatch")

    def test_unapproved_rights_reference_never_satisfies_manual_approval(self):
        intake = card_news_intake()
        intake["assets"][0]["rights_evidence"].update(
            review_status="NOT GRANTED",
        )
        result = self.assert_blocked_with(intake, "asset_rights_evidence_invalid")
        self.assertTrue(result["manual_reviews"])
        self.assertTrue(result["pre_publish_attestation"]["blockers"])

    def test_url_shaped_references_require_explicit_operator_verification(self):
        for target in ("rights", "evidence"):
            with self.subTest(target=target):
                intake = card_news_intake()
                if target == "rights":
                    intake["assets"][0]["rights_evidence"]["reference_verified"] = "true"
                    expected = "asset_rights_evidence_invalid"
                else:
                    intake["evidence"][0]["reference_verified"] = "true"
                    expected = "evidence_attestation_invalid"
                result = self.assert_blocked_with(intake, expected)
                self.assertTrue(result["manual_reviews"])
                self.assertEqual(
                    result["manual_reviews"],
                    result["pre_publish_attestation"]["manual_reviews"],
                )

    def test_actual_repository_image_is_decoded_without_global_mock(self):
        self.image_check.stop()
        fixture = Path("tests/fixtures/card_news_rights/first_party_technical_fixture.png")
        existed = fixture.exists()
        if not existed:
            Image.new("RGB", (2, 2), (32, 64, 96)).save(fixture, format="PNG")
        self.addCleanup(lambda: fixture.unlink(missing_ok=True) if not existed else None)

        intake = card_news_intake()
        intake["assets"][0]["asset_path"] = fixture.as_posix()
        intake["assets"][0]["rights_evidence"]["asset_path"] = fixture.as_posix()
        intake["evidence"][0]["asset_path"] = fixture.as_posix()
        for index, card in enumerate(intake["final_cards"], start=1):
            card["path"] = fixture.as_posix()
            if index > 1:
                # Exact card uniqueness remains independently enforced, so this
                # test isolates the real decoder through the publishable asset.
                card["path"] = f"assets/card_{index}.png"
        with patch.object(
            CardNewsPublishGate,
            "_check_final_cards",
            return_value=intake["final_cards"],
        ):
            result = self.gate.check(intake)
        self.assertTrue(result["asset_results"][0]["valid"])
        self.assertIn("hero-1", result["render_allowed_asset_ids"])

    def test_technical_fixture_never_counts_as_publish_approved_asset(self):
        fixture = {"asset_id": "fixture-1", "classification": "technical_fixture"}
        result = self.assert_blocked_with(card_news_intake(assets=[fixture]), "publishable_asset_missing")

        self.assertEqual(result["render_allowed_asset_ids"], [])
        self.assertFalse(result["asset_results"][0]["render_allowed"])

    def test_forged_rights_string_and_mismatched_evidence_fail_closed(self):
        intake = card_news_intake()
        intake["assets"][0]["rights_evidence"] = "approved by owner"
        self.assert_blocked_with(intake, "asset_rights_evidence_invalid")

    def test_arbitrary_repo_relative_reference_cannot_forge_rights_or_source(self):
        intake = card_news_intake()
        intake["assets"][0]["rights_evidence"]["reference"] = "approved-by-me"
        self.assert_blocked_with(intake, "asset_rights_evidence_invalid")

        intake = card_news_intake()
        intake["evidence"][0]["source_url"] = "trust-me.txt"
        self.assert_blocked_with(intake, "evidence_attestation_invalid")

    def test_publishable_asset_path_must_exist_be_file_and_valid_image(self):
        self.image_check.stop()
        intake = card_news_intake()
        intake["assets"][0]["asset_path"] = "missing.png"
        self.assert_blocked_with(intake, "asset_file_invalid")

        intake = card_news_intake()
        intake["assets"][0]["asset_path"] = "tests/fixtures/card_news_rights"
        self.assert_blocked_with(intake, "asset_file_invalid")

        intake = card_news_intake()
        intake["assets"][0]["asset_path"] = "tests/fixtures/card_news_rights/ownership_record.txt"
        self.assert_blocked_with(intake, "asset_file_invalid")

    def test_absolute_traversal_and_outside_repository_asset_paths_are_blocked(self):
        self.image_check.stop()
        outside_path = str((Path.cwd().parent / "outside.png").resolve())
        for unsafe_path in (
            str((Path.cwd() / "assets" / "hero.png").resolve()),
            "../outside.png",
            "assets/../../outside.png",
            outside_path,
        ):
            with self.subTest(asset_path=unsafe_path):
                intake = card_news_intake()
                intake["assets"][0]["asset_path"] = unsafe_path
                self.assert_blocked_with(intake, "asset_file_invalid")

    def test_evidence_must_attest_the_exact_asset(self):
        intake = card_news_intake()
        intake["evidence"][0]["asset_id"] = "different-asset"
        self.assert_blocked_with(intake, "evidence_asset_mismatch")

    def test_repository_technical_fixture_contract_is_never_publish_approved(self):
        spec = json.loads(Path("tests/fixtures/card_news_rights/technical_fixture_spec.json").read_text(encoding="utf-8"))
        ownership = Path("tests/fixtures/card_news_rights/ownership_record.txt").read_text(encoding="utf-8")
        self.assertEqual(spec["classification"], "technical_fixture_not_publish_approved")
        self.assertIn("Publish permission: NOT GRANTED", ownership)

        intake = card_news_intake(assets=[{
            "asset_id": "fixture-contract",
            "classification": spec["classification"],
        }])
        result = self.assert_blocked_with(
            intake, "technical_fixture_not_publish_approved"
        )
        self.assertTrue(
            result["pre_publish_attestation"]["technical_fixture_not_publish_approved"]
        )

    def test_relabeling_fixture_metadata_cannot_bypass_publish_evidence(self):
        self.image_check.stop()
        intake = card_news_intake()
        asset = intake["assets"][0]
        asset.update(
            asset_path="tests/fixtures/card_news_rights/technical_fixture_spec.json",
            rights_evidence={
                "type": "ownership_record",
                "reference": "tests/fixtures/card_news_rights/ownership_record.txt",
                "review_status": "approved",
                "reviewed_at": "2026-07-12T08:00:00+00:00",
                "asset_id": "hero-1",
            },
            attribution_required=True,
            attribution_text="",
        )
        result = self.gate.check(intake)
        codes = {item["code"] for item in result["blocking_reasons"]}
        self.assertIn("asset_file_invalid", codes)
        self.assertIn("asset_rights_evidence_invalid", codes)
        self.assertIn("asset_attribution_missing", codes)

    def test_string_boolean_fields_are_ambiguous_and_fail_closed(self):
        intake = card_news_intake()
        intake["assets"][0]["attribution_required"] = "yes"
        intake["campaign"].update(
            is_advertising="false",
            is_sponsored="false",
            has_affiliate_link="false",
            commercial_relationship_reviewed="true",
        )
        result = self.gate.check(intake)
        codes = {item["code"] for item in result["blocking_reasons"]}
        self.assertIn("asset_attribution_ambiguous", codes)
        self.assertIn("campaign_flags_ambiguous", codes)

        intake = card_news_intake()
        intake["assets"][0]["rights_evidence"].update(
            type="license_url", asset_id="different-asset"
        )
        self.assert_blocked_with(intake, "asset_rights_evidence_invalid")

    def test_ambiguous_or_future_rights_review_timestamp_fails_closed(self):
        intake = card_news_intake()
        intake["assets"][0]["rights_evidence"]["reviewed_at"] = "2026-07-12T08:00:00"
        self.assert_blocked_with(intake, "asset_rights_evidence_invalid")

        intake = card_news_intake()
        intake["assets"][0]["rights_evidence"]["reviewed_at"] = "2999-01-01T00:00:00+00:00"
        self.assert_blocked_with(intake, "asset_rights_evidence_invalid")

    def test_provenance_relevance_and_attribution_are_independent_blockers(self):
        intake = card_news_intake()
        asset = intake["assets"][0]
        asset.update(topic_relevant=False, topic_relevance_note="", attribution_required=True)
        result = self.gate.check(intake)

        codes = {item["code"] for item in result["blocking_reasons"]}
        self.assertIn("asset_topic_relevance_unverified", codes)
        self.assertIn("asset_attribution_missing", codes)
        self.assertEqual(result["render_allowed_asset_ids"], [])

    def test_evidence_forgery_and_timestamp_inversion_block_claim(self):
        intake = card_news_intake()
        intake["evidence"][0].update(
            source_url="https://user:secret@example.com/source",
            captured_at="2026-07-12T09:00:00+00:00",
            reviewed_at="2026-07-12T08:00:00+00:00",
            authenticity_status="self_asserted",
        )
        result = self.gate.check(intake)

        codes = {item["code"] for item in result["blocking_reasons"]}
        self.assertIn("evidence_attestation_invalid", codes)
        self.assertIn("claim_evidence_invalid", codes)
        self.assertNotIn("secret", json.dumps(result))

    def test_claim_must_link_only_to_valid_evidence(self):
        intake = card_news_intake()
        intake["claims"][0]["evidence_ids"] = ["missing-evidence"]
        self.assert_blocked_with(intake, "claim_evidence_invalid")

    def test_ad_and_affiliate_disclosures_require_text_and_verified_placement(self):
        intake = card_news_intake()
        intake["campaign"].update(is_advertising=True, has_affiliate_link=True)
        intake["disclosures"] = [
            {"type": "advertising", "text": "광고", "placement_verified": True},
            {"type": "affiliate", "text": "제휴 링크 포함", "placement_verified": False},
        ]
        result = self.gate.check(intake)

        missing = {item.get("disclosure_type") for item in result["blocking_reasons"]}
        self.assertIn("affiliate", missing)
        self.assertNotIn("advertising", missing)

    def test_incomplete_operator_review_remains_blocked_with_actionable_fields(self):
        intake = card_news_intake()
        intake["operator_checklist"]["checks"]["final_asset_reviewed"] = False
        result = self.assert_blocked_with(intake, "operator_checklist_incomplete")

        blocker = next(item for item in result["blocking_reasons"] if item["code"] == "operator_checklist_incomplete")
        self.assertEqual(blocker["fields"], ["final_asset_reviewed"])


if __name__ == "__main__":
    unittest.main()
