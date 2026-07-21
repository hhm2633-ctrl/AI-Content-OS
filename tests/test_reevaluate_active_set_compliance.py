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

# Workspace-local temp root (not the OS %TEMP% path) -- consistent with the
# rest of this Rights Intake / Manual Image Intake test suite: avoids the
# Windows short/long path alias that used to break CardNewsPublishGate's
# repo-relative checks.
WORKSPACE_TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp_test_workspace"


def _now_iso(offset_seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def _make_png(path, color):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1080, 1080), color).save(path)


class ReevaluateActiveSetComplianceTests(unittest.TestCase):
    """WorkflowEngine.reevaluate_active_set_compliance: re-runs Rights/
    Compliance/Attestation for an already-committed active set without
    hand-editing blocker_codes, using only the real, unmodified
    CardNewsPublishGate / PublishingModule logic."""

    def setUp(self):
        self.previous_cwd = Path.cwd()
        WORKSPACE_TMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=WORKSPACE_TMP_ROOT))
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self.previous_cwd)
        remove_temp_tree_with_retry(self.root)

    def _run_fresh_transaction(self):
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
        active = json.loads(Path("storage/output_sets/card_news/active.json").read_text(encoding="utf-8"))
        return engine, active["output_set_id"]

    def _committed_publishing(self, output_set_id):
        return json.loads(
            (Path("storage/output_sets/card_news/sets") / output_set_id / "09_publishing_result.json")
            .read_text(encoding="utf-8")
        )

    def _write_bound_record(self, path, asset_id, rights_status="generated"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "asset_id": asset_id,
                    "type": "generation_record",
                    "publish_permission": "granted",
                    "rights_status": rights_status,
                    "review_status": "approved",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _write_complete_rights_intake(self, output_set_id, card_paths):
        for index in range(1, 5):
            self._write_bound_record(
                Path(f"storage/rights_records/card_{index}_record.json"), f"card_{index}",
            )
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

    def _write_scope_limited_rights_intake(self, output_set_id, card_paths):
        """Mirrors the real CN-006 approval: only 2 of the 5 operator
        checklist items are honestly true, the rest stay false."""
        for index in range(1, 5):
            self._write_bound_record(
                Path(f"storage/rights_records/card_{index}_record.json"), f"card_{index}",
            )
        cards = []
        for index in range(1, 5):
            cards.append(
                {
                    "card_index": index,
                    "card_path": card_paths[index - 1],
                    "origin": "first_party",
                    "role": "decorative",
                    "rights_status": "generated",
                    "rights_review_status": "partially_approved_scope_limited",
                    "rights_reviewed_at": _now_iso(),
                    "reference_url": f"storage/rights_records/card_{index}_record.json",
                    "reference_verified": False,
                    "source_name": "Single blanket approval sentence, scope-limited",
                    "evidence_captured_at": _now_iso(-10),
                    "evidence_reviewed_at": _now_iso(),
                    "topic_relevance": "Card illustrates the exact topic for this slide position.",
                    "authenticity_status": "pending_operator_confirmation",
                    "attribution_required": False,
                    "attribution_text": "",
                    "operator_checklist": {
                        "source_opened": True,
                        "rights_reviewed": True,
                        "claims_reviewed": False,
                        "attribution_reviewed": False,
                        "final_asset_reviewed": False,
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

    def test_no_rights_intake_leaves_blockers_unchanged(self):
        engine, output_set_id = self._run_fresh_transaction()
        before = self._committed_publishing(output_set_id)

        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            result = engine.reevaluate_active_set_compliance()

        after = self._committed_publishing(output_set_id)
        self.assertEqual(result["blocker_codes"], before["blocker_codes"])
        self.assertIn("PUBLISH_RIGHTS_BLOCKED", after["blocker_codes"])
        self.assertIn("PUBLISH_EVIDENCE_BLOCKED", after["blocker_codes"])
        self.assertFalse(result["actual_publish"])

    def test_complete_valid_rights_intake_clears_rights_evidence_compliance(self):
        engine, output_set_id = self._run_fresh_transaction()
        card_paths = [
            f"storage/output_sets/card_news/sets/{output_set_id}/cards/card_news_{i}.png"
            for i in range(1, 5)
        ]
        self._write_complete_rights_intake(output_set_id, card_paths)

        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            result = engine.reevaluate_active_set_compliance()

        self.assertNotIn("PUBLISH_RIGHTS_BLOCKED", result["blocker_codes"])
        self.assertNotIn("PUBLISH_EVIDENCE_BLOCKED", result["blocker_codes"])
        self.assertNotIn("PUBLISH_COMPLIANCE_BLOCKED", result["blocker_codes"])
        self.assertFalse(result["actual_publish"])
        self.assertFalse(result["publishing_ready"])
        self.assertFalse(result["package_ready"])

    def test_scope_limited_single_sentence_approval_keeps_blockers_fail_closed(self):
        """Reproduces the real CN-006 scenario: one blanket approval sentence
        cannot honestly satisfy all five itemized operator checklist entries,
        so the whole rights intake must be treated as incomplete -- not
        partially applied -- and every rights/evidence/compliance blocker
        must remain exactly as it was."""
        engine, output_set_id = self._run_fresh_transaction()
        before = self._committed_publishing(output_set_id)
        card_paths = [
            f"storage/output_sets/card_news/sets/{output_set_id}/cards/card_news_{i}.png"
            for i in range(1, 5)
        ]
        self._write_scope_limited_rights_intake(output_set_id, card_paths)

        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            result = engine.reevaluate_active_set_compliance()

        self.assertEqual(set(result["blocker_codes"]), set(before["blocker_codes"]))
        self.assertIn("PUBLISH_RIGHTS_BLOCKED", result["blocker_codes"])
        self.assertIn("PUBLISH_EVIDENCE_BLOCKED", result["blocker_codes"])
        self.assertIn("PUBLISH_COMPLIANCE_BLOCKED", result["blocker_codes"])
        self.assertFalse(result["actual_publish"])

    def test_output_set_id_mismatch_raises_and_leaves_active_set_untouched(self):
        engine, output_set_id = self._run_fresh_transaction()
        before = self._committed_publishing(output_set_id)

        with self.assertRaises(ValueError):
            engine.reevaluate_active_set_compliance(output_set_id="not-the-real-id")

        after = self._committed_publishing(output_set_id)
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
