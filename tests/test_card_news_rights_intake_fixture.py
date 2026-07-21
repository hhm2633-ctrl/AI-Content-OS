import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from modules.card_news.evidence_input_validator import EvidenceInputValidator


class TestCardNewsRightsIntakeFixture(unittest.TestCase):
    NOW = datetime(2026, 7, 13, tzinfo=timezone.utc)
    FIXTURES = Path(__file__).parent / "fixtures" / "card_news_rights"

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        target = self.root / "tests" / "fixtures" / "card_news_rights"
        target.mkdir(parents=True)
        spec = json.loads((self.FIXTURES / "technical_fixture_spec.json").read_text(encoding="utf-8"))
        Image.new(spec["mode"], (spec["width"], spec["height"]), tuple(spec["color"])).save(
            target / spec["output_name"]
        )
        (target / "ownership_record.txt").write_text(
            (self.FIXTURES / "ownership_record.txt").read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.manifest = json.loads((self.FIXTURES / "intake_manifest.json").read_text(encoding="utf-8"))
        self.validator = EvidenceInputValidator(self.root, max_age_days=30)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _codes(result):
        return {issue["code"] for issue in result["issues"]}

    def _validate(self, manifest=None):
        return self.validator.validate(manifest or self.manifest, self.NOW)

    def test_valid_first_party_fixture_keeps_publish_gates_closed(self):
        result = self._validate()
        self.assertEqual(self.manifest["fixture_classification"], "technical_fixture_not_publish_approved")
        self.assertTrue(result["input_valid"])
        self.assertTrue(result["assets"][0]["asset_decoded"])
        self.assertEqual(result["assets"][0]["permission_evidence"]["type"], "ownership_record")
        self.assertTrue(result["manual_image_required"])
        self.assertFalse(result["publishing_ready"])
        self.assertFalse(result["real_image_gate"]["satisfied"])

    def test_credential_urls_are_blocked_and_secrets_removed(self):
        manifest = copy.deepcopy(self.manifest)
        asset = manifest["assets"][0]
        asset["source_url"] = "https://user:secret@example.org/source"
        asset["permission_evidence"]["reference"] = "https://key:token@example.org/rights"
        result = self._validate(manifest)
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("source_url_invalid", self._codes(result))
        self.assertIn("permission_reference_invalid", self._codes(result))
        for secret in ("user:secret", "key:token", "secret", "token"):
            self.assertNotIn(secret, serialized)

    def test_private_url_is_blocked(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["assets"][0]["source_url"] = "http://169.254.1.2/source"
        self.assertIn("source_url_invalid", self._codes(self._validate(manifest)))

    def test_rights_mismatch_is_fail_closed(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["assets"][0]["permission_evidence"]["type"] = "written_permission"
        result = self._validate(manifest)
        self.assertIn("permission_type_mismatch", self._codes(result))
        self.assertFalse(result["publishing_ready"])

    def test_corrupt_image_is_rejected(self):
        (self.root / self.manifest["assets"][0]["asset_path"]).write_bytes(b"corrupt")
        self.assertIn("asset_image_invalid", self._codes(self._validate()))

    def test_path_escape_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["assets"][0]["asset_path"] = "../outside.png"
        manifest["assets"][0]["permission_evidence"]["asset_path"] = "../outside.png"
        self.assertIn("asset_path_outside_repository", self._codes(self._validate(manifest)))

    def test_missing_attribution_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["assets"][0]["attribution_text"] = ""
        self.assertIn("attribution_missing", self._codes(self._validate(manifest)))

    def test_keyword_only_topic_review_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["assets"][0]["topic_relevance_review"]["status"] = "pending"
        result = self._validate(manifest)
        self.assertIn("topic_review_not_confirmed", self._codes(result))
        self.assertFalse(result["input_valid"])


if __name__ == "__main__":
    unittest.main()
