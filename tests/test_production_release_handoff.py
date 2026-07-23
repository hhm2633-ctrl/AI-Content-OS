import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.card_news.production_release_handoff import build_production_release_handoff
from scripts.build_cardnews_render_request import resolve_owned_asset


class ProductionReleaseHandoffTests(unittest.TestCase):
    def test_package_asset_is_automatic_and_explicit_path_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            automatic = root / "automatic.png"
            override = root / "override.png"
            Image.new("RGB", (10, 10)).save(automatic)
            Image.new("RGB", (10, 10)).save(override)
            package = {
                "slides": [{
                    "visual_spec": {
                        "source_media_candidate": {
                            "local_path": str(automatic),
                            "rights_status": "owner_approved",
                            "render_allowed": True,
                        }
                    }
                }]
            }
            self.assertEqual(resolve_owned_asset(package), automatic)
            self.assertEqual(resolve_owned_asset(package, override), override)

    def test_owner_approved_controller_builds_manual_only_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "page-001.png"
            Image.new("RGB", (1080, 1350)).save(image)
            state = {
                "state": "manual_upload_ready",
                "manual_upload_ready": True,
                "controller_id": "controller-1",
                "state_hash": "a" * 64,
                "accounts": ["A"],
                "candidate_ids": ["candidate-a"],
                "representative_qa_receipt_ids": {"A": "qa-representative-a"},
                "batch_qa_receipt_hashes": {"candidate-a": "b" * 64},
            }
            attribution = [{"asset_id": "asset-1", "attribution_text": "Photographer"}]
            manifest = {
                "output_set_id": "output-1",
                "records": [{
                    "status": "render_completed_pending_visual_qa",
                    "candidate_id": "candidate-a",
                    "outputs": [str(image)],
                    "rendered_asset_ids": ["asset-1"],
                    "attribution_receipt": attribution,
                }],
            }
            packages = [{
                "candidate": {"candidate_id": "candidate-a", "title": "Title"},
                "evidence": {"assets": [{
                    "asset_id": "asset-1",
                    "rights_status": "owner_approved",
                    "render_allowed": True,
                    "source_url": "https://example.com/source",
                }]},
            }]
            result = build_production_release_handoff(state, manifest, packages)
            self.assertEqual(result["status"], "ready_for_publishing_module")
            self.assertFalse(result["actual_publish"])
            self.assertFalse(result["upload_executed"])
            attestation = result["pre_publish_attestation"]
            self.assertEqual(attestation["rendered_asset_ids"], ["asset-1"])
            self.assertEqual(attestation["render_allowed_asset_ids"], ["asset-1"])
            self.assertEqual(attestation["attribution_receipt"], attribution)

    def test_missing_owner_visual_approval_remains_blocked(self):
        result = build_production_release_handoff(
            {"state": "manual_upload_ready", "manual_upload_ready": True},
            {"output_set_id": "output-1"},
            [],
        )
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["actual_publish"])


if __name__ == "__main__":
    unittest.main()
