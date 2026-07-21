from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from modules.tool_adapters.seaweedfs_runtime import (
    DEFAULT_SEAWEEDFS_EXECUTABLE,
    SEAWEEDFS_EXECUTABLE_ENV,
    resolve_seaweedfs_runtime,
)


class SeaweedFSRuntimeTests(unittest.TestCase):
    def test_default_executable(self):
        self.assertEqual(
            DEFAULT_SEAWEEDFS_EXECUTABLE,
            Path(r"F:\AI-Content-OS-Data\tools\seaweedfs\4.39\weed.exe"),
        )

    def test_ready_binary_reports_version_and_missing_license_separately(self):
        with TemporaryDirectory() as temporary_directory:
            executable = Path(temporary_directory) / "4.39" / "weed.exe"
            executable.parent.mkdir()
            executable.write_bytes(b"MZ\x00weed")
            result = resolve_seaweedfs_runtime(
                env={SEAWEEDFS_EXECUTABLE_ENV: str(executable)}
            )
            self.assertTrue(result.ready)
            self.assertEqual(result.version, "4.39")
            self.assertEqual(result.platform, "windows-amd64")
            self.assertEqual(result.license, "unverified")
            self.assertEqual(
                result.diagnostics,
                (f"license_file_missing:{executable.parent}",),
            )

    def test_adjacent_license_is_detected_without_running_binary(self):
        with TemporaryDirectory() as temporary_directory:
            executable = Path(temporary_directory) / "4.39" / "weed.exe"
            executable.parent.mkdir()
            executable.write_bytes(b"MZ\x00weed")
            license_path = executable.parent / "LICENSE"
            license_path.write_text("Apache License", encoding="utf-8")
            result = resolve_seaweedfs_runtime(
                env={SEAWEEDFS_EXECUTABLE_ENV: str(executable)}
            )
            self.assertTrue(result.ready)
            self.assertEqual(result.license, "locally_verified")
            self.assertEqual(result.license_path, str(license_path))
            self.assertEqual(result.diagnostics, ())

    def test_empty_binary_is_not_ready(self):
        with TemporaryDirectory() as temporary_directory:
            executable = Path(temporary_directory) / "4.39" / "weed.exe"
            executable.parent.mkdir()
            executable.touch()
            result = resolve_seaweedfs_runtime(
                env={SEAWEEDFS_EXECUTABLE_ENV: str(executable)}
            )
            self.assertFalse(result.ready)
            self.assertIn(f"executable_empty:{executable}", result.diagnostics)


if __name__ == "__main__":
    unittest.main()
