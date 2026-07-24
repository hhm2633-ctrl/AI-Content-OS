import copy
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.card_news.production_render_request_builder import (
    build_production_render_request,
)
from modules.card_news.selected_candidate_production_package import (
    build_selected_candidate_production_package,
)


class TwoCandidatePreuploadDryRunTests(unittest.TestCase):
    @staticmethod
    def _plan(candidate_id):
        return {
            "schema_version": "selected_candidate_production_plan_v1",
            "status": "production_plan_ready",
            "candidate_id": candidate_id,
            "account": "A",
            "category": "news",
            "title": candidate_id,
            "slide_count": 1,
            "slide_plan": [
                {
                    "slide_role": "cover",
                    "media_type": "image",
                    "asset_refs": ["asset-1"],
                }
            ],
            "copy_plan": {
                "source_credit": ["https://news.example/source"]
            },
                "asset_inventory": [
                {
                    "asset_id": "asset-1",
                    "origin": "news",
                    "asset_class": "source_evidence",
                    "locator": "C:/approved/source.jpg",
                    "source_url": "https://news.example/source",
                    "rights_status": "source_editorial_usable",
                    "topic_relevant": True,
                    "attribution_required": True,
                    "publish_authorized": False,
                    "quality_gate": {
                        "passed": True,
                        "relevant_score": 0.9,
                    },
                }
            ],
        }

    def test_two_selections_stop_at_preupload_owner_gate(self):
        statuses = []
        with tempfile.TemporaryDirectory() as temp:
            owned_asset = Path(temp) / "owned.png"
            Image.new("RGB", (1080, 1440), "white").save(owned_asset)
            for candidate_id in (
                "topic:cluster:0201",
                "topic:cluster:0291",
            ):
                plan = self._plan(candidate_id)
                plan["asset_inventory"] = []
                plan["slide_plan"][0]["media_type"] = "editorial"
                plan["slide_plan"][0]["asset_refs"] = []
                render_input = {
                    "schema_version": "selected_candidate_render_input_v1",
                    "status": "renderer_input_ready",
                    "renderer_ready": True,
                    "render_executed": False,
                    "publish_executed": False,
                    "full_plan_preserved": copy.deepcopy(plan),
                }
                package = build_selected_candidate_production_package(
                    plan,
                    render_input,
                    {
                        "candidate_id": candidate_id,
                        "account": "A",
                        "story": {"summary": "source-backed summary"},
                        "slide_copy": [
                            {
                                "page": 1,
                                "headline": candidate_id,
                                "body": "source-backed body",
                            }
                        ],
                        "feed_caption": "separate feed caption",
                    },
                    {
                        "status": "approved",
                        "scope": "production_package",
                        "candidate_id": candidate_id,
                        "approved_by": "dry-run-production-controller",
                        "receipt_id": f"dry-package-{candidate_id}",
                    },
                )
                render = build_production_render_request(
                    package,
                    {
                        "authorized": True,
                        "authorization_id": f"dry-render-{candidate_id}",
                        "mode": "representative",
                        "input_sha256": "a" * 64,
                        "output_root": (
                            "F:/AI-Content-OS-Data/qa/"
                            "two_candidate_preupload_dry_run"
                        ),
                        "local_media_receipt_hashes": {
                            candidate_id: ["b" * 64]
                        },
                    },
                    owned_asset,
                )
                statuses.append(
                    {
                        "candidate_id": candidate_id,
                        "package_status": package["status"],
                        "package_blocker": package["reason_code"],
                        "render_contract_status": render["status"],
                        "render_executed": False,
                        "owner_approval_required_at": (
                            "pre_upload_manual_upload_ready"
                        ),
                        "manual_upload_ready": False,
                        "exact_blocker": (
                            "dry_run_render_not_executed_and_"
                            "owner_visual_approval_missing"
                        ),
                        "auto_owner_approval": False,
                        "actual_publish": False,
                        "upload_executed": False,
                    }
                )

        self.assertEqual(len(statuses), 2)
        for status in statuses:
            self.assertEqual(
                status["package_status"],
                "production_package_ready",
            )
            self.assertEqual(
                status["package_blocker"], "strict_package_composed"
            )
            self.assertEqual(
                status["render_contract_status"], "ready"
            )
            self.assertFalse(status["render_executed"])
            self.assertEqual(
                status["owner_approval_required_at"],
                "pre_upload_manual_upload_ready",
            )
            self.assertFalse(status["manual_upload_ready"])
            self.assertFalse(status["auto_owner_approval"])
            self.assertFalse(status["actual_publish"])
            self.assertFalse(status["upload_executed"])


if __name__ == "__main__":
    unittest.main()
