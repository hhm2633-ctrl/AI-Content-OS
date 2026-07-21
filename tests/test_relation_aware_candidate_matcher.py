"""Focused tests for the relation-aware Brand Connect candidate matcher."""

import unittest

from modules.brandconnect.brandconnect_product_catalog import normalize_brandconnect_catalog
from modules.brandconnect.relation_aware_candidate_matcher import (
    match_candidate_with_relations,
    prepare_relation_index,
    relation_signal_fields,
)

PRODUCTS = normalize_brandconnect_catalog({
    "products": [
        {"product_id": "P-CLEAN", "name": "슈 프레시 클리너 세트", "category": "생활",
         "keywords": ["클리너"]},
        {"product_id": "P-SHIRT", "name": "여름 린넨 셔츠", "brand": "모던핏", "category": "패션",
         "keywords": ["셔츠", "린넨"]},
        {"product_id": "P-TUMBLER", "name": "보온 텀블러", "category": "생활", "keywords": ["텀블러"]},
    ]
})["products"]

# Raw shard-row shape (derived_terms + mapping season_context).
RELATIONS = {
    "P-CLEAN": {
        "derived_terms": ["신발", "세척", "클리너"],
        "season_context": {"season": "사계절", "daily_environment": "귀가 후 현관"},
        "practical_topic": "신발 세척 루틴을 짧게 유지하는 방법",
        "product_role": "신발 관리 콘텐츠에 클리너 제품으로 연결",
    },
    "P-SHIRT": {
        "derived_terms": ["셔츠", "린넨", "여름"],
        "season_context": {"season": "여름", "weather": "더위"},
        "practical_topic": "린넨 셔츠 구김을 줄이는 코디",
        "product_role": "여름 코디 콘텐츠에 셔츠 제품으로 연결",
    },
    "P-TUMBLER": {
        "derived_terms": ["텀블러", "보온"],
        "season_context": "겨울 출근길",
        "practical_topic": "따뜻한 음료를 오래 유지하는 방법",
        "product_role": "출근길 콘텐츠에 텀블러 제품으로 연결",
    },
}


class RelationSignalExtractionTest(unittest.TestCase):
    def test_accepts_raw_row_and_engine_normalized_shapes(self):
        raw = relation_signal_fields(RELATIONS["P-CLEAN"])
        self.assertIn("신발", raw["derived_terms"])
        self.assertIn("귀가 후 현관", raw["season_context"])
        normalized = relation_signal_fields({
            "season_context": "출근·등교 전 매일 아침",
            "practical_topic": "아침 가글 루틴",
            "product_role": "구강 콘텐츠 연결 상품 후보",
        })
        self.assertEqual(normalized["derived_terms"], "")
        self.assertEqual(normalized["season_context"], "출근·등교 전 매일 아침")
        self.assertEqual(relation_signal_fields(None), {})


class RelationAwareMatcherTest(unittest.TestCase):
    def test_care_to_function_bridge_matches_via_relations(self):
        candidate = {"id": "C-1", "title": "운동화 세척과 신발 관리법 총정리", "category": "생활"}
        outcome = match_candidate_with_relations(candidate, PRODUCTS, RELATIONS)
        self.assertEqual(outcome["match_status"], "matched")
        self.assertTrue(outcome["relation_signals_used"])
        match = outcome["matches"][0]
        self.assertEqual(match["product_id"], "P-CLEAN")
        self.assertIn("relation_term:신발", match["match_basis"])
        self.assertIn("relation_term:세척", match["match_basis"])
        self.assertTrue(any(b.startswith("relation_fields:") for b in match["match_basis"]))
        self.assertFalse(match["link_issued"])

    def test_single_token_overlap_never_matches(self):
        candidate = {"id": "C-2", "title": "신발 브랜드 대규모 세일 소식", "category": "생활"}
        outcome = match_candidate_with_relations(candidate, [PRODUCTS[0]], RELATIONS)
        self.assertEqual(outcome["match_status"], "unmatched")
        self.assertEqual(outcome["matches"], [])

    def test_season_words_alone_are_not_evidence(self):
        candidate = {"id": "C-3", "title": "여름 전력 수요 급증 전망", "category": "생활"}
        outcome = match_candidate_with_relations(candidate, [PRODUCTS[1]], RELATIONS)
        self.assertEqual(outcome["match_status"], "unmatched")

    def test_editorial_bypass_is_preserved(self):
        candidate = {"id": "C-4", "title": "디올 2026 가을 런웨이 컬렉션 공개", "category": "패션"}
        outcome = match_candidate_with_relations(candidate, PRODUCTS, RELATIONS)
        self.assertEqual(outcome["match_status"], "editorial_bypass")
        self.assertIsNone(outcome["commerce_fit"])
        self.assertFalse(outcome["penalized"])

    def test_exact_matching_still_works_without_relation_data(self):
        candidate = {"id": "C-5", "title": "여름 린넨 셔츠 코디", "category": "패션"}
        outcome = match_candidate_with_relations(candidate, PRODUCTS, relation_index=None)
        self.assertEqual(outcome["match_status"], "matched")
        self.assertEqual(outcome["matches"][0]["product_id"], "P-SHIRT")
        self.assertFalse(outcome["relation_signals_used"])

    def test_agreeing_relations_raise_an_exact_match_score(self):
        candidate = {"id": "C-6", "title": "여름 린넨 셔츠 코디", "category": "패션"}
        base_only = match_candidate_with_relations(candidate, PRODUCTS, relation_index=None)
        combined = match_candidate_with_relations(candidate, PRODUCTS, RELATIONS)
        self.assertEqual(combined["matches"][0]["product_id"], "P-SHIRT")
        self.assertGreater(combined["matches"][0]["score"], base_only["matches"][0]["score"])

    def test_deterministic_across_runs(self):
        candidate = {"id": "C-7", "title": "운동화 세척과 신발 관리법 총정리", "category": "생활"}
        self.assertEqual(
            match_candidate_with_relations(candidate, PRODUCTS, RELATIONS),
            match_candidate_with_relations(candidate, PRODUCTS, RELATIONS),
        )

    def test_unrelated_candidate_stays_unmatched_and_unpenalized(self):
        candidate = {"id": "C-8", "title": "지하철 요금 인상 논의", "category": "사회"}
        outcome = match_candidate_with_relations(candidate, PRODUCTS, RELATIONS)
        self.assertEqual(outcome["match_status"], "unmatched")
        self.assertIsNone(outcome["commerce_fit"])
        self.assertFalse(outcome["penalized"])

    def test_prepared_index_retains_hand_shoe_and_male_removal_matches(self):
        products = normalize_brandconnect_catalog({"products": [
            {"product_id": "P-HAND", "name": "고보습 핸드크림", "category": "뷰티"},
            {"product_id": "P-SHOE", "name": "운동화 신발 세척 클리너", "category": "생활"},
            {"product_id": "P-REMOVE", "name": "남성 바디 제모 왁싱 키트", "category": "뷰티"},
        ]})["products"]
        relations = {
            "P-HAND": {"derived_terms": ["손", "보습"], "practical_topic": "손 보습 관리", "product_role": "손 관리에 핸드 제품 연결"},
            "P-SHOE": {"derived_terms": ["신발", "세척"], "practical_topic": "신발 세척 관리", "product_role": "신발 관리에 클리너 연결"},
            "P-REMOVE": {"derived_terms": ["남성", "제모"], "practical_topic": "남성 제모 관리", "product_role": "남성 관리에 왁싱 제품 연결"},
        }
        prepared = prepare_relation_index(relations, products)
        cases = (
            ("건조한 손 보습 관리", "P-HAND"),
            ("운동화 신발 세척 관리", "P-SHOE"),
            ("남성 바디 제모 관리", "P-REMOVE"),
        )
        for title, expected_product_id in cases:
            with self.subTest(title=title):
                raw = match_candidate_with_relations({"title": title, "category": "뷰티"}, products, relations)
                indexed = match_candidate_with_relations({"title": title, "category": "뷰티"}, products, prepared)
                self.assertEqual(indexed, raw)
                self.assertEqual(indexed["matches"][0]["product_id"], expected_product_id)

    def test_prepared_index_retains_false_positive_guards_and_determinism(self):
        prepared = prepare_relation_index(RELATIONS, PRODUCTS)
        candidates = (
            {"id": "FP-1", "title": "신발 브랜드 대규모 세일 소식", "category": "생활"},
            {"id": "FP-2", "title": "여름 전력 수요 급증 전망", "category": "생활"},
            {"id": "FP-3", "title": "지하철 요금 인상 논의", "category": "사회"},
        )
        first = [match_candidate_with_relations(candidate, PRODUCTS, prepared) for candidate in candidates]
        second = [match_candidate_with_relations(candidate, PRODUCTS, prepared) for candidate in candidates]
        self.assertEqual(first, second)
        self.assertTrue(all(outcome["match_status"] == "unmatched" for outcome in first))

    def test_prepared_index_is_conservative_for_brand_and_situation_matches(self):
        products = normalize_brandconnect_catalog({"products": [
            {"product_id": "P-BRAND", "name": "여름 셔츠", "brand": "A.B.C", "category": "패션"},
            {"product_id": "P-RAIN", "name": "장마 방수 우산", "category": "생활"},
        ]})["products"]
        prepared = prepare_relation_index({}, products)
        candidates = (
            {"title": "A.B.C 신제품 공개", "category": "패션"},
            {"title": "비가 내리는 출근길 준비", "category": "생활"},
        )
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                self.assertEqual(
                    match_candidate_with_relations(candidate, products, {}),
                    match_candidate_with_relations(candidate, products, prepared),
                )


if __name__ == "__main__":
    unittest.main()
