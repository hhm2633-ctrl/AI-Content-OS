"""CardNews Topic Intelligence Engine V1 coverage.

modules/topic_engine/card_news_topic_intelligence.py의 세 구성요소
(CommunityIssueRadar / InstagramLearningSelector / CardNewsTopicSelector)와
TopicEngineModule 연결을 검증한다. 네트워크/LLM 호출 없음. Instagram
pattern registry는 tempfile로 주입해 실제 knowledge/ 파일에 의존하지 않는다.
"""

import json
import tempfile
import unittest
from pathlib import Path

from modules.topic_engine.card_news_topic_intelligence import (
    CANDIDATE_REFERENCE_LABEL,
    CardNewsTopicIntelligence,
    CommunityIssueRadar,
)
from modules.topic_engine.topic_engine_module import TopicEngineModule


def _item(keyword, source="naver_news", **overrides):
    base = {
        "keyword": keyword,
        "source": source,
        "quality_score": 60,
        "score": 100,
        "link": "",
        "summary": "",
        "publisher": "",
        "published_at": "",
        "collection_method": "live",
        "is_fallback": False,
    }
    base.update(overrides)
    return base


def _write_registry(records):
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".jsonl", delete=False, encoding="utf-8"
    )
    for record in records:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    handle.close()
    return Path(handle.name)


def _candidate_pattern(pattern_id, domain, name):
    return {
        "pattern_id": pattern_id,
        "domain": domain,
        "name": name,
        "status": "CANDIDATE",
        "confidence": 0.5,
        "version": "1.0.0",
    }


QUOTE_REVERSAL = _candidate_pattern(
    "pattern.instagram_learning.content_pattern.quote_reversal_hook",
    "content_pattern",
    "인용·반전형 헤드라인 참고 신호",
)
DM_CTA = _candidate_pattern(
    "pattern.instagram_learning.engagement_mechanic.dm_keyword_cta",
    "engagement_mechanic",
    "댓글 키워드 DM funnel 신호",
)
NUMBERED_LIST = _candidate_pattern(
    "pattern.instagram_learning.content_pattern.numbered_curation_list_structure",
    "content_pattern",
    "번호형 큐레이션 리스트 참고 신호",
)


def _build(trend_result, registry_records=None):
    registry_path = _write_registry(registry_records or [])
    engine = CardNewsTopicIntelligence(registry_path=registry_path)
    try:
        return engine.build(trend_result)
    finally:
        registry_path.unlink(missing_ok=True)


class TitleLengthDoesNotWinTests(unittest.TestCase):
    def test_long_title_only_candidate_is_not_ranked_first(self):
        long_title = (
            "아주아주 길고 길기만 하고 실속은 전혀 없는 그런 게시글 제목이라서 "
            "딱히 카드뉴스로 만들 거리가 보이지 않는 이야기"
        )
        trends = [
            _item(long_title, source="naver_news"),
            _item("전세사기 피해 지원 대책 정리", source="nate_pann",
                  summary="피해자 지원 기준 정리", link="https://pann.nate.com/1"),
            _item("전세사기 피해 지원 대책 총정리", source="fmkorea",
                  summary="지원 대책 반응", link="https://fmkorea.com/1"),
            _item("전세사기 지원 대책 정리 글", source="bobaedream",
                  summary="커뮤니티 반응 모음", link="https://bobaedream.co.kr/1"),
        ]

        result = _build({"trends": trends})
        top = result["top_candidates"][0]

        self.assertNotEqual(top["topic_title"], long_title)
        self.assertIn("전세사기", top["topic_title"])
        # 점수 항목에 제목 길이 기반 항목이 없어야 한다.
        self.assertNotIn("title_length", json.dumps(top["score_breakdown"]))


class SourceRepeatScoreTests(unittest.TestCase):
    def test_issue_repeated_across_communities_gets_repeat_score(self):
        radar = CommunityIssueRadar()
        clusters = radar.build_clusters([
            _item("중고차 허위매물 단속 결과 정리", source="nate_pann"),
            _item("중고차 허위매물 단속 결과", source="fmkorea"),
            _item("중고차 허위매물 단속 결과 후기", source="bobaedream"),
            _item("완전히 다른 별개의 주제 게시글", source="naver_news"),
        ])

        repeated = next(c for c in clusters if "중고차" in c["topic_title"])
        single = next(c for c in clusters if "별개의" in c["topic_title"])

        self.assertGreaterEqual(repeated["scores"]["source_repeat_score"], 85)
        self.assertEqual(single["scores"]["source_repeat_score"], 20)
        self.assertGreater(
            repeated["scores"]["source_repeat_score"],
            single["scores"]["source_repeat_score"],
        )
        self.assertEqual(
            sorted(repeated["community_sources"]),
            ["bobaedream", "fmkorea", "nate_pann"],
        )


class CandidatePatternPolicyTests(unittest.TestCase):
    def test_candidate_pattern_is_reference_only_without_verified_language(self):
        trends = [
            _item("유명 배우 발언 논란 정리", source="nate_pann",
                  summary="발언 전문과 반응 정리", link="https://pann.nate.com/2"),
        ]
        result = _build({"trends": trends}, registry_records=[QUOTE_REVERSAL])
        top = result["top_candidates"][0]

        self.assertTrue(result["instagram_learning_used"])
        self.assertEqual(
            result["instagram_learning_policy"],
            "candidate_patterns_reference_only",
        )

        notes = top["instagram_pattern_notes"]
        self.assertTrue(any(CANDIDATE_REFERENCE_LABEL in note for note in notes))

        serialized = json.dumps(result, ensure_ascii=False)
        for forbidden in ("검증된", "입증된", "proven", "확정 법칙"):
            self.assertNotIn(forbidden, serialized)

        # CANDIDATE 가중치(0.2)는 낮은 참고 신호: hook_fit 보정은 0.5 -> 최대 0.6.
        self.assertLessEqual(top["score_breakdown"]["hook_fit"], 0.6)
        self.assertGreater(top["score_breakdown"]["hook_fit"], 0.5)


class DMCTATests(unittest.TestCase):
    def test_dm_cta_is_never_recommended_and_only_recorded_as_risk(self):
        trends = [
            _item("생활비 절약 꿀팁 정리", source="nate_pann",
                  summary="절약 방법 정리", link="https://pann.nate.com/3"),
        ]
        result = _build({"trends": trends}, registry_records=[DM_CTA, NUMBERED_LIST])

        for candidate in result["top_candidates"]:
            self.assertNotEqual(candidate["cta_recommendation"]["cta_type"], "dm")
            self.assertIn("dm_cta_manipulation_risk", candidate["risk_flags"])


class SourceBindingTests(unittest.TestCase):
    def test_candidate_without_source_binding_is_not_go(self):
        trends = [
            _item("근거 없는 placeholder 주제 정리", source="placeholder",
                  collection_method="placeholder_fallback", is_fallback=True),
        ]
        result = _build({"trends": trends})
        top = result["top_candidates"][0]

        self.assertEqual(top["go_no_go"], "NO_GO")
        self.assertIn("source binding", top["selection_reason"])


class HighRiskNoGoTests(unittest.TestCase):
    def test_high_risk_topics_without_evidence_are_no_go(self):
        risky_titles = [
            "신형 백신 부작용 소문",
            "유명인 구속 기소 소식",
            "대통령 탄핵 관련 주장",
            "연예인 열애 루머 의혹",
        ]

        for title in risky_titles:
            with self.subTest(title=title):
                trends = [
                    _item(title, source="nate_pann", is_fallback=True,
                          collection_method="nate_pann_cache"),
                ]
                result = _build({"trends": trends})
                top = result["top_candidates"][0]
                self.assertEqual(top["go_no_go"], "NO_GO")
                self.assertTrue(top["risk_flags"])

    def test_high_risk_flags_add_evidence_needs(self):
        trends = [
            _item("신형 백신 부작용 소문", source="nate_pann", is_fallback=True,
                  collection_method="nate_pann_cache"),
        ]
        result = _build({"trends": trends})
        top = result["top_candidates"][0]
        self.assertTrue(any("근거" in need for need in top["evidence_needs"]))


class TopicEngineIntegrationTests(unittest.TestCase):
    def test_existing_fields_kept_and_intelligence_field_added(self):
        module = TopicEngineModule()
        trend_result = {
            "selected_topic": {
                "title": "전세사기 피해 지원 대책",
                "quality_score": 70,
                "picked_reason": "테스트",
            },
            "trends": [
                _item("전세사기 피해 지원 대책 정리", source="nate_pann",
                      summary="지원 기준 정리", link="https://pann.nate.com/4"),
            ],
        }

        result = module.run(trend_result)

        # 기존 topic_result 구조 유지
        for field in ("status", "message", "selected_topic", "created_at"):
            self.assertIn(field, result)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "topic_selection_completed")
        self.assertEqual(result["selected_topic"]["keyword"], "전세사기 피해 지원 대책")

        # 신규 필드 추가
        intelligence = result["card_news_topic_intelligence"]
        self.assertEqual(intelligence["status"], "topic_intelligence_completed")
        self.assertLessEqual(intelligence["candidate_count"], 5)
        self.assertGreaterEqual(intelligence["candidate_count"], 1)
        self.assertIn("top_candidates", intelligence)
        self.assertIn("selected_candidate", intelligence)

        top = intelligence["top_candidates"][0]
        for field in (
            "topic_title", "source_cluster", "source_items", "total_score",
            "score_breakdown", "recommended_angle", "hook_candidates",
            "story_structure", "cta_recommendation", "visual_direction",
            "risk_flags", "evidence_needs", "go_no_go", "selection_reason",
        ):
            self.assertIn(field, top)
        self.assertGreaterEqual(len(top["hook_candidates"]), 3)


class FallbackSafetyTests(unittest.TestCase):
    def test_empty_trend_result_produces_fallback_not_failure(self):
        result = CardNewsTopicIntelligence().build({})
        self.assertEqual(result["status"], "topic_intelligence_completed")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["candidate_count"], 0)
        self.assertTrue(result["warnings"])

    def test_none_trend_result_does_not_raise(self):
        result = CardNewsTopicIntelligence().build(None)
        self.assertTrue(result["fallback_used"])

    def test_topic_engine_run_survives_missing_trends(self):
        module = TopicEngineModule()
        result = module.run(None)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "topic_selection_completed")
        intelligence = result["card_news_topic_intelligence"]
        self.assertTrue(intelligence["fallback_used"])
        self.assertEqual(
            intelligence["instagram_learning_policy"],
            "candidate_patterns_reference_only",
        )

    def test_broken_intelligence_engine_does_not_break_topic_engine(self):
        # trends가 이상한 타입이어도 fallback으로 흡수되어야 한다.
        result = CardNewsTopicIntelligence().build({"trends": "not-a-list"})
        self.assertEqual(result["status"], "topic_intelligence_completed")
        self.assertTrue(result["fallback_used"])


if __name__ == "__main__":
    unittest.main()
