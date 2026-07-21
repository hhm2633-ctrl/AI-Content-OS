import copy
import unittest

from modules.source_intake.stage2_format_router_bridge import (
    STAGE2_FORMAT_ROUTER_BRIDGE_VERSION,
    route_reviewed_stage2_candidate,
)


def _stage2(**overrides):
    value = {
        "status": "ok",
        "candidate_id": "candidate-1",
        "cluster_id": "cluster-1",
        "decision": "GO",
        "primary_category": "major_news_policy",
        "source_id": "yonhap",
        "source_lane_id": "news_society_economy",
        "source_type": "news",
        "source_refs": [{"source_id": "yonhap", "url": "https://example.com/1"}],
        "hard_risk_flags": [],
        "soft_risk_flags": [],
        "evidence_needs": [],
        "risk_detection_status": "cleared",
        "human_review": {
            "status": "approved",
            "approved": True,
            "reviewer_id": "reviewer-1",
            "reviewer_type": "human",
            "reviewed_at": "2026-07-16T09:00:00+09:00",
            "reviewed_candidate_id": "candidate-1",
            "reviewed_decision": "GO",
            "risk_clearance": "cleared",
        },
        "evidence_bundle": {
            "status": "verified",
            "verified": True,
            "eligible": True,
            "bundle_evidence_needs": [],
            "warnings": [],
            "verified_evidence_items": [{
                "evidence_id": "evidence-1",
                "verification_status": "verified",
                "reviewer_type": "human",
                "reviewed_at": "2026-07-16T09:00:00+09:00",
                "source_url": "https://www.korea.kr/briefing/example",
                "claim_ids": ["claim-1"],
            }],
            "claims": [{
                "claim_id": "claim-1",
                "status": "verified",
                "claim_alignment": True,
                "evidence_needs": [],
                "verified_evidence_ids": ["evidence-1"],
            }],
        },
    }
    value.update(overrides)
    return value


def _format_fit():
    return {
        "card_news": {
            "score": 0.81,
            "confidence": 0.73,
            "eligible": True,
            "reasons": ["precomputed format assessment"],
            "missing_requirements": [],
        },
        "commerce": {
            "score": 0.22,
            "confidence": 0.61,
            "eligible": False,
            "reasons": ["insufficient product evidence"],
            "missing_requirements": ["product_facts"],
        },
    }


class Stage2FormatRouterBridgeTests(unittest.TestCase):
    def test_reviewed_go_calls_existing_router_without_inventing_scores(self):
        result = route_reviewed_stage2_candidate(_stage2(), _format_fit())

        self.assertEqual("routed", result["status"])
        self.assertEqual(STAGE2_FORMAT_ROUTER_BRIDGE_VERSION, result["bridge_schema_version"])
        self.assertTrue(result["router_invoked"])
        self.assertTrue(result["review_gate_passed"])
        self.assertEqual(
            "caller_attested_offline_not_identity_authenticated",
            result["review_attestation"],
        )
        self.assertEqual(1, result["route_count"])
        route = result["routes"][0]
        self.assertEqual(0.81, route["score"])
        self.assertEqual(0.73, route["confidence"])
        self.assertEqual("major_news_policy", route["category_id"])
        self.assertEqual("cleared", route["risk_status"])
        self.assertEqual("verified", route["evidence_status"])
        self.assertEqual("yonhap", route["source_refs"][0]["source_id"])

    def test_non_go_or_non_ok_stage2_fails_before_router(self):
        cases = (
            (_stage2(status="closed"), "stage2_not_ok"),
            (_stage2(decision="WATCH"), "stage2_not_go"),
            (_stage2(decision="NEEDS_EVIDENCE"), "stage2_not_go"),
            (_stage2(decision="REJECT"), "stage2_not_go"),
        )
        for stage2, reason_code in cases:
            with self.subTest(reason_code=reason_code, decision=stage2.get("decision")):
                result = route_reviewed_stage2_candidate(stage2, _format_fit())
                self.assertEqual("closed", result["status"])
                self.assertEqual(reason_code, result["reason_code"])
                self.assertFalse(result["router_invoked"])
                self.assertEqual([], result["routes"])

    def test_human_review_must_be_explicitly_approved(self):
        cases = (
            None,
            True,
            {"status": "approved"},
            {"status": "approved", "approved": True},
            {"status": "pending", "approved": True},
            {"status": "approved", "approved": False},
            {**_stage2()["human_review"], "reviewer_type": "model"},
            {**_stage2()["human_review"], "reviewed_at": "2026-07-16T09:00:00"},
            {**_stage2()["human_review"], "reviewed_candidate_id": "other"},
            {**_stage2()["human_review"], "reviewed_decision": "WATCH"},
            {**_stage2()["human_review"], "risk_clearance": "reviewed"},
        )
        for review in cases:
            with self.subTest(review=review):
                result = route_reviewed_stage2_candidate(_stage2(human_review=review), _format_fit())
                self.assertEqual("human_review_not_approved", result["reason_code"])
                self.assertFalse(result["router_invoked"])

    def test_evidence_bundle_requires_status_verified_and_eligible(self):
        cases = (
            None,
            {"status": "verified", "verified": True},
            {**_stage2()["evidence_bundle"], "verified": False},
            {**_stage2()["evidence_bundle"], "status": "ready"},
            {**_stage2()["evidence_bundle"], "eligible": False},
            {**_stage2()["evidence_bundle"], "bundle_evidence_needs": ["manual_review"]},
            {**_stage2()["evidence_bundle"], "warnings": ["unresolved_metadata"]},
            {**_stage2()["evidence_bundle"], "claims": []},
            {
                **_stage2()["evidence_bundle"],
                "claims": [{
                    "status": "needs_evidence",
                    "claim_alignment": None,
                    "evidence_needs": ["claim_alignment"],
                    "verified_evidence_ids": [],
                }],
            },
            {
                **_stage2()["evidence_bundle"],
                "claims": [{
                    "status": "verified",
                    "claim_alignment": True,
                    "evidence_needs": [],
                    "verified_evidence_ids": [],
                }],
            },
        )
        for evidence in cases:
            with self.subTest(evidence=evidence):
                result = route_reviewed_stage2_candidate(_stage2(evidence_bundle=evidence), _format_fit())
                self.assertEqual("evidence_not_verified_or_eligible", result["reason_code"])
                self.assertFalse(result["router_invoked"])

    def test_any_risk_or_open_evidence_need_blocks(self):
        cases = (
            (_stage2(hard_risk_flags=["doxxing"]), "hard_risk_present"),
            (_stage2(soft_risk_flags=["rumor"]), "soft_risk_present"),
            (_stage2(evidence_needs=["second_source"]), "evidence_needs_present"),
            (_stage2(risk_detection_status="undetermined"), "risk_not_cleared"),
            (_stage2(risk_detection_status="needs_evidence"), "risk_not_cleared"),
            (_stage2(risk_detection_status="blocked"), "risk_not_cleared"),
            (_stage2(risk_detection_status="reviewed"), "risk_not_cleared"),
            (_stage2(risk_detection_status="safe"), "risk_not_cleared"),
        )
        for stage2, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                result = route_reviewed_stage2_candidate(stage2, _format_fit())
                self.assertEqual(reason_code, result["reason_code"])
                self.assertFalse(result["router_invoked"])
                self.assertEqual([], result["routes"])

    def test_malformed_or_missing_gate_fields_fail_closed(self):
        cases = (
            (None, "invalid_stage2_result"),
            (_stage2(candidate_id=""), "missing_candidate_id"),
            (_stage2(primary_category=None), "missing_primary_category"),
            (_stage2(hard_risk_flags=None), "hard_risk_present"),
            (_stage2(soft_risk_flags="none"), "soft_risk_present"),
            (_stage2(evidence_needs=None), "evidence_needs_present"),
        )
        for stage2, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                result = route_reviewed_stage2_candidate(stage2, _format_fit())
                self.assertEqual("closed", result["status"])
                self.assertEqual(reason_code, result["reason_code"])
                self.assertFalse(result["router_invoked"])

    def test_router_owns_format_assessment_validation(self):
        malformed_assessment = {
            "card_news": {
                "score": "invent-me",
                "confidence": 0.8,
                "eligible": True,
                "reasons": [],
                "missing_requirements": [],
            }
        }
        result = route_reviewed_stage2_candidate(_stage2(), malformed_assessment)

        self.assertTrue(result["router_invoked"])
        self.assertTrue(result["review_gate_passed"])
        self.assertEqual("closed", result["status"])
        self.assertEqual("malformed_format_assessment", result["reason_code"])
        self.assertEqual([], result["routes"])

    def test_inputs_are_not_mutated_and_output_is_deterministic(self):
        stage2 = _stage2()
        assessment = _format_fit()
        stage2_before = copy.deepcopy(stage2)
        assessment_before = copy.deepcopy(assessment)

        first = route_reviewed_stage2_candidate(stage2, assessment)
        second = route_reviewed_stage2_candidate(stage2, assessment)

        self.assertEqual(first, second)
        self.assertEqual(stage2_before, stage2)
        self.assertEqual(assessment_before, assessment)

    def test_nonexistent_verified_evidence_reference_cannot_route(self):
        stage2 = _stage2()
        stage2["evidence_bundle"]["claims"][0]["verified_evidence_ids"] = ["not-present"]
        result = route_reviewed_stage2_candidate(stage2, _format_fit())
        self.assertEqual("evidence_not_verified_or_eligible", result["reason_code"])
        self.assertFalse(result["router_invoked"])


if __name__ == "__main__":
    unittest.main()
