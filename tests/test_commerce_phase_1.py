import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import tempfile
from unittest.mock import MagicMock, patch

from modules.commerce import CommerceModule
from modules.commerce.approval_gate import ApprovalGate
from modules.commerce.audit_logger import AuditLogger
from modules.commerce.commerce_storage import CommerceStorage
from modules.commerce.contract_loader import load_contract
from modules.commerce.schema_validator import validate_payload


NOW = datetime.now(timezone.utc)


def iso(delta=timedelta()):
    return (NOW + delta).isoformat()


def source(source_id="merchant", *, rights="merchant_authorized"):
    return {
        "source_id": source_id,
        "source_type": "merchant_record",
        "source_name": "merchant product master",
        "source_locator": f"record:{source_id}",
        "retrieved_at": iso(timedelta(minutes=-5)),
        "rights_or_permission": rights,
    }


def item(field_id, value, *, source_ids=None, volatile=False, expires_at=None, method="merchant_input"):
    result = {
        "field_id": field_id,
        "value": value,
        "source_ids": list(source_ids or ["merchant"]),
        "verified_at": iso(timedelta(minutes=-5)),
        "verification_method": method,
        "volatile": volatile,
    }
    if expires_at is not None:
        result["expires_at"] = expires_at
    return result


def request():
    return {
        "request_id": "order-42",
        "requested_at": iso(),
        "target_platforms": ["smartstore", "coupang"],
        "product": {
            "product_id": item("product_id", "SKU-42"),
            "brand": item("brand", "테스트브랜드"),
            "manufacturer": item("manufacturer", "테스트 제조사"),
            "model_name": item("model_name", "T-500"),
            "category": item("category", "텀블러"),
            "product_name": item("product_name", "테스트 텀블러"),
            "seller": item("seller", "테스트 판매자"),
            "country_of_origin": item("country_of_origin", "대한민국"),
            "facts": [item("feature.insulation", "이중 구조")],
            "options": [item("option.color", {"name": "색상", "values": ["검정"], "sku": "SKU-42-B"})],
            "specifications": [item("spec.capacity", {"name": "용량", "value": 500, "unit": "ml"})],
            "usage": [item("usage.1", "세척 후 사용")],
            "cautions": [item("caution.1", "화기 주의")],
            "notice_information": {
                "material": item("notice.material", "스테인리스"),
                "size": item("notice.size", "500ml"),
                "warranty": item("notice.warranty", "구매처 확인"),
                "certification": item("notice.certification", "해당 없음"),
            },
        },
        "commercial_facts": {"price": None, "discount": None, "stock": None, "shipping": None, "benefits": []},
        "claims": [],
        "reviews": [],
        "sales_metrics": [],
        "sources": [source()],
        "freshness_policy": {"default_max_age_seconds": 86400, "volatile_max_age_seconds": 3600},
        "search_seed_keywords": ["텀블러"],
        "learned_data": {"knowledge_enabled": False, "brand_dna_enabled": False, "content_patterns_enabled": False},
    }


def reason_codes(result):
    return {entry["code"] for entry in result["blocked_reasons"]}


def blocked_fields(result):
    return {entry["field"] for entry in result["blocked_reasons"]}


class TestCommercePhaseOneTruthGates(unittest.TestCase):
    def run_request(self, payload=None):
        return CommerceModule().run(payload or request(), persist=False)

    def test_arbitrary_source_string_cannot_validate_efficacy_or_fda_certification(self):
        payload = request()
        payload["claims"] = [{
            "field_id": "claim.efficacy", "value": "질병 치료", "source": "아무 문자열",
            "verified_at": iso(), "verification_method": "merchant_input", "volatile": False,
        }]
        payload["product"]["notice_information"]["certification"] = {
            "field_id": "notice.certification", "value": "FDA 승인", "source": "FDA",
            "verified_at": iso(), "verification_method": "merchant_input", "volatile": False,
        }
        result = self.run_request(payload)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("claim.efficacy", blocked_fields(result))
        self.assertIn("notice.certification", blocked_fields(result))
        rendered = str(result["platform_packages"])
        self.assertNotIn("질병 치료", rendered)
        self.assertNotIn("FDA 승인", rendered)

    def test_claim_language_is_blocked_from_every_customer_visible_entry_path(self):
        cases = (
            ("generic_fact", lambda payload: payload["product"]["facts"].append(
                item("feature.claim", "질병 치료")
            ), "질병 치료"),
            ("merchant_claim", lambda payload: payload["claims"].append(
                item("claim.certification", "FDA approved", method="merchant_input")
            ), "FDA approved"),
            ("product_name", lambda payload: payload["product"].update({
                "product_name": item("product_name", "FDA 승인 질병 치료 90% OFF")
            }), "FDA 승인 질병 치료 90% OFF"),
        )
        for name, mutate, forbidden in cases:
            with self.subTest(name=name):
                payload = request()
                mutate(payload)
                result = self.run_request(payload)
                self.assertEqual(result["status"], "blocked")
                self.assertIn("unsupported_claim", reason_codes(result))
                self.assertNotIn(forbidden, str(result["platform_packages"]))

    def test_empty_unsupported_and_malformed_platform_requests_fail_closed(self):
        for target_platforms in ([], ["amazon"], "smartstore", [None], ["smartstore", 7]):
            with self.subTest(target_platforms=target_platforms):
                payload = request()
                payload["target_platforms"] = target_platforms
                result = self.run_request(payload)
                self.assertEqual(result["status"], "blocked")
                self.assertTrue(reason_codes(result) & {
                    "invalid_target_platforms", "unsupported_platform", "malformed_input"
                })
                self.assertEqual(result["platform_packages"], {})

    def test_future_source_and_fact_timestamps_fail_closed(self):
        cases = []
        future_source = request()
        future_source["sources"][0]["retrieved_at"] = iso(timedelta(days=1))
        cases.append(future_source)
        future_fact = request()
        future_fact["product"]["facts"][0]["verified_at"] = iso(timedelta(days=1))
        cases.append(future_fact)
        for payload in cases:
            with self.subTest(payload=payload):
                result = self.run_request(payload)
                self.assertEqual(result["status"], "blocked")
                self.assertIn("future_verification_time", reason_codes(result))

    def test_freshness_policy_has_a_safe_upper_bound_and_never_overflows(self):
        for max_age in (978307200, 10**100):
            with self.subTest(max_age=max_age):
                payload = request()
                payload["freshness_policy"]["default_max_age_seconds"] = max_age
                payload["freshness_policy"]["volatile_max_age_seconds"] = max_age
                result = self.run_request(payload)
                self.assertEqual(result["status"], "blocked")
                self.assertIn("invalid_freshness_policy", reason_codes(result))

    def test_duplicate_source_ids_fail_closed_instead_of_last_write_wins(self):
        payload = request()
        duplicate = source("merchant")
        duplicate["source_locator"] = "record:conflicting-merchant"
        payload["sources"].append(duplicate)
        result = self.run_request(payload)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("duplicate_source_id", reason_codes(result))

    def test_secret_bearing_source_ids_are_rejected_without_echoing_secrets(self):
        secret_id = "Bearer eyJhbGciOiJIUzI1NiJ9.secret.signature"
        payload = request()
        payload["sources"] = [source(secret_id)]
        for product_item in (
            payload["product"]["product_id"], payload["product"]["brand"],
            payload["product"]["manufacturer"], payload["product"]["model_name"],
            payload["product"]["category"], payload["product"]["product_name"],
            payload["product"]["seller"], payload["product"]["country_of_origin"],
            *payload["product"]["facts"], *payload["product"]["options"],
            *payload["product"]["specifications"], *payload["product"]["usage"],
            *payload["product"]["cautions"],
            *payload["product"]["notice_information"].values(),
        ):
            product_item["source_ids"] = [secret_id]
        result = self.run_request(payload)
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("unsafe_source_id", reason_codes(result))
        self.assertNotIn(secret_id, serialized)
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", serialized)

    def test_malformed_claims_and_platform_scopes_return_structured_blockers(self):
        cases = []
        malformed_claim = request()
        malformed_claim["claims"] = ["bad"]
        cases.append(malformed_claim)
        malformed_scope = request()
        malformed_scope["product"]["facts"][0]["platforms"] = None
        cases.append(malformed_scope)
        for payload in cases:
            with self.subTest(payload=payload):
                result = self.run_request(payload)
                self.assertEqual(result["status"], "blocked")
                self.assertIn("malformed_input", reason_codes(result))

    def test_source_id_must_resolve_to_a_complete_source_record(self):
        payload = request()
        payload["product"]["facts"][0]["source_ids"] = ["does-not-exist"]
        result = self.run_request(payload)
        self.assertIn("missing_source", reason_codes(result))
        self.assertIn("feature.insulation", blocked_fields(result))

    def test_verification_method_and_time_are_required(self):
        payload = request()
        del payload["product"]["usage"][0]["verification_method"]
        del payload["product"]["cautions"][0]["verified_at"]
        result = self.run_request(payload)
        self.assertIn("missing_verification_method", reason_codes(result))
        self.assertIn("missing_verification_time", reason_codes(result))

    def test_volatile_fact_requires_bounded_policy_and_must_be_fresh(self):
        cases = []
        no_policy = request()
        no_policy["freshness_policy"] = {}
        no_policy["commercial_facts"]["price"] = item("price", {"amount": 10000, "currency": "KRW"}, volatile=True)
        cases.append(no_policy)
        stale = request()
        stale["commercial_facts"]["stock"] = item("stock", 3, volatile=True, expires_at=iso(timedelta(seconds=-1)))
        cases.append(stale)
        over_age = request()
        over_age["commercial_facts"]["discount"] = item("discount", "10%", volatile=True, expires_at=iso(timedelta(hours=1)))
        over_age["commercial_facts"]["discount"]["verified_at"] = iso(timedelta(hours=-2))
        cases.append(over_age)
        for payload in cases:
            with self.subTest(field=next(k for k, v in payload["commercial_facts"].items() if v)):
                result = self.run_request(payload)
                self.assertEqual(result["status"], "blocked")
                self.assertIn("stale_volatile_fact", reason_codes(result))

    def test_conflicting_source_values_are_not_silently_selected(self):
        payload = request()
        payload["sources"].append(source("manufacturer"))
        payload["product"]["facts"] = [
            item("feature.capacity", "500ml", source_ids=["merchant"]),
            item("feature.capacity", "450ml", source_ids=["manufacturer"]),
        ]
        result = self.run_request(payload)
        self.assertIn("conflicting_sources", reason_codes(result))
        self.assertNotIn("500ml", str(result["platform_packages"]))
        self.assertNotIn("450ml", str(result["platform_packages"]))

    def test_claim_review_and_certification_require_documented_rights(self):
        payload = request()
        payload["sources"] = [source(rights="")]
        payload["claims"] = [item("claim.efficacy", "질병 치료")]
        payload["reviews"] = [dict(item("review.1", "정말 좋아요"), authenticity_confirmed=False,
                                   contains_pii=True, attribution="")]
        payload["product"]["notice_information"]["certification"] = item("notice.certification", "FDA 승인")
        result = self.run_request(payload)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("missing_source_rights", reason_codes(result))
        customer_copy = str(result["platform_packages"])
        for forbidden in ("질병 치료", "정말 좋아요", "FDA 승인"):
            self.assertNotIn(forbidden, customer_copy)

    def test_missing_and_block_entries_follow_canonical_structure(self):
        payload = request()
        payload["product"]["seller"] = None
        result = self.run_request(payload)
        self.assertTrue(result["missing_fields"])
        self.assertTrue(result["blocked_reasons"])
        self.assertTrue({"field", "platforms", "required", "reason", "required_action"}.issubset(result["missing_fields"][0]))
        self.assertTrue({"code", "field", "platforms", "severity", "message", "required_action"}.issubset(result["blocked_reasons"][0]))

    def test_brand_none_and_blank_source_backed_values_are_hard_blocked(self):
        for brand in (None, item("brand", ""), item("brand", " \t\n")):
            with self.subTest(brand=brand):
                payload = request()
                payload["product"]["brand"] = brand
                result = self.run_request(payload)
                self.assertEqual(result["status"], "blocked")
                reasons = [x for x in result["blocked_reasons"] if x["field"] in {"brand", "product.brand"}]
                self.assertTrue(reasons)
                self.assertTrue(all(x["code"] == "missing_required_field" for x in reasons))
                self.assertTrue(all(set(x["platforms"]) == {"smartstore", "coupang"} for x in reasons))

    def test_product_name_none_and_blank_are_structured_blockers(self):
        for product_name in (None, item("product_name", ""), item("product_name", "\u3000")):
            with self.subTest(product_name=product_name):
                payload = request()
                payload["product"]["product_name"] = product_name
                result = self.run_request(payload)
                self.assertEqual(result["status"], "blocked")
                self.assertTrue(any(x["field"] in {"product_name", "product.product_name"}
                                    for x in result["missing_fields"]))
                self.assertTrue(any(x["code"] == "missing_required_field"
                                    and x["field"] in {"product_name", "product.product_name"}
                                    for x in result["blocked_reasons"]))

    def test_missing_seller_is_scoped_only_to_requested_platform(self):
        for platform in ("smartstore", "coupang"):
            with self.subTest(platform=platform):
                payload = request()
                payload["target_platforms"] = [platform]
                payload["product"]["seller"] = None
                result = self.run_request(payload)
                seller_reasons = [x for x in result["blocked_reasons"] if x["field"] == "product.seller"]
                self.assertTrue(seller_reasons)
                self.assertTrue(all(x["platforms"] == [platform] for x in seller_reasons))
                self.assertEqual(set(result["platform_packages"]), {platform})

    def test_each_detail_section_exposes_status_and_source_ids(self):
        detail = self.run_request()["detail_page"]
        expected = {"headline", "problem", "benefits", "features", "specifications", "usage", "cautions", "faq", "cta"}
        self.assertEqual(set(detail), expected)
        for section in detail.values():
            self.assertIn(section["status"], {"ready", "partial", "blocked"})
            self.assertIsInstance(section["source_ids"], list)
            self.assertTrue("items" in section or "text" in section)

    def test_platform_packages_are_separately_formatted_and_gated(self):
        result = self.run_request()
        smartstore = result["platform_packages"]["smartstore"]
        coupang = result["platform_packages"]["coupang"]
        for package in (smartstore, coupang):
            self.assertIn("status", package)
            self.assertIn("missing_fields", package)
            self.assertIn("blocked_reasons", package)
            self.assertIn("notice_information", package)
            self.assertIn("manual_upload_text_path", package)
        self.assertNotEqual(smartstore["detail_description"], coupang["detail_description"])
        self.assertNotEqual(smartstore["manual_upload_text_path"], coupang["manual_upload_text_path"])

    def test_learned_metadata_records_application_fallback_and_no_writes(self):
        payload = request()
        payload["learned_data"] = {"knowledge_enabled": True, "brand_dna_enabled": True, "content_patterns_enabled": True}
        knowledge = MagicMock()
        knowledge.get_top_hooks.return_value = []
        knowledge.get_top_ctas.side_effect = RuntimeError("corrupt snapshot")
        brand = MagicMock()
        brand.get_dominant_preferences.return_value = {"tone": "calm"}
        result = CommerceModule(knowledge_interface=knowledge, brand_dna_interface=brand).run(payload, persist=False)
        metadata = result["learned_data_metadata"]
        self.assertEqual(metadata["application_mode"], "read_only")
        self.assertFalse(metadata["writes_performed"])
        self.assertTrue(metadata["knowledge"]["fallback_used"])
        self.assertTrue(metadata["knowledge"]["reason"])
        self.assertTrue(metadata["brand_dna"]["available"])
        self.assertEqual(metadata["brand_dna"]["applied_preferences"], [])
        self.assertTrue(metadata["brand_dna"]["reason"])

    def test_learned_metadata_never_claims_unconsumed_input_was_applied(self):
        payload = request()
        payload["learned_data"] = {
            "knowledge_enabled": True,
            "brand_dna_enabled": True,
            "content_patterns_enabled": True,
            "knowledge": {"unused-record": {"text": "not consumed"}},
            "brand_dna": {"unused-preference": "not consumed"},
            "content_patterns": {"unused-pattern": "not consumed"},
        }
        result = self.run_request(payload)
        metadata = result["learned_data_metadata"]
        self.assertEqual(metadata["knowledge"]["applied_record_ids"], [])
        self.assertEqual(metadata["brand_dna"]["applied_preferences"], [])
        self.assertEqual(metadata["content_patterns"]["applied_patterns"], [])
        self.assertFalse(metadata["writes_performed"])

    def test_storage_failure_is_safe_and_structured(self):
        storage = MagicMock(spec=CommerceStorage)
        storage.save.side_effect = OSError("atomic replace failed")
        result = CommerceModule(storage=storage).run(request())
        self.assertEqual(result["status"], "blocked")
        self.assertIn("storage_write_failed", reason_codes(result))
        self.assertEqual(result["output_paths"], [])

    def test_capability_boundary_remains_manual_only(self):
        result = self.run_request()
        self.assertEqual(result["upload_mode"], "manual_only")
        self.assertFalse(result["auto_upload_performed"])
        self.assertEqual(result["phase_2_gate"]["status"], "not_approved")

    def test_unverified_claim_language_is_removed_from_search_seed_keywords(self):
        payload = request()
        payload["search_seed_keywords"] = [
            "판매량 1위", "재고마감", "50% 할인", "질병 치료", "FDA 승인", "안전한 텀블러"
        ]
        result = self.run_request(payload)
        rendered = str(result["platform_packages"])
        for claim in ("판매량 1위", "재고마감", "50% 할인", "질병 치료", "FDA 승인"):
            self.assertNotIn(claim, rendered)
        self.assertIn("unsupported_claim", reason_codes(result))

    def test_unicode_whitespace_punctuation_and_synonym_claim_evasion_is_blocked(self):
        attacks = [
            "판매\u200b량 １위", "누 적 판 매", "베스트-셀러", "랭 킹", "rank.ing",
            "50％ 할-인", "특　가", "dis count", "재\u200d고 있음", "품절-임박", "in stock",
            "질 병 치 료", "완-치", "효　능", "c.u.r.e", "FDA 인 증", "공식-승인", "certi fied",
        ]
        for attack in attacks:
            with self.subTest(attack=attack):
                payload = request()
                payload["search_seed_keywords"] = [attack, "텀블러"]
                result = self.run_request(payload)
                rendered = str(result["platform_packages"])
                self.assertNotIn(attack, rendered)
                self.assertIn("unsupported_claim", reason_codes(result))

    def test_semantic_ranking_sales_and_discount_claim_evasion_is_blocked(self):
        attacks = [
            "BEST SELLER", "No. 1", "NUMBER ONE", "90% OFF", "TOP PICK",
            "판매 일등", "가장 많이 팔린", "best selling", "top rated",
            "number 1", "ninety percent off", "top seller", "가장많이팔렸음",
            "bEsT   SeLlEr", "Ｎｏ．　１", "number-one", "90％\u200bOFF", "top.pick",
            "판 매　일 등", "가장-많이-팔린",
            "ＢＥＳＴ　ＳＥＬＬＩＮＧ", "Top-RaTeD", "Ｎｕｍｂｅｒ　１",
            "ninety.percent-OFF", "ＴＯＰ\u200bＳＥＬＬＥＲ", "가 장 많 이 팔 렸 음",
        ]
        for attack in attacks:
            with self.subTest(attack=attack):
                payload = request()
                payload["search_seed_keywords"] = [attack, "텀블러"]
                result = self.run_request(payload)
                rendered = str(result["platform_packages"])
                self.assertNotIn(attack, rendered)
                self.assertIn("unsupported_claim", reason_codes(result))

    def test_benign_search_keywords_remain_ready_and_are_emitted(self):
        benign = [
            "텀블러", "보온 텀블러", "스테인리스 물병",
            "office chair", "top-loading bottle", "model number 1 label",
            "rated voltage 220V", "seller information", "sale color",
            "상단 투입형 물병", "모델 번호 1 라벨", "판매자 정보",
        ]
        for keyword in benign:
            with self.subTest(keyword=keyword):
                payload = request()
                payload["search_seed_keywords"] = [keyword]
                result = self.run_request(payload)
                self.assertEqual(result["status"], "ready_for_manual_upload")
                self.assertNotIn("unsupported_claim", reason_codes(result))
                smartstore_keywords = result["platform_packages"]["smartstore"]["search_keywords"]
                coupang_keywords = result["platform_packages"]["coupang"]["search_keywords"]
                self.assertIn(keyword, smartstore_keywords)
                self.assertIn(keyword, coupang_keywords)

    def test_fully_verified_input_is_ready_for_both_platforms(self):
        result = self.run_request(request())
        self.assertEqual(result["status"], "ready_for_manual_upload")
        self.assertEqual(result["platform_packages"]["smartstore"]["status"], "ready_for_manual_upload")
        self.assertEqual(result["platform_packages"]["coupang"]["status"], "ready_for_manual_upload")
        self.assertEqual(result["missing_fields"], [])

    def test_category_required_by_only_one_platform_blocks_only_that_package(self):
        payload = request()
        payload["product"]["category"]["platforms"] = ["smartstore"]
        result = self.run_request(payload)
        self.assertEqual(result["platform_packages"]["smartstore"]["status"], "ready_for_manual_upload")
        self.assertEqual(result["platform_packages"]["coupang"]["status"], "blocked")
        self.assertIn("product.category", {x["field"] for x in result["platform_packages"]["coupang"]["missing_fields"]})

    def test_options_required_by_only_one_platform_blocks_only_that_package(self):
        payload = request()
        payload["product"]["options"][0]["platforms"] = ["coupang"]
        result = self.run_request(payload)
        self.assertEqual(result["platform_packages"]["smartstore"]["status"], "blocked")
        self.assertEqual(result["platform_packages"]["coupang"]["status"], "ready_for_manual_upload")
        self.assertIn("product.options", {x["field"] for x in result["platform_packages"]["smartstore"]["missing_fields"]})

    def test_identity_facts_are_hard_gated_by_requested_platforms(self):
        for field in ("brand", "product_name", "seller"):
            with self.subTest(field=field):
                payload = request()
                payload["product"][field]["platforms"] = ["smartstore"]
                result = self.run_request(payload)
                smartstore = result["platform_packages"]["smartstore"]
                coupang = result["platform_packages"]["coupang"]
                self.assertEqual(smartstore["status"], "ready_for_manual_upload")
                self.assertEqual(coupang["status"], "blocked")
                expected_field = f"product.{field}"
                self.assertIn(expected_field, {x["field"] for x in coupang["missing_fields"]})
                identity_reasons = [
                    x for x in coupang["blocked_reasons"]
                    if x["field"] == expected_field
                ]
                self.assertTrue(identity_reasons)
                self.assertTrue(all(x["platforms"] == ["coupang"] for x in identity_reasons))

    def test_safe_ordinary_request_id_is_stable_in_all_metadata_paths(self):
        result = self.run_request(request())
        self.assertEqual(result["request_id"], "order-42")
        for package in result["platform_packages"].values():
            self.assertIn("storage/commerce/order-42/", package["manual_upload_text_path"].replace("\\", "/"))

    def test_secret_or_path_bearing_request_id_becomes_irreversible_opaque_id(self):
        raw_ids = (
            "../../customer/secret-order-42",
            r"C:\\Users\\merchant\\token_sk-live-DO-NOT-LEAK",
            "Bearer eyJhbGciOiJIUzI1NiJ9.payload.signature",
        )
        for raw_id in raw_ids:
            with self.subTest(raw_id=raw_id):
                payload = request()
                payload["request_id"] = raw_id
                result = self.run_request(payload)
                serialized = json.dumps(result, ensure_ascii=False)
                self.assertNotIn(raw_id, serialized)
                for secret_fragment in ("secret-order-42", "sk-live-DO-NOT-LEAK", "eyJhbGciOiJIUzI1NiJ9"):
                    self.assertNotIn(secret_fragment, serialized)
                self.assertRegex(result["request_id"], r"^commerce_[0-9a-f]{24,64}$")
                for package in result["platform_packages"].values():
                    self.assertIn(f"/{result['request_id']}/", package["manual_upload_text_path"].replace("\\", "/"))

    def test_every_source_requires_rights_and_merchant_authorized_is_allowed(self):
        valid = self.run_request(request())
        self.assertEqual(valid["status"], "ready_for_manual_upload")
        payload = request()
        del payload["sources"][0]["rights_or_permission"]
        invalid = self.run_request(payload)
        self.assertEqual(invalid["status"], "blocked")
        self.assertIn("missing_source_rights", reason_codes(invalid))

    def test_storage_error_redacts_paths_and_secrets(self):
        storage = MagicMock(spec=CommerceStorage)
        storage.save.side_effect = OSError(r"C:\\Users\\merchant\\secret\\sk-live-DO-NOT-LEAK")
        result = CommerceModule(storage=storage).run(request())
        self.assertEqual(result["status"], "blocked")
        error = result.get("storage_error", "")
        self.assertNotIn("C:\\Users", error)
        self.assertNotIn("sk-live-DO-NOT-LEAK", error)


class TestCommerceApprovalBinding(unittest.TestCase):
    def approval_config(self, **overrides):
        config = {
            "phase_2_cto_gate_satisfied": True,
            "approved_capabilities": {"listing_creation": True},
            "approval_identity": {
                "approval_id": "approval-42",
                "platform": "coupang",
                "product_id": "SKU-42",
                "payload_hash": "sha256:payload-42",
                "issued_at": iso(timedelta(minutes=-5)),
                "expires_at": iso(timedelta(minutes=5)),
            },
        }
        for key, value in overrides.items():
            if key in config["approval_identity"]:
                config["approval_identity"][key] = value
            else:
                config[key] = value
        return config

    def check(self, config, **target):
        gate = ApprovalGate()
        with patch.object(gate, "load", return_value=deepcopy(config)):
            return gate.check(
                "listing_creation",
                platform=target.get("platform", "coupang"),
                product_id=target.get("product_id", "SKU-42"),
                payload_hash=target.get("payload_hash", "sha256:payload-42"),
                approval_id=target.get("approval_id", "approval-42"),
                now=NOW,
            )

    def test_non_boolean_gate_or_scope_fails_closed(self):
        cases = (
            self.approval_config(phase_2_cto_gate_satisfied="false"),
            self.approval_config(approved_capabilities={"listing_creation": "true"}),
        )
        for config in cases:
            with self.subTest(config=config):
                decision = self.check(config)
                self.assertFalse(decision["approved"])
                self.assertEqual(decision["reason_code"], "invalid_approval_boolean")

    def test_approval_is_bound_to_platform_product_and_payload(self):
        mismatch_cases = (
            {"platform": "smartstore"},
            {"product_id": "SKU-OTHER"},
            {"payload_hash": "sha256:other-payload"},
            {"approval_id": "approval-other"},
        )
        for target in mismatch_cases:
            with self.subTest(target=target):
                decision = self.check(self.approval_config(), **target)
                self.assertFalse(decision["approved"])
                self.assertEqual(decision["reason_code"], "approval_target_mismatch")

        gate = ApprovalGate()
        config = self.approval_config()
        with patch.object(gate, "load", return_value=deepcopy(config)):
            missing_target = gate.check("listing_creation")
        self.assertFalse(missing_target["approved"])
        self.assertEqual(missing_target["reason_code"], "missing_approval_target")

    def test_expired_approval_fails_closed(self):
        decision = self.check(self.approval_config(expires_at=iso(timedelta(seconds=-1))))
        self.assertFalse(decision["approved"])
        self.assertEqual(decision["reason_code"], "approval_expired")

    def test_exact_unexpired_scoped_approval_is_allowed(self):
        decision = self.check(self.approval_config())
        self.assertTrue(decision["approved"])
        self.assertEqual(decision["reason_code"], "approved")
        self.assertEqual(decision["approval_id"], "approval-42")


class TestCommercePhaseTwoSchemaHandoff(unittest.TestCase):
    def test_notice_information_is_the_only_missing_field_and_blocks_both_platforms(self):
        for platform in ("smartstore", "coupang"):
            with self.subTest(platform=platform):
                contract = load_contract(platform)
                fields = {
                    field_name: {
                        "value": {"verified_field": field_name},
                        "status": "ready",
                        "classification": spec.get("classification"),
                    }
                    for field_name, spec in contract.items()
                }
                fields["notice_information"] = {
                    "value": None,
                    "status": "missing",
                    "classification": contract["notice_information"]["classification"],
                }

                result = validate_payload(platform, {"fields": fields}).to_dict()

                self.assertFalse(result["valid"])
                self.assertEqual(
                    result["blocked_reasons"],
                    [{
                        "code": "notice_information_incomplete",
                        "field": "notice_information",
                        "severity": "blocking",
                        "message": (
                            "'notice_information' has no accepted Phase 1 fact "
                            "(classification: conditional)."
                        ),
                        "required_action": (
                            "Resolve 'notice_information' via Phase 1's truth/source/freshness "
                            "gates, then regenerate the payload."
                        ),
                    }],
                )


class TestCommerceAuditRedactionHandoff(unittest.TestCase):
    def test_nested_credential_shapes_are_fully_redacted_and_json_serializable(self):
        secrets = {
            "api_key": "Top-Key_1234567890.segment_ABCDEFGHIJ.final-987654321",
            "credential": "x7",
            "client_key": "shortS3",
            "auth": "tiny42",
            "refresh_token": "RefreshTokenUnique_12345",
            "bearer": "Bearer BearerUniqueToken12345",
            "private_key": "PrivateKeyUnique_67890",
            "authorization": "authorization=AuthorizationUnique_24680",
        }
        entry = {
            "apiKey": secrets["api_key"],
            "credential": secrets["credential"],
            "Client-Key": secrets["client_key"],
            "client_key": secrets["client_key"],
            "auth": secrets["auth"],
            "nested": [
                {"refresh_token": secrets["refresh_token"]},
                {"ordinary_header": secrets["bearer"]},
                ({"private-key": secrets["private_key"]},),
                {"ordinary_query": secrets["authorization"]},
            ],
            "message": "normal dry-run audit message",
            "request_id": "order-42",
            "idempotency_key": "sha256:approved-dry-run-identifier-42",
        }

        sanitized = AuditLogger()._sanitize(entry)

        self.assertEqual(sanitized["apiKey"], "***REDACTED***")
        self.assertEqual(sanitized["credential"], "***REDACTED***")
        self.assertEqual(sanitized["Client-Key"], "***REDACTED***")
        self.assertEqual(sanitized["client_key"], "***REDACTED***")
        self.assertEqual(sanitized["auth"], "***REDACTED***")
        self.assertEqual(sanitized["nested"][0]["refresh_token"], "***REDACTED***")
        self.assertEqual(sanitized["nested"][1]["ordinary_header"], "***REDACTED***")
        self.assertEqual(sanitized["nested"][2][0]["private-key"], "***REDACTED***")
        self.assertEqual(sanitized["nested"][3]["ordinary_query"], "***REDACTED***")
        self.assertEqual(sanitized["message"], "normal dry-run audit message")
        self.assertEqual(sanitized["request_id"], "order-42")
        self.assertEqual(
            sanitized["idempotency_key"],
            "sha256:approved-dry-run-identifier-42",
        )

        serialized = json.dumps(sanitized, ensure_ascii=False)
        for secret in secrets.values():
            self.assertNotIn(secret, serialized)
        for identifying_fragment in (
            "segment_ABCDEFGHIJ", "RefreshTokenUnique", "BearerUniqueToken",
            "PrivateKeyUnique", "AuthorizationUnique",
        ):
            self.assertNotIn(identifying_fragment, serialized)


class TestCommerceStorage(unittest.TestCase):
    @staticmethod
    def module(storage):
        return CommerceModule(storage=storage, knowledge_interface=MagicMock(), brand_dna_interface=MagicMock())

    def test_request_id_path_component_is_sanitized(self):
        self.assertEqual(CommerceStorage._safe_request_id("order-42"), "order-42")
        opaque = CommerceStorage._safe_request_id("../../secret/sk-live-DO-NOT-LEAK")
        self.assertRegex(opaque, r"^commerce_[0-9a-f]{24,64}$")
        self.assertNotIn("secret", opaque)

    def test_atomic_write_creates_complete_package_in_workspace_temp_root(self):
        with tempfile.TemporaryDirectory(prefix="commerce-test-") as root:
            storage = CommerceStorage(Path(root))
            result = self.module(storage).run(request())
            target = Path(root) / "order-42"
            self.assertEqual(result["status"], "ready_for_manual_upload")
            self.assertTrue((target / "commerce_result.json").is_file())
            self.assertTrue((target / "smartstore_package.txt").is_file())
            self.assertTrue((target / "coupang_package.txt").is_file())
            self.assertFalse(any(p.name.startswith(".order-42-") for p in Path(root).iterdir()))

    def test_saved_json_output_paths_equal_returned_runtime_paths(self):
        with tempfile.TemporaryDirectory(prefix="commerce-test-") as root:
            storage = CommerceStorage(Path(root))
            result = self.module(storage).run(request())
            saved = json.loads(Path(result["output_paths"][0]).read_text(encoding="utf-8"))
            self.assertEqual(saved["output_paths"], result["output_paths"])

    def test_intermediate_write_failure_removes_temp_and_leaves_no_target(self):
        with tempfile.TemporaryDirectory(prefix="commerce-test-") as root:
            storage = CommerceStorage(Path(root))
            with patch.object(storage, "_write_json", side_effect=OSError("injected write failure")):
                result = self.module(storage).run(request())
            self.assertEqual(result["status"], "blocked")
            self.assertIn("storage_write_failed", reason_codes(result))
            self.assertFalse((Path(root) / "order-42").exists())
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_existing_request_collision_preserves_original_package(self):
        with tempfile.TemporaryDirectory(prefix="commerce-test-") as root:
            storage = CommerceStorage(Path(root))
            first = self.module(storage).run(request())
            result_path = Path(first["output_paths"][0])
            original = result_path.read_bytes()
            second = self.module(storage).run(request())
            self.assertEqual(second["status"], "blocked")
            self.assertIn("storage_write_failed", reason_codes(second))
            self.assertEqual(result_path.read_bytes(), original)
            self.assertFalse(any(p.name.startswith(".order-42-") for p in Path(root).iterdir()))

    def test_atomic_replace_failure_removes_temp_and_leaves_no_target(self):
        with tempfile.TemporaryDirectory(prefix="commerce-test-") as root:
            storage = CommerceStorage(Path(root))
            with patch("modules.commerce.commerce_storage.os", wraps=__import__("os")) as storage_os:
                storage_os.replace.side_effect = OSError("replace failed")
                result = self.module(storage).run(request())
            self.assertEqual(result["status"], "blocked")
            self.assertIn("storage_write_failed", reason_codes(result))
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_cleanup_failure_is_reported_as_structured_blocker(self):
        with tempfile.TemporaryDirectory(prefix="commerce-test-") as root:
            storage = CommerceStorage(Path(root))
            real_rmtree = __import__("shutil").rmtree
            with patch.object(storage, "_write_json", side_effect=OSError("injected write failure")), \
                 patch("modules.commerce.commerce_storage.shutil.rmtree", side_effect=OSError("injected cleanup failure")):
                result = self.module(storage).run(request())
            # Clean the intentionally retained test temp after restoring the real cleanup function.
            for candidate in Path(root).glob(".order-42-*"):
                real_rmtree(candidate)
            self.assertEqual(result["status"], "blocked")
            self.assertIn("storage_cleanup_failed", reason_codes(result))
            self.assertEqual(result["output_paths"], [])


if __name__ == "__main__":
    unittest.main()
