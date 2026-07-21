import subprocess
import unittest
from unittest.mock import patch

from modules.tool_adapters.realesrgan_runtime import RealEsrganRuntimeAdapter


class TestRealEsrganRuntimeAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = RealEsrganRuntimeAdapter("F:/runtime", timeout_seconds=7)

    @patch("modules.tool_adapters.realesrgan_runtime.subprocess.run")
    @patch("modules.tool_adapters.realesrgan_runtime.Path.exists", return_value=False)
    @patch("modules.tool_adapters.realesrgan_runtime.Path.is_dir", return_value=True)
    @patch("modules.tool_adapters.realesrgan_runtime.Path.is_file", return_value=True)
    def test_runs_allow_listed_local_command(self, _is_file, _is_dir, _exists, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="ok", stderr="")

        result = self.adapter.upscale("F:/in.png", "F:/out.png", model="realesr-animevideov3", scale=2)

        self.assertEqual(result["status"], "completed")
        command = run.call_args.args[0]
        self.assertEqual(command[1:5], ["-i", "F:\\in.png", "-o", "F:\\out.png"])
        self.assertIn("realesr-animevideov3", command)
        self.assertEqual(run.call_args.kwargs["timeout"], 7.0)
        self.assertNotIn("shell", run.call_args.kwargs)

    @patch("modules.tool_adapters.realesrgan_runtime.subprocess.run")
    @patch("modules.tool_adapters.realesrgan_runtime.Path.is_file", return_value=True)
    def test_rejects_unlisted_model_without_process(self, _is_file, run):
        result = self.adapter.upscale("F:/in.png", "F:/out.png", model="arbitrary")
        self.assertEqual(result["reason_code"], "MODEL_NOT_ALLOW_LISTED")
        run.assert_not_called()

    @patch("modules.tool_adapters.realesrgan_runtime.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 7))
    @patch("modules.tool_adapters.realesrgan_runtime.Path.exists", return_value=False)
    @patch("modules.tool_adapters.realesrgan_runtime.Path.is_dir", return_value=True)
    @patch("modules.tool_adapters.realesrgan_runtime.Path.is_file", return_value=True)
    def test_timeout_fails_closed(self, _is_file, _is_dir, _exists, _run):
        result = self.adapter.upscale("F:/in.png", "F:/out.png")
        self.assertEqual(result["reason_code"], "RUNTIME_TIMEOUT")


if __name__ == "__main__":
    unittest.main()
