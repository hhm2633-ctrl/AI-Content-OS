import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from modules.commerce.approval_gate import CAPABILITIES, ApprovalGate
from modules.commerce.audit_logger import AuditLogger
from modules.commerce.commerce_engine import CommerceEngine
from modules.commerce.dry_run_executor import DryRunExecutor
from modules.commerce.rollback_manager import RollbackManager
from tests.commerce.fixtures import sample_commerce_result


class CommerceEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        audit_logger = AuditLogger(audit_dir=Path(self.tmp_dir.name) / "audit")
        self.engine = CommerceEngine(
            audit_logger=audit_logger,
            dry_run_executor=DryRunExecutor(dryrun_dir=Path(self.tmp_dir.name) / "dryrun", audit_logger=audit_logger),
            rollback_manager=RollbackManager(audit_logger=audit_logger),
            approval_gate=ApprovalGate(approval_path=Path("this/path/does/not/exist.json")),
        )
        self.commerce_result = sample_commerce_result()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_run_full_dry_run_covers_both_default_platforms(self):
        summary = self.engine.run_full_dry_run(self.commerce_result, persist=False)
        self.assertEqual(set(summary["platforms"]), {"smartstore", "coupang"})

    def test_run_full_dry_run_never_makes_network_call(self):
        summary = self.engine.run_full_dry_run(self.commerce_result, persist=False)
        self.assertFalse(summary["capability_boundaries"]["network_calls"])
        self.assertFalse(summary["capability_boundaries"]["platform_upload"])
        self.assertFalse(summary["auto_upload_performed"])
        self.assertEqual(summary["upload_mode"], "dry_run_only")

    def test_run_full_dry_run_records_phase1_traceability(self):
        summary = self.engine.run_full_dry_run(self.commerce_result, persist=False)
        self.assertEqual(summary["phase1_request_id"], "smoke_test_001")
        self.assertEqual(summary["phase1_status"], "ready_for_manual_upload")

    def test_run_full_dry_run_restricts_to_requested_platforms(self):
        summary = self.engine.run_full_dry_run(self.commerce_result, platforms=["coupang"], persist=False)
        self.assertEqual(set(summary["platforms"]), {"coupang"})

    def test_run_full_dry_run_overall_ready_false_when_required_fields_missing(self):
        # sample_commerce_result() is missing category/price/stock/shipping/images
        # for both platforms -- neither package can be dry-run ready today.
        summary = self.engine.run_full_dry_run(self.commerce_result, persist=False)
        self.assertFalse(summary["overall_dry_run_ready"])

    def test_run_full_dry_run_unsupported_platform_reports_error_not_raise(self):
        summary = self.engine.run_full_dry_run(self.commerce_result, platforms=["gmarket"], persist=False)
        self.assertIn("error", summary["platforms"]["gmarket"])
        self.assertFalse(summary["platforms"]["gmarket"]["network_call_made"])

    def test_run_full_dry_run_persists_when_requested(self):
        summary = self.engine.run_full_dry_run(self.commerce_result, platforms=["coupang"], persist=True)
        self.assertTrue(summary["platforms"]["coupang"]["executor_metadata"]["persisted"])

    def test_run_from_facts_composes_phase1_and_phase2a(self):
        fake_commerce_module = MagicMock()
        fake_commerce_module.run.return_value = self.commerce_result
        engine = CommerceEngine(
            commerce_module=fake_commerce_module,
            audit_logger=self.engine.audit_logger,
            dry_run_executor=self.engine.dry_run_executor,
            rollback_manager=self.engine.rollback_manager,
            approval_gate=self.engine.approval_gate,
        )

        combined = engine.run_from_facts(product_facts={"request_id": "smoke_test_001"})

        fake_commerce_module.run.assert_called_once()
        self.assertEqual(combined["phase1_result"], self.commerce_result)
        self.assertIn("phase2a_result", combined)
        self.assertEqual(set(combined["phase2a_result"]["platforms"]), {"smartstore", "coupang"})

    def test_check_approval_status_reports_every_capability_unapproved_by_default(self):
        status = self.engine.check_approval_status()
        self.assertEqual(set(status), set(CAPABILITIES))
        for capability_status in status.values():
            self.assertFalse(capability_status["approved"])

    def test_check_approval_status_never_mutates_config(self):
        approval_path = Path("this/path/does/not/exist.json")
        self.assertFalse(approval_path.exists())
        self.engine.check_approval_status()
        self.assertFalse(approval_path.exists())


if __name__ == "__main__":
    unittest.main()
