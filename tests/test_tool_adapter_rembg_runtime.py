import subprocess
import unittest
from unittest.mock import patch

from modules.tool_adapters.rembg_runtime import PINNED_MODEL_MD5, RembgRuntimeAdapter


class TestRembgRuntimeAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = RembgRuntimeAdapter("F:/runtime", "F:/models", timeout_seconds=9)

    @patch("modules.tool_adapters.rembg_runtime.subprocess.run")
    @patch("modules.tool_adapters.rembg_runtime.Path.exists", return_value=False)
    @patch("modules.tool_adapters.rembg_runtime.Path.is_dir", return_value=True)
    @patch("modules.tool_adapters.rembg_runtime.Path.is_file", return_value=True)
    @patch.object(RembgRuntimeAdapter, "_model_md5", return_value=PINNED_MODEL_MD5)
    def test_runs_cpu_only_with_pinned_model(self, _md5, _is_file, _is_dir, _exists, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")

        result = self.adapter.cutout("F:/in.jpg", "F:/out.png")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["provider"], "CPUExecutionProvider")
        command = run.call_args.args[0]
        self.assertEqual(command[1:3], ["-I", "-c"])
        environment = run.call_args.kwargs["env"]
        self.assertEqual(environment["U2NET_HOME"], "F:\\models")
        self.assertNotIn("MODEL_CHECKSUM_DISABLED", environment)
        self.assertEqual(run.call_args.kwargs["timeout"], 9.0)

    @patch("modules.tool_adapters.rembg_runtime.subprocess.run")
    @patch("modules.tool_adapters.rembg_runtime.Path.is_file", return_value=True)
    @patch.object(RembgRuntimeAdapter, "_model_md5", return_value="bad")
    def test_checksum_mismatch_blocks_without_process(self, _md5, _is_file, run):
        result = self.adapter.cutout("F:/in.jpg", "F:/out.png")
        self.assertEqual(result["reason_code"], "RUNTIME_NOT_READY")
        self.assertEqual(result["readiness"]["reason_code"], "MODEL_CHECKSUM_MISMATCH")
        run.assert_not_called()

    @patch("modules.tool_adapters.rembg_runtime.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 9))
    @patch("modules.tool_adapters.rembg_runtime.Path.exists", return_value=False)
    @patch("modules.tool_adapters.rembg_runtime.Path.is_dir", return_value=True)
    @patch("modules.tool_adapters.rembg_runtime.Path.is_file", return_value=True)
    @patch.object(RembgRuntimeAdapter, "_model_md5", return_value=PINNED_MODEL_MD5)
    def test_timeout_fails_closed(self, _md5, _is_file, _is_dir, _exists, _run):
        result = self.adapter.cutout("F:/in.jpg", "F:/out.png")
        self.assertEqual(result["reason_code"], "RUNTIME_TIMEOUT")


if __name__ == "__main__":
    unittest.main()
