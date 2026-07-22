import unittest

from modules.card_news.account_variable_slide_planner import (
    run_account_variable_slide_planner,
)
from modules.source_intake.same_event_topic_clusterer import (
    run_same_event_topic_clustering,
)
from modules.source_intake.source_field_completeness_audit import (
    analyze_daily_shallow_collection,
)
from modules.source_intake.reviewed_watch_promotion_gate import (
    run_reviewed_watch_promotion_gate,
)
from modules.source_intake.watch_candidate_review_queue import (
    run_watch_candidate_review_queue,
)


class TestSourceFieldCompletenessAudit(unittest.TestCase):
    def test_missing_summary_is_reported_without_inventing_metric_failures(self):
        payload = {
            "schema_version": "daily_shallow_collection_v1",
            "status": "completed",
            "date": "2026-07-16",
            "items": [
                {
                    "source_id": "fmkorea",
                    "title": "테스트 커뮤니티 제목",
                    "link": "https://example.com/post/1",
                    "summary": "",
                    "publisher": "FMKorea",
                    "published_at": "2026-07-16T09:00:00+09:00",
                    "rank_position": 1,
                    "visible_metrics": {"comments": 8, "likes": 14},
                    "is_fallback": False,
                }
            ],
            "source_results": [
                {
                    "source_id": "fmkorea",
                    "status": "success",
                    "expected_metrics": ["rank_position", "comments", "likes"],
                }
            ],
        }

        result = analyze_daily_shallow_collection(payload)

        self.assertEqual(result["status"], "completed")
        report = result["source_reports"]["fmkorea"]
        self.assertEqual(report["fields"]["summary"]["status"], "missing")
        self.assertEqual(report["engagement_metrics"]["views"]["status"], "unsupported")
        self.assertGreater(report["remediation"]["score"], 0)


class TestSameEventTopicClustering(unittest.TestCase):
    @staticmethod
    def _exact_news_items():
        return [
            {
                "source_id": "naver_news",
                "source_type": "news",
                "title": "서울 지하철 운행 정상화 공식 발표",
                "published_at": "2026-07-16T09:00:00+09:00",
                "link": "https://example.com/naver/1",
            },
            {
                "source_id": "yonhap",
                "source_type": "news_wire",
                "title": "서울 지하철 운행 정상화 공식 발표",
                "published_at": "2026-07-16T09:10:00+09:00",
                "link": "https://example.com/yonhap/1",
            },
        ]

    def test_exact_cross_source_news_titles_share_one_cluster(self):
        result = run_same_event_topic_clustering(
            self._exact_news_items(), semantic_scorer=None
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["cluster_count"], 1)
        self.assertEqual(result["clusters"][0]["source_observations_count"], 2)

    def test_semantic_similarity_is_additive_internal_proxy_after_existing_gates(self):
        calls = []

        def fake_scorer(pairs, **kwargs):
            calls.append((pairs, kwargs))
            return {"status": "completed", "scores": [0.94], "errors": []}

        result = run_same_event_topic_clustering(
            self._exact_news_items(), semantic_scorer=fake_scorer
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(result["cluster_count"], 1)
        self.assertTrue(
            any(
                str(reason).startswith("semantic_proxy:")
                for reason in result["clusters"][0]["match_reasons"]
            )
        )
        semantic = result["diagnostics"]["semantic_similarity"]
        self.assertEqual(semantic["status"], "completed")
        self.assertTrue(semantic["not_fact_rights_or_performance_evidence"])

    def test_semantic_similarity_cannot_bypass_existing_jaccard_gate(self):
        calls = []

        def fake_scorer(pairs, **kwargs):
            calls.append((pairs, kwargs))
            return {"status": "completed", "scores": [0.99], "errors": []}

        result = run_same_event_topic_clustering(
            [
                {
                    "source_id": "naver_news",
                    "source_type": "news",
                    "title": "수도권 집중호우 피해 집계",
                    "published_at": "2026-07-16T09:00:00+09:00",
                },
                {
                    "source_id": "yonhap",
                    "source_type": "news_wire",
                    "title": "서울 폭우로 주민 대피",
                    "published_at": "2026-07-16T09:10:00+09:00",
                },
            ],
            semantic_scorer=fake_scorer,
        )

        self.assertEqual(calls, [])
        self.assertEqual(result["cluster_count"], 2)
        self.assertEqual(
            result["diagnostics"]["semantic_similarity"]["status"], "not_needed"
        )

    def test_unavailable_semantic_runtime_falls_back_to_existing_result_visibly(self):
        def unavailable_scorer(pairs, **kwargs):
            return {
                "status": "unavailable",
                "scores": [],
                "errors": ["runtime_missing"],
                "fallback": "existing_deterministic_similarity",
            }

        result = run_same_event_topic_clustering(
            self._exact_news_items(), semantic_scorer=unavailable_scorer
        )

        self.assertEqual(result["cluster_count"], 1)
        semantic = result["diagnostics"]["semantic_similarity"]
        self.assertEqual(semantic["status"], "unavailable")
        self.assertEqual(semantic["fallback"], "existing_deterministic_similarity")


class TestWatchCandidateReviewQueue(unittest.TestCase):
    @staticmethod
    def _watch_candidate(candidate_id="candidate-1", cluster_id="cluster-1"):
        return {
            "status": "ok",
            "decision": "WATCH",
            "candidate_id": candidate_id,
            "cluster_id": cluster_id,
            "representative_title": "검토 대상 뉴스",
            "primary_category": "major_news_policy",
            "category_fit_all": {"major_news_policy": 0.82},
            "category_value_score": 0.74,
            "confidence": 0.68,
            "attention": {"score": 0.77},
            "source_id": "naver_news",
            "source_attribution": ["Naver News"],
            "source_refs": ["https://example.com/news/1"],
            "hard_risk_flags": [],
            "soft_risk_flags": ["needs_context"],
            "evidence_needs": ["official_source"],
            "missing_signals": ["second_source"],
            "risk_detection_status": "undetermined",
            "risk_detector_status": "ok",
            "verification_policy": {
                "eligible": True,
                "verification_tier": "source_attribution_only",
                "fact_checked": False,
                "common_minimum": {"valid": True},
                "provenance": {
                    "risk_detection_status": "undetermined",
                    "risk_detector_status": "ok",
                },
            },
        }

    def test_only_safe_watch_candidate_enters_queue(self):
        safe = self._watch_candidate()
        go = {**self._watch_candidate("candidate-go", "cluster-go"), "decision": "GO"}
        hard_risk = {
            **self._watch_candidate("candidate-risk", "cluster-risk"),
            "hard_risk_flags": ["defamation"],
        }

        result = run_watch_candidate_review_queue([safe, go, hard_risk])

        self.assertEqual(result["status"], "queued")
        self.assertEqual(result["queued_count"], 1)
        self.assertEqual(result["review_state_counts"]["pending"], 1)
        self.assertFalse(result["stage2_decisions_mutated"])
        self.assertFalse(result["production_ready"])
        self.assertEqual(
            {entry["reason_code"] for entry in result["excluded"]},
            {"stage2_decision_not_watch", "hard_risk_not_review_queue_eligible"},
        )

    def test_human_approval_is_recorded_but_never_promotes_stage2(self):
        candidate = self._watch_candidate()
        reviews = {
            "candidate-1": {
                "review_state": "approved",
                "reviewer_id": "owner",
                "reviewer_type": "human",
                "reviewed_at": "2026-07-16T15:00:00+09:00",
                "review_note": "후속 검토 승인",
            }
        }

        result = run_watch_candidate_review_queue([candidate], review_records=reviews)
        entry = result["queue_by_account"]["account_a_news_incident"][0]

        self.assertEqual(entry["review_state"], "approved")
        self.assertEqual(entry["stage2_decision"], "WATCH")
        self.assertEqual(entry["promotion_status"], "not_promoted")
        self.assertFalse(result["approved_means_stage2_go"])
        self.assertEqual(len(result["calibration_observations"]), 1)

    def test_review_without_timezone_fails_closed(self):
        reviews = {
            "candidate-1": {
                "review_state": "hold",
                "reviewer_id": "owner",
                "reviewer_type": "human",
                "reviewed_at": "2026-07-16T15:00:00",
            }
        }

        result = run_watch_candidate_review_queue(
            [self._watch_candidate()], review_records=reviews
        )

        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["reason_code"], "invalid_review_records")


class TestReviewedWatchPromotionGate(unittest.TestCase):
    @staticmethod
    def _candidate():
        return TestWatchCandidateReviewQueue._watch_candidate()

    @staticmethod
    def _review(state="approved", reviewed_category=None):
        review = {
            "review_state": state,
            "reviewer_id": "owner",
            "reviewer_type": "human",
            "reviewed_at": "2026-07-16T15:00:00+09:00",
        }
        if reviewed_category is not None:
            review["reviewed_category"] = reviewed_category
        return review

    def test_approved_fast_path_watch_becomes_separate_routing_candidate(self):
        candidate = self._candidate()
        candidate["primary_category"] = "economy_market"
        candidate["category_fit_all"] = {"economy_market": 0.82}
        candidate["soft_risk_flags"] = []
        candidate["evidence_needs"] = []
        queue = run_watch_candidate_review_queue(
            [candidate], review_records={"candidate-1": self._review()}
        )

        result = run_reviewed_watch_promotion_gate(queue)

        self.assertEqual(result["status"], "promoted")
        self.assertEqual(result["promoted_count"], 1)
        promoted = result["routing_candidates"][0]
        self.assertEqual(promoted["decision"], "GO")
        self.assertEqual(promoted["routing_decision"], "REVIEWED_GO")
        self.assertEqual(promoted["original_stage2_decision"], "WATCH")
        self.assertEqual(
            queue["queue_by_account"]["account_a_news_incident"][0]["stage2_decision"],
            "WATCH",
        )
        self.assertFalse(result["original_stage2_decisions_mutated"])
        self.assertFalse(result["production_ready"])

    def test_hold_and_category_change_never_promote(self):
        hold_candidate = self._candidate()
        hold_candidate["primary_category"] = "economy_market"
        hold_candidate["category_fit_all"] = {"economy_market": 0.82}
        hold_queue = run_watch_candidate_review_queue(
            [hold_candidate],
            review_records={
                "candidate-1": self._review("hold", "incident_conflict")
            },
        )
        hold_result = run_reviewed_watch_promotion_gate(hold_queue)
        self.assertEqual(hold_result["promoted_count"], 0)
        self.assertEqual(hold_result["blocked"][0]["reason_code"], "review_state_not_approved")

        changed_queue = run_watch_candidate_review_queue(
            [hold_candidate],
            review_records={
                "candidate-1": self._review("approved", "incident_conflict")
            },
        )
        changed_result = run_reviewed_watch_promotion_gate(changed_queue)
        self.assertEqual(changed_result["promoted_count"], 0)
        self.assertEqual(
            changed_result["blocked"][0]["reason_code"],
            "category_change_requires_stage2_reclassification",
        )


class TestVariableSlidePlannerConfig(unittest.TestCase):
    def test_json_string_slide_count_keys_are_valid(self):
        result = run_account_variable_slide_planner(
            {
                "account_id": "account_b_issue_story",
                "candidate_id": "candidate-top-1",
                "cluster_id": "cluster-top-1",
                "primary_category": "entertainment_relationship",
                "title": "연예 이슈 테스트",
            }
        )

        self.assertEqual(result["status"], "planning_deferred")
        self.assertEqual(result["reason_code"], "deep_content_required_for_slide_count")
        self.assertEqual(result["slide_count"], 0)

    def test_single_source_breaking_news_does_not_force_one_slide(self):
        result = run_account_variable_slide_planner(
            {
                "account_id": "account_a_news_incident",
                "candidate_id": "candidate-news-1",
                "cluster_id": "cluster-news-1",
                "primary_category": "major_news_policy",
                "topic_signature": "breaking_news",
                "title": "한 장이면 충분한 단신",
                "source_refs": ["https://news.example/1"],
            }
        )

        self.assertEqual(result["status"], "planning_deferred")
        self.assertEqual(result["slide_count"], 0)
        self.assertEqual(result["selected_pattern"]["count_basis"], "deferred_until_deep_content")

    def test_content_supported_twenty_slide_request_is_preserved(self):
        result = run_account_variable_slide_planner(
            {
                "account_id": "account_c_beauty_fashion",
                "candidate_id": "candidate-fashion-20",
                "cluster_id": "cluster-fashion-20",
                "primary_category": "fashion",
                "topic_signature": "beauty_guide",
                "title": "공식 이미지가 풍부한 시즌 컬렉션",
                "requested_slide_count": 20,
            }
        )

        self.assertIn(result["status"], {"planned", "planned_with_fallback"})
        self.assertEqual(result["slide_count"], 20)
        self.assertEqual(len(result["slides"]), 20)


if __name__ == "__main__":
    unittest.main()
