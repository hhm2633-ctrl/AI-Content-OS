from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from modules.tool_adapters.sentence_transformers_runtime import (
    DEFAULT_SENTENCE_TRANSFORMERS_MODEL_REVISION,
    DEFAULT_SENTENCE_TRANSFORMERS_RUNTIME_ROOT,
    OFFLINE_ENVIRONMENT,
    SENTENCE_TRANSFORMERS_MODEL_ROOT_ENV,
    SENTENCE_TRANSFORMERS_RUNTIME_ROOT_ENV,
    resolve_sentence_transformers_model,
    resolve_sentence_transformers_runtime,
    score_text_pairs,
)


class SentenceTransformersRuntimeTests(unittest.TestCase):
    def _runtime(self, root: Path) -> None:
        python = root / "Scripts" / "python.exe"
        python.parent.mkdir(parents=True)
        python.write_bytes(b"MZ")
        package = root / "Lib" / "site-packages" / "sentence_transformers" / "__init__.py"
        package.parent.mkdir(parents=True)
        package.write_text("", encoding="utf-8")
        dist = root / "Lib" / "site-packages" / "sentence_transformers-5.6.0.dist-info"
        (dist / "licenses").mkdir(parents=True)
        (dist / "METADATA").write_text(
            "Name: sentence-transformers\nVersion: 5.6.0\nLicense-Expression: Apache-2.0\n",
            encoding="utf-8",
        )
        (dist / "licenses" / "LICENSE").write_text("Apache 2.0", encoding="utf-8")
        (dist / "licenses" / "NOTICE.txt").write_text("Notice", encoding="utf-8")

    @staticmethod
    def _model(root: Path) -> None:
        for relative in (
            "model.safetensors",
            "modules.json",
            "config.json",
            "tokenizer.json",
            "1_Pooling/config.json",
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"ready")

    def test_default_path_and_offline_contract(self):
        self.assertEqual(
            DEFAULT_SENTENCE_TRANSFORMERS_RUNTIME_ROOT,
            Path(r"F:\AI-Content-OS-Data\tools\sentence-transformers"),
        )
        self.assertEqual(dict(OFFLINE_ENVIRONMENT)["HF_HUB_OFFLINE"], "1")

    def test_ready_override_reads_static_metadata(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._runtime(root)
            result = resolve_sentence_transformers_runtime(
                env={SENTENCE_TRANSFORMERS_RUNTIME_ROOT_ENV: str(root)}
            )
            self.assertTrue(result.ready)
            self.assertEqual(result.version, "5.6.0")
            self.assertEqual(result.license, "Apache-2.0")
            self.assertTrue(result.notice_path.endswith("NOTICE.txt"))
            self.assertEqual(result.offline_environment, OFFLINE_ENVIRONMENT)

    def test_missing_root_is_diagnostic(self):
        with TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing"
            result = resolve_sentence_transformers_runtime(
                env={SENTENCE_TRANSFORMERS_RUNTIME_ROOT_ENV: str(missing)}
            )
            self.assertFalse(result.ready)
            self.assertIn(f"runtime_root_missing:{missing}", result.diagnostics)

    def test_local_model_requires_safe_weights_and_sentence_transformer_contract(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._model(root)
            result = resolve_sentence_transformers_model(
                env={SENTENCE_TRANSFORMERS_MODEL_ROOT_ENV: str(root)}
            )
            self.assertTrue(result.ready)
            self.assertEqual(result.license, "Apache-2.0")
            self.assertEqual(result.revision, DEFAULT_SENTENCE_TRANSFORMERS_MODEL_REVISION)

    def test_local_model_missing_file_is_fail_closed(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            result = resolve_sentence_transformers_model(
                env={SENTENCE_TRANSFORMERS_MODEL_ROOT_ENV: str(root)}
            )
            self.assertFalse(result.ready)
            self.assertTrue(any(item.startswith("model_file_missing:") for item in result.diagnostics))

    def test_text_similarity_uses_bounded_offline_local_process(self):
        with TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            runtime = base / "runtime"
            model = base / "model"
            self._runtime(runtime)
            self._model(model)
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout='{"offline": true, "scores": [0.9461, 0.1879]}\n',
                    stderr="",
                )

            result = score_text_pairs(
                [("서울 폭우 피해", "수도권 집중호우 피해"), ("서울 폭우", "여름 향수")],
                env={
                    SENTENCE_TRANSFORMERS_RUNTIME_ROOT_ENV: str(runtime),
                    SENTENCE_TRANSFORMERS_MODEL_ROOT_ENV: str(model),
                },
                runner=fake_runner,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["scores"], [0.9461, 0.1879])
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1]["env"]["HF_HUB_OFFLINE"], "1")
            self.assertTrue(result["boundaries"]["not_fact_evidence"])

    def test_text_similarity_missing_runtime_falls_back_visibly(self):
        with TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing"
            result = score_text_pairs(
                [("같은 사건", "동일 사건")],
                env={
                    SENTENCE_TRANSFORMERS_RUNTIME_ROOT_ENV: str(missing),
                    SENTENCE_TRANSFORMERS_MODEL_ROOT_ENV: str(missing),
                },
            )
            self.assertEqual(result["status"], "unavailable")
            self.assertEqual(result["fallback"], "existing_deterministic_similarity")
            self.assertEqual(result["scores"], [])

    def test_text_similarity_rejects_unbounded_input(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 128"):
            score_text_pairs([("왼쪽", "오른쪽")] * 129)


if __name__ == "__main__":
    unittest.main()
