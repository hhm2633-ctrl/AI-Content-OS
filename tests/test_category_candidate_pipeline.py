import copy
import unittest

from modules.source_intake.category_candidate_pipeline import run_category_candidate_pipeline


class CategoryCandidatePipelineTests(unittest.TestCase):
    def test_policy_news_is_normalized_and_categorized_without_raw_score_reuse(self):
        candidates = [
            {
                "source_id": "naver_news", "source_type": "news",
                "source_lane_id": "news_society_economy",
                "title": "정부가 새 복지 정책 시행을 발표",
                "summary": "국회 법안과 제도 변경 내용을 설명했다.",
                "publisher": "example-news", "link": "https://example.com/policy",
                "rank_position": 1, "published_at": "2026-07-16T08:00:00+09:00",
                "collected_at": "2026-07-16T09:00:00+09:00",
            },
            {
                "source_id": "naver_news", "source_type": "news",
                "source_lane_id": "news_society_economy",
                "title": "정부 교육 정책 후속 발표", "publisher": "other-news",
                "rank_position": 2, "published_at": "2026-07-16T07:00:00+09:00",
                "collected_at": "2026-07-16T09:00:00+09:00",
            },
        ]
        result = run_category_candidate_pipeline(candidates)
        self.assertEqual("ok", result["status"])
        self.assertEqual(2, result["item_count"])
        self.assertEqual("major_news_policy", result["items"][0]["primary_category"])
        self.assertTrue(result["items"][0]["candidate_id"].startswith("candidate:"))
        self.assertFalse(result["production_wired"])
        self.assertTrue(result["items"][0]["feature_diagnostics"]["shallow_heuristics_only"])

    def test_missing_news_engagement_remains_missing_but_rank_drives_attention(self):
        candidate = {
            "candidate_id": "news-1", "source_id": "yonhap", "source_type": "news",
            "source_lane_id": "news_society_economy", "title": "정부 정책 발표",
            "rank_position": 1,
        }
        result = run_category_candidate_pipeline([candidate])
        item = result["items"][0]
        self.assertIsNotNone(item["attention"]["score"])
        self.assertNotIn("views", item["feature_diagnostics"]["attention_components_used"])

    def test_rfc2822_news_timestamp_is_measured_without_network(self):
        candidate = {
            "candidate_id": "news-rfc", "source_id": "naver_news", "source_type": "news",
            "source_lane_id": "news_society_economy", "title": "정부 정책 발표",
            "rank_position": 1,
            "published_at": "Wed, 15 Jul 2026 20:46:00 +0900",
            "collected_at": "2026-07-15T20:59:08+09:00",
        }
        result = run_category_candidate_pipeline([candidate])
        self.assertEqual("measured", result["items"][0]["freshness"]["status"])
        self.assertLess(result["items"][0]["freshness"]["age_hours"], 1.0)

    def test_community_subject_keyword_beats_community_prior(self):
        candidates = [
            {
                "candidate_id": "fashion-1", "source_id": "theqoo", "source_type": "community",
                "source_lane_id": "beauty_fashion", "title": "여름 패션 코디 신상 후기",
                "visible_metrics": {"views": 1000, "comments": 20, "likes": 30},
            },
            {
                "candidate_id": "fashion-2", "source_id": "theqoo", "source_type": "community",
                "source_lane_id": "beauty_fashion", "title": "여름 화장품 스타일 추천",
                "visible_metrics": {"views": 800, "comments": 10, "likes": 20},
            },
        ]
        result = run_category_candidate_pipeline(candidates)
        self.assertEqual("beauty_fashion", result["items"][0]["primary_category"])
        self.assertNotEqual("community_buzz", result["items"][0]["primary_category"])

    def test_input_is_not_mutated_and_malformed_batch_fails_closed(self):
        candidates = [{"candidate_id": "x", "source_id": "s", "title": "생활 꿀팁"}]
        snapshot = copy.deepcopy(candidates)
        run_category_candidate_pipeline(candidates)
        self.assertEqual(snapshot, candidates)
        closed = run_category_candidate_pipeline({"items": candidates})
        self.assertEqual("closed", closed["status"])
        self.assertEqual([], closed["items"])

    def test_shallow_absence_does_not_claim_risk_clearance_or_qualitative_proxies(self):
        candidate = {
            "candidate_id": "incident-1", "source_id": "bobaedream", "source_type": "community",
            "source_lane_id": "dopamine_community", "title": "경찰 사건 사고 논란",
            "visible_metrics": {"views": 100, "comments": 10},
        }
        result = run_category_candidate_pipeline([candidate])
        values = result["items"][0]["category_value_all"]
        self.assertIsNone(values["incident_conflict"]["weighted_breakdown"]["risk_clearance"]["value"])
        self.assertIsNone(values["incident_conflict"]["weighted_breakdown"]["public_interest"]["value"])
        self.assertIsNone(values["community_buzz"]["weighted_breakdown"]["novelty"]["value"])

    def test_official_exception_is_derived_only_from_allowlisted_https_domain(self):
        base = {
            "source_id": "naver_news", "source_type": "news",
            "source_lane_id": "news_society_economy", "title": "정부 정책 발표",
            "rank_position": 1,
        }
        forged = dict(base, candidate_id="forged", link="https://example.com/policy", authoritative_official_origin=True)
        verified = dict(base, candidate_id="verified", link="https://www.korea.kr/briefing/policy")
        result = run_category_candidate_pipeline([forged, verified])
        by_id = {item["candidate_id"]: item for item in result["items"]}
        self.assertFalse(by_id["forged"]["authoritative_official_origin"])
        self.assertFalse(by_id["verified"]["authoritative_official_origin"])
        self.assertEqual(
            "official_domain_identity_only",
            by_id["verified"]["feature_diagnostics"]["evidence_bundle"]
            ["official_document_candidates"][0]["verification_status"],
        )

    def test_malformed_official_url_fails_closed_as_non_evidence_without_exception(self):
        candidate = {
            "candidate_id": "bad-url", "source_id": "naver_news", "source_type": "news",
            "source_lane_id": "news_society_economy", "title": "정부 정책 발표",
            "rank_position": 1, "link": "https://[",
        }
        item = run_category_candidate_pipeline([candidate])["items"][0]
        self.assertFalse(item["authoritative_official_origin"])
        self.assertEqual([], item["evidence_bundle"]["official_document_candidates"])
        self.assertEqual("NEEDS_EVIDENCE", item["decision"])

    def test_soft_risk_detector_is_composed_into_evidence_gate(self):
        candidate = {
            "candidate_id": "rumor-1", "source_id": "nate_pann", "source_type": "community",
            "source_lane_id": "dopamine_community", "title": "배우 불륜 의혹 루머",
            "visible_metrics": {"views": 5000, "comments": 300, "likes": 100},
        }
        item = run_category_candidate_pipeline([candidate])["items"][0]
        self.assertEqual("NEEDS_EVIDENCE", item["decision"])
        self.assertIn("defamation", item["soft_risk_flags"])
        self.assertIn("rumor_independent_confirmation", item["evidence_needs"])
        self.assertEqual("needs_evidence", item["risk_detection_status"])

    def test_hard_risk_detector_is_composed_into_reject_gate(self):
        candidate = {
            "candidate_id": "privacy-1", "source_id": "bobaedream", "source_type": "community",
            "source_lane_id": "dopamine_community",
            "title": "신상 공개 전화번호 010-1234-5678",
        }
        item = run_category_candidate_pipeline([candidate])["items"][0]
        self.assertEqual("REJECT", item["decision"])
        self.assertIn("doxxing", item["hard_risk_flags"])

    def test_portal_without_underlying_publisher_keeps_origin_unknown(self):
        candidate = {
            "candidate_id": "portal-unknown", "source_id": "naver_news", "source_type": "news",
            "source_lane_id": "news_society_economy", "title": "정부 정책 발표",
            "rank_position": 1,
        }
        item = run_category_candidate_pipeline([candidate])["items"][0]
        self.assertIsNone(item["origin_independence"]["score"])
        self.assertEqual("NEEDS_EVIDENCE", item["decision"])

    def test_evidence_bundle_is_composed_and_open_claim_alignment_blocks_go(self):
        candidate = {
            "candidate_id": "official-policy", "source_id": "naver_news", "source_type": "news",
            "source_lane_id": "news_society_economy", "title": "정부 복지 정책 시행 발표",
            "summary": "지원 대상은 10만 명이며 다음 달 시행한다.",
            "publisher": "정책브리핑", "link": "https://www.korea.kr/briefing/policy",
            "rank_position": 1,
        }
        item = run_category_candidate_pipeline([candidate])["items"][0]
        self.assertEqual("ok", item["evidence_bundle"]["status"])
        self.assertEqual(1, len(item["evidence_bundle"]["official_document_candidates"]))
        self.assertIn("claim_to_evidence_alignment_review", item["evidence_needs"])
        self.assertEqual("NEEDS_EVIDENCE", item["decision"])

    def test_post_selection_catalog_cannot_become_a_topic_candidate(self):
        editorial = {
            "candidate_id": "fashion-editorial",
            "source_id": "fashionn",
            "source_type": "fashion_editorial",
            "source_lane_id": "beauty_fashion",
            "title": "여름 크롭 재킷과 롱스커트 스타일",
            "post_selection_only": False,
        }
        catalog = {
            "candidate_id": "luxury-catalog-item",
            "source_id": "musinsa_boutique",
            "source_type": "luxury_reference_catalog",
            "source_lane_id": "beauty_fashion",
            "title": "럭셔리 크롭 재킷",
            "rank_position": 1,
            "post_selection_only": True,
        }
        result = run_category_candidate_pipeline([catalog, editorial])
        self.assertEqual(1, result["item_count"])
        self.assertEqual("fashion-editorial", result["items"][0]["candidate_id"])
        self.assertEqual(1, result["diagnostics"]["post_selection_excluded_count"])
        self.assertEqual(
            "post_selection_catalog_not_topic_candidate",
            result["diagnostics"]["post_selection_excluded"][0]["reason_code"],
        )

    def test_supporting_industry_source_cannot_become_a_topic_candidate(self):
        consumer_editorial = {
            "candidate_id": "consumer-beauty",
            "source_id": "allure_beauty",
            "source_type": "beauty_consumer_editorial",
            "source_lane_id": "beauty_fashion",
            "title": "장마철 축 처진 앞머리 복구법",
            "editorial_topic_eligible": True,
            "topic_selection_role": "primary_consumer_editorial",
        }
        industry_news = {
            "candidate_id": "beauty-industry",
            "source_id": "cosin",
            "source_type": "beauty_industry_editorial",
            "source_lane_id": "beauty_fashion",
            "title": "화장품 기업 수출 실적 발표",
            "editorial_topic_eligible": False,
            "topic_selection_role": "supporting_industry",
        }

        result = run_category_candidate_pipeline([industry_news, consumer_editorial])

        self.assertEqual(1, result["item_count"])
        self.assertEqual("consumer-beauty", result["items"][0]["candidate_id"])
        self.assertEqual(1, result["diagnostics"]["post_selection_excluded_count"])
        excluded = result["diagnostics"]["post_selection_excluded"][0]
        self.assertEqual("supporting_source_not_topic_candidate", excluded["reason_code"])
        self.assertEqual("supporting_industry", excluded["topic_selection_role"])


if __name__ == "__main__":
    unittest.main()
