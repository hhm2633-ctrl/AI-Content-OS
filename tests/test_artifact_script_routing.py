import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"test_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ArtifactScriptRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prototypes = load_script("render_cardnews_prototypes")
        cls.motion = load_script("render_no_video_motion_samples")
        cls.packages = load_script("build_category_publish_packages")

    def test_prototype_defaults_use_external_artifact_root(self):
        external = Path("F:/test-heavy/artifacts/cardnews_prototypes/2026-07-16")
        with patch.object(self.prototypes, "resolve_external_path", return_value=external) as resolver:
            root, output = self.prototypes.resolve_cli_paths(
                self.prototypes.parse_args([])
            )

        self.assertEqual(root, external)
        self.assertEqual(output, external / "previews")
        resolver.assert_called_once_with(
            "artifacts",
            "cardnews_prototypes",
            "2026-07-16",
            config_path=self.prototypes.STORAGE_CONFIG,
        )

    def test_prototype_explicit_paths_are_preserved(self):
        explicit_root = Path("C:/owner/input")
        explicit_output = Path("C:/owner/output")
        with patch.object(
            self.prototypes, "resolve_external_path", side_effect=AssertionError
        ):
            args = self.prototypes.parse_args(
                ["--root", str(explicit_root), "--output-root", str(explicit_output)]
            )
            root, output = self.prototypes.resolve_cli_paths(args)

        self.assertEqual(root, explicit_root)
        self.assertEqual(output, explicit_output)

    def test_motion_default_and_explicit_output_routing(self):
        external = Path("F:/test-heavy/artifacts/cardnews_motion_samples/no_source_video")
        with patch.object(self.motion, "resolve_external_path", return_value=external) as resolver:
            self.assertEqual(self.motion.resolve_output_root(None), external)
        resolver.assert_called_once_with(
            "artifacts",
            "cardnews_motion_samples",
            "no_source_video",
            config_path=self.motion.STORAGE_CONFIG,
        )

        explicit = Path("C:/owner/motion")
        with patch.object(self.motion, "resolve_external_path", side_effect=AssertionError):
            self.assertEqual(self.motion.resolve_output_root(explicit), explicit)

    def test_publish_package_default_and_explicit_output_routing(self):
        external = Path("F:/test-heavy/artifacts/publish_packages")
        with patch.object(self.packages, "resolve_external_path", return_value=external) as resolver:
            self.assertEqual(self.packages.resolve_output_root(None), external)
        resolver.assert_called_once_with(
            "artifacts", "publish_packages", config_path=self.packages.STORAGE_CONFIG
        )

        explicit = Path("C:/owner/packages")
        with patch.object(self.packages, "resolve_external_path", side_effect=AssertionError):
            self.assertEqual(self.packages.resolve_output_root(explicit), explicit)


if __name__ == "__main__":
    unittest.main()
