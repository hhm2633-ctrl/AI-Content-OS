import json
import subprocess
import unittest
from unittest.mock import Mock, patch

from modules.tool_adapters.intel_xpu_runtime import IntelXpuRuntimeProbe


class TestIntelXpuRuntimeProbe(unittest.TestCase):
    def setUp(self):
        self.probe = IntelXpuRuntimeProbe("F:/isolated-xpu/python.exe", timeout_seconds=5)

    @staticmethod
    def _completed(payload, *, returncode=0, stderr=""):
        return subprocess.CompletedProcess(
            args=[],
            returncode=returncode,
            stdout=json.dumps(payload) + "\n",
            stderr=stderr,
        )

    @patch("modules.tool_adapters.intel_xpu_runtime.subprocess.run")
    @patch("modules.tool_adapters.intel_xpu_runtime.Path.is_file", return_value=True)
    def test_separates_runtime_execution_imports_and_generation_claim(self, _is_file, run):
        run.side_effect = [
            self._completed(
                {
                    "torch_version": "2.13.0+xpu",
                    "xpu_available": True,
                    "device_name": "Intel Arc",
                    "operations": {
                        "float32": {"passed": True, "observed": 8.0},
                        "float16": {"passed": True, "observed": 8.0},
                        "bfloat16": {"passed": True, "observed": 8.0},
                    },
                }
            ),
            self._completed(
                {
                    "imported": [
                        "QwenImagePipeline",
                        "Flux2Pipeline",
                        "Flux2KleinPipeline",
                    ]
                }
            ),
        ]

        result = self.probe.probe()

        self.assertEqual(result["status"], "runtime_ready_generation_unverified")
        self.assertEqual(result["device_execution"]["status"], "passed")
        self.assertEqual(result["pipeline_imports"]["status"], "passed")
        readiness = result["model_generation_readiness"]
        self.assertTrue(readiness["prerequisites_verified"])
        self.assertFalse(readiness["ready"])
        self.assertFalse(readiness["generation_attempted"])
        self.assertIn("END_TO_END_GENERATION_NOT_VERIFIED", readiness["blocker_codes"])
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            self.assertEqual(call.kwargs["timeout"], 5.0)
            self.assertFalse(call.kwargs["check"])
            self.assertEqual(call.args[0][1:3], ["-I", "-c"])
            self.assertEqual(call.kwargs["env"]["HF_HUB_OFFLINE"], "1")

    @patch("modules.tool_adapters.intel_xpu_runtime.subprocess.run")
    @patch("modules.tool_adapters.intel_xpu_runtime.Path.is_file", return_value=False)
    def test_missing_runtime_fails_closed_without_subprocess(self, _is_file, run):
        result = self.probe.probe()

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(
            result["device_execution"]["reason_code"], "XPU_PYTHON_NOT_FOUND"
        )
        self.assertFalse(result["model_generation_readiness"]["ready"])
        run.assert_not_called()

    @patch("modules.tool_adapters.intel_xpu_runtime.subprocess.run")
    @patch("modules.tool_adapters.intel_xpu_runtime.Path.is_file", return_value=True)
    def test_timeout_is_bounded_and_does_not_raise(self, _is_file, run):
        run.side_effect = [
            subprocess.TimeoutExpired(cmd="probe", timeout=5),
            self._completed({"imported": ["QwenImagePipeline"]}),
        ]

        result = self.probe.probe()

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["device_execution"]["reason_code"], "PROBE_TIMEOUT")
        self.assertEqual(result["device_execution"]["timeout_seconds"], 5.0)
        self.assertFalse(result["model_generation_readiness"]["prerequisites_verified"])

    @patch("modules.tool_adapters.intel_xpu_runtime.subprocess.run")
    @patch("modules.tool_adapters.intel_xpu_runtime.Path.is_file", return_value=True)
    def test_nonzero_and_invalid_json_are_reported_separately(self, _is_file, run):
        run.side_effect = [
            subprocess.CompletedProcess([], 7, stdout="", stderr="xpu failure"),
            subprocess.CompletedProcess([], 0, stdout="not-json\n", stderr=""),
        ]

        result = self.probe.probe()

        self.assertEqual(
            result["device_execution"]["reason_code"], "PROBE_NONZERO_EXIT"
        )
        self.assertEqual(
            result["pipeline_imports"]["reason_code"], "PROBE_INVALID_JSON"
        )
        self.assertFalse(result["model_generation_readiness"]["ready"])

    def test_timeout_validation_and_absolute_cap(self):
        with self.assertRaises(ValueError):
            IntelXpuRuntimeProbe(timeout_seconds=0)
        capped = IntelXpuRuntimeProbe(timeout_seconds=999)
        self.assertEqual(capped.timeout_seconds, 30.0)


if __name__ == "__main__":
    unittest.main()
