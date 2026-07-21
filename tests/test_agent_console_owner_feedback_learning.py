import json
import tempfile
import unittest
from pathlib import Path

from modules.agent_console.owner_feedback_learning import (
    append_owner_feedback_event,
    append_owner_review_feedback,
    build_owner_learning_index,
    classify_feedback_event,
    ensure_owner_learning_index,
    normalize_owner_review_event,
    select_category_learning,
)


class TestOwnerFeedbackLearning(unittest.TestCase):
    def _event(self, event_id="e1", **overrides):
        event = {
            "event_id": event_id,
            "recorded_at": "2026-07-19T00:00:00+09:00",
            "source": "human_owner_chat",
            "feedback_type": "production_quality_correction",
            "category": "fashion_commerce",
            "title": "상품부터 시작하지 않기",
            "owner_decision": "REQUIRE_STORY_FIRST",
            "owner_reason": "이슈와 생활 장면 뒤에 상품을 공개한다.",
            "applies_to": ["fashion", "commerce_storytelling"],
            "is_performance_evidence": False,
            "consumption_status": "ACTIVE",
        }
        event.update(overrides)
        return event

    def test_explicit_direction_becomes_active_owner_rule_not_performance_evidence(self):
        record = classify_feedback_event({**self._event(), "owner_rule_activation": "EXPLICIT"})
        self.assertEqual(record["stage"], "ACTIVE_OWNER_RULE")
        self.assertTrue(record["active"])
        self.assertFalse(record["is_performance_evidence"])
        self.assertEqual(record["categories"], ["fashion"])

    def test_candidate_decision_and_hypothesis_do_not_become_active_rules(self):
        candidate = classify_feedback_event(self._event(feedback_type="candidate_decision"))
        hypothesis = classify_feedback_event(
            self._event(feedback_type="operating_hypothesis", consumption_status="HYPOTHESIS_ONLY")
        )
        self.assertEqual(candidate["stage"], "CLASSIFIED_EXAMPLE")
        self.assertEqual(hypothesis["stage"], "LEARNING_CANDIDATE")
        self.assertFalse(candidate["active"])
        self.assertFalse(hypothesis["active"])

    def test_superseded_rule_is_not_active(self):
        old = {**self._event("old"), "owner_rule_activation": "EXPLICIT"}
        new = {**self._event("new", supersedes_event_id="old", owner_reason="상품은 마지막에 공개한다."), "owner_rule_activation": "EXPLICIT"}
        index = build_owner_learning_index([old, new])
        records = {item["learning_id"]: item for item in index["records"]}
        self.assertEqual(records["old"]["stage"], "SUPERSEDED")
        self.assertFalse(records["old"]["active"])
        self.assertTrue(records["new"]["active"])

    def test_index_rebuilds_once_then_uses_compact_cache_and_selects_relevant_rule(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            feedback = root / "feedback.jsonl"
            index = root / "index.json"
            rows = [
                {**self._event("fashion-story"), "owner_rule_activation": "EXPLICIT"},
                {**self._event(
                    "beauty-hair",
                    category="beauty",
                    title="습한 날 앞머리",
                    owner_reason="습도와 앞머리 고민을 먼저 보여주고 헤어 제품을 연결한다.",
                    applies_to=["beauty", "hair", "humidity"],
                ), "owner_rule_activation": "EXPLICIT"},
            ]
            feedback.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
            first = ensure_owner_learning_index(feedback_path=feedback, index_path=index)
            second = ensure_owner_learning_index(feedback_path=feedback, index_path=index)
            self.assertTrue(first["feedback_log_reloaded"])
            self.assertFalse(second["feedback_log_reloaded"])
            selected, receipt = select_category_learning(
                "beauty",
                {"title": "장마철 습한 날 앞머리 고정"},
                feedback_path=feedback,
                index_path=index,
            )
            self.assertEqual(selected[0]["learning_id"], "beauty-hair")
            self.assertFalse(receipt["feedback_log_reloaded"])

    def test_append_rejects_duplicates_and_refreshes_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            feedback = root / "feedback.jsonl"
            index = root / "index.json"
            result = append_owner_feedback_event(
                {**self._event("new-event"), "owner_rule_activation": "EXPLICIT"}, feedback_path=feedback, index_path=index
            )
            self.assertEqual(result["stats"]["feedback_event_count"], 1)
            self.assertEqual(result["stats"]["active_owner_rule_count"], 1)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                append_owner_feedback_event(
                    {**self._event("new-event"), "owner_rule_activation": "EXPLICIT"}, feedback_path=feedback, index_path=index
                )

    def test_normalized_candidate_review_never_activates_and_tracks_completed_result(self):
        event = normalize_owner_review_event(
            {
                "review_kind": "candidate_evaluation",
                "category": "beauty",
                "candidate_id": "beauty-7",
                "owner_decision": "GRADE_1",
                "owner_reason": "훅이 강하다.",
                "applies_to": ["beauty", "candidate_selection"],
            },
            execution_context={
                "job_id": "job-7",
                "education_receipt": {
                    "prompt_pack_sha256": "abc123",
                    "owner_learning_ids": ["rule-a", "rule-b"],
                },
            },
            result_receipt={"result_receipt_id": "receipt-7", "result_status": "completed"},
        )
        self.assertEqual(event["owner_rule_activation"], "NONE")
        self.assertEqual(event["execution_trace"]["job_id"], "job-7")
        self.assertEqual(event["execution_trace"]["prompt_pack_sha256"], "abc123")
        self.assertEqual(event["execution_trace"]["learning_ids"], ["rule-a", "rule-b"])
        self.assertEqual(event["execution_trace"]["result_receipt_id"], "receipt-7")
        record = classify_feedback_event(event)
        self.assertEqual(record["stage"], "CLASSIFIED_EXAMPLE")
        self.assertFalse(record["active"])

    def test_append_owner_review_is_deterministic_duplicate_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            feedback = root / "feedback.jsonl"
            index = root / "index.json"
            payload = {
                "review_kind": "correction",
                "category": "story",
                "owner_decision": "REVISE",
                "owner_reason": "설명보다 감정선을 먼저 보여준다.",
                "applies_to": ["story", "hook"],
            }
            receipt = append_owner_review_feedback(
                payload, feedback_path=feedback, index_path=index
            )
            self.assertEqual(receipt["learning_record"]["stage"], "ACTIVE_OWNER_RULE")
            self.assertFalse(receipt["learning_record"]["is_performance_evidence"])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                append_owner_review_feedback(
                    payload, feedback_path=feedback, index_path=index
                )

    def test_unmarked_legacy_event_does_not_auto_activate(self):
        record = classify_feedback_event(self._event("legacy", feedback_type="owner_note"))
        self.assertEqual(record["stage"], "CLASSIFIED_PENDING")
        self.assertFalse(record["active"])


if __name__ == "__main__":
    unittest.main()
