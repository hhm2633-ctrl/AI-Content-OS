import json
import os
import shutil
import unittest
import uuid

from modules.source_intake.collector_readiness_registry import (
    REASON_COUNT_MISMATCH,
    REASON_DUPLICATE_SOURCE,
    REASON_MALFORMED_JSON,
    REASON_SOURCE_NOT_READY,
    REASON_UNKNOWN_SOURCE,
    CollectorReadinessRegistryError,
    load_collector_readiness_registry,
)


class TestCollectorReadinessRegistry(unittest.TestCase):
    def setUp(self):
        self.root = os.path.join(".", f"collector-readiness-registry-{uuid.uuid4().hex}")
        os.makedirs(self.root, exist_ok=True)
        self.bundle_path = os.path.join(self.root, "source_intake_status_bundle.json")
        self.gap_path = os.path.join(self.root, "collection_gap_report.json")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_json(self, path: str, payload) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

    def test_ready_source_accepted(self):
        self._write_json(
            self.bundle_path,
            {
                "classification_source_count": 1,
                "readiness_status_counts": {
                    "ready": 1,
                    "partial": 0,
                    "blocked": 0,
                    "external_blocked": 0,
                },
            },
        )
        self._write_json(
            self.gap_path,
            {
                "source_status_by_readiness": {
                    "ready": [{"source_id": "daum_news"}],
                    "partial": [],
                    "blocked": [],
                    "external_blocked": [],
                },
                "source_count": 1,
            },
        )

        registry = load_collector_readiness_registry(self.bundle_path)
        record = registry.get("daum_news")
        self.assertTrue(record["selectable"])
        self.assertEqual(record["readiness_status"], "ready")
        self.assertEqual(registry.require_ready("daum_news"), record)

    def test_partial_blocked_external_blocked_and_unknown_source_rejected(self):
        self._write_json(
            self.bundle_path,
            {
                "classification_source_count": 4,
                "readiness_status_counts": {
                    "ready": 1,
                    "partial": 1,
                    "blocked": 1,
                    "external_blocked": 1,
                },
            },
        )
        self._write_json(
            self.gap_path,
            {
                "source_status_by_readiness": {
                    "ready": [{"source_id": "nate_pann"}],
                    "partial": [{"source_id": "fmkorea"}],
                    "blocked": [{"source_id": "ppomppu"}],
                    "external_blocked": [{"source_id": "instiz"}],
                },
                "source_count": 4,
            },
        )

        registry = load_collector_readiness_registry(self.bundle_path)
        for source_id in ("fmkorea", "ppomppu", "instiz"):
            query = registry.get(source_id)
            self.assertFalse(query["selectable"])
            self.assertEqual(query["reason_code"], REASON_SOURCE_NOT_READY)
            with self.assertRaises(CollectorReadinessRegistryError) as cm:
                registry.require_ready(source_id)
            self.assertEqual(cm.exception.reason_code, REASON_SOURCE_NOT_READY)

        with self.assertRaises(CollectorReadinessRegistryError) as cm:
            registry.require_ready("missing-source")
        self.assertEqual(cm.exception.reason_code, REASON_UNKNOWN_SOURCE)

    def test_registry_rejects_malformed_duplicate_and_count_mismatch(self):
        with open(self.bundle_path, "w", encoding="utf-8") as handle:
            handle.write("{bad json")
        self._write_json(
            self.gap_path,
            {
                "source_status_by_readiness": {
                    "ready": [],
                    "partial": [],
                    "blocked": [],
                    "external_blocked": [],
                },
                "source_count": 0,
            },
        )
        with self.assertRaises(CollectorReadinessRegistryError) as cm:
            load_collector_readiness_registry(self.bundle_path)
        self.assertEqual(cm.exception.reason_code, REASON_MALFORMED_JSON)

        self._write_json(
            self.bundle_path,
            {
                "classification_source_count": 2,
                "readiness_status_counts": {
                    "ready": 2,
                    "partial": 0,
                    "blocked": 0,
                    "external_blocked": 0,
                },
            },
        )
        self._write_json(
            self.gap_path,
            {
                "source_status_by_readiness": {
                    "ready": [{"source_id": "newsis"}, {"source_id": "newsis"}],
                    "partial": [],
                    "blocked": [],
                    "external_blocked": [],
                },
                "source_count": 2,
            },
        )
        with self.assertRaises(CollectorReadinessRegistryError) as cm:
            load_collector_readiness_registry(self.bundle_path)
        self.assertEqual(cm.exception.reason_code, REASON_DUPLICATE_SOURCE)

        self._write_json(
            self.gap_path,
            {
                "source_status_by_readiness": {
                    "ready": [{"source_id": "newsis"}],
                    "partial": [],
                    "blocked": [],
                    "external_blocked": [],
                },
                "source_count": 1,
            },
        )
        with self.assertRaises(CollectorReadinessRegistryError) as cm:
            load_collector_readiness_registry(self.bundle_path)
        self.assertEqual(cm.exception.reason_code, REASON_COUNT_MISMATCH)


if __name__ == "__main__":
    unittest.main()
