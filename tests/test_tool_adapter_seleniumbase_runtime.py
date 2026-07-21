from pathlib import Path
import hashlib
import json
from tempfile import TemporaryDirectory
import unittest

from modules.tool_adapters.seleniumbase_runtime import (
    DEFAULT_SELENIUMBASE_RUNTIME_ROOT,
    DEFAULT_SELENIUMBASE_DRIVER_ROOT,
    PINNED_CHROMEDRIVER_VERSION,
    SELENIUMBASE_DRIVER_ROOT_ENV,
    SELENIUMBASE_RUNTIME_ROOT_ENV,
    resolve_seleniumbase_runtime,
)


class SeleniumBaseRuntimeTests(unittest.TestCase):
    def _runtime(self, root: Path) -> None:
        python = root / "Scripts" / "python.exe"
        python.parent.mkdir(parents=True)
        python.write_bytes(b"MZ")
        package = root / "Lib" / "site-packages" / "seleniumbase" / "__init__.py"
        package.parent.mkdir(parents=True)
        package.write_text("", encoding="utf-8")
        dist = root / "Lib" / "site-packages" / "seleniumbase-4.51.2.dist-info"
        (dist / "licenses").mkdir(parents=True)
        (dist / "METADATA").write_text(
            "Name: seleniumbase\nVersion: 4.51.2\nLicense: MIT\n", encoding="utf-8"
        )
        (dist / "licenses" / "LICENSE").write_text("MIT", encoding="utf-8")

    @staticmethod
    def _driver(root: Path) -> Path:
        driver = root / "package" / "chromedriver-win64" / "chromedriver.exe"
        driver.parent.mkdir(parents=True)
        driver.write_bytes(b"MZ-official-test-driver")
        digest = hashlib.sha256(driver.read_bytes()).hexdigest()
        (root / "install_manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "seleniumbase_chromedriver_provenance_v1",
                    "source": {
                        "provider": "Chrome for Testing",
                        "version": PINNED_CHROMEDRIVER_VERSION,
                    },
                    "driver": {
                        "bytes": driver.stat().st_size,
                        "sha256": digest,
                    },
                    "runtime_policy": {
                        "offline_local_driver_only": True,
                        "selenium_manager_forbidden": True,
                        "runtime_download_forbidden": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        return driver

    def test_default_path(self):
        self.assertEqual(
            DEFAULT_SELENIUMBASE_RUNTIME_ROOT,
            Path(r"F:\AI-Content-OS-Data\tools\seleniumbase"),
        )
        self.assertEqual(
            DEFAULT_SELENIUMBASE_DRIVER_ROOT,
            DEFAULT_SELENIUMBASE_RUNTIME_ROOT
            / "drivers"
            / PINNED_CHROMEDRIVER_VERSION,
        )

    def test_ready_override_reads_version_and_license_without_import(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._runtime(root)
            driver_root = root / "driver"
            driver = self._driver(driver_root)
            env = {
                SELENIUMBASE_RUNTIME_ROOT_ENV: str(root),
                SELENIUMBASE_DRIVER_ROOT_ENV: str(driver_root),
            }
            original = dict(env)
            result = resolve_seleniumbase_runtime(env=env)
            self.assertTrue(result.ready)
            self.assertEqual(result.version, "4.51.2")
            self.assertEqual(result.license, "MIT")
            self.assertEqual(result.source, "environment_root")
            self.assertEqual(result.driver_path, str(driver))
            self.assertEqual(result.driver_version, PINNED_CHROMEDRIVER_VERSION)
            self.assertEqual(env, original)

    def test_missing_root_is_diagnostic(self):
        with TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing"
            result = resolve_seleniumbase_runtime(
                env={
                    SELENIUMBASE_RUNTIME_ROOT_ENV: str(missing),
                    SELENIUMBASE_DRIVER_ROOT_ENV: str(missing),
                }
            )
            self.assertFalse(result.ready)
            self.assertIn(f"runtime_root_missing:{missing}", result.diagnostics)

    def test_driver_hash_tampering_blocks_runtime(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._runtime(root)
            driver_root = root / "driver"
            driver = self._driver(driver_root)
            driver.write_bytes(b"changed")
            result = resolve_seleniumbase_runtime(
                env={
                    SELENIUMBASE_RUNTIME_ROOT_ENV: str(root),
                    SELENIUMBASE_DRIVER_ROOT_ENV: str(driver_root),
                }
            )
            self.assertFalse(result.ready)
            self.assertIn("driver_sha256_mismatch", result.diagnostics)


if __name__ == "__main__":
    unittest.main()
