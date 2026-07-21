import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.common.card_news_output_set import CardNewsOutputSetTransaction
from modules.publishing.publishing_module import PublishingModule
from src.workflow_engine import WorkflowEngine


class WorkflowCardNewsReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.previous_cwd = Path.cwd()
        os.chdir(self.root)
        self.engine = WorkflowEngine.__new__(WorkflowEngine)
        self.engine.output_dir = Path("storage/workflow_results")
        self.engine.output_dir.mkdir(parents=True)
        Path("storage/card_news").mkdir(parents=True)
        self.active_dir = Path("active")
        self.active_dir.mkdir()
        self.active = {}
        payloads = {
            "card_news_result": {
                "status": "card_news_completed",
                "output_set_id": "new-set",
                "cards": [
                    {
                        "index": index,
                        "card_path": (
                            "storage/output_sets/card_news/sets/new-set/cards/"
                            f"card_news_{index}.png"
                        ),
                    }
                    for index in range(1, 5)
                ],
            },
            "publishing": {
                "status": "publishing_blocked",
                "output_set_id": "new-set",
                "publishing_ready": False,
                "actual_publish": False,
            },
            "quality": {"passed": True, "output_set_id": "new-set"},
        }
        for key, filename in (
            ("card_news_result", "08_card_news_result.json"),
            ("publishing", "09_publishing_result.json"),
            ("quality", "card_news_quality.json"),
        ):
            source = self.active_dir / filename
            source.write_text(json.dumps(payloads[key]), encoding="utf-8")
            self.active[key] = source.resolve()
        old_card = {"status": "card_news_completed", "output_set_id": "old-set"}
        legacy_card_without_id = {
            "status": "card_news_completed",
            "cards": [
                {
                    "index": index,
                    "card_path": f"storage/card_news/card_news_{index}.png",
                }
                for index in range(1, 5)
            ],
        }
        old_publish = {
            "status": "publishing_ready",
            "output_set_id": "old-set",
            "publishing_ready": True,
            "actual_publish": False,
            "publish_queue_path": "storage/publishing/publish_queue.json",
        }
        for destination, payload in (
            (Path("storage/workflow_results/05_card_news_result.json"), legacy_card_without_id),
            (Path("storage/workflow_results/07_card_news_result.json"), old_card),
            (Path("storage/workflow_results/08_card_news_result.json"), old_card),
            (Path("storage/workflow_results/06_publishing_result.json"), old_publish),
            (Path("storage/workflow_results/08_publishing_result.json"), old_publish),
            (Path("storage/workflow_results/09_publishing_result.json"), old_publish),
            (Path("storage/publishing/publishing_result.json"), old_publish),
            (Path("storage/outputs/publishing_result.json"), old_publish),
            (Path("storage/outputs/card_news_result.json"), old_card),
            (Path("storage/card_news/card_news_quality.json"), {"output_set_id": "old-set"}),
        ):
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(payload), encoding="utf-8")
        queue = Path("storage/publishing/publish_queue.json")
        queue.parent.mkdir(parents=True, exist_ok=True)
        queue.write_text(json.dumps({"output_set_id": "old-set"}), encoding="utf-8")
        Path("storage/workflow_results/final_result.json").write_text(
            json.dumps({"status": "publishing_ready"}),
            encoding="utf-8",
        )
        for index in range(1, 5):
            Path(f"storage/card_news/card_news_{index}.png").write_bytes(b"legacy")

    def tearDown(self):
        os.chdir(self.previous_cwd)
        self.temp.cleanup()

    def test_receipts_complete_before_loose_pngs_are_removed(self):
        self.engine._write_compatible_output_set_receipts(self.active)
        ids = {
            json.loads(path.read_text(encoding="utf-8"))["output_set_id"]
            for path in (
                Path("storage/workflow_results/05_card_news_result.json"),
                Path("storage/workflow_results/07_card_news_result.json"),
                Path("storage/workflow_results/08_card_news_result.json"),
                Path("storage/workflow_results/06_publishing_result.json"),
                Path("storage/workflow_results/08_publishing_result.json"),
                Path("storage/workflow_results/09_publishing_result.json"),
                Path("storage/publishing/publishing_result.json"),
                Path("storage/outputs/publishing_result.json"),
                Path("storage/outputs/card_news_result.json"),
                Path("storage/card_news/card_news_quality.json"),
            )
        }
        self.assertEqual(ids, {"new-set"})
        canonical_card = json.loads(
            Path("storage/workflow_results/08_card_news_result.json").read_text(
                encoding="utf-8"
            )
        )
        global_card_receipts = list(
            Path("storage/workflow_results").glob("*card_news_result.json")
        ) + [Path("storage/outputs/card_news_result.json")]
        self.assertTrue(global_card_receipts)
        for path in global_card_receipts:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("status") == "card_news_completed":
                self.assertEqual(payload.get("output_set_id"), "new-set")
                self.assertEqual(payload.get("cards"), canonical_card["cards"])
                self.assertFalse(
                    any(
                        item["card_path"].startswith("storage/card_news/")
                        for item in payload["cards"]
                    )
                )
        for path in (
            Path("storage/workflow_results/06_publishing_result.json"),
            Path("storage/workflow_results/08_publishing_result.json"),
            Path("storage/workflow_results/09_publishing_result.json"),
            Path("storage/publishing/publishing_result.json"),
            Path("storage/outputs/publishing_result.json"),
        ):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "publishing_blocked")
            self.assertFalse(payload["publishing_ready"])
            self.assertFalse(payload["actual_publish"])
            self.assertNotIn("publish_queue_path", payload)
        global_publish_receipts = list(
            Path("storage/workflow_results").glob("*publishing_result.json")
        ) + [
            Path("storage/publishing/publishing_result.json"),
            Path("storage/outputs/publishing_result.json"),
        ]
        self.assertTrue(global_publish_receipts)
        for path in global_publish_receipts:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["output_set_id"], "new-set")
            self.assertEqual(payload["status"], "publishing_blocked")
            self.assertFalse(payload["publishing_ready"])
            self.assertFalse(payload["actual_publish"])
            self.assertNotIn("publish_queue_path", payload)
        self.assertFalse(Path("storage/publishing/publish_queue.json").exists())
        legacy_final = json.loads(
            Path("storage/workflow_results/final_result.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(legacy_final["output_set_id"], "new-set")
        self.assertEqual(legacy_final["status"], "legacy_receipt_blocked")
        self.assertFalse(legacy_final["selectable"])
        self.assertFalse(legacy_final["publishing_ready"])
        self.assertFalse(legacy_final["actual_publish"])
        self.assertFalse(Path("storage/card_news/card_news_1.png").exists())

    def test_interrupted_receipt_update_has_no_missing_file_or_png_gap(self):
        real_replace = os.replace
        calls = 0

        def fail_on_second(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected receipt interruption")
            return real_replace(source, destination)

        with patch("src.workflow_engine.os.replace", side_effect=fail_on_second):
            with self.assertRaises(OSError):
                self.engine._write_compatible_output_set_receipts(self.active)

        receipt_paths = (
            Path("storage/workflow_results/05_card_news_result.json"),
            Path("storage/workflow_results/07_card_news_result.json"),
            Path("storage/workflow_results/08_card_news_result.json"),
            Path("storage/workflow_results/06_publishing_result.json"),
            Path("storage/workflow_results/08_publishing_result.json"),
            Path("storage/workflow_results/09_publishing_result.json"),
            Path("storage/publishing/publishing_result.json"),
            Path("storage/outputs/publishing_result.json"),
            Path("storage/outputs/card_news_result.json"),
            Path("storage/card_news/card_news_quality.json"),
        )
        self.assertTrue(all(path.is_file() for path in receipt_paths))
        self.assertTrue(all(Path(f"storage/card_news/card_news_{i}.png").is_file() for i in range(1, 5)))
        ids = [
            json.loads(path.read_text(encoding="utf-8")).get("output_set_id")
            for path in receipt_paths
        ]
        self.assertGreater(len(set(ids)), 1)
        self.assertFalse(Path("storage/publishing/publish_queue.json").exists())
        legacy_publish = json.loads(
            Path("storage/workflow_results/08_publishing_result.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(legacy_publish["publishing_ready"])
        self.assertEqual(legacy_publish["status"], "publishing_blocked")

    def test_concurrent_reader_never_sees_missing_receipt_or_false_ready_mix(self):
        receipt_paths = (
            Path("storage/workflow_results/05_card_news_result.json"),
            Path("storage/workflow_results/07_card_news_result.json"),
            Path("storage/workflow_results/08_card_news_result.json"),
            Path("storage/workflow_results/06_publishing_result.json"),
            Path("storage/workflow_results/08_publishing_result.json"),
            Path("storage/workflow_results/09_publishing_result.json"),
            Path("storage/publishing/publishing_result.json"),
            Path("storage/outputs/publishing_result.json"),
            Path("storage/outputs/card_news_result.json"),
            Path("storage/card_news/card_news_quality.json"),
        )
        observations = []
        missing_or_corrupt = []
        blocked_reads = []
        writing = threading.Event()
        finished = threading.Event()
        real_replace = os.replace

        def delayed_replace(source, destination):
            result = real_replace(source, destination)
            time.sleep(0.01)
            return result

        def reader():
            writing.wait()
            while not finished.is_set():
                try:
                    ids = tuple(
                        json.loads(path.read_text(encoding="utf-8")).get("output_set_id")
                        for path in receipt_paths
                    )
                    observations.append(ids)
                    time.sleep(0.001)
                except FileNotFoundError as error:
                    missing_or_corrupt.append(error)
                except json.JSONDecodeError as error:
                    missing_or_corrupt.append(error)
                except PermissionError as error:
                    blocked_reads.append(error)

        thread = threading.Thread(target=reader)
        thread.start()
        writing.set()
        try:
            with patch("src.workflow_engine.os.replace", side_effect=delayed_replace):
                self.engine._write_compatible_output_set_receipts(self.active)
        finally:
            finished.set()
            thread.join(timeout=1)

        self.assertFalse(missing_or_corrupt)
        self.assertTrue(all(path.is_file() for path in receipt_paths))
        self.assertTrue(observations)
        for ids in observations:
            receipt_set_ready = len(set(ids)) == 1
            if receipt_set_ready:
                self.assertIn(ids[0], {"old-set", "new-set"})
            else:
                self.assertGreater(len(set(ids)), 1)
        self.assertFalse(Path("storage/publishing/publish_queue.json").exists())

    def test_partial_generation_failure_leaves_no_run_scratch_and_no_mixed_state(self):
        """Mixed-generation attack: CardNews renders a real artifact into the
        run-scoped scratch directory, but Publishing fails before the transaction
        ever stages or commits anything. A crash after real rendering has begun
        must never leave an orphaned run directory, a half-created output set, or
        any change to the pre-existing legacy receipts -- old and new state must
        never mix."""

        class FakeCardNewsModule:
            def __init__(self):
                self.card_dir = Path("unused-before-call")

            def run(self, content_result, image_generation_result, image_strategy_result):
                # Simulate a real render: the run-scoped card_dir the engine just
                # assigned actually receives bytes before the downstream stage fails.
                self.card_dir.mkdir(parents=True, exist_ok=True)
                (self.card_dir / "card_news_1.png").write_bytes(b"rendered-but-never-committed")
                return {
                    "status": "card_news_completed",
                    "cards": [
                        {"index": i, "card_path": str(self.card_dir / f"card_news_{i}.png")}
                        for i in range(1, 5)
                    ],
                    "card_news_quality": {"passed": True, "checks": {}},
                }

        class FakePublishingModule:
            def __init__(self):
                self.publishing_dir = Path("unused-before-call")

            def run(self, card_news_result):
                raise RuntimeError("simulated publishing failure mid-generation")

        self.engine.card_news_module = FakeCardNewsModule()
        self.engine.publishing_module = FakePublishingModule()
        original_card_dir = self.engine.card_news_module.card_dir
        original_publishing_dir = self.engine.publishing_module.publishing_dir

        store = Path("storage/output_sets/card_news")
        pre_existing_receipt = json.loads(
            Path("storage/workflow_results/08_card_news_result.json").read_text(encoding="utf-8")
        )

        with self.assertRaises(RuntimeError):
            self.engine._run_card_news_output_transaction(
                content_result={}, image_generation_result={}, image_strategy_result={},
            )

        # card_dir/publishing_dir must be restored even though the downstream stage
        # raised -- the try/finally must not leave the engine's modules pointed at a
        # scratch directory that no longer exists.
        self.assertEqual(self.engine.card_news_module.card_dir, original_card_dir)
        self.assertEqual(self.engine.publishing_module.publishing_dir, original_publishing_dir)

        # No orphaned run-scoped scratch directory: the failure happened after a
        # real file was written into it, which is exactly the case that would leak
        # a half-generated artifact if cleanup were not unconditional.
        runs_dir = store / ".runs"
        self.assertEqual(list(runs_dir.iterdir()) if runs_dir.exists() else [], [])

        # Nothing was ever staged or committed -- the failure happened before
        # transaction.stage() was ever called, so no output set (complete or
        # partial) may exist.
        self.assertFalse((store / "sets").exists())
        self.assertFalse((store / "active.json").exists())

        # The legacy receipts already on disk (from setUp) must be untouched --
        # a mid-flight failure before staging must never overwrite them with
        # fragments of the failed attempt.
        self.assertEqual(
            json.loads(Path("storage/workflow_results/08_card_news_result.json").read_text(encoding="utf-8")),
            pre_existing_receipt,
        )

    def test_build_pre_publish_attestation_rejects_scratch_and_absolute_paths_but_accepts_committed_relative(self):
        """Locks the exact contract the V1.7 fix depends on: CardNewsPublishGate
        (invoked via _build_pre_publish_attestation) must reject an absolute,
        .runs-scoped path -- reproducing the original defect -- but must accept a
        real, existing, repo-relative committed-style path, producing exactly 4
        populated attestation cards with no final_cards_invalid blocker."""
        output_set_id = "contract-check-001"
        quality_result = {
            "passed": True,
            "checks": {"unlicensed_asset_not_rendered": True, "attribution_needed": False},
        }

        # Case 1: absolute .runs-scoped path (the pre-fix pipeline's shape) must be
        # rejected, leaving an empty attestation cards list.
        runs_dir = Path("storage/output_sets/card_news/.runs") / output_set_id / "card_news"
        runs_dir.mkdir(parents=True)
        absolute_cards = []
        for index in range(1, 5):
            path = runs_dir / f"card_news_{index}.png"
            Image.new("RGB", (1080, 1080), (index, 1, 1)).save(path)
            absolute_cards.append({"index": index, "card_path": str(path.resolve())})
        rejected_attestation = WorkflowEngine._build_pre_publish_attestation(
            {"cards": absolute_cards}, quality_result, output_set_id,
        )
        self.assertEqual(rejected_attestation["cards"], [])
        self.assertTrue(
            any(
                item.get("code") == "final_cards_invalid"
                for item in rejected_attestation["compliance_result"]["blocking_reasons"]
            )
        )

        # Case 2: real, existing, repo-relative committed-style path -- must be
        # accepted, populating exactly 4 cards, none referencing .runs/.staging/an
        # absolute location. CardNewsPublishGate resolves repo-relative paths
        # against its own hardcoded `_REPOSITORY_ROOT` module constant (not the
        # transaction's own repository_root parameter), so it must be patched to
        # this test's isolated temp root for the file-existence check to see the
        # fixture files created here -- this patches runtime state in our own test
        # file only; modules/compliance/card_news_publish_gate.py itself is never
        # touched.
        committed_dir = Path("storage/output_sets/card_news/sets") / output_set_id / "cards"
        committed_dir.mkdir(parents=True)
        committed_cards = []
        for index in range(1, 5):
            path = committed_dir / f"card_news_{index}.png"
            Image.new("RGB", (1080, 1080), (index, 2, 2)).save(path)
            committed_cards.append({"index": index, "card_path": path.as_posix()})
        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            accepted_attestation = WorkflowEngine._build_pre_publish_attestation(
                {"cards": committed_cards}, quality_result, output_set_id,
            )
        self.assertEqual(len(accepted_attestation["cards"]), 4)
        for card in accepted_attestation["cards"]:
            self.assertFalse(Path(card["path"]).is_absolute())
            self.assertNotIn(".runs", card["path"])
            self.assertNotIn(".staging", card["path"])
            self.assertEqual(card["output_set_id"], output_set_id)
        self.assertFalse(
            any(
                item.get("code") == "final_cards_invalid"
                for item in accepted_attestation["compliance_result"]["blocking_reasons"]
            )
        )

    def test_resolve_package_readiness_output_set_id_mismatch_fails_closed(self):
        """Even with otherwise-valid committed paths and a well-formed attestation,
        a mismatched output_set_id must still fail closed -- confirms the V1.7 fix
        does not weaken this guarantee."""
        output_set_id = "match-me"
        quality_result = {
            "passed": True,
            "checks": {"unlicensed_asset_not_rendered": True, "attribution_needed": False},
        }
        committed_dir = Path("storage/output_sets/card_news/sets") / output_set_id / "cards"
        committed_dir.mkdir(parents=True)
        cards = []
        for index in range(1, 5):
            path = committed_dir / f"card_news_{index}.png"
            Image.new("RGB", (1080, 1080), (index, 3, 3)).save(path)
            cards.append({"index": index, "card_path": path.as_posix()})
        attestation = WorkflowEngine._build_pre_publish_attestation(
            {"cards": cards}, quality_result, output_set_id,
        )
        card_news_result = {
            "output_set_id": "a-different-id",
            "cards": cards,
            "card_news_manifest": attestation,
        }
        publishing_module = PublishingModule()
        readiness = publishing_module._resolve_package_readiness(
            card_news_result,
            [c["card_path"] for c in cards],
            {"publishing_blocked": False},
        )
        self.assertFalse(readiness["ready"])
        self.assertIn("PUBLISH_OUTPUT_SET_MISMATCH", readiness["blocking_reasons"])

    def test_manifest_path_mismatch_resolved_after_commit_while_rights_blockers_persist(self):
        """End-to-end proof of the V1.7 fix. After a full stage/rebind/promote
        cycle, PUBLISH_MANIFEST_PATH_MISMATCH must be gone -- the attestation now
        references real, committed, repo-relative paths -- while
        PUBLISH_RIGHTS_BLOCKED, PUBLISH_EVIDENCE_BLOCKED,
        PUBLISH_MANUAL_IMAGE_REQUIRED, and the aggregate
        PUBLISH_COMMITTED_ATTESTATION_INVALID remain, and actual_publish /
        publishing_ready / package_ready stay false throughout. The correction must
        be visible both in the committed output-set files and in the mirrored
        legacy workflow_results receipts."""

        class FakeCardNewsModule:
            def __init__(self):
                self.card_dir = Path("unused-before-call")

            def run(self, content_result, image_generation_result, image_strategy_result):
                self.card_dir.mkdir(parents=True, exist_ok=True)
                cards = []
                for index in range(1, 5):
                    path = self.card_dir / f"card_news_{index}.png"
                    Image.new("RGB", (1080, 1080), (index, 5, 5)).save(path)
                    cards.append({"index": index, "card_path": str(path), "status": "created"})
                return {
                    "module": "CardNewsModule",
                    "status": "card_news_completed",
                    "cards": cards,
                    "card_news_quality": {
                        "passed": True,
                        "checks": {"unlicensed_asset_not_rendered": True, "attribution_needed": False},
                    },
                }

        def fake_publishing_run(card_news_result):
            card_paths = [c["card_path"] for c in card_news_result["cards"]]
            return {
                "module": "PublishingModule",
                "status": "publishing_blocked",
                "platform": "instagram",
                "upload_mode": "manual",
                "actual_publish": False,
                "card_paths": card_paths,
                "operator_upload_package": {
                    "status": "blocked", "platform": "instagram", "upload_mode": "manual",
                    "actual_publish": False, "ordered_card_paths": card_paths, "blocker_codes": [],
                },
                "operations": {
                    "publishing_blocked": True,
                    "blocking_reasons": ["manual_image_required"],
                    "real_image_used_count": 0,
                },
            }

        self.engine.card_news_module = FakeCardNewsModule()
        self.engine.publishing_module = PublishingModule()
        self.engine.publishing_module.run = fake_publishing_run

        # See the note in test_build_pre_publish_attestation_..._accepts_committed_
        # relative above: CardNewsPublishGate resolves repo-relative paths against
        # its own hardcoded _REPOSITORY_ROOT module constant, which must be patched
        # to this test's isolated temp root so the post-commit correction's
        # file-existence check can see the fixture files this test creates.
        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            card_news_result, publishing_result, manifest = self.engine._run_card_news_output_transaction(
                content_result={}, image_generation_result={}, image_strategy_result={},
            )

        attestation = card_news_result["card_news_manifest"]
        self.assertEqual(len(attestation["cards"]), 4)
        for card in attestation["cards"]:
            self.assertFalse(Path(card["path"]).is_absolute())
            self.assertNotIn(".runs", card["path"])
            self.assertNotIn(".staging", card["path"])
            self.assertEqual(card["output_set_id"], manifest["output_set_id"])

        self.assertNotIn("PUBLISH_MANIFEST_PATH_MISMATCH", publishing_result["blocker_codes"])
        self.assertIn("PUBLISH_RIGHTS_BLOCKED", publishing_result["blocker_codes"])
        self.assertIn("PUBLISH_EVIDENCE_BLOCKED", publishing_result["blocker_codes"])
        self.assertIn("PUBLISH_MANUAL_IMAGE_REQUIRED", publishing_result["blocker_codes"])
        self.assertIn("PUBLISH_COMMITTED_ATTESTATION_INVALID", publishing_result["blocker_codes"])

        self.assertTrue(publishing_result["readiness_checks"]["manifest_paths_match"])
        self.assertFalse(publishing_result["readiness_checks"]["rights_passed"])
        self.assertFalse(publishing_result["readiness_checks"]["evidence_passed"])

        self.assertFalse(publishing_result["actual_publish"])
        self.assertFalse(publishing_result["publishing_ready"])
        self.assertFalse(publishing_result["package_ready"])
        self.assertEqual(publishing_result["status"], "publishing_blocked")

        # The correction must be persisted into the actually-committed files, since
        # that is what _write_compatible_output_set_receipts mirrors afterward.
        committed_publishing = json.loads(
            (
                Path("storage/output_sets/card_news/sets")
                / manifest["output_set_id"]
                / "09_publishing_result.json"
            ).read_text(encoding="utf-8")
        )
        self.assertNotIn("PUBLISH_MANIFEST_PATH_MISMATCH", committed_publishing["blocker_codes"])
        self.assertEqual(len(committed_publishing["pre_publish_attestation"]["cards"]), 4)

        legacy_publishing = json.loads(
            Path("storage/workflow_results/09_publishing_result.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("PUBLISH_MANIFEST_PATH_MISMATCH", legacy_publishing["blocker_codes"])
        self.assertIn("PUBLISH_RIGHTS_BLOCKED", legacy_publishing["blocker_codes"])

    def test_commit_failure_after_staging_never_reaches_attestation_correction(self):
        """If the transaction fails while writing the active pointer (after
        CardNews has already rendered real files and staging/rebind succeeded),
        the post-commit attestation correction must never run: no output set may
        become active, and nothing may be left half-committed."""

        class FakeCardNewsModule:
            def __init__(self):
                self.card_dir = Path("unused-before-call")

            def run(self, content_result, image_generation_result, image_strategy_result):
                self.card_dir.mkdir(parents=True, exist_ok=True)
                cards = []
                for index in range(1, 5):
                    path = self.card_dir / f"card_news_{index}.png"
                    Image.new("RGB", (1080, 1080), (index, 7, 7)).save(path)
                    cards.append({"index": index, "card_path": str(path), "status": "created"})
                return {
                    "module": "CardNewsModule",
                    "status": "card_news_completed",
                    "cards": cards,
                    "card_news_quality": {
                        "passed": True,
                        "checks": {"unlicensed_asset_not_rendered": True, "attribution_needed": False},
                    },
                }

        def fake_publishing_run(card_news_result):
            card_paths = [c["card_path"] for c in card_news_result["cards"]]
            return {
                "module": "PublishingModule",
                "status": "publishing_blocked",
                "platform": "instagram",
                "upload_mode": "manual",
                "actual_publish": False,
                "card_paths": card_paths,
                "operator_upload_package": {
                    "status": "blocked", "platform": "instagram", "upload_mode": "manual",
                    "actual_publish": False, "ordered_card_paths": card_paths, "blocker_codes": [],
                },
                "operations": {
                    "publishing_blocked": True,
                    "blocking_reasons": ["manual_image_required"],
                    "real_image_used_count": 0,
                },
            }

        self.engine.card_news_module = FakeCardNewsModule()
        self.engine.publishing_module = PublishingModule()
        self.engine.publishing_module.run = fake_publishing_run

        real_replace = os.replace

        def fail_on_active_pointer(source, destination):
            if str(destination).endswith("active.json"):
                raise OSError("simulated interruption during active pointer write")
            return real_replace(source, destination)

        with patch("modules.common.card_news_output_set.os.replace", side_effect=fail_on_active_pointer):
            with self.assertRaises(OSError):
                self.engine._run_card_news_output_transaction(
                    content_result={}, image_generation_result={}, image_strategy_result={},
                )

        self.assertFalse(Path("storage/output_sets/card_news/active.json").exists())
        sets_dir = Path("storage/output_sets/card_news/sets")
        self.assertEqual(list(sets_dir.iterdir()) if sets_dir.exists() else [], [])

    def test_compliance_blocked_attestation_never_exposes_outer_pass(self):
        cards = []
        for index in range(1, 5):
            path = Path(f"card_{index}.png")
            Image.new("RGB", (1080, 1080), (index, 2, 3)).save(path)
            cards.append({"index": index, "card_path": path.as_posix()})
        attestation = WorkflowEngine._build_pre_publish_attestation(
            {"cards": cards},
            {
                "passed": True,
                "checks": {
                    "unlicensed_asset_not_rendered": True,
                    "attribution_needed": False,
                    "evidence_available": False,
                },
            },
            "blocked-set",
        )
        self.assertEqual(attestation["rights"]["status"], "blocked")
        self.assertEqual(attestation["evidence"]["status"], "blocked")
        self.assertFalse(attestation["release_guard"]["ready"])
        self.assertEqual(attestation["render_allowed_asset_ids"], [])


if __name__ == "__main__":
    unittest.main()
