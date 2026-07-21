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

CONTENT_ID = "CN-ATTACK-TEST"

# Deterministic per-slide colors so each slide's PNG has a distinct,
# reproducible SHA-256.
_SLIDE_COLORS = {1: (10, 20, 30), 2: (40, 50, 60), 3: (70, 80, 90), 4: (100, 110, 120)}


def _now_iso(offset_seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def _make_png(path, color):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1080, 1080), color).save(path)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _valid_slides_payload(hashes):
    roles = ("hook", "problem", "solution", "cta")
    slides = []
    for index, role in zip(range(1, 5), roles):
        slide = {
            "slide_index": index,
            "role": role,
            "headline": f"approved headline {index}",
            "body": f"approved body {index}",
            "image_sha256": hashes[index],
            "cta_type": "",
            "cta_label": "",
        }
        if role == "cta":
            slide["cta_type"] = "save"
            slide["cta_label"] = "SAVE"
        slides.append(slide)
    return slides


class CopyIntakeReleaseRevisionTests(unittest.TestCase):
    """Attack + success tests for the Copy-Intake-driven
    WorkflowEngine.create_release_revision(content_id=...) path -- the fix
    for the CN-006 semantic false-ready incident."""

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

    def _run_fresh_transaction(self):
        class FakeCardNewsModule:
            def __init__(self):
                self.card_dir = Path("unused-before-call")

            def run(self, content_result, image_generation_result, image_strategy_result):
                self.card_dir.mkdir(parents=True, exist_ok=True)
                cards = []
                for index in range(1, 5):
                    path = self.card_dir / f"card_news_{index}.png"
                    _make_png(path, _SLIDE_COLORS[index])
                    cards.append({"index": index, "card_path": str(path), "status": "created"})
                return {
                    "module": "CardNewsModule",
                    "status": "card_news_completed",
                    "content_id": CONTENT_ID,
                    "cards": cards,
                    "card_news_quality": {
                        "passed": True,
                        "checks": {"unlicensed_asset_not_rendered": True, "attribution_needed": False},
                    },
                    "image_sourcing_status": {
                        "manual_image_required": False,
                        "real_image_used_count": 4,
                        "checklist": [],
                        "reason": "fixture",
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
        engine, output_set_id = self._run_fresh_transaction()
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
        return engine, output_set_id, card_paths

    def _write_copy_intake(self, card_paths, mutate=None):
        hashes = {i: _sha256(card_paths[i - 1]) for i in range(1, 5)}
        slides = _valid_slides_payload(hashes)
        payload = {
            "content_id": CONTENT_ID,
            "title": "The approved clean title",
            "operator_id": "content_ops_review",
            "approved_at": _now_iso(-60),
            "slides": slides,
        }
        if mutate is not None:
            mutate(payload)
        path = Path("storage/copy_intake") / f"{CONTENT_ID}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return hashes

    # ---------------------------------------------------------------
    # Success path
    # ---------------------------------------------------------------

    def test_success_builds_clean_set_with_matching_hashes_and_ready_state(self):
        engine, source_id = self._run_fresh_transaction()
        _, _, card_paths = engine, source_id, [
            f"storage/output_sets/card_news/sets/{source_id}/cards/card_news_{i}.png" for i in range(1, 5)
        ]
        # Re-derive fully-verified state (mirrors _fully_verified_active_set
        # without re-running the transaction).
        self._write_complete_rights_intake(source_id, card_paths)
        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            engine.reevaluate_active_set_compliance()
        source_hashes = self._write_copy_intake(card_paths)

        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            result = engine.create_release_revision(content_id=CONTENT_ID)

        self.assertNotEqual(result["new_output_set_id"], source_id)
        self.assertEqual(result["content_id"], CONTENT_ID)
        self.assertEqual(result["blocker_codes"], [])
        self.assertEqual(result["status"], "publishing_ready")
        self.assertTrue(result["publishing_ready"])
        self.assertTrue(result["package_ready"])
        self.assertFalse(result["actual_publish"])

        new_id = result["new_output_set_id"]
        new_dir = Path("storage/output_sets/card_news/sets") / new_id
        new_card_news = json.loads((new_dir / "08_card_news_result.json").read_text(encoding="utf-8"))
        self.assertEqual(new_card_news["title"], "The approved clean title")
        cards_by_index = {c["index"]: c for c in new_card_news["cards"]}
        self.assertEqual(cards_by_index[1]["headline"], "approved headline 1")
        self.assertEqual(cards_by_index[4]["cta_type"], "save")
        for index in range(1, 5):
            new_path = new_dir / f"cards/card_news_{index}.png"
            self.assertEqual(_sha256(new_path), source_hashes[index])

        new_publishing = json.loads((new_dir / "09_publishing_result.json").read_text(encoding="utf-8"))
        self.assertFalse(new_publishing["manual_image_required"])
        self.assertEqual(new_publishing["publish_queue"]["status"], "queue_ready")
        self.assertEqual(new_publishing["publish_queue"]["items"][0]["status"], "ready_for_manual_upload")
        self.assertEqual(new_publishing["operator_upload_package"]["status"], "ready_for_manual_upload")
        self.assertIn("The approved clean title", new_publishing["caption"])

        manifest = json.loads((new_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["release_ready"])
        self.assertFalse(manifest["actual_publish"])

        # Source set byte-for-byte untouched.
        source_dir = Path("storage/output_sets/card_news/sets") / source_id
        for index in range(1, 5):
            self.assertEqual(_sha256(source_dir / f"cards/card_news_{index}.png"), source_hashes[index])

    # ---------------------------------------------------------------
    # Attack scenarios -- all must refuse (raise) and create nothing new.
    # ---------------------------------------------------------------

    def _prepare_verified_source(self):
        engine, source_id, card_paths = self._fully_verified_active_set()
        return engine, source_id, card_paths

    def _assert_refused_and_no_new_set(self, engine, source_id, action):
        sets_dir = Path("storage/output_sets/card_news/sets")
        ids_before = set(p.name for p in sets_dir.iterdir())
        rights_intake_before = set(Path("storage/rights_intake").glob("*.json"))
        with self.assertRaises(ValueError):
            with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
                action()
        ids_after = set(p.name for p in sets_dir.iterdir())
        self.assertEqual(ids_before, ids_after)
        rights_intake_after = set(Path("storage/rights_intake").glob("*.json"))
        self.assertEqual(rights_intake_before, rights_intake_after)
        active = json.loads(Path("storage/output_sets/card_news/active.json").read_text(encoding="utf-8"))
        self.assertEqual(active["output_set_id"], source_id)

    def test_attack_no_copy_intake_file(self):
        engine, source_id, card_paths = self._prepare_verified_source()
        self._assert_refused_and_no_new_set(
            engine, source_id, lambda: engine.create_release_revision(content_id=CONTENT_ID)
        )

    def test_attack_correct_png_wrong_headline_banned_phrase(self):
        engine, source_id, card_paths = self._prepare_verified_source()

        def mutate(payload):
            payload["slides"][0]["headline"] = "요즘 다이어트 성공한 연예인들 특징"

        self._write_copy_intake(card_paths, mutate=mutate)
        self._assert_refused_and_no_new_set(
            engine, source_id, lambda: engine.create_release_revision(content_id=CONTENT_ID)
        )

    def test_attack_correct_headline_wrong_png_hash(self):
        engine, source_id, card_paths = self._prepare_verified_source()

        def mutate(payload):
            payload["slides"][0]["image_sha256"] = "b" * 64

        self._write_copy_intake(card_paths, mutate=mutate)
        self._assert_refused_and_no_new_set(
            engine, source_id, lambda: engine.create_release_revision(content_id=CONTENT_ID)
        )

    def test_attack_missing_copy_intake_fields(self):
        engine, source_id, card_paths = self._prepare_verified_source()

        def mutate(payload):
            del payload["slides"][2]["body"]

        self._write_copy_intake(card_paths, mutate=mutate)
        self._assert_refused_and_no_new_set(
            engine, source_id, lambda: engine.create_release_revision(content_id=CONTENT_ID)
        )

    def test_attack_wrong_role_order(self):
        engine, source_id, card_paths = self._prepare_verified_source()

        def mutate(payload):
            payload["slides"][1]["role"], payload["slides"][2]["role"] = (
                payload["slides"][2]["role"],
                payload["slides"][1]["role"],
            )

        self._write_copy_intake(card_paths, mutate=mutate)
        self._assert_refused_and_no_new_set(
            engine, source_id, lambda: engine.create_release_revision(content_id=CONTENT_ID)
        )

    def test_attack_content_id_mismatch_with_source(self):
        engine, source_id, card_paths = self._prepare_verified_source()
        self._write_copy_intake(card_paths)
        # Poison the source card_news_result with a DIFFERENT explicit
        # content_id than what's being requested.
        active = json.loads(Path("storage/output_sets/card_news/active.json").read_text(encoding="utf-8"))
        card_news_path = (
            Path("storage/output_sets/card_news/sets") / active["output_set_id"] / "08_card_news_result.json"
        )
        data = json.loads(card_news_path.read_text(encoding="utf-8"))
        data["content_id"] = "SOME-OTHER-CONTENT-ID"
        card_news_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        self._assert_refused_and_no_new_set(
            engine, source_id, lambda: engine.create_release_revision(content_id=CONTENT_ID)
        )

    def test_attack_source_output_set_id_mismatch(self):
        engine, source_id, card_paths = self._prepare_verified_source()
        self._write_copy_intake(card_paths)
        self._assert_refused_and_no_new_set(
            engine,
            source_id,
            lambda: engine.create_release_revision(
                source_output_set_id="not-the-real-id", content_id=CONTENT_ID
            ),
        )

    def test_attack_source_not_fully_verified_refuses_before_copy_intake(self):
        engine, source_id = self._run_fresh_transaction()  # never reevaluated -> still blocked
        card_paths = [
            f"storage/output_sets/card_news/sets/{source_id}/cards/card_news_{i}.png" for i in range(1, 5)
        ]
        self._write_copy_intake(card_paths)
        self._assert_refused_and_no_new_set(
            engine, source_id, lambda: engine.create_release_revision(content_id=CONTENT_ID)
        )

    def test_no_publish_queue_leaked_to_global_storage(self):
        engine, source_id, card_paths = self._prepare_verified_source()
        self._write_copy_intake(card_paths)
        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            engine.create_release_revision(content_id=CONTENT_ID)
        self.assertFalse(Path("storage/publishing/publish_queue.json").exists())


if __name__ == "__main__":
    unittest.main()
