import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.card_news.source_image_motion_montage import (
    render_source_image_motion_montage,
)


class SourceImageMotionMontageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _image_record(self, name, color, **overrides):
        path = self.root / f"{name}.png"
        Image.new("RGB", (96, 120), color).save(path)
        record = {
            "asset_id": name,
            "local_path": str(path),
            "source_url": f"https://official.example/{name}",
            "source_name": "Official Brand",
            "origin": "official",
            "rights_status": "unrecorded",
        }
        record.update(overrides)
        return record

    def test_requires_two_valid_traced_local_images(self):
        result = render_source_image_motion_montage(
            [self._image_record("one", "red")],
            self.root / "one.mp4",
        )
        self.assertEqual(result["reason_code"], "insufficient_valid_images")
        self.assertFalse(result["render_executed"])

    def test_rejects_generated_ap_and_reference_only_assets(self):
        records = [
            self._image_record("generated", "red", origin="generated"),
            self._image_record("ap", "blue", ap_source=True),
            self._image_record("reference", "green", reference_only=True),
        ]
        result = render_source_image_motion_montage(records, self.root / "blocked.mp4")
        self.assertEqual(result["reason_code"], "insufficient_valid_images")
        reasons = {
            reason
            for item in result["diagnostics"]
            for reason in item.get("reason_codes", [])
        }
        self.assertIn("origin_not_allowed", reasons)
        self.assertIn("ap_reference_only", reasons)
        self.assertIn("reference_only", reasons)

    def test_renders_tiny_mp4_and_deterministic_source_sidecar(self):
        records = [
            self._image_record("first", "#d8c2a6"),
            self._image_record("second", "#f3a8bb"),
            self._image_record("third", "#84c6d8"),
        ]
        output = self.root / "montage.mp4"
        result = render_source_image_motion_montage(
            records,
            output,
            width=96,
            height=120,
            fps=5,
            seconds_per_image=0.2,
            transition_seconds=0.05,
        )
        self.assertEqual(result["status"], "motion_montage_ready")
        self.assertTrue(result["render_executed"])
        self.assertFalse(result["publish_executed"])
        self.assertTrue(output.is_file())
        self.assertGreater(output.stat().st_size, 0)
        manifest_path = Path(result["source_manifest_path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["method"], "source_still_images_zoom_pan_crossfade")
        self.assertFalse(manifest["generated_source_footage"])
        self.assertEqual([item["asset_id"] for item in manifest["sources"]], ["first", "second", "third"])
        self.assertEqual(manifest["frame_count"], 3)

    def test_remote_or_missing_source_does_not_render(self):
        records = [
            self._image_record("valid", "white"),
            {
                "asset_id": "remote",
                "local_path": "https://example.com/image.jpg",
                "source_url": "https://example.com/source",
                "origin": "official",
            },
        ]
        result = render_source_image_motion_montage(records, self.root / "missing.mp4")
        self.assertEqual(result["reason_code"], "insufficient_valid_images")
        self.assertFalse((self.root / "missing.mp4").exists())


if __name__ == "__main__":
    unittest.main()
