"""Publishing RC contract tests for a safe, operator-driven CardNews upload package."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from modules.compliance.card_news_publish_gate import CardNewsPublishGate
from modules.publishing.publishing_module import PublishingModule


class PublishingReleaseCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.card_paths = []
        for index in range(1, 5):
            path = self.root / f"card_news_{index}.png"
            Image.new("RGB", (1080, 1080), color=(index * 20, 30, 40)).save(path)
            self.card_paths.append(str(path))

        self.module = PublishingModule.__new__(PublishingModule)
        self.module.config = {}
        self.module.publishing_dir = self.root
        self.module.publishing_config = self.module._fallback_publishing_config()
        self.save_json = patch.object(self.module, "_save_json").start()
        self.save_text = patch.object(self.module, "_save_text").start()

    def tearDown(self):
        patch.stopall()
        self.temp_dir.cleanup()

    def _ready_input(self):
        output_set_id = "card-news-set-001"
        return {
            "title": "업로드 가능한 카드뉴스",
            "output_set_id": output_set_id,
            "cards": [
                {"card_path": path, "index": index}
                for index, path in enumerate(self.card_paths, start=1)
            ],
            "image_sourcing_status": {
                "manual_image_required": False,
                "real_image_used_count": 4,
                "checklist": [],
            },
            "pre_publish_attestation": {
                "schema_version": 1,
                "contract": "card_news_pre_publish_attestation_v1",
                "output_set_id": output_set_id,
                "cards": [
                    {"path": path, "index": index, "exists": True}
                    for index, path in enumerate(self.card_paths, start=1)
                ],
                "quality": {"passed": True},
                "rights": {"status": "pass", "ready": True},
                "evidence": {"status": "applied", "available": True, "applied": True},
                "compliance_result": {
                    "schema_version": "card_news_compliance.v1",
                    "package_id": "compliance-set-001",
                    "status": "valid",
                    "publish_ready": True,
                    "blocking_reasons": [],
                },
                "provenance": {
                    "source": "CardNewsPublishGate",
                    "result_id": "compliance-set-001",
                },
                "technical_fixture_not_publish_approved": False,
                "release_guard": {"ready": True, "issue_codes": []},
            },
        }

    def test_ready_contract_builds_complete_operator_package_without_publishing(self):
        result = self.module.run(self._ready_input())

        self.assertTrue(result["package_ready"])
        self.assertTrue(result["publishing_ready"])
        self.assertFalse(result["actual_publish"])
        self.assertEqual(result["blocker_codes"], [])
        self.assertTrue(all(result["readiness_checks"].values()))

        package = result["operator_upload_package"]
        self.assertEqual(package["status"], "ready_for_manual_upload")
        self.assertEqual(package["upload_mode"], "manual")
        self.assertFalse(package["actual_publish"])
        self.assertEqual(package["output_set_id"], "card-news-set-001")
        self.assertEqual(package["ordered_card_paths"], self.card_paths)
        self.assertEqual(len(package["ordered_card_paths"]), 4)
        self.assertTrue(package["caption"])
        self.assertTrue(package["hashtags"])
        self.assertTrue(package["full_caption"])
        self.assertTrue(package["manual_upload_checklist"])
        self.assertIn("schedule", package)
        self.assertIn("account", package)
        self.assertEqual(package["blocker_codes"], [])

    def test_builder_shaped_attestation_has_no_publishing_result_dependency(self):
        payload = self._ready_input()
        attestation = payload["pre_publish_attestation"]

        self.assertNotIn("publishing", attestation)
        self.assertNotIn("09_publishing_result", str(attestation))
        self.assertEqual(
            set(("cards", "quality", "rights", "evidence", "release_guard"))
            - set(attestation),
            set(),
        )
        result = self.module.run(payload)
        self.assertTrue(result["package_ready"])
        self.assertFalse(result["actual_publish"])

    def test_real_compliance_gate_blocked_result_is_consumed_fail_closed(self):
        compliance_result = CardNewsPublishGate().check(
            {
                "package_id": "technical-fixture-package",
                "output_set_id": "card-news-set-001",
                "assets": [
                    {"asset_id": "fixture-1", "classification": "technical_fixture"}
                ],
                "evidence": [],
                "claims": [],
                "campaign": {
                    "is_advertising": False,
                    "is_sponsored": False,
                    "has_affiliate_link": False,
                    "commercial_relationship_reviewed": True,
                },
                "disclosures": [],
                "operator_checklist": {},
            }
        )
        self.assertEqual(compliance_result["schema_version"], "card_news_compliance.v1")
        self.assertEqual(compliance_result["status"], "blocked")

        payload = self._ready_input()
        payload["pre_publish_attestation"]["compliance_result"] = compliance_result
        result = self.module.run(payload)

        self.assertFalse(result["package_ready"])
        self.assertIn("PUBLISH_COMPLIANCE_BLOCKED", result["blocker_codes"])
        self.assertNotIn("PUBLISH_COMPLIANCE_PROVENANCE_MISSING", result["blocker_codes"])
        self.assertFalse(result["actual_publish"])

    def test_missing_attestation_does_not_misdiagnose_valid_top_level_card_files(self):
        payload = self._ready_input()
        payload.pop("pre_publish_attestation")

        result = self.module.run(payload)

        self.assertIn("PUBLISH_ATTESTATION_MISSING", result["blocker_codes"])
        self.assertNotIn("PUBLISH_CARD_COUNT_INVALID", result["blocker_codes"])
        self.assertNotIn("PUBLISH_CARD_FILE_MISSING", result["blocker_codes"])
        self.assertFalse(result["package_ready"])
        self.assertFalse(result["actual_publish"])

    def test_rebind_committed_paths_survives_run_source_cleanup(self):
        source_dir = self.root / ".runs" / "run-1"
        source_dir.mkdir(parents=True)
        source_paths = []
        for index in range(1, 5):
            path = source_dir / f"card_{index}.png"
            Image.new("RGB", (1080, 1080), color=(index * 30, 50, 70)).save(path)
            source_paths.append(str(path))

        original_paths = self.card_paths
        self.card_paths = source_paths
        try:
            publishing_result = self.module.run(self._ready_input())
        finally:
            self.card_paths = original_paths

        self.assertTrue(publishing_result["package_ready"])
        self.assertEqual(publishing_result["card_paths"], source_paths)
        self.assertEqual(
            publishing_result["operator_upload_package"]["ordered_card_paths"],
            source_paths,
        )
        self.assertIn("publish_queue", publishing_result)
        self.assertEqual(
            publishing_result["publish_queue"]["items"][0]["card_paths"],
            source_paths,
        )
        self.assertEqual(publishing_result["output_set_id"], "card-news-set-001")
        self.assertEqual(
            publishing_result["publish_queue"]["output_set_id"],
            "card-news-set-001",
        )
        self.assertFalse(publishing_result["actual_publish"])
        self.assertFalse(publishing_result["operator_upload_package"]["actual_publish"])
        self.assertFalse(publishing_result["publish_queue"]["actual_publish"])
        self.assertFalse(
            publishing_result["publish_queue"]["items"][0]["actual_publish"]
        )

        committed_dir = self.root / "committed" / "card-news-set-001"
        committed_dir.mkdir(parents=True)
        committed_paths = []
        for index in range(1, 5):
            path = committed_dir / f"card_{index}.png"
            Image.new("RGB", (1080, 1080), color=(index * 40, 80, 100)).save(path)
            committed_paths.append(str(path))

        rebound = self.module.rebind_committed_paths(
            publishing_result, committed_paths, "card-news-set-001"
        )

        derived_queue_target = committed_dir / "09_publish_queue.json"
        self.assertEqual(
            Path(rebound["publish_queue_path"]).resolve(),
            derived_queue_target.resolve(),
        )
        self.assertEqual(
            rebound["operator_upload_package"]["publish_queue_path"],
            rebound["publish_queue_path"],
        )
        self.assertTrue(derived_queue_target.is_file())
        self.assertEqual(
            json.loads(derived_queue_target.read_text(encoding="utf-8")),
            rebound["publish_queue"],
        )

        for path in source_paths:
            Path(path).unlink()

        self.assertEqual(rebound["card_paths"], committed_paths)
        self.assertEqual(
            rebound["operator_upload_package"]["ordered_card_paths"], committed_paths
        )
        self.assertTrue(
            all(
                item["card_paths"] == committed_paths
                for item in rebound["publish_queue"]["items"]
            )
        )
        self.assertNotIn(".runs", str(rebound))
        self.assertTrue(all(Path(path).is_file() for path in rebound["card_paths"]))
        self.assertTrue(
            all(
                Path(path).is_file()
                for path in rebound["operator_upload_package"]["ordered_card_paths"]
            )
        )
        self.assertTrue(
            all(
                Path(path).is_file()
                for item in rebound["publish_queue"]["items"]
                for path in item["card_paths"]
            )
        )
        self.assertEqual(rebound["output_set_id"], "card-news-set-001")
        self.assertEqual(
            rebound["operator_upload_package"]["output_set_id"], "card-news-set-001"
        )
        self.assertEqual(rebound["publish_queue"]["output_set_id"], "card-news-set-001")
        self.assertTrue(
            all(
                item["output_set_id"] == "card-news-set-001"
                for item in rebound["publish_queue"]["items"]
            )
        )
        self.assertFalse(rebound["actual_publish"])
        self.assertFalse(rebound["operator_upload_package"]["actual_publish"])
        self.assertFalse(rebound["publish_queue"]["actual_publish"])
        self.assertTrue(
            all(not item["actual_publish"] for item in rebound["publish_queue"]["items"])
        )

        def assert_rebind_queue_blocked(result):
            queue = result["publish_queue"]
            self.assertEqual(queue["status"], "queue_blocked")
            self.assertFalse(queue["actual_publish"])
            self.assertEqual(queue["blocker_codes"], result["blocker_codes"])
            for item in queue["items"]:
                self.assertEqual(item["status"], "blocked_rebind_failed")
                self.assertFalse(item["actual_publish"])
                self.assertEqual(item["blocker_codes"], result["blocker_codes"])

        failed = self.module.rebind_committed_paths(
            publishing_result, [], "card-news-set-001"
        )
        self.assertFalse(failed["package_ready"])
        self.assertFalse(failed["publishing_ready"])
        self.assertFalse(failed["actual_publish"])
        self.assertEqual(failed["operator_upload_package"]["status"], "blocked")
        assert_rebind_queue_blocked(failed)

        for invalid_id in ("", "different-set"):
            with self.subTest(invalid_output_set_id=invalid_id):
                identity_failed = self.module.rebind_committed_paths(
                    publishing_result, committed_paths, invalid_id
                )
                self.assertFalse(identity_failed["package_ready"])
                self.assertIn(
                    "PUBLISH_COMMITTED_OUTPUT_SET_MISMATCH",
                    identity_failed["blocker_codes"],
                )
                self.assertEqual(
                    identity_failed["operator_upload_package"]["blocker_codes"],
                    identity_failed["blocker_codes"],
                )
                self.assertFalse(identity_failed["actual_publish"])
                assert_rebind_queue_blocked(identity_failed)

        manual_blocked = copy.deepcopy(publishing_result)
        manual_blocked.update(
            package_ready=False,
            publishing_ready=False,
            blocker_codes=["PUBLISH_MANUAL_IMAGE_REQUIRED"],
        )
        manual_blocked["operator_upload_package"].update(
            status="blocked", blocker_codes=["PUBLISH_MANUAL_IMAGE_REQUIRED"]
        )
        rebound_blocked = self.module.rebind_committed_paths(
            manual_blocked, committed_paths, "card-news-set-001"
        )
        self.assertFalse(rebound_blocked["package_ready"])
        self.assertEqual(
            rebound_blocked["operator_upload_package"]["blocker_codes"],
            rebound_blocked["blocker_codes"],
        )
        self.assertEqual(rebound_blocked["card_paths"], committed_paths)
        self.assertFalse(rebound_blocked["actual_publish"])
        assert_rebind_queue_blocked(rebound_blocked)

        required_rebind_checks = tuple(publishing_result["readiness_checks"])
        for failed_check in required_rebind_checks:
            with self.subTest(failed_check=failed_check):
                invalid_attestation = copy.deepcopy(publishing_result)
                invalid_attestation["readiness_checks"][failed_check] = False
                blocked = self.module.rebind_committed_paths(
                    invalid_attestation, committed_paths, "card-news-set-001"
                )
                self.assertFalse(blocked["package_ready"])
                self.assertFalse(blocked["publishing_ready"])
                self.assertIn(
                    "PUBLISH_COMMITTED_ATTESTATION_INVALID",
                    blocked["blocker_codes"],
                )
                self.assertEqual(
                    blocked["operator_upload_package"]["blocker_codes"],
                    blocked["blocker_codes"],
                )
                self.assertFalse(blocked["actual_publish"])
                assert_rebind_queue_blocked(blocked)

        missing_attestation_check = copy.deepcopy(publishing_result)
        missing_attestation_check["readiness_checks"].pop("compliance_passed")
        blocked = self.module.rebind_committed_paths(
            missing_attestation_check, committed_paths, "card-news-set-001"
        )
        self.assertFalse(blocked["package_ready"])
        self.assertFalse(blocked["publishing_ready"])
        self.assertFalse(blocked["actual_publish"])
        self.assertIn(
            "PUBLISH_COMMITTED_ATTESTATION_INVALID", blocked["blocker_codes"]
        )
        assert_rebind_queue_blocked(blocked)

    def test_rebind_atomically_replaces_stale_external_queue_and_survives_cleanup(self):
        source_dir = self.root / ".runs" / "production-run"
        source_dir.mkdir(parents=True)
        source_paths = []
        for index in range(1, 5):
            path = source_dir / f"card_{index}.png"
            Image.new("RGB", (1080, 1080), color=(index * 25, 60, 90)).save(path)
            source_paths.append(str(path))

        original_paths = self.card_paths
        self.card_paths = source_paths
        try:
            production_result = self.module.run(self._ready_input())
        finally:
            self.card_paths = original_paths

        committed_dir = self.root / "output_sets" / "card-news-set-001"
        committed_dir.mkdir(parents=True)
        committed_paths = []
        for index in range(1, 5):
            path = committed_dir / f"card_{index}.png"
            Image.new("RGB", (1080, 1080), color=(index * 35, 80, 110)).save(path)
            committed_paths.append(str(path))

        queue_target = committed_dir / "09_publish_queue.json"
        stale_payload = {
            "output_set_id": "old-set",
            "actual_publish": True,
            "items": [{
                "output_set_id": "old-set",
                "actual_publish": True,
                "card_paths": [str(self.root / "loose.png")],
            }],
        }
        queue_target.write_text(json.dumps(stale_payload), encoding="utf-8")

        rebound = self.module.rebind_committed_paths(
            production_result,
            committed_paths,
            "card-news-set-001",
            queue_target,
        )
        persisted = json.loads(queue_target.read_text(encoding="utf-8"))
        embedded = rebound["publish_queue"]

        self.assertEqual(
            Path(rebound["publish_queue_path"]).resolve(),
            queue_target.resolve(),
        )
        self.assertEqual(persisted, embedded)
        self.assertEqual(persisted["output_set_id"], "card-news-set-001")
        self.assertFalse(persisted["actual_publish"])
        self.assertTrue(persisted["items"])
        for item in persisted["items"]:
            self.assertEqual(item["output_set_id"], "card-news-set-001")
            self.assertFalse(item["actual_publish"])
            self.assertEqual(item["card_paths"], committed_paths)

        for path in source_paths:
            Path(path).unlink()
        source_dir.rmdir()
        self.assertNotIn(".runs", str(rebound))
        self.assertTrue(all(Path(path).is_file() for path in committed_paths))
        self.assertEqual(
            rebound["operator_upload_package"]["ordered_card_paths"],
            committed_paths,
        )

        failed_target = committed_dir / "publish_queue.json"
        production_result["publish_queue_path"] = "storage/publishing/publish_queue.json"
        production_result["operator_upload_package"]["publish_queue_path"] = (
            "storage/publishing/publish_queue.json"
        )
        with patch("modules.publishing.publishing_module.os.replace", side_effect=OSError("disk")):
            failed = self.module.rebind_committed_paths(
                production_result,
                committed_paths,
                "card-news-set-001",
                failed_target,
            )
        self.assertFalse(failed["package_ready"])
        self.assertFalse(failed["publishing_ready"])
        self.assertFalse(failed["actual_publish"])
        self.assertIn("PUBLISH_COMMITTED_QUEUE_PERSIST_FAILED", failed["blocker_codes"])
        self.assertFalse(failed_target.exists())
        self.assertNotIn("publish_queue_path", failed)
        self.assertNotIn(
            "publish_queue_path", failed["operator_upload_package"]
        )

        unrelated_target = self.root / "global" / "publish_queue.json"
        attacked = self.module.rebind_committed_paths(
            production_result,
            committed_paths,
            "card-news-set-001",
            unrelated_target,
        )
        self.assertFalse(attacked["package_ready"])
        self.assertFalse(attacked["publishing_ready"])
        self.assertFalse(attacked["actual_publish"])
        self.assertIn(
            "PUBLISH_COMMITTED_QUEUE_TARGET_INVALID", attacked["blocker_codes"]
        )
        self.assertFalse(unrelated_target.exists())
        self.assertNotIn("publish_queue_path", attacked)
        self.assertNotIn(
            "publish_queue_path", attacked["operator_upload_package"]
        )
        self.assertEqual(attacked["publish_queue"]["status"], "queue_blocked")
        self.assertFalse(attacked["publish_queue"]["actual_publish"])
        self.assertTrue(
            all(
                item["status"] == "blocked_rebind_failed"
                and item["actual_publish"] is False
                for item in attacked["publish_queue"]["items"]
            )
        )

    def test_compliance_block_normalizes_outer_rights_and_evidence_fail_closed(self):
        payload = self._ready_input()
        attestation = payload["pre_publish_attestation"]
        attestation["rights"] = {"status": "pass", "ready": True}
        attestation["evidence"] = {
            "status": "unavailable",
            "available": False,
            "applied": False,
        }
        attestation["render_allowed_asset_ids"] = []
        attestation["compliance_result"].update(
            status="blocked",
            publish_ready=False,
            blocking_reasons=["rights_review_required"],
        )
        attestation["release_guard"] = {
            "ready": False,
            "issue_codes": ["rights_review_required"],
        }

        result = self.module.run(payload)

        self.assertFalse(result["package_ready"])
        self.assertFalse(result["publishing_ready"])
        self.assertFalse(result["actual_publish"])
        self.assertFalse(result["readiness_checks"]["compliance_passed"])
        self.assertFalse(result["readiness_checks"]["rights_passed"])
        self.assertFalse(result["readiness_checks"]["evidence_passed"])
        for code in (
            "PUBLISH_COMPLIANCE_BLOCKED",
            "PUBLISH_RIGHTS_BLOCKED",
            "PUBLISH_EVIDENCE_BLOCKED",
        ):
            self.assertIn(code, result["blocker_codes"])
        package = result["operator_upload_package"]
        self.assertFalse(package["actual_publish"])
        self.assertEqual(package["blocker_codes"], result["blocker_codes"])
        self.assertFalse(result["publish_queue"]["actual_publish"])
        self.assertTrue(
            all(not item["actual_publish"] for item in result["publish_queue"]["items"])
        )

    def test_truth_table_fail_closed_for_every_release_blocker(self):
        cases = {
            "card_count": ("PUBLISH_CARD_COUNT_INVALID", lambda data: data.update(cards=[])),
            "file_missing": (
                "PUBLISH_CARD_FILE_MISSING",
                lambda data: (
                    data["cards"][0].update(card_path=str(self.root / "missing.png")),
                    data["pre_publish_attestation"]["cards"][0].update(
                        path=str(self.root / "missing.png")
                    ),
                ),
            ),
            "manifest_paths": (
                "PUBLISH_MANIFEST_PATH_MISMATCH",
                lambda data: data["pre_publish_attestation"]["cards"][0].update(path=self.card_paths[1]),
            ),
            "output_set_missing": (
                "PUBLISH_OUTPUT_SET_MISSING",
                lambda data: data.pop("output_set_id"),
            ),
            "output_set_mismatch": (
                "PUBLISH_OUTPUT_SET_MISMATCH",
                lambda data: data["pre_publish_attestation"].update(output_set_id="other-set"),
            ),
            "rights": (
                "PUBLISH_RIGHTS_BLOCKED",
                lambda data: data["pre_publish_attestation"]["rights"].update(status="blocked", ready=False),
            ),
            "evidence": (
                "PUBLISH_EVIDENCE_BLOCKED",
                lambda data: data["pre_publish_attestation"]["evidence"].update(
                    status="not_applied", available=True, applied=False
                ),
            ),
            "qa": (
                "PUBLISH_QA_BLOCKED",
                lambda data: data["pre_publish_attestation"]["quality"].update(passed=False),
            ),
            "compliance": (
                "PUBLISH_COMPLIANCE_BLOCKED",
                lambda data: data["pre_publish_attestation"]["compliance_result"].update(
                    status="blocked", publish_ready=False
                ),
            ),
            "compliance_provenance": (
                "PUBLISH_COMPLIANCE_PROVENANCE_MISSING",
                lambda data: data["pre_publish_attestation"]["compliance_result"].pop(
                    "package_id"
                ),
            ),
            "technical_fixture": (
                "PUBLISH_COMPLIANCE_BLOCKED",
                lambda data: data["pre_publish_attestation"].update(
                    technical_fixture_not_publish_approved=True
                ),
            ),
            "attestation_missing": (
                "PUBLISH_ATTESTATION_MISSING",
                lambda data: data.pop("pre_publish_attestation"),
            ),
            "attestation_schema": (
                "PUBLISH_ATTESTATION_SCHEMA_INVALID",
                lambda data: data["pre_publish_attestation"].update(schema_version=2),
            ),
            "manual_image": (
                "PUBLISH_MANUAL_IMAGE_REQUIRED",
                lambda data: data["image_sourcing_status"].update(manual_image_required=True),
            ),
        }

        for name, (expected_code, mutate) in cases.items():
            with self.subTest(name=name):
                payload = copy.deepcopy(self._ready_input())
                mutate(payload)
                result = self.module.run(payload)
                package = result["operator_upload_package"]

                self.assertFalse(result["package_ready"])
                self.assertFalse(result["publishing_ready"])
                self.assertFalse(result["actual_publish"])
                self.assertIn(expected_code, result["blocker_codes"])
                self.assertEqual(package["status"], "blocked")
                self.assertFalse(package["actual_publish"])
                self.assertEqual(package["blocker_codes"], result["blocker_codes"])

    def test_non_manual_configuration_never_becomes_ready_or_published(self):
        self.module.publishing_config["upload_mode"] = "api"

        result = self.module.run(self._ready_input())

        self.assertFalse(result["package_ready"])
        self.assertFalse(result["actual_publish"])
        self.assertIn("PUBLISH_UPLOAD_MODE_UNSAFE", result["blocker_codes"])
        self.assertEqual(result["operator_upload_package"]["upload_mode"], "manual")
        self.assertFalse(result["operator_upload_package"]["actual_publish"])


if __name__ == "__main__":
    unittest.main()
