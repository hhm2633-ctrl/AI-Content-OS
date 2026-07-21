import copy
from datetime import datetime, timedelta, timezone
import unittest

from modules.source_intake.stage2_review_calibrator import calibrate_stage2_reviews


class Stage2ReviewCalibratorTests(unittest.TestCase):
    def _observation(
        self,
        index,
        day,
        category="major_news_policy",
        reviewed_category="major_news_policy",
        decision="GO",
        reviewed_decision="GO",
        evidence_gaps=None,
    ):
        reviewed_at = datetime(2026, 7, 1, 9, tzinfo=timezone.utc) + timedelta(days=day)
        return {
            "candidate_id": f"candidate-{index}",
            "category_id": category,
            "decision": decision,
            "reviewer_id": "human-reviewer-1",
            "reviewer_type": "human",
            "reviewer_label": {
                "category_id": reviewed_category,
                "decision": reviewed_decision,
                "evidence_gaps": list(evidence_gaps or []),
            },
            "reviewed_at": reviewed_at.isoformat(),
        }

    def test_malformed_input_fails_closed(self):
        result = calibrate_stage2_reviews("bad")
        self.assertEqual("closed", result["status"])
        self.assertFalse(result["calibration_ready"])
        self.assertEqual([], result["recommendations"])

    def test_explicit_human_reviewer_and_label_are_required(self):
        missing_reviewer = self._observation(1, 0)
        missing_reviewer.pop("reviewer_id")
        result = calibrate_stage2_reviews([missing_reviewer])
        self.assertEqual("closed", result["status"])
        self.assertEqual("invalid_review_observation", result["reason_code"])

        non_human = self._observation(2, 0)
        non_human["reviewer_type"] = "model"
        self.assertEqual("closed", calibrate_stage2_reviews([non_human])["status"])

    def test_naive_or_invalid_timestamp_fails_closed(self):
        observation = self._observation(1, 0)
        observation["reviewed_at"] = "2026-07-01T09:00:00"
        self.assertEqual("closed", calibrate_stage2_reviews([observation])["status"])

    def test_needs_evidence_label_requires_named_gap(self):
        observation = self._observation(1, 0, reviewed_decision="NEEDS_EVIDENCE")
        result = calibrate_stage2_reviews([observation])
        self.assertEqual("closed", result["status"])

    def test_non_evidence_decision_rejects_contradictory_named_gaps(self):
        observation = self._observation(1, 0, reviewed_decision="GO", evidence_gaps=["open_gap"])
        result = calibrate_stage2_reviews([observation])
        self.assertEqual("closed", result["status"])
        self.assertEqual("invalid_review_observation", result["reason_code"])

    def test_duplicate_candidate_reviewer_pair_fails_closed_without_sample_inflation(self):
        first = self._observation(1, 0)
        duplicate = copy.deepcopy(first)
        duplicate["reviewed_at"] = self._observation(2, 10)["reviewed_at"]
        result = calibrate_stage2_reviews([first, duplicate])
        self.assertEqual("closed", result["status"])
        self.assertEqual("duplicate_review_observation", result["reason_code"])
        self.assertFalse(result["calibration_ready"])

    def test_same_candidate_across_28_reviewers_cannot_make_calibration_ready(self):
        observations = []
        for index in range(28):
            observation = self._observation(1, index % 14)
            observation["reviewer_id"] = f"human-reviewer-{index}"
            observations.append(observation)
        result = calibrate_stage2_reviews(observations)
        self.assertEqual("closed", result["status"])
        self.assertEqual("duplicate_review_observation", result["reason_code"])
        self.assertFalse(result["calibration_ready"])
        self.assertEqual(1, result["summary"]["distinct_candidate_count"])
        self.assertEqual(28, result["summary"]["reviewer_count"])

    def test_short_period_or_small_sample_remains_collecting_without_recommendation(self):
        observations = [self._observation(index, index % 10) for index in range(40)]
        result = calibrate_stage2_reviews(observations)
        self.assertEqual("collecting", result["status"])
        self.assertFalse(result["calibration_ready"])
        self.assertEqual("not_authorized_collecting", result["recommendation_status"])
        self.assertEqual([], result["recommendations"])

    def test_fourteen_days_and_28_reviews_enable_only_unapproved_advice(self):
        observations = []
        for index in range(28):
            reviewed_category = "economy_market" if index < 8 else "major_news_policy"
            observations.append(self._observation(index, index % 14, reviewed_category=reviewed_category))
        result = calibrate_stage2_reviews(observations)
        self.assertEqual("minimum_ready", result["status"])
        self.assertTrue(result["calibration_ready"])
        self.assertFalse(result["target_window_ready"])
        self.assertFalse(result["active_config_changed"])
        self.assertTrue(result["recommendations"])
        self.assertTrue(all(item["approval_status"] == "advisory_unapproved" for item in result["recommendations"]))
        self.assertTrue(all(item["threshold_path"] is None for item in result["recommendations"]))
        self.assertTrue(all(item["maximum_delta"] is None for item in result["recommendations"]))
        self.assertEqual(28, result["summary"]["distinct_candidate_count"])
        self.assertEqual(1, result["summary"]["reviewer_count"])

    def test_category_precision_false_positive_false_negative_and_gaps(self):
        observations = [
            self._observation(1, 0),
            self._observation(2, 1, reviewed_category="economy_market"),
            self._observation(3, 2, category="economy_market", reviewed_category="major_news_policy"),
            self._observation(
                4, 3, decision="GO", reviewed_decision="NEEDS_EVIDENCE",
                evidence_gaps=["independent_origin_confirmation"],
            ),
        ]
        result = calibrate_stage2_reviews(observations)
        metrics = result["categories"]["major_news_policy"]
        self.assertEqual(3, metrics["predicted_count"])
        self.assertEqual(3, metrics["reviewer_positive_count"])
        self.assertEqual(2, metrics["true_positive_count"])
        self.assertEqual(1, metrics["false_positive_count"])
        self.assertEqual(1, metrics["false_negative_count"])
        self.assertEqual({"independent_origin_confirmation": 1}, metrics["evidence_gap_distribution"])

    def test_target_requires_28_days_and_70_in_window_reviews(self):
        observations = [self._observation(index, index % 28) for index in range(70)]
        result = calibrate_stage2_reviews(observations)
        self.assertEqual("target_ready", result["status"])
        self.assertTrue(result["target_window_ready"])
        self.assertEqual(28, result["window"]["elapsed_calendar_days"])

    def test_only_trailing_28_days_from_latest_review_are_aggregated(self):
        observations = [self._observation(1, 0)]
        observations.extend(self._observation(index + 2, 40 + index % 28) for index in range(70))
        result = calibrate_stage2_reviews(observations)
        self.assertEqual(1, result["window"]["excluded_older_observation_count"])
        self.assertEqual(70, result["summary"]["in_window_observation_count"])

    def test_deterministic_and_non_mutating(self):
        observations = [self._observation(index, index % 14) for index in range(28)]
        before = copy.deepcopy(observations)
        first = calibrate_stage2_reviews(observations)
        second = calibrate_stage2_reviews(observations)
        self.assertEqual(first, second)
        self.assertEqual(before, observations)


if __name__ == "__main__":
    unittest.main()
