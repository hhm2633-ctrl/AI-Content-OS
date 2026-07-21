import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.design_learning.local_image_intake import run_local_image_intake


class TestDesignLearningLocalImageIntake(unittest.TestCase):
    def test_unique_and_exact_duplicate_preserve_originals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "source", root / "output"
            source.mkdir()
            Image.new("RGB", (20, 10), "red").save(source / "a.png")
            (source / "b.png").write_bytes((source / "a.png").read_bytes())
            Image.new("RGB", (20, 10), "blue").save(source / "c.png")
            originals = {path.name: path.read_bytes() for path in source.iterdir()}

            result = run_local_image_intake(source, output)

            self.assertEqual(result["scan"]["unique_count"], 2)
            self.assertEqual(result["scan"]["exact_duplicate_count"], 1)
            duplicate = next(item for item in result["files"] if item["status"] == "exact_duplicate")
            owner = next(item for item in result["files"] if item["source_relative_path"] == "a.png")
            self.assertEqual(duplicate["duplicate_of"], owner["asset_id"])
            self.assertEqual(originals, {path.name: path.read_bytes() for path in source.iterdir()})

    def test_corrupt_unsupported_and_missing_are_fail_soft(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "source", root / "output"
            source.mkdir()
            (source / "broken.png").write_bytes(b"not an image")
            (source / "notes.txt").write_text("not an image", encoding="utf-8")

            result = run_local_image_intake(source, output)
            missing_result = run_local_image_intake(root / "missing", root / "missing-output")

            self.assertEqual(result["status"], "completed_with_warnings")
            self.assertEqual(result["scan"]["unreadable_count"], 1)
            self.assertEqual(result["scan"]["unsupported_count"], 1)
            self.assertEqual(missing_result["status"], "completed_with_warnings")
            self.assertTrue((root / "missing-output" / "local_image_manifest.json").is_file())

    def test_dimensions_staging_and_contact_sheet_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "source", root / "output"
            source.mkdir()
            Image.new("RGB", (30, 10), "green").save(source / "z.png")
            Image.new("RGB", (12, 24), "yellow").save(source / "A.png")

            result = run_local_image_intake(source, output)

            self.assertEqual(
                [item["source_relative_path"] for item in result["files"]],
                ["A.png", "z.png"],
            )
            self.assertEqual((result["files"][0]["width"], result["files"][0]["height"]), (12, 24))
            self.assertTrue(all((output / item["staged_relative_path"]).is_file() for item in result["files"]))
            self.assertEqual(result["contact_sheet"]["status"], "created")
            self.assertEqual(
                result["contact_sheet"]["included_asset_ids"],
                [item["asset_id"] for item in result["files"]],
            )
            self.assertTrue((output / "contact_sheet.png").is_file())
            written = json.loads((output / "local_image_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], "local_image_intake_v1")
            self.assertEqual(written["source_root"], "local_source")
            self.assertEqual(written["output_root"], "intake_output")
            self.assertFalse(written["path_policy"]["absolute_paths_persisted"])
            self.assertNotIn(str(root), json.dumps(written, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
