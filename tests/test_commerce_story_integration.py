import json
import tempfile
import unittest
from pathlib import Path

from modules.brandconnect.commerce_story_integration import merge_commerce_story_shards


def _row(product_id, name, story):
    return {
        "product_id": product_id,
        "product_name": name,
        "derived_terms": [name],
        "season_context": "여름 · 습한 출근길",
        "practical_topic": f"{name} 실생활 관리",
        "short_story": story,
        "product_role": f"{name}을 자연스럽게 연결",
        "blog_seed": f"{name} 활용법",
        "confidence": 0.8,
        "fallback_used": False,
    }


class CommerceStoryIntegrationTest(unittest.TestCase):
    def _shard(self, root, shard_id, category, rows):
        shard = root / f"{shard_id}.jsonl"
        report = root / f"{shard_id}.json"
        shard.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        report.write_text(json.dumps({
            "product_count": len(rows),
            "story_count": len(rows),
            "product_id_coverage_valid": True,
            "validation": {"result": "PASS"},
        }), encoding="utf-8")
        return {
            "shard_id": shard_id,
            "category": category,
            "shard_path": str(shard),
            "report_path": str(report),
        }

    def test_incremental_shards_attach_supplied_briefs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            beauty = self._shard(root, "beauty", "beauty", [_row("P1", "핸드크림", "건조한 손에 보습 한 번")])
            lifestyle = self._shard(root, "lifestyle", "lifestyle", [_row("P2", "신발 클리너", "비 온 뒤 신발을 산뜻하게")])
            candidates = [{
                "candidate_id": "C1",
                "title": "장마철 생활 관리",
                "matches": [{"product_id": "P1"}, {"product_id": "P2"}],
            }]
            first = merge_commerce_story_shards(candidates, [beauty])
            second = merge_commerce_story_shards(candidates, [beauty, lifestyle], first["engine_state"])

        self.assertEqual(first["unique_product_count"], 1)
        self.assertEqual(second["unique_product_count"], 2)
        self.assertEqual(second["shards"][0]["status"], "already_completed")
        briefs = second["story_briefs"]["candidates"][0]["briefs"]
        self.assertEqual([item["product_id"] for item in briefs], ["P1", "P2"])
        self.assertTrue(all(item["link_issued"] is False for item in briefs))

    def test_invalid_shard_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._shard(root, "broken", "beauty", [_row("P1", "핸드크림", "x" * 30)])
            result = merge_commerce_story_shards([], [spec])

        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["accepted_shards"], 0)
        self.assertEqual(result["unique_product_count"], 0)
        self.assertFalse(result["network_used"])
        self.assertFalse(result["link_issuance"])
        self.assertFalse(result["publishing"])


if __name__ == "__main__":
    unittest.main()
