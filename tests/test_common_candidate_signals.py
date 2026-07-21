import copy
import unittest

from modules.source_intake.common_candidate_signals import build_common_candidate_signals


class CommonCandidateSignalsTests(unittest.TestCase):
    def _candidate(self):
        return {
            "title": "해외 여름 할인 상품 20% 비교하는 법",
            "summary": "가격이 낮아진 이유를 설명합니다. 1. 준비물 확인 2. 구매 순서 확인",
            "publisher": "example",
            "link": "https://example.com/item",
            "published_at": "2026-07-16T00:00:00+09:00",
            "collected_at": "2026-07-16T06:00:00+09:00",
        }

    def _stage1(self):
        return {
            "comments": {"status": "observed", "raw_value": 0, "normalized_value": 0.2, "confidence": 0.8},
            "likes": {"status": "observed", "raw_value": 10, "normalized_value": 0.8, "confidence": 0.9},
        }

    def test_complete_result_has_evidence_labeled_signal_and_tag_records(self):
        result = build_common_candidate_signals(self._candidate(), self._stage1())
        self.assertEqual("ok", result["status"])
        self.assertEqual(
            {
                "freshness", "reaction_velocity", "novelty", "numeric_evidence_strength",
                "information_completeness", "practical_actionability", "explainability",
            },
            set(result["signals"]),
        )
        for record in [*result["signals"].values(), *result["tags"].values()]:
            self.assertEqual({"value", "status", "provenance", "confidence", "reason"}, set(record))

    def test_is_deterministic_and_does_not_mutate_inputs(self):
        candidate = self._candidate()
        stage1 = self._stage1()
        before_candidate = copy.deepcopy(candidate)
        before_stage1 = copy.deepcopy(stage1)
        first = build_common_candidate_signals(candidate, stage1)
        second = build_common_candidate_signals(candidate, stage1)
        self.assertEqual(first, second)
        self.assertEqual(before_candidate, candidate)
        self.assertEqual(before_stage1, stage1)

    def test_iso_and_rfc2822_timestamps_are_supported(self):
        iso = build_common_candidate_signals(self._candidate(), self._stage1())
        self.assertEqual(6.0, iso["signals"]["freshness"]["provenance"]["age_hours"])

        candidate = self._candidate()
        candidate["published_at"] = "Thu, 16 Jul 2026 00:00:00 +0900"
        rfc = build_common_candidate_signals(candidate, self._stage1())
        self.assertEqual("measured", rfc["signals"]["freshness"]["status"])
        self.assertEqual(6.0, rfc["signals"]["novelty"]["provenance"]["age_hours"])

    def test_reaction_velocity_requires_timestamps_and_an_observed_normalized_reaction(self):
        no_time = self._candidate()
        no_time.pop("collected_at")
        self.assertIsNone(build_common_candidate_signals(no_time, self._stage1())["signals"]["reaction_velocity"]["value"])

        missing_reactions = {"likes": {"status": "missing", "raw_value": None, "normalized_value": None}}
        result = build_common_candidate_signals(self._candidate(), missing_reactions)
        self.assertEqual("missing", result["signals"]["reaction_velocity"]["status"])

        raw_only = {"likes": {"status": "observed", "raw_value": 10, "normalized_value": None}}
        result = build_common_candidate_signals(self._candidate(), raw_only)
        self.assertIsNone(result["signals"]["reaction_velocity"]["value"])

    def test_explicit_zero_reaction_is_observed_not_missing(self):
        stage1 = {"comments": {"status": "observed", "raw_value": 0, "normalized_value": 0.0, "confidence": 0.7}}
        record = build_common_candidate_signals(self._candidate(), stage1)["signals"]["reaction_velocity"]
        self.assertEqual("measured", record["status"])
        self.assertEqual(0.0, record["value"])

    def test_invalid_or_negative_age_stays_missing(self):
        candidate = self._candidate()
        candidate["published_at"] = "not-a-date"
        result = build_common_candidate_signals(candidate, self._stage1())
        self.assertIsNone(result["signals"]["freshness"]["value"])
        self.assertIsNone(result["signals"]["novelty"]["value"])

        candidate = self._candidate()
        candidate["published_at"] = "2026-07-17T00:00:00+09:00"
        self.assertIsNone(build_common_candidate_signals(candidate, self._stage1())["signals"]["freshness"]["value"])

    def test_numeric_evidence_requires_units_or_explicit_ratios(self):
        candidate = self._candidate()
        result = build_common_candidate_signals(candidate, {})
        self.assertGreater(result["signals"]["numeric_evidence_strength"]["value"], 0.0)
        self.assertIn("20%", result["signals"]["numeric_evidence_strength"]["provenance"]["matches_by_field"]["title"])

        candidate["title"] = "2026년 발표"
        candidate["summary"] = "표본은 3대 2 비율이다"
        self.assertGreater(build_common_candidate_signals(candidate, {})["signals"]["numeric_evidence_strength"]["value"], 0.0)

        candidate["title"] = "숫자 2026 하나만 적힌 제목"
        candidate["summary"] = "단위가 없는 숫자 1234"
        self.assertEqual(0.0, build_common_candidate_signals(candidate, {})["signals"]["numeric_evidence_strength"]["value"])

    def test_information_completeness_is_field_presence_not_content_quality(self):
        candidate = {"title": "제목", "summary": "요약"}
        record = build_common_candidate_signals(candidate, {})["signals"]["information_completeness"]
        self.assertEqual(0.6, record["value"])
        self.assertIn("publisher", record["provenance"]["missing_fields"])

    def test_actionability_uses_only_explicit_structure_markers(self):
        structured = build_common_candidate_signals(self._candidate(), {})["signals"]["practical_actionability"]
        self.assertGreaterEqual(structured["value"], 0.75)

        plain = {"title": "새로운 생활 이야기", "summary": "오늘 있었던 일을 전한다."}
        record = build_common_candidate_signals(plain, {})["signals"]["practical_actionability"]
        self.assertEqual(0.0, record["value"])
        self.assertEqual("observed", record["status"])

    def test_explainability_combines_markers_and_summary_completeness(self):
        result = build_common_candidate_signals(self._candidate(), {})["signals"]["explainability"]
        self.assertGreater(result["value"], 0.0)
        self.assertIn("cause", result["provenance"]["matched_marker_groups"])
        self.assertIn("summary_completeness", result["provenance"]["components"])

    def test_auxiliary_tags_are_lexicon_evidence_not_categories(self):
        tags = build_common_candidate_signals(self._candidate(), {})["tags"]
        self.assertTrue(tags["international"]["value"])
        self.assertTrue(tags["commerce_signal"]["value"])
        self.assertEqual(["summer"], tags["seasonality"]["value"])
        for tag in tags.values():
            self.assertIn("matches", str(tag["provenance"]))

    def test_text_absence_and_malformed_inputs_fail_closed_without_fabricated_zero(self):
        empty = build_common_candidate_signals({}, {})
        self.assertIsNone(empty["signals"]["numeric_evidence_strength"]["value"])
        self.assertIsNone(empty["signals"]["information_completeness"]["value"])
        self.assertIsNone(empty["tags"]["international"]["value"])

        malformed = build_common_candidate_signals([], None)
        self.assertEqual("closed", malformed["status"])
        self.assertTrue(all(record["value"] is None for record in malformed["signals"].values()))


if __name__ == "__main__":
    unittest.main()
