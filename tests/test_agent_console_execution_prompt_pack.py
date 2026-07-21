import json
import unittest
from pathlib import Path

from modules.agent_console.execution_prompt_pack import (
    PRODUCTION_HARD_DIRECTIVE_IDS,
    build_execution_prompt_pack,
    compact_candidate_context,
    select_production_hard_rules,
    select_owner_learning,
)
from modules.agent_console.executor import ClaudeCliAdapter
from modules.agent_console.spark_host_bridge import SparkHostBridge


class TestExecutionPromptPack(unittest.TestCase):
    def _job(self, category: str):
        return {"job_id": "job-1", "category": category, "title": "selected candidate"}

    def _context(self):
        return {
            "source": "owner_review",
            "candidate_id": "C-1",
            "title": "selected candidate",
            "source_urls": [f"https://example.com/{index}" for index in range(8)],
            "requested_media": [f"asset-{index}" for index in range(9)],
            "unused_large_field": "x" * 5000,
            "api_key": "secret",
        }

    def test_pack_is_bounded_and_never_reloads_upstream_or_full_feedback(self):
        pack = build_execution_prompt_pack(self._job("fashion"), self._context())
        self.assertEqual(len(pack["past_owner_learning"]), 5)
        self.assertEqual(len(pack["current_candidate"]["source_urls"]), 3)
        self.assertEqual(len(pack["current_candidate"]["requested_media"]), 6)
        self.assertNotIn("unused_large_field", pack["current_candidate"])
        self.assertNotIn("api_key", pack["current_candidate"])
        self.assertFalse(pack["source_policy"]["agency_agents_upstream_reloaded"])
        self.assertFalse(pack["source_policy"]["full_feedback_log_reloaded"])
        self.assertTrue(pack["source_policy"]["adapted_category_asset_used"])

    def test_each_category_gets_only_its_bounded_owner_learning(self):
        expected_first = {
            "news": "OD-CARD-010",
            "story": "OD-CARD-002",
            "fashion": "OD-CARD-004",
            "beauty": "OD-CARD-001",
        }
        for category, first_id in expected_first.items():
            with self.subTest(category=category):
                rows = select_owner_learning(category)
                self.assertEqual(len(rows), 5)
                self.assertEqual(rows[0]["claim_id"], first_id)

    def test_production_hard_rules_are_never_relevance_ranked_away(self):
        rows = select_production_hard_rules()
        self.assertEqual(
            [row["claim_id"] for row in rows],
            list(PRODUCTION_HARD_DIRECTIVE_IDS),
        )
        for category in ("news", "story", "fashion", "beauty"):
            with self.subTest(category=category):
                pack = build_execution_prompt_pack(self._job(category), self._context())
                self.assertEqual(
                    [row["claim_id"] for row in pack["production_hard_rules"]],
                    list(PRODUCTION_HARD_DIRECTIVE_IDS),
                )
                self.assertTrue(pack["education_receipt"]["production_hard_rules_complete"])

    def test_claude_and_spark_consume_the_same_pack_contract(self):
        job = self._job("beauty")
        context = self._context()
        pack = build_execution_prompt_pack(job, context)
        claude_prompt = ClaudeCliAdapter._prompt(
            job=job,
            context=context,
            handoff_path=Path("inbox/job-1.json"),
            dispatch_nonce="nonce",
            attempt=1,
            prompt_pack=pack,
        )
        spark_prompt = json.loads(SparkHostBridge._prompt_block(job, context))
        self.assertIn(pack["education_receipt"]["prompt_pack_sha256"], claude_prompt)
        self.assertEqual(
            spark_prompt["execution_prompt_pack"]["education_receipt"],
            pack["education_receipt"],
        )

    def test_compaction_keeps_only_one_candidate_contract(self):
        compact = compact_candidate_context(self._context())
        self.assertEqual(compact["candidate_id"], "C-1")
        self.assertNotIn("unused_large_field", compact)


if __name__ == "__main__":
    unittest.main()
