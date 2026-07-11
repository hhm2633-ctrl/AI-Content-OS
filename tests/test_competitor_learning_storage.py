import shutil
import tempfile
import unittest
from pathlib import Path

from modules.competitor_learning.competitor_learning_storage import CompetitorLearningStorage


class TestCompetitorLearningStorage(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="competitor_learning_test_")
        self.knowledge_dir = Path(self.tmp_dir) / "knowledge"
        self.dashboard_dir = Path(self.tmp_dir) / "dashboard"
        self.storage = CompetitorLearningStorage(knowledge_dir=self.knowledge_dir, dashboard_dir=self.dashboard_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_creates_knowledge_and_dashboard_directories(self):
        self.assertTrue(self.knowledge_dir.exists())
        self.assertTrue(self.dashboard_dir.exists())

    def test_load_knowledge_database_returns_empty_default_when_missing(self):
        db = self.storage.load_knowledge_database()
        self.assertEqual(db["entries"], [])
        self.assertEqual(db["total_count"], 0)

    def test_save_and_load_knowledge_database_roundtrip(self):
        entries = [{"knowledge_id": "a", "type": "hook", "value": "attention"}]
        self.storage.save_knowledge_database(entries, {"caption_summary": {}, "sample_size": 5})
        db = self.storage.load_knowledge_database()
        self.assertEqual(db["entries"], entries)
        self.assertEqual(db["sample_size"], 5)

    def test_save_knowledge_database_computes_new_count_on_first_save(self):
        entries = [{"knowledge_id": "a"}, {"knowledge_id": "b"}]
        result = self.storage.save_knowledge_database(entries, {})
        self.assertEqual(result["new_count"], 2)

    def test_save_knowledge_database_new_count_zero_when_same_ids_resaved(self):
        entries = [{"knowledge_id": "a"}]
        self.storage.save_knowledge_database(entries, {})
        result = self.storage.save_knowledge_database(entries, {})
        self.assertEqual(result["new_count"], 0)

    def test_save_knowledge_database_new_count_positive_for_new_ids(self):
        self.storage.save_knowledge_database([{"knowledge_id": "a"}], {})
        result = self.storage.save_knowledge_database([{"knowledge_id": "a"}, {"knowledge_id": "b"}], {})
        self.assertEqual(result["new_count"], 1)

    def test_save_and_load_hook_statistics_roundtrip(self):
        self.storage.save_hook_statistics({"distribution": {"attention": 3}})
        loaded = self.storage.load_hook_statistics()
        self.assertEqual(loaded["distribution"], {"attention": 3})
        self.assertIn("updated_at", loaded)

    def test_save_and_load_cta_statistics_roundtrip(self):
        self.storage.save_cta_statistics({"distribution": {"save": 2}})
        self.assertEqual(self.storage.load_cta_statistics()["distribution"], {"save": 2})

    def test_save_and_load_pattern_statistics_roundtrip(self):
        self.storage.save_pattern_statistics({"distribution": {"funnel": 1}})
        self.assertEqual(self.storage.load_pattern_statistics()["distribution"], {"funnel": 1})

    def test_save_and_load_layout_statistics_roundtrip(self):
        self.storage.save_layout_statistics({"post_type_distribution": {"reel": 2}})
        self.assertEqual(self.storage.load_layout_statistics()["post_type_distribution"], {"reel": 2})

    def test_save_and_load_competitor_statistics_roundtrip(self):
        self.storage.save_competitor_statistics({"account_count": 3})
        self.assertEqual(self.storage.load_competitor_statistics()["account_count"], 3)

    def test_record_history_appends_and_caps_at_500(self):
        for i in range(505):
            self.storage.record_history({"entry_count": i})
        history = self.storage.load_history()
        self.assertEqual(len(history["records"]), 500)
        self.assertEqual(history["records"][-1]["entry_count"], 504)

    def test_save_and_load_dashboard_roundtrip(self):
        report = {"analyzed_post_count": 10}
        self.assertTrue(self.storage.save_dashboard(report))
        self.assertEqual(self.storage.load_dashboard(), report)

    def test_invalid_json_does_not_raise(self):
        self.storage.knowledge_database_path.write_text("not valid json", encoding="utf-8")
        db = self.storage.load_knowledge_database()
        self.assertEqual(db["entries"], [])

    def test_load_history_returns_default_when_missing(self):
        self.assertEqual(self.storage.load_history(), {"records": []})

    def test_stats_files_get_updated_at_stamp(self):
        result = self.storage.save_hook_statistics({})
        self.assertIn("updated_at", result)
        self.assertIsInstance(result["updated_at"], str)

    def test_save_dashboard_handles_none_report(self):
        self.assertTrue(self.storage.save_dashboard(None))
        self.assertEqual(self.storage.load_dashboard(), {})


if __name__ == "__main__":
    unittest.main()
