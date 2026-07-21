import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.common.card_news_output_set import (
    CardNewsOutputSetTransaction,
    OutputSetValidationError,
)


class TestCardNewsOutputSetTransaction(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sources = self.root / "sources"
        self.sources.mkdir()
        self.paths = []
        for index in range(1, 5):
            path = self.sources / f"source_{index}.png"
            Image.new("RGB", (1080, 1080), (index, 2, 3)).save(path)
            self.paths.append(path.relative_to(self.root).as_posix())

    def tearDown(self):
        self.temp.cleanup()

    def payloads(self):
        card = {"status": "card_news_completed", "cards": [{"index": i, "card_path": path} for i, path in enumerate(self.paths, 1)]}
        quality = {"passed": True, "checks": {}}
        publishing = {
            "status": "publishing_ready",
            "card_paths": self.paths,
            "operator_upload_package": {"ordered_card_paths": self.paths},
        }
        return card, quality, publishing

    @staticmethod
    def rebind(publishing, committed_paths, output_set_id, queue_target):
        rebound = json.loads(json.dumps(publishing))
        rebound["output_set_id"] = output_set_id
        rebound["actual_publish"] = False
        rebound["card_paths"] = committed_paths
        rebound["operator_upload_package"]["output_set_id"] = output_set_id
        rebound["operator_upload_package"]["actual_publish"] = False
        rebound["operator_upload_package"]["ordered_card_paths"] = committed_paths
        if rebound.get("status") == "publishing_blocked":
            rebound["package_ready"] = False
            rebound.pop("publish_queue_path", None)
            rebound["operator_upload_package"].pop("publish_queue_path", None)
            return rebound
        queue = {
            "status": "queue_ready",
            "output_set_id": output_set_id,
            "actual_publish": False,
            "items": [{
                "output_set_id": output_set_id,
                "actual_publish": False,
                "card_paths": committed_paths,
            }],
        }
        queue_target.parent.mkdir(parents=True, exist_ok=True)
        queue_target.write_text(json.dumps(queue), encoding="utf-8")
        rebound["package_ready"] = True
        rebound["publish_queue"] = queue
        rebound["publish_queue_path"] = str(queue_target.resolve())
        rebound["operator_upload_package"]["publish_queue_path"] = str(queue_target.resolve())
        return rebound

    def complete(self, tx, payloads=None):
        tx.stage(*(payloads or self.payloads()))
        tx.rebind_publishing(self.rebind)
        return tx.promote()

    def test_promotes_complete_set_and_resolves_only_active_manifest(self):
        tx = CardNewsOutputSetTransaction(self.root, "run-001")
        manifest = self.complete(tx)
        resolved = CardNewsOutputSetTransaction.resolve_active(self.root)
        self.assertEqual(manifest["output_set_id"], "run-001")
        self.assertEqual(set(resolved), set(manifest["artifacts"]))
        self.assertTrue(all(path.is_file() for path in resolved.values()))
        publishing = json.loads(resolved["publishing"].read_text(encoding="utf-8"))
        self.assertEqual(
            publishing["operator_upload_package"]["ordered_card_paths"],
            manifest["card_paths"],
        )
        self.assertTrue(all((self.root / path).is_file() for path in manifest["card_paths"]))
        self.assertNotIn("/.runs/", json.dumps(publishing).replace("\\", "/"))
        self.assertFalse(manifest["actual_publish"])
        Image.new("RGB", (1080, 1080)).save(self.root / "latest.png")
        self.assertNotIn(self.root / "latest.png", resolved.values())

    def test_partial_mismatch_corrupt_and_wrong_size_fail_closed(self):
        cases = ("partial", "mismatch", "corrupt", "wrong_size")
        for case in cases:
            with self.subTest(case=case):
                tx = CardNewsOutputSetTransaction(self.root, f"run-{case}")
                card, quality, publishing = self.payloads()
                if case == "partial":
                    card["cards"] = card["cards"][:3]
                elif case == "mismatch":
                    card["cards"][1]["card_path"] = self.paths[0]
                elif case == "corrupt":
                    (self.root / self.paths[1]).write_bytes(b"broken")
                else:
                    Image.new("RGB", (1079, 1080)).save(self.root / self.paths[1])
                with self.assertRaises(OutputSetValidationError):
                    tx.stage(card, quality, publishing)
                self.assertFalse(tx.staging.exists())
                self.assertFalse(tx.active_pointer.exists())
                # Restore shared source for the next subtest.
                Image.new("RGB", (1080, 1080), (2, 2, 3)).save(self.root / self.paths[1])

    def test_allowed_canvas_sizes_are_accepted_and_arbitrary_size_fails(self):
        for size in ((1080, 1080), (1080, 1350), (1080, 1440)):
            with self.subTest(size=size):
                for index, relative_path in enumerate(self.paths, start=1):
                    Image.new("RGB", size, (index, 2, 3)).save(self.root / relative_path)
                tx = CardNewsOutputSetTransaction(
                    self.root,
                    f"canvas-{size[0]}-{size[1]}",
                )
                tx.stage(*self.payloads())
                self.assertTrue(tx.staging.is_dir())
                tx._discard_staging()

        Image.new("RGB", (800, 800), (2, 2, 3)).save(self.root / self.paths[1])
        with self.assertRaises(OutputSetValidationError):
            CardNewsOutputSetTransaction(self.root, "canvas-800-800").stage(
                *self.payloads()
            )

    def test_reversed_input_is_canonicalized_but_duplicate_or_extra_fails(self):
        card, quality, publishing = self.payloads()
        card["cards"].reverse()
        tx = CardNewsOutputSetTransaction(self.root, "reversed")
        self.complete(tx, (card, quality, publishing))
        saved = json.loads((tx.committed / "08_card_news_result.json").read_text(encoding="utf-8"))
        self.assertEqual([item["index"] for item in saved["cards"]], [1, 2, 3, 4])

        for mutation in ("duplicate", "extra"):
            card, quality, publishing = self.payloads()
            if mutation == "duplicate":
                card["cards"][3]["index"] = 3
            else:
                card["cards"].append({"index": 5, "card_path": self.paths[0]})
            with self.assertRaises(OutputSetValidationError):
                CardNewsOutputSetTransaction(self.root, mutation).stage(card, quality, publishing)

    def test_interruption_keeps_previous_active_set(self):
        first = CardNewsOutputSetTransaction(self.root, "first")
        self.complete(first)
        second = CardNewsOutputSetTransaction(self.root, "second")
        second.stage(*self.payloads())
        (second.staging / "card_news_quality.json").unlink()
        with self.assertRaises(OutputSetValidationError):
            second.promote()
        active = json.loads(first.active_pointer.read_text(encoding="utf-8"))
        self.assertEqual(active["output_set_id"], "first")

    def test_pointer_failure_rolls_back_new_commit_and_preserves_old_pointer(self):
        first = CardNewsOutputSetTransaction(self.root, "first")
        self.complete(first)
        second = CardNewsOutputSetTransaction(self.root, "second")
        second.stage(*self.payloads())
        second.rebind_publishing(self.rebind)
        original_replace = __import__("os").replace

        def fail_pointer(source, destination):
            if Path(destination) == second.active_pointer:
                raise OSError("simulated interruption")
            return original_replace(source, destination)

        with patch("modules.common.card_news_output_set.os.replace", side_effect=fail_pointer):
            with self.assertRaises(OSError):
                second.promote()
        self.assertFalse(second.committed.exists())
        self.assertEqual(json.loads(first.active_pointer.read_text(encoding="utf-8"))["output_set_id"], "first")

    def test_retry_is_idempotent(self):
        tx = CardNewsOutputSetTransaction(self.root, "same-run")
        first = self.complete(tx)
        second = tx.promote()
        self.assertEqual(first, second)
        self.assertEqual(CardNewsOutputSetTransaction.resolve_active(self.root)["quality"], tx.committed / "card_news_quality.json")

    def test_tampered_committed_set_is_never_resolved(self):
        tx = CardNewsOutputSetTransaction(self.root, "tampered")
        self.complete(tx)
        (tx.committed / "cards/card_news_3.png").write_bytes(b"corrupt")
        with self.assertRaises(OutputSetValidationError):
            CardNewsOutputSetTransaction.resolve_active(self.root)

    def test_complete_blocked_or_failed_qa_set_promotes_as_not_release_ready(self):
        for mode in ("publishing", "quality"):
            with self.subTest(mode=mode):
                card, quality, publishing = self.payloads()
                if mode == "publishing":
                    publishing["status"] = "publishing_blocked"
                else:
                    quality["passed"] = False
                    publishing["status"] = "publishing_blocked"
                tx = CardNewsOutputSetTransaction(self.root, f"blocked-{mode}")
                manifest = self.complete(tx, (card, quality, publishing))
                self.assertFalse(manifest["release_ready"])
                self.assertEqual(
                    json.loads(tx.active_pointer.read_text(encoding="utf-8"))["output_set_id"],
                    f"blocked-{mode}",
                )


if __name__ == "__main__":
    unittest.main()
