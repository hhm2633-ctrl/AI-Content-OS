import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.source_intake.reaction_media_discovery_provider import (
    ReactionMediaDiscoveryProvider,
)


class FakeOpenClip:
    def score_image_topics(self, path, topics, *, timeout_seconds):
        return {"status": "ok", "scores": {topics[0]: 0.8}}


class ReactionMediaDiscoveryProviderTests(unittest.TestCase):
    def test_approved_local_gif_produces_static_frame_and_motion_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gif_path = root / "놀람_리액션.gif"
            frames = [
                Image.new("RGB", (40, 30), "black"),
                Image.new("RGB", (40, 30), "white"),
            ]
            frames[0].save(
                gif_path,
                save_all=True,
                append_images=frames[1:],
                duration=80,
                loop=0,
            )
            gif_path.with_suffix(".gif.json").write_text(
                json.dumps(
                    {
                        "usage_approved": True,
                        "rights_status": "owner_approved",
                        "source_url": "https://example.com/reaction",
                        "emotion": "surprise",
                    }
                ),
                encoding="utf-8",
            )
            provider = ReactionMediaDiscoveryProvider(
                library_root=root,
                openclip=FakeOpenClip(),
                giphy_api_key="",
                tenor_api_key="",
            )

            result = provider.discover(
                "B",
                "search_reaction_media",
                {"title": "충격적인 반전"},
            )

            self.assertEqual("ok", result["status"])
            asset = result["assets"][0]
            self.assertTrue(asset["render_allowed"])
            self.assertEqual("gif_representative_frame", asset["type"])
            self.assertEqual(str(gif_path), asset["motion_source_path"])
            self.assertEqual(2, asset["frame_count"])
            self.assertTrue(Path(asset["local_path"]).is_file())
            self.assertEqual("giphy_api_key_missing", result["diagnostics"]["giphy"])
            self.assertEqual("tenor_api_key_missing", result["diagnostics"]["tenor"])

    def test_unapproved_local_asset_remains_reference_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "공감.png"
            Image.new("RGB", (20, 20), "blue").save(image_path)
            provider = ReactionMediaDiscoveryProvider(
                library_root=root,
                openclip=FakeOpenClip(),
                giphy_api_key="",
                tenor_api_key="",
            )

            result = provider.discover(
                "A",
                "search_reaction_media",
                {"title": "공감되는 이야기"},
            )

            self.assertFalse(result["assets"][0]["render_allowed"])
            self.assertEqual("unverified", result["assets"][0]["rights_status"])


if __name__ == "__main__":
    unittest.main()
