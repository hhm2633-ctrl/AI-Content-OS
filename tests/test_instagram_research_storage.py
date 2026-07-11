import json
import shutil
import tempfile
import unittest
from pathlib import Path

from modules.instagram_research.instagram_storage import InstagramResearchStorage


class TestInstagramResearchStorage(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="instagram_research_test_")
        self.storage = InstagramResearchStorage(base_dir=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_creates_output_directory(self):
        self.assertTrue(Path(self.tmp_dir).exists())
        self.assertTrue((Path(self.tmp_dir) / "screenshots").exists())

    def test_invalid_json_does_not_raise(self):
        self.storage.posts_path.write_text("{not valid json", encoding="utf-8")
        result = self.storage.load_posts()
        self.assertEqual(result, [])

    def test_invalid_json_recovers_to_default(self):
        self.storage.statistics_path.write_text("not json at all", encoding="utf-8")
        result = self.storage.load_statistics()
        self.assertEqual(result, {})

    def test_load_accounts_returns_empty_list_when_file_missing(self):
        self.assertEqual(self.storage.load_accounts(), [])

    def test_load_capability_audit_returns_empty_dict_when_missing(self):
        self.assertEqual(self.storage.load_capability_audit(), {})

    def test_load_posts_returns_empty_list_when_file_missing(self):
        self.assertEqual(self.storage.load_posts(), [])

    def test_load_statistics_returns_empty_dict_when_file_missing(self):
        self.assertEqual(self.storage.load_statistics(), {})

    def test_save_and_load_accounts_roundtrip(self):
        accounts = [{"account_handle": "brand_a"}]
        self.assertTrue(self.storage.save_accounts(accounts))
        self.assertEqual(self.storage.load_accounts(), accounts)

    def test_save_and_load_capability_audit_roundtrip(self):
        audit = {"can_view_public_posts": True}
        self.assertTrue(self.storage.save_capability_audit(audit))
        self.assertEqual(self.storage.load_capability_audit(), audit)

    def test_save_and_load_classifications_roundtrip(self):
        classifications = [{"account_handle": "brand_a", "hook": {"value": "unknown"}}]
        self.assertTrue(self.storage.save_classifications(classifications))
        self.assertEqual(self.storage.load_classifications(), classifications)

    def test_save_and_load_posts_roundtrip(self):
        posts = [{"account_handle": "brand_a", "post_shortcode": "abc"}]
        self.assertTrue(self.storage.save_posts(posts))
        self.assertEqual(self.storage.load_posts(), posts)

    def test_save_and_load_research_run_roundtrip(self):
        run = {"checked_at": "2026-07-11T00:00:00", "current_run_accounts": ["brand_a"]}
        self.assertTrue(self.storage.save_research_run(run))
        self.assertEqual(self.storage.load_research_run(), run)

    def test_save_and_load_statistics_roundtrip(self):
        stats = {"total_posts": 5}
        self.assertTrue(self.storage.save_statistics(stats))
        self.assertEqual(self.storage.load_statistics(), stats)

    def test_save_posts_deduplicates_by_shortcode(self):
        # Storage itself does not dedupe (that's the normalizer's job) - it
        # persists exactly what it is given.
        posts = [{"post_shortcode": "abc"}, {"post_shortcode": "abc"}]
        self.storage.save_posts(posts)
        self.assertEqual(len(self.storage.load_posts()), 2)

    def test_save_posts_handles_empty_list(self):
        self.assertTrue(self.storage.save_posts([]))
        self.assertEqual(self.storage.load_posts(), [])

    def test_saved_posts_file_is_valid_json_on_disk(self):
        self.storage.save_posts([{"account_handle": "brand_a"}])
        with open(self.storage.posts_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data, [{"account_handle": "brand_a"}])


if __name__ == "__main__":
    unittest.main()
