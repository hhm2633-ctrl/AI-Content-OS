import unittest

from modules.card_news.workflow_production_preparation import (
    WorkflowProductionPreparation,
)


class FakeCompiler:
    def compile(self, context):
        return {
            "status": "ready",
            "context": context,
            "reference_candidates": [{"reference_id": "owner:1"}],
        }


class FakeMediaBridge:
    def discover(self, request, *, account=""):
        return {
            "status": "completed",
            "query": request["title"],
            "account": account,
            "assets": [],
            "render_assets": [],
        }


class WorkflowProductionPreparationTests(unittest.TestCase):
    def test_connects_learning_and_media_but_blocks_missing_geometry(self):
        result = WorkflowProductionPreparation(
            profile_compiler=FakeCompiler(),
            media_bridge=FakeMediaBridge(),
        ).prepare(
            {"selected_topic": {"title": "검증 주제", "source": "naver_news"}},
            {"body": "확인된 본문"},
        )

        self.assertEqual("prepared", result["status"])
        self.assertEqual("검증 주제", result["media_discovery"]["query"])
        self.assertTrue(
            result["production_learning_profile"]["reference_candidates"]
        )
        self.assertEqual("blocked", result["reference_v2"]["status"])
        self.assertEqual(
            "owner_approved_reference_geometry_required",
            result["reference_v2"]["reason_code"],
        )
        self.assertFalse(result["production_ready"])


if __name__ == "__main__":
    unittest.main()
