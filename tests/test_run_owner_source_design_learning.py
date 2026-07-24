import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_owner_source_design_learning import (
    audit_existing_reference_v2,
    draft_existing_reference_v2_geometry,
)


class RunOwnerSourceDesignLearningTests(unittest.TestCase):
    def test_read_only_audit_reports_blocker_and_no_external_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "owner_source"
            (source / "batch_001").mkdir(parents=True)
            (source / "batch_001" / "reference.jpg").write_bytes(b"fixture")
            analysis = root / "analysis.json"
            analysis.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_no": 1,
                                "design_learning": "candidate layout",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            taxonomy = root / "taxonomy.json"
            taxonomy.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "learning_id": "claim:1",
                                "source_file": "analysis.json",
                                "source_item_id": "item_0001",
                                "accounts": ["news"],
                                "formats": ["card_news"],
                                "learning_layers": ["layout"],
                                "owner_confirmed": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = audit_existing_reference_v2(
                source_dir=source,
                taxonomy_path=taxonomy,
                repository_root=root,
            )
            self.assertEqual(
                result["status"],
                "blocked_no_production_selectable_reference",
            )
            self.assertEqual(
                result["intermediate_artifact"]["status"],
                "automatically_generatable",
            )
            self.assertFalse(result["intermediate_artifact"]["production_registry"])
            self.assertFalse(result["external_write_performed"])
            self.assertEqual(result["selectable_reference_ids"], [])

    def test_geometry_draft_runner_consumes_candidate_json_without_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "owner_source"
            batch = source / "batch_001"
            batch.mkdir(parents=True)
            from PIL import Image

            image = Image.new("RGB", (100, 200), "black")
            for y in range(30, 155):
                for x in range(100):
                    image.putpixel((x, y), (245, 245, 245))
            image.save(batch / "reference.png")
            evidence = root / "candidate.json"
            evidence.write_text(
                json.dumps(
                    {
                        "candidate_evidence": [
                            {
                                "reference_id": "ref-1",
                                "source_relative_path": (
                                    "owner_source/batch_001/reference.png"
                                ),
                                "production_selectable": False,
                                "reference_only": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            from unittest.mock import patch

            fake_receipt = type(
                "Receipt",
                (),
                {
                    "success": True,
                    "status": "completed",
                    "reason": "",
                    "lines": ("제목",),
                    "scores": (0.99,),
                    "boxes": ((10, 10, 90, 40),),
                    "polys": (),
                    "elapsed_seconds": 0.01,
                    "paddleocr_version": "fixture",
                    "paddlepaddle_version": "fixture",
                    "device": "cpu",
                },
            )()
            with patch(
                "modules.design_learning.reference_geometry_draft_builder.extract_korean_text",
                return_value=fake_receipt,
            ):
                result = draft_existing_reference_v2_geometry(
                    candidate_evidence_path=evidence,
                    source_dir=source,
                    output_dir=root / "output",
                    ocr_extractor=lambda path, **_kwargs: (
                        fake_receipt
                        if Path(path).parent.name == "crops"
                        else type(
                            "Receipt",
                            (),
                            {
                                "success": True,
                                "status": "completed",
                                "reason": "",
                                "lines": (
                                    "게시물 원본 오디오",
                                    "좋아요 6월 23일",
                                ),
                                "scores": (0.99, 0.99),
                                "boxes": (
                                    (5, 5, 90, 20),
                                    (5, 170, 90, 190),
                                ),
                                "polys": (),
                                "elapsed_seconds": 0.01,
                                "paddleocr_version": "fixture",
                                "paddlepaddle_version": "fixture",
                                "device": "cpu",
                            },
                        )()
                    ),
                )
            self.assertEqual(result["generated_count"], 1)
            self.assertEqual(result["failed_count"], 0)
            self.assertFalse(result["production_selectable"])
            self.assertFalse(result["full_screenshot_geometry_fallback"])
            self.assertIsNone(result["owner_approval_receipt_id"])


if __name__ == "__main__":
    unittest.main()
