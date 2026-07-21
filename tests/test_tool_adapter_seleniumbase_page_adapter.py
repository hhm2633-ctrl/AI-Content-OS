import base64
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from modules.tool_adapters.seleniumbase_page_adapter import SeleniumBasePageAdapter


class _FakeProcess:
    def __init__(self, responses):
        self.stdin = io.StringIO()
        self.stdout = io.StringIO("\n".join(responses) + "\n")
        self.stderr = io.StringIO()
        self.terminated = False

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True


class SeleniumBasePageAdapterTests(unittest.TestCase):
    def test_playwright_like_subset_uses_explicit_local_python_driver_and_chrome(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            python = root / "python.exe"
            driver = root / "chromedriver.exe"
            chrome = root / "chrome.exe"
            for path in (python, driver, chrome):
                path.write_bytes(b"MZ")
            png = b"\x89PNG\r\n\x1a\nreadable"
            responses = [
                '{"status":"ready"}',
                '{"id":1,"status":"ok","result":"<html>fixture</html>"}',
                '{"id":2,"status":"ok","result":2}',
                '{"id":3,"status":"ok","result":true}',
                '{"id":4,"status":"ok","result":"'
                + base64.b64encode(png).decode("ascii")
                + '"}',
                '{"id":5,"status":"ok","result":null}',
                '{"id":6,"status":"ok","result":null}',
            ]
            calls = []

            def process_factory(command, **kwargs):
                calls.append((command, kwargs))
                return _FakeProcess(responses)

            page = SeleniumBasePageAdapter(
                runtime=SimpleNamespace(
                    python_executable=str(python), driver_path=str(driver)
                ),
                chrome_executable=chrome,
                process_factory=process_factory,
            )
            self.assertEqual(page.content(), "<html>fixture</html>")
            locator = page.locator("li.comment")
            self.assertEqual(locator.count(), 2)
            self.assertTrue(locator.first.is_visible(timeout=1))
            self.assertEqual(locator.nth(1).screenshot(type="png"), png)
            self.assertIsNone(page.evaluate("return 1"))
            page.close()

            self.assertEqual(len(calls), 1)
            command = calls[0][0]
            self.assertEqual(command[0], str(python))
            self.assertIn(str(driver), command)
            self.assertIn(str(chrome), command)
            self.assertFalse(calls[0][1]["shell"])

    def test_missing_explicit_driver_fails_before_process_start(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            python = root / "python.exe"
            chrome = root / "chrome.exe"
            python.write_bytes(b"MZ")
            chrome.write_bytes(b"MZ")
            calls = []
            with self.assertRaisesRegex(RuntimeError, "selenium_local_driver_missing"):
                SeleniumBasePageAdapter(
                    runtime=SimpleNamespace(
                        python_executable=str(python),
                        driver_path=str(root / "missing-driver.exe"),
                    ),
                    chrome_executable=chrome,
                    process_factory=lambda *args, **kwargs: calls.append((args, kwargs)),
                )
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
