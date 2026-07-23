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
                },
                {
                    "asset_id": "direct",
                    "local_path": "F:/direct.jpg",
                    "source_url": source,
                    "rights_status": "source_editorial_usable",
                    "openclip_score": 0.2,
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


if __name__ == "__main__":
    unittest.main()
