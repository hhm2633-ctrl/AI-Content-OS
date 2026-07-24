import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.card_news.story_comment_spotlight import (
    build_story_comment_spotlight,
)


class StoryCommentSpotlightTests(unittest.TestCase):
    def test_ranks_masked_crops_by_ocr_reaction_and_composes_cover(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            comments = []
            reactions = (12, 175, 124)
            for index, reaction in enumerate(reactions, start=1):
                path = root / f"comment_{index:03d}_masked.png"
                Image.new("RGB", (600, 180), "white").save(path)
                comments.append(
                    {
                        "comment_id": f"comment-{index}",
                        "text": f"실제 논쟁 댓글 {index} 남편 육아 둘째?",
                        "source_url": "https://community.example/post",
                        "screenshot_path": str(path),
                        "identity_masked": True,
                        "comment_slide_eligible": True,
                        "is_real_comment": True,
                    }
                )

            by_path = {
                str(root / f"comment_{index:03d}_masked.png"): reaction
                for index, reaction in enumerate(reactions, start=1)
            }

            def fake_ocr(path, timeout_seconds):
                reaction = by_path[path]
                return {
                    "success": True,
                    "status": "completed",
                    "lines": (str(reaction),),
                    "boxes": ((500.0, 20.0, 550.0, 40.0),),
                }

            output = root / "spotlight.png"
            result = build_story_comment_spotlight(
                comments,
                output,
                ocr_extractor=fake_ocr,
            )

            self.assertEqual(result["status"], "ready")
            self.assertEqual(
                [item["reaction_count"] for item in result["spotlight_selected"]],
                [175, 124],
            )
            self.assertTrue(output.is_file())
            self.assertFalse(result["source_modified"])
            self.assertFalse(result["publish_authorized"])
            with Image.open(output) as rendered:
                self.assertEqual(rendered.size, (1080, 1440))

    def test_rejects_unmasked_or_missing_comment_crops(self):
        result = build_story_comment_spotlight(
            [
                {
                    "text": "댓글",
                    "screenshot_path": "missing.png",
                    "identity_masked": False,
                    "comment_slide_eligible": False,
                    "is_real_comment": True,
                }
            ],
            "unused.png",
            ocr_extractor=lambda *args, **kwargs: {},
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(
            result["reason_code"],
            "eligible_masked_comment_crop_missing",
        )
