import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.publishing.publishing_module import _valid_card_png_set
from modules.publishing.publishing_module import PublishingModule


class PublishingImageGateTest(unittest.TestCase):
    def _run(self, image_sourcing_status):
        with patch.object(Path, "mkdir"):
            module = PublishingModule()
        with patch.object(module, "_save_json"), patch.object(module, "_save_text"):
            result = module.run(
                {
                    "title": "테스트 카드뉴스",
                    "cards": [{"card_path": "storage/card_news/card_news_1.png"}],
                    "image_sourcing_status": image_sourcing_status,
                }
            )
        return result, module

    def test_manual_image_requirement_blocks_publishing_without_leaking_into_caption(self):
        result, _ = self._run(
            {
                "manual_image_required": True,
                "real_image_used_count": 0,
                "checklist": ["실제 이미지 반영"],
            }
        )

        self.assertEqual(result["status"], "publishing_blocked")
        self.assertTrue(result["operations"]["publishing_blocked"])
        self.assertEqual(
            result["operations"]["blocking_reasons"],
            ["manual_image_required", "real_image_used_count_zero"],
        )
        self.assertNotIn("manual_image_required", result["caption"])
        self.assertEqual(result["upload_mode"], "manual")

    def test_zero_real_images_blocks_even_without_manual_flag(self):
        result, _ = self._run(
            {"manual_image_required": False, "real_image_used_count": 0, "checklist": []}
        )

        self.assertEqual(result["status"], "publishing_blocked")
        self.assertEqual(result["operations"]["blocking_reasons"], ["real_image_used_count_zero"])

    def test_blocked_queue_is_not_ready_for_manual_upload(self):
        with patch.object(Path, "mkdir"):
            module = PublishingModule()
        image_status = {
            "manual_image_required": True,
            "real_image_used_count": 0,
            "checklist": ["실제 이미지 반영"],
        }
        operations = module._resolve_publishing_gate(image_status)

        queue = module._create_publish_queue(
            title="테스트",
            card_paths=["card.png"],
            caption="공개 캡션",
            hashtags=["#테스트"],
            image_sourcing_status=image_status,
            operations=operations,
        )

        self.assertEqual(queue["status"], "queue_blocked")
        self.assertEqual(queue["items"][0]["status"], "blocked_pending_image_sourcing")
        self.assertEqual(queue["items"][0]["caption"], "공개 캡션")

    def test_real_image_allows_existing_ready_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            card_paths = []
            for index in range(1, 5):
                path = Path(temp_dir) / f"card_news_{index}.png"
                Image.new("RGB", (1080, 1080), color=(index * 20, 30, 40)).save(path)
                card_paths.append(str(path))

            output_set_id = "publishing-image-gate-001"
            payload = {
                "title": "테스트 카드뉴스",
                "output_set_id": output_set_id,
                "cards": [
                    {"index": index, "card_path": path}
                    for index, path in enumerate(card_paths, start=1)
                ],
                "image_sourcing_status": {
                    "manual_image_required": False,
                    "real_image_used_count": 4,
                    "checklist": [],
                },
                "pre_publish_attestation": {
                    "schema_version": 1,
                    "contract": "card_news_pre_publish_attestation_v1",
                    "output_set_id": output_set_id,
                    "cards": [
                        {"index": index, "path": path, "exists": True}
                        for index, path in enumerate(card_paths, start=1)
                    ],
                    "quality": {"passed": True},
                    "rights": {"status": "pass", "ready": True},
                    "evidence": {"status": "applied", "available": True, "applied": True},
                    "compliance_result": {
                        "schema_version": "card_news_compliance.v1",
                        "package_id": "compliance-image-gate-001",
                        "status": "valid",
                        "publish_ready": True,
                        "blocking_reasons": [],
                    },
                    "provenance": {
                        "source": "CardNewsPublishGate",
                        "result_id": "compliance-image-gate-001",
                    },
                    "technical_fixture_not_publish_approved": False,
                    "release_guard": {"ready": True, "issue_codes": []},
                },
            }
            with patch.object(Path, "mkdir"):
                module = PublishingModule()
            with patch.object(module, "_save_json"), patch.object(module, "_save_text"):
                result = module.run(payload)

        self.assertEqual(result["status"], "publishing_ready")
        self.assertFalse(result["operations"]["publishing_blocked"])
        self.assertEqual(result["upload_mode"], "manual")
        self.assertTrue(result["package_ready"])
        self.assertFalse(result["actual_publish"])

    def test_card_png_set_accepts_allowed_canvas_sizes_and_rejects_arbitrary_size(self):
        for size in ((1080, 1080), (1080, 1440)):
            with self.subTest(size=size):
                with tempfile.TemporaryDirectory() as temp_dir:
                    paths = []
                    for index in range(1, 5):
                        path = Path(temp_dir) / f"card_news_{index}.png"
                        Image.new("RGB", size, color=(index * 20, 30, 40)).save(path)
                        paths.append(str(path))
                    self.assertTrue(_valid_card_png_set(paths))

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = []
            for index in range(1, 5):
                path = Path(temp_dir) / f"card_news_{index}.png"
                Image.new("RGB", (800, 800), color=(index * 20, 30, 40)).save(path)
                paths.append(str(path))
            self.assertFalse(_valid_card_png_set(paths))


if __name__ == "__main__":
    unittest.main()
