import copy
import json
import tempfile
import unittest
from pathlib import Path

from modules.source_intake.candidate_risk_detector import (
    DEFAULT_RULES_PATH,
    RISK_DETECTOR_SCHEMA_VERSION,
    detect_candidate_risks,
)


class CandidateRiskDetectorTests(unittest.TestCase):
    def test_absence_of_keyword_is_undetermined_not_safe(self):
        result = detect_candidate_risks({"title": "여름철 옷장 정리 방법"})
        self.assertEqual("undetermined", result["risk_status"])
        self.assertEqual([], result["hard_risk_flags"])
        self.assertEqual("no_shallow_indicator_detected", result["reason_code"])
        self.assertNotIn("safe", result.values())

    def test_soft_hit_requests_evidence_and_records_location(self):
        result = detect_candidate_risks({"title": "배우 불륜 의혹", "summary": "확인되지 않은 소문"})
        self.assertEqual("needs_evidence", result["risk_status"])
        self.assertIn("defamation", result["soft_risk_flags"])
        self.assertIn("rumor", result["soft_risk_flags"])
        self.assertIn("defamation_claim_corroboration", result["evidence_needs"])
        self.assertTrue(all(set(item) == {"field", "term", "rule", "severity"} for item in result["matched_indicators"]))

    def test_lone_generic_privacy_word_does_not_trigger_doxxing(self):
        result = detect_candidate_risks({"title": "연락처 관리 방법"})
        self.assertNotIn("doxxing", result["hard_risk_flags"])
        self.assertIn("privacy", result["soft_risk_flags"])

    def test_configured_doxxing_combination_blocks(self):
        result = detect_candidate_risks({"title": "신상 공개", "summary": "전화번호와 주소 공개"})
        self.assertEqual("blocked", result["risk_status"])
        self.assertIn("doxxing", result["hard_risk_flags"])
        self.assertIn("privacy", result["soft_risk_flags"])

    def test_minor_word_alone_is_soft_but_sexual_combination_is_hard(self):
        soft = detect_candidate_risks({"title": "청소년 교육 정책"})
        self.assertEqual([], soft["hard_risk_flags"])
        self.assertIn("minor", soft["soft_risk_flags"])

        hard = detect_candidate_risks({"title": "미성년자 성착취 영상"})
        self.assertIn("child_sexual_content", hard["hard_risk_flags"])
        self.assertEqual("blocked", hard["risk_status"])

    def test_graphic_words_require_exploitation_combination(self):
        lone = detect_candidate_risks({"title": "사고 시신 수습"})
        self.assertNotIn("graphic_exploitation", lone["hard_risk_flags"])
        combined = detect_candidate_risks({"title": "시신 원본 영상 공개"})
        self.assertIn("graphic_exploitation", combined["hard_risk_flags"])

    def test_self_harm_method_and_imminent_threat_are_hard(self):
        method = detect_candidate_risks({"title": "자해 방법 단계별"})
        threat = detect_candidate_risks({"summary": "오늘 찾아간다 죽이겠다"})
        self.assertIn("imminent_harm", method["hard_risk_flags"])
        self.assertIn("imminent_harm", threat["hard_risk_flags"])

    def test_illegal_topic_without_instruction_is_not_hard(self):
        topic = detect_candidate_risks({"title": "해킹 사건 수사"})
        instruction = detect_candidate_risks({"title": "계정 탈취 우회법 단계별"})
        self.assertNotIn("illegal_content", topic["hard_risk_flags"])
        self.assertIn("illegal_content", instruction["hard_risk_flags"])

    def test_all_required_soft_flag_families_are_configured(self):
        config = json.loads(Path(DEFAULT_RULES_PATH).read_text(encoding="utf-8"))
        flags = {rule["flag"] for rule in config["soft_rules"]}
        self.assertEqual(
            {
                "privacy", "minor", "crime_claim", "defamation", "rumor", "harassment",
                "financial_claim", "investment_advice", "medical_claim", "legal_claim",
                "political_persuasion", "geopolitical_claim", "efficacy_claim", "price_prediction",
            },
            flags,
        )

    def test_keyword_board_and_category_inputs_are_inspected(self):
        result = detect_candidate_risks(
            {"keyword": ["목표가"], "board_or_category": "투자 추천", "category": "경제"}
        )
        self.assertIn("price_prediction", result["soft_risk_flags"])
        self.assertIn("investment_advice", result["soft_risk_flags"])
        fields = {item["field"] for item in result["matched_indicators"]}
        self.assertIn("keyword", fields)
        self.assertIn("board_or_category", fields)

    def test_detector_is_deterministic_and_non_mutating(self):
        candidate = {"title": "완치 효과 보장", "keyword": ["건강"]}
        before = copy.deepcopy(candidate)
        first = detect_candidate_risks(candidate)
        second = detect_candidate_risks(candidate)
        self.assertEqual(first, second)
        self.assertEqual(before, candidate)
        self.assertEqual(RISK_DETECTOR_SCHEMA_VERSION, first["schema_version"])
        self.assertEqual("initial_unvalidated", first["calibration"])

    def test_invalid_candidate_and_rules_fail_closed(self):
        invalid = detect_candidate_risks(None)
        self.assertEqual("undetermined", invalid["risk_status"])
        self.assertIn("manual_shallow_risk_review", invalid["evidence_needs"])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{}", encoding="utf-8")
            bad_rules = detect_candidate_risks({"title": "test"}, rules_path=path)
        self.assertEqual("invalid", bad_rules["status"])
        self.assertEqual("undetermined", bad_rules["risk_status"])


if __name__ == "__main__":
    unittest.main()
