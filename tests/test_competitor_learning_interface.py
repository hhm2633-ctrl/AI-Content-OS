import shutil
import tempfile
import unittest
from pathlib import Path

from modules.competitor_learning.competitor_learning_interface import CompetitorLearningInterface
from modules.competitor_learning.competitor_learning_storage import CompetitorLearningStorage


def _entry(entry_type, value, score=0.5):
    return {
        "knowledge_id": f"competitor_learning_{entry_type}_{value}",
        "type": entry_type,
        "value": value,
        "score": {"overall_score": score},
    }


class TestCompetitorLearningInterface(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="competitor_learning_interface_test_")
        self.storage = CompetitorLearningStorage(
            knowledge_dir=Path(self.tmp_dir) / "knowledge",
            dashboard_dir=Path(self.tmp_dir) / "dashboard",
        )
        self.interface = CompetitorLearningInterface(storage=self.storage)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_is_available_false_when_no_entries(self):
        self.assertFalse(self.interface.is_available())

    def test_is_available_true_after_entries_saved(self):
        self.storage.save_knowledge_database([_entry("hook", "attention")], {})
        self.assertTrue(self.interface.is_available())

    def test_get_knowledge_database_returns_saved_data(self):
        self.storage.save_knowledge_database([_entry("hook", "attention")], {"sample_size": 3})
        db = self.interface.get_knowledge_database()
        self.assertEqual(db["sample_size"], 3)

    def test_get_top_hooks_filters_by_type_and_sorts_by_score(self):
        self.storage.save_knowledge_database(
            [_entry("hook", "attention", 0.3), _entry("hook", "pain_point", 0.9), _entry("cta", "save", 0.99)],
            {},
        )
        top_hooks = self.interface.get_top_hooks(limit=5)
        self.assertEqual(len(top_hooks), 2)
        self.assertEqual(top_hooks[0]["value"], "pain_point")

    def test_get_top_ctas_filters_by_type(self):
        self.storage.save_knowledge_database([_entry("cta", "save"), _entry("hook", "attention")], {})
        top_ctas = self.interface.get_top_ctas()
        self.assertEqual(len(top_ctas), 1)
        self.assertEqual(top_ctas[0]["type"], "cta")

    def test_get_top_patterns_filters_by_type(self):
        self.storage.save_knowledge_database([_entry("pattern", "funnel")], {})
        self.assertEqual(len(self.interface.get_top_patterns()), 1)

    def test_get_top_layouts_filters_by_type(self):
        self.storage.save_knowledge_database([_entry("layout", "carousel")], {})
        self.assertEqual(len(self.interface.get_top_layouts()), 1)

    def test_get_hook_statistics_returns_empty_dict_when_missing(self):
        self.assertEqual(self.interface.get_hook_statistics(), {})

    def test_get_competitor_statistics_returns_saved_data(self):
        self.storage.save_competitor_statistics({"account_count": 2})
        self.assertEqual(self.interface.get_competitor_statistics()["account_count"], 2)

    def test_get_account_profile_returns_profile_for_known_handle(self):
        self.storage.save_competitor_statistics({"accounts": {"brand_a": {"post_count": 5}}})
        profile = self.interface.get_account_profile("brand_a")
        self.assertEqual(profile["post_count"], 5)

    def test_get_account_profile_returns_empty_dict_for_unknown_handle(self):
        self.storage.save_competitor_statistics({"accounts": {"brand_a": {"post_count": 5}}})
        self.assertEqual(self.interface.get_account_profile("brand_z"), {})

    def test_get_dashboard_returns_saved_report(self):
        self.storage.save_dashboard({"analyzed_post_count": 7})
        self.assertEqual(self.interface.get_dashboard()["analyzed_post_count"], 7)

    def test_interface_never_raises_on_broken_storage(self):
        self.storage.knowledge_database_path.write_text("not json", encoding="utf-8")
        self.assertEqual(self.interface.get_top_hooks(), [])
        self.assertFalse(self.interface.is_available())

    def test_limit_parameter_respected(self):
        entries = [_entry("hook", f"value_{i}", score=i / 10) for i in range(10)]
        self.storage.save_knowledge_database(entries, {})
        self.assertEqual(len(self.interface.get_top_hooks(limit=3)), 3)

    def test_get_layout_statistics_returns_empty_dict_when_missing(self):
        self.assertEqual(self.interface.get_layout_statistics(), {})

    def test_get_pattern_statistics_returns_empty_dict_when_missing(self):
        self.assertEqual(self.interface.get_pattern_statistics(), {})


if __name__ == "__main__":
    unittest.main()
