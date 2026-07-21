import unittest
from unittest.mock import Mock

from modules.media_intelligence.image_operations import LocalMediaImageOperations


class TestLocalMediaImageOperations(unittest.TestCase):
    def setUp(self):
        self.realesrgan = Mock()
        self.rembg = Mock()
        self.operations = LocalMediaImageOperations(
            "F:/AI-Content-OS-Data/external_tools/outputs/image_operations",
            realesrgan=self.realesrgan,
            rembg=self.rembg,
        )

    def request(self, **updates):
        request = {
            "request_id": "operation-001",
            "operation": "upscale",
            "source_path": "C:/synthetic/source.png",
            "output_path": "F:/AI-Content-OS-Data/external_tools/outputs/image_operations/result.png",
            "asset_class": "auxiliary",
            "model": "realesrgan-x4plus",
            "scale": 4,
        }
        request.update(updates)
        return request

    def test_never_infers_missing_operation(self):
        result = self.operations.execute(self.request(operation=None))
        self.assertEqual(result["reason_code"], "OPERATION_REQUIRED")
        self.realesrgan.upscale.assert_not_called()
        self.rembg.cutout.assert_not_called()

    def test_rejects_non_f_output_root(self):
        operations = LocalMediaImageOperations(
            "C:/outputs", realesrgan=self.realesrgan, rembg=self.rembg
        )
        result = operations.execute(self.request())
        self.assertEqual(result["reason_code"], "OUTPUT_ROOT_NOT_F_DRIVE")
        self.realesrgan.upscale.assert_not_called()

    def test_rejects_output_outside_root_and_source_overwrite(self):
        outside = self.operations.execute(self.request(output_path="F:/elsewhere/out.png"))
        self.assertEqual(outside["reason_code"], "OUTPUT_OUTSIDE_APPROVED_ROOT")
        collision = self.operations.execute(
            self.request(
                source_path="F:/AI-Content-OS-Data/external_tools/outputs/image_operations/same.png",
                output_path="F:/AI-Content-OS-Data/external_tools/outputs/image_operations/same.png",
            )
        )
        self.assertEqual(collision["reason_code"], "SOURCE_OVERWRITE_FORBIDDEN")
        self.realesrgan.upscale.assert_not_called()

    def test_rembg_blocks_source_evidence(self):
        result = self.operations.execute(
            self.request(operation="remove_background", asset_class="source_evidence")
        )
        self.assertEqual(result["reason_code"], "REMBG_ASSET_CLASS_BLOCKED")
        self.rembg.cutout.assert_not_called()

    def test_rembg_allows_only_declared_non_evidence_classes_and_labels_derivative(self):
        self.rembg.cutout.return_value = {"status": "completed", "provider": "CPUExecutionProvider"}
        for asset_class in ("auxiliary", "product", "generated"):
            with self.subTest(asset_class=asset_class):
                result = self.operations.execute(
                    self.request(operation="remove_background", asset_class=asset_class)
                )
                self.assertEqual(result["status"], "completed")
                self.assertTrue(result["source"]["preserved"])
                self.assertTrue(result["output"]["is_derivative"])
                self.assertEqual(result["output"]["asset_class"], "auxiliary")
                self.assertFalse(result["source_modified"])

    def test_evidence_upscale_requires_explicit_derivative_permission(self):
        result = self.operations.execute(self.request(asset_class="source_evidence"))
        self.assertEqual(result["reason_code"], "EVIDENCE_DERIVATIVE_APPROVAL_REQUIRED")
        self.realesrgan.upscale.assert_not_called()

    def test_approved_evidence_upscale_receipt_cannot_masquerade_as_original(self):
        self.realesrgan.upscale.return_value = {
            "status": "completed",
            "release": "v0.2.5.0/windows-20220424",
        }
        result = self.operations.execute(
            self.request(
                asset_class="source_evidence",
                derivative_enhancement_allowed=True,
            )
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["output"]["derivative_label"], "DERIVATIVE_UPSCALED")
        self.assertTrue(result["output"]["derivative_of_source_evidence"])
        self.assertTrue(result["output"]["not_original_evidence"])
        self.assertTrue(result["evidence_policy"]["original_evidence_preserved"])
        self.assertFalse(result["source_modified"])

    def test_adapter_failure_is_fail_closed_and_retained(self):
        self.realesrgan.upscale.return_value = {
            "status": "blocked",
            "reason_code": "RUNTIME_TIMEOUT",
        }
        result = self.operations.execute(self.request())
        self.assertEqual(result["reason_code"], "ADAPTER_OPERATION_FAILED")
        self.assertEqual(result["adapter_result"]["reason_code"], "RUNTIME_TIMEOUT")
        self.assertFalse(result["output_created"])


if __name__ == "__main__":
    unittest.main()
