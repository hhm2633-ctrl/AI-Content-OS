import json
import tempfile
import unittest
from pathlib import Path

from modules.agent_console.category_prompt_loader import (
    DEFAULT_ASSET_PATH,
    build_category_prompt,
    load_category_prompts,
)
from modules.agent_console.executor import ClaudeCliAdapter


CATEGORY_MARKERS = {
    "news": "기사 본문",
    "story": "감정 변화",
    "fashion": "룩북",
    "beauty": "제형",
}


class TestCategoryExecutionPromptAsset(unittest.TestCase):
    def test_asset_defines_all_categories_with_separate_rules_and_prohibitions(self):
        payload = load_category_prompts()
        self.assertEqual(payload.get("schema_version"), "category_execution_prompts_v1")
        categories = payload["categories"]
        self.assertEqual(set(categories), {"news", "story", "fashion", "beauty"})
        seen_rules: dict[str, str] = {}
        for name, entry in categories.items():
            self.assertTrue(entry["rules"], f"{name} has no rules")
            self.assertTrue(entry["prohibited"], f"{name} has no prohibitions")
            for rule in [*entry["rules"], *entry["prohibited"]]:
                self.assertNotIn(
                    rule, seen_rules, f"rule shared between {seen_rules.get(rule)} and {name}"
                )
                seen_rules[rule] = name

    def test_prompt_block_is_category_specific_not_generic(self):
        blocks = {name: build_category_prompt(name) for name in CATEGORY_MARKERS}
        for name, marker in CATEGORY_MARKERS.items():
            self.assertIn(marker, blocks[name], f"{name} block misses its own marker")
            self.assertIn("금지:", blocks[name])
            for other, other_marker in CATEGORY_MARKERS.items():
                if other != name:
                    self.assertNotIn(
                        other_marker, blocks[name], f"{name} block leaks {other} rules"
                    )

    def test_unknown_category_and_broken_asset_degrade_to_empty(self):
        self.assertEqual(build_category_prompt("commerce"), "")
        self.assertEqual(build_category_prompt(""), "")
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing.json"
            self.assertEqual(build_category_prompt("news", asset_path=missing), "")
            broken = Path(temp) / "broken.json"
            broken.write_text("{not json", encoding="utf-8")
            self.assertEqual(build_category_prompt("news", asset_path=broken), "")

    def test_asset_file_is_valid_json_at_default_path(self):
        payload = json.loads(DEFAULT_ASSET_PATH.read_text(encoding="utf-8"))
        self.assertIn("precedence", payload)
        self.assertIn("shared", payload)


class TestExecutorPromptInjection(unittest.TestCase):
    def _prompt_for(self, category):
        return ClaudeCliAdapter._prompt(
            job={"job_id": "job-1", "category": category, "title": "t"},
            context={"source": "owner_review"},
            handoff_path=Path("inbox") / "job-1.json",
            dispatch_nonce="nonce-1",
            attempt=1,
        )

    def test_executor_injects_matching_category_rules_only(self):
        category_blocks = {name: build_category_prompt(name) for name in CATEGORY_MARKERS}
        for name, marker in CATEGORY_MARKERS.items():
            prompt = self._prompt_for(name)
            self.assertIn("[카테고리 실행 교육 | " + name, prompt)
            self.assertIn(marker, prompt)
            for other, other_block in category_blocks.items():
                if other != name:
                    self.assertNotIn(other_block, prompt)

    def test_executor_keeps_base_contract_and_handles_unknown_category(self):
        prompt = self._prompt_for("news")
        self.assertIn("게시, 링크 발급, Git, 자동화", prompt)
        self.assertIn("job-1.json", prompt)
        self.assertIn("dispatch_nonce=nonce-1", prompt)
        unknown = self._prompt_for("commerce")
        self.assertNotIn("[카테고리 실행 교육", unknown)
        self.assertIn("게시, 링크 발급, Git, 자동화", unknown)


if __name__ == "__main__":
    unittest.main()
