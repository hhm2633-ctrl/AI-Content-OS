import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from modules.media_intelligence.local_media_pipeline import (
    LocalMediaPipeline,
    prepare_local_media,
)


F_OUTPUT_ROOT = "F:/AI-Content-OS-Data/external_tools/outputs/local_media_pipeline"


class TestLocalMediaPipeline(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.source = Path(self.temporary_directory.name).resolve() / "owner.png"
        self.source.write_bytes(b"stable-owner-asset")
        self.ocr = Mock(
            return_value={
                "status": "completed",
                "success": True,
                "input_unchanged": True,
                "text": "안녕하세요",
                "lines": ["안녕하세요"],
                "scores": [0.99],
                "elapsed_seconds": 9.99,
            }
        )
        self.openclip = Mock()
        self.openclip.score_image_topics.return_value = {
            "status": "passed",
            "passed": True,
            "score_semantics": "internal_semantic_relevance_proxy",
            "ranked_topics": [{"topic": "향수", "cosine_similarity": 0.4}],
        }
        self.scene_detector = Mock(
            return_value={"status": "completed", "scenes": [], "errors": []}
        )
        self.image_operations = Mock()
        self.image_operations_factory = Mock(return_value=self.image_operations)
        self.pipeline = LocalMediaPipeline(
            image_operations_factory=self.image_operations_factory,
            ocr_extractor=self.ocr,
            openclip=self.openclip,
            scene_detector=self.scene_detector,
        )

    def request(self, **updates):
        request = {
            "request_id": "prepare-001",
            "asset_id": "asset-001",
            "owner_selected": True,
            "rights_cleared": True,
            "source_path": str(self.source),
            "output_root": F_OUTPUT_ROOT,
            "media_type": "image",
            "asset_class": "auxiliary",
            "operations": [{"operation": "ocr"}],
            "execute": True,
            "validate_only": False,
        }
        request.update(updates)
        return request

    def assert_no_tools_called(self):
        self.ocr.assert_not_called()
        self.openclip.score_image_topics.assert_not_called()
        self.scene_detector.assert_not_called()
        self.image_operations.execute.assert_not_called()

    def test_requires_explicit_owner_selection_and_rights_clearance(self):
        not_selected = self.pipeline.prepare(self.request(owner_selected=False))
        self.assertEqual(not_selected["reason_code"], "OWNER_SELECTION_REQUIRED")
        not_cleared = self.pipeline.prepare(self.request(rights_cleared=False))
        self.assertEqual(not_cleared["reason_code"], "RIGHTS_CLEARANCE_REQUIRED")
        self.assert_no_tools_called()

    def test_source_editorial_contract_allows_preparation_without_rights_cleared(self):
        result = self.pipeline.prepare(
            self.request(
                rights_cleared=False,
                source_editorial_usable=True,
                topic_relevant=True,
                attribution_required=True,
                source_url="https://news.example.com/source-story",
                publish_authorized=False,
                operations=[{"operation": "preserve_original"}],
            )
        )

        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["rights_cleared"])
        self.assertTrue(result["source_editorial_usable"])
        self.assertTrue(result["topic_relevant"])
        self.assertTrue(result["attribution_required"])
        self.assertEqual(result["source_url"], "https://news.example.com/source-story")
        self.assertFalse(result["publish_authorized"])

    def test_source_editorial_contract_blocks_each_missing_condition(self):
        valid = {
            "rights_cleared": False,
            "source_editorial_usable": True,
            "topic_relevant": True,
            "attribution_required": True,
            "source_url": "https://news.example.com/source-story",
            "publish_authorized": False,
            "operations": [{"operation": "preserve_original"}],
        }
        invalid_values = {
            "source_editorial_usable": False,
            "topic_relevant": False,
            "attribution_required": False,
            "source_url": "",
            "publish_authorized": True,
        }

        for field, invalid in invalid_values.items():
            with self.subTest(field=field):
                result = self.pipeline.prepare(self.request(**{**valid, field: invalid}))
                self.assertEqual(result["reason_code"], "RIGHTS_CLEARANCE_REQUIRED")

    def test_validate_only_fingerprints_but_never_calls_an_adapter(self):
        result = self.pipeline.prepare(
            self.request(execute=False, validate_only=True)
        )
        self.assertEqual(result["status"], "validated")
        self.assertFalse(result["tools_executed"])
        self.assertFalse(result["pre_render_prepared"])
        self.assertEqual(result["source"]["bytes"], self.source.stat().st_size)
        self.assertEqual(result["operations"][0]["status"], "not_executed")
        self.assert_no_tools_called()

    def test_missing_or_contradictory_execution_mode_fails_closed(self):
        for execute, validate_only in ((None, None), (True, True), (False, False)):
            with self.subTest(execute=execute, validate_only=validate_only):
                request = self.request()
                if execute is None:
                    request.pop("execute")
                    request.pop("validate_only")
                else:
                    request["execute"] = execute
                    request["validate_only"] = validate_only
                result = self.pipeline.prepare(request)
                self.assertEqual(result["reason_code"], "EXECUTION_MODE_REQUIRED")
        self.assert_no_tools_called()

    def test_requires_explicit_absolute_f_output_root(self):
        for root in (None, "outputs", "C:/outputs"):
            with self.subTest(root=root):
                result = self.pipeline.prepare(self.request(output_root=root))
                self.assertEqual(result["reason_code"], "OUTPUT_ROOT_NOT_ABSOLUTE_F_DRIVE")
        self.assert_no_tools_called()

    def test_blocks_source_overwrite_before_any_tool_runs(self):
        result = self.pipeline.prepare(
            self.request(
                operations=[
                    {
                        "operation": "upscale",
                        "output_path": str(self.source),
                        "asset_class": "auxiliary",
                    }
                ]
            )
        )
        self.assertEqual(result["reason_code"], "SOURCE_OVERWRITE_FORBIDDEN")
        self.assert_no_tools_called()

    def test_unsupported_operation_is_blocked_without_partial_execution(self):
        result = self.pipeline.prepare(
            self.request(
                operations=[
                    {"operation": "ocr"},
                    {"operation": "invent_missing_media"},
                ]
            )
        )
        self.assertEqual(result["reason_code"], "OPERATION_NOT_SUPPORTED")
        self.assert_no_tools_called()

    def test_tool_failure_and_exception_fail_closed(self):
        self.ocr.return_value = {
            "status": "failed",
            "success": False,
            "input_unchanged": True,
            "reason": "runtime_not_ready",
        }
        failed = self.pipeline.prepare(self.request())
        self.assertEqual(failed["reason_code"], "TOOL_OPERATION_FAILED")
        self.assertFalse(failed["pre_render_prepared"])

        self.ocr.reset_mock()
        self.ocr.side_effect = RuntimeError("runtime exploded")
        raised = self.pipeline.prepare(self.request())
        self.assertEqual(raised["reason_code"], "TOOL_OPERATION_FAILED")
        self.assertEqual(raised["operations"][0]["reason_code"], "TOOL_EXCEPTION")

    def test_analysis_results_are_never_truth_rights_or_performance_evidence(self):
        result = self.pipeline.prepare(
            self.request(
                operations=[
                    {"operation": "ocr"},
                    {"operation": "openclip_topic_score", "topics": ["향수"]},
                ]
            )
        )
        self.assertEqual(result["status"], "completed")
        for boundary in [result["analysis_boundary"]] + [
            operation["analysis_boundary"] for operation in result["operations"]
        ]:
            self.assertEqual(boundary["classification"], "internal_analysis_only")
            self.assertFalse(boundary["source_truth"])
            self.assertFalse(boundary["rights_evidence"])
            self.assertFalse(boundary["performance_evidence"])

    def test_explicit_preserve_original_prepares_image_without_tool_subprocess(self):
        result = self.pipeline.prepare(
            self.request(operations=[{"operation": "preserve_original"}])
        )

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["pre_render_prepared"])
        self.assertFalse(result["tools_executed"])
        self.assertFalse(result["implicit_execution"])
        self.assertFalse(result["source_modified"])
        self.assertTrue(result["source"]["preserved"])
        self.assertEqual(result["operations"][0]["operation"], "preserve_original")
        self.assertFalse(result["operations"][0]["result"]["tool_subprocess_executed"])
        self.assert_no_tools_called()

    def test_preserve_original_supports_video_but_cannot_mix_with_tools(self):
        video = Path(self.temporary_directory.name).resolve() / "owner.mp4"
        video.write_bytes(b"stable-owner-video")
        preserved = self.pipeline.prepare(
            self.request(
                source_path=str(video),
                media_type="video",
                operations=[{"operation": "preserve_original"}],
            )
        )
        self.assertEqual(preserved["status"], "completed")
        self.assertFalse(preserved["tools_executed"])

        mixed = self.pipeline.prepare(
            self.request(
                operations=[{"operation": "preserve_original"}, {"operation": "ocr"}]
            )
        )
        self.assertEqual(mixed["reason_code"], "PRESERVE_ORIGINAL_MUST_BE_SOLE_OPERATION")
        self.assert_no_tools_called()

    def test_derivative_operation_cannot_replace_source_evidence(self):
        output_path = f"{F_OUTPUT_ROOT}/asset-001-upscaled.png"
        self.image_operations.execute.return_value = {
            "status": "completed",
            "source_modified": False,
            "output": {
                "path": output_path,
                "asset_class": "auxiliary",
                "is_derivative": True,
                "derivative_of_source_evidence": True,
                "not_original_evidence": True,
            },
        }
        result = self.pipeline.prepare(
            self.request(
                asset_class="source_evidence",
                operations=[
                    {
                        "operation": "upscale",
                        "output_path": output_path,
                        "asset_class": "source_evidence",
                        "derivative_enhancement_allowed": True,
                    }
                ],
            )
        )
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["derivative_policy"]["derivatives_replace_source_evidence"])
        forwarded = self.image_operations.execute.call_args.args[0]
        self.assertTrue(forwarded["derivative_enhancement_allowed"])
        self.assertNotEqual(forwarded["source_path"], forwarded["output_path"])

    def test_receipt_schema_and_hash_are_deterministic(self):
        first = self.pipeline.prepare(self.request())
        self.ocr.return_value["elapsed_seconds"] = 0.001
        second = self.pipeline.prepare(self.request())
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "local_media_pre_render_receipt.v1")
        supplied_hash = first.pop("receipt_hash")
        canonical = json.dumps(
            first, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(supplied_hash, hashlib.sha256(canonical).hexdigest())

    def test_public_wrapper_applies_config_and_injected_dependencies(self):
        dependencies = {
            "image_operations_factory": self.image_operations_factory,
            "ocr_extractor": self.ocr,
            "openclip": self.openclip,
            "scene_detector": self.scene_detector,
        }
        pipeline = Mock()
        pipeline.prepare.return_value = {"status": "validated"}
        with patch(
            "modules.media_intelligence.local_media_pipeline.LocalMediaPipeline",
            return_value=pipeline,
        ) as pipeline_class:
            result = prepare_local_media(
                self.request(output_root="F:/request-root"),
                config={"output_root": F_OUTPUT_ROOT},
                dependencies=dependencies,
            )
        pipeline_class.assert_called_once_with(**dependencies)
        forwarded = pipeline.prepare.call_args.args[0]
        self.assertEqual(forwarded["output_root"], F_OUTPUT_ROOT)
        self.assertEqual(result, {"status": "validated"})


if __name__ == "__main__":
    unittest.main()
