import unittest

from modules.card_news.production_package_pipeline import (
    build_package_from_completed_handoff,
    normalize_completed_handoff,
)


class CardNewsProductionPackagePipelineTests(unittest.TestCase):
    def setUp(self):
        self.candidate = {
            "candidate_id": "A-1",
            "account": "A",
            "category": "국내뉴스",
            "title": "폭우 대응 단계 격상",
            "source_urls": ["https://news.example/item"],
        }
        self.handoff = {
            "summary": "공개 기사에 나온 대응 단계와 시민 안내를 정리한다.",
            "outputs": {
                "cardnews_plan": {
                    "slides": [
                        "1 훅: 비상 대응 단계 격상",
                        "2 상황: 취약 구간 점검이 시작됐다",
                    ],
                    "caption_draft": "공개 기사에 나온 대응 상황을 짧게 정리했습니다.",
                }
            },
        }

    def test_normalizes_only_completed_copy_and_source_references(self):
        result = normalize_completed_handoff(self.candidate, self.handoff)
        self.assertEqual(result["deep_bundle"]["status"], "completed")
        self.assertEqual(len(result["deep_bundle"]["planned_slides"]), 2)
        self.assertEqual(result["deep_bundle"]["assets"][0]["rights_status"], "reference_only")

    def test_builds_approved_package_but_keeps_render_and_publish_blocked(self):
        result = build_package_from_completed_handoff(
            self.candidate,
            self.handoff,
            {
                "status": "approved",
                "scope": "production_package",
                "candidate_id": "A-1",
                "approved_by": "owner_delegate",
                "receipt_id": "approval-1",
            },
        )
        package = result["package"]
        self.assertEqual(package["status"], "production_package_ready")
        self.assertEqual(len(package["slides"]), 2)
        self.assertTrue(package["gates"]["package_approval"]["approved"])
        self.assertFalse(package["gates"]["render"]["authorized"])
        self.assertFalse(package["gates"]["publish"]["authorized"])


if __name__ == "__main__":
    unittest.main()
