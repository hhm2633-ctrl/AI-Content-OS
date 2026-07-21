import copy
import unittest

from modules.source_intake.candidate_evidence_bundle import (
    CANDIDATE_EVIDENCE_BUNDLE_VERSION,
    build_candidate_evidence_bundle,
)


class CandidateEvidenceBundleTests(unittest.TestCase):
    def test_invalid_candidate_fails_closed_with_unknown_axes(self):
        result = build_candidate_evidence_bundle(None)
        self.assertEqual("closed", result["status"])
        self.assertIsNone(result["factual_origin_evidence"]["score"])
        self.assertIsNone(result["distribution_evidence"]["score"])

    def test_portal_repeats_are_distribution_not_independent_origins(self):
        candidate = {
            "candidate_id": "portal-reposts", "title": "정책 발표",
            "source_id": "naver_news", "publisher": "연합뉴스",
            "source_agreement": {"sources": [
                {"source_id": "naver_news", "publisher": "연합뉴스"},
                {"source_id": "daum_news", "publisher": "연합뉴스"},
                {"source_id": "yonhap", "publisher": "연합뉴스"},
            ]},
        }
        result = build_candidate_evidence_bundle(candidate)
        self.assertEqual(["yonhap"], result["factual_origin_evidence"]["origin_groups"])
        self.assertEqual(1, result["factual_origin_evidence"]["independent_origin_count"])
        self.assertEqual(3, result["distribution_evidence"]["distribution_count"])
        self.assertTrue(all(
            item["factual_origin"] is False
            for item in result["distribution_evidence"]["items"]
        ))

    def test_community_repeats_never_become_factual_news_origins(self):
        result = build_candidate_evidence_bundle({
            "title": "온라인 화제", "source_id": "theqoo",
            "source_refs": [{"source_id": "fmkorea"}, {"source_id": "ruliweb"}],
        })
        self.assertEqual([], result["factual_origin_evidence"]["origin_groups"])
        self.assertEqual(3, result["distribution_evidence"]["distribution_count"])

    def test_distinct_wires_create_multiple_origin_candidates_with_provenance(self):
        result = build_candidate_evidence_bundle({
            "title": "경제 발표", "source_id": "yonhap",
            "source_refs": [{"source_id": "newsis"}, {"source_id": "news1"}],
        })
        factual = result["factual_origin_evidence"]
        self.assertEqual(3, factual["independent_origin_count"])
        self.assertEqual(["news1", "newsis", "yonhap"], factual["origin_groups"])
        self.assertTrue(all(item["claim_alignment"] is None for item in factual["items"]))

    def test_only_supplied_https_official_domain_url_becomes_document_candidate(self):
        result = build_candidate_evidence_bundle({
            "title": "공식 발표", "source_id": "naver_news",
            "source_refs": [
                {"source_id": "naver_news", "link": "https://www.korea.kr/briefing/1"},
                {"source_id": "daum_news", "link": "http://www.korea.kr/briefing/2"},
                {"source_id": "news1", "link": "https://example.com/article"},
            ],
        })
        documents = result["official_document_candidates"]
        self.assertEqual(1, len(documents))
        self.assertEqual("official_domain_identity_only", documents[0]["verification_status"])
        self.assertEqual("unknown", documents[0]["original_document_status"])
        self.assertIsNone(documents[0]["claim_alignment"])

    def test_source_agreement_additive_link_fields_are_used_when_present(self):
        result = build_candidate_evidence_bundle({
            "title": "정부 자료", "source_id": "naver_news",
            "source_agreement": {"sources": [{
                "source_id": "naver_news", "source_type": "news",
                "source_name": "Naver", "title": "정부 자료",
                "link": "https://www.moel.go.kr/news/example",
            }]},
        })
        self.assertEqual(1, len(result["official_document_candidates"]))
        self.assertEqual(
            "source_agreement.sources[0]",
            result["official_document_candidates"][0]["provenance"][0]["location"],
        )

    def test_missing_additive_link_fields_remains_unknown_without_failure(self):
        result = build_candidate_evidence_bundle({
            "title": "정부 자료", "source_id": "naver_news",
            "source_agreement": {"sources": [{"source_id": "naver_news"}]},
        })
        self.assertEqual("ok", result["status"])
        self.assertEqual([], result["official_document_candidates"])

    def test_malformed_https_url_fails_closed_as_non_evidence(self):
        result = build_candidate_evidence_bundle({
            "title": "정부 자료", "source_id": "naver_news",
            "official_url": "https://www.korea.kr:bad/briefing",
        })
        self.assertEqual("ok", result["status"])
        self.assertEqual([], result["official_document_candidates"])

    def test_each_claim_records_declared_and_computed_evidence_needs(self):
        result = build_candidate_evidence_bundle({
            "candidate_id": "claims", "source_id": "yonhap",
            "evidence_needs": ["numeric_source_check"],
            "claims": [
                {"claim_id": "c1", "text": "지원 대상은 10만 명이다", "requires_official_document": True},
                {"claim_id": "c2", "text": "두 번째 주장", "evidence_needs": ["date_confirmation"]},
            ],
        })
        by_id = {claim["claim_id"]: claim for claim in result["claims"]}
        self.assertIn("numeric_source_check", by_id["c1"]["evidence_needs"])
        self.assertIn("official_original_document", by_id["c1"]["evidence_needs"])
        self.assertIn("date_confirmation", by_id["c2"]["evidence_needs"])
        self.assertIn("claim_to_evidence_alignment_review", by_id["c2"]["evidence_needs"])
        self.assertEqual([], by_id["c1"]["verified_evidence_ids"])

    def test_official_candidate_does_not_claim_content_alignment(self):
        result = build_candidate_evidence_bundle({
            "source_id": "naver_news", "title": "정책 주장",
            "claims": [{
                "text": "정책이 내일부터 시행된다",
                "requires_official_document": True,
            }],
            "official_url": "https://www.korea.kr/briefing/policy",
        })
        claim = result["claims"][0]
        self.assertIn("official_original_document", claim["evidence_needs"])
        self.assertIn("claim_to_evidence_alignment_review", claim["evidence_needs"])
        self.assertIsNone(claim["claim_alignment"])
        self.assertEqual(
            result["official_document_candidates"][0]["evidence_id"],
            claim["candidate_evidence_ids"][-1],
        )
        self.assertEqual([], claim["verified_evidence_ids"])

    def test_malformed_claims_fail_closed_but_keep_observed_source_bundle(self):
        result = build_candidate_evidence_bundle({
            "candidate_id": "bad", "source_id": "news1", "claims": "not-a-list",
        })
        self.assertEqual("closed", result["status"])
        self.assertEqual(["news1"], result["factual_origin_evidence"]["origin_groups"])
        self.assertEqual([], result["claims"])

    def test_malformed_nested_source_metadata_is_partial_and_fail_closed(self):
        result = build_candidate_evidence_bundle({
            "title": "자료", "source_id": "naver_news",
            "source_refs": ["bad"], "source_agreement": {"sources": "bad"},
        })
        self.assertEqual("partial", result["status"])
        self.assertTrue(any(item.startswith("malformed_") for item in result["warnings"]))
        self.assertIsNone(result["factual_origin_evidence"]["score"])

    def test_deterministic_non_mutating_and_schema_versioned(self):
        candidate = {
            "candidate_id": "stable", "title": "발표",
            "source_id": "news1", "source_refs": [{"source_id": "newsis"}],
        }
        before = copy.deepcopy(candidate)
        first = build_candidate_evidence_bundle(candidate)
        second = build_candidate_evidence_bundle(candidate)
        self.assertEqual(first, second)
        self.assertEqual(before, candidate)
        self.assertEqual(CANDIDATE_EVIDENCE_BUNDLE_VERSION, first["schema_version"])


if __name__ == "__main__":
    unittest.main()
