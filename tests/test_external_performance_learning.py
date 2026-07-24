import json
import tempfile
import unittest
from pathlib import Path

from modules.analytics_engine.promotion_candidate_builder import PromotionCandidateBuilder
from modules.learning.performance_ledger import PerformanceLedger, PerformanceLedgerError
from modules.learning.promotion_controller import PromotionController, PromotionControllerError
from scripts.import_external_performance import load_import_file


def measured_record(**overrides):
    value = {
        "measurement_class": "external_measured",
        "output_set_id": "output-1",
        "candidate_id": "candidate-1",
        "pattern_ids": ["pattern-1"],
        "reference_ids": ["reference-1"],
        "media_id": "media-1",
        "evaluation_period": {
            "start": "2026-07-01T00:00:00Z",
            "end": "2026-07-08T00:00:00Z",
        },
        "sample_size": 100,
        "metrics": {"reach": 1000, "save_rate": 0.08},
    }
    value.update(overrides)
    return value


class FakeRegistry:
    def __init__(self):
        self.calls = []

    def promote(self, pattern, *, performance_met, human_approved):
        self.calls.append((pattern, performance_met, human_approved))
        return pattern


class ExternalPerformanceLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ledger = PerformanceLedger(self.root / "ledger.json")

    def tearDown(self):
        self.temp.cleanup()

    def import_one(self, record=None):
        return self.ledger.import_external(
            [record or measured_record()],
            source_type="manual_json",
            source_name="performance.json",
            source_hash="a" * 64,
        )

    def test_internal_proxy_cannot_enter_external_measured_partition(self):
        record = measured_record(measurement_class="internal_proxy")
        with self.assertRaises(PerformanceLedgerError):
            self.import_one(record)

    def test_internal_proxy_metric_cannot_be_labeled_external_measured(self):
        record = measured_record(metrics={"overall_performance_score": 0.9})
        with self.assertRaises(PerformanceLedgerError):
            self.import_one(record)

    def test_evaluation_period_is_required_and_ordered(self):
        record = measured_record(
            evaluation_period={
                "start": "2026-07-08T00:00:00Z",
                "end": "2026-07-01T00:00:00Z",
            }
        )
        with self.assertRaises(PerformanceLedgerError):
            self.import_one(record)

    def test_sample_size_must_be_positive(self):
        with self.assertRaises(PerformanceLedgerError):
            self.import_one(measured_record(sample_size=0))

    def test_duplicate_import_is_idempotent(self):
        first = self.import_one()
        second = self.import_one()
        self.assertEqual(first["inserted_count"], 1)
        self.assertEqual(second["inserted_count"], 0)
        self.assertEqual(second["duplicate_count"], 1)
        self.assertEqual(len(self.ledger.external_records()), 1)

    def test_json_import_accepts_records_envelope(self):
        path = self.root / "input.json"
        path.write_text(json.dumps({"records": [measured_record()]}), encoding="utf-8")
        self.assertEqual(len(load_import_file(path)), 1)

    def test_csv_import_is_supported_without_api(self):
        path = self.root / "input.csv"
        path.write_text(
            "output_set_id,candidate_id,pattern_ids,reference_ids,media_id,"
            "evaluation_start,evaluation_end,sample_size,reach\n"
            "output-1,candidate-1,pattern-1,reference-1,media-1,"
            "2026-07-01T00:00:00Z,2026-07-08T00:00:00Z,100,1000\n",
            encoding="utf-8",
        )
        self.assertEqual(load_import_file(path)[0]["media_id"], "media-1")

    def test_analytics_builds_review_candidate_without_automatic_apply(self):
        self.import_one()
        builder = PromotionCandidateBuilder(self.root / "candidates.json")
        candidate = builder.build(
            pattern_id="pattern-1",
            records=self.ledger.external_records(),
            metric_thresholds={"save_rate": 0.05},
            minimum_sample_size=50,
        )
        self.assertTrue(candidate["performance_met"])
        self.assertEqual(candidate["status"], "pending_owner_approval")
        self.assertFalse(candidate["automatic_apply"])
        self.assertFalse(candidate["pattern_registry_called"])
        self.assertEqual(candidate["measurement_class"], "external_measured")

    def test_pattern_registry_is_not_called_before_owner_approval(self):
        self.import_one()
        candidate_path = self.root / "candidates.json"
        candidate = PromotionCandidateBuilder(candidate_path).build(
            pattern_id="pattern-1",
            records=self.ledger.external_records(),
            metric_thresholds={"save_rate": 0.05},
            minimum_sample_size=50,
        )
        registry = FakeRegistry()
        controller = PromotionController(candidate_path, registry=registry)
        with self.assertRaises(PromotionControllerError):
            controller.promote_approved(candidate["promotion_candidate_id"], object())
        self.assertEqual(registry.calls, [])

    def test_owner_approval_allows_single_explicit_registry_call(self):
        self.import_one()
        candidate_path = self.root / "candidates.json"
        candidate = PromotionCandidateBuilder(candidate_path).build(
            pattern_id="pattern-1",
            records=self.ledger.external_records(),
            metric_thresholds={"save_rate": 0.05},
            minimum_sample_size=50,
        )
        registry = FakeRegistry()
        controller = PromotionController(candidate_path, registry=registry)
        controller.review(
            candidate["promotion_candidate_id"],
            owner_approved=True,
            approved_by="owner",
        )
        pattern = object()
        self.assertIs(controller.promote_approved(candidate["promotion_candidate_id"], pattern), pattern)
        self.assertEqual(registry.calls, [(pattern, True, True)])


if __name__ == "__main__":
    unittest.main()
