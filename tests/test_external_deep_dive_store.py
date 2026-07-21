import json
import tempfile
import unittest
from pathlib import Path

from modules.source_intake.external_deep_dive_store import write_deep_dive_artifact


class TestExternalDeepDiveStore(unittest.TestCase):
    def test_writes_json_beneath_external_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = write_deep_dive_artifact(
                date_str="2026-07-18",
                stage="raw_html",
                source_id="news-1",
                filename="article.json",
                payload={"title": "source"},
                base_dir=temp_dir,
            )

            self.assertEqual(
                target,
                Path(temp_dir)
                / "source_intake"
                / "2026-07-18"
                / "deep_dive"
                / "raw_html"
                / "news-1"
                / "article.json",
            )
            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")),
                {"title": "source"},
            )

    def test_writes_binary_media(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = write_deep_dive_artifact(
                date_str="2026-07-18",
                stage="screenshots",
                source_id="brand",
                filename="frame.png",
                payload=b"png-data",
                base_dir=temp_dir,
            )
            self.assertEqual(target.read_bytes(), b"png-data")

    def test_rejects_traversal_and_unknown_stage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                write_deep_dive_artifact(
                    date_str="2026-07-18",
                    stage="screenshots",
                    source_id="../escape",
                    filename="x.png",
                    payload=b"x",
                    base_dir=temp_dir,
                )
            with self.assertRaises(ValueError):
                write_deep_dive_artifact(
                    date_str="2026-07-18",
                    stage="unknown",
                    source_id="source",
                    filename="x.bin",
                    payload=b"x",
                    base_dir=temp_dir,
                )


if __name__ == "__main__":
    unittest.main()
