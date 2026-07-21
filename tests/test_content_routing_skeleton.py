import unittest

from modules.source_intake.content_production_handoff import (
    build_content_production_handoff,
)
from modules.source_intake.format_fit_router import run_format_fit_router
from modules.source_intake.portfolio_candidate_selector import (
    run_portfolio_candidate_selector,
)
from modules.source_intake.selective_deep_dive_queue import (
    build_selective_deep_dive_queue,
)


class TestContentRoutingSkeleton(unittest.TestCase):
    def test_stages_three_to_six_share_a_fail_safe_contract(self):
        candidate = {
            "candidate_id": "candidate-1",
            "cluster_id": "cluster-1",
            "category_id": "domestic_news",
            "source_refs": [
                {"source_id": "news1", "url": "https://example.com/news1"}
            ],
            "risk_status": "reviewed",
            "evidence_status": "READY",
            "format_fit": {
                format_id: {
                    "score": score,
                    "confidence": confidence,
                    "eligible": True,
                    "reasons": ["precomputed assessment"],
                    "missing_requirements": [],
                }
                for format_id, score, confidence in (
                    ("card_news", 0.9, 0.8),
                    ("shorts_reels", 0.8, 0.7),
                    ("commerce", 0.7, 0.6),
                )
            },
        }

        routed = run_format_fit_router(candidate, min_score=0.5, min_confidence=0.5)
        selected = run_portfolio_candidate_selector(
            routed,
            per_format_limits={
                "card_news": 1,
                "shorts_reels": 1,
                "commerce": 1,
            },
        )
        queue = build_selective_deep_dive_queue(selected)
        handoff = build_content_production_handoff(
            queue,
            {
                "candidate-1": {
                    "candidate_id": "candidate-1",
                    "status": "complete",
                    "evidence_status": "READY",
                    "risk_status": "reviewed",
                    "keyword": "확인된 주제",
                    "title": "확인된 주제 제목",
                    "summary": "확인된 원문을 바탕으로 한 요약",
                    "key_points": ["근거 1", "근거 2"],
                    "target": "일반 독자",
                    "topic_angle": "사실 중심",
                    "source_refs": candidate["source_refs"],
                }
            },
        )

        self.assertEqual(routed["route_count"], 3)
        self.assertEqual(selected["selected_count"], 3)
        self.assertEqual(queue["request_count"], 1)
        self.assertFalse(queue["execution_enabled"])
        self.assertEqual(handoff["status"], "handoff_ready")
        self.assertFalse(handoff["workflow_wired"])
        self.assertFalse(handoff["production_executed"])
        targets = handoff["handoffs"][0]["targets"]
        self.assertEqual(targets[0]["status"], "ready_for_manual_integration")
        self.assertEqual(targets[1]["status"], "planned_not_wired")
        self.assertEqual(targets[2]["status"], "planned_not_wired")


if __name__ == "__main__":
    unittest.main()
