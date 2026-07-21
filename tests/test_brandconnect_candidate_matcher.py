"""Focused tests for Brand Connect catalog normalization, matching, second stage."""

import unittest

from modules.brandconnect.brandconnect_candidate_matcher import (
    is_editorial_bypass,
    match_candidate_to_products,
)
from modules.brandconnect.brandconnect_product_catalog import normalize_brandconnect_catalog
from modules.brandconnect.brandconnect_second_stage import run_brandconnect_second_stage

SNAPSHOT = {
    "source": "authorized_ui_snapshot",
    "captured_at": "2026-07-17T10:00:00+09:00",
    "products": [
        {"product_id": "P-1", "name": "UV 차단 양산", "brand": "쿨셰이드", "category": "생활",
         "keywords": ["양산", "쿨링"], "url": "https://smartstore.example/p1", "price": 19900},
        {"product_id": "P-2", "name": "여름 린넨 셔츠", "brand": "모던핏", "category": "패션",
         "keywords": ["셔츠", "린넨"]},
        {"product_id": "P-3", "name": "남성 헤어 왁스", "brand": "그루밍랩", "category": "뷰티",
         "keywords": ["헤어", "왁스"]},
        {"product_id": "P-1", "name": "UV 차단 양산", "brand": "쿨셰이드", "category": "생활"},
        {"name": "아이디 없는 상품"},
        "malformed-entry",
    ],
}


class CatalogNormalizationTest(unittest.TestCase):
    def test_dedupe_and_drop_are_deterministic(self):
        first = normalize_brandconnect_catalog(SNAPSHOT)
        second = normalize_brandconnect_catalog(SNAPSHOT)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "ready")
        self.assertEqual([p["product_id"] for p in first["products"]], ["P-1", "P-2", "P-3"])
        reasons = [d["reason"] for d in first["dropped"]]
        self.assertIn("duplicate_product", reasons)
        self.assertIn("missing_id_or_name", reasons)
        self.assertIn("malformed_product", reasons)

    def test_family_and_audience_derived_without_inventing_facts(self):
        catalog = normalize_brandconnect_catalog(SNAPSHOT)
        by_id = {p["product_id"]: p for p in catalog["products"]}
        self.assertEqual(by_id["P-2"]["product_family"], "fashion")
        self.assertEqual(by_id["P-3"]["product_family"], "hair")
        self.assertEqual(by_id["P-3"]["audience"], "male")
        self.assertEqual(by_id["P-1"]["price"], 19900)
        self.assertNotIn("price", by_id["P-2"])
        self.assertNotIn("stock_status", by_id["P-2"])
        self.assertNotIn("review_count", by_id["P-2"])

    def test_missing_or_malformed_catalog_is_explicitly_incomplete(self):
        for snapshot in (None, {}, {"products": []}, "not-a-catalog", {"products": "nope"}):
            result = normalize_brandconnect_catalog(snapshot)
            self.assertFalse(result["complete"])
            self.assertIn(result["status"], {"catalog_missing", "malformed_catalog"})
            self.assertEqual(result["products"], [])


class CandidateMatcherTest(unittest.TestCase):
    def setUp(self):
        self.products = normalize_brandconnect_catalog(SNAPSHOT)["products"]

    def test_situational_heat_match_earns_commerce_fit(self):
        candidate = {"id": "C-1", "title": "역대급 폭염 속 출근길", "category": "생활"}
        outcome = match_candidate_to_products(candidate, self.products)
        self.assertEqual(outcome["match_status"], "matched")
        self.assertEqual(outcome["matches"][0]["product_id"], "P-1")
        self.assertIn("situational:heat", outcome["matches"][0]["match_basis"])
        self.assertGreater(outcome["commerce_fit"], 0)
        self.assertFalse(outcome["matches"][0]["link_issued"])

    def test_keyword_category_match_for_fashion(self):
        candidate = {"id": "C-2", "title": "여름 린넨 셔츠 코디", "category": "패션"}
        outcome = match_candidate_to_products(candidate, self.products)
        self.assertEqual(outcome["match_status"], "matched")
        self.assertEqual(outcome["matches"][0]["product_id"], "P-2")

    def test_editorial_runway_bypasses_commerce_without_penalty(self):
        candidate = {"id": "C-3", "title": "디올 2026 가을 런웨이 컬렉션 공개", "category": "패션"}
        self.assertTrue(is_editorial_bypass(candidate))
        outcome = match_candidate_to_products(candidate, self.products)
        self.assertEqual(outcome["match_status"], "editorial_bypass")
        self.assertIsNone(outcome["commerce_fit"])
        self.assertFalse(outcome["penalized"])
        self.assertEqual(outcome["matches"], [])

    def test_unmatched_candidate_is_not_penalized(self):
        candidate = {"id": "C-4", "title": "지하철 요금 인상 논의", "category": "사회"}
        outcome = match_candidate_to_products(candidate, self.products)
        self.assertEqual(outcome["match_status"], "unmatched")
        self.assertIsNone(outcome["commerce_fit"])
        self.assertFalse(outcome["penalized"])

    def test_situation_word_alone_cannot_cross_product_families(self):
        products = normalize_brandconnect_catalog({
            "products": [
                {
                    "product_id": "P-PANTS",
                    "name": "아이스 조거팬츠 냉감 여름",
                    "category": "남성패션",
                    "keywords": ["냉감", "여름", "팬츠"],
                }
            ]
        })["products"]
        candidate = {
            "id": "C-FRAGRANCE",
            "title": "콜라 향수와 워터프루프 선크림 출시",
            "category": "뷰티·향수",
            "context": "여름철 무더위를 겨냥한 뷰티 신제품",
        }
        self.assertEqual(match_candidate_to_products(candidate, products)["match_status"], "unmatched")

    def test_incidental_standalone_bi_is_not_rain(self):
        products = normalize_brandconnect_catalog({
            "products": [
                {
                    "product_id": "P-WATERPROOF",
                    "name": "핸드폰 방수팩",
                    "category": "스포츠/레저",
                    "keywords": ["방수팩"],
                }
            ]
        })["products"]
        candidate = {
            "id": "C-DONATION",
            "title": "의류 기부 캠페인 성료",
            "category": "패션",
            "context": "그린 비(GREEN B) 프로젝트를 마무리했다.",
        }
        self.assertEqual(match_candidate_to_products(candidate, products)["match_status"], "editorial_bypass")

    def test_season_collection_is_editorial_bypass(self):
        candidate = {
            "id": "C-COLLECTION",
            "title": "돌체앤가바나 2027 S/S 남성복 컬렉션",
            "category": "패션",
        }
        self.assertEqual(
            match_candidate_to_products(candidate, self.products)["match_status"],
            "editorial_bypass",
        )

    def test_product_family_does_not_use_ambiguous_substrings(self):
        products = normalize_brandconnect_catalog({
            "products": [
                {"product_id": "P-FAN", "name": "클리프팬 휴대용 손 선풍기"},
                {
                    "product_id": "P-SHOE",
                    "name": "아쿠아슈즈 페더 크림",
                    "category": "패션잡화",
                },
            ]
        })["products"]
        by_id = {item["product_id"]: item for item in products}
        self.assertEqual(by_id["P-FAN"]["product_family"], "lifestyle")
        self.assertEqual(by_id["P-SHOE"]["product_family"], "accessory")

    def test_care_article_rejects_non_care_product(self):
        products = normalize_brandconnect_catalog({
            "products": [
                {
                    "product_id": "P-SHOE",
                    "name": "아쿠아슈즈 신발",
                    "category": "패션잡화",
                    "keywords": ["신발"],
                }
            ]
        })["products"]
        candidate = {
            "id": "C-SHOE-CARE",
            "title": "신발 오래 깨끗하게 신는 관리법",
            "category": "뷰티",
        }
        self.assertEqual(match_candidate_to_products(candidate, products)["match_status"], "unmatched")

    def test_style_word_alone_cannot_turn_outerwear_into_underwear(self):
        products = normalize_brandconnect_catalog({
            "products": [
                {
                    "product_id": "P-BRA",
                    "name": "레이스 브라 속옷 란제리",
                    "category": "여성패션",
                    "keywords": ["레이스", "브라"],
                }
            ]
        })["products"]
        candidate = {
            "id": "C-OUTFIT",
            "title": "레이스 크롭 톱에 집업 재킷 출국룩",
            "category": "패션",
        }
        self.assertEqual(match_candidate_to_products(candidate, products)["match_status"], "unmatched")

    def test_general_summer_fashion_does_not_become_sleepwear(self):
        products = normalize_brandconnect_catalog({
            "products": [
                {
                    "product_id": "P-PAJAMA",
                    "name": "냉감 여름잠옷 홈웨어 파자마",
                    "category": "남성패션",
                    "keywords": ["냉감", "잠옷"],
                }
            ]
        })["products"]
        candidate = {
            "id": "C-SUMMER-FASHION",
            "title": "폭염이 바꾼 냉감 티셔츠 패션 공식",
            "category": "패션",
        }
        self.assertEqual(match_candidate_to_products(candidate, products)["match_status"], "unmatched")

    def test_single_incidental_word_does_not_match_large_catalog_product(self):
        products = normalize_brandconnect_catalog({
            "products": [{
                "product_id": "P-SPACE",
                "name": "스페이스 그래픽 티셔츠",
                "category": "패션의류",
            }]
        })["products"]
        candidate = {"id": "C-SPACE", "title": "브랜드 스페이스 오픈", "category": "패션"}
        self.assertEqual(match_candidate_to_products(candidate, products)["match_status"], "unmatched")

    def test_short_ascii_brand_cannot_substring_match(self):
        products = normalize_brandconnect_catalog({
            "products": [{
                "product_id": "P-LE",
                "name": "그린 홀터넥",
                "brand": "LE",
                "category": "패션의류",
            }]
        })["products"]
        candidate = {"id": "C-BENETTON", "title": "베네통 GREEN B 프로젝트", "category": "패션"}
        self.assertEqual(match_candidate_to_products(candidate, products)["match_status"], "unmatched")

    def test_perfume_article_rejects_perfumed_bodywash(self):
        products = normalize_brandconnect_catalog({
            "products": [{
                "product_id": "P-WASH",
                "name": "퍼퓸 바디워시",
                "category": "화장품/미용",
                "keywords": ["퍼퓸", "바디워시"],
            }]
        })["products"]
        candidate = {"id": "C-PERFUME", "title": "여름 신상 향수 공개", "category": "뷰티·향수"}
        self.assertEqual(match_candidate_to_products(candidate, products)["match_status"], "unmatched")

    def test_clothing_donation_campaign_bypasses_commerce(self):
        candidate = {
            "id": "C-DONATION",
            "title": "브랜드, 아름다운가게와 의류 기부 캠페인 성료",
            "category": "패션",
        }
        self.assertEqual(match_candidate_to_products(candidate, self.products)["match_status"], "editorial_bypass")

    def test_matching_is_deterministic(self):
        candidate = {"id": "C-1", "title": "폭염 양산 필수", "category": "생활"}
        self.assertEqual(
            match_candidate_to_products(candidate, self.products),
            match_candidate_to_products(candidate, self.products),
        )

    def test_korean_topic_particle_does_not_hide_shampoo_match(self):
        products = normalize_brandconnect_catalog({"products": [{
            "product_id": "P-SHAMPOO",
            "name": "데일리 두피 샴푸",
            "category": "화장품/미용",
        }]})["products"]
        candidate = {
            "id": "C-SHAMPOO",
            "title": "마트 샴푸도 괜찮을까? 전문가들의 답은 의외였습니다",
            "category": "뷰티",
        }
        outcome = match_candidate_to_products(candidate, products)
        self.assertEqual(outcome["match_status"], "matched")
        self.assertEqual(outcome["matches"][0]["product_id"], "P-SHAMPOO")

    def test_humid_bangs_connect_to_observable_hair_function(self):
        products = normalize_brandconnect_catalog({"products": [{
            "product_id": "P-BANGS",
            "name": "앞머리 픽서 뿌리볼륨 헤어스프레이",
            "category": "화장품/미용",
        }]})["products"]
        candidate = {
            "id": "C-BANGS",
            "title": "비 올 때 축 처진 앞머리, 요즘은 이렇게 복구합니다",
            "category": "뷰티·헤어",
        }
        outcome = match_candidate_to_products(candidate, products)
        self.assertEqual(outcome["match_status"], "matched")
        self.assertEqual(outcome["matches"][0]["product_id"], "P-BANGS")
        self.assertTrue(any(value in outcome["matches"][0]["match_basis"] for value in (
            "meaningful_keyword_overlap", "situational:hair_humidity"
        )))

    def test_unrelated_rain_news_does_not_match_hair_product(self):
        products = normalize_brandconnect_catalog({"products": [{
            "product_id": "P-BANGS",
            "name": "앞머리 픽서 뿌리볼륨 헤어스프레이",
            "category": "화장품/미용",
        }]})["products"]
        candidate = {"id": "A-RAIN", "title": "폭우로 도로 통제", "category": "국내뉴스"}
        self.assertEqual(match_candidate_to_products(candidate, products)["match_status"], "unmatched")

    def test_pack_size_variants_do_not_fill_all_match_slots(self):
        products = normalize_brandconnect_catalog({"products": [
            {"product_id": "P-1", "name": "초록 두피 샴푸 500ml, 1개", "brand": "A", "category": "화장품/미용"},
            {"product_id": "P-2", "name": "초록 두피 샴푸 500ml, 2개", "brand": "A", "category": "화장품/미용"},
            {"product_id": "P-3", "name": "데일리 샴푸 500ml", "brand": "B", "category": "화장품/미용"},
        ]})["products"]
        outcome = match_candidate_to_products(
            {"id": "C-SHAMPOO", "title": "마트 샴푸도 괜찮을까?", "category": "뷰티"},
            products,
        )
        self.assertEqual([item["product_id"] for item in outcome["matches"]], ["P-1", "P-3"])


class SecondStageTest(unittest.TestCase):
    CANDIDATES = [
        {"id": "C-1", "title": "폭염 속 양산 필수템", "category": "생활"},
        {"id": "C-2", "title": "디올 런웨이 시즌 콘셉트", "category": "패션"},
        {"id": "C-3", "title": "지하철 요금 인상", "category": "사회"},
        {"id": "C-4", "title": "등급 없는 후보", "category": "생활"},
    ]
    RATINGS = {"C-1": {"grade": "1"}, "C-2": {"grade": "2"}, "C-3": {"grade": "3"}, "C-5": {"grade": "exclude"}}

    def test_runs_after_grading_and_annotates_by_status(self):
        stage = run_brandconnect_second_stage(self.CANDIDATES, self.RATINGS, SNAPSHOT)
        self.assertEqual(stage["status"], "completed")
        self.assertEqual(stage["stage_position"], "after_owner_grading_before_final_four")
        self.assertEqual(stage["graded_candidate_count"], 3)
        by_id = {a["candidate_id"]: a for a in stage["annotations"]}
        self.assertNotIn("C-4", by_id)
        self.assertEqual(by_id["C-1"]["commerce_status"], "matched")
        self.assertEqual(by_id["C-2"]["commerce_status"], "editorial_bypass")
        self.assertEqual(by_id["C-3"]["commerce_status"], "unmatched")
        self.assertTrue(all(a["penalized"] is False for a in stage["annotations"]))
        self.assertFalse(stage["network_used"])
        self.assertFalse(stage["login_automation"])
        self.assertFalse(stage["link_issuance"])
        self.assertFalse(stage["publishing"])

    def test_missing_catalog_stays_explicitly_incomplete(self):
        stage = run_brandconnect_second_stage(self.CANDIDATES, self.RATINGS, None)
        self.assertEqual(stage["status"], "incomplete_catalog")
        self.assertFalse(stage["complete"])
        for annotation in stage["annotations"]:
            self.assertEqual(annotation["commerce_status"], "catalog_unavailable")
            self.assertIsNone(annotation["commerce_fit"])
            self.assertEqual(annotation["matches"], [])

    def test_no_fabricated_commercial_facts_in_matches(self):
        stage = run_brandconnect_second_stage(self.CANDIDATES, self.RATINGS, SNAPSHOT)
        matched = next(a for a in stage["annotations"] if a["commerce_status"] == "matched")
        for match in matched["matches"]:
            self.assertFalse(match["link_issued"])
            for forbidden in ("price", "stock_status", "review_count", "rating", "affiliate_link"):
                self.assertNotIn(forbidden, match)

    def test_relation_index_expands_a_care_topic_without_issuing_link(self):
        snapshot = {
            "products": [
                {
                    "product_id": "P-SHOE-CARE",
                    "name": "운동화 신발 세제 클리너",
                    "category": "생활",
                }
            ]
        }
        candidates = [
            {
                "id": "C-SHOE-CARE",
                "title": "신발 오래 깨끗하게 신는 관리법",
                "category": "생활",
            }
        ]
        relation_index = {
            "P-SHOE-CARE": {
                "derived_terms": ["빨래", "세탁"],
                "practical_topic": "신발을 오래 쓰는 세척과 관리 순서",
                "product_role": "생활 관리 콘텐츠에 연결할 상품 후보",
            }
        }
        stage = run_brandconnect_second_stage(
            candidates,
            {"C-SHOE-CARE": {"grade": "1"}},
            snapshot,
            relation_index=relation_index,
        )
        annotation = stage["annotations"][0]
        self.assertEqual(annotation["commerce_status"], "matched")
        self.assertTrue(annotation["relation_signals_used"])
        self.assertFalse(annotation["matches"][0]["link_issued"])


if __name__ == "__main__":
    unittest.main()
