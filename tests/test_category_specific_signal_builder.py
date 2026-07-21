import copy
import unittest

from modules.source_intake.category_specific_signal_builder import (
    CATEGORY_SIGNAL_NAMES,
    build_category_specific_signals,
)


def signal(value, reason="measured"):
    return {
        "value": value,
        "status": "observed",
        "provenance": {"source": "test_common"},
        "confidence": 0.8,
        "reason": reason,
    }


def measured_signal(value, reason="measured"):
    record = signal(value, reason)
    record["status"] = "measured"
    return record


class CategorySpecificSignalBuilderTests(unittest.TestCase):
    def test_all_seven_categories_and_exact_weight_names_are_returned(self):
        result = build_category_specific_signals({}, {}, {}, {})
        self.assertEqual("ok", result["status"])
        self.assertEqual(set(CATEGORY_SIGNAL_NAMES), set(result["category_signals"]))
        for category_id, names in CATEGORY_SIGNAL_NAMES.items():
            self.assertEqual(set(names), set(result["category_signals"][category_id]))
            for record in result["category_signals"][category_id].values():
                self.assertEqual(
                    {"value", "status", "provenance", "confidence", "reason"},
                    set(record),
                )

    def test_invalid_input_fails_closed_with_all_missing_records(self):
        result = build_category_specific_signals(None, {}, {}, {})
        self.assertEqual("closed", result["status"])
        self.assertTrue(all(
            record["value"] is None and record["status"] == "missing"
            for category in result["category_signals"].values()
            for record in category.values()
        ))

    def test_policy_impact_requires_explicit_scope_population_or_service(self):
        unsupported = build_category_specific_signals(
            {"title": "정부가 새로운 정책을 발표"}, {}, {}, {},
        )
        self.assertIsNone(unsupported["category_signals"]["major_news_policy"]["public_impact"]["value"])

        supported = build_category_specific_signals(
            {"title": "전국 시행 복지 서비스로 10만 가구 지원"}, {}, {}, {},
        )
        record = supported["category_signals"]["major_news_policy"]["public_impact"]
        self.assertEqual("observed", record["status"])
        self.assertGreaterEqual(record["value"], 0.8)

    def test_incident_crime_keyword_alone_does_not_create_public_interest(self):
        unsupported = build_category_specific_signals({"title": "범죄 사건 논란"}, {}, {}, {})
        self.assertIsNone(unsupported["category_signals"]["incident_conflict"]["public_interest"]["value"])

        supported = build_category_specific_signals(
            {"summary": "소방당국은 긴급 대피와 구조 작업을 진행했고 3명이 부상했다."},
            {}, {}, {},
        )
        self.assertIsNotNone(supported["category_signals"]["incident_conflict"]["public_interest"]["value"])

    def test_economy_everyday_impact_uses_explicit_household_domains(self):
        result = build_category_specific_signals(
            {"title": "기준금리 인상으로 월세와 전기요금 부담 확대"}, {}, {}, {},
        )
        record = result["category_signals"]["economy_market"]["everyday_impact"]
        self.assertEqual("observed", record["status"])
        self.assertIn("rates", record["provenance"]["domains"])
        self.assertIn("bills", record["provenance"]["domains"])

    def test_entertainment_summary_and_attribution_are_separate_evidence(self):
        result = build_category_specific_signals(
            {"summary": "두 배우가 새 작품에서 다시 만난다. 소속사는 공식 입장을 통해 일정을 밝혔다."},
            {}, {}, {},
        )
        category = result["category_signals"]["entertainment_relationship"]
        self.assertEqual("observed", category["narrative_explainability"]["status"])
        self.assertEqual("observed", category["evidence_feasibility"]["status"])
        self.assertIsNone(category["public_relevance"]["value"])

    def test_community_recurrence_and_news_bridge_require_distinct_supplied_sources(self):
        candidate = {
            "source_id": "theqoo",
            "source_refs": [
                {"source_id": "fmkorea"},
                {"source_id": "news1"},
                {"source_id": "theqoo"},
            ],
        }
        result = build_category_specific_signals(candidate, {}, {}, {})
        category = result["category_signals"]["community_buzz"]
        self.assertEqual("observed", category["cross_community_recurrence"]["status"])
        self.assertEqual("observed", category["news_evidence_bridge"]["status"])

        single = build_category_specific_signals({"source_id": "theqoo"}, {}, {}, {})
        self.assertIsNone(single["category_signals"]["community_buzz"]["cross_community_recurrence"]["value"])
        self.assertIsNone(single["category_signals"]["community_buzz"]["news_evidence_bridge"]["value"])

    def test_beauty_signals_use_details_media_and_normalized_likes(self):
        stage1 = {
            "likes": {
                "status": "observed", "normalized_value": 0.75,
                "confidence": 0.7, "basis": "source_topic", "sample_size": 10,
                "raw_value": 30, "value_origin": "visible_metrics",
            }
        }
        candidate = {
            "summary": "선크림 사용법은 먼저 소량을 바르고 2번 덧바르는 순서다.",
            "media_flags": {"has_image": True, "has_video": False, "image_count": 2},
        }
        result = build_category_specific_signals(candidate, stage1, {}, {})
        category = result["category_signals"]["beauty_fashion"]
        self.assertEqual("observed", category["practical_specificity"]["status"])
        self.assertEqual(1.0, category["visuality"]["value"])
        self.assertEqual(0.75, category["positive_reaction"]["value"])

    def test_lifestyle_requires_explicit_actionability_and_durability(self):
        result = build_category_specific_signals(
            {"summary": "매달 점검하는 체크리스트다. 준비물과 3단계 순서를 안내한다."},
            {}, {}, {},
        )
        category = result["category_signals"]["lifestyle_knowledge"]
        self.assertEqual("observed", category["utility_actionability"]["status"])
        self.assertEqual("observed", category["durability_recurrence"]["status"])

    def test_common_and_origin_records_are_copied_without_fit_reuse(self):
        common = {"freshness": signal(0.9), "category_fit": signal(1.0)}
        origin = {
            "origin_independence": {
                "score": 0.8, "confidence": 0.7,
                "independent_origin_count": 2, "origin_groups": ["news1", "newsis"],
                "provenance": [{"source": "resolver"}],
            }
        }
        result = build_category_specific_signals({}, {}, common, origin)
        self.assertEqual(0.9, result["category_signals"]["major_news_policy"]["freshness"]["value"])
        self.assertEqual(0.8, result["category_signals"]["economy_market"]["source_agreement"]["value"])
        self.assertIsNone(result["category_signals"]["entertainment_relationship"]["public_relevance"]["value"])
        self.assertIsNot(common["freshness"], result["category_signals"]["major_news_policy"]["freshness"])

    def test_measured_common_records_and_numeric_strength_alias_are_preserved(self):
        common = {
            "freshness": measured_signal(0.9),
            "reaction_velocity": measured_signal(0.7),
            "information_completeness": measured_signal(0.8),
            "numeric_evidence_strength": measured_signal(0.6),
        }
        result = build_category_specific_signals({}, {}, common, {})
        categories = result["category_signals"]
        self.assertEqual(0.9, categories["major_news_policy"]["freshness"]["value"])
        self.assertEqual(0.7, categories["entertainment_relationship"]["reaction_velocity"]["value"])
        self.assertEqual(0.8, categories["lifestyle_knowledge"]["completeness"]["value"])
        self.assertEqual(0.6, categories["economy_market"]["numeric_evidence"]["value"])
        self.assertEqual("measured", categories["economy_market"]["numeric_evidence"]["status"])

    def test_no_risk_clearance_from_absence_and_input_is_not_mutated(self):
        candidate = {"title": "평범한 생활 정보", "media_flags": {"has_image": False}}
        stage1 = {"likes": {"status": "missing", "normalized_value": None}}
        common = {"explainability": signal(0.6)}
        origin = {}
        snapshots = copy.deepcopy((candidate, stage1, common, origin))
        first = build_category_specific_signals(candidate, stage1, common, origin)
        second = build_category_specific_signals(candidate, stage1, common, origin)
        self.assertEqual(first, second)
        self.assertEqual(snapshots, (candidate, stage1, common, origin))
        self.assertIsNone(first["category_signals"]["incident_conflict"]["risk_clearance"]["value"])


if __name__ == "__main__":
    unittest.main()
