import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.compliance.card_news_publish_gate import (
    _repo_relative_path,
    _valid_image_file,
)


class TestExternalCardNewsPublishPaths(unittest.TestCase):
    def test_configured_external_card_is_managed_and_arbitrary_absolute_is_not(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "card_news"
            card = root / "output_sets" / "sets" / "set-1" / "cards" / "card.png"
            card.parent.mkdir(parents=True)
            Image.new("RGB", (1080, 1080), "white").save(card, format="PNG")
            outside = Path(temp_dir) / "outside.png"
            Image.new("RGB", (1080, 1080), "white").save(outside, format="PNG")

            with patch(
                "modules.compliance.card_news_publish_gate.resolve_external_path",
                return_value=root,
            ):
                self.assertTrue(_repo_relative_path(str(card)))
                self.assertTrue(_valid_image_file(str(card)))
                self.assertFalse(_repo_relative_path(str(outside)))
                self.assertFalse(_valid_image_file(str(outside)))


if __name__ == "__main__":
    unittest.main()
