import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.competitor_learning.competitor_learning_module import CompetitorLearningModule
from modules.competitor_learning.competitor_learning_storage import CompetitorLearningStorage


def _observation(**overrides):
    base = {
        "account_handle": "brand_a",
        "post_shortcode": "abc",
        "post_type": "carousel",
        "slide_count": 4,
        "image_count": 4,
        "caption_length": 20,
        "hashtag_count": 1,
        "hashtags": ["#ai"],
        "like_count": 100,
        "comment_count": 10,
        "hook_type": "attention",
        "hook_confidence": 0.6,
        "cta_type": "save",
        "cta_confidence": 0.6,
        "pattern_type": "funnel",
        "pattern_confidence": 0.6,
    }
    base.update(overrides)
    return base


class _FakeExtractor:
    def __init__(self, observations):
        self._observations = observations

    def extract(self):
        return self._observations


class TestCompetitorLearningModule(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="competitor_learning_module_test_")
        storage = CompetitorLearningStorage(
            knowledge_dir=Path(self.tmp_dir) / "knowledge",
            dashboard_dir=Path(self.tmp_dir) / "dashboard",
        )
        self.module = CompetitorLearningModule(storage=storage)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_run_returns_completed_status(self):
        self.module.extractor = _FakeExtractor([])
        result = self.module.run()
        self.assertEqual(result["status"], "competitor_learning_completed")

    def test_run_fallback_used_true_when_no_observations(self):
        self.module.extractor = _FakeExtractor([])
        result = self.module.run()
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["sample_size"], 0)

    def test_run_fallback_used_false_when_observations_present(self):
        self.module.extractor = _FakeExtractor([_observation(), _observation(), _observation()])
        result = self.module.run()
        self.assertFalse(result["fallback_used"])
        self.assertEqual(result["sample_size"], 3)

    def test_run_persists_all_six_required_files(self):
        self.module.extractor = _FakeExtractor([_observation()])
        self.module.run()
        storage = self.module.storage
        self.assertTrue(storage.knowledge_database_path.exists())
        self.assertTrue(storage.hook_statistics_path.exists())
        self.assertTrue(storage.cta_statistics_path.exists())
        self.assertTrue(storage.pattern_statistics_path.exists())
        self.assertTrue(storage.layout_statistics_path.exists())
        self.assertTrue(storage.competitor_statistics_path.exists())

    def test_run_persists_dashboard_report(self):
        self.module.extractor = _FakeExtractor([_observation()])
        self.module.run()
        self.assertTrue(self.module.storage.dashboard_path.exists())

    def test_run_never_raises_on_extractor_exception(self):
        class RaisingExtractor:
            def extract(self):
                raise RuntimeError("boom")

        self.module.extractor = RaisingExtractor()
        result = self.module.run()
        self.assertEqual(result["status"], "competitor_learning_completed")
        self.assertTrue(result["fallback_used"])

    def test_run_entry_count_matches_scorer_output(self):
        self.module.extractor = _FakeExtractor([_observation(), _observation(hook_type="pain_point")])
        result = self.module.run()
        self.assertGreater(result["entry_count"], 0)
        self.assertEqual(result["entry_count"], len(result["knowledge_database"]["entries"]))

    def test_run_account_count_matches_statistics(self):
        self.module.extractor = _FakeExtractor([
            _observation(account_handle="brand_a"),
            _observation(account_handle="brand_b"),
        ])
        result = self.module.run()
        self.assertEqual(result["account_count"], 2)

    def test_run_records_history(self):
        self.module.extractor = _FakeExtractor([_observation()])
        self.module.run()
        history = self.module.storage.load_history()
        self.assertEqual(len(history["records"]), 1)

    def test_run_new_count_increases_on_first_run_with_data(self):
        self.module.extractor = _FakeExtractor([_observation(), _observation(), _observation()])
        result = self.module.run()
        self.assertGreater(result["new_count"], 0)

    def test_fallback_result_has_safe_defaults(self):
        result = self.module._fallback_result(reason="test")
        self.assertEqual(result["status"], "competitor_learning_completed")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["entry_count"], 0)
        self.assertEqual(result["knowledge_database"], {})

    def test_run_logs_start_and_finish(self):
        self.module.extractor = _FakeExtractor([])
        with patch("builtins.print") as mock_print:
            self.module.run()
            printed = " ".join(str(call) for call in mock_print.call_args_list)
        self.assertIn("Competitor Learning Module Started", printed)
        self.assertIn("Competitor Learning Module Finished", printed)


if __name__ == "__main__":
    unittest.main()
