import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.card_news.card_news_result_manifest import build_card_news_result_manifest


class TestCardNewsOutputSetIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "storage/workflow_results").mkdir(parents=True)
        (self.root / "storage/card_news").mkdir(parents=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_json(self, relative_path, payload):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _read_json(self, relative_path):
        return json.loads((self.root / relative_path).read_text(encoding="utf-8"))

    def _write_json_back(self, relative_path, payload):
        (self.root / relative_path).write_text(json.dumps(payload), encoding="utf-8")

    def _write_png(self, name, size=(1080, 1080)):
        path = self.root / "storage/card_news" / name
        Image.new("RGB", size, (40, 50, 60)).save(path)
        return path.relative_to(self.root).as_posix()

    def _ready_fixture(self, output_set_id="run-001"):
        paths = [self._write_png(f"card_news_{index}.png") for index in range(1, 5)]
        self._write_json("storage/workflow_results/08_card_news_result.json", {
            "status": "card_news_completed",
            "output_set_id": output_set_id,
            "cards": [
                {"index": index, "card_path": paths[index - 1], "status": "created"}
                for index in range(1, 5)
            ],
            "image_sourcing_status": {"manual_image_required": False},
        })
        self._write_json("storage/card_news/card_news_quality.json", {
            "passed": True,
            "output_set_id": output_set_id,
            "checks": {
                "unlicensed_asset_not_rendered": True,
                "attribution_needed": False,
                "attribution_present": False,
            },
        })
        self._write_json("storage/workflow_results/09_publishing_result.json", {
            "status": "publishing_ready",
            "output_set_id": output_set_id,
            "manual_image_required": False,
            "card_paths": paths,
            "operations": {
                "publishing_blocked": False,
                "blocking_reasons": [],
                "real_image_used_count": 4,
            },
        })
        return paths

    def _manifest(self):
        return build_card_news_result_manifest(self.root)

    def _assert_blocked(self, manifest, issue_code=None):
        self.assertEqual(manifest["status"], "incomplete")
        self.assertFalse(manifest["release_guard"]["ready"])
        self.assertFalse(manifest["publishing"]["ready"])
        self.assertTrue(manifest["publishing"]["blocked"])
        if issue_code:
            self.assertIn(issue_code, manifest["release_guard"]["issue_codes"])
            self.assertIn(issue_code, manifest["publishing"]["blocking_reasons"])

    def test_output_set_id_missing_incomplete_and_mismatch_fail_closed(self):
        files = [
            "storage/workflow_results/08_card_news_result.json",
            "storage/card_news/card_news_quality.json",
            "storage/workflow_results/09_publishing_result.json",
        ]
        cases = [
            ((None, None, None), "missing", "CN_ATOMIC_OUTPUT_SET_ID_MISSING"),
            (("run-1", None, "run-1"), "incomplete", "CN_ATOMIC_OUTPUT_SET_ID_INCOMPLETE"),
            (("run-1", "run-2", "run-1"), "mismatch", "CN_ATOMIC_OUTPUT_SET_ID_MISMATCH"),
        ]
        for ids, status, code in cases:
            with self.subTest(status=status):
                self._ready_fixture()
                for filename, value in zip(files, ids):
                    payload = self._read_json(filename)
                    if value is None:
                        payload.pop("output_set_id", None)
                    else:
                        payload["output_set_id"] = value
                    self._write_json_back(filename, payload)
                manifest = self._manifest()
                self.assertEqual(manifest["output_set_identity"]["status"], status)
                self._assert_blocked(manifest, code)

    def test_three_cards_duplicate_index_and_order_mismatch_fail_closed(self):
        paths = self._ready_fixture()
        result_file = "storage/workflow_results/08_card_news_result.json"
        result = self._read_json(result_file)
        result["cards"] = result["cards"][:3]
        self._write_json_back(result_file, result)
        self._assert_blocked(self._manifest(), "CN_ATOMIC_CARD_PATHS_MISMATCH")

        self._ready_fixture()
        result = self._read_json(result_file)
        result["cards"][3]["index"] = 3
        self._write_json_back(result_file, result)
        self._assert_blocked(self._manifest(), "CN_ATOMIC_CARD_PATHS_MISMATCH")

        self._ready_fixture()
        publishing_file = "storage/workflow_results/09_publishing_result.json"
        publishing = self._read_json(publishing_file)
        publishing["card_paths"] = [paths[1], paths[0], paths[2], paths[3]]
        self._write_json_back(publishing_file, publishing)
        self._assert_blocked(self._manifest(), "CN_ATOMIC_CARD_PATHS_MISMATCH")

    def test_five_card_result_must_fail_closed_instead_of_ignoring_extra_card(self):
        self._ready_fixture()
        extra_path = self._write_png("card_news_5.png")
        result_file = "storage/workflow_results/08_card_news_result.json"
        result = self._read_json(result_file)
        result["cards"].append({"index": 5, "card_path": extra_path, "status": "created"})
        self._write_json_back(result_file, result)
        self._assert_blocked(self._manifest(), "CN_ATOMIC_CARD_PATHS_MISMATCH")

    def test_duplicate_and_outside_paths_fail_closed(self):
        paths = self._ready_fixture()
        publishing_file = "storage/workflow_results/09_publishing_result.json"
        publishing = self._read_json(publishing_file)
        publishing["card_paths"] = [paths[0], paths[0], paths[2], paths[3]]
        self._write_json_back(publishing_file, publishing)
        manifest = self._manifest()
        self._assert_blocked(manifest, "CN_ATOMIC_PUBLISHING_PATH_DUPLICATE")

        self._ready_fixture()
        result_file = "storage/workflow_results/08_card_news_result.json"
        result = self._read_json(result_file)
        result["cards"][0]["card_path"] = str(self.root.parent / "outside.png")
        self._write_json_back(result_file, result)
        self._assert_blocked(self._manifest(), "CN_ATOMIC_CARD_PATH_INVALID")

    def test_empty_corrupt_and_wrong_size_png_fail_closed(self):
        cases = [
            ("empty", "CN_ATOMIC_CARD_FILE_EMPTY"),
            ("corrupt", "CN_ATOMIC_CARD_IMAGE_DECODE_FAILED"),
            ("wrong_size", "CN_ATOMIC_CARD_DIMENSIONS_INVALID"),
        ]
        for mutation, code in cases:
            with self.subTest(mutation=mutation):
                self._ready_fixture()
                target = self.root / "storage/card_news/card_news_2.png"
                if mutation == "empty":
                    target.write_bytes(b"")
                elif mutation == "corrupt":
                    target.write_bytes(b"not-an-image")
                else:
                    Image.new("RGB", (1080, 1079), "white").save(target)
                self._assert_blocked(self._manifest(), code)

    def test_loose_or_stale_pngs_never_substitute_for_referenced_set(self):
        self._write_png("card_news_1.png")
        self._write_png("card_news_2.png")
        self._write_png("card_news_3.png")
        self._write_png("card_news_4.png")
        self._write_png("latest.png")
        manifest = self._manifest()
        self._assert_blocked(manifest, "CN_ATOMIC_OUTPUT_SET_ID_MISSING")
        self.assertTrue(all(card["path"] is None for card in manifest["cards"]))

        self._ready_fixture()
        stale = self._write_png("card_news_stale.png")
        self.assertTrue((self.root / stale).is_file())
        manifest = self._manifest()
        self.assertTrue(manifest["release_guard"]["ready"])
        self.assertNotIn(stale, [card["path"] for card in manifest["cards"]])

    def test_interrupted_stage_files_are_fail_closed(self):
        cases = [
            "storage/card_news/card_news_quality.json",
            "storage/workflow_results/09_publishing_result.json",
        ]
        for missing_file in cases:
            with self.subTest(missing_file=missing_file):
                self._ready_fixture()
                (self.root / missing_file).unlink()
                self._assert_blocked(self._manifest())

        self._ready_fixture()
        quality = self.root / "storage/card_news/card_news_quality.json"
        quality.write_text("{interrupted", encoding="utf-8")
        self._assert_blocked(self._manifest())

    def test_manual_image_and_rights_gates_remain_fail_closed(self):
        self._ready_fixture()
        publishing_file = "storage/workflow_results/09_publishing_result.json"
        publishing = self._read_json(publishing_file)
        publishing["manual_image_required"] = True
        self._write_json_back(publishing_file, publishing)
        manifest = self._manifest()
        self.assertFalse(manifest["publishing"]["ready"])
        self.assertTrue(manifest["publishing"]["manual_image_required"])

        self._ready_fixture()
        quality_file = "storage/card_news/card_news_quality.json"
        quality = self._read_json(quality_file)
        quality["checks"]["unlicensed_asset_not_rendered"] = False
        self._write_json_back(quality_file, quality)
        self._assert_blocked(self._manifest(), "CARD_NEWS_RIGHTS_BLOCKED")


if __name__ == "__main__":
    unittest.main()
