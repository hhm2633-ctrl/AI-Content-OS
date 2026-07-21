import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.publishing.publishing_module import PublishingModule
from src.workflow_engine import WorkflowEngine
from tests._temp_cleanup import remove_temp_tree_with_retry

WORKSPACE_TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp_test_workspace"


def _now_iso(offset_seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def _make_png(path, color):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1080, 1080), color).save(path)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ReleaseRevisionTests(unittest.TestCase):
    """Attack + regression tests for WorkflowEngine.create_release_revision."""

    def setUp(self):
        self.previous_cwd = Path.cwd()
        WORKSPACE_TMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=WORKSPACE_TMP_ROOT))
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self.previous_cwd)
        remove_temp_tree_with_retry(self.root)

    def _write_bound_record(self, path, asset_id):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "asset_id": asset_id,
                    "type": "generation_record",
                    "publish_permission": "granted",
                    "rights_status": "generated",
                    "review_status": "approved",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _run_fresh_transaction(self, manual_image_required=True):
        class FakeCardNewsModule:
            def __init__(self):
                self.card_dir = Path("unused-before-call")

            def run(self, content_result, image_generation_result, image_strategy_result):
                self.card_dir.mkdir(parents=True, exist_ok=True)
                cards = []
                for index in range(1, 5):
                    path = self.card_dir / f"card_news_{index}.png"
                    _make_png(path, (index, 1, 1))
                    cards.append({"index": index, "card_path": str(path), "status": "created"})
                return {
                    "module": "CardNewsModule",
                    "status": "card_news_completed",
                    "cards": cards,
                    "card_news_quality": {
                        "passed": True,
                        "checks": {"unlicensed_asset_not_rendered": True, "attribution_needed": False},
                    },
                    "image_sourcing_status": {
                        "manual_image_required": manual_image_required,
                        "real_image_used_count": 0 if manual_image_required else 4,
                        "checklist": [],
                        "reason": "fallback used",
                    },
                }

        engine = WorkflowEngine.__new__(WorkflowEngine)
        engine.output_dir = Path("storage/workflow_results")
        engine.output_dir.mkdir(parents=True, exist_ok=True)
        engine.card_news_module = FakeCardNewsModule()
        engine.publishing_module = PublishingModule()
        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            engine._run_card_news_output_transaction(
                content_result={}, image_generation_result={}, image_strategy_result={},
            )
        active = json.loads(Path("storage/output_sets/card_news/active.json").read_text(encoding="utf-8"))
        return engine, active["output_set_id"]

    def _write_complete_rights_intake(self, output_set_id, card_paths):
        for index in range(1, 5):
            self._write_bound_record(Path(f"storage/rights_records/card_{index}_record.json"), f"card_{index}")
        cards = []
        for index in range(1, 5):
            cards.append(
                {
                    "card_index": index,
                    "card_path": card_paths[index - 1],
                    "origin": "first_party",
                    "role": "decorative",
                    "rights_status": "generated",
                    "rights_review_status": "approved",
                    "rights_reviewed_at": _now_iso(),
                    "reference_url": f"storage/rights_records/card_{index}_record.json",
                    "reference_verified": True,
                    "source_name": "Fully reviewed AI-generated illustration",
                    "evidence_captured_at": _now_iso(-10),
                    "evidence_reviewed_at": _now_iso(),
                    "topic_relevance": "Card illustrates the exact topic for this slide position.",
                    "authenticity_status": "verified",
                    "attribution_required": False,
                    "attribution_text": "",
                    "operator_checklist": {
                        "source_opened": True,
                        "rights_reviewed": True,
                        "claims_reviewed": True,
                        "attribution_reviewed": True,
                        "final_asset_reviewed": True,
                    },
                    "provenance": "ai_generated",
                }
            )
        payload = {
            "output_set_id": output_set_id,
            "operator_id": "test_operator",
            "operator_reviewed_at": _now_iso(),
            "is_advertising": False,
            "is_sponsored": False,
            "has_affiliate_link": False,
            "commercial_relationship_reviewed": True,
            "disclosures": [],
            "cards": cards,
        }
        path = Path("storage/rights_intake") / f"{output_set_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _fully_verified_active_set(self):
        """Produce a fresh committed set, then verify it via
        reevaluate_active_set_compliance so it reaches genuine
        publishing_ready/package_ready=True, blocker_codes=[] -- the only
        starting state create_release_revision is allowed to act on."""
        engine, output_set_id = self._run_fresh_transaction(manual_image_required=False)
        card_paths = [
            f"storage/output_sets/card_news/sets/{output_set_id}/cards/card_news_{i}.png"
            for i in range(1, 5)
        ]
        self._write_complete_rights_intake(output_set_id, card_paths)
        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            result = engine.reevaluate_active_set_compliance()
        self.assertEqual(result["blocker_codes"], [])
        self.assertTrue(result["publishing_ready"])
        self.assertTrue(result["package_ready"])
        return engine, output_set_id

    def test_creates_new_set_with_identical_hashes_and_publishing_ready(self):
        engine, source_id = self._fully_verified_active_set()
        source_dir = Path("storage/output_sets/card_news/sets") / source_id
        source_hashes = {i: _sha256(source_dir / f"cards/card_news_{i}.png") for i in range(1, 5)}
        source_card_news_before = json.loads((source_dir / "08_card_news_result.json").read_text(encoding="utf-8"))
        source_publishing_before = json.loads((source_dir / "09_publishing_result.json").read_text(encoding="utf-8"))

        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            result = engine.create_release_revision()

        self.assertNotEqual(result["new_output_set_id"], source_id)
        self.assertEqual(result["source_output_set_id"], source_id)
        self.assertEqual(result["blocker_codes"], [])
        self.assertEqual(result["status"], "publishing_ready")
        self.assertTrue(result["publishing_ready"])
        self.assertTrue(result["package_ready"])
        self.assertFalse(result["actual_publish"])

        # Source set must be byte-for-byte untouched.
        source_card_news_after = json.loads((source_dir / "08_card_news_result.json").read_text(encoding="utf-8"))
        source_publishing_after = json.loads((source_dir / "09_publishing_result.json").read_text(encoding="utf-8"))
        self.assertEqual(source_card_news_before, source_card_news_after)
        self.assertEqual(source_publishing_before, source_publishing_after)
        for i in range(1, 5):
            self.assertEqual(_sha256(source_dir / f"cards/card_news_{i}.png"), source_hashes[i])

        # New set must resolve and its 4 PNGs must match the source hashes.
        new_id = result["new_output_set_id"]
        new_dir = Path("storage/output_sets/card_news/sets") / new_id
        from modules.common.card_news_output_set import CardNewsOutputSetTransaction
        active = CardNewsOutputSetTransaction.resolve_active(Path("."))
        self.assertEqual(active["card_news_result"].parent, new_dir.resolve())
        for i in range(1, 5):
            new_path = new_dir / f"cards/card_news_{i}.png"
            self.assertTrue(new_path.is_file())
            with Image.open(new_path) as image:
                image.verify()
            with Image.open(new_path) as image:
                self.assertEqual(image.size, (1080, 1080))
            self.assertEqual(_sha256(new_path), source_hashes[i])

        new_publishing = json.loads((new_dir / "09_publishing_result.json").read_text(encoding="utf-8"))
        self.assertFalse(new_publishing["actual_publish"])
        self.assertEqual(new_publishing["status"], "publishing_ready")
        manifest = json.loads((new_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["release_ready"])
        self.assertFalse(manifest["actual_publish"])

        # No global publish queue anywhere; if a queue exists it must live
        # only inside the new immutable set.
        self.assertFalse(Path("storage/publishing/publish_queue.json").exists())

    def test_refuses_when_source_not_fully_verified(self):
        engine, source_id = self._run_fresh_transaction()  # never reevaluated -> still blocked
        rights_intake_before = Path(f"storage/rights_intake/{source_id}.json").exists()
        sets_dir = Path("storage/output_sets/card_news/sets")
        ids_before = set(p.name for p in sets_dir.iterdir())

        with self.assertRaises(ValueError):
            engine.create_release_revision()

        self.assertEqual(rights_intake_before, Path(f"storage/rights_intake/{source_id}.json").exists())
        ids_after = set(p.name for p in sets_dir.iterdir())
        self.assertEqual(ids_before, ids_after)

    def test_output_set_id_mismatch_guard_refuses_and_creates_nothing(self):
        engine, source_id = self._fully_verified_active_set()
        sets_dir = Path("storage/output_sets/card_news/sets")
        ids_before = set(p.name for p in sets_dir.iterdir())

        with self.assertRaises(ValueError):
            engine.create_release_revision(source_output_set_id="not-the-real-id")

        ids_after = set(p.name for p in sets_dir.iterdir())
        self.assertEqual(ids_before, ids_after)

    def test_missing_rights_intake_file_refuses(self):
        engine, source_id = self._fully_verified_active_set()
        Path(f"storage/rights_intake/{source_id}.json").unlink()
        sets_dir = Path("storage/output_sets/card_news/sets")
        ids_before = set(p.name for p in sets_dir.iterdir())

        with self.assertRaises(ValueError):
            engine.create_release_revision()

        ids_after = set(p.name for p in sets_dir.iterdir())
        self.assertEqual(ids_before, ids_after)

    def test_interrupted_promote_leaves_source_active(self):
        engine, source_id = self._fully_verified_active_set()
        real_replace = os.replace

        def fail_on_active_pointer(source, destination):
            if str(destination).endswith("active.json"):
                raise OSError("simulated interruption during active pointer write")
            return real_replace(source, destination)

        rights_intake_files_before = set(Path("storage/rights_intake").glob("*.json"))

        with patch("modules.common.card_news_output_set.os.replace", side_effect=fail_on_active_pointer):
            with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
                with self.assertRaises(OSError):
                    engine.create_release_revision()

        active = json.loads(Path("storage/output_sets/card_news/active.json").read_text(encoding="utf-8"))
        self.assertEqual(active["output_set_id"], source_id)

        from modules.common.card_news_output_set import CardNewsOutputSetTransaction
        resolved = CardNewsOutputSetTransaction.resolve_active(Path("."))
        self.assertEqual(resolved["card_news_result"].parent.name, source_id)

        # The half-created rights intake file for the never-committed new id
        # must be cleaned up by the exception handler, leaving only the
        # source's own rights intake file behind.
        rights_intake_files_after = set(Path("storage/rights_intake").glob("*.json"))
        self.assertEqual(rights_intake_files_before, rights_intake_files_after)

    def test_stale_receipt_and_old_new_mixed_attack_cannot_confuse_new_set(self):
        """After a successful release revision, the new rights intake file
        must be strictly bound to the new id/new committed paths -- it must
        never validate against the old id's card_news_result, and the old
        id's rights intake file must never validate against the new set's
        committed paths (no accidental old/new mixing)."""
        engine, source_id = self._fully_verified_active_set()
        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            result = engine.create_release_revision()
        new_id = result["new_output_set_id"]

        from modules.compliance.rights_intake_loader import load_verified_rights_intake

        new_card_news = json.loads(
            (Path("storage/output_sets/card_news/sets") / new_id / "08_card_news_result.json")
            .read_text(encoding="utf-8")
        )
        source_card_news = json.loads(
            (Path("storage/output_sets/card_news/sets") / source_id / "08_card_news_result.json")
            .read_text(encoding="utf-8")
        )

        # The OLD rights intake file, bound to the OLD committed paths, must
        # not validate when asked for the NEW id (wrong id) ...
        self.assertIsNone(load_verified_rights_intake(new_id, source_card_news))
        # ... nor when asked for the OLD id against the NEW card_news_result's
        # (different) committed paths.
        self.assertIsNone(load_verified_rights_intake(source_id, new_card_news))
        # The NEW rights intake file only validates for the NEW id with the
        # NEW card_news_result.
        self.assertIsNotNone(load_verified_rights_intake(new_id, new_card_news))

    def test_no_actual_publish_side_effects(self):
        engine, source_id = self._fully_verified_active_set()
        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            result = engine.create_release_revision()
        self.assertFalse(result["actual_publish"])
        new_id = result["new_output_set_id"]
        new_publishing = json.loads(
            (Path("storage/output_sets/card_news/sets") / new_id / "09_publishing_result.json")
            .read_text(encoding="utf-8")
        )
        self.assertFalse(new_publishing["actual_publish"])
        package = new_publishing.get("operator_upload_package")
        if isinstance(package, dict):
            self.assertFalse(package.get("actual_publish", False))


if __name__ == "__main__":
    unittest.main()
