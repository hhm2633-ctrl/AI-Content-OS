import json
from pathlib import Path
import tempfile
import unittest

from modules.tool_adapters.publishing_reference_runtime import (
    PublishingReferenceRuntime,
    probe_publishing_references,
)


class PublishingReferenceRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.mixpost = base / "mixpost"
        self.trypost = base / "trypost"
        self._build_mixpost(self.mixpost)
        self._build_trypost(self.trypost)
        self.roots = {"mixpost": self.mixpost, "trypost": self.trypost}

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _common(root: Path, composer: dict, license_text: str) -> None:
        root.mkdir()
        (root / "composer.json").write_text(json.dumps(composer), encoding="utf-8")
        (root / "LICENSE.md").write_text(license_text, encoding="utf-8")
        (root / "vendor").mkdir()
        (root / "vendor" / "autoload.php").write_text("<?php", encoding="utf-8")

    def _build_mixpost(self, root: Path) -> None:
        composer = {
            "name": "inovector/mixpost",
            "version": "2.1.0",
            "homepage": "https://github.com/inovector/mixpost",
            "license": "MIT",
            "require": {"php": "^8.2"},
            "autoload": {"psr-4": {"Inovector\\Mixpost\\": "src"}},
        }
        self._common(root, composer, "The MIT License (MIT)\nMIT License")
        (root / "src" / "SocialProviders" / "Meta").mkdir(parents=True)
        (root / "src" / "SocialProviders" / "Twitter").mkdir()

    def _build_trypost(self, root: Path) -> None:
        composer = {
            "name": "trypost-it/trypost",
            "version": "1.4.2",
            "support": {"source": "https://github.com/trypost-it/trypost"},
            "license": "AGPL-3.0-only",
            "require": {"php": "^8.2", "laravel/framework": "^13.0"},
            "autoload": {"psr-4": {"App\\": "app/"}},
        }
        self._common(root, composer, "GNU AFFERO GENERAL PUBLIC LICENSE\nVersion 3")
        enum_path = root / "app" / "Enums" / "SocialAccount" / "Platform.php"
        enum_path.parent.mkdir(parents=True)
        enum_path.write_text(
            "<?php enum Platform: string { case Instagram = 'instagram'; case Threads = 'threads'; }",
            encoding="utf-8",
        )

    def test_complete_local_evidence_is_reference_ready(self):
        result = probe_publishing_references(self.roots)
        self.assertTrue(result["reference_ready"])
        self.assertEqual(result["status"], "reference_ready")
        self.assertEqual(result["projects"]["mixpost"]["social_platforms"]["platforms"], ["meta", "twitter"])
        self.assertEqual(result["projects"]["trypost"]["social_platforms"]["platforms"], ["instagram", "threads"])
        for project in result["projects"].values():
            self.assertTrue(project["boundaries"]["reference_only"])
            self.assertFalse(project["boundaries"]["application_execution"])
            self.assertFalse(project["boundaries"]["publishing"])

    def test_unversioned_composer_placeholder_fails_closed(self):
        composer = json.loads((self.mixpost / "composer.json").read_text(encoding="utf-8"))
        composer.pop("version")
        (self.mixpost / "composer.json").write_text(json.dumps(composer), encoding="utf-8")
        installed = self.mixpost / "vendor" / "composer" / "installed.php"
        installed.parent.mkdir()
        installed.write_text("<?php 'pretty_version' => '1.0.0+no-version-set';", encoding="utf-8")
        result = PublishingReferenceRuntime(self.roots).probe_project("mixpost")
        self.assertFalse(result["reference_ready"])
        self.assertEqual(result["version"]["reason"], "source_version_unpinned")
        self.assertIn("version_evidence_missing", result["errors"])

    def test_verified_source_provenance_pins_commit_without_composer_version(self):
        composer = json.loads((self.mixpost / "composer.json").read_text(encoding="utf-8"))
        composer.pop("version")
        (self.mixpost / "composer.json").write_text(json.dumps(composer), encoding="utf-8")
        provenance = {
            "schema_version": "publishing_reference_source_provenance_v1",
            "source_slug": "inovector/mixpost",
            "pinned_commit": "a" * 40,
            "archive": {"sha256": "b" * 64},
            "verification": {
                "tracked_file_count": 10,
                "source_files_match": True,
                "allowed_local_exceptions": [],
            },
            "reference_only": True,
        }
        (self.mixpost / "SOURCE_PROVENANCE.json").write_text(
            json.dumps(provenance), encoding="utf-8"
        )

        result = PublishingReferenceRuntime(self.roots).probe_project("mixpost")

        self.assertTrue(result["version"]["ready"])
        self.assertEqual(result["version"]["value"], "a" * 40)
        self.assertEqual(result["version"]["source"], "SOURCE_PROVENANCE.json")

    def test_invalid_source_provenance_fails_closed(self):
        composer = json.loads((self.mixpost / "composer.json").read_text(encoding="utf-8"))
        composer.pop("version")
        (self.mixpost / "composer.json").write_text(json.dumps(composer), encoding="utf-8")
        (self.mixpost / "SOURCE_PROVENANCE.json").write_text(
            json.dumps({"pinned_commit": "not-a-commit"}), encoding="utf-8"
        )

        result = PublishingReferenceRuntime(self.roots).probe_project("mixpost")

        self.assertFalse(result["version"]["ready"])
        self.assertEqual(result["version"]["reason"], "source_provenance_invalid")

    def test_license_requires_matching_declaration_and_root_text(self):
        (self.trypost / "LICENSE.md").write_text("MIT License", encoding="utf-8")
        result = PublishingReferenceRuntime(self.roots).probe_project("trypost")
        self.assertFalse(result["license"]["ready"])
        self.assertIn("license_evidence_missing", result["errors"])

    def test_autoload_requires_manifest_target_and_vendor_marker(self):
        (self.mixpost / "vendor" / "autoload.php").unlink()
        result = PublishingReferenceRuntime(self.roots).probe_project("mixpost")
        self.assertFalse(result["autoload"]["ready"])
        self.assertIn("autoload_evidence_missing", result["errors"])

    def test_platform_evidence_is_required(self):
        (self.trypost / "app" / "Enums" / "SocialAccount" / "Platform.php").unlink()
        result = PublishingReferenceRuntime(self.roots).probe_project("trypost")
        self.assertFalse(result["social_platforms"]["ready"])
        self.assertIn("social_platforms_evidence_missing", result["errors"])

    def test_identity_source_php_and_manifest_fail_closed(self):
        composer = json.loads((self.mixpost / "composer.json").read_text(encoding="utf-8"))
        composer["name"] = "someone/else"
        composer["homepage"] = "https://example.invalid/project"
        composer["require"].pop("php")
        (self.mixpost / "composer.json").write_text(json.dumps(composer), encoding="utf-8")
        result = PublishingReferenceRuntime(self.roots).probe_project("mixpost")
        self.assertFalse(result["reference_ready"])
        self.assertIn("identity_evidence_missing", result["errors"])
        self.assertIn("source_evidence_missing", result["errors"])
        self.assertIn("runtime_platform_evidence_missing", result["errors"])

        (self.mixpost / "composer.json").write_text("not-json", encoding="utf-8")
        result = PublishingReferenceRuntime(self.roots).probe_project("mixpost")
        self.assertFalse(result["reference_ready"])
        self.assertTrue(any(error.startswith("invalid:composer.json") for error in result["errors"]))

    def test_measurement_excludes_installed_dependency_trees(self):
        source_file = self.mixpost / "src" / "Reference.php"
        source_file.write_bytes(b"source")
        dependency = self.mixpost / "node_modules" / "large" / "bundle.js"
        dependency.parent.mkdir(parents=True)
        dependency.write_bytes(b"x" * 50_000)
        result = PublishingReferenceRuntime(self.roots).probe_project("mixpost")
        self.assertGreater(result["measurement"]["source_file_count"], 0)
        self.assertLess(result["measurement"]["source_bytes"], 50_000)

    def test_missing_root_and_unknown_project_are_blocked(self):
        runtime = PublishingReferenceRuntime({"mixpost": self.mixpost, "trypost": self.trypost / "missing"})
        self.assertEqual(runtime.probe_project("trypost")["errors"], ["reference_root_missing"])
        self.assertEqual(runtime.probe_project("postiz")["errors"], ["unsupported_project"])


if __name__ == "__main__":
    unittest.main()
