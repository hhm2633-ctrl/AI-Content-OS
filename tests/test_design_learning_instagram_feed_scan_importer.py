import json
import tempfile
import unittest
from pathlib import Path

from modules.design_learning.instagram_feed_scan_importer import import_scan
from modules.design_learning.layout_candidate_map import known_layout_ids


def _base_candidate(**overrides):
    candidate = {
        "observed_order": 1,
        "source_surface": "home_feed_natural",
        "account_handle": "example.account",
        "post_url": "https://www.instagram.com/p/example/",
        "visible_post_age": "1일",
        "post_type": "carousel_cardnews",
        "topic_category_guess": "example topic",
        "cover_hook_text": "example hook",
        "cover_visual_type": "bold_text_over_illustration",
        "color_palette": "white/black",
        "typography_style": "bold sans-serif",
        "image_usage": "illustration",
        "slide_count_if_visible": "5",
        "cta_type": "caption-driven",
        "visible_likes": 10,
        "visible_comments": 2,
        "why_it_stopped_scroll": "example reason",
        "mapped_existing_layout_candidate": "tutorial",
        "risk_flags": [],
        "screenshot_path_if_captured": None,
        "notes": "example notes",
    }
    candidate.update(overrides)
    return candidate


class TestInstagramFeedScanImporter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_scan(self, candidates):
        scan_path = self.root / "scan.json"
        scan_path.write_text(
            json.dumps({
                "scan_id": "unit_test_scan",
                "scan_date": "2026-07-15",
                "candidates": candidates,
            }),
            encoding="utf-8",
        )
        return scan_path

    def test_known_layout_ids_has_exactly_ten_layouts(self):
        self.assertEqual(len(known_layout_ids()), 10)

    def test_imports_candidate_mapped_to_known_layout_as_candidate_status(self):
        scan_path = self._write_scan([_base_candidate()])

        result = import_scan(scan_path)

        self.assertEqual(result["imported_count"], 1)
        self.assertEqual(result["rejected_count"], 0)
        imported = result["candidates"][0]
        self.assertEqual(imported["status"], "candidate")
        self.assertEqual(imported["layout_id"], "tutorial")
        self.assertEqual(imported["evidence"]["post_url"], "https://www.instagram.com/p/example/")
        self.assertEqual(imported["evidence"]["observed_metrics"]["visible_likes"], 10)

    def test_rejects_candidate_with_layout_id_outside_the_ten_known_layouts(self):
        scan_path = self._write_scan([
            _base_candidate(mapped_existing_layout_candidate="brand_new_layout_not_in_engine"),
        ])

        result = import_scan(scan_path)

        self.assertEqual(result["imported_count"], 0)
        self.assertEqual(result["rejected_count"], 1)
        self.assertEqual(result["rejected"][0]["reason"], "unmapped_layout_id")

    def test_rejects_candidate_missing_layout_mapping(self):
        scan_path = self._write_scan([
            _base_candidate(mapped_existing_layout_candidate=None),
        ])

        result = import_scan(scan_path)

        self.assertEqual(result["rejected_count"], 1)
        self.assertEqual(result["rejected"][0]["reason"], "missing_layout_mapping")

    def test_rejects_non_carousel_cardnews_post_type(self):
        scan_path = self._write_scan([
            _base_candidate(post_type="reel"),
        ])

        result = import_scan(scan_path)

        self.assertEqual(result["rejected_count"], 1)
        self.assertEqual(result["rejected"][0]["reason"], "not_carousel_cardnews")

    def test_low_confidence_when_risk_flags_present(self):
        scan_path = self._write_scan([
            _base_candidate(risk_flags=["cover visual details could not be confirmed"]),
        ])

        result = import_scan(scan_path)

        self.assertEqual(result["candidates"][0]["confidence"], "low")

    def test_low_confidence_when_core_design_fields_are_null(self):
        scan_path = self._write_scan([
            _base_candidate(cover_hook_text=None, cover_visual_type=None, why_it_stopped_scroll=None),
        ])

        result = import_scan(scan_path)

        self.assertEqual(result["candidates"][0]["confidence"], "low")

    def test_does_not_fabricate_engagement_when_metrics_are_null(self):
        scan_path = self._write_scan([
            _base_candidate(visible_likes=None, visible_comments=None),
        ])

        result = import_scan(scan_path)

        metrics = result["candidates"][0]["evidence"]["observed_metrics"]
        self.assertIsNone(metrics["visible_likes"])
        self.assertIsNone(metrics["visible_comments"])

    def test_missing_scan_file_returns_candidate_status_with_warning_not_exception(self):
        missing_path = self.root / "does_not_exist.json"

        result = import_scan(missing_path)

        self.assertEqual(result["status"], "candidate")
        self.assertEqual(result["imported_count"], 0)
        self.assertTrue(any("missing" in warning for warning in result["warnings"]))

    def test_malformed_candidates_field_does_not_raise(self):
        scan_path = self.root / "scan.json"
        scan_path.write_text(json.dumps({"scan_id": "bad", "candidates": "not_a_list"}), encoding="utf-8")

        result = import_scan(scan_path)

        self.assertEqual(result["imported_count"], 0)
        self.assertTrue(any("candidates" in warning for warning in result["warnings"]))

    def test_writes_output_file_when_output_path_given(self):
        scan_path = self._write_scan([_base_candidate()])
        output_path = self.root / "out" / "candidates.json"

        import_scan(scan_path, output_path=output_path)

        self.assertTrue(output_path.is_file())
        written = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(written["imported_count"], 1)


if __name__ == "__main__":
    unittest.main()
