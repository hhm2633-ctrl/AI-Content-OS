"""Independent coverage for the pure ranking/status functions in
modules/trend_collector/trend_collector_module.py.

Priority-2 gap-fill (continuation): `tests/test_trend_retry_policy.py` already covers
`RetryPolicy`/`NatePannCollector`/part of `TrendSourceManager`; this file covers
`TrendCollectorModule._rank_trends`/`_keyword_bonus`/`_build_trend_engine_status`, which the
earlier coverage audit flagged as untested. The module's own constructor pulls in real
`TrendSourceManager`/`TopTopicPicker`/etc. (with real `storage/trends` I/O), so tests here bypass
`__init__` via `__new__` and only set the one real collaborator each pure method actually needs
(`TrendQualityScorer`, itself pure/no I/O) -- no existing module or test file is modified, and no
real `storage/trends/` file is touched by this test.
"""

import unittest

from modules.trend_collector.trend_collector_module import TrendCollectorModule
from modules.trend_collector.trend_quality_scorer import TrendQualityScorer


def _make_module():
    module = TrendCollectorModule.__new__(TrendCollectorModule)
    module.config = {}
    module.quality_scorer = TrendQualityScorer()
    return module


class KeywordBonusTests(unittest.TestCase):
    def setUp(self):
        self.module = _make_module()

    def test_single_bonus_keyword_adds_ten(self):
        self.assertEqual(self.module._keyword_bonus("AI 자동화 소식"), 20)  # AI + 자동화

    def test_no_bonus_keyword_is_zero(self):
        self.assertEqual(self.module._keyword_bonus("완전히 무관한 제목입니다"), 0)

    def test_multiple_bonus_keywords_stack(self):
        score = self.module._keyword_bonus("카드뉴스 수익화 부업 콘텐츠")
        self.assertEqual(score, 40)  # 카드뉴스 + 수익화 + 부업 + 콘텐츠

    def test_empty_keyword_is_zero(self):
        self.assertEqual(self.module._keyword_bonus(""), 0)


class RankTrendsTests(unittest.TestCase):
    def setUp(self):
        self.module = _make_module()

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(self.module._rank_trends([]), [])

    def test_items_without_keyword_are_dropped(self):
        raw = [{"keyword": ""}, {"keyword": "   "}, {"keyword": "실제 주제"}]
        ranked = self.module._rank_trends(raw)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["keyword"], "실제 주제")

    def test_rank_is_reassigned_sequentially_after_sort(self):
        raw = [
            {"keyword": "낮은 점수 주제", "base_score": 10, "weight": 0, "tier": 99},
            {"keyword": "AI 자동화 카드뉴스 수익화", "base_score": 80, "weight": 10, "tier": 1},
        ]
        ranked = self.module._rank_trends(raw)
        ranks = [item["rank"] for item in ranked]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(ranked[0]["rank"], 1)

    def test_higher_base_score_and_bonus_ranks_first(self):
        raw = [
            {"keyword": "평범한 주제 제목입니다 적당한 길이", "base_score": 30, "weight": 0, "tier": 50},
            {"keyword": "AI 자동화로 부업 수익화 하는 카드뉴스 콘텐츠 만들기", "base_score": 60, "weight": 5, "tier": 1},
        ]
        ranked = self.module._rank_trends(raw)
        self.assertEqual(ranked[0]["keyword"], "AI 자동화로 부업 수익화 하는 카드뉴스 콘텐츠 만들기")

    def test_tier_bonus_decreases_as_tier_number_increases(self):
        raw = [
            {"keyword": "동일한 조건의 주제 A", "base_score": 50, "weight": 0, "tier": 1},
            {"keyword": "동일한 조건의 주제 B", "base_score": 50, "weight": 0, "tier": 5},
        ]
        ranked = self.module._rank_trends(raw)
        tier1_item = next(item for item in ranked if item["tier"] == 1)
        tier5_item = next(item for item in ranked if item["tier"] == 5)
        self.assertGreater(tier1_item["score"], tier5_item["score"])

    def test_missing_numeric_fields_default_safely(self):
        raw = [{"keyword": "필드가 거의 없는 항목"}]
        ranked = self.module._rank_trends(raw)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["base_score"], 50)
        self.assertEqual(ranked[0]["tier"], 99)

    def test_result_includes_quality_score_from_scorer(self):
        raw = [{"keyword": "품질 점수가 매겨져야 하는 주제", "base_score": 50, "weight": 0, "tier": 10}]
        ranked = self.module._rank_trends(raw)
        self.assertIn("quality_score", ranked[0])
        self.assertIn("selection_reason", ranked[0])

    def test_is_fallback_flag_is_preserved_as_bool(self):
        raw = [{"keyword": "폴백 항목", "is_fallback": True}]
        ranked = self.module._rank_trends(raw)
        self.assertTrue(ranked[0]["is_fallback"])


class BuildTrendEngineStatusTests(unittest.TestCase):
    def setUp(self):
        self.module = _make_module()

    def test_success_and_failed_sources_are_classified(self):
        summary = {
            "latest": {
                "naver_news": {"source": "naver_news", "attempted": True, "success": True, "collection_method": "live"},
                "nate_pann": {"source": "nate_pann", "attempted": True, "success": False, "collection_method": "unknown"},
            }
        }
        status = self.module._build_trend_engine_status(summary, {"title": "선택된 주제"})
        self.assertIn("naver_news", status["success_sources"])
        self.assertIn("nate_pann", status["failed_sources"])
        self.assertEqual(status["total_sources"], 2)
        self.assertTrue(status["workflow_safe"])

    def test_fallback_source_detected_by_cache_suffix(self):
        summary = {"latest": {"naver_news": {"source": "naver_news", "attempted": True, "success": True, "collection_method": "naver_news_cache"}}}
        status = self.module._build_trend_engine_status(summary, {"title": "x"})
        self.assertIn("naver_news", status["fallback_sources"])

    def test_fallback_source_detected_by_used_cache_flag(self):
        summary = {"latest": {"src": {"source": "src", "attempted": True, "success": True, "used_cache": True}}}
        status = self.module._build_trend_engine_status(summary, {"title": "x"})
        self.assertIn("src", status["fallback_sources"])

    def test_fallback_source_detected_by_fallback_reason(self):
        summary = {"latest": {"src": {"source": "src", "attempted": True, "success": False, "fallback_reason": "network_error"}}}
        status = self.module._build_trend_engine_status(summary, {"title": "x"})
        self.assertIn("src", status["fallback_sources"])

    def test_selected_topic_available_false_when_no_title(self):
        status = self.module._build_trend_engine_status({"latest": {}}, {})
        self.assertFalse(status["selected_topic_available"])

    def test_selected_topic_available_false_when_selected_topic_none(self):
        status = self.module._build_trend_engine_status({"latest": {}}, None)
        self.assertFalse(status["selected_topic_available"])

    def test_selected_topic_available_true_with_title(self):
        status = self.module._build_trend_engine_status({"latest": {}}, {"title": "실제 주제"})
        self.assertTrue(status["selected_topic_available"])

    def test_non_dict_entries_in_latest_are_ignored(self):
        summary = {"latest": {"bad": "not-a-dict", "good": {"source": "good", "attempted": True, "success": True}}}
        status = self.module._build_trend_engine_status(summary, {"title": "x"})
        self.assertEqual(status["total_sources"], 1)

    def test_missing_latest_key_does_not_crash(self):
        status = self.module._build_trend_engine_status({}, {"title": "x"})
        self.assertEqual(status["total_sources"], 0)
        self.assertTrue(status["workflow_safe"])


if __name__ == "__main__":
    unittest.main()
