from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from modules.tool_adapters.paddleocr_runtime import (
    MODEL_REQUIRED_FILES,
    PADDLEOCR_MODEL_ROOT_ENV,
    PADDLEOCR_RUNTIME_ROOT_ENV,
    TEXT_DETECTION_MODEL_NAME,
    TEXT_RECOGNITION_MODEL_NAME,
    extract_korean_text,
    resolve_paddleocr_runtime,
)


class PaddleOCRRuntimeTests(unittest.TestCase):
    def _distribution(self, root: Path, name: str, version: str) -> None:
        dist = root / "Lib" / "site-packages" / f"{name}-{version}.dist-info"
        dist.mkdir(parents=True)
        (dist / "METADATA").write_text(
            f"Name: {name}\nVersion: {version}\nLicense: Apache-2.0\n",
            encoding="utf-8",
        )
        (dist / "LICENSE").write_text("Apache License 2.0", encoding="utf-8")

    def _model(self, model_root: Path, name: str) -> None:
        model = model_root / name
        model.mkdir(parents=True)
        for filename in MODEL_REQUIRED_FILES:
            (model / filename).write_bytes(b"model")

    def _ready_bundle(self, root: Path, *, suffix: str = ".png") -> tuple[Path, Path, Path]:
        runtime = root / "runtime"
        models = root / "models"
        python = runtime / "Scripts" / "python.exe"
        python.parent.mkdir(parents=True)
        python.write_bytes(b"MZ")
        self._distribution(runtime, "paddleocr", "3.7.0")
        self._distribution(runtime, "paddlepaddle", "3.2.0")
        self._model(models, TEXT_DETECTION_MODEL_NAME)
        self._model(models, TEXT_RECOGNITION_MODEL_NAME)
        image = root / f"sample{suffix}"
        image.write_bytes(b"local-image")
        return runtime, models, image

    def test_ready_bundle_is_static_and_pinned(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            runtime = root / "runtime"
            models = root / "models"
            python = runtime / "Scripts" / "python.exe"
            python.parent.mkdir(parents=True)
            python.write_bytes(b"MZ")
            self._distribution(runtime, "paddleocr", "3.7.0")
            self._distribution(runtime, "paddlepaddle", "3.2.0")
            self._model(models, TEXT_DETECTION_MODEL_NAME)
            self._model(models, TEXT_RECOGNITION_MODEL_NAME)

            result = resolve_paddleocr_runtime(
                env={
                    PADDLEOCR_RUNTIME_ROOT_ENV: str(runtime),
                    PADDLEOCR_MODEL_ROOT_ENV: str(models),
                }
            )

            self.assertTrue(result.ready)
            self.assertEqual(result.paddleocr_version, "3.7.0")
            self.assertEqual(result.paddlepaddle_version, "3.2.0")
            self.assertEqual(result.device, "cpu")
            self.assertEqual(result.license, "Apache-2.0")

    def test_inference_kwargs_force_local_models_and_disable_auxiliary_models(self):
        result = resolve_paddleocr_runtime(env={})
        kwargs = result.inference_kwargs()
        self.assertEqual(kwargs["device"], "cpu")
        self.assertEqual(kwargs["cpu_threads"], 2)
        self.assertFalse(kwargs["enable_mkldnn"])
        self.assertFalse(kwargs["use_doc_orientation_classify"])
        self.assertFalse(kwargs["use_doc_unwarping"])
        self.assertFalse(kwargs["use_textline_orientation"])
        self.assertTrue(str(kwargs["text_detection_model_dir"]).endswith(TEXT_DETECTION_MODEL_NAME))
        self.assertTrue(
            str(kwargs["text_recognition_model_dir"]).endswith(TEXT_RECOGNITION_MODEL_NAME)
        )

    def test_missing_model_file_fails_closed(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            result = resolve_paddleocr_runtime(
                env={
                    PADDLEOCR_RUNTIME_ROOT_ENV: str(root / "runtime"),
                    PADDLEOCR_MODEL_ROOT_ENV: str(root / "models"),
                }
            )
            self.assertFalse(result.ready)
            self.assertTrue(any(item.startswith("model_file_missing:") for item in result.diagnostics))

    def test_extract_returns_structured_receipt_and_uses_shell_false(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            runtime, models, image = self._ready_bundle(root)
            payload = (
                'log line\n__PADDLEOCR_RECEIPT__'
                '{"lines":["한글 OCR 테스트 2026"],"scores":[0.99]}\n'
            )
            completed = subprocess.CompletedProcess([], 0, stdout=payload, stderr="")
            with patch(
                "modules.tool_adapters.paddleocr_runtime.subprocess.run",
                return_value=completed,
            ) as run:
                receipt = extract_korean_text(
                    image,
                    timeout_seconds=10,
                    env={
                        PADDLEOCR_RUNTIME_ROOT_ENV: str(runtime),
                        PADDLEOCR_MODEL_ROOT_ENV: str(models),
                    },
                )

            self.assertTrue(receipt.success)
            self.assertEqual(receipt.status, "completed")
            self.assertEqual(receipt.text, "한글 OCR 테스트 2026")
            self.assertEqual(receipt.scores, (0.99,))
            self.assertTrue(receipt.input_unchanged)
            command = run.call_args.args[0]
            self.assertEqual(command[0], str(runtime / "Scripts" / "python.exe"))
            self.assertIn(str(models / TEXT_DETECTION_MODEL_NAME), command)
            self.assertIn(str(models / TEXT_RECOGNITION_MODEL_NAME), command)
            self.assertIs(run.call_args.kwargs["shell"], False)
            self.assertEqual(run.call_args.kwargs["timeout"], 10.0)
            self.assertEqual(run.call_args.kwargs["env"]["HF_HUB_OFFLINE"], "1")

    def test_extract_rejects_unsupported_suffix_without_launch(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            runtime, models, image = self._ready_bundle(root, suffix=".txt")
            with patch("modules.tool_adapters.paddleocr_runtime.subprocess.run") as run:
                receipt = extract_korean_text(
                    image,
                    env={
                        PADDLEOCR_RUNTIME_ROOT_ENV: str(runtime),
                        PADDLEOCR_MODEL_ROOT_ENV: str(models),
                    },
                )
            self.assertFalse(receipt.success)
            self.assertEqual(receipt.status, "rejected")
            self.assertEqual(receipt.reason, "unsupported_image_suffix")
            run.assert_not_called()

    def test_extract_rejects_unbounded_timeout_without_launch(self):
        with patch("modules.tool_adapters.paddleocr_runtime.subprocess.run") as run:
            receipt = extract_korean_text("unused.png", timeout_seconds=121)
        self.assertFalse(receipt.success)
        self.assertEqual(receipt.reason, "invalid_timeout")
        run.assert_not_called()

    def test_extract_rejects_missing_path_without_launch(self):
        with TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing.png"
            with patch("modules.tool_adapters.paddleocr_runtime.subprocess.run") as run:
                receipt = extract_korean_text(missing)
            self.assertFalse(receipt.success)
            self.assertEqual(receipt.status, "rejected")
            self.assertEqual(receipt.reason, "image_not_found")
            run.assert_not_called()

    def test_extract_timeout_fails_closed(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            runtime, models, image = self._ready_bundle(root)
            with patch(
                "modules.tool_adapters.paddleocr_runtime.subprocess.run",
                side_effect=subprocess.TimeoutExpired(["python"], 2),
            ):
                receipt = extract_korean_text(
                    image,
                    timeout_seconds=2,
                    env={
                        PADDLEOCR_RUNTIME_ROOT_ENV: str(runtime),
                        PADDLEOCR_MODEL_ROOT_ENV: str(models),
                    },
                )
            self.assertFalse(receipt.success)
            self.assertEqual(receipt.status, "timed_out")
            self.assertEqual(receipt.reason, "ocr_timeout")

    def test_extract_invalid_worker_payload_fails_closed(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            runtime, models, image = self._ready_bundle(root)
            completed = subprocess.CompletedProcess([], 0, stdout="not-json", stderr="")
            with patch(
                "modules.tool_adapters.paddleocr_runtime.subprocess.run",
                return_value=completed,
            ):
                receipt = extract_korean_text(
                    image,
                    env={
                        PADDLEOCR_RUNTIME_ROOT_ENV: str(runtime),
                        PADDLEOCR_MODEL_ROOT_ENV: str(models),
                    },
                )
            self.assertFalse(receipt.success)
            self.assertEqual(receipt.reason, "invalid_ocr_receipt")


if __name__ == "__main__":
    unittest.main()
