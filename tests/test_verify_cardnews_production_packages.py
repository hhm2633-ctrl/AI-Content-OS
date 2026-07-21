import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_cardnews_production_packages import verify_package_index


def _package(candidate_id, status="production_package_ready"):
    value = {
        "schema_version": "selected_candidate_production_package_v1",
        "status": status,
        "reason_code": "strict_package_composed" if status != "blocked" else "handoff_missing",
        "candidate": {"candidate_id": candidate_id, "account": "A"},
        "story": {"summary": "스토리"} if status != "blocked" else {},
        "slides": [{"page": 1, "headline": "첫 장"}] if status != "blocked" else [],
        "feed_caption": "별도 본문" if status != "blocked" else "",
        "media_plan": [{"page": 1, "media_type": "editorial"}] if status != "blocked" else [],
        "quality_receipt": {
            "schema_version": "cardnews_package_content_quality_gate_v1",
            "quality_passed": status != "blocked",
        },
        "gates": {
            "render": {"status": "blocked", "authorized": False},
            "publish": {"status": "blocked", "authorized": False},
        },
        "receipts": {
            "package_only": True,
            "render_executed": False,
            "publish_executed": False,
            "link_issuance_executed": False,
        },
    }
    return value


class VerifyCardNewsProductionPackagesTests(unittest.TestCase):
    def _write_index(self, root, packages):
        entries = []
        ready = 0
        for package in packages:
            candidate_id = package["candidate"]["candidate_id"]
            (root / f"{candidate_id}.json").write_text(
                json.dumps(package, ensure_ascii=False), encoding="utf-8"
            )
            entries.append({"candidate_id": candidate_id, "status": package["status"]})
            ready += package["status"] == "production_package_ready"
        index = {
            "schema_version": "cardnews_production_package_index_v1",
            "package_count": len(entries),
            "ready_count": ready,
            "blocked_count": len(entries) - ready,
            "packages": entries,
            "render_executed": False,
            "publish_executed": False,
            "link_issuance_executed": False,
        }
        path = root / "latest.json"
        path.write_text(json.dumps(index), encoding="utf-8")
        return path

    def test_passes_read_only_ready_and_blocked_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = self._write_index(root, [_package("A-1"), _package("A-2", "blocked")])

            receipt = verify_package_index(index)

            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(receipt["checked_count"], 2)
            self.assertTrue(receipt["package_only"])
            self.assertTrue(all(value is False for value in receipt["execution"].values()))

    def test_fails_closed_when_render_was_authorized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = _package("A-1")
            package["gates"]["render"] = {"status": "approved", "authorized": True}
            index = self._write_index(root, [package])

            receipt = verify_package_index(index)

            self.assertEqual(receipt["status"], "failed")
            self.assertIn("A-1:render_gate_not_blocked", receipt["errors"])

    def test_fails_closed_when_ready_content_is_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = _package("A-1")
            package["feed_caption"] = ""
            index = self._write_index(root, [package])

            receipt = verify_package_index(index)

            self.assertEqual(receipt["status"], "failed")
            self.assertIn("A-1:ready_feed_caption_missing", receipt["errors"])


if __name__ == "__main__":
    unittest.main()
