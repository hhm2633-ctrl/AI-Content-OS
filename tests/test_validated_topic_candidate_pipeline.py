from __future__ import annotations

import json
import tempfile
from pathlib import Path

from modules.source_intake.validated_topic_candidate_pipeline import (
    run_validated_topic_candidate_pipeline,
)


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_ready_multi_source_input_produces_candidate_ready_with_composed_diagnostics() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        bundle_path = root / "source_intake_status_bundle.json"
        gap_path = root / "collection_gap_report.json"

        _write_json(
            gap_path,
            {
                "source_status_by_readiness": {
                    "ready": [{"source_id": "s1"}, {"source_id": "s2"}],
                    "partial": [],
                    "blocked": [],
                    "external_blocked": [],
                },
                "source_count": 2,
            },
        )
        _write_json(
            bundle_path,
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

        payload_path = root / "daily_shallow_collection.json"
        _write_json(
            payload_path,
            {
                "schema_version": "daily_shallow_collection_v1",
                "items": [
                    {"source_id": "s1", "keyword": "A", "title": "A"},
                    {"source_id": "s2", "keyword": "B", "title": "B"},
                ],
            },
        )

        result = run_validated_topic_candidate_pipeline(
            daily_shallow_collection=str(payload_path),
            source_intake_status_bundle_path=str(bundle_path),
            collection_gap_report_path=str(gap_path),
        )

        assert result["status"] == "candidate_ready"
        assert len(result["candidates"]) == 2
        assert result["stage_diagnostics"]["registry"]["status"] == "ok"
        assert result["stage_diagnostics"]["adapter"]["status"] == "ok"
        assert result["stage_diagnostics"]["quality_gate"]["status"] == "ok"
        assert result["stage_diagnostics"]["quality_gate"]["candidate_count"] == 2


def test_non_ready_or_unknown_only_input_closes_with_zero_candidates() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        bundle_path = root / "source_intake_status_bundle.json"
        gap_path = root / "collection_gap_report.json"

        _write_json(
            gap_path,
            {
                "source_status_by_readiness": {
                    "ready": [],
                    "partial": [{"source_id": "s1"}, {"source_id": "s_unknown"}],
                    "blocked": [],
                    "external_blocked": [],
                },
                "source_count": 2,
            },
        )
        _write_json(
            bundle_path,
            {
                "classification_source_count": 2,
                "readiness_status_counts": {
                    "ready": 0,
                    "partial": 2,
                    "blocked": 0,
                    "external_blocked": 0,
                },
            },
        )

        payload_path = root / "daily_shallow_collection.json"
        _write_json(
            payload_path,
            {
                "schema_version": "daily_shallow_collection_v1",
                "items": [
                    {"source_id": "s_unknown", "keyword": "A", "title": "A"},
                    {"source_id": "s1", "keyword": "B", "title": "B"},
                ],
            },
        )

        result = run_validated_topic_candidate_pipeline(
            daily_shallow_collection=str(payload_path),
            source_intake_status_bundle_path=str(bundle_path),
            collection_gap_report_path=str(gap_path),
        )

        assert result["status"] == "closed"
        assert result["candidates"] == []
        assert result["stage_diagnostics"]["adapter"]["status"] == "closed"
        assert result["stage_diagnostics"]["adapter"]["reason_code"] == "no_ready_items"
        assert result["stage_diagnostics"]["quality_gate"]["status"] == "closed"
        assert result["stage_diagnostics"]["quality_gate"]["reason_code"] == "no_candidates"


def test_malformed_registry_or_adapter_input_closes_without_exception_leakage_or_fabrication() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        bad_bundle_path = root / "source_intake_status_bundle.json"
        gap_path = root / "collection_gap_report.json"
        _write_json(
            gap_path,
            {
                "source_status_by_readiness": {"ready": [{"source_id": "s1"}], "partial": [], "blocked": [], "external_blocked": []},
                "source_count": 1,
            },
        )
        # Malformed registry payload: missing object -> JSON string without braces is invalid.
        bad_bundle_path.write_text("{", encoding="utf-8")

        payload_path = root / "daily_shallow_collection.json"
        payload_path.write_text("{\"schema_version\":", encoding="utf-8")

        bad_bundle_result = run_validated_topic_candidate_pipeline(
            daily_shallow_collection=str(payload_path),
            source_intake_status_bundle_path=str(bad_bundle_path),
            collection_gap_report_path=str(gap_path),
        )
        assert bad_bundle_result["status"] == "closed"
        assert bad_bundle_result["candidates"] == []

        malformed_payload = root / "bad_payload.json"
        malformed_payload.write_text("[1,2,3]", encoding="utf-8")

        good_bundle_path = root / "good_bundle.json"
        _write_json(
            good_bundle_path,
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

        malformed_payload_result = run_validated_topic_candidate_pipeline(
            daily_shallow_collection=str(malformed_payload),
            source_intake_status_bundle_path=str(good_bundle_path),
            collection_gap_report_path=str(gap_path),
        )
        assert malformed_payload_result["status"] == "closed"
        assert malformed_payload_result["candidates"] == []
        assert malformed_payload_result["stage_diagnostics"]["adapter"]["status"] == "closed"
        assert malformed_payload_result["stage_diagnostics"]["registry"]["status"] == "ok"
