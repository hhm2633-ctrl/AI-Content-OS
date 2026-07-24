import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from modules.common.card_news_output_set import CardNewsOutputSetTransaction
from modules.compliance.manual_image_intake_loader import (
    load_staged_manual_images,
    load_verified_manual_images,
)
from modules.publishing.publishing_module import PublishingModule
from src.workflow_engine import WorkflowEngine
from tests._temp_cleanup import remove_temp_tree_with_retry

# Workspace-local temp root (not the OS %TEMP% path) -- consistent with
# tests/test_card_news_rights_intake.py: avoids the Windows short/long path
# alias that used to break CardNewsPublishGate's repo-relative checks.
WORKSPACE_TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp_test_workspace"

OUTPUT_SET_ID = "manual-image-intake-test-0001"


def _now_iso(offset_seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def _valid_rights_record(**overrides):
    record = {
        "origin": "first_party",
        "role": "decorative",
        "rights_status": "owned",
        "rights_review_status": "approved",
        "rights_reviewed_at": _now_iso(),
        "reference_url": "https://example.com/evidence/manual-image",
        "reference_verified": True,
        "source_name": "Operator capture log",
        "evidence_captured_at": _now_iso(-10),
        "evidence_reviewed_at": _now_iso(),
        "topic_relevance": "Image directly illustrates the selected topic.",
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
    }
    record.update(overrides)
    return record


def _make_png(path, size=(1080, 1080), color=(1, 2, 3)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ManualImageIntakeLoaderTests(unittest.TestCase):
    """Unit tests for modules.compliance.manual_image_intake_loader (V2.0)."""

    def setUp(self):
        self.previous_cwd = Path.cwd()
        WORKSPACE_TMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=WORKSPACE_TMP_ROOT))
        os.chdir(self.root)
        Path("storage/manual_image_intake").mkdir(parents=True, exist_ok=True)
        Path("real_images").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        os.chdir(self.previous_cwd)
        remove_temp_tree_with_retry(self.root)

    def _write_intake(self, payload, output_set_id=OUTPUT_SET_ID):
        path = Path("storage/manual_image_intake") / f"{output_set_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _image_entry(self, index, image_path, **rights_overrides):
        return {
            "card_index": index,
            "image_path": image_path,
            "rights_record": _valid_rights_record(**rights_overrides),
        }

    def test_no_file_returns_empty(self):
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})

    def test_single_valid_image_is_accepted(self):
        _make_png(Path("real_images/card_1.png"))
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [self._image_entry(1, "real_images/card_1.png")],
            }
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(set(result), {1})
        self.assertEqual(result[1]["sha256"], _sha256("real_images/card_1.png"))
        self.assertIn("rights_record", result[1])

    def test_allowed_canvas_sizes_are_accepted_and_arbitrary_size_rejected(self):
        for size in ((1080, 1080), (1080, 1440)):
            with self.subTest(size=size):
                _make_png(Path("real_images/card_1.png"), size=size)
                self._write_intake(
                    {
                        "output_set_id": OUTPUT_SET_ID,
                        "images": [self._image_entry(1, "real_images/card_1.png")],
                    }
                )
                self.assertEqual(set(load_verified_manual_images(OUTPUT_SET_ID)), {1})

        _make_png(Path("real_images/card_1.png"), size=(800, 800))
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [self._image_entry(1, "real_images/card_1.png")],
            }
        )
        self.assertEqual(load_verified_manual_images(OUTPUT_SET_ID), {})

    def test_all_four_valid_images_are_accepted(self):
        for index in range(1, 5):
            _make_png(Path(f"real_images/card_{index}.png"), color=(index, 0, 0))
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [
                    self._image_entry(index, f"real_images/card_{index}.png")
                    for index in range(1, 5)
                ],
            }
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(set(result), {1, 2, 3, 4})

    def test_absolute_path_rejected(self):
        _make_png(Path("real_images/card_1.png"))
        absolute = str((self.root / "real_images/card_1.png").resolve())
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [self._image_entry(1, absolute)],
            }
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})

    def test_runs_path_rejected(self):
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [self._image_entry(1, ".runs/some-id/card_news/card_news_1.png")],
            }
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})

    def test_staging_path_rejected(self):
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [self._image_entry(1, ".staging/some-id/cards/card_news_1.png")],
            }
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})

    def test_corrupt_image_rejected(self):
        Path("real_images/card_1.png").write_bytes(b"not-a-real-png-file")
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [self._image_entry(1, "real_images/card_1.png")],
            }
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})

    def test_wrong_size_image_rejected(self):
        _make_png(Path("real_images/card_1.png"), size=(500, 500))
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [self._image_entry(1, "real_images/card_1.png")],
            }
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})

    def test_missing_rights_record_rejected(self):
        _make_png(Path("real_images/card_1.png"))
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [{"card_index": 1, "image_path": "real_images/card_1.png"}],
            }
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})

    def test_placeholder_rights_record_rejected(self):
        _make_png(Path("real_images/card_1.png"))
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [
                    self._image_entry(
                        1, "real_images/card_1.png",
                        reference_verified=False,
                    )
                ],
            }
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})

    def test_duplicate_card_index_rejected_for_both_entries(self):
        _make_png(Path("real_images/card_1a.png"), color=(9, 0, 0))
        _make_png(Path("real_images/card_1b.png"), color=(9, 9, 0))
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [
                    self._image_entry(1, "real_images/card_1a.png"),
                    self._image_entry(1, "real_images/card_1b.png"),
                ],
            }
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})

    def test_partial_coverage_applies_only_valid_entries(self):
        _make_png(Path("real_images/card_1.png"), color=(1, 0, 0))
        _make_png(Path("real_images/card_2.png"), color=(2, 0, 0))
        self._write_intake(
            {
                "output_set_id": OUTPUT_SET_ID,
                "images": [
                    self._image_entry(1, "real_images/card_1.png"),
                    self._image_entry(2, "real_images/card_2.png", reference_verified=False),
                ],
            }
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(set(result), {1})

    def test_output_set_id_mismatch_rejects_whole_file(self):
        _make_png(Path("real_images/card_1.png"))
        self._write_intake(
            {
                "output_set_id": "different-output-set-id",
                "images": [self._image_entry(1, "real_images/card_1.png")],
            },
            output_set_id=OUTPUT_SET_ID,
        )
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})

    def test_zero_images_rejected(self):
        self._write_intake({"output_set_id": OUTPUT_SET_ID, "images": []})
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})

    def test_more_than_twenty_images_rejected(self):
        entries = []
        for index in range(1, 22):
            _make_png(Path(f"real_images/card_{index}.png"), color=(index, 0, 0))
            entries.append(self._image_entry(index, f"real_images/card_{index}.png"))
        entries.append(self._image_entry(1, "real_images/card_1.png"))
        self._write_intake({"output_set_id": OUTPUT_SET_ID, "images": entries})
        result = load_verified_manual_images(OUTPUT_SET_ID)
        self.assertEqual(result, {})


class ManualImageIntakeWorkflowIntegrationTests(unittest.TestCase):
    """Confirms WorkflowEngine._apply_manual_image_intake and the end-to-end
    transaction preserve every V2.0 guarantee: fallback preserved with no
    intake file, real images committed with a validated intake, and
    actual_publish stays false regardless."""

    def setUp(self):
        self.previous_cwd = Path.cwd()
        WORKSPACE_TMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=WORKSPACE_TMP_ROOT))
        os.chdir(self.root)
        Path("storage/manual_image_intake").mkdir(parents=True, exist_ok=True)
        Path("real_images").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        os.chdir(self.previous_cwd)
        remove_temp_tree_with_retry(self.root)

    def _write_intake(self, images, output_set_id=OUTPUT_SET_ID):
        path = Path("storage/manual_image_intake") / f"{output_set_id}.json"
        path.write_text(
            json.dumps({"output_set_id": output_set_id, "images": images}, ensure_ascii=False),
            encoding="utf-8",
        )

    def _image_entry(self, index, image_path):
        return {
            "card_index": index,
            "image_path": image_path,
            "rights_record": _valid_rights_record(),
        }

    def _fresh_engine(self):
        engine = WorkflowEngine.__new__(WorkflowEngine)
        engine.output_dir = Path("storage/workflow_results")
        engine.output_dir.mkdir(parents=True, exist_ok=True)
        return engine

    def test_no_intake_leaves_fallback_cards_untouched(self):
        engine = self._fresh_engine()
        card_dir = Path("scratch/card_news")
        card_dir.mkdir(parents=True)
        fallback_hashes = {}
        cards = []
        for index in range(1, 5):
            path = card_dir / f"card_news_{index}.png"
            _make_png(path, color=(index, 5, 5))
            fallback_hashes[index] = _sha256(path)
            cards.append({"index": index, "card_path": str(path)})
        card_news_result = {
            "cards": cards,
            "image_sourcing_status": {"manual_image_required": True, "real_image_used_count": 0},
        }

        engine._apply_manual_image_intake(card_news_result, card_dir, OUTPUT_SET_ID)

        for index in range(1, 5):
            path = card_dir / f"card_news_{index}.png"
            self.assertEqual(_sha256(path), fallback_hashes[index])
        self.assertTrue(card_news_result["image_sourcing_status"]["manual_image_required"])
        self.assertEqual(card_news_result["image_sourcing_status"]["real_image_used_count"], 0)
        for card in card_news_result["cards"]:
            self.assertNotIn("image_source", card)

    def test_full_coverage_replaces_bytes_and_clears_manual_image_required(self):
        engine = self._fresh_engine()
        card_dir = Path("scratch/card_news")
        card_dir.mkdir(parents=True)
        cards = []
        for index in range(1, 5):
            path = card_dir / f"card_news_{index}.png"
            _make_png(path, color=(index, 5, 5))
            cards.append({"index": index, "card_path": str(path)})
        card_news_result = {
            "cards": cards,
            "image_sourcing_status": {"manual_image_required": True, "real_image_used_count": 0},
        }

        real_hashes = {}
        entries = []
        for index in range(1, 5):
            real_path = Path(f"real_images/card_{index}.png")
            _make_png(real_path, color=(index, 9, 9))
            real_hashes[index] = _sha256(real_path)
            entries.append(self._image_entry(index, str(real_path)))
        self._write_intake(entries)

        engine._apply_manual_image_intake(card_news_result, card_dir, OUTPUT_SET_ID)

        for index in range(1, 5):
            path = card_dir / f"card_news_{index}.png"
            self.assertEqual(_sha256(path), real_hashes[index])
        status = card_news_result["image_sourcing_status"]
        self.assertFalse(status["manual_image_required"])
        self.assertEqual(status["real_image_used_count"], 4)
        for card in card_news_result["cards"]:
            self.assertEqual(card["image_source"], "manual_intake")
            self.assertIn("image_sha256", card)
            self.assertIn("rights_record", card)

    def test_partial_coverage_keeps_manual_image_required_true(self):
        engine = self._fresh_engine()
        card_dir = Path("scratch/card_news")
        card_dir.mkdir(parents=True)
        cards = []
        for index in range(1, 5):
            path = card_dir / f"card_news_{index}.png"
            _make_png(path, color=(index, 5, 5))
            cards.append({"index": index, "card_path": str(path)})
        card_news_result = {
            "cards": cards,
            "image_sourcing_status": {"manual_image_required": True, "real_image_used_count": 0},
        }

        real_path = Path("real_images/card_1.png")
        _make_png(real_path, color=(1, 9, 9))
        self._write_intake([self._image_entry(1, str(real_path))])

        engine._apply_manual_image_intake(card_news_result, card_dir, OUTPUT_SET_ID)

        status = card_news_result["image_sourcing_status"]
        self.assertTrue(status["manual_image_required"])
        self.assertEqual(status["real_image_used_count"], 1)

    def test_end_to_end_transaction_commits_real_images_actual_publish_stays_false(self):
        """Full _run_card_news_output_transaction with a validated 4/4 manual
        image intake: the committed PNGs must match the operator-supplied
        images by hash, PUBLISH_MANUAL_IMAGE_REQUIRED must clear, but
        actual_publish/publishing_ready/package_ready must all stay false and
        rights/evidence blockers (unrelated to image sourcing, no V1.9 rights
        intake file provided here) must remain."""

        class FakeCardNewsModule:
            def __init__(self):
                self.card_dir = Path("unused-before-call")

            def run(self, content_result, image_generation_result, image_strategy_result):
                self.card_dir.mkdir(parents=True, exist_ok=True)
                cards = []
                for index in range(1, 5):
                    path = self.card_dir / f"card_news_{index}.png"
                    _make_png(path, color=(index, 1, 1))
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
                        "manual_image_required": True,
                        "real_image_used_count": 0,
                        "checklist": [],
                        "reason": "fallback used",
                    },
                }

        def fake_publishing_run(card_news_result):
            card_paths = [c["card_path"] for c in card_news_result["cards"]]
            image_status = card_news_result.get("image_sourcing_status", {})
            manual_required = bool(image_status.get("manual_image_required", False))
            real_count = int(image_status.get("real_image_used_count", 0) or 0)
            blocking_reasons = []
            if manual_required:
                blocking_reasons.append("manual_image_required")
            if real_count <= 0:
                blocking_reasons.append("real_image_used_count_zero")
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
                    "publishing_blocked": bool(blocking_reasons),
                    "blocking_reasons": blocking_reasons,
                    "real_image_used_count": real_count,
                },
            }

        engine = WorkflowEngine.__new__(WorkflowEngine)
        engine.output_dir = Path("storage/workflow_results")
        engine.output_dir.mkdir(parents=True, exist_ok=True)
        engine.card_news_module = FakeCardNewsModule()
        engine.publishing_module = PublishingModule()
        engine.publishing_module.run = fake_publishing_run

        # The output_set_id is normally a random uuid4().hex generated inside
        # CardNewsOutputSetTransaction.__init__; patch uuid.uuid4 there to a
        # fixed value so the intake file (keyed by output_set_id) can be
        # prepared before the transaction runs.
        real_hashes = {}
        entries = []
        for index in range(1, 5):
            real_path = Path(f"real_images/card_{index}.png")
            _make_png(real_path, color=(index, 8, 8))
            real_hashes[index] = _sha256(real_path)
            entries.append(
                {
                    "card_index": index,
                    "image_path": str(real_path),
                    "rights_record": _valid_rights_record(),
                }
            )
        Path("storage/manual_image_intake").mkdir(parents=True, exist_ok=True)
        Path(f"storage/manual_image_intake/{OUTPUT_SET_ID}.json").write_text(
            json.dumps({"output_set_id": OUTPUT_SET_ID, "images": entries}, ensure_ascii=False),
            encoding="utf-8",
        )

        with patch(
            "modules.common.card_news_output_set.uuid.uuid4",
            return_value=Mock(hex=OUTPUT_SET_ID),
        ), patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            card_news_result, publishing_result, manifest = engine._run_card_news_output_transaction(
                content_result={}, image_generation_result={}, image_strategy_result={},
            )

        self.assertEqual(manifest["output_set_id"], OUTPUT_SET_ID)
        for index in range(1, 5):
            committed_path = (
                Path("storage/output_sets/card_news/sets")
                / OUTPUT_SET_ID / "cards" / f"card_news_{index}.png"
            )
            self.assertEqual(_sha256(committed_path), real_hashes[index])
        for card in card_news_result["cards"]:
            self.assertEqual(card["image_source"], "manual_intake")

        # PUBLISH_MANUAL_IMAGE_REQUIRED can still appear here: the existing
        # (unmodified) transaction code forces operations["publishing_blocked"]
        # = True whenever overall readiness fails for *any* reason (rights and
        # evidence are still blocked in this test, since no V1.9 rights intake
        # was supplied), and manual_image_clear reads that same shared flag.
        # That coupling predates and is independent of V2.0 -- what V2.0 itself
        # controls is verified directly: with the corrected, uncoupled
        # operations dict this transaction actually produced pre-correction,
        # the image-sourcing gate alone is genuinely satisfied.
        self.assertEqual(card_news_result["image_sourcing_status"]["real_image_used_count"], 4)
        self.assertFalse(card_news_result["image_sourcing_status"]["manual_image_required"])
        clean_readiness = PublishingModule()._resolve_package_readiness(
            card_news_result,
            publishing_result["card_paths"],
            {"publishing_blocked": False},
        )
        self.assertTrue(clean_readiness["checks"]["manual_image_clear"])

        self.assertIn("PUBLISH_RIGHTS_BLOCKED", publishing_result["blocker_codes"])
        self.assertIn("PUBLISH_EVIDENCE_BLOCKED", publishing_result["blocker_codes"])
        self.assertFalse(publishing_result["actual_publish"])
        self.assertFalse(publishing_result["publishing_ready"])
        self.assertFalse(publishing_result["package_ready"])
        self.assertEqual(publishing_result["status"], "publishing_blocked")


CONTENT_ID = "TEST-CONTENT-STAGED-001"


class StagedManualImageIntakeLoaderTests(unittest.TestCase):
    """Unit tests for the content_id-keyed staged loader (not bound to any
    output_set_id, since none exists yet at staging time)."""

    def setUp(self):
        self.previous_cwd = Path.cwd()
        WORKSPACE_TMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=WORKSPACE_TMP_ROOT))
        os.chdir(self.root)
        Path("storage/manual_image_intake/staged").mkdir(parents=True, exist_ok=True)
        Path("real_images").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        os.chdir(self.previous_cwd)
        remove_temp_tree_with_retry(self.root)

    def _write_staged(self, images, content_id=CONTENT_ID):
        path = Path("storage/manual_image_intake/staged") / f"{content_id}.json"
        path.write_text(
            json.dumps({"content_id": content_id, "images": images}, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_no_staged_file_returns_empty(self):
        self.assertEqual(load_staged_manual_images(CONTENT_ID), {})

    def test_valid_staged_images_accepted_without_any_output_set_id(self):
        entries = []
        for index in range(1, 5):
            path = Path(f"real_images/slide_{index}.png")
            _make_png(path, color=(index, 4, 4))
            entries.append(
                {
                    "card_index": index,
                    "image_path": str(path),
                    "rights_record": _valid_rights_record(
                        origin="first_party", role="decorative", rights_status="generated",
                        provenance="ai_generated",
                    ),
                }
            )
        self._write_staged(entries)
        result = load_staged_manual_images(CONTENT_ID)
        self.assertEqual(set(result), {1, 2, 3, 4})
        for index in range(1, 5):
            self.assertEqual(result[index]["rights_record"]["provenance"], "ai_generated")

    def test_content_id_mismatch_rejected(self):
        self._write_staged(
            [
                {
                    "card_index": 1,
                    "image_path": "real_images/slide_1.png",
                    "rights_record": _valid_rights_record(),
                }
            ],
            content_id="a-different-content-id",
        )
        _make_png(Path("real_images/slide_1.png"))
        self.assertEqual(load_staged_manual_images(CONTENT_ID), {})


class StagedManualImageIntakeBindingTests(unittest.TestCase):
    """Integration tests for the two-stage flow: a real committed output set
    is created first (as an ordinary workflow run would), then staged CN-006-
    style images are bound onto it afterward via
    WorkflowEngine.apply_staged_manual_image_intake_to_active_set."""

    def setUp(self):
        self.previous_cwd = Path.cwd()
        WORKSPACE_TMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=WORKSPACE_TMP_ROOT))
        os.chdir(self.root)
        Path("storage/manual_image_intake/staged").mkdir(parents=True, exist_ok=True)
        Path("real_images").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        os.chdir(self.previous_cwd)
        remove_temp_tree_with_retry(self.root)

    def _stage_images(self, content_id=CONTENT_ID):
        real_hashes = {}
        entries = []
        for index in range(1, 5):
            path = Path(f"real_images/slide_{index}.png")
            _make_png(path, color=(index, 6, 6))
            real_hashes[index] = _sha256(path)
            entries.append(
                {
                    "card_index": index,
                    "image_path": str(path),
                    "rights_record": _valid_rights_record(
                        origin="first_party", role="decorative", rights_status="generated",
                        provenance="ai_generated",
                    ),
                }
            )
        Path(f"storage/manual_image_intake/staged/{content_id}.json").write_text(
            json.dumps({"content_id": content_id, "images": entries}, ensure_ascii=False),
            encoding="utf-8",
        )
        return real_hashes

    def _run_fresh_transaction(self):
        class FakeCardNewsModule:
            def __init__(self):
                self.card_dir = Path("unused-before-call")

            def run(self, content_result, image_generation_result, image_strategy_result):
                self.card_dir.mkdir(parents=True, exist_ok=True)
                cards = []
                for index in range(1, 5):
                    path = self.card_dir / f"card_news_{index}.png"
                    _make_png(path, color=(index, 1, 1))
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
                        "manual_image_required": True,
                        "real_image_used_count": 0,
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
        return engine

    def test_full_two_stage_flow_binds_staged_images_and_clears_manual_image_gate_only(self):
        engine = self._run_fresh_transaction()
        active_before = json.loads(Path("storage/output_sets/card_news/active.json").read_text(encoding="utf-8"))
        output_set_id = active_before["output_set_id"]
        committed_publishing_before = json.loads(
            (Path("storage/output_sets/card_news/sets") / output_set_id / "09_publishing_result.json")
            .read_text(encoding="utf-8")
        )
        self.assertIn("PUBLISH_MANUAL_IMAGE_REQUIRED", committed_publishing_before["blocker_codes"])
        self.assertIn("PUBLISH_RIGHTS_BLOCKED", committed_publishing_before["blocker_codes"])

        real_hashes = self._stage_images()

        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            result = engine.apply_staged_manual_image_intake_to_active_set(CONTENT_ID)

        self.assertTrue(result["applied"])
        self.assertEqual(result["output_set_id"], output_set_id)
        self.assertEqual(result["applied_count"], 4)

        committed_card = json.loads(
            (Path("storage/output_sets/card_news/sets") / output_set_id / "08_card_news_result.json")
            .read_text(encoding="utf-8")
        )
        for card in committed_card["cards"]:
            index = card["index"]
            committed_path = Path("storage/output_sets/card_news/sets") / output_set_id / "cards" / f"card_news_{index}.png"
            self.assertEqual(_sha256(committed_path), real_hashes[index])
            self.assertEqual(card["image_source"], "manual_intake")
            self.assertEqual(card["image_sha256"], real_hashes[index])
            self.assertEqual(card["rights_record"]["provenance"], "ai_generated")

        committed_publishing_after = json.loads(
            (Path("storage/output_sets/card_news/sets") / output_set_id / "09_publishing_result.json")
            .read_text(encoding="utf-8")
        )
        # The image-sourcing gate must clear now that all 4 slots are
        # genuinely covered by validated manual images...
        self.assertNotIn("PUBLISH_MANUAL_IMAGE_REQUIRED", committed_publishing_after["blocker_codes"])
        # ...but no other blocker may be touched: no V1.9 rights intake file
        # was ever provided for this output set, so rights/evidence/
        # compliance must remain exactly as blocked as before.
        self.assertIn("PUBLISH_RIGHTS_BLOCKED", committed_publishing_after["blocker_codes"])
        self.assertIn("PUBLISH_EVIDENCE_BLOCKED", committed_publishing_after["blocker_codes"])
        self.assertIn("PUBLISH_COMPLIANCE_BLOCKED", committed_publishing_after["blocker_codes"])
        self.assertFalse(committed_publishing_after["actual_publish"])
        self.assertFalse(committed_publishing_after["publishing_ready"])
        self.assertFalse(committed_publishing_after["package_ready"])

        legacy_publishing = json.loads(
            Path("storage/workflow_results/09_publishing_result.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("PUBLISH_MANUAL_IMAGE_REQUIRED", legacy_publishing["blocker_codes"])
        self.assertIn("PUBLISH_RIGHTS_BLOCKED", legacy_publishing["blocker_codes"])
        self.assertFalse(legacy_publishing["actual_publish"])

    def test_no_staged_intake_leaves_active_set_completely_untouched(self):
        engine = self._run_fresh_transaction()
        active = json.loads(Path("storage/output_sets/card_news/active.json").read_text(encoding="utf-8"))
        output_set_id = active["output_set_id"]
        card_dir = Path("storage/output_sets/card_news/sets") / output_set_id / "cards"
        before_hashes = {i: _sha256(card_dir / f"card_news_{i}.png") for i in range(1, 5)}
        before_publishing = json.loads(
            (Path("storage/output_sets/card_news/sets") / output_set_id / "09_publishing_result.json")
            .read_text(encoding="utf-8")
        )

        result = engine.apply_staged_manual_image_intake_to_active_set("no-such-content-id")

        self.assertFalse(result["applied"])
        for i in range(1, 5):
            self.assertEqual(_sha256(card_dir / f"card_news_{i}.png"), before_hashes[i])
        after_publishing = json.loads(
            (Path("storage/output_sets/card_news/sets") / output_set_id / "09_publishing_result.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(after_publishing, before_publishing)

    def test_output_set_id_mismatch_raises_and_leaves_active_set_untouched(self):
        engine = self._run_fresh_transaction()
        active = json.loads(Path("storage/output_sets/card_news/active.json").read_text(encoding="utf-8"))
        output_set_id = active["output_set_id"]
        card_dir = Path("storage/output_sets/card_news/sets") / output_set_id / "cards"
        before_hashes = {i: _sha256(card_dir / f"card_news_{i}.png") for i in range(1, 5)}

        self._stage_images()

        with self.assertRaises(ValueError):
            engine.apply_staged_manual_image_intake_to_active_set(
                CONTENT_ID, output_set_id="not-the-real-output-set-id",
            )

        for i in range(1, 5):
            self.assertEqual(_sha256(card_dir / f"card_news_{i}.png"), before_hashes[i])


if __name__ == "__main__":
    unittest.main()
