import shutil
import tempfile
import unittest
from pathlib import Path

from modules.instagram_research.instagram_research_interface import InstagramResearchInterface
from modules.instagram_research.instagram_storage import InstagramResearchStorage


class TestInstagramResearchInterface(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="instagram_research_test_")
        self.storage = InstagramResearchStorage(base_dir=self.tmp_dir)
        self.interface = InstagramResearchInterface(storage=self.storage)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_dataset_status_available_false_when_empty(self):
        status = self.interface.get_dataset_status()
        self.assertFalse(status["available"])
        self.assertEqual(status["total_posts"], 0)

    def test_dataset_status_available_true_after_posts_saved(self):
        self.storage.save_posts([{"account_handle": "brand_a"}])
        status = self.interface.get_dataset_status()
        self.assertTrue(status["available"])
        self.assertEqual(status["total_posts"], 1)

    def test_dataset_status_reports_auto_learning_not_connected(self):
        status = self.interface.get_dataset_status()
        self.assertFalse(status["auto_learning_connected"])

    def test_get_accounts_returns_empty_list_when_missing(self):
        self.assertEqual(self.interface.get_accounts(), [])

    def test_get_capability_audit_returns_empty_dict_when_missing(self):
        self.assertEqual(self.interface.get_capability_audit(), {})

    def test_get_classifications_returns_empty_list_when_missing(self):
        self.assertEqual(self.interface.get_classifications(), [])

    def test_get_posts_filters_by_account_handle(self):
        self.storage.save_posts([
            {"account_handle": "brand_a", "post_shortcode": "1"},
            {"account_handle": "brand_b", "post_shortcode": "2"},
        ])
        posts = self.interface.get_posts(account_handle="brand_a")
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["account_handle"], "brand_a")

    def test_get_posts_returns_all_when_no_filter(self):
        self.storage.save_posts([
            {"account_handle": "brand_a", "post_shortcode": "1"},
            {"account_handle": "brand_b", "post_shortcode": "2"},
        ])
        self.assertEqual(len(self.interface.get_posts()), 2)

    def test_get_statistics_returns_empty_dict_when_missing(self):
        self.assertEqual(self.interface.get_statistics(), {})

    def test_interface_never_raises_on_broken_storage(self):
        self.storage.posts_path.write_text("not valid json", encoding="utf-8")
        self.storage.statistics_path.write_text("not valid json", encoding="utf-8")
        status = self.interface.get_dataset_status()
        self.assertFalse(status["available"])
        self.assertEqual(self.interface.get_statistics(), {})


if __name__ == "__main__":
    unittest.main()
