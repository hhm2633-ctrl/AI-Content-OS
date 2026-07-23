import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.source_intake.reaction_media_discovery_provider import (
    ReactionMediaDiscoveryProvider,
)


class FakeOpenClip:
    def __init__(self, scores):
        self.scores = scores

    def score_image_topics(self, path, topics, *, timeout_seconds):
        return {"scores": {topic: self.scores.get(topic, 0.0) for topic in topics}}


class ReactionMediaRebalanceTests(unittest.TestCase):
    def test_lexical_match_cannot_bypass_openclip_minimum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGB", (64, 64), "white").save(root / "놀람반응.png")
            (root / "놀람반응.json").write_text(
                '{"usage_approved": true, "rights_status": "owner_approved"}',
                encoding="utf-8",
            )
            provider = ReactionMediaDiscoveryProvider(
                library_root=root,
                openclip=FakeOpenClip(
                    {
                        "놀람 반응": 0.10,
                        "surprise": 0.09,
                        "generic abstract background": 0.30,
                    }
                ),
            )
            result = provider._local("놀람 반응", "surprise")
            self.assertFalse(result[0]["topic_relevant"])


if __name__ == "__main__":
    unittest.main()
