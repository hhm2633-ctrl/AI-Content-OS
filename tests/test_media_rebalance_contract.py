import unittest

from modules.media_intelligence.source_media_quality_gate import SourceMediaQualityGate


class MediaRebalanceContractTests(unittest.TestCase):
    def test_ocr_requirement_depends_on_media_class(self):
        gate = SourceMediaQualityGate()
        self.assertTrue(gate._ocr_required({"media_type": "comment_screenshot"}))
        self.assertTrue(gate._ocr_required({"asset_class": "document"}))
        self.assertFalse(gate._ocr_required({"media_type": "editorial_photo"}))


if __name__ == "__main__":
    unittest.main()
