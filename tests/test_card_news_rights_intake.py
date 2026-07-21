import hashlib
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.compliance.card_news_publish_gate import CardNewsPublishGate
from modules.compliance.rights_intake_loader import load_verified_rights_intake
from modules.publishing.publishing_module import PublishingModule
from src.workflow_engine import WorkflowEngine

# Historically this module used a dedicated chdir temp root. Environment ACL
# restrictions make that unstable, so tests now remain in the real repo root
# and clean only per-test fixtures deterministically.

OUTPUT_SET_ID = "test-output-set-id-0001"
CARD_PATHS = [
    f"storage/output_sets/card_news/sets/{OUTPUT_SET_ID}/cards/card_news_{index}.png"
    for index in range(1, 5)
]


def _now_iso(offset_seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def _card_news_result(card_paths=CARD_PATHS):
    return {"cards": [{"index": i + 1, "card_path": path} for i, path in enumerate(card_paths)]}


def _valid_card(index, card_path, **overrides):
    card = {
        "card_index": index,
        "card_path": card_path,
        "origin": "first_party",
        "role": "decorative",
        "rights_status": "owned",
        "rights_review_status": "approved",
        "rights_reviewed_at": _now_iso(),
        "reference_url": "https://example.com/evidence/card",
        "reference_verified": True,
        "source_name": "Operator capture log",
        "evidence_captured_at": _now_iso(-10),
        "evidence_reviewed_at": _now_iso(),
        "topic_relevance": "Card directly illustrates the selected topic.",
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
    card.update(overrides)
    return card


def _valid_file(card_paths=CARD_PATHS, output_set_id=OUTPUT_SET_ID, card_overrides=None):
    card_overrides = card_overrides or {}
    return {
        "output_set_id": output_set_id,
        "operator_id": "operator_han",
        "operator_reviewed_at": _now_iso(),
        "is_advertising": False,
        "is_sponsored": False,
        "has_affiliate_link": False,
        "commercial_relationship_reviewed": True,
        "disclosures": [],
        "cards": [
            _valid_card(i + 1, path, **card_overrides.get(i + 1, {}))
            for i, path in enumerate(card_paths)
        ],
    }


class RightsIntakeLoaderTests(unittest.TestCase):
    """Unit tests for modules.compliance.rights_intake_loader (V1.9)."""

    def setUp(self):
        self.previous_cwd = Path.cwd()
        self.root = self.previous_cwd
        (self.root / "storage" / "rights_intake").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        # Never rmtree the shared storage/rights_intake directory: it is a
        # real, shared production location (this suite runs against the
        # actual repo root, not an isolated temp dir) and a rival active
        # output set's genuine rights intake file could exist alongside this
        # test's own fixture. Only ever remove exactly the files this test
        # itself may have written.
        for output_set_id in (OUTPUT_SET_ID, "old-output-set-id-0000", "different-output-set-id"):
            path = self.root / "storage" / "rights_intake" / f"{output_set_id}.json"
            if path.exists():
                path.unlink()
        output_set_dir = self.root / "storage" / "output_sets" / "card_news" / "sets" / OUTPUT_SET_ID
        shutil.rmtree(output_set_dir, ignore_errors=True)

    def _write_intake(self, payload, output_set_id=OUTPUT_SET_ID):
        path = Path("storage/rights_intake") / f"{output_set_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_no_file_returns_none(self):
        result = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(result)

    def test_normal_format_is_accepted(self):
        self._write_intake(_valid_file())
        result = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result["assets"]), 4)
        self.assertEqual(len(result["evidence"]), 4)
        self.assertTrue(all(item["classification"] == "publishable_asset" for item in result["assets"]))
        self.assertTrue(all(result["operator_checklist"]["checks"].values()))
        self.assertTrue(result["campaign"]["commercial_relationship_reviewed"])

    def test_missing_required_field_keeps_blocked(self):
        payload = _valid_file(card_overrides={1: {"reference_verified": None}})
        self._write_intake(payload)
        result = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(result)

        payload2 = _valid_file()
        del payload2["cards"][0]["operator_checklist"]["rights_reviewed"]
        self._write_intake(payload2)
        result2 = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(result2)

    def test_forged_approval_with_placeholder_fields_rejected(self):
        forged_card = _valid_card(
            1, CARD_PATHS[0],
            reference_url="REQUIRED_SOURCE_URL",
            authenticity_status="VERIFIED",
            source_name="REQUIRED_SOURCE_NAME",
        )
        forged_card["publish_ready"] = True
        forged_card["actual_publish"] = True
        payload = _valid_file()
        payload["cards"][0] = forged_card
        payload["publish_ready"] = True
        payload["actual_publish"] = True
        self._write_intake(payload)
        result = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(result)

    def test_publish_flags_are_never_propagated_even_when_otherwise_valid(self):
        payload = _valid_file()
        payload["publish_ready"] = True
        payload["actual_publish"] = True
        payload["cards"][0]["publish_ready"] = True
        payload["cards"][0]["actual_publish"] = True
        self._write_intake(payload)
        result = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsInstance(result, dict)
        for asset in result["assets"]:
            self.assertNotIn("publish_ready", asset)
            self.assertNotIn("actual_publish", asset)
        for item in result["evidence"]:
            self.assertNotIn("publish_ready", item)
            self.assertNotIn("actual_publish", item)

    def test_absolute_path_rejected(self):
        absolute = str((self.root / "storage/output_sets/card_news/sets" / OUTPUT_SET_ID / "cards/card_news_1.png").resolve())
        payload = _valid_file()
        payload["cards"][0]["card_path"] = absolute
        self._write_intake(payload)
        result = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(result)

    def test_runs_path_rejected(self):
        payload = _valid_file()
        payload["cards"][0]["card_path"] = f"storage/output_sets/card_news/.runs/{OUTPUT_SET_ID}/card_news/card_news_1.png"
        self._write_intake(payload)
        result = load_verified_rights_intake(
            OUTPUT_SET_ID,
            _card_news_result([payload["cards"][0]["card_path"]] + CARD_PATHS[1:]),
        )
        self.assertIsNone(result)

    def test_staging_path_rejected(self):
        payload = _valid_file()
        payload["cards"][0]["card_path"] = f"storage/output_sets/card_news/.staging/{OUTPUT_SET_ID}/cards/card_news_1.png"
        self._write_intake(payload)
        result = load_verified_rights_intake(
            OUTPUT_SET_ID,
            _card_news_result([payload["cards"][0]["card_path"]] + CARD_PATHS[1:]),
        )
        self.assertIsNone(result)

    def test_output_set_id_mismatch_rejected(self):
        payload = _valid_file(output_set_id="different-output-set-id")
        self._write_intake(payload, output_set_id=OUTPUT_SET_ID)
        result = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(result)

    def test_missing_and_duplicate_card_rejected(self):
        payload = _valid_file()
        del payload["cards"][3]
        self._write_intake(payload)
        result = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(result)

        payload2 = _valid_file()
        payload2["cards"][3] = dict(payload2["cards"][0])
        self._write_intake(payload2)
        result2 = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(result2)

    def test_evidence_url_without_verified_flag_rejected(self):
        payload = _valid_file(card_overrides={1: {"reference_verified": False}})
        self._write_intake(payload)
        result = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(result)

    def test_previous_output_set_approval_cannot_be_reused(self):
        old_id = "old-output-set-id-0000"
        self._write_intake(_valid_file(output_set_id=old_id), output_set_id=old_id)
        result = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(result)

        renamed_payload = _valid_file(output_set_id=old_id)
        self._write_intake(renamed_payload, output_set_id=OUTPUT_SET_ID)
        result2 = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(result2)


class RightsIntakeAttestationIntegrationTests(unittest.TestCase):
    """Confirms the loaded intake actually clears rights/evidence/compliance
    blockers through the real, unmodified gate while actual_publish stays
    forced false, and that a missing intake keeps the original V1.7 stub
    behavior unchanged."""

    def setUp(self):
        self.previous_cwd = Path.cwd()
        self.root = self.previous_cwd
        self.card_dir = Path("storage/output_sets/card_news/sets") / OUTPUT_SET_ID / "cards"
        self.card_dir.mkdir(parents=True, exist_ok=True)
        Path("storage/rights_intake").mkdir(parents=True, exist_ok=True)
        self.generation_record_path = Path("storage/manual_image_intake/staged_assets/CN-006-tests") / "generation_record.json"
        self.generation_record_path.parent.mkdir(parents=True, exist_ok=True)
        for index in range(1, 5):
            Image.new("RGB", (1080, 1080), (10, 20, 30)).save(self.card_dir / f"card_news_{index}.png")

    def tearDown(self):
        shutil.rmtree(self.card_dir.parent, ignore_errors=True)
        # Never rmtree the shared storage/rights_intake directory (real repo
        # root, shared with genuine production output sets) -- only remove
        # exactly the fixture files this test class itself writes.
        for output_set_id in (OUTPUT_SET_ID, "some-other-output-set-id"):
            path = self.root / "storage" / "rights_intake" / f"{output_set_id}.json"
            if path.exists():
                path.unlink()
        shutil.rmtree(self.root / "storage" / "manual_image_intake" / "staged_assets" / "CN-006-tests", ignore_errors=True)

    def test_no_intake_file_keeps_original_blocked_stub_behavior(self):
        card_news_result = _card_news_result()
        quality_result = {"passed": True, "checks": {}}
        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            attestation = WorkflowEngine._build_pre_publish_attestation(
                card_news_result, quality_result, OUTPUT_SET_ID, rights_intake=None,
            )
        self.assertTrue(attestation["technical_fixture_not_publish_approved"])
        self.assertFalse(attestation["publish_ready"])
        codes = {item["code"] for item in attestation["blockers"]}
        self.assertIn("technical_fixture_not_publish_approved", codes)
        self.assertIn("publishable_asset_missing", codes)

    def test_valid_intake_clears_rights_evidence_compliance_blockers(self):
        path = Path("storage/rights_intake") / f"{OUTPUT_SET_ID}.json"
        path.write_text(json.dumps(_valid_file(), ensure_ascii=False), encoding="utf-8")
        card_news_result = _card_news_result()
        quality_result = {"passed": True, "checks": {}}

        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            rights_intake = load_verified_rights_intake(OUTPUT_SET_ID, card_news_result)
            self.assertIsNotNone(rights_intake)
            attestation = WorkflowEngine._build_pre_publish_attestation(
                card_news_result, quality_result, OUTPUT_SET_ID, rights_intake=rights_intake,
            )
            self.assertTrue(attestation["publish_ready"], attestation["blockers"])
            self.assertFalse(attestation["technical_fixture_not_publish_approved"])
            self.assertEqual(attestation["blockers"], [])

            card_news_result["output_set_id"] = OUTPUT_SET_ID
            card_news_result["card_news_manifest"] = attestation
            card_news_result["quality"] = {"passed": True, "output_set_id": OUTPUT_SET_ID}

            publisher = PublishingModule()
            readiness = publisher._resolve_package_readiness(
                card_news_result, CARD_PATHS, {"publishing_blocked": False},
            )
            self.assertTrue(readiness["checks"]["rights_passed"])
            self.assertTrue(readiness["checks"]["evidence_passed"])
            self.assertTrue(readiness["checks"]["compliance_passed"])
            self.assertNotIn("PUBLISH_RIGHTS_BLOCKED", readiness["blocking_reasons"])
            self.assertNotIn("PUBLISH_EVIDENCE_BLOCKED", readiness["blocking_reasons"])
            self.assertNotIn("PUBLISH_COMPLIANCE_BLOCKED", readiness["blocking_reasons"])

            publishing_result = {
                "output_set_id": OUTPUT_SET_ID,
                "card_paths": CARD_PATHS,
                "blocker_codes": readiness["blocking_reasons"],
                "readiness_checks": readiness["checks"],
                "actual_publish": False,
            }
            rebound = publisher.rebind_committed_paths(
                publishing_result, CARD_PATHS, OUTPUT_SET_ID, None,
            )
            self.assertFalse(rebound["actual_publish"])

    def test_local_generation_record_binds_real_file_the_gate_reads_directly(self):
        """CardNewsPublishGate._rights_reference / _bound_local_record resolve
        and read the referenced file themselves -- they never accept an
        in-memory "normalized" record as a substitute. So a generation_record
        file that is missing required fields (asset_id/publish_permission/
        type/rights_status) or not yet review_status="approved" must NOT be
        talked into passing by the loader; only a genuinely complete, already
        -approved on-disk record can satisfy the real gate. This also locks
        that the loader's informational generation_record_id/recorded_at
        fields are still correctly read from that same real file for
        traceability, without ever touching the gate-facing `reference`
        field's plain-string contract."""
        generation_record_path = self.generation_record_path
        generation_record_path.parent.mkdir(parents=True, exist_ok=True)
        generation_record_path.write_text(
            json.dumps(
                {
                    "record_id": "cn-006-generation-normalized",
                    "recorded_at": _now_iso(-30),
                    "asset_id": "card_1",
                    "type": "generation_record",
                    "evidence_type": "generation_record",
                    "publish_permission": "granted",
                    "rights_status": "generated",
                    "review_status": "approved",
                    "provenance": "ai_generated",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        # CardNewsPublishGate._rights_reference matches a record's own
        # asset_id against the exact card being validated -- a shared record
        # file cannot honestly back more than one asset_id, so cards 2-4 get
        # their own distinct (but equally complete) records here.
        other_record_paths = {}
        for index in (2, 3, 4):
            other_path = self.generation_record_path.parent / f"generation_record_card_{index}.json"
            other_path.write_text(
                json.dumps(
                    {
                        "record_id": f"cn-006-generation-normalized-{index}",
                        "recorded_at": _now_iso(-30),
                        "asset_id": f"card_{index}",
                        "type": "generation_record",
                        "evidence_type": "generation_record",
                        "publish_permission": "granted",
                        "rights_status": "generated",
                        "review_status": "approved",
                        "provenance": "ai_generated",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            other_record_paths[index] = other_path

        payload = _valid_file()
        payload["cards"] = [
            _valid_card(
                index,
                path,
                origin="first_party",
                role="decorative",
                rights_status="generated",
                reference_url=str(
                    (generation_record_path if index == 1 else other_record_paths[index]).as_posix()
                ),
            )
            for index, path in enumerate(CARD_PATHS, start=1)
        ]
        path = Path("storage/rights_intake") / f"{OUTPUT_SET_ID}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            card_news_result = _card_news_result()
            quality_result = {"passed": True, "checks": {}}
            rights_intake = load_verified_rights_intake(OUTPUT_SET_ID, card_news_result)
            self.assertIsNotNone(rights_intake)
            attestation = WorkflowEngine._build_pre_publish_attestation(
                card_news_result, quality_result, OUTPUT_SET_ID, rights_intake=rights_intake,
            )

        self.assertTrue(attestation["publish_ready"], attestation["blockers"])
        self.assertEqual(attestation["actual_publish"], False)
        self.assertEqual(len(attestation["blockers"]), 0)

        asset = rights_intake["assets"][0]
        rights_evidence = asset["rights_evidence"]
        # The gate-facing field must stay the plain repo-relative path string
        # -- this is exactly what CardNewsPublishGate._rights_reference reads
        # and independently re-validates from disk.
        self.assertEqual(rights_evidence["reference"], str(generation_record_path.as_posix()))
        self.assertIsInstance(rights_evidence["reference"], str)
        # Informational fields, read from that same real file for
        # traceability only -- never fed back into the gate.
        self.assertEqual(rights_evidence["generation_record_id"], "cn-006-generation-normalized")
        self.assertEqual(rights_evidence["generation_recorded_at"], json.loads(generation_record_path.read_text(encoding="utf-8"))["recorded_at"])
        self.assertEqual(rights_evidence["authenticity_status"], "verified")

        expected_sha = hashlib.sha256()
        with open(self.card_dir / "card_news_1.png", "rb") as file:
            expected_sha.update(file.read())
        self.assertEqual(rights_evidence["image_sha256"], expected_sha.hexdigest())

        evidence = rights_intake["evidence"][0]
        self.assertEqual(evidence["provenance_reference"], str(generation_record_path.as_posix()))
        self.assertIsInstance(evidence["provenance_reference"], str)

    def test_incomplete_local_generation_record_keeps_gate_blocked(self):
        """An on-disk generation_record file missing required gate fields (or
        not yet review_status="approved") must leave rights/evidence blocked
        -- the loader must never paper over an incomplete real record."""
        generation_record_path = self.generation_record_path
        generation_record_path.parent.mkdir(parents=True, exist_ok=True)
        generation_record_path.write_text(
            json.dumps(
                {
                    "record_id": "cn-006-generation-incomplete",
                    "recorded_at": _now_iso(-30),
                    "review_status": "pending",
                    "provenance": "ai_generated",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        payload = _valid_file()
        payload["cards"] = [
            _valid_card(
                index,
                path,
                origin="first_party",
                role="decorative",
                rights_status="generated",
                reference_url=str(generation_record_path.as_posix()),
            )
            for index, path in enumerate(CARD_PATHS, start=1)
        ]
        path = Path("storage/rights_intake") / f"{OUTPUT_SET_ID}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        with patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve()):
            card_news_result = _card_news_result()
            quality_result = {"passed": True, "checks": {}}
            rights_intake = load_verified_rights_intake(OUTPUT_SET_ID, card_news_result)
            self.assertIsNotNone(rights_intake)
            attestation = WorkflowEngine._build_pre_publish_attestation(
                card_news_result, quality_result, OUTPUT_SET_ID, rights_intake=rights_intake,
            )

        self.assertFalse(attestation["publish_ready"])
        codes = {item["code"] for item in attestation["blockers"]}
        self.assertIn("asset_rights_evidence_invalid", codes)

    def test_output_set_id_mismatch_between_active_set_and_intake_keeps_blocked(self):
        mismatched_file = _valid_file(output_set_id="some-other-output-set-id")
        path = Path("storage/rights_intake") / f"{OUTPUT_SET_ID}.json"
        path.write_text(json.dumps(mismatched_file, ensure_ascii=False), encoding="utf-8")
        rights_intake = load_verified_rights_intake(OUTPUT_SET_ID, _card_news_result())
        self.assertIsNone(rights_intake)


if __name__ == "__main__":
    unittest.main()
