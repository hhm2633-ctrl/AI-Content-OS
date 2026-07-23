import json
import tempfile
import unittest
from pathlib import Path

from modules.design_learning.owner_feedback_corpus import (
    compile_owner_feedback_corpus,
    register_candidate_patterns,
)


class OwnerFeedbackCorpusTest(unittest.TestCase):
    def test_compiles_corrections_and_analysis_without_performance_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "owner_correction_example.json").write_text(
                json.dumps(
                    {
                        "owner_correction": "카드뉴스 장수는 가변으로 한다.",
                        "standing_learning_rules": ["뉴스와 썰 계정을 분리한다."],
                        "runtime_connected": False,
                        "tested": False,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "analysis.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "id": 1,
                                "learning": "패션 아이템은 착장과 디테일을 함께 보여준다.",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = compile_owner_feedback_corpus(root, output_path=None)

            self.assertEqual(result["stats"]["source_file_count"], 2)
            self.assertTrue(result["owner_rule_payloads"])
            self.assertTrue(all(not item["is_performance_evidence"] for item in result["records"]))
            self.assertFalse(result["learning_boundary"]["candidate_patterns_auto_promoted"])

    def test_registers_candidate_only_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            registry_path = Path(temporary) / "patterns.jsonl"
            pattern = {
                "pattern_id": "pattern.test.owner-corpus",
                "name": "Owner corpus candidate",
                "domain": "content_pattern",
                "source_claim_ids": ["owner-feedback:test:root"],
                "preconditions": ["topic exists"],
                "recommended_action": "Use as reference only.",
                "prohibited_actions": ["auto promote"],
                "success_metrics": [],
                "failure_signals": ["owner rejection"],
                "confidence": 0.3,
                "status": "CANDIDATE",
                "version": "1.0",
                "reviewed_at": None,
                "owner_skill": "ai-content-os-knowledge-intelligence",
                "supersedes": None,
                "expires_at": None,
            }

            first = register_candidate_patterns([pattern], registry_path=registry_path)
            second = register_candidate_patterns([pattern], registry_path=registry_path)

            self.assertEqual(first["registered_count"], 1)
            self.assertEqual(second["skipped_existing_count"], 1)
            rows = [
                json.loads(line)
                for line in registry_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(rows[0]["status"], "CANDIDATE")


if __name__ == "__main__":
    unittest.main()
