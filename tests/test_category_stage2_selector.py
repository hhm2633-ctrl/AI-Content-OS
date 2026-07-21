import copy
import json
import unittest
from pathlib import Path

from modules.source_intake.category_stage2_selector import (
    CATEGORY_STAGE2_SCHEMA_VERSION,
    DEFAULT_CONFIG_PATH,
    run_category_stage2_selector,
)


class CategoryStage2SelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(Path(DEFAULT_CONFIG_PATH).read_text(encoding="utf-8"))
        cls.taxonomy = cls.config["taxonomy"]

    def _candidate(self, primary="major_news_policy", fit=0.82, signal_value=0.8):
        fit_all = {category_id: 0.1 for category_id in self.taxonomy}
        fit_all[primary] = fit
        category_signals = {
            category_id: {
                signal_name: signal_value
                for signal_name in self.config["categories"][category_id]["weights"]
            }
            for category_id in self.taxonomy
        }
        return {
            "candidate_id": "candidate-1",
            "cluster_id": "cluster-1",
            "source_id": "source-a",
            "source_name": "Source A",
            "source_attribution": "Source A",
            "link": "https://example.com/source-a/story-1",
            "published_at": "2026-07-16T09:00:00+09:00",
            "source_refs": [{"source_id": "source-a"}],
            "stage1_normalized_signals": {
                "attention": 0.73,
                "attention_confidence": 0.68,
            },
            "category_fit_all": fit_all,
            "category_signals": category_signals,
            "origin_independence": {
                "score": 0.8,
                "independent_origin_count": 2,
                "origin_groups": ["origin-a", "origin-b"],
            },
            "distribution_spread": {
                "score": 0.9,
                "distribution_count": 5,
                "portals": ["portal-a", "portal-b"],
            },
            "authoritative_official_origin": False,
            "hard_risk_flags": [],
            "soft_risk_flags": [],
            "evidence_needs": [],
            "risk_detection_status": "cleared",
            "evidence_bundle": {
                "status": "verified", "verified": True, "eligible": True,
                "bundle_evidence_needs": [], "warnings": [],
                "verified_evidence_items": [{
                    "evidence_id": "evidence-1", "verification_status": "verified",
                    "reviewer_type": "human", "reviewed_at": "2026-07-16T10:00:00+09:00",
                    "source_url": "https://www.korea.kr/briefing/example",
                    "claim_ids": ["claim-1"],
                }],
                "claims": [{
                    "claim_id": "claim-1",
                    "status": "verified", "claim_alignment": True,
                    "evidence_needs": [], "verified_evidence_ids": ["evidence-1"],
                }],
            },
            "tags": {
                "international": True,
                "commerce_signal": False,
                "seasonality": "summer",
                "shorts_reels": True,
            },
            "freshness": {"status": "fresh", "age_hours": 3},
        }

    def _mark_verified_official(self, candidate):
        candidate["authoritative_official_origin"] = True
        candidate["authoritative_origin_verification"] = {
            "verified": True,
            "source_url": "https://www.korea.kr/briefing/example",
            "original_document_verified": True,
            "claim_alignment_verified": True,
            "reviewer_type": "human",
        }

    def test_config_has_exact_taxonomy_weights_and_unvalidated_thresholds(self):
        self.assertEqual(7, len(self.taxonomy))
        self.assertEqual("initial_unvalidated", self.config["calibration_status"])
        self.assertNotIn("shorts_reels", self.taxonomy)
        self.assertNotIn("commerce", self.taxonomy)
        for category_id in self.taxonomy:
            self.assertEqual(100, sum(self.config["categories"][category_id]["weights"].values()))

    def test_go_keeps_attention_confidence_and_source_axes_separate(self):
        candidate = self._candidate()
        result = run_category_stage2_selector(candidate)

        self.assertEqual(CATEGORY_STAGE2_SCHEMA_VERSION, result["schema_version"])
        self.assertEqual("GO", result["decision"])
        self.assertEqual("major_news_policy", result["primary_category"])
        self.assertEqual({"score": 0.73, "confidence": 0.68}, result["attention"])
        self.assertEqual(candidate["origin_independence"], result["origin_independence"])
        self.assertEqual(candidate["distribution_spread"], result["distribution_spread"])
        self.assertNotEqual(result["confidence"], result["attention"]["score"])
        self.assertNotIn("shorts_reels", result["tags"])

    def test_go_requires_explicit_risk_clearance_and_verified_claim_evidence(self):
        missing_risk = self._candidate()
        missing_risk.pop("risk_detection_status")
        result = run_category_stage2_selector(missing_risk)
        self.assertEqual("NEEDS_EVIDENCE", result["decision"])
        self.assertIn("risk_clearance_review", result["evidence_needs"])

        unresolved = self._candidate()
        unresolved["evidence_bundle"]["claims"][0]["claim_alignment"] = None
        result = run_category_stage2_selector(unresolved)
        self.assertEqual("NEEDS_EVIDENCE", result["decision"])
        self.assertIn("verified_evidence_bundle_review", result["evidence_needs"])

        malformed_warnings = self._candidate()
        malformed_warnings["evidence_bundle"]["warnings"] = "none"
        result = run_category_stage2_selector(malformed_warnings)
        self.assertEqual("NEEDS_EVIDENCE", result["decision"])

        blank_evidence_id = self._candidate()
        blank_evidence_id["evidence_bundle"]["claims"][0]["verified_evidence_ids"] = [" "]
        result = run_category_stage2_selector(blank_evidence_id)
        self.assertEqual("NEEDS_EVIDENCE", result["decision"])

        nonexistent_evidence_id = self._candidate()
        nonexistent_evidence_id["evidence_bundle"]["claims"][0]["verified_evidence_ids"] = ["not-present"]
        result = run_category_stage2_selector(nonexistent_evidence_id)
        self.assertEqual("NEEDS_EVIDENCE", result["decision"])

    def test_malformed_verified_official_url_cannot_raise_or_bypass(self):
        for source_url in ("https://[", "https://www.korea.kr:bad/x", "https://www.korea.kr:8443/x"):
            candidate = self._candidate(primary="major_news_policy")
            candidate["origin_independence"] = {"score": 0.0, "independent_origin_count": 1}
            candidate["authoritative_official_origin"] = True
            candidate["authoritative_origin_verification"] = {
                "verified": True, "source_url": source_url,
                "original_document_verified": True,
                "claim_alignment_verified": True,
                "reviewer_type": "human",
            }
            candidate["evidence_bundle"] = {}
            result = run_category_stage2_selector(candidate)
            self.assertEqual("NEEDS_EVIDENCE", result["decision"])
            self.assertIn("verified_evidence_bundle_review", result["evidence_needs"])

    def test_missing_news_attention_is_not_scored_as_zero(self):
        candidate = self._candidate(signal_value=0.8)
        candidate["category_signals"]["major_news_policy"]["attention"] = None
        self._mark_verified_official(candidate)
        candidate["origin_independence"]["score"] = 0.1

        result = run_category_stage2_selector(candidate)

        self.assertEqual("GO", result["decision"])
        self.assertEqual(0.8, result["category_value_score"])
        self.assertIn("attention", result["missing_signals"])
        self.assertNotIn("independent_origin_confirmation", result["evidence_needs"])

    def test_official_origin_exception_does_not_require_two_news_sources(self):
        candidate = self._candidate(primary="economy_market")
        candidate["origin_independence"] = {"score": 0.0, "independent_origin_count": 1}
        candidate["distribution_spread"] = {"score": 1.0, "distribution_count": 12}
        self._mark_verified_official(candidate)
        candidate["evidence_needs"] = ["second_independent_source"]

        result = run_category_stage2_selector(candidate)

        self.assertEqual("GO", result["decision"])
        self.assertEqual([], result["evidence_needs"])
        self.assertEqual(0.0, result["origin_independence"]["score"])
        self.assertEqual(1.0, result["distribution_spread"]["score"])

    def test_fast_path_category_can_use_attribution_without_origin_inflation(self):
        candidate = self._candidate(primary="entertainment_relationship")
        candidate["origin_independence"] = {"score": 0.1, "independent_origin_count": 1}
        candidate["distribution_spread"] = {"score": 1.0, "distribution_count": 20}

        result = run_category_stage2_selector(candidate)

        self.assertEqual("GO", result["decision"])
        self.assertEqual("source_attribution_only", result["verification_policy"]["verification_tier"])
        self.assertNotIn("independent_origin_confirmation", result["evidence_needs"])

    def test_uncategorized_fit_bands_are_explicit(self):
        watch_candidate = self._candidate(fit=0.4)
        watch_result = run_category_stage2_selector(watch_candidate)
        self.assertIsNone(watch_result["primary_category"])
        self.assertEqual("uncategorized", watch_result["routing_state"])
        self.assertEqual("WATCH", watch_result["decision"])

        reject_candidate = self._candidate(fit=0.29)
        reject_result = run_category_stage2_selector(reject_candidate)
        self.assertIsNone(reject_result["primary_category"])
        self.assertEqual("REJECT", reject_result["decision"])

    def test_risk_sensitive_tie_selects_stricter_category(self):
        candidate = self._candidate(primary="major_news_policy", fit=0.8)
        candidate["category_fit_all"]["incident_conflict"] = 0.8
        candidate["authoritative_official_origin"] = True

        result = run_category_stage2_selector(candidate)

        self.assertEqual("incident_conflict", result["primary_category"])

    def test_community_is_primary_only_when_it_clearly_leads_subject_category(self):
        close_candidate = self._candidate(primary="community_buzz", fit=0.8)
        close_candidate["category_fit_all"]["beauty_fashion"] = 0.77
        close_result = run_category_stage2_selector(close_candidate)
        self.assertEqual("beauty_fashion", close_result["primary_category"])

        native_candidate = self._candidate(primary="community_buzz", fit=0.9)
        native_candidate["category_fit_all"]["beauty_fashion"] = 0.6
        native_result = run_category_stage2_selector(native_candidate)
        self.assertEqual("community_buzz", native_result["primary_category"])

    def test_secondary_categories_are_bounded_and_deterministic(self):
        candidate = self._candidate(primary="major_news_policy", fit=0.8)
        candidate["category_fit_all"].update(
            {
                "economy_market": 0.75,
                "lifestyle_knowledge": 0.7,
                "beauty_fashion": 0.69,
            }
        )
        candidate["authoritative_official_origin"] = True

        first = run_category_stage2_selector(candidate)
        second = run_category_stage2_selector(candidate)

        self.assertEqual(first, second)
        self.assertEqual(2, len(first["secondary_categories"]))
        self.assertEqual(
            ["economy_market", "lifestyle_knowledge"],
            [item["category_id"] for item in first["secondary_categories"]],
        )

    def test_hard_and_soft_risks_apply_different_gates(self):
        hard_candidate = self._candidate()
        hard_candidate["hard_risk_flags"] = ["doxxing"]
        self.assertEqual("REJECT", run_category_stage2_selector(hard_candidate)["decision"])

        soft_candidate = self._candidate()
        soft_candidate["soft_risk_flags"] = ["rumor"]
        soft_candidate["risk_detection_status"] = "undetermined"
        self.assertEqual("NEEDS_EVIDENCE", run_category_stage2_selector(soft_candidate)["decision"])

    def test_lane_hn_normalized_metric_records_are_accepted_without_mutation(self):
        candidate = self._candidate()
        candidate["stage1_normalized_signals"]["views"] = {
            "raw_value": 10000,
            "normalized_value": 0.72,
            "status": "observed",
            "basis": "source_category_window",
            "sample_size": 20,
            "confidence": 0.8,
            "value_origin": "live",
        }
        before = copy.deepcopy(candidate)

        result = run_category_stage2_selector(candidate)

        self.assertEqual("GO", result["decision"])
        self.assertEqual(before, candidate)

    def test_direct_raw_metric_value_is_rejected(self):
        candidate = self._candidate()
        candidate["stage1_normalized_signals"]["views"] = 10000

        result = run_category_stage2_selector(candidate)

        self.assertEqual("REJECT", result["decision"])
        self.assertEqual("raw_metrics_prohibited", result["reason_code"])

    def test_all_missing_category_signals_remain_none_not_zero(self):
        candidate = self._candidate()
        candidate["category_signals"]["major_news_policy"] = {
            name: None
            for name in self.config["categories"]["major_news_policy"]["weights"]
        }
        result = run_category_stage2_selector(candidate)
        self.assertIsNone(result["category_value_score"])
        self.assertIsNone(result["category_value_all"]["major_news_policy"]["score"])

    def test_bare_official_boolean_cannot_bypass_origin_evidence(self):
        candidate = self._candidate(primary="major_news_policy")
        candidate["origin_independence"] = {"score": 0.0, "independent_origin_count": 1}
        candidate["authoritative_official_origin"] = True
        candidate["evidence_bundle"] = {}
        result = run_category_stage2_selector(candidate)
        self.assertFalse(result["authoritative_official_origin"])
        self.assertEqual("NEEDS_EVIDENCE", result["decision"])
        self.assertIn("verified_evidence_bundle_review", result["evidence_needs"])

    def test_unallowlisted_official_url_cannot_bypass_evidence(self):
        candidate = self._candidate(primary="major_news_policy")
        candidate["origin_independence"] = {"score": 0.0, "independent_origin_count": 1}
        candidate["authoritative_official_origin"] = True
        candidate["authoritative_origin_verification"] = {
            "verified": True,
            "source_url": "https://example.com/claim",
        }
        candidate["evidence_bundle"] = {}
        result = run_category_stage2_selector(candidate)
        self.assertFalse(result["authoritative_official_origin"])
        self.assertEqual("NEEDS_EVIDENCE", result["decision"])

    def test_unknown_origin_remains_none_and_requires_evidence(self):
        candidate = self._candidate(primary="major_news_policy")
        candidate["origin_independence"] = {
            "score": None,
            "independent_origin_count": 0,
            "unresolved": ["portal_underlying_origin_unknown"],
        }
        candidate["evidence_bundle"] = {}
        result = run_category_stage2_selector(candidate)
        self.assertIsNone(result["origin_independence"]["score"])
        self.assertEqual("NEEDS_EVIDENCE", result["decision"])
        self.assertIn("verified_evidence_bundle_review", result["evidence_needs"])


if __name__ == "__main__":
    unittest.main()
