import unittest

from modules.research.research_context_builder import ResearchContextBuilder
from modules.research.research_insight_generator import ResearchInsightGenerator


class ClaimingLLMClient:
    def generate_text(self, system_prompt, user_prompt):
        return """{
            "summary": "naver_news에서 검증 주제가 폭발적으로 유행 중입니다.",
            "key_points": ["naver_news가 현재 인기를 확인했습니다."],
            "issue_background": "검증 주제가 naver_news 후보에서 확인됐습니다.",
            "why_trending_now": "naver_news 수집 성공으로 지금 유행 중입니다."
        }"""


class ResearchEvidenceFallbackTest(unittest.TestCase):
    def test_all_fallback_sources_do_not_become_cross_channel_evidence(self):
        generator = ResearchInsightGenerator(llm_client=None)
        result = generator.generate(
            keyword="캐시 주제",
            title="캐시 주제",
            research_context={
                "source_signals": {
                    "naver_news": {
                        "success": False,
                        "is_fallback": True,
                        "collection_method": "settings_keyword_fallback",
                    },
                    "nate_pann": {
                        "success": False,
                        "is_fallback": True,
                        "collection_method": "nate_pann_cache",
                    },
                }
            },
        )

        self.assertTrue(result["fallback_used"])
        self.assertIn("실시간 출처 근거는 없습니다", result["issue_background"])
        self.assertIn("유행한다고 단정할 수 없습니다", result["why_trending_now"])
        self.assertNotIn("여러 채널", result["issue_background"])
        self.assertNotIn("반복적으로 확인", result["why_trending_now"])
        self.assertIn("게시 전 원문과 최신성", result["summary"])
        self.assertNotIn("automation", result["summary"])
        self.assertTrue(any("사용할 수 없습니다" in point for point in result["key_points"]))

    def test_partial_success_without_direct_topic_match_is_not_evidence(self):
        generator = ResearchInsightGenerator(llm_client=ClaimingLLMClient())
        result = generator.generate(
            keyword="검증 주제",
            title="검증 주제",
            research_context={
                "source_signals": {
                    "naver_news": {"success": True, "is_fallback": False},
                    "nate_pann": {"success": False, "is_fallback": True},
                }
            },
        )

        self.assertFalse(result["fallback_used"])
        self.assertIn("실시간 출처 근거는 없습니다", result["issue_background"])
        self.assertNotIn("naver_news", result["issue_background"])
        self.assertNotIn("nate_pann", result["issue_background"])
        self.assertIn("유행한다고 단정할 수 없습니다", result["why_trending_now"])

    def test_malicious_llm_summary_and_key_points_are_replaced_without_direct_match(self):
        generator = ResearchInsightGenerator(llm_client=ClaimingLLMClient())
        result = generator.generate(
            keyword="검증 주제",
            title="검증 주제",
            research_context={
                "source_signals": {
                    "naver_news": {"success": True, "is_fallback": False}
                }
            },
        )

        self.assertIn("게시 전 원문과 최신성", result["summary"])
        self.assertNotIn("폭발적으로 유행", result["summary"])
        self.assertTrue(any("사용할 수 없습니다" in point for point in result["key_points"]))
        self.assertFalse(any("현재 인기를 확인" in point for point in result["key_points"]))

    def test_topic_source_mismatch_is_not_evidence_even_when_marked_confirmed(self):
        generator = ResearchInsightGenerator(llm_client=None)
        result = generator.generate(
            keyword="선정 주제",
            title="선정 주제",
            research_context={
                "source_signals": {
                    "naver_news": {
                        "success": True,
                        "is_fallback": False,
                        "topic_match_confirmed": True,
                        "matched_topic": "다른 주제",
                        "matched_item_url": "https://example.com/other",
                    }
                }
            },
        )

        self.assertIn("실시간 출처 근거는 없습니다", result["issue_background"])
        self.assertNotIn("naver_news", result["issue_background"])

    def test_direct_topic_item_match_can_be_named_as_evidence(self):
        generator = ResearchInsightGenerator(llm_client=None)
        result = generator.generate(
            keyword="직접 확인 주제",
            title="직접 확인 주제",
            research_context={
                "source_signals": {
                    "naver_news": {
                        "success": True,
                        "is_fallback": False,
                        "topic_match_confirmed": True,
                        "matched_topic": "  직접   확인 주제 ",
                        "matched_item_url": "https://example.com/direct",
                    }
                }
            },
        )

        self.assertIn("naver_news", result["issue_background"])
        self.assertIn("직접 연결된 source item", result["issue_background"])
        self.assertIn("추가 사실 검증이 필요", result["why_trending_now"])


class ResearchContextDirectMatchTest(unittest.TestCase):
    def _build_context(self, selected_topic, trend_result):
        builder = ResearchContextBuilder()
        builder._load_trend_result = lambda: trend_result
        return builder.build(selected_topic, {})

    def test_operational_context_passes_direct_topic_item_match(self):
        context = self._build_context(
            selected_topic={"title": "직접 확인 주제", "source": "naver_news"},
            trend_result={
                "collection_summary": {
                    "naver_news": {
                        "attempted": True,
                        "success": True,
                        "collection_method": "naver_news_api",
                    }
                },
                "trends": [
                    {
                        "keyword": "  직접   확인 주제 ",
                        "source": "naver_news",
                        "link": "https://example.com/direct",
                    }
                ],
            },
        )

        signal = context["source_signals"]["naver_news"]
        self.assertTrue(signal["topic_match_confirmed"])
        self.assertEqual(signal["matched_topic"], "직접   확인 주제")
        self.assertEqual(signal["matched_item_url"], "https://example.com/direct")

    def test_operational_context_rejects_topic_mismatch(self):
        context = self._build_context(
            selected_topic={"title": "선정 주제", "source": "naver_news"},
            trend_result={
                "collection_summary": {"naver_news": {"success": True}},
                "trends": [
                    {
                        "keyword": "다른 주제",
                        "source": "naver_news",
                        "link": "https://example.com/other",
                    }
                ],
            },
        )

        signal = context["source_signals"]["naver_news"]
        self.assertFalse(signal["topic_match_confirmed"])
        self.assertEqual(signal["matched_item_url"], "")

    def test_operational_context_rejects_source_mismatch_on_partial_success(self):
        context = self._build_context(
            selected_topic={"title": "선정 주제", "source": "nate_pann"},
            trend_result={
                "collection_summary": {
                    "naver_news": {"success": True},
                    "nate_pann": {"success": False},
                },
                "trends": [
                    {
                        "keyword": "선정 주제",
                        "source": "naver_news",
                        "link": "https://example.com/wrong-source",
                    }
                ],
            },
        )

        self.assertFalse(context["source_signals"]["naver_news"]["topic_match_confirmed"])
        self.assertFalse(context["source_signals"]["nate_pann"]["topic_match_confirmed"])


if __name__ == "__main__":
    unittest.main()
