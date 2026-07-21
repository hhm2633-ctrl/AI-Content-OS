import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from modules.affiliate.affiliate_revenue_router import AffiliateRevenueRouter


NOW = datetime(2026, 7, 12, 9, 0, 0, tzinfo=timezone.utc)


def iso(delta=timedelta()):
    return (NOW + delta).isoformat()


def enrollment(**overrides):
    base = {
        "account_access_confirmed": True,
        "merchant_enrollment_confirmed": True,
        "product_enrollment_confirmed": True,
        "channel_allowed_confirmed": True,
        "evidence_checked_at": iso(timedelta(days=-1)),
    }
    base.update(overrides)
    return base


def program(**overrides):
    base = {
        "network_id": "linkprice",
        "program_id": "p1",
        "program_type": "product_affiliate",
        "merchant_id": "m1",
        "region": "KR",
        "currency": "KRW",
        "allowed_channels": ["blog", "instagram"],
        "restricted_categories": ["adult"],
        "attribution_window": "30d",
        "policy_version": "2026.07",
        "policy_evidence_url": "https://www.linkprice.com/affiliate/views/affiliate_marketing/plus_service_api.html",
        "policy_checked_at": iso(timedelta(days=-1)),
        "api_status": "confirmed",
        "enrollment": enrollment(),
    }
    base.update(overrides)
    return base


def offer(**overrides):
    base = {
        "offer_id": "o1",
        "network_id": "linkprice",
        "program_id": "p1",
        "merchant_id": "m1",
        "product_id": "prod1",
        "title": "Test Product",
        "canonical_url": "https://merchant.example.com/product/1",
        "image_url": "https://merchant.example.com/img/1.jpg",
        "category": "electronics",
        "region": "KR",
        "currency": "KRW",
        "price": 10000,
        "availability": "in_stock",
        "commission_type": "cps",
        "commission_value": 5.0,
        "valid_from": iso(timedelta(days=-1)),
        "valid_until": iso(timedelta(days=10)),
        "source_url": "https://merchant.example.com/product/1",
        "source_timestamp": iso(timedelta(minutes=-30)),
        "rights_status": "owned",
    }
    base.update(overrides)
    return base


def request(programs=None, offers=None, **overrides):
    base = {
        "request_id": "req-001",
        "channel": "blog",
        "region": "KR",
        "category": "electronics",
        "content_type": "review",
        "candidate_programs": programs if programs is not None else [program()],
        "candidate_offers": offers if offers is not None else [offer()],
        "current_time": iso(),
        "human_approval": True,
        "disclosure_policy_verified": True,
    }
    base.update(overrides)
    return base


def reasons_of(candidate):
    return {reason["code"] for reason in candidate["reasons"]}


class AffiliateRevenueRouterTests(unittest.TestCase):
    def setUp(self):
        self.router = AffiliateRevenueRouter()

    def _only_candidate(self, result):
        all_candidates = (
            result["eligible_candidates"] + result["manual_review_candidates"] + result["rejected_candidates"]
        )
        self.assertEqual(len(all_candidates), 1)
        return all_candidates[0]

    # ------------------------------------------------------------------
    # Positive path / priority program handling
    # ------------------------------------------------------------------

    def test_fully_valid_positive_path_is_eligible_and_publish_ready(self):
        result = self.router.route(request())

        self.assertEqual(len(result["eligible_candidates"]), 1)
        self.assertTrue(result["publish_ready"])
        self.assertEqual(len(result["tracking_link_requests"]), 1)
        self.assertEqual(len(result["disclosure_texts"]), 1)
        self.assertEqual(result["manual_actions"], [])
        self.assertFalse(result["network_used"])

    def test_linkprice_and_adpick_both_confirmed_candidates(self):
        programs = [
            program(network_id="linkprice", program_id="lp1"),
            program(network_id="adpick", program_id="ap1", policy_evidence_url="https://biz.adpick.co.kr/?ac=api&sub=guide"),
        ]
        offers = [
            offer(offer_id="o1", network_id="linkprice", program_id="lp1"),
            offer(offer_id="o2", network_id="adpick", program_id="ap1"),
        ]
        result = self.router.route(request(programs=programs, offers=offers))

        self.assertEqual(len(result["eligible_candidates"]), 2)
        network_ids = {c["network_id"] for c in result["eligible_candidates"]}
        self.assertEqual(network_ids, {"linkprice", "adpick"})

    def test_naver_shopping_connect_is_manual_only_with_correct_domain(self):
        naver_program = program(
            network_id="naver_shopping_connect", program_id="np1",
            policy_evidence_url="https://brandconnect.naver.com/service/policy/affiliate/creator",
        )
        naver_offer = offer(network_id="naver_shopping_connect", program_id="np1")
        result = self.router.route(request(programs=[naver_program], offers=[naver_offer]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("api_status_manual_only_capability_capped", reasons_of(candidate))

    def test_impact_is_capped_manual_only_with_correct_domain(self):
        impact_program = program(
            network_id="impact", program_id="ip1",
            policy_evidence_url="https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/tracking/tracking-links",
        )
        impact_offer = offer(network_id="impact", program_id="ip1")
        result = self.router.route(request(programs=[impact_program], offers=[impact_offer]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("api_status_manual_only_capability_capped", reasons_of(candidate))

    def test_tos_is_always_unknown_even_if_declared_confirmed(self):
        tos_program = program(network_id="tos", program_id="tp1", api_status="confirmed")
        tos_offer = offer(network_id="tos", program_id="tp1")
        result = self.router.route(request(programs=[tos_program], offers=[tos_offer]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("api_status_unknown", reasons_of(candidate))

    def test_lead_cpa_program_type_is_always_blocked(self):
        result = self.router.route(request(programs=[program(program_type="lead_cpa")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("lead_cpa_blocked", reasons_of(candidate))

    def test_declared_blocked_api_status_is_rejected(self):
        result = self.router.route(request(programs=[program(api_status="blocked")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("api_status_blocked", reasons_of(candidate))

    # ------------------------------------------------------------------
    # Back-reference matching (NO-GO fixes)
    # ------------------------------------------------------------------

    def test_offer_missing_back_reference_is_rejected(self):
        result = self.router.route(request(offers=[offer(network_id="", program_id="", merchant_id="")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("offer_missing_back_reference", reasons_of(candidate))

    def test_offer_with_mismatched_merchant_id_is_rejected(self):
        result = self.router.route(request(offers=[offer(merchant_id="wrong_merchant")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("no_matching_program_reference", reasons_of(candidate))

    def test_offer_with_mismatched_network_id_is_rejected(self):
        result = self.router.route(request(offers=[offer(network_id="adpick")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("no_matching_program_reference", reasons_of(candidate))

    def test_same_program_id_different_network_are_evaluated_independently(self):
        # Two programs share program_id "p1" but differ by network_id -- an
        # offer referencing (adpick, p1, m1) must pair with the adpick
        # program only, never be confused with the linkprice one.
        programs = [
            program(network_id="linkprice", program_id="p1", merchant_id="m1"),
            program(network_id="adpick", program_id="p1", merchant_id="m1", policy_evidence_url="https://biz.adpick.co.kr/?ac=api&sub=guide"),
        ]
        offers = [offer(network_id="adpick", program_id="p1", merchant_id="m1")]
        result = self.router.route(request(programs=programs, offers=offers))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["network_id"], "adpick")
        self.assertEqual(candidate["status"], "eligible")

    def test_no_full_cartesian_join_unrelated_program_produces_no_extra_candidate(self):
        programs = [
            program(network_id="linkprice", program_id="p1", merchant_id="m1"),
            program(network_id="adpick", program_id="p2", merchant_id="m2", policy_evidence_url="https://biz.adpick.co.kr/?ac=api&sub=guide"),
        ]
        offers = [offer(network_id="linkprice", program_id="p1", merchant_id="m1")]
        result = self.router.route(request(programs=programs, offers=offers))

        all_candidates = result["eligible_candidates"] + result["manual_review_candidates"] + result["rejected_candidates"]
        # Exactly one candidate (the one real back-reference match) -- not
        # 2 (one offer * two programs), which the old Cartesian join produced.
        self.assertEqual(len(all_candidates), 1)

    def test_candidate_id_includes_all_four_identifiers(self):
        result = self.router.route(request())
        candidate = self._only_candidate(result)
        self.assertEqual(candidate["candidate_id"], "linkprice:p1:m1:o1")

    # ------------------------------------------------------------------
    # Unregistered network / capability ceiling
    # ------------------------------------------------------------------

    def test_unknown_network_self_declared_confirmed_is_capped_to_unknown(self):
        unlisted_program = program(network_id="totally_unregistered_network", api_status="confirmed")
        unlisted_offer = offer(network_id="totally_unregistered_network")
        result = self.router.route(request(programs=[unlisted_program], offers=[unlisted_offer]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("api_status_unknown", reasons_of(candidate))

    # ------------------------------------------------------------------
    # Enrollment evidence (NO-GO fixes)
    # ------------------------------------------------------------------

    def test_enrollment_evidence_missing_is_manual_review_not_eligible(self):
        no_enrollment_program = program(enrollment=enrollment(
            account_access_confirmed=False, merchant_enrollment_confirmed=False,
            product_enrollment_confirmed=False, channel_allowed_confirmed=False,
            evidence_checked_at=None,
        ))
        result = self.router.route(request(programs=[no_enrollment_program]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("enrollment_evidence_incomplete", reasons_of(candidate))

    def test_enrollment_evidence_fake_type_is_treated_as_not_confirmed(self):
        fake_program = program(enrollment=enrollment(
            account_access_confirmed="true",  # string, not bool -- must not count
            merchant_enrollment_confirmed=1,   # int, not bool -- must not count
        ))
        result = self.router.route(request(programs=[fake_program]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("enrollment_evidence_incomplete", reasons_of(candidate))

    def test_rights_status_does_not_grant_program_eligibility(self):
        # rule 23: a valid image rights_status must never substitute for
        # missing enrollment evidence.
        no_enrollment_program = program(enrollment=enrollment(account_access_confirmed=False))
        rights_ok_offer = offer(rights_status="owned")
        result = self.router.route(request(programs=[no_enrollment_program], offers=[rights_ok_offer]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertTrue(candidate["image_usage_approved"])  # image usage itself is fine
        self.assertIn("enrollment_evidence_incomplete", reasons_of(candidate))  # but not eligible

    def test_api_status_existence_alone_is_not_eligible_without_enrollment(self):
        confirmed_no_enrollment = program(
            api_status="confirmed",
            enrollment=enrollment(account_access_confirmed=False, merchant_enrollment_confirmed=False,
                                   product_enrollment_confirmed=False, channel_allowed_confirmed=False),
        )
        result = self.router.route(request(programs=[confirmed_no_enrollment]))

        candidate = self._only_candidate(result)
        self.assertNotEqual(candidate["status"], "eligible")

    # ------------------------------------------------------------------
    # Policy metadata / freshness / future timestamps
    # ------------------------------------------------------------------

    def test_missing_policy_version_url_and_checked_at_is_manual_review(self):
        result = self.router.route(request(programs=[program(policy_version=None, policy_evidence_url=None, policy_checked_at=None)]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("policy_metadata_incomplete", reasons_of(candidate))

    def test_timezone_naive_policy_checked_at_is_manual_review(self):
        result = self.router.route(request(programs=[program(policy_checked_at="2026-07-11T09:00:00")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("policy_checked_at_invalid_timezone", reasons_of(candidate))

    def test_stale_policy_is_manual_review(self):
        result = self.router.route(request(programs=[program(policy_checked_at=iso(timedelta(days=-40)))]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("policy_stale", reasons_of(candidate))

    def test_future_policy_checked_at_is_rejected(self):
        result = self.router.route(request(programs=[program(policy_checked_at=iso(timedelta(days=1)))]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("policy_checked_at_future", reasons_of(candidate))

    def test_stale_price_is_manual_review(self):
        result = self.router.route(request(offers=[offer(source_timestamp=iso(timedelta(hours=-7)), price=9999, availability="")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("price_stale", reasons_of(candidate))

    def test_stale_availability_is_manual_review(self):
        result = self.router.route(request(offers=[offer(source_timestamp=iso(timedelta(hours=-2)), price=None, commission_value=None)]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("availability_stale", reasons_of(candidate))

    def test_stale_commission_is_manual_review(self):
        result = self.router.route(request(offers=[offer(source_timestamp=iso(timedelta(hours=-25)), price=None, availability="")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("commission_stale", reasons_of(candidate))

    def test_future_source_timestamp_is_rejected(self):
        result = self.router.route(request(offers=[offer(source_timestamp=iso(timedelta(hours=1)))]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("source_timestamp_future", reasons_of(candidate))

    # ------------------------------------------------------------------
    # Offer validity window
    # ------------------------------------------------------------------

    def test_expired_offer_is_rejected(self):
        result = self.router.route(request(offers=[offer(valid_until=iso(timedelta(days=-1)))]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("offer_expired", reasons_of(candidate))

    def test_future_start_offer_is_rejected(self):
        result = self.router.route(request(offers=[offer(valid_from=iso(timedelta(days=1)))]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("offer_not_yet_valid", reasons_of(candidate))

    # ------------------------------------------------------------------
    # Region / currency / channel / category
    # ------------------------------------------------------------------

    def test_program_region_mismatch_is_rejected(self):
        result = self.router.route(request(programs=[program(region="US")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("region_mismatch", reasons_of(candidate))

    def test_region_case_normalization_matches(self):
        result = self.router.route(request(
            programs=[program(region="kr")],
            offers=[offer(region="Kr")],
            region="kR",
        ))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "eligible")

    def test_currency_mismatch_is_rejected(self):
        result = self.router.route(request(offers=[offer(currency="USD")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("currency_mismatch", reasons_of(candidate))

    def test_channel_not_allowed_is_rejected(self):
        result = self.router.route(request(programs=[program(allowed_channels=["youtube"])]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("channel_not_allowed", reasons_of(candidate))

    def test_restricted_category_is_rejected(self):
        result = self.router.route(request(programs=[program(restricted_categories=["electronics"])]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("restricted_category", reasons_of(candidate))

    def test_offer_region_mismatch_is_rejected(self):
        result = self.router.route(request(offers=[offer(region="US")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("offer_region_mismatch", reasons_of(candidate))

    def test_offer_category_mismatch_is_rejected(self):
        result = self.router.route(request(offers=[offer(category="fashion")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("offer_category_mismatch", reasons_of(candidate))

    # ------------------------------------------------------------------
    # Availability / rights / URL safety / policy domain
    # ------------------------------------------------------------------

    def test_availability_unknown_is_manual_review(self):
        result = self.router.route(request(offers=[offer(availability="", price=None, commission_value=None)]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("availability_unknown", reasons_of(candidate))

    def test_out_of_stock_offer_is_rejected(self):
        result = self.router.route(request(offers=[offer(availability="out_of_stock")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("offer_out_of_stock", reasons_of(candidate))

    def test_missing_rights_status_blocks_image_usage_and_is_manual_review(self):
        result = self.router.route(request(offers=[offer(rights_status="")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "manual_review")
        self.assertIn("image_rights_unconfirmed", reasons_of(candidate))
        self.assertFalse(candidate["image_usage_approved"])

    def test_url_with_embedded_credentials_is_rejected(self):
        result = self.router.route(request(offers=[offer(canonical_url="https://user:pass@merchant.example.com/1")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("unsafe_canonical_url", reasons_of(candidate))

    def test_localhost_url_is_rejected(self):
        result = self.router.route(request(offers=[offer(canonical_url="http://localhost/product/1")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("unsafe_canonical_url", reasons_of(candidate))

    def test_private_ip_url_is_rejected(self):
        result = self.router.route(request(offers=[offer(canonical_url="http://192.168.1.10/product/1")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("unsafe_canonical_url", reasons_of(candidate))

    def test_unsafe_policy_evidence_url_with_credentials_is_rejected(self):
        result = self.router.route(request(programs=[program(policy_evidence_url="https://user:pass@evil.example.com/policy")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("unsafe_policy_evidence_url", reasons_of(candidate))

    def test_policy_evidence_url_domain_mismatch_is_rejected(self):
        result = self.router.route(request(programs=[program(policy_evidence_url="https://not-linkprice-at-all.com/policy")]))

        candidate = self._only_candidate(result)
        self.assertEqual(candidate["status"], "rejected")
        self.assertIn("policy_evidence_domain_mismatch", reasons_of(candidate))

    def test_policy_receipt_masks_unsafe_url(self):
        result = self.router.route(request(programs=[program(policy_evidence_url="https://user:pass@evil.example.com/policy")]))

        receipt = result["policy_receipts"][0]
        self.assertEqual(receipt["policy_evidence_url"], "***REDACTED_UNSAFE_URL***")

    # ------------------------------------------------------------------
    # Commission value attacks
    # ------------------------------------------------------------------

    def test_commission_value_string_type_attack_is_sanitized_to_none(self):
        result = self.router.route(request(offers=[offer(commission_value="100abc; DROP TABLE")]))

        candidate = self._only_candidate(result)
        self.assertIsNone(candidate["commission_value"])

    def test_commission_value_dict_type_attack_is_sanitized_to_none(self):
        result = self.router.route(request(offers=[offer(commission_value={"$gt": 0})]))

        candidate = self._only_candidate(result)
        self.assertIsNone(candidate["commission_value"])

    def test_negative_commission_is_sanitized_to_none(self):
        result = self.router.route(request(offers=[offer(commission_value=-5.0)]))

        candidate = self._only_candidate(result)
        self.assertIsNone(candidate["commission_value"])

    def test_nan_commission_is_sanitized_to_none(self):
        result = self.router.route(request(offers=[offer(commission_value=float("nan"))]))

        candidate = self._only_candidate(result)
        self.assertIsNone(candidate["commission_value"])

    def test_infinite_commission_is_sanitized_to_none(self):
        result = self.router.route(request(offers=[offer(commission_value=float("inf"))]))

        candidate = self._only_candidate(result)
        self.assertIsNone(candidate["commission_value"])

    # ------------------------------------------------------------------
    # request_id secret/JWT/path handling (NO-GO fix)
    # ------------------------------------------------------------------

    def test_ordinary_request_id_is_echoed_unchanged(self):
        result = self.router.route(request(request_id="req-001"))
        self.assertEqual(result["request_id"], "req-001")

    def test_secret_like_request_id_is_replaced_with_opaque_id(self):
        secret_id = "req_api_key_" + "a" * 40
        result = self.router.route(request(request_id=secret_id))

        self.assertNotEqual(result["request_id"], secret_id)
        self.assertTrue(result["request_id"].startswith("opaque:"))
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(secret_id, serialized)

    def test_jwt_shaped_request_id_is_replaced_with_opaque_id(self):
        jwt_like = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = self.router.route(request(request_id=jwt_like))

        self.assertTrue(result["request_id"].startswith("opaque:"))

    def test_path_traversal_request_id_is_replaced_with_opaque_id(self):
        traversal_id = "../../etc/passwd"
        result = self.router.route(request(request_id=traversal_id))

        self.assertTrue(result["request_id"].startswith("opaque:"))

    def test_opaque_request_id_is_deterministic(self):
        secret_id = "token_" + "b" * 40
        result_one = self.router.route(request(request_id=secret_id))
        result_two = self.router.route(request(request_id=secret_id))
        self.assertEqual(result_one["request_id"], result_two["request_id"])

    # ------------------------------------------------------------------
    # Manual-review candidates never get tracking artifacts (NO-GO fixes)
    # ------------------------------------------------------------------

    def test_manual_review_candidate_has_no_tracking_link_request(self):
        no_enrollment_program = program(enrollment=enrollment(account_access_confirmed=False))
        result = self.router.route(request(programs=[no_enrollment_program]))

        self.assertEqual(result["tracking_link_requests"], [])
        self.assertEqual(result["disclosure_texts"], [])

    def test_manual_review_candidate_has_manual_action_entry(self):
        no_enrollment_program = program(enrollment=enrollment(account_access_confirmed=False))
        result = self.router.route(request(programs=[no_enrollment_program]))

        self.assertEqual(len(result["manual_actions"]), 1)
        action = result["manual_actions"][0]
        self.assertEqual(action["candidate_id"], "linkprice:p1:m1:o1")
        self.assertIn("reasons", action)

    def test_eligible_candidate_still_has_tracking_link_request(self):
        result = self.router.route(request())
        self.assertEqual(len(result["tracking_link_requests"]), 1)

    def test_rejected_candidate_has_no_tracking_request_or_manual_action(self):
        result = self.router.route(request(programs=[program(program_type="lead_cpa")]))

        self.assertEqual(result["tracking_link_requests"], [])
        self.assertEqual(result["manual_actions"], [])

    # ------------------------------------------------------------------
    # publish_ready gating (NO-GO fixes)
    # ------------------------------------------------------------------

    def test_disclosure_texts_empty_and_publish_not_ready_when_no_eligible_candidate(self):
        result = self.router.route(request(programs=[program(program_type="lead_cpa")]))

        self.assertEqual(result["disclosure_texts"], [])
        self.assertFalse(result["publish_ready"])

    def test_publish_ready_requires_disclosure_policy_verified(self):
        result = self.router.route(request(disclosure_policy_verified=False))

        self.assertEqual(len(result["eligible_candidates"]), 1)
        self.assertFalse(result["publish_ready"])

    def test_publish_ready_requires_human_approval(self):
        result = self.router.route(request(human_approval=False))

        self.assertEqual(len(result["eligible_candidates"]), 1)
        self.assertFalse(result["publish_ready"])

    def test_disclosure_policy_verified_alone_without_human_approval_not_enough(self):
        result = self.router.route(request(disclosure_policy_verified=True, human_approval=False))
        self.assertFalse(result["publish_ready"])

    def test_both_disclosure_and_approval_true_with_eligible_candidate_is_publish_ready(self):
        result = self.router.route(request(disclosure_policy_verified=True, human_approval=True))
        self.assertTrue(result["publish_ready"])

    # ------------------------------------------------------------------
    # Duplicates / input limits (contract blockers, NO-GO fixes)
    # ------------------------------------------------------------------

    def test_duplicate_program_id_is_contract_blocker(self):
        programs = [program(), program()]
        result = self.router.route(request(programs=programs))

        self.assertEqual(result["status"], "blocked")
        all_candidates = result["eligible_candidates"] + result["manual_review_candidates"] + result["rejected_candidates"]
        self.assertEqual(all_candidates, [])
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("affiliate_contract_invalid", codes)

    def test_duplicate_offer_id_is_contract_blocker(self):
        offers = [offer(), offer()]
        result = self.router.route(request(offers=offers))

        self.assertEqual(result["status"], "blocked")
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("affiliate_contract_invalid", codes)

    def test_same_network_program_different_merchant_is_not_a_duplicate(self):
        programs = [program(merchant_id="m1"), program(merchant_id="m2")]
        result = self.router.route(request(programs=programs, offers=[offer(merchant_id="m2")]))

        self.assertEqual(result["status"], "routed")

    def test_max_programs_exceeded_is_contract_blocker(self):
        programs = [program(program_id=f"p{i}") for i in range(60)]
        result = self.router.route(request(programs=programs))

        self.assertEqual(result["status"], "blocked")
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("affiliate_contract_invalid", codes)

    def test_max_offers_exceeded_is_contract_blocker(self):
        offers = [offer(offer_id=f"o{i}") for i in range(250)]
        result = self.router.route(request(offers=offers))

        self.assertEqual(result["status"], "blocked")
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("affiliate_contract_invalid", codes)

    # ------------------------------------------------------------------
    # Robustness / secrets / determinism
    # ------------------------------------------------------------------

    def test_empty_candidates_returns_neutral_result(self):
        result = self.router.route(request(programs=[], offers=[]))

        self.assertEqual(result["eligible_candidates"], [])
        self.assertEqual(result["rejected_candidates"], [])
        self.assertEqual(result["manual_review_candidates"], [])
        self.assertFalse(result["publish_ready"])
        self.assertEqual(result["status"], "routed")

    def test_all_candidates_blocked(self):
        programs = [program(program_type="lead_cpa"), program(network_id="tos", program_id="p2")]
        offers = [offer(program_id="p1"), offer(offer_id="o2", network_id="tos", program_id="p2")]
        result = self.router.route(request(programs=programs, offers=offers))

        self.assertEqual(result["eligible_candidates"], [])
        self.assertEqual(result["manual_review_candidates"], [])
        self.assertEqual(len(result["rejected_candidates"]), 2)
        self.assertFalse(result["publish_ready"])

    def test_some_candidates_are_manual_review_others_eligible(self):
        programs = [
            program(network_id="linkprice", program_id="p1"),
            program(network_id="naver_shopping_connect", program_id="p2", policy_evidence_url="https://brandconnect.naver.com/service/policy/affiliate/creator"),
        ]
        offers = [
            offer(offer_id="o1", network_id="linkprice", program_id="p1"),
            offer(offer_id="o2", network_id="naver_shopping_connect", program_id="p2"),
        ]
        result = self.router.route(request(programs=programs, offers=offers))

        self.assertEqual(len(result["eligible_candidates"]), 1)
        self.assertEqual(len(result["manual_review_candidates"]), 1)

    def test_tie_break_sort_is_deterministic(self):
        programs = [
            program(network_id="adpick", program_id="p_b", policy_evidence_url="https://biz.adpick.co.kr/?ac=api&sub=guide"),
            program(network_id="linkprice", program_id="p_a"),
        ]
        offers = [
            offer(offer_id="o1", network_id="adpick", program_id="p_b", commission_value=5.0),
            offer(offer_id="o2", network_id="linkprice", program_id="p_a", commission_value=5.0),
        ]

        result_one = self.router.route(request(programs=programs, offers=offers))
        result_two = self.router.route(request(programs=list(reversed(programs)), offers=list(reversed(offers))))

        ids_one = [c["candidate_id"] for c in result_one["eligible_candidates"]]
        ids_two = [c["candidate_id"] for c in result_two["eligible_candidates"]]
        self.assertEqual(ids_one, ids_two)
        network_ids_one = [c["network_id"] for c in result_one["eligible_candidates"]]
        self.assertEqual(network_ids_one, sorted(network_ids_one))

    def test_result_is_independent_of_input_list_order(self):
        programs = [
            program(network_id="linkprice", program_id="p1"),
            program(network_id="adpick", program_id="p2", policy_evidence_url="https://biz.adpick.co.kr/?ac=api&sub=guide"),
        ]
        offers = [
            offer(offer_id="o1", network_id="linkprice", program_id="p1"),
            offer(offer_id="o2", network_id="adpick", program_id="p2"),
        ]

        result_forward = self.router.route(request(programs=programs, offers=offers))
        result_reversed = self.router.route(request(programs=list(reversed(programs)), offers=list(reversed(offers))))

        def candidate_ids(result):
            return sorted(c["candidate_id"] for c in result["eligible_candidates"])

        self.assertEqual(candidate_ids(result_forward), candidate_ids(result_reversed))

    def test_input_objects_are_not_mutated(self):
        req = request()
        snapshot = copy.deepcopy(req)

        self.router.route(req)

        self.assertEqual(req, snapshot)

    def test_result_is_json_serializable(self):
        result = self.router.route(request())

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIsInstance(serialized, str)
        self.assertEqual(json.loads(serialized)["schema_version"], result["schema_version"])

    def test_internal_error_returns_fail_closed_blocked_result(self):
        with patch(
            "modules.affiliate.affiliate_revenue_router.normalize_routing_request",
            side_effect=RuntimeError("boom"),
        ):
            result = self.router.route(request())

        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["publish_ready"])
        codes = {reason["code"] for reason in result["blocking_reasons"]}
        self.assertIn("affiliate_router_internal_error", codes)

    def test_raw_exception_text_with_secret_never_leaks_into_result(self):
        secret_token = "s" * 40
        with patch(
            "modules.affiliate.affiliate_revenue_router.normalize_routing_request",
            side_effect=RuntimeError(f"failed with api_key={secret_token}"),
        ):
            result = self.router.route(request())

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(secret_token, serialized)

    def test_network_used_is_always_false(self):
        result = self.router.route(request())
        self.assertFalse(result["network_used"])

        blocked_result = self.router.route(request(programs=[program(program_type="lead_cpa")]))
        self.assertFalse(blocked_result["network_used"])

    def test_no_real_tracking_url_is_ever_generated(self):
        result = self.router.route(request())

        tracking_request = result["tracking_link_requests"][0]
        self.assertEqual(tracking_request["destination_url"], "https://merchant.example.com/product/1")
        self.assertFalse(tracking_request["tracking_link_generated"])
        self.assertNotIn("affiliate_url", tracking_request)
        self.assertNotIn("tracking_url", tracking_request)
        self.assertNotIn("deep_link", tracking_request)

    def test_deterministic_semantic_result_for_same_input(self):
        req_one = request()
        req_two = copy.deepcopy(req_one)

        result_one = self.router.route(req_one)
        result_two = self.router.route(req_two)

        for entry in result_one["tracking_link_requests"]:
            entry.pop("requested_at", None)
        for entry in result_two["tracking_link_requests"]:
            entry.pop("requested_at", None)

        self.assertEqual(result_one["eligible_candidates"], result_two["eligible_candidates"])
        self.assertEqual(result_one["rejected_candidates"], result_two["rejected_candidates"])
        self.assertEqual(result_one["manual_review_candidates"], result_two["manual_review_candidates"])
        self.assertEqual(result_one["tracking_link_requests"], result_two["tracking_link_requests"])
        self.assertEqual(result_one["publish_ready"], result_two["publish_ready"])


if __name__ == "__main__":
    unittest.main()
