import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.card_news.card_news_module import CardNewsModule
from modules.common.card_news_output_set import CardNewsOutputSetTransaction
from modules.image_generation.image_generation_module import ImageGenerationModule


class CardNewsHeavyOutputRoutingTests(unittest.TestCase):
    @staticmethod
    def _write_storage_config(root: Path, external_root: Path) -> None:
        config_dir = root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "source_data_storage.json").write_text(
            json.dumps(
                {
                    "source_data_root": str(external_root),
                    "external_heavy_storage": {
                        "enabled": True,
                        "root": str(external_root),
                        "fallback_root": "artifacts/fallback",
                        "buckets": {"card_news": "card_news"},
                    },
                }
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _blocked_rebind(publishing, committed_paths, output_set_id, queue_target):
        rebound = json.loads(json.dumps(publishing))
        rebound["output_set_id"] = output_set_id
        rebound["actual_publish"] = False
        rebound["package_ready"] = False
        rebound["card_paths"] = committed_paths
        rebound["operator_upload_package"]["ordered_card_paths"] = committed_paths
        rebound["operator_upload_package"]["actual_publish"] = False
        return rebound

    def test_output_set_heavy_package_is_external_and_manifest_stays_in_repo(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            root.mkdir()
            external = base / "external"
            self._write_storage_config(root, external)
            sources = root / "sources"
            sources.mkdir()
            cards = []
            for index in range(1, 5):
                source = sources / f"source_{index}.png"
                Image.new("RGB", (1080, 1080), (index, 2, 3)).save(source)
                cards.append({"index": index, "card_path": source.relative_to(root).as_posix()})

            transaction = CardNewsOutputSetTransaction(root, "external-set")
            transaction.stage(
                {"status": "card_news_completed", "cards": cards},
                {"passed": True},
                {
                    "status": "publishing_blocked",
                    "card_paths": [card["card_path"] for card in cards],
                    "operator_upload_package": {
                        "ordered_card_paths": [card["card_path"] for card in cards]
                    },
                },
            )
            transaction.rebind_publishing(self._blocked_rebind)
            manifest = transaction.promote()

            self.assertEqual(
                transaction.store,
                (external / "card_news" / "output_sets").resolve(),
            )
            self.assertTrue(all(Path(path).is_absolute() for path in manifest["card_paths"]))
            self.assertTrue(all(Path(path).is_file() for path in manifest["card_paths"]))
            self.assertTrue(transaction.active_pointer.is_file())
            self.assertTrue(transaction.metadata_manifest.is_file())
            self.assertFalse(
                (root / "storage/output_sets/card_news/sets/external-set/cards").exists()
            )
            resolved = CardNewsOutputSetTransaction.resolve_active(root)
            self.assertTrue(all(path.is_file() for path in resolved.values()))

    def test_explicit_transaction_store_bypasses_configured_default(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            configured = root / "configured"
            explicit = root / "explicit-output-sets"
            self._write_storage_config(root, configured)
            transaction = CardNewsOutputSetTransaction(
                root, "explicit-set", heavy_store=explicit
            )
            self.assertEqual(transaction.store, explicit.resolve())
            self.assertFalse(configured.exists())

    def test_cardnews_default_is_created_only_when_writing_and_override_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "external" / "card_news" / "renders"

            def resolve(*args, **kwargs):
                if kwargs.get("create"):
                    target.mkdir(parents=True, exist_ok=True)
                return target

            with patch(
                "modules.card_news.card_news_module.resolve_external_path",
                side_effect=resolve,
            ):
                module = CardNewsModule({})
                self.assertFalse(target.exists())
                module._ensure_card_dir()
                self.assertEqual(module.card_dir, target)
                self.assertTrue(target.is_dir())

            explicit = Path(temporary) / "explicit-cards"
            module = CardNewsModule({"card_news_output_dir": str(explicit)})
            module._ensure_card_dir()
            self.assertEqual(module.card_dir, explicit)
            self.assertTrue(explicit.is_dir())

    def test_image_generation_default_is_lazy_and_override_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "external" / "card_news" / "generated_images"

            def resolve(*args, **kwargs):
                if kwargs.get("create"):
                    target.mkdir(parents=True, exist_ok=True)
                return target

            with patch("modules.image_generation.image_generation_module.OpenAI"), patch(
                "modules.image_generation.image_generation_module.resolve_external_path",
                side_effect=resolve,
            ):
                module = ImageGenerationModule({})
                self.assertFalse(target.exists())
                module._ensure_image_dir()
                self.assertEqual(module.image_dir, target)
                self.assertTrue(target.is_dir())

            explicit = Path(temporary) / "explicit-images"
            with patch("modules.image_generation.image_generation_module.OpenAI"):
                module = ImageGenerationModule(
                    {"image_generation_output_dir": str(explicit)}
                )
            module._ensure_image_dir()
            self.assertEqual(module.image_dir, explicit)
            self.assertTrue(explicit.is_dir())


if __name__ == "__main__":
    unittest.main()
