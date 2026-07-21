from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from modules.tool_adapters.pyscenedetect_runtime import detect_scenes


class PySceneDetectRuntimeTests(unittest.TestCase):
    def test_missing_video_fails_closed(self):
        with patch(
            "modules.tool_adapters.pyscenedetect_runtime.resolve_pyscenedetect_runtime"
        ) as resolver:
            resolver.return_value = SimpleNamespace(
                ready=True, python_executable="python.exe", diagnostics=()
            )
            result = detect_scenes("missing.mp4")
        self.assertEqual(result["status"], "blocked")

    def test_unsupported_suffix_is_rejected(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "input.txt"
            path.write_text("not video", encoding="utf-8")
            with patch(
                "modules.tool_adapters.pyscenedetect_runtime.resolve_pyscenedetect_runtime"
            ) as resolver:
                resolver.return_value = SimpleNamespace(
                    ready=True, python_executable="python.exe", diagnostics=()
                )
                result = detect_scenes(path)
        self.assertEqual(result["errors"], ["unsupported_video_suffix"])

    def test_bounded_shell_free_scene_payload(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "input.mp4"
            path.write_bytes(b"video")
            calls = []

            def runner(command, **kwargs):
                calls.append((command, kwargs))
                return SimpleNamespace(
                    returncode=0,
                    stdout='[{"start_seconds": 0.0, "end_seconds": 1.0}]',
                    stderr="",
                )

            with patch(
                "modules.tool_adapters.pyscenedetect_runtime.resolve_pyscenedetect_runtime"
            ) as resolver:
                resolver.return_value = SimpleNamespace(
                    ready=True, python_executable="python.exe", diagnostics=()
                )
                result = detect_scenes(path, timeout_seconds=999, runner=runner)
        self.assertEqual(result["status"], "completed")
        self.assertFalse(calls[0][1]["shell"])
        self.assertEqual(calls[0][1]["timeout"], 300)


if __name__ == "__main__":
    unittest.main()
