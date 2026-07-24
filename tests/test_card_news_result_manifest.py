import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.card_news.card_news_result_manifest import build_card_news_result_manifest


class TestCardNewsResultManifest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "storage/workflow_results").mkdir(parents=True)
        (self.root / "storage/card_news").mkdir(parents=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_json(self, relative_path, payload):
        (self.root / relative_path).write_text(json.dumps(payload), encoding="utf-8")

    def _write_png(self, index, size=(1080, 1080)):
        path = self.root / f"storage/card_news/card_news_{index}.png"
        Image.new("RGB", size, color=(index * 20, 30, 40)).save(path)
        return path.relative_to(self.root).as_posix()

    def _write_ready_fixture(self, output_set_id="set-001", size=(1080, 1080)):
        card_paths = [self._write_png(index, size=size) for index in range(1, 5)]
        cards = [
            {
                "index": index,
                "card_path": card_paths[index - 1],
                "headline": f"headline {index}",
                "status": "created",
            }
            for index in range(1, 5)
        ]
        self._write_json("storage/workflow_results/08_card_news_result.json", {
            "status": "card_news_completed",
            "title": "Result",
            "cards": list(reversed(cards)),
            "output_set_id": output_set_id,
            "image_sourcing_status": {
                "manual_image_required": False,
                "real_image_used_count": 4,
                "checklist": [],
                "recommended_source": "owned",
                "reason": "approved images rendered",
            },
        })
        self._write_json("storage/card_news/card_news_quality.json", {
            "passed": True,
            "qa_score": 0.9,
            "warnings": ["layout fallback"],
            "output_set_id": output_set_id,
            "checks": {
                "layout_fallback_used": True,
                "rendering_fallback_used": False,
                "fallback_used": True,
                "unlicensed_asset_not_rendered": True,
                "attribution_needed": False,
                "attribution_present": False,
                "evidence_available": False,
                "evidence_applied": False,
                "social_proof_available": False,
                "social_proof_applied": False,
            },
        })
        self._write_json("storage/workflow_results/09_publishing_result.json", {
            "status": "publishing_ready",
            "platform": "instagram",
            "upload_mode": "manual",
            "manual_image_required": False,
            "next_action": "check images",
            "card_paths": card_paths,
            "output_set_id": output_set_id,
            "operations": {
                "publishing_blocked": False,
                "blocking_reasons": [],
                "required_action": "final manual review",
                "real_image_used_count": 4,
            },
        })
        return card_paths

    def test_builds_ready_manifest_only_for_consistent_valid_output_set(self):
        self._write_ready_fixture()

        manifest = build_card_news_result_manifest(self.root)

        self.assertEqual(manifest["status"], "ready")
        self.assertEqual([card["index"] for card in manifest["cards"]], [1, 2, 3, 4])
        self.assertEqual([card["role"] for card in manifest["cards"]], ["hook", "problem", "solution", "cta"])
        self.assertTrue(all(card["exists"] for card in manifest["cards"]))
        self.assertTrue(manifest["release_guard"]["ready"])
        self.assertEqual(manifest["output_set_identity"]["status"], "consistent")
        self.assertTrue(manifest["publishing"]["ready"])
        self.assertTrue(manifest["publishing"]["card_paths_match"])
        self.assertEqual(manifest["rights"]["status"], "pass")
        self.assertTrue(all(item["valid"] for item in manifest["release_guard"]["card_artifacts"]))

    def test_allowed_canvas_sizes_are_ready_and_arbitrary_size_is_blocked(self):
        for size in ((1080, 566), (1080, 1080), (1080, 1440)):
            with self.subTest(size=size):
                self._write_ready_fixture(size=size)
                manifest = build_card_news_result_manifest(self.root)
                self.assertEqual(manifest["status"], "ready")
                self.assertTrue(
                    all(
                        item["dimensions_ok"]
                        for item in manifest["release_guard"]["card_artifacts"]
                    )
                )

        self._write_ready_fixture(size=(800, 800))
        manifest = build_card_news_result_manifest(self.root)
        self.assertIn(
            "CN_ATOMIC_CARD_DIMENSIONS_INVALID",
            manifest["release_guard"]["issue_codes"],
        )
        self.assertFalse(manifest["release_guard"]["ready"])

    def test_layout_and_rendering_fallback_diagnostics_stay_separate(self):
        self._write_ready_fixture()
        manifest = build_card_news_result_manifest(self.root)
        self.assertTrue(manifest["qa"]["layout_fallback_used"])
        self.assertFalse(manifest["qa"]["rendering_fallback_used"])
        self.assertTrue(manifest["qa"]["fallback_used"])

    def test_manual_image_requirement_blocks_all_ready_states(self):
        self._write_ready_fixture()
        publishing_path = self.root / "storage/workflow_results/09_publishing_result.json"
        publishing = json.loads(publishing_path.read_text(encoding="utf-8"))
        publishing["manual_image_required"] = True
        publishing["operations"]["publishing_blocked"] = True
        publishing["operations"]["blocking_reasons"] = ["manual_image_required"]
        publishing_path.write_text(json.dumps(publishing), encoding="utf-8")

        manifest = build_card_news_result_manifest(self.root)

        self.assertEqual(manifest["status"], "incomplete")
        self.assertFalse(manifest["publishing"]["ready"])
        self.assertTrue(manifest["publishing"]["manual_image_required"])
        self.assertIn("manual_image_required", manifest["publishing"]["blocking_reasons"])

    def test_output_set_id_missing_incomplete_and_mismatch_are_fail_closed(self):
        cases = [
            ("missing", (None, None, None), "CN_ATOMIC_OUTPUT_SET_ID_MISSING"),
            ("incomplete", ("set-1", None, "set-1"), "CN_ATOMIC_OUTPUT_SET_ID_INCOMPLETE"),
            ("mismatch", ("set-1", "set-2", "set-1"), "CN_ATOMIC_OUTPUT_SET_ID_MISMATCH"),
        ]
        paths = (
            "storage/workflow_results/08_card_news_result.json",
            "storage/card_news/card_news_quality.json",
            "storage/workflow_results/09_publishing_result.json",
        )
        for status, ids, issue_code in cases:
            with self.subTest(status=status):
                self._write_ready_fixture()
                for path, output_set_id in zip(paths, ids):
                    file_path = self.root / path
                    payload = json.loads(file_path.read_text(encoding="utf-8"))
                    if output_set_id is None:
                        payload.pop("output_set_id", None)
                    else:
                        payload["output_set_id"] = output_set_id
                    file_path.write_text(json.dumps(payload), encoding="utf-8")
                manifest = build_card_news_result_manifest(self.root)
                self.assertEqual(manifest["output_set_identity"]["status"], status)
                self.assertIn(issue_code, manifest["release_guard"]["issue_codes"])
                self.assertFalse(manifest["publishing"]["ready"])

    def test_path_order_duplicate_and_outside_repository_are_blocked(self):
        card_paths = self._write_ready_fixture()
        publishing_path = self.root / "storage/workflow_results/09_publishing_result.json"
        publishing = json.loads(publishing_path.read_text(encoding="utf-8"))
        publishing["card_paths"] = [card_paths[1], card_paths[0], card_paths[2], card_paths[2]]
        publishing_path.write_text(json.dumps(publishing), encoding="utf-8")

        manifest = build_card_news_result_manifest(self.root)
        self.assertIn("CN_ATOMIC_PUBLISHING_PATH_DUPLICATE", manifest["release_guard"]["issue_codes"])
        self.assertIn("CN_ATOMIC_CARD_PATHS_MISMATCH", manifest["release_guard"]["issue_codes"])
        self.assertFalse(manifest["publishing"]["ready"])

        result_path = self.root / "storage/workflow_results/08_card_news_result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["cards"][0]["card_path"] = str(self.root.parent / "outside.png")
        result_path.write_text(json.dumps(result), encoding="utf-8")
        manifest = build_card_news_result_manifest(self.root)
        self.assertIn("CN_ATOMIC_CARD_PATH_INVALID", manifest["release_guard"]["issue_codes"])

    def test_empty_corrupt_and_wrong_dimension_png_are_blocked(self):
        cases = [
            ("empty", "CN_ATOMIC_CARD_FILE_EMPTY"),
            ("corrupt", "CN_ATOMIC_CARD_IMAGE_DECODE_FAILED"),
            ("dimension", "CN_ATOMIC_CARD_DIMENSIONS_INVALID"),
        ]
        for kind, issue_code in cases:
            with self.subTest(kind=kind):
                self._write_ready_fixture()
                target = self.root / "storage/card_news/card_news_2.png"
                if kind == "empty":
                    target.write_bytes(b"")
                elif kind == "corrupt":
                    target.write_bytes(b"not a png")
                else:
                    Image.new("RGB", (1079, 1080), "white").save(target)
                manifest = build_card_news_result_manifest(self.root)
                self.assertIn(issue_code, manifest["release_guard"]["issue_codes"])
                self.assertFalse(manifest["release_guard"]["ready"])
                self.assertFalse(manifest["publishing"]["ready"])

    def test_unknown_and_blocked_rights_never_become_ready(self):
        self._write_ready_fixture()
        quality_path = self.root / "storage/card_news/card_news_quality.json"
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        quality["checks"].pop("unlicensed_asset_not_rendered")
        quality_path.write_text(json.dumps(quality), encoding="utf-8")
        manifest = build_card_news_result_manifest(self.root)
        self.assertEqual(manifest["rights"]["status"], "unknown")
        self.assertIn("CARD_NEWS_RIGHTS_UNKNOWN", manifest["release_guard"]["issue_codes"])
        self.assertFalse(manifest["publishing"]["ready"])

        quality["checks"]["unlicensed_asset_not_rendered"] = False
        quality_path.write_text(json.dumps(quality), encoding="utf-8")
        manifest = build_card_news_result_manifest(self.root)
        self.assertEqual(manifest["rights"]["status"], "blocked")
        self.assertIn("CARD_NEWS_RIGHTS_BLOCKED", manifest["release_guard"]["issue_codes"])
        self.assertFalse(manifest["publishing"]["ready"])

    def test_missing_and_malformed_files_return_safe_fallback(self):
        (self.root / "storage/workflow_results/08_card_news_result.json").write_text("not json", encoding="utf-8")
        self._write_json("storage/card_news/card_news_quality.json", [])

        manifest = build_card_news_result_manifest(self.root)

        self.assertEqual(manifest["status"], "incomplete")
        self.assertEqual(len(manifest["cards"]), 0)
        self.assertFalse(manifest["publishing"]["ready"])
        self.assertGreaterEqual(len(manifest["qa"]["warnings"]), 3)


if __name__ == "__main__":
    unittest.main()
