import unittest

from modules.card_news.reference_v2_satori_adapter import (
    build_reference_v2_satori_tree,
)


class ReferenceV2SatoriAdapterTests(unittest.TestCase):
    def test_preserves_geometry_and_builds_media_and_text_nodes(self):
        adapted = {
            "status": "adapted",
            "geometry_hash": "hash-1",
            "regions": [
                {
                    "region_id": "photo",
                    "role": "primary_media",
                    "box_norm": [0.0, 0.0, 1.0, 0.7],
                    "z_index": 1,
                },
                {
                    "region_id": "title",
                    "role": "headline",
                    "box_norm": [0.08, 0.72, 0.84, 0.2],
                    "z_index": 2,
                },
            ],
            "media_bindings": [
                {
                    "region_id": "photo",
                    "asset": {"remote_url": "https://img.example/photo.jpg"},
                }
            ],
            "content_bindings": [
                {"region_id": "title", "content": "학습된 제목"}
            ],
            "reference_consumption_receipt": {
                "geometry_modified": False,
                "geometry_hash": "hash-1",
            },
        }

        result = build_reference_v2_satori_tree(adapted)

        self.assertEqual("ready", result["status"])
        children = result["tree"]["props"]["children"]
        self.assertEqual("70.000000%", children[0]["props"]["style"]["height"])
        self.assertEqual("학습된 제목", children[1]["props"]["children"])
        self.assertFalse(
            result["reference_consumption_receipt"]["geometry_modified"]
        )

    def test_missing_adapted_geometry_blocks(self):
        result = build_reference_v2_satori_tree({"status": "blocked"})
        self.assertEqual("blocked", result["status"])


if __name__ == "__main__":
    unittest.main()
