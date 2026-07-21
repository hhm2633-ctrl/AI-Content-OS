import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from modules.card_news.evidence_input_validator import EvidenceInputValidator


class TestEvidenceInputValidator(unittest.TestCase):
    NOW = datetime(2026, 7, 12, 0, 0, tzinfo=timezone.utc)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "assets").mkdir(parents=True)
        self.asset_path = self.root / "assets" / "evidence.png"
        Image.new("RGB", (12, 12), color="white").save(self.asset_path)
        self.validator = EvidenceInputValidator(self.root, max_age_days=30)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _manifest(self):
        return {
            "topic_terms": ["카드뉴스", "근거", "검증"],
            "assets": [{
                "asset_path": "assets/evidence.png",
                "source_url": "https://example.com/original/1",
                "source_name": "Example 공식 자료",
                "captured_at": "2026-07-10T09:00:00+00:00",
                "copyright_status": "licensed",
                "permission_evidence": {
                    "type": "license_url",
                    "reference": "https://example.com/license/1",
                    "review_status": "approved",
                    "reviewed_at": "2026-07-11T09:00:00+00:00",
                    "asset_path": "assets/evidence.png",
                },
                "asset_role": "topic_evidence",
                "topic_terms": ["카드뉴스", "근거", "검증"],
                "topic_relevance_note": "원문과 이미지가 동일한 검증 사례를 설명함.",
                "topic_relevance_review": {
                    "status": "confirmed",
                    "reviewed_by": "content-operator",
                    "reviewed_at": "2026-07-11T10:00:00+00:00",
                },
                "attribution_required": True,
                "attribution_text": "Example 공식 자료",
            }],
        }

    @staticmethod
    def _codes(result):
        return {issue["code"] for issue in result["issues"]}

    def test_valid_input_preserves_provenance_but_keeps_all_publish_gates_closed(self):
        result = self.validator.validate(self._manifest(), self.NOW)

        self.assertTrue(result["input_valid"])
        asset = result["assets"][0]
        self.assertEqual(asset["source_name"], "Example 공식 자료")
        self.assertEqual(asset["captured_at"], "2026-07-10T09:00:00+00:00")
        self.assertEqual(asset["topic_relevance_note"], "원문과 이미지가 동일한 검증 사례를 설명함.")
        self.assertEqual(asset["permission_evidence"]["review_status"], "approved")
        self.assertEqual(asset["source_url_risk"]["status"], "UNKNOWN")
        self.assertTrue(asset["topic_match_candidate"])
        self.assertTrue(asset["topic_relevance_manually_confirmed"])
        self.assertTrue(result["manual_image_required"])
        self.assertFalse(result["publishing_ready"])
        self.assertFalse(result["real_image_gate"]["satisfied"])
        self.assertFalse(result["network_used"])
        self.assertTrue(result["source_verification_pending"])
        self.assertTrue(result["manual_approval_required"])
        self.assertGreaterEqual(len(result["manual_approval_checklist"]), 5)

    def test_source_name_is_required(self):
        manifest = self._manifest()
        manifest["assets"][0]["source_name"] = ""
        result = self.validator.validate(manifest, self.NOW)
        self.assertIn("source_name_missing", self._codes(result))

    def test_arbitrary_permission_string_is_rejected(self):
        manifest = self._manifest()
        manifest["assets"][0]["permission_evidence"] = "trust me"
        result = self.validator.validate(manifest, self.NOW)
        self.assertIn("permission_evidence_invalid", self._codes(result))

    def test_permission_must_be_approved_and_linked_to_same_asset(self):
        manifest = self._manifest()
        permission = manifest["assets"][0]["permission_evidence"]
        permission["review_status"] = "pending"
        permission["asset_path"] = "assets/other.png"
        result = self.validator.validate(manifest, self.NOW)
        self.assertIn("permission_review_not_approved", self._codes(result))
        self.assertIn("permission_asset_mismatch", self._codes(result))

    def test_copyright_status_permission_type_mapping_positive_and_negative(self):
        positive = {
            "owned": "ownership_record",
            "licensed": "license_url",
            "public_domain": "public_domain_record",
            "official_reuse_allowed": "official_reuse_policy",
            "user_supplied_with_permission": "written_permission",
            "permission_granted": "written_permission",
        }
        local_types = {"ownership_record", "written_permission"}
        for copyright_status, permission_type in positive.items():
            with self.subTest(copyright_status=copyright_status, positive=True):
                manifest = self._manifest()
                permission = manifest["assets"][0]["permission_evidence"]
                manifest["assets"][0]["copyright_status"] = copyright_status
                permission["type"] = permission_type
                if permission_type in local_types:
                    permission_file = self.root / "permissions" / f"{copyright_status}.txt"
                    permission_file.parent.mkdir(exist_ok=True)
                    permission_file.write_text("reviewed evidence", encoding="utf-8")
                    permission["reference"] = permission_file.relative_to(self.root).as_posix()
                result = self.validator.validate(manifest, self.NOW)
                self.assertNotIn("permission_type_mismatch", self._codes(result))
                self.assertTrue(result["input_valid"])

            with self.subTest(copyright_status=copyright_status, positive=False):
                manifest = self._manifest()
                manifest["assets"][0]["copyright_status"] = copyright_status
                wrong_type = "public_domain_record" if permission_type != "public_domain_record" else "license_url"
                permission = manifest["assets"][0]["permission_evidence"]
                permission["type"] = wrong_type
                permission["reference"] = "https://example.com/wrong-rights"
                result = self.validator.validate(manifest, self.NOW)
                self.assertIn("permission_type_mismatch", self._codes(result))
                self.assertFalse(result["input_valid"])

    def test_structured_local_permission_reference_must_exist_inside_repository(self):
        manifest = self._manifest()
        permission = manifest["assets"][0]["permission_evidence"]
        permission["type"] = "written_permission"
        permission["reference"] = "permissions/nonexistent.txt"
        result = self.validator.validate(manifest, self.NOW)
        self.assertIn("permission_reference_invalid", self._codes(result))

    def test_text_extension_is_rejected_even_when_file_exists(self):
        text_path = self.root / "assets" / "fake.txt"
        text_path.write_text("not an image", encoding="utf-8")
        manifest = self._manifest()
        manifest["assets"][0]["asset_path"] = "assets/fake.txt"
        manifest["assets"][0]["permission_evidence"]["asset_path"] = "assets/fake.txt"
        result = self.validator.validate(manifest, self.NOW)
        self.assertIn("asset_extension_not_allowed", self._codes(result))

    def test_corrupt_image_with_allowed_extension_is_rejected(self):
        corrupt = self.root / "assets" / "corrupt.png"
        corrupt.write_bytes(b"not a png")
        manifest = self._manifest()
        manifest["assets"][0]["asset_path"] = "assets/corrupt.png"
        manifest["assets"][0]["permission_evidence"]["asset_path"] = "assets/corrupt.png"
        result = self.validator.validate(manifest, self.NOW)
        self.assertIn("asset_image_invalid", self._codes(result))

    def test_credential_localhost_private_and_link_local_urls_are_rejected(self):
        blocked = [
            "https://user:secret@example.com/image",
            "http://localhost/image",
            "http://127.0.0.1/image",
            "http://10.1.2.3/image",
            "http://169.254.10.20/image",
            "http://[::1]/image",
        ]
        for source_url in blocked:
            with self.subTest(source_url=source_url):
                manifest = self._manifest()
                manifest["assets"][0]["source_url"] = source_url
                result = self.validator.validate(manifest, self.NOW)
                self.assertIn("source_url_invalid", self._codes(result))

    def test_credential_urls_are_removed_from_all_returned_provenance(self):
        manifest = self._manifest()
        manifest["assets"][0]["source_url"] = "https://user:secret@example.com/source"
        manifest["assets"][0]["permission_evidence"]["reference"] = (
            "https://key:token@example.com/license"
        )

        result = self.validator.validate(manifest, self.NOW)
        serialized = json.dumps(result, ensure_ascii=False)

        self.assertEqual(result["assets"][0]["source_url"], "")
        self.assertEqual(result["assets"][0]["permission_evidence"]["reference"], "")
        for secret in ("user:secret", "key:token", "secret", "token"):
            self.assertNotIn(secret, serialized)
        self.assertIn("source_url_invalid", self._codes(result))
        self.assertIn("permission_reference_invalid", self._codes(result))

    def test_attribution_required_must_be_explicit_boolean(self):
        for invalid in (None, "true", 1):
            with self.subTest(invalid=invalid):
                manifest = self._manifest()
                manifest["assets"][0]["attribution_required"] = invalid
                result = self.validator.validate(manifest, self.NOW)
                self.assertIn("attribution_required_invalid", self._codes(result))

    def test_keyword_match_without_manual_topic_review_is_not_verified(self):
        manifest = self._manifest()
        manifest["assets"][0]["topic_relevance_review"] = {
            "status": "pending",
            "reviewed_by": "",
            "reviewed_at": "",
        }
        result = self.validator.validate(manifest, self.NOW)
        self.assertTrue(result["assets"][0]["topic_match_candidate"])
        self.assertFalse(result["assets"][0]["topic_relevance_manually_confirmed"])
        self.assertIn("topic_review_not_confirmed", self._codes(result))
        self.assertFalse(result["input_valid"])

    def test_timezone_naive_captured_at_is_rejected(self):
        manifest = self._manifest()
        manifest["assets"][0]["captured_at"] = "2026-07-10T09:00:00"
        result = self.validator.validate(manifest, self.NOW)
        self.assertIn("captured_at_invalid", self._codes(result))

    def test_future_and_timezone_naive_reviewed_at_values_are_rejected(self):
        manifest = self._manifest()
        manifest["assets"][0]["permission_evidence"]["reviewed_at"] = "2026-07-13T00:00:00+00:00"
        manifest["assets"][0]["topic_relevance_review"]["reviewed_at"] = "2026-07-13T00:00:00+00:00"
        result = self.validator.validate(manifest, self.NOW)
        self.assertIn("permission_reviewed_at_future", self._codes(result))
        self.assertIn("topic_reviewed_at_future", self._codes(result))

        manifest = self._manifest()
        manifest["assets"][0]["permission_evidence"]["reviewed_at"] = "2026-07-11T09:00:00"
        manifest["assets"][0]["topic_relevance_review"]["reviewed_at"] = "2026-07-11T10:00:00"
        result = self.validator.validate(manifest, self.NOW)
        self.assertIn("permission_reviewed_at_invalid", self._codes(result))
        self.assertIn("topic_reviewed_at_invalid", self._codes(result))

    def test_hostname_risk_is_unknown_without_dns_and_policy_is_explicit(self):
        result = self.validator.validate(self._manifest(), self.NOW)
        self.assertEqual(result["assets"][0]["source_url_risk"]["status"], "UNKNOWN")
        self.assertFalse(result["hostname_risk_policy"]["dns_resolution_performed"])
        self.assertEqual(result["hostname_risk_policy"]["hostname_status_without_dns"], "UNKNOWN")

    def test_stale_topic_mismatch_missing_file_attribution_and_path_escape_remain_blocked(self):
        cases = [
            ("evidence_stale", {"captured_at": "2026-05-01T00:00:00+00:00"}),
            ("topic_mismatch", {"topic_terms": ["여행", "숙소"]}),
            ("asset_file_missing", {"asset_path": "assets/missing.png"}),
            ("attribution_missing", {"attribution_text": ""}),
            ("asset_path_outside_repository", {"asset_path": "../outside.png"}),
        ]
        for expected, changes in cases:
            with self.subTest(expected=expected):
                manifest = self._manifest()
                manifest["assets"][0].update(changes)
                if "asset_path" in changes:
                    manifest["assets"][0]["permission_evidence"]["asset_path"] = changes["asset_path"]
                result = self.validator.validate(manifest, self.NOW)
                self.assertIn(expected, self._codes(result))
                self.assertTrue(result["manual_image_required"])
                self.assertFalse(result["publishing_ready"])


if __name__ == "__main__":
    unittest.main()
