import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from modules.tool_adapters.openclip_runtime import (
    PINNED_MODEL_REVISION,
    OpenClipRuntime,
)


class OpenClipRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.runtime = root / "runtime"
        self.model = root / "model"
        self.provenance = root / "provenance.json"
        (self.runtime / "Scripts").mkdir(parents=True)
        (self.runtime / "Scripts" / "python.exe").write_bytes(b"python")
        license_path = self.runtime / "LICENSE"
        license_path.write_bytes(b"MIT License")
        self.model.mkdir()
        weight_path = self.model / "open_clip_model.safetensors"
        weight_path.write_bytes(b"safe weights")
        self.manifest = {
            "schema_version": "openclip_install_provenance_v1",
            "runtime": {"open_clip_torch": "3.3.0"},
            "code_license": {
                "spdx": "MIT",
                "commercial_reuse": True,
                "installed_license_path": str(license_path),
                "license_bytes": license_path.stat().st_size,
                "license_sha256": hashlib.sha256(license_path.read_bytes()).hexdigest(),
            },
            "weights": {
                "repository": "timm/resnet50_clip.openai",
                "model_name": "RN50-quickgelu",
                "revision": PINNED_MODEL_REVISION,
                "private": False,
                "gated": False,
                "license_spdx": "MIT",
                "commercial_reuse": True,
                "license_evidence": "https://huggingface.co/timm/resnet50_clip.openai",
                "weight_path": str(weight_path),
                "weight_bytes": weight_path.stat().st_size,
                "weight_sha256": hashlib.sha256(weight_path.read_bytes()).hexdigest(),
            },
            "smoke": {
                "passed": True,
                "offline": True,
                "image_norm": 1.0,
                "text_norms": [1.0, 1.0],
                "cosine_similarity": [0.2, 0.1],
            },
        }
        self._write_manifest()
        self.image = root / "fixture.png"
        self.image.write_bytes(b"not decoded because subprocess is mocked")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_manifest(self):
        self.provenance.write_text(json.dumps(self.manifest), encoding="utf-8")

    def probe(self):
        return OpenClipRuntime(
            runtime_root=self.runtime,
            model_root=self.model,
            provenance_path=self.provenance,
        ).probe()

    def test_complete_pinned_commercial_runtime_is_ready(self):
        result = self.probe()
        self.assertTrue(result["ready"])
        self.assertTrue(all(result["capabilities"].values()))
        self.assertEqual(result["licenses"]["code"]["spdx"], "MIT")
        self.assertEqual(result["licenses"]["weights"]["spdx"], "MIT")
        self.assertTrue(result["boundaries"]["offline_only"])
        self.assertFalse(result["boundaries"]["owner_assets"])

    def test_code_and_weight_license_are_independent_fail_closed_checks(self):
        self.manifest["code_license"]["spdx"] = "unknown"
        self._write_manifest()
        result = self.probe()
        self.assertFalse(result["checks"]["code_license"])
        self.assertTrue(result["checks"]["weight_license"])

        self.manifest["code_license"]["spdx"] = "MIT"
        self.manifest["weights"]["commercial_reuse"] = False
        self._write_manifest()
        result = self.probe()
        self.assertTrue(result["checks"]["code_license"])
        self.assertFalse(result["checks"]["weight_license"])

    def test_gated_private_or_unpinned_weights_are_blocked(self):
        self.manifest["weights"]["gated"] = True
        self.manifest["weights"]["revision"] = "main"
        self._write_manifest()
        result = self.probe()
        self.assertFalse(result["checks"]["weight_access"])
        self.assertFalse(result["checks"]["weight_revision"])

    def test_weight_path_must_stay_at_pinned_local_model_location(self):
        outside = self.model.parent / "outside.safetensors"
        outside.write_bytes(b"safe weights")
        self.manifest["weights"]["weight_path"] = str(outside)
        self.manifest["weights"]["weight_bytes"] = outside.stat().st_size
        self.manifest["weights"]["weight_sha256"] = hashlib.sha256(outside.read_bytes()).hexdigest()
        self._write_manifest()
        result = self.probe()
        self.assertFalse(result["checks"]["weight_integrity"])

    def test_weight_bytes_and_hash_must_match_provenance(self):
        Path(self.manifest["weights"]["weight_path"]).write_bytes(b"changed")
        result = self.probe()
        self.assertFalse(result["checks"]["weight_integrity"])
        self.assertIn("weight_integrity_check_failed", result["errors"])

    def test_normalized_offline_smoke_receipt_is_required(self):
        self.manifest["smoke"]["offline"] = False
        self.manifest["smoke"]["image_norm"] = 0.5
        self._write_manifest()
        result = self.probe()
        self.assertFalse(result["checks"]["offline_smoke"])
        self.assertFalse(result["capabilities"]["normalized_similarity"])

    def test_missing_or_invalid_provenance_is_blocked(self):
        self.provenance.unlink()
        self.assertEqual(self.probe()["errors"], ["provenance_missing"])
        self.provenance.write_text("not json", encoding="utf-8")
        self.assertTrue(self.probe()["errors"][0].startswith("provenance_invalid"))

    def test_score_validates_path_suffix_topics_and_timeout_before_execution(self):
        runtime = OpenClipRuntime(
            runtime_root=self.runtime,
            model_root=self.model,
            provenance_path=self.provenance,
        )
        runner = mock.Mock()
        with self.assertRaises(FileNotFoundError):
            runtime.score_image_topics(self.image.parent / "missing.png", ["topic"], runner=runner)
        invalid_suffix = self.image.with_suffix(".txt")
        invalid_suffix.write_bytes(b"x")
        with self.assertRaises(ValueError):
            runtime.score_image_topics(invalid_suffix, ["topic"], runner=runner)
        for topics in ([], [""], "topic"):
            with self.assertRaises(ValueError):
                runtime.score_image_topics(self.image, topics, runner=runner)
        with self.assertRaises(ValueError):
            runtime.score_image_topics(self.image, ["topic"], timeout_seconds=61, runner=runner)
        runner.assert_not_called()

    def test_score_runs_pinned_model_offline_without_shell(self):
        payload = {
            "offline": True,
            "model_name": "RN50-quickgelu",
            "embedding_dim": 1024,
            "image_norm": 1.0,
            "text_norms": [1.0, 1.0],
            "topics": ["red square", "blue circle"],
            "cosine_similarity": [0.3, 0.1],
        }
        runner = mock.Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(payload), stderr=""
            )
        )
        runtime = OpenClipRuntime(
            runtime_root=self.runtime,
            model_root=self.model,
            provenance_path=self.provenance,
        )
        result = runtime.score_image_topics(
            self.image, [" red square ", "blue circle"], timeout_seconds=12, runner=runner
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["score_semantics"], "internal_semantic_relevance_proxy")
        self.assertEqual(result["ranked_topics"][0]["topic"], "red square")
        self.assertIn("factual_accuracy", result["not_evidence_for"])
        args, kwargs = runner.call_args
        self.assertIn("RN50-quickgelu", args[0][2])
        self.assertEqual(kwargs["env"]["HF_HUB_OFFLINE"], "1")
        self.assertEqual(kwargs["env"]["TRANSFORMERS_OFFLINE"], "1")
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["timeout"], 12.0)

    def test_score_fails_closed_for_runtime_timeout_and_bad_receipt(self):
        runtime = OpenClipRuntime(
            runtime_root=self.runtime,
            model_root=self.model,
            provenance_path=self.provenance,
        )
        self.manifest["weights"]["gated"] = True
        self._write_manifest()
        blocked_runner = mock.Mock()
        blocked = runtime.score_image_topics(self.image, ["topic"], runner=blocked_runner)
        self.assertEqual(blocked["status"], "blocked")
        blocked_runner.assert_not_called()

        self.manifest["weights"]["gated"] = False
        self._write_manifest()
        timeout_runner = mock.Mock(side_effect=subprocess.TimeoutExpired(cmd=["python"], timeout=1))
        self.assertEqual(runtime.score_image_topics(self.image, ["topic"], runner=timeout_runner)["status"], "timeout")

        invalid_runner = mock.Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout='{"image_norm": 0.5}', stderr=""
            )
        )
        invalid = runtime.score_image_topics(self.image, ["topic"], runner=invalid_runner)
        self.assertEqual(invalid["reason"], "invalid_normalized_embedding_receipt")


if __name__ == "__main__":
    unittest.main()
