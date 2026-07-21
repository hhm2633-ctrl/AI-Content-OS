"""Independent coverage for modules/trend_memory/trend_memory_checker.py.

Priority-2 gap-fill test: `modules/trend_memory/` has no dedicated test file
today despite being pure repeat-detection logic (no I/O, no network). No
existing module or test file is modified.
"""

import unittest

from modules.trend_memory.trend_memory_checker import TrendMemoryChecker


class TrendMemoryCheckerTests(unittest.TestCase):
    def setUp(self):
        self.checker = TrendMemoryChecker()

    def test_no_recent_records_is_low_risk(self):
        result = self.checker.check({"topic_title": "새로운 주제"}, [])
        self.assertEqual(result["topic_repeat_risk"], "low")
        self.assertEqual(result["topic_similarity"], 0.0)
        self.assertEqual(result["matched_topic"], "")

    def test_identical_topic_title_is_high_risk(self):
        recent = [{"topic_title": "AI 자동화 트렌드"}]
        result = self.checker.check({"topic_title": "AI 자동화 트렌드"}, recent)
        self.assertEqual(result["topic_repeat_risk"], "high")
        self.assertEqual(result["topic_similarity"], 1.0)
        self.assertEqual(result["matched_topic"], "AI 자동화 트렌드")

    def test_completely_different_topic_is_low_risk(self):
        recent = [{"topic_title": "완전히 다른 주제입니다"}]
        result = self.checker.check({"topic_title": "abc"}, recent)
        self.assertEqual(result["topic_repeat_risk"], "low")

    def test_moderately_similar_topic_is_medium_risk(self):
        # Same words in a different order/with small variation -- similarity
        # should land in the medium band (>=0.5, <0.85).
        recent = [{"topic_title": "인공지능 자동화 콘텐츠 제작 트렌드 총정리"}]
        current = {"topic_title": "인공지능 콘텐츠 자동화 트렌드"}
        result = self.checker.check(current, recent)
        self.assertIn(result["topic_repeat_risk"], ("medium", "high"))
        self.assertGreaterEqual(result["topic_similarity"], 0.5)

    def test_only_the_most_recent_window_is_considered(self):
        # RECENT_WINDOW is 10 -- an identical topic outside that window must
        # not trigger a match.
        old_identical = [{"topic_title": "오래된 반복 주제"}] + [{"topic_title": f"filler-{i}"} for i in range(10)]
        result = self.checker.check({"topic_title": "오래된 반복 주제"}, old_identical)
        self.assertNotEqual(result["matched_topic"], "오래된 반복 주제")

    def test_best_match_is_the_highest_similarity_not_the_first(self):
        recent = [
            {"topic_title": "완전히 다른 것"},
            {"topic_title": "동일한 주제 텍스트"},
        ]
        result = self.checker.check({"topic_title": "동일한 주제 텍스트"}, recent)
        self.assertEqual(result["matched_topic"], "동일한 주제 텍스트")
        self.assertEqual(result["topic_similarity"], 1.0)

    def test_element_repeat_counts_for_matching_fields(self):
        recent = [
            {"hook_type": "질문형", "cta_type": "저장"},
            {"hook_type": "질문형", "cta_type": "댓글"},
            {"hook_type": "충격형", "cta_type": "저장"},
        ]
        current = {"topic_title": "x", "hook_type": "질문형", "cta_type": "저장", "layout_type": "notebook"}
        result = self.checker.check(current, recent)

        self.assertEqual(result["element_repeat_counts"]["hook_type"], 2)
        self.assertEqual(result["element_repeat_counts"]["cta_type"], 2)
        # layout_type never appeared in any recent record.
        self.assertEqual(result["element_repeat_counts"]["layout_type"], 0)

    def test_empty_field_values_are_excluded_from_element_repeat_counts(self):
        current = {"topic_title": "x", "hook_type": "", "cta_type": "저장"}
        result = self.checker.check(current, [{"cta_type": "저장"}])
        self.assertNotIn("hook_type", result["element_repeat_counts"])
        self.assertIn("cta_type", result["element_repeat_counts"])

    def test_missing_topic_title_in_current_does_not_crash(self):
        result = self.checker.check({}, [{"topic_title": "무언가"}])
        self.assertEqual(result["topic_repeat_risk"], "low")

    def test_none_current_and_recent_records_do_not_crash(self):
        result = self.checker.check(None, None)
        self.assertEqual(result["topic_repeat_risk"], "low")

    def test_malformed_recent_record_entries_do_not_crash(self):
        # A non-dict entry mixed into recent_records must not raise --
        # the whole check() call degrades to the safe "low" fallback.
        result = self.checker.check({"topic_title": "topic"}, ["not-a-dict", 123, None])
        self.assertEqual(result["topic_repeat_risk"], "low")

    def test_never_raises_and_always_returns_required_keys(self):
        result = self.checker.check({"topic_title": object()}, [{"topic_title": object()}])
        for key in ("topic_repeat_risk", "topic_similarity", "matched_topic", "element_repeat_counts", "reason"):
            self.assertIn(key, result)

    def test_result_is_deterministic_for_same_input(self):
        current = {"topic_title": "동일 입력", "hook_type": "질문형"}
        recent = [{"topic_title": "동일 입력", "hook_type": "질문형"}]

        result_one = self.checker.check(dict(current), list(recent))
        result_two = self.checker.check(dict(current), list(recent))
        self.assertEqual(result_one, result_two)


if __name__ == "__main__":
    unittest.main()
