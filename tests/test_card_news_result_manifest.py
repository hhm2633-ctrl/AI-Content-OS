import json
import tempfile
import unittest
from pathlib import Path

from modules.card_news.card_news_result_manifest import build_card_news_result_manifest


class TestCardNewsResultManifest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.root = Path(self.temp_dir.name)
        (self.root / "storage/workflow_results").mkdir(parents=True)
        (self.root / "storage/card_news").mkdir(parents=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_json(self, relative_path, payload):
        (self.root / relative_path).write_text(json.dumps(payload), encoding="utf-8")

    def test_builds_ordered_repository_relative_manifest(self):
        cards = []
        for index in range(1, 5):
            relative_path = f"storage/card_news/card_news_{index}.png"
            (self.root / relative_path).write_bytes(b"png")
            cards.append({
                "index": index,
                "card_path": relative_path,
                "headline": f"headline {index}",
                "status": "created",
            })
        self._write_json("storage/workflow_results/08_card_news_result.json", {
            "status": "card_news_completed", "title": "Result", "cards": list(reversed(cards)),
        })
        self._write_json("storage/card_news/card_news_quality.json", {
            "passed": True, "qa_score": 0.9, "warnings": ["layout fallback"],
        })
        self._write_json("storage/workflow_results/09_publishing_result.json", {
            "status": "publishing_ready", "platform": "instagram", "upload_mode": "manual",
            "manual_image_required": False, "next_action": "check images",
        })

        manifest = build_card_news_result_manifest(self.root)

        self.assertEqual(manifest["status"], "ready")
        self.assertEqual([card["index"] for card in manifest["cards"]], [1, 2, 3, 4])
        self.assertEqual([card["role"] for card in manifest["cards"]], ["hook", "problem", "solution", "cta"])
        self.assertEqual(manifest["cards"][0]["path"], "storage/card_news/card_news_1.png")
        self.assertTrue(all(card["exists"] for card in manifest["cards"]))
        self.assertEqual(manifest["qa"]["warnings"], ["layout fallback"])
        self.assertTrue(manifest["publishing"]["ready"])
        self.assertFalse(manifest["publishing"]["manual_image_required"])

    def test_manual_image_requirement_blocks_all_ready_states(self):
        cards = []
        for index in range(1, 5):
            relative_path = f"storage/card_news/card_news_{index}.png"
            (self.root / relative_path).write_bytes(b"png")
            cards.append({"index": index, "card_path": relative_path, "status": "created"})
        self._write_json("storage/workflow_results/08_card_news_result.json", {
            "status": "card_news_completed", "cards": cards,
        })
        self._write_json("storage/card_news/card_news_quality.json", {"passed": True, "qa_score": 1.0})
        self._write_json("storage/workflow_results/09_publishing_result.json", {
            "status": "publishing_ready", "manual_image_required": True,
        })

        manifest = build_card_news_result_manifest(self.root)

        self.assertEqual(manifest["status"], "incomplete")
        self.assertFalse(manifest["publishing"]["ready"])
        self.assertTrue(manifest["publishing"]["manual_image_required"])

    def test_missing_and_malformed_files_return_safe_fallback(self):
        (self.root / "storage/workflow_results/08_card_news_result.json").write_text("not json", encoding="utf-8")
        self._write_json("storage/card_news/card_news_quality.json", [])

        manifest = build_card_news_result_manifest(self.root)

        self.assertEqual(manifest["status"], "incomplete")
        self.assertEqual(len(manifest["cards"]), 4)
        self.assertTrue(all(card["path"] is None for card in manifest["cards"]))
        self.assertFalse(manifest["qa"]["passed"])
        self.assertFalse(manifest["publishing"]["ready"])
        self.assertGreaterEqual(len(manifest["qa"]["warnings"]), 3)

    def test_rejects_card_path_outside_repository(self):
        outside = self.root.parent / "outside.png"
        self._write_json("storage/workflow_results/08_card_news_result.json", {
            "status": "card_news_completed",
            "cards": [{"index": 1, "card_path": str(outside), "status": "created"}],
        })

        manifest = build_card_news_result_manifest(self.root)

        self.assertIsNone(manifest["cards"][0]["path"])
        self.assertFalse(manifest["cards"][0]["exists"])
        self.assertTrue(any("outside the repository" in warning for warning in manifest["qa"]["warnings"]))


if __name__ == "__main__":
    unittest.main()
