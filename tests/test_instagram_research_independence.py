import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_DIR = REPO_ROOT / "modules" / "instagram_research"

FORBIDDEN_NETWORK_OR_LLM_IMPORTS = (
    "requests",
    "urllib",
    "http.client",
    "socket",
    "openai",
    "anthropic",
)

FORBIDDEN_BROWSER_AUTOMATION_IMPORTS = (
    "playwright",
    "selenium",
    "puppeteer",
)


class TestInstagramResearchWorkflowIndependence(unittest.TestCase):
    def _module_py_files(self):
        return list(MODULE_DIR.glob("*.py"))

    def test_driver_script_does_not_import_playwright_or_browser_automation(self):
        for path in self._module_py_files():
            content = path.read_text(encoding="utf-8").lower()
            for forbidden in FORBIDDEN_BROWSER_AUTOMATION_IMPORTS:
                pattern = rf"^\s*(import|from)\s+{re.escape(forbidden)}\b"
                self.assertIsNone(
                    re.search(pattern, content, re.MULTILINE),
                    f"{path.name} must not import browser automation library '{forbidden}'"
                )

    def test_gitignore_has_no_unignore_rule_for_research_data(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("!storage/research", gitignore)

    def test_gitignore_still_blanket_ignores_storage(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("storage/**", gitignore)

    def test_module_does_not_import_llm_client(self):
        for path in self._module_py_files():
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("llm_client", content, f"{path.name} must not import llm_client")

    def test_module_files_do_not_import_network_or_llm_libraries(self):
        for path in self._module_py_files():
            content = path.read_text(encoding="utf-8").lower()
            for forbidden in FORBIDDEN_NETWORK_OR_LLM_IMPORTS:
                pattern = rf"^\s*(import|from)\s+{re.escape(forbidden)}\b"
                self.assertIsNone(
                    re.search(pattern, content, re.MULTILINE),
                    f"{path.name} must not import '{forbidden}'"
                )

    def test_module_package_exists(self):
        self.assertTrue((MODULE_DIR / "__init__.py").exists())

    def test_workflow_engine_has_no_instagram_research_stage_wired_in(self):
        content = (REPO_ROOT / "src" / "workflow_engine.py").read_text(encoding="utf-8")
        self.assertNotIn("instagram_research", content)


if __name__ == "__main__":
    unittest.main()
