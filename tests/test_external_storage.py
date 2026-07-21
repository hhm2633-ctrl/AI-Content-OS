import json
import tempfile
import unittest
from pathlib import Path

from modules.common.external_storage import (
    resolve_external_path,
    resolve_external_storage,
)


class ExternalStorageResolverTests(unittest.TestCase):
    def _config(self, root: Path, **heavy_overrides: object) -> Path:
        config_dir = root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "source_data_root": str(root / "external"),
            "external_heavy_storage": {
                "enabled": True,
                "root": str(root / "external"),
                "fallback_root": "artifacts/fallback",
                "buckets": {
                    "source_data": "source_intake",
                    "card_news": "card_news",
                    "artifacts": "artifacts",
                },
                **heavy_overrides,
            },
        }
        path = config_dir / "source_data_storage.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_read_resolution_uses_external_bucket_without_creating_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = self._config(root)

            resolved = resolve_external_storage(
                "card_news", "output_sets", config_path=config_path
            )

            self.assertEqual(
                resolved.path, root / "external" / "card_news" / "output_sets"
            )
            self.assertFalse(resolved.fallback_used)
            self.assertFalse(resolved.path.exists())

    def test_create_makes_only_requested_external_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = self._config(root)

            resolved = resolve_external_path(
                "artifacts", "galleries", config_path=config_path, create=True
            )

            self.assertEqual(resolved, root / "external" / "artifacts" / "galleries")
            self.assertTrue(resolved.is_dir())
            self.assertFalse((root / "artifacts" / "fallback").exists())

    def test_disabled_external_storage_uses_repo_relative_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = self._config(root, enabled=False)

            resolved = resolve_external_storage(
                "source_data", "selected", config_path=config_path
            )

            self.assertEqual(
                resolved.path,
                root / "artifacts" / "fallback" / "source_intake" / "selected",
            )
            self.assertTrue(resolved.fallback_used)
            self.assertEqual(resolved.reason, "external_storage_disabled")
            self.assertFalse(resolved.path.exists())

    def test_unknown_bucket_and_parent_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = self._config(Path(temporary))
            with self.assertRaises(ValueError):
                resolve_external_path("unknown", config_path=config_path)
            with self.assertRaises(ValueError):
                resolve_external_path(
                    "artifacts", "../outside", config_path=config_path
                )


if __name__ == "__main__":
    unittest.main()
