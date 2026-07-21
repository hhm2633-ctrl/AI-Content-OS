import copy
import unittest

from modules.source_intake.candidate_selection_signal_normalizer import (
    CANDIDATE_SELECTION_SIGNAL_NORMALIZER_VERSION,
    normalize_candidate_selection_signals,
)


class TestCandidateSelectionSignalNormalizer(unittest.TestCase):
    def test_unknown_inputs_remain_unknown_and_side_effect_free(self):
        candidate = {"id": "a"}
        original = copy.deepcopy(candidate)

        result = normalize_candidate_selection_signals(candidate)
        self.assertEqual(result["schema_version"], CANDIDATE_SELECTION_SIGNAL_NORMALIZER_VERSION)
        self.assertIsNone(result["source_count"])
        self.assertIsNone(result["reaction_count"])
        self.assertIsNone(result["media_count"])
        self.assertNotEqual(id(result), id(candidate))
        self.assertEqual(candidate, original)
        self.assertEqual(result["signal_provenance"]["source_count"]["status"], "missing")

    def test_source_count_from_urls_and_distinct_domains(self):
        candidate = {
            "urls": [
                "https://a.com/path",
                "https://A.com/other",
                "https://b.com/x",
            ]
        }
        result = normalize_candidate_selection_signals(candidate)
        self.assertEqual(result["source_count"], 2)
        self.assertEqual(result["signal_provenance"]["source_count"]["status"], "normalized")
        self.assertEqual(result["signal_provenance"]["source_count"]["item_count"], 3)
        self.assertEqual(result["signal_provenance"]["source_count"]["distinct_count"], 2)

    def test_reaction_count_sums_named_alias_groups_without_double_count(self):
        candidate = {
            "comments": "3",
            "comment_count": 10,
            "likes": "4",
            "like_count": 100,
            "reaction_count": 2,
            "public_reaction": 3,
        }
        result = normalize_candidate_selection_signals(candidate)
        self.assertEqual(result["reaction_count"], 112)
        self.assertEqual(result["signal_provenance"]["reaction_count"]["status"], "normalized")
        self.assertEqual(
            set(result["signal_provenance"]["reaction_count"]["used_fields"]),
            {"comment_count", "like_count", "reaction_count"},
        )

    def test_media_count_from_asset_image_video_lists(self):
        candidate = {
            "images": ["a.png", "a.png", "b.png"],
            "videos": ["v.mp4"],
            "media": ["x.bin"],
        }
        result = normalize_candidate_selection_signals(candidate)
        self.assertEqual(result["media_count"], 4)
        self.assertEqual(result["signal_provenance"]["media_count"]["status"], "normalized")
        self.assertEqual(result["signal_provenance"]["media_count"]["item_count"], 5)

    def test_negative_invalid_nan_and_bools_are_rejected(self):
        result_negative = normalize_candidate_selection_signals({"source_count": "-1", "reaction_count": -2, "media_count": True, "urls": []})
        self.assertIsNone(result_negative["source_count"])
        self.assertIsNone(result_negative["media_count"])
        self.assertEqual(result_negative["signal_provenance"]["media_count"]["status"], "invalid")

        result_nan = normalize_candidate_selection_signals({"reaction_count": float("nan"), "urls": [], "images": []})
        self.assertIsNone(result_nan["reaction_count"])
        self.assertEqual(result_nan["signal_provenance"]["reaction_count"]["status"], "invalid")

    def test_malformed_containers_are_invalid(self):
        urls_invalid = normalize_candidate_selection_signals({"urls": "https://example.com"})
        self.assertIsNone(urls_invalid["source_count"])
        self.assertEqual(urls_invalid["signal_provenance"]["source_count"]["status"], "invalid")

        media_invalid = normalize_candidate_selection_signals({"images": "not-a-list"})
        self.assertIsNone(media_invalid["media_count"])
        self.assertEqual(media_invalid["signal_provenance"]["media_count"]["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
