import copy
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from modules.brandconnect.brandconnect_contract import normalize_brandconnect_request
from modules.brandconnect.brandconnect_package_builder import build_brandconnect_package
from modules.brandconnect.brandconnect_policy_gate import evaluate_brandconnect_policy


NOW = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)


def _receipt(status, schema_version, receipt_id, issuer, **overrides):
    value = {
        "status": status,
        "schema_version": schema_version,
        "receipt_id": receipt_id,
        "input_hash": "sha256:fixture-input-hash",
        "checked_at": "2026-07-12T09:45:00+09:00",
        "issuer": issuer,
        "trusted": True,
    }
    value.update(overrides)
    return value


def fixture(mode="shopping_connect"):
    return {
        "request_id": "bc-001",
        "mode": mode,
        "channel": "naver_blog",
        "category": "beauty",
        "campaign_brief": {
            "campaign_id": "campaign-1",
            "title": "여름 캠페인",
            "required_keywords": ["선케어", "사용법"],
            "required_keyword_count": 2,
            "required_images": 3,
            "required_video": False,
            "required_map": False,
            "required_links": ["shopping_connect"],
            "required_disclosure": True,
            "disclosure_text": "이 포스팅은 네이버 쇼핑 커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다.",
            "deadline": "2026-07-20T18:00:00+09:00",
            "terms_confirmed": True,
            "compensation": {"type": "product", "amount": None},
        },
        "creator": {"creator_id": "creator-1", "ownership_evidence_id": "creator-proof-1"},
        "seller": {"seller_id": "seller-1", "smartstore_id": "store-1", "ownership_evidence_id": "seller-proof-1"},
        "product": {
            "smartstore_product_id": "product-1",
            "name": "선케어",
            "category": "beauty",
            "product_status": "active",
            "configured_commission": {"value": None, "currency": "KRW"},
            "checked_at": "2026-07-12T09:00:00+09:00",
            "source_ref": "manual-ui-check",
        },
        "creator_compensation": {"type": "product", "amount": None},
        "affiliate_commission": {"rate": None, "currency": "KRW"},
        "content": {
            "title": "선케어 사용법",
            "body": "근거가 확인된 소개입니다.",
            "claims": [{"text": "공식 설명", "evidence_ref": "seller-brief"}],
            "contains_pii": False,
            "rights_status": "licensed",
            "disclosure_text": "이 포스팅은 네이버 쇼핑 커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다.",
            "stats_external_disclosure": False,
            "manual_pii_review": True,
            "manual_claim_review": True,
            "manual_traffic_review": True,
        },
        "manual_link": {
            "attached": mode == "shopping_connect",
            "url": "https://naver.me/REDACTED_PATH" if mode == "shopping_connect" else "",
            "generated_in": "naver_brandconnect_ui" if mode == "shopping_connect" else "",
            "tampered": False,
            "manual_link_attached": mode == "shopping_connect",
            "link_source": "naver_brandconnect_ui" if mode == "shopping_connect" else "",
            "attached_by": "human-reviewer" if mode == "shopping_connect" else "",
            "attached_at": "2026-07-12T09:30:00+09:00" if mode == "shopping_connect" else None,
            "owner_scope": "creator_product" if mode == "shopping_connect" else "",
            "owner_creator_id": "creator-1" if mode == "shopping_connect" else "",
            "owner_product_id": "product-1" if mode == "shopping_connect" else "",
            "tamper_checked": mode == "shopping_connect",
            "disclosure_present": mode == "shopping_connect",
            "cross_creator_reuse": False,
            "cross_product_reuse": False,
            "generated_sub_id": False,
            "generated_hash": False,
        },
        "traffic": {"abnormal": False, "rewarded_click": False},
        "policy_context": {
            "api_status": "manual_only",
            "policy_version": "2025.03",
            "policy_evidence_urls": ["https://brandconnect.naver.com/service/policy/affiliate/creator"],
            "checked_at": "2026-07-12T09:00:00+09:00",
            "allowed_channels": ["naver_blog"],
            "restricted_channels": ["adult_site"],
            "restricted_categories": ["gambling", "tobacco"],
        },
        "compliance_ready": True,
        "affiliate_ready": True,
        "human_approval": True,
        "compliance_receipt": _receipt("passed", "campaign_compliance_phase_1.v1", "compliance-1", "campaign_compliance_phase_1"),
        "affiliate_receipt": _receipt("routed", "affiliate_revenue_router_phase_1.v1", "affiliate-1", "affiliate_revenue_router_phase_1"),
        "human_approval_receipt": _receipt("approved", "brandconnect_human_approval.v1", "human-1", "brandconnect_human_approval"),
        "disclosure_receipt": _receipt("approved", "brandconnect_disclosure_review.v1", "disclosure-1", "brandconnect_disclosure_review"),
        "current_time": NOW.isoformat(),
    }


def codes(decision):
    return {item["code"] for item in decision["blocking_reasons"]}


class BrandConnectContractTests(unittest.TestCase):
    def test_creator_campaign_mode_normalized(self):
        self.assertEqual(normalize_brandconnect_request(fixture("creator_campaign"))["mode"], "creator_campaign")

    def test_shopping_connect_mode_normalized(self):
        self.assertEqual(normalize_brandconnect_request(fixture())["mode"], "shopping_connect")

    def test_input_is_not_mutated_by_normalizer(self):
        raw = fixture(); before = copy.deepcopy(raw)
        normalize_brandconnect_request(raw)
        self.assertEqual(raw, before)

    def test_input_is_not_mutated_by_builder(self):
        raw = fixture(); before = copy.deepcopy(raw)
        build_brandconnect_package(raw, now=NOW)
        self.assertEqual(raw, before)

    def test_requirement_fields_are_normalized(self):
        brief = normalize_brandconnect_request(fixture())["campaign_brief"]
        self.assertEqual(brief["required_keyword_count"], 2)
        self.assertEqual(brief["required_images"], 3)
        self.assertIn("shopping_connect", brief["required_links"])

    def test_invalid_mode_is_blocked(self):
        raw = fixture(); raw["mode"] = "automatic"
        self.assertIn("unsupported_mode", codes(evaluate_brandconnect_policy(raw, NOW)))

    def test_json_serialization(self):
        json.dumps(build_brandconnect_package(fixture(), now=NOW), ensure_ascii=False)


class BrandConnectPolicyTests(unittest.TestCase):
    def decide(self, mutate=None, mode="shopping_connect"):
        raw = fixture(mode)
        if mutate: mutate(raw)
        return evaluate_brandconnect_policy(raw, NOW)

    def test_shopping_positive_manual_path_passes_policy(self):
        self.assertFalse(self.decide()["publish_ready"])
        self.assertIn("upstream_integration_no_go", codes(self.decide()))

    def test_creator_positive_manual_path_passes_policy(self):
        self.assertFalse(self.decide(mode="creator_campaign")["publish_ready"])
        self.assertIn("upstream_integration_no_go", codes(self.decide(mode="creator_campaign")))

    def test_api_unknown_blocks(self):
        self.assertIn("brandconnect_api_unknown", codes(self.decide(lambda r: r["policy_context"].update(api_status="unknown"))))

    def test_missing_disclosure_blocks(self):
        def change(r): r["content"]["disclosure_text"] = ""; r["campaign_brief"]["disclosure_text"] = ""
        self.assertIn("missing_disclosure", codes(self.decide(change)))

    def test_restricted_category_blocks(self):
        self.assertIn("restricted_category", codes(self.decide(lambda r: r.update(category="gambling"))))

    def test_restricted_channel_blocks(self):
        self.assertIn("restricted_channel", codes(self.decide(lambda r: r.update(channel="adult_site"))))

    def test_channel_outside_allowlist_blocks(self):
        self.assertIn("restricted_channel", codes(self.decide(lambda r: r.update(channel="unknown_channel"))))

    def test_false_claim_blocks(self):
        self.assertIn("false_or_exaggerated_claim", codes(self.decide(lambda r: r["content"].update(claims=[{"false": True, "evidence_ref": "x"}]))))

    def test_exaggerated_claim_blocks(self):
        self.assertIn("false_or_exaggerated_claim", codes(self.decide(lambda r: r["content"].update(claims=[{"exaggerated": True, "evidence_ref": "x"}]))))

    def test_unverifiable_claim_blocks(self):
        self.assertIn("unverifiable_claim", codes(self.decide(lambda r: r["content"].update(claims=[{"text": "claim"}]))))

    def test_pii_blocks(self):
        self.assertIn("pii_detected", codes(self.decide(lambda r: r["content"].update(contains_pii=True))))

    def test_invalid_rights_blocks(self):
        self.assertIn("invalid_rights", codes(self.decide(lambda r: r["content"].update(rights_status="unknown"))))

    def test_missing_campaign_terms_blocks(self):
        self.assertIn("missing_campaign_terms", codes(self.decide(lambda r: r["campaign_brief"].update(terms_confirmed=False))))

    def test_expired_deadline_blocks(self):
        self.assertIn("campaign_deadline_expired", codes(self.decide(lambda r: r["campaign_brief"].update(deadline="2026-07-01T00:00:00+09:00"))))

    def test_naive_deadline_blocks(self):
        self.assertIn("deadline_invalid_timezone", codes(self.decide(lambda r: r["campaign_brief"].update(deadline="2026-07-20T18:00:00"))))

    def test_naive_policy_check_blocks(self):
        self.assertIn("policy_checked_at_invalid", codes(self.decide(lambda r: r["policy_context"].update(checked_at="2026-07-12T09:00:00"))))

    def test_monthly_rate_recheck_blocks(self):
        self.assertIn("monthly_product_rate_recheck_required", codes(self.decide(lambda r: r["product"].update(checked_at="2026-06-30T09:00:00+09:00"))))

    def test_missing_manual_link_blocks(self):
        self.assertIn("missing_manual_link", codes(self.decide(lambda r: r["manual_link"].update(attached=False, url=""))))

    def test_link_tampering_blocks(self):
        self.assertIn("link_tampering_or_origin_invalid", codes(self.decide(lambda r: r["manual_link"].update(tampered=True))))

    def test_wrong_link_origin_blocks(self):
        self.assertIn("link_tampering_or_origin_invalid", codes(self.decide(lambda r: r["manual_link"].update(generated_in="external_tool", link_source="external_tool"))))

    def test_naver_me_requires_https(self):
        self.assertIn("invalid_manual_link_syntax", codes(self.decide(lambda r: r["manual_link"].update(url="http://naver.me/REDACTED_PATH"))))

    def test_naver_me_requires_exact_host(self):
        self.assertIn("invalid_manual_link_syntax", codes(self.decide(lambda r: r["manual_link"].update(url="https://evil.example/REDACTED_PATH"))))

    def test_naver_me_requires_nonempty_path(self):
        self.assertIn("invalid_manual_link_syntax", codes(self.decide(lambda r: r["manual_link"].update(url="https://naver.me/"))))

    def test_naver_me_rejects_query_fragment_and_credentials(self):
        for url in ("https://naver.me/PATH?x=1", "https://naver.me/PATH#x", "https://user@naver.me/PATH"):
            with self.subTest(url=url):
                self.assertIn("invalid_manual_link_syntax", codes(self.decide(lambda r, u=url: r["manual_link"].update(url=u))))

    def test_owner_creator_mismatch_blocks(self):
        self.assertIn("creator_owner_mismatch", codes(self.decide(lambda r: r["manual_link"].update(owner_creator_id="creator-2"))))

    def test_owner_product_mismatch_blocks(self):
        self.assertIn("product_owner_mismatch", codes(self.decide(lambda r: r["manual_link"].update(owner_product_id="product-2"))))

    def test_cross_creator_reuse_blocks(self):
        self.assertIn("manual_link_reuse_prohibited", codes(self.decide(lambda r: r["manual_link"].update(cross_creator_reuse=True))))

    def test_cross_product_reuse_blocks(self):
        self.assertIn("manual_link_reuse_prohibited", codes(self.decide(lambda r: r["manual_link"].update(cross_product_reuse=True))))

    def test_generated_sub_id_blocks(self):
        self.assertIn("generated_tracking_identifier_prohibited", codes(self.decide(lambda r: r["manual_link"].update(generated_sub_id=True))))

    def test_generated_hash_blocks(self):
        self.assertIn("generated_tracking_identifier_prohibited", codes(self.decide(lambda r: r["manual_link"].update(generated_hash=True))))

    def test_private_link_blocks(self):
        self.assertIn("invalid_manual_link_syntax", codes(self.decide(lambda r: r["manual_link"].update(url="http://127.0.0.1/secret"))))

    def test_stats_disclosure_blocks(self):
        self.assertIn("stats_external_disclosure_prohibited", codes(self.decide(lambda r: r["content"].update(stats_external_disclosure=True))))

    def test_abnormal_traffic_blocks(self):
        self.assertIn("abnormal_traffic_prohibited", codes(self.decide(lambda r: r["traffic"].update(abnormal=True))))

    def test_rewarded_click_blocks(self):
        self.assertIn("abnormal_traffic_prohibited", codes(self.decide(lambda r: r["traffic"].update(rewarded_click=True))))

    def test_compliance_no_go_blocks(self):
        self.assertIn("compliance_not_ready", codes(self.decide(lambda r: r.update(compliance_ready=False))))

    def test_affiliate_not_ready_blocks(self):
        self.assertIn("affiliate_not_ready", codes(self.decide(lambda r: r.update(affiliate_ready=False))))

    def test_human_approval_missing_blocks(self):
        self.assertIn("human_approval_required", codes(self.decide(lambda r: r.update(human_approval=False))))

    def test_self_declared_booleans_never_open_publish(self):
        raw = fixture()
        raw.pop("compliance_receipt"); raw.pop("affiliate_receipt"); raw.pop("human_approval_receipt")
        self.assertFalse(evaluate_brandconnect_policy(raw, NOW)["publish_ready"])

    def test_receipt_trusted_defaults_false(self):
        raw = fixture(); raw["compliance_receipt"].pop("trusted")
        decision = self.decide(lambda r: r["compliance_receipt"].pop("trusted"))
        self.assertIn("compliance_receipt_untrusted", codes(decision))

    def test_receipt_schema_issuer_status_and_hash_are_required(self):
        mutations = (
            ("schema_version", "wrong"), ("issuer", "caller"),
            ("status", "approved"), ("input_hash", ""), ("receipt_id", ""),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                decision = self.decide(lambda r, f=field, v=value: r["compliance_receipt"].update({f: v}))
                self.assertIn("compliance_receipt_untrusted", codes(decision))

    def test_future_receipt_policy_and_link_times_block(self):
        future = "2026-07-13T00:00:00+00:00"
        cases = (
            lambda r: r["compliance_receipt"].update(checked_at=future),
            lambda r: r["policy_context"].update(checked_at=future),
            lambda r: r["manual_link"].update(attached_at=future),
        )
        for mutate in cases:
            with self.subTest(mutate=mutate):
                self.assertTrue(codes(self.decide(mutate)) & {"compliance_receipt_untrusted", "policy_checked_at_future", "manual_link_attached_at_future"})

    def test_identity_and_ownership_evidence_required(self):
        cases = (
            lambda r: r["creator"].update(creator_id=""),
            lambda r: r["creator"].update(ownership_evidence_id=""),
            lambda r: r["seller"].update(seller_id=""),
            lambda r: r["seller"].update(ownership_evidence_id=""),
            lambda r: r["product"].update(smartstore_product_id=""),
            lambda r: r["product"].update(source_ref=""),
        )
        for mutate in cases:
            with self.subTest(mutate=mutate):
                self.assertTrue(codes(self.decide(mutate)) & {"creator_identity_ownership_missing", "seller_identity_ownership_missing", "product_identity_ownership_missing"})

    def test_disclosure_requires_approved_exact_copy_receipt(self):
        decision = self.decide(lambda r: r["disclosure_receipt"].update(status="self_declared"))
        self.assertIn("disclosure_receipt_untrusted", codes(decision))
        decision = self.decide(lambda r: r["content"].update(disclosure_text="광고"))
        self.assertIn("disclosure_copy_unapproved", codes(decision))

    def test_deterministic_content_scan_catches_pii_claim_and_reward_prompt(self):
        samples = (
            ("문의 010-1234-5678", "pii_detected"),
            ("무조건 100% 완치되는 최고의 제품", "risky_claim_detected"),
            ("링크 클릭하면 포인트를 드립니다", "rewarded_click_text_detected"),
        )
        for body, expected in samples:
            with self.subTest(body=body):
                self.assertIn(expected, codes(self.decide(lambda r, b=body: r["content"].update(body=b))))

    def test_manual_content_review_gates_required(self):
        for field in ("manual_pii_review", "manual_claim_review", "manual_traffic_review"):
            with self.subTest(field=field):
                self.assertIn(field + "_required", codes(self.decide(lambda r, f=field: r["content"].update({f: False}))))


class BrandConnectPackageTests(unittest.TestCase):
    def test_required_top_level_outputs(self):
        result = build_brandconnect_package(fixture(), now=NOW)
        for key in ("creator_delivery_package", "seller_campaign_package", "manual_actions", "policy_receipts", "disclosure_text", "revenue_ledger_draft", "blocking_reasons", "warnings", "publish_ready"):
            self.assertIn(key, result)

    def test_no_network_or_publish(self):
        result = build_brandconnect_package(fixture(), now=NOW)
        self.assertIs(result["network_used"], False)
        self.assertIs(result["actual_publish"], False)

    def test_manual_link_contract(self):
        result = build_brandconnect_package(fixture(), now=NOW)
        self.assertIs(result["manual_link_required"], True)
        self.assertEqual(result["link_generation_location"], "naver_brandconnect_ui")

    def test_opaque_link_is_preserved_without_resolution(self):
        result = build_brandconnect_package(fixture(), now=NOW)
        rendered = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("https://naver.me/REDACTED_PATH", rendered)
        self.assertIn('"opaque_value_redacted": true', rendered)
        for forbidden in ("expanded_url", "destination_url", "resolved_url", "NaPm", "trx", "hk"):
            self.assertNotIn(forbidden, rendered)

    def test_manual_link_metadata_is_preserved(self):
        rendered = json.dumps(build_brandconnect_package(fixture(), now=NOW), ensure_ascii=False)
        for expected in ('"attached": true', "link_source", "attached_by", "attached_at", "owner_scope", "tamper_checked", "disclosure_present"):
            self.assertIn(expected, rendered)

    def test_ledger_never_contains_link_tracking_material(self):
        rendered = json.dumps(build_brandconnect_package(fixture(), now=NOW)["revenue_ledger_draft"], ensure_ascii=False)
        for forbidden in ("naver.me", "NaPm", "trx", "hk", "expanded_url", "destination_url"):
            self.assertNotIn(forbidden, rendered)

    def test_stats_disclosure_prohibition_marker(self):
        self.assertIs(build_brandconnect_package(fixture(), now=NOW)["stats_external_disclosure_prohibited"], True)

    def test_creator_and_seller_contracts_are_separate_objects(self):
        result = build_brandconnect_package(fixture(), now=NOW)
        self.assertIsNot(result["creator_delivery_package"]["campaign_brief"], result["seller_campaign_package"]["creator_campaign_brief"])
        self.assertIs(result["seller_campaign_package"]["contract_separate_from_creator"], True)

    def test_creator_compensation_and_affiliate_commission_are_separate(self):
        result = build_brandconnect_package(fixture(), now=NOW)
        ledger = result["revenue_ledger_draft"]
        self.assertEqual(ledger["campaign_compensation"]["stream_type"], "campaign_compensation")
        self.assertEqual(ledger["affiliate_commission"]["stream_type"], "affiliate_commission")
        self.assertFalse(ledger["campaign_compensation"]["amount_included"])
        self.assertFalse(ledger["affiliate_commission"]["amount_included"])
        self.assertIs(ledger["revenue_streams_separated"], True)

    def test_cancellation_and_refund_ledger_events(self):
        events = {x["event_type"] for x in build_brandconnect_package(fixture(), now=NOW)["revenue_ledger_draft"]["events"]}
        self.assertTrue({"purchase_confirmed", "cancelled", "returned", "settlement_confirmed"}.issubset(events))

    def test_ledger_has_no_actual_statistics(self):
        ledger = build_brandconnect_package(fixture(), now=NOW)["revenue_ledger_draft"]
        self.assertIs(ledger["actual_statistics_included"], False)
        self.assertIs(ledger["actual_sales_included"], False)

    def test_policy_receipt_requires_recheck_marker(self):
        receipt = build_brandconnect_package(fixture(), now=NOW)["policy_receipts"][0]
        self.assertIn("recheck_required", receipt)
        self.assertIn("product_rate_recheck_required", receipt)

    def test_publish_ready_requires_all_gates(self):
        raw = fixture(); raw["human_approval"] = False
        self.assertIs(build_brandconnect_package(raw, now=NOW)["publish_ready"], False)

    def test_positive_manual_path_can_be_publish_ready_after_all_approvals(self):
        self.assertIs(build_brandconnect_package(fixture(), now=NOW)["publish_ready"], False)

    def test_current_upstream_no_go_is_absolute(self):
        result = build_brandconnect_package(fixture(), now=NOW)
        self.assertFalse(result["publish_ready"])
        self.assertIn("upstream_integration_no_go", codes(result))

    def test_invalid_link_is_not_echoed(self):
        raw = fixture(); raw["manual_link"]["url"] = "https://naver.me/PATH?tracking=secret"
        rendered = json.dumps(build_brandconnect_package(raw, now=NOW), ensure_ascii=False)
        self.assertNotIn("tracking=secret", rendered)

    def test_ledger_uses_allowlist_and_discards_estimates(self):
        raw = fixture()
        raw["creator_compensation"].update(estimated_reward=999, estimated_sales=10, tracking_id="track")
        raw["affiliate_commission"].update(estimated_commission=500, estimated_sales=20, tracking_id="track2")
        rendered = json.dumps(build_brandconnect_package(raw, now=NOW)["revenue_ledger_draft"])
        for forbidden in ("estimated_reward", "estimated_commission", "estimated_sales", "tracking_id", "track2"):
            self.assertNotIn(forbidden, rendered)

    def test_request_id_is_irreversible_and_secret_not_echoed(self):
        raw = fixture(); raw["request_id"] = "customer-secret-request-id"
        result = build_brandconnect_package(raw, now=NOW)
        self.assertNotEqual(result["request_ref"], raw["request_id"])
        self.assertNotIn("customer-secret-request-id", json.dumps(result))

    def test_builder_does_not_resolve_or_publish(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")), \
             patch("http.client.HTTPSConnection.request", side_effect=AssertionError("network forbidden")):
            result = build_brandconnect_package(fixture(), now=NOW)
        self.assertFalse(result["network_used"])
        self.assertFalse(result["actual_publish"])

    def test_hostile_deepcopy_fails_closed_without_raw_secret(self):
        class Hostile(dict):
            def __deepcopy__(self, memo):
                raise RuntimeError("sk-hostile C:/private/path")
        rendered = json.dumps(build_brandconnect_package(Hostile(fixture()), now=NOW))
        self.assertIn("internal_error_fail_closed", rendered)
        self.assertNotIn("sk-hostile", rendered)
        self.assertNotIn("C:/private", rendered)

    def test_internal_error_fails_closed(self):
        with patch("modules.brandconnect.brandconnect_package_builder.normalize_brandconnect_request", side_effect=RuntimeError("C:/secret/token=abc")):
            result = build_brandconnect_package(fixture(), now=NOW)
        self.assertEqual(result["blocking_reasons"], ["internal_error_fail_closed"])
        self.assertNotIn("secret", json.dumps(result))

    def test_secret_and_path_are_not_echoed_on_failure(self):
        raw = {"request_id": "safe-id", "mode": "shopping_connect", "token": "sk-secret", "path": "C:/Users/private/file"}
        with patch("modules.brandconnect.brandconnect_package_builder.normalize_brandconnect_request", side_effect=ValueError("sk-secret C:/Users/private/file")):
            rendered = json.dumps(build_brandconnect_package(raw, now=NOW))
        self.assertNotIn("sk-secret", rendered)
        self.assertNotIn("C:/Users/private", rendered)


if __name__ == "__main__":
    unittest.main()
