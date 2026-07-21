import os
import unittest
import shutil
import uuid

import json

from modules.source_intake.source_intake_brief import (
    BRIEF_FILE_NAME,
    BUNDLE_FILE_NAME,
    build_source_intake_brief,
    run_source_intake_brief,
)


class TestSourceIntakeBrief(unittest.TestCase):
    _TODAY = "2099-02-03"

    def setUp(self):
        self.work_root = os.path.join(".", "source_intake_brief_tmp", uuid.uuid4().hex)
        os.makedirs(self.work_root, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.work_root, ignore_errors=True)

    def _write_bundle(self, bundle):
        root = os.path.join(self.work_root, self._TODAY)
        os.makedirs(root, exist_ok=True)
        path = os.path.join(root, BUNDLE_FILE_NAME)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(bundle, handle, ensure_ascii=False)
        return path

    def test_fake_bundle_builds_expected_sections(self):
        bundle = {
            "not_implemented_collectors": ["news_a", "news_b"],
            "fallback_only_sources": ["naver_news"],
            "blocked_lanes": ["news_society_economy", "entertainment_news"],
            "top_queue_sources": ["daum_news", "news1", "alpha", "beta", "gamma", "delta"],
        }
        markdown = build_source_intake_brief(bundle)

        self.assertIn("## Not implemented collectors", markdown)
        self.assertIn("## Fallback only sources", markdown)
        self.assertIn("## Blocked/weak lanes", markdown)
        self.assertIn("## Next queue top 5", markdown)
        self.assertIn("- news_a", markdown)
        self.assertIn("- naver_news", markdown)
        self.assertIn("- news_society_economy", markdown)
        self.assertIn("- daum_news", markdown)
        self.assertNotIn("- delta", markdown)
        self.assertNotIn("commerce_detail", markdown)
        self.assertIn("- (none)", build_source_intake_brief({}))

    def test_fake_bundle_builds_headings_only(self):
        bundle = {
            "not_implemented_collectors": ["news_a", "news_b"],
            "fallback_only_sources": ["naver_news"],
            "blocked_lanes": ["news_society_economy"],
            "top_queue_sources": ["daum_news"],
        }
        markdown = build_source_intake_brief(bundle)
        headings = [line.strip() for line in markdown.splitlines() if line.startswith("## ")]
        self.assertEqual(
            headings,
            [
                "## Not implemented collectors",
                "## Fallback only sources",
                "## Blocked/weak lanes",
                "## Next queue top 5",
            ],
        )

    def test_smoke_current_source_intake_brief_if_present(self):
        today = "2026-07-14"
        bundle_path = os.path.join("storage", "source_intake", today, BUNDLE_FILE_NAME)
        if not os.path.exists(bundle_path):
            self.skipTest("source_intake status bundle unavailable")

        markdown = build_source_intake_brief(bundle_path)
        self.assertIn("## Not implemented collectors", markdown)
        self.assertIn("## Fallback only sources", markdown)
        self.assertIn("## Blocked/weak lanes", markdown)
        self.assertIn("## Next queue top 5", markdown)
        self.assertNotIn("commerce_detail", markdown)

    def test_missing_input_returns_input_missing_and_writes_nothing(self):
        result = run_source_intake_brief(today=self._TODAY, root=self.work_root)
        expected_path = os.path.join(self.work_root, self._TODAY, BRIEF_FILE_NAME)

        self.assertEqual(result["status"], "input_missing")
        self.assertFalse(os.path.exists(expected_path))
        self.assertEqual(result["bundle_path"], os.path.join(self.work_root, self._TODAY, BUNDLE_FILE_NAME))

    def test_run_writes_markdown(self):
        self._write_bundle({"status_summary": {"NOT_IMPLEMENTED": []}, "top_queue_sources": ["news1"]})
        result = run_source_intake_brief(today=self._TODAY, root=self.work_root)
        brief_path = result["brief_path"]

        self.assertEqual(result["status"], "written")
        self.assertTrue(os.path.exists(brief_path))
        with open(brief_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("## Next queue top 5", content)


if __name__ == "__main__":
    unittest.main()
