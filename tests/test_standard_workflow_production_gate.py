import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from modules.image_generation.image_generation_module import ImageGenerationModule
from src.workflow_engine import WorkflowEngine


class StandardWorkflowProductionGateTest(unittest.TestCase):
    def test_image_api_is_not_called_without_controller_authorization(self):
        module = ImageGenerationModule({})
        with mock.patch.object(module, "_generate_image") as generate:
            result = module.run({"image_prompts": ["must not run"]})

        generate.assert_not_called()
        self.assertEqual(result["status"], "image_generation_blocked")
        self.assertFalse(result["external_api_called"])

    def test_expired_or_incomplete_authorization_is_rejected(self):
        expired = {
            "authorized": True,
            "authorization_id": "auth-1",
            "candidate_id": "candidate-1",
            "approved_by": "owner",
            "controller_state_hash": "a" * 64,
            "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            "scope": ["image_generation"],
        }
        self.assertFalse(ImageGenerationModule._has_controller_authorization({"production_authorization": expired}))
        self.assertFalse(ImageGenerationModule._has_controller_authorization({"production_authorization": {"authorized": True}}))

    def test_standard_workflow_returns_blocked_non_publishing_results(self):
        card_news, publishing, manifest = WorkflowEngine._build_blocked_standard_production_results(
            {"status": "image_generation_blocked"}
        )

        self.assertEqual(card_news["cards"], [])
        self.assertFalse(card_news["production_ready"])
        self.assertFalse(publishing["actual_publish"])
        self.assertFalse(publishing["publishing_ready"])
        self.assertIsNone(manifest["output_set_id"])
        self.assertFalse(manifest["promoted"])

    def test_standard_workflow_completes_without_render_or_publish_side_effects(self):
        engine = WorkflowEngine.__new__(WorkflowEngine)
        engine._save_workflow_result = mock.Mock()
        engine._run_ai_planner = mock.Mock(return_value=None)
        engine._run_pattern_engine = mock.Mock(return_value={})
        engine._run_knowledge_engine = mock.Mock(return_value={})
        engine._run_card_news_output_transaction = mock.Mock()

        def module(result=None):
            return SimpleNamespace(run=mock.Mock(return_value={} if result is None else result))

        engine.trend_collector = module()
        engine.topic_engine = module()
        engine.research_module = module()
        engine.content_module = module()
        engine.image_strategy_module = module()
        engine.image_prompt_module = module()
        engine.image_generation_module = module({
            "status": "image_generation_blocked",
            "external_api_called": False,
        })
        engine.card_news_module = module()
        engine.publishing_module = module()
        engine.trend_memory_module = module()
        engine.performance_score_module = module()
        engine.audit_engine_module = module()
        engine.learning_engine_module = module()
        engine.analytics_engine_module = module()
        engine.brand_dna_engine_module = module()
        engine.competitor_engine_module = module()

        result = engine.run()

        self.assertEqual(result["status"], "workflow_completed")
        self.assertEqual(result["image_generation"]["status"], "image_generation_blocked")
        self.assertEqual(result["card_news"]["status"], "card_news_production_blocked")
        self.assertFalse(result["publishing"]["actual_publish"])
        engine._run_card_news_output_transaction.assert_not_called()
        engine.card_news_module.run.assert_not_called()
        engine.publishing_module.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
