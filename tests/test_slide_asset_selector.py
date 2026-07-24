import unittest

from modules.media_intelligence.slide_asset_selector import SlideAssetSelector


class SlideAssetSelectorTests(unittest.TestCase):
    def test_direct_topic_precedes_reaction_score(self):
        source = "https://publisher.example/story"
        result = SlideAssetSelector().select(
            [{"page": 1, "slide_role": "hook"}],
            [
                {
                    "asset_id": "reaction",
                    "local_path": "F:/reaction.png",
                    "rights_status": "owner_approved",
                    "source_provider": "local_reaction_library",
                    "openclip_score": 0.99,
                    "quality_gate": {"passed": True, "relevant_score": 0.99},
                },
                {
                    "asset_id": "direct",
                    "local_path": "F:/direct.jpg",
                    "source_url": source,
                    "rights_status": "source_editorial_usable",
                    "openclip_score": 0.2,
                    "quality_gate": {"passed": True, "relevant_score": 0.2},
                },
            ],
            topic="직접 주제",
            emotion="긴장",
            source_urls=[source],
        )
        self.assertEqual(result["slides"][0]["asset_refs"], ["direct"])

    def test_unverified_or_remote_assets_are_rejected(self):
        result = SlideAssetSelector().select(
            [{"page": 1, "slide_role": "hook"}],
            [
                {
                    "asset_id": "remote",
                    "local_path": "https://example.com/a.jpg",
                    "rights_status": "licensed",
                },
                {
                    "asset_id": "unverified",
                    "local_path": "F:/a.jpg",
                    "rights_status": "unverified",
                },
            ],
        )
        self.assertEqual(result["status"], "no_eligible_assets")
        self.assertEqual(result["slides"][0]["asset_refs"], [])

    def test_quality_gate_and_minimum_relevance_are_required(self):
        result = SlideAssetSelector().select(
            [{"page": 1, "slide_role": "hook"}],
            [
                {
                    "asset_id": "no-gate",
                    "local_path": "F:/no-gate.jpg",
                    "rights_status": "owned",
                },
                {
                    "asset_id": "weak",
                    "local_path": "F:/weak.jpg",
                    "rights_status": "owned",
                    "quality_gate": {"passed": True, "relevant_score": 0.19},
                },
            ],
        )
        self.assertEqual(result["status"], "no_eligible_assets")
        self.assertEqual(
            {row["reason_code"] for row in result["rejected_assets"]},
            {"quality_gate_required", "minimum_relevance_not_met"},
        )


if __name__ == "__main__":
    unittest.main()
