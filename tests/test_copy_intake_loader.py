import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.compliance.copy_intake_loader import load_verified_copy_intake
from tests._temp_cleanup import remove_temp_tree_with_retry

WORKSPACE_TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp_test_workspace"

_VALID_HASH = "a" * 64


def _now_iso(offset_seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def _make_slide(index, role, headline="headline text", body="body text", image_sha256=None,
                 cta_type="", cta_label=""):
    return {
        "slide_index": index,
        "role": role,
        "headline": headline,
        "body": body,
        "image_sha256": image_sha256 or _VALID_HASH,
        "cta_type": cta_type,
        "cta_label": cta_label,
    }


def _valid_slides():
    return [
        _make_slide(1, "hook"),
        _make_slide(2, "problem"),
        _make_slide(3, "solution"),
        _make_slide(4, "cta", cta_type="save", cta_label="SAVE"),
    ]


def _valid_payload(content_id="CN-TEST"):
    return {
        "content_id": content_id,
        "title": "A genuine title",
        "operator_id": "operator_01",
        "approved_at": _now_iso(-10),
        "slides": _valid_slides(),
    }


class CopyIntakeLoaderTests(unittest.TestCase):
    def setUp(self):
        self.previous_cwd = Path.cwd()
        WORKSPACE_TMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=WORKSPACE_TMP_ROOT))
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self.previous_cwd)
        remove_temp_tree_with_retry(self.root)

    def _write(self, content_id, payload):
        path = Path("storage/copy_intake") / f"{content_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_accepts_a_fully_valid_contract(self):
        self._write("CN-TEST", _valid_payload())
        result = load_verified_copy_intake("CN-TEST")
        self.assertIsNotNone(result)
        self.assertEqual(result["content_id"], "CN-TEST")
        self.assertEqual(result["title"], "A genuine title")
        self.assertEqual(set(result["slides"]), {1, 2, 3, 4})
        self.assertEqual(result["slides"][4]["cta_type"], "save")

    def test_missing_file_returns_none(self):
        self.assertIsNone(load_verified_copy_intake("CN-DOES-NOT-EXIST"))

    def test_empty_content_id_returns_none(self):
        self.assertIsNone(load_verified_copy_intake(""))
        self.assertIsNone(load_verified_copy_intake(None))

    def test_path_traversal_content_id_returns_none(self):
        # A content_id containing path-separator characters must never be
        # used to build a filesystem path outside storage/copy_intake/.
        self.assertIsNone(load_verified_copy_intake("../../etc/passwd"))
        self.assertIsNone(load_verified_copy_intake("CN-006/../secret"))

    def test_content_id_field_mismatch_returns_none(self):
        payload = _valid_payload(content_id="OTHER-ID")
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_placeholder_title_returns_none(self):
        payload = _valid_payload()
        payload["title"] = "PLACEHOLDER"
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_placeholder_operator_id_returns_none(self):
        payload = _valid_payload()
        payload["operator_id"] = "TODO"
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_missing_approved_at_returns_none(self):
        payload = _valid_payload()
        del payload["approved_at"]
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_future_approved_at_returns_none(self):
        payload = _valid_payload()
        payload["approved_at"] = _now_iso(60 * 60 * 24)
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_naive_approved_at_returns_none(self):
        payload = _valid_payload()
        payload["approved_at"] = datetime.now().isoformat()  # no tz
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_wrong_slide_count_returns_none(self):
        payload = _valid_payload()
        payload["slides"] = _valid_slides()[:1]
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_wrong_slide_count_too_many_returns_none(self):
        payload = _valid_payload()
        payload["slides"] = [
            _make_slide(index, f"role-{index}") for index in range(1, 22)
        ]
        payload["slides"][-1]["cta_type"] = "save"
        payload["slides"][-1]["cta_label"] = "SAVE"
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_duplicate_slide_index_returns_none(self):
        payload = _valid_payload()
        slides = _valid_slides()
        slides[3]["slide_index"] = 3  # duplicate of slide 3, index 4 missing
        payload["slides"] = slides
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_missing_or_placeholder_role_returns_none(self):
        payload = _valid_payload()
        slides = _valid_slides()
        slides[1]["role"] = ""
        payload["slides"] = slides
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

        payload = _valid_payload()
        slides = _valid_slides()
        slides[1]["role"] = "TODO"
        payload["slides"] = slides
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_placeholder_headline_returns_none(self):
        payload = _valid_payload()
        slides = _valid_slides()
        slides[0]["headline"] = "TBD"
        payload["slides"] = slides
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_placeholder_body_returns_none(self):
        payload = _valid_payload()
        slides = _valid_slides()
        slides[0]["body"] = ""
        payload["slides"] = slides
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_malformed_sha256_returns_none(self):
        payload = _valid_payload()
        slides = _valid_slides()
        slides[0]["image_sha256"] = "not-a-hash"
        payload["slides"] = slides
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_uppercase_sha256_is_normalized_to_lowercase(self):
        # Uppercase hex is the same hash value, just different casing; the
        # loader normalizes rather than rejecting it.
        payload = _valid_payload()
        slides = _valid_slides()
        slides[0]["image_sha256"] = _VALID_HASH.upper()
        payload["slides"] = slides
        self._write("CN-TEST", payload)
        result = load_verified_copy_intake("CN-TEST")
        self.assertIsNotNone(result)
        self.assertEqual(result["slides"][1]["image_sha256"], _VALID_HASH)

    def test_cta_slide_missing_cta_type_returns_none(self):
        payload = _valid_payload()
        slides = _valid_slides()
        slides[3]["cta_type"] = ""
        payload["slides"] = slides
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_non_cta_slide_with_cta_fields_returns_none(self):
        payload = _valid_payload()
        slides = _valid_slides()
        slides[0]["cta_type"] = "save"
        payload["slides"] = slides
        self._write("CN-TEST", payload)
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_corrupt_json_returns_none(self):
        path = Path("storage/copy_intake/CN-TEST.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not valid json", encoding="utf-8")
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_non_object_json_returns_none(self):
        path = Path("storage/copy_intake/CN-TEST.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        self.assertIsNone(load_verified_copy_intake("CN-TEST"))

    def test_real_cn_006_contract_is_valid_shape(self):
        """Sanity-check the actual repo fixture this task installs at
        storage/copy_intake/CN-006.json against the loader's own rules,
        using a private copy so this test never depends on repo cwd."""
        real_path = self.previous_cwd / "storage/copy_intake/CN-006.json"
        payload = json.loads(real_path.read_text(encoding="utf-8"))
        self._write("CN-006", payload)
        result = load_verified_copy_intake("CN-006")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "미니멀리즘 시작하는 법")
        self.assertEqual(
            result["slides"][1]["image_sha256"],
            "7c89e197ad0b03711dd381c58b8ec38aee9e27d5fbcbf22861130d0749aec79b",
        )
        self.assertEqual(result["slides"][4]["cta_label"], "SAVE 저장하기")


if __name__ == "__main__":
    unittest.main()
