import copy
import unittest

from modules.source_intake.content_production_handoff import (
    build_content_production_handoff,
)


def _queue(*formats):
    return {
        "status": "queue_ready",
        "execution_enabled": False,
        "requests": [
            {
                "candidate_id": "c1",
                "requested_formats": list(formats),
                "status": "planned",
                "execution_enabled": False,
            }
        ],
    }


def _bundle(**overrides):
    value = {
        "candidate_id": "c1",
        "status": "complete",
        "evidence_status": "READY",
        "risk_status": "reviewed",
        "keyword": "검증된 주제",
        "title": "검증된 주제 제목",
        "summary": "확인된 원문과 근거를 요약한 내용",
        "key_points": ["근거 1", "근거 2"],
        "target": "일반 독자",
        "topic_angle": "사실 중심 설명",
        "source_refs": [{"source_id": "news1", "url": "https://example.com/1"}],
    }
    value.update(overrides)
    return value


class TestContentProductionHandoff(unittest.TestCase):
    def test_missing_completed_bundle_blocks_production(self):
        result = build_content_production_handoff(_queue("card_news"), {})
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["workflow_wired"])
        self.assertFalse(result["production_executed"])
        self.assertEqual(result["handoffs"][0]["reason_code"], "deep_dive_not_completed")

    def test_ready_evidence_builds_existing_content_input_without_execution(self):
        result = build_content_production_handoff(
            _queue("card_news"),
            {"c1": _bundle()},
        )
        self.assertEqual(result["status"], "handoff_ready")
        target = result["handoffs"][0]["targets"][0]
        self.assertEqual(target["status"], "ready_for_manual_integration")
        self.assertEqual(target["target_contract"], "ContentModule.run(research_result)")
        self.assertEqual(target["payload"]["summary"], "확인된 원문과 근거를 요약한 내용")
        self.assertEqual(target["payload"]["key_points"], ["근거 1", "근거 2"])
        self.assertFalse(result["workflow_wired"])
        self.assertFalse(result["production_executed"])

    def test_missing_evidence_is_not_fabricated(self):
        result = build_content_production_handoff(
            _queue("card_news"),
            {"c1": _bundle(summary="")},
        )
        target = result["handoffs"][0]["targets"][0]
        self.assertEqual(target["status"], "blocked")
        self.assertIsNone(target["payload"])
        self.assertIn("summary", target["missing_requirements"])

    def test_shorts_and_commerce_remain_explicitly_not_wired(self):
        result = build_content_production_handoff(
            _queue("shorts_reels", "commerce"),
            {"c1": _bundle()},
        )
        targets = result["handoffs"][0]["targets"]
        self.assertEqual([target["status"] for target in targets], [
            "planned_not_wired",
            "planned_not_wired",
        ])
        self.assertEqual(result["status"], "blocked")

    def test_unready_or_risk_blocked_evidence_stays_blocked(self):
        evidence_result = build_content_production_handoff(
            _queue("card_news"), {"c1": _bundle(evidence_status="NEEDS_EVIDENCE")}
        )
        risk_result = build_content_production_handoff(
            _queue("card_news"), {"c1": _bundle(risk_status="BLOCKED")}
        )
        self.assertEqual(evidence_result["handoffs"][0]["reason_code"], "evidence_not_ready")
        self.assertEqual(risk_result["handoffs"][0]["reason_code"], "risk_blocked")

    def test_unknown_risk_cannot_reach_production_handoff(self):
        result = build_content_production_handoff(
            _queue("card_news"), {"c1": _bundle(risk_status="unknown")}
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["handoffs"][0]["reason_code"], "risk_not_cleared")

    def test_inputs_are_not_mutated(self):
        queue = _queue("card_news")
        bundles = {"c1": _bundle()}
        expected_queue = copy.deepcopy(queue)
        expected_bundles = copy.deepcopy(bundles)
        build_content_production_handoff(queue, bundles)
        self.assertEqual(queue, expected_queue)
        self.assertEqual(bundles, expected_bundles)


if __name__ == "__main__":
    unittest.main()
