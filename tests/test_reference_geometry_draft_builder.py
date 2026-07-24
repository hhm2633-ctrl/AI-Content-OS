import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from modules.design_learning.reference_geometry_draft_builder import (
    build_reference_geometry_draft,
    build_reference_geometry_draft_batch,
    detect_instagram_content_viewport,
)


def receipt(*, boxes=(), lines=(), scores=(), success=True, status="completed"):
    return SimpleNamespace(
        success=success,
        status=status,
        reason="",
        lines=tuple(lines),
        scores=tuple(scores),
        boxes=tuple(boxes),
        polys=(),
        elapsed_seconds=0.01,
        paddleocr_version="fixture",
        paddlepaddle_version="fixture",
        device="cpu",
    )


class ReferenceGeometryDraftBuilderTests(unittest.TestCase):
    def _fixture(self, root: Path, name: str, size=(100, 200)) -> dict:
        batch = root / "owner_source" / "batch_001"
        batch.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", size, "black")
        viewport_height = int(round(size[0] * 5 / 4))
        viewport_top = 30
        for y in range(viewport_top, viewport_top + viewport_height):
            for x in range(size[0]):
                image.putpixel((x, y), (245, 245, 245))
        image.save(batch / name)
        return {
            "reference_id": f"ref-{Path(name).stem}",
            "source_relative_path": f"owner_source/batch_001/{name}",
            "source_claim_ids": ["claim-1"],
            "analysis_record_ids": ["analysis-1"],
            "suggested_blueprint_id": f"bp-{Path(name).stem}",
            "production_selectable": False,
            "reference_only": True,
        }

    def test_ocr_boxes_become_normalized_text_regions_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self._fixture(root, "one.png")

            def fake_ocr(path, **_kwargs):
                if Path(path).parent.name != "crops":
                    return receipt(
                        boxes=((5, 5, 90, 20), (5, 170, 90, 190)),
                        lines=("게시물 원본 오디오", "좋아요 6월 23일"),
                        scores=(0.99, 0.99),
                    )
                return receipt(
                    boxes=((10, 20, 90, 60), (20, 100, 80, 140)),
                    lines=("큰 제목", "본문"),
                    scores=(0.99, 0.95),
                )

            draft = build_reference_geometry_draft(
                candidate,
                source_root=root / "owner_source",
                crop_output_dir=root / "crops",
                ocr_extractor=fake_ocr,
            )
            regions = draft["blueprint_draft"]["regions"]
            self.assertEqual(regions[0]["box_norm"], [0.1, 0.16, 0.8, 0.32])
            self.assertEqual({item["role"] for item in regions}, {"headline", "body"})
            self.assertTrue(draft["geometry_contract_valid"])
            crop_box = draft["viewport_detection"]["crop_box_original_px"]
            self.assertLessEqual(abs(crop_box["y"] - 30), 1)
            self.assertEqual(crop_box["height"], 125)
            self.assertGreaterEqual(draft["viewport_detection"]["confidence"], 0.55)
            self.assertEqual(len(draft["original_sha256"]), 64)
            self.assertEqual(len(draft["crop_sha256"]), 64)
            self.assertTrue(
                all(
                    item["candidate_kind"] == "media_or_background_candidate"
                    and item["production_binding"] is False
                    for item in draft["media_background_candidates"]
                )
            )
            self.assertEqual(draft["status"], "draft_pending_owner_approval")
            self.assertEqual(draft["approval_status"], "draft_unapproved")
            self.assertIsNone(draft["owner_approval_receipt_id"])
            self.assertFalse(draft["production_selectable"])

    def test_crop_ocr_without_boxes_fails_and_never_uses_full_screenshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self._fixture(root, "two.png")
            calls = 0

            def fake_ocr(_path, **_kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    return receipt(
                        boxes=((5, 5, 90, 20), (5, 170, 90, 190)),
                        lines=("게시물 원본 오디오", "좋아요 6월 23일"),
                        scores=(0.99, 0.99),
                    )
                return receipt()

            draft = build_reference_geometry_draft(
                candidate,
                source_root=root / "owner_source",
                crop_output_dir=root / "crops",
                ocr_extractor=fake_ocr,
            )
            self.assertEqual(draft["status"], "draft_failed_crop_geometry")
            self.assertEqual(
                draft["validation_errors"],
                ["crop_ocr_text_regions_unavailable"],
            )
            self.assertFalse(draft["production_selectable"])
            self.assertNotIn("blueprint_draft", draft)

    def test_low_confidence_has_no_full_screenshot_fallback(self):
        image = Image.new("RGB", (100, 200), "white")
        detected = detect_instagram_content_viewport(
            image,
            receipt(),
        )
        self.assertEqual(detected["status"], "failed")
        self.assertEqual(
            detected["reason_code"],
            "viewport_confidence_below_threshold",
        )

    def test_alternate_known_edges_rescue_weak_boundary_without_fallback(self):
        image = Image.new("RGB", (100, 200), (12, 12, 12))
        for y in range(25, 150):
            for x in range(100):
                image.putpixel((x, y), (22, 22, 22))
        detected = detect_instagram_content_viewport(
            image,
            receipt(
                boxes=((5, 5, 55, 20), (5, 155, 70, 175)),
                lines=("게시물 원본 오디오", "좋아요 6월 23일"),
                scores=(0.99, 0.99),
            ),
        )
        self.assertEqual(detected["status"], "detected")
        self.assertLessEqual(abs(detected["crop_box_original_px"]["y"] - 25), 6)
        self.assertTrue(detected["alternate_boundary_candidates"])

    def test_instagram_ui_is_filtered_and_prompt_cannot_be_headline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self._fixture(root, "ui.png")
            calls = 0

            def fake_ocr(_path, **_kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    return receipt(
                        boxes=((5, 5, 90, 20), (5, 170, 90, 190)),
                        lines=("게시물 원본 오디오", "좋아요 6월 23일"),
                        scores=(0.99, 0.99),
                    )
                return receipt(
                    boxes=(
                        (80, 4, 96, 14),
                        (5, 8, 35, 15),
                        (8, 24, 92, 48),
                        (5, 62, 96, 92),
                        (5, 112, 50, 123),
                    ),
                    lines=(
                        "3/6",
                        "MKTG WITH AI",
                        "오늘 바로 시작하는 법",
                        (
                            "A dramatic reference image prompt with cinematic "
                            "lighting and editorial composition"
                        ),
                        "좋아요 23개",
                    ),
                    scores=(0.99, 0.99, 0.99, 0.99, 0.99),
                )

            draft = build_reference_geometry_draft(
                candidate,
                source_root=root / "owner_source",
                crop_output_dir=root / "crops",
                ocr_extractor=fake_ocr,
            )
            self.assertEqual(draft["status"], "draft_pending_owner_approval")
            self.assertEqual(
                draft["ocr_receipt"]["excluded_instagram_ui_region_count"],
                2,
            )
            regions = draft["blueprint_draft"]["regions"]
            headline = next(item for item in regions if item["role"] == "headline")
            self.assertEqual(headline["recognized_text"], "오늘 바로 시작하는 법")
            prompt = next(
                item for item in regions
                if item["recognized_text"].startswith("A dramatic")
            )
            self.assertEqual(prompt["role"], "body")
            self.assertNotIn(
                "3/6",
                {item["recognized_text"] for item in regions},
            )
            self.assertFalse(draft["production_selectable"])

    def test_prompt_only_geometry_has_no_required_headline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self._fixture(root, "prompt.png")
            calls = 0

            def fake_ocr(_path, **_kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    return receipt(
                        boxes=((5, 5, 90, 20), (5, 170, 90, 190)),
                        lines=("게시물 원본 오디오", "좋아요 6월 23일"),
                        scores=(0.99, 0.99),
                    )
                return receipt(
                    boxes=((5, 20, 95, 70),),
                    lines=(
                        "Image prompt reference image cinematic lighting composition",
                    ),
                    scores=(0.99,),
                )

            draft = build_reference_geometry_draft(
                candidate,
                source_root=root / "owner_source",
                crop_output_dir=root / "crops",
                ocr_extractor=fake_ocr,
            )
            self.assertEqual(draft["status"], "draft_failed_crop_geometry")
            self.assertIn(
                "headline_candidate_unavailable_without_prompt_brand_or_ui",
                draft["validation_errors"],
            )
            self.assertFalse(draft["production_selectable"])

    def test_batch_writes_two_drafts_and_nonproduction_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = [
                self._fixture(root, "one.png"),
                self._fixture(root, "two.png"),
            ]
            output = root / "draft_output"
            calls = {}

            def fake_ocr(path, **_kwargs):
                key = str(path)
                calls[key] = calls.get(key, 0) + 1
                if Path(path).parent.name != "crops":
                    return receipt(
                        boxes=((5, 5, 90, 20), (5, 170, 90, 190)),
                        lines=("게시물 원본 오디오", "좋아요 6월 23일"),
                        scores=(0.99, 0.99),
                    )
                return receipt(
                    boxes=((10, 20, 90, 60),),
                    lines=("제목",),
                    scores=(0.99,),
                )

            result = build_reference_geometry_draft_batch(
                {"candidate_evidence": candidates},
                source_root=root / "owner_source",
                output_dir=output,
                ocr_extractor=fake_ocr,
            )
            self.assertEqual(result["generated_count"], 2)
            self.assertEqual(result["failed_count"], 0)
            self.assertFalse(result["production_selectable"])
            self.assertFalse(result["production_registry_written"])
            self.assertFalse(result["full_screenshot_geometry_fallback"])
            self.assertTrue(Path(result["index_path"]).is_file())
            persisted = json.loads(Path(result["index_path"]).read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "draft_pending_owner_approval")
            self.assertIsNone(persisted["owner_approval_receipt_id"])


if __name__ == "__main__":
    unittest.main()
