import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from modules.tool_adapters.playwright_runtime import (
    DEFAULT_PLAYWRIGHT_BROWSERS_PATH,
    PLAYWRIGHT_BROWSERS_PATH_ENV,
    PLAYWRIGHT_EXECUTABLE_ENV,
    resolve_playwright_executable,
    resolve_playwright_runtime,
)


class PlaywrightRuntimeResolverTests(unittest.TestCase):
    def _write_executable(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"MZ\x00offline-test")
        return path

    def test_default_path_is_the_verified_f_drive_browser_store(self):
        self.assertEqual(
            DEFAULT_PLAYWRIGHT_BROWSERS_PATH,
            Path(r"F:\AI-Content-OS-Data\tools\playwright-browsers"),
        )

    def test_direct_executable_override_has_highest_precedence(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            executable = self._write_executable(root / "override" / "chromium.exe")
            fallback = self._write_executable(
                root
                / "store"
                / "chromium_headless_shell-1228"
                / "chrome-headless-shell-win64"
                / "chrome-headless-shell.exe"
            )
            result = resolve_playwright_runtime(
                env={
                    PLAYWRIGHT_EXECUTABLE_ENV: str(executable),
                    PLAYWRIGHT_BROWSERS_PATH_ENV: str(fallback.parents[2]),
                }
            )

            self.assertTrue(result.ready)
            self.assertEqual(result.executable_path, str(executable))
            self.assertEqual(result.source, "environment_executable")
            self.assertEqual(result.diagnostics, ())

    def test_missing_direct_override_does_not_silently_fall_back(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            missing = root / "missing" / "chrome.exe"
            self._write_executable(
                root
                / "store"
                / "chromium-1228"
                / "chrome-win64"
                / "chrome.exe"
            )
            result = resolve_playwright_runtime(
                env={
                    PLAYWRIGHT_EXECUTABLE_ENV: str(missing),
                    PLAYWRIGHT_BROWSERS_PATH_ENV: str(root / "store"),
                }
            )

            self.assertFalse(result.ready)
            self.assertEqual(result.executable_path, "")
            self.assertEqual(result.checked_paths, (str(missing),))
            self.assertEqual(
                result.diagnostics,
                (f"executable_override_missing:{missing}",),
            )

    def test_browser_root_prefers_newest_headless_revision(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            older = self._write_executable(
                root
                / "chromium_headless_shell-1227"
                / "chrome-headless-shell-win64"
                / "chrome-headless-shell.exe"
            )
            newer = self._write_executable(
                root
                / "chromium_headless_shell-1228"
                / "chrome-headless-shell-win64"
                / "chrome-headless-shell.exe"
            )
            self._write_executable(
                root / "chromium-9999" / "chrome-win64" / "chrome.exe"
            )

            result = resolve_playwright_runtime(
                env={PLAYWRIGHT_BROWSERS_PATH_ENV: str(root)}
            )

            self.assertTrue(result.ready)
            self.assertEqual(result.executable_path, str(newer))
            self.assertEqual(result.source, "environment_browser_root")
            self.assertEqual(result.checked_paths[:2], (str(newer), str(older)))

    def test_browser_root_falls_back_to_full_chromium(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            chromium = self._write_executable(
                root / "chromium-1228" / "chrome-win64" / "chrome.exe"
            )

            result = resolve_playwright_runtime(
                env={PLAYWRIGHT_BROWSERS_PATH_ENV: str(root)}
            )

            self.assertTrue(result.ready)
            self.assertEqual(result.executable_path, str(chromium))

    def test_missing_root_reports_every_checked_default_layout_path(self):
        with TemporaryDirectory() as temporary_directory:
            missing_root = Path(temporary_directory) / "not-installed"
            result = resolve_playwright_runtime(
                env={}, default_browser_root=missing_root
            )

            self.assertFalse(result.ready)
            self.assertEqual(result.source, "default_browser_root")
            self.assertEqual(len(result.checked_paths), 2)
            self.assertIn(f"browser_root_missing:{missing_root}", result.diagnostics)
            self.assertTrue(
                result.diagnostics[-1].startswith("playwright_executable_missing:")
            )

    def test_empty_executable_is_not_ready(self):
        with TemporaryDirectory() as temporary_directory:
            executable = Path(temporary_directory) / "chrome.exe"
            executable.touch()

            result = resolve_playwright_runtime(
                env={PLAYWRIGHT_EXECUTABLE_ENV: str(executable)}
            )

            self.assertFalse(result.ready)
            self.assertEqual(
                result.diagnostics,
                (f"executable_override_empty_file:{executable}",),
            )

    def test_explicit_environment_mapping_is_not_mutated(self):
        with TemporaryDirectory() as temporary_directory:
            mapping = {
                PLAYWRIGHT_BROWSERS_PATH_ENV: str(
                    Path(temporary_directory) / "missing"
                )
            }
            original_mapping = dict(mapping)
            process_environment = dict(os.environ)

            resolve_playwright_runtime(env=mapping)

            self.assertEqual(mapping, original_mapping)
            self.assertEqual(dict(os.environ), process_environment)

    def test_executable_convenience_function_returns_empty_when_missing(self):
        with TemporaryDirectory() as temporary_directory:
            self.assertEqual(
                resolve_playwright_executable(
                    env={}, default_browser_root=Path(temporary_directory) / "missing"
                ),
                "",
            )


if __name__ == "__main__":
    unittest.main()
