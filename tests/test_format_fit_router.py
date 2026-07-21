from __future__ import annotations

import copy
import unittest

from modules.source_intake.format_fit_router import run_format_fit_router


def _candidate_with_format_fit(**overrides):
    base = {
        "candidate_id": "cand-001",
        "cluster_id": "cluster-a",
        "category": "tech",
        "source_id": "source-1",
        "source_lane_id": "lane-1",
        "source_type": "news",
        "source_attribution": {"source_id": "source-1", "lane_id": "lane-1"},
        "source_refs": [{"source_id": "source-1", "url": "https://example.com/1"}],
        "category_id": "domestic_news",
        "risk_status": "reviewed",
        "evidence_status": "READY",
    }
    base.update(overrides)
    return base


def test_absent_format_fit_is_closed_and_does_not_leak_exceptions():
    payload = {"candidate_id": "c1", "title": "테스트"}
    result = run_format_fit_router(payload)

    assert result["status"] == "closed"
    assert result["fallback_used"] is True
    assert result["reason_code"] == "missing_or_invalid_format_fit"
    assert result["routes"] == []


def test_invalid_assessment_is_closed_with_no_fabricated_route():
    payload = _candidate_with_format_fit(
        format_fit={
            "card_news": {
                "score": "high",
                "confidence": 0.9,
                "eligible": True,
                "reasons": [],
                "missing_requirements": [],
            }
        }
    )
    result = run_format_fit_router(payload)

    assert result["status"] == "closed"
    assert result["routes"] == []
    assert result["fallback_used"] is True


def test_multi_format_route_generation_and_score_confidence_separation():
    payload = _candidate_with_format_fit(
        format_fit={
            "card_news": {
                "score": 0.6,
                "confidence": 0.7,
                "eligible": True,
                "reasons": ["format match"],
                "missing_requirements": [],
            },
            "shorts_reels": {
                "score": 0.95,
                "confidence": 0.88,
                "eligible": True,
                "reasons": ["vertical confidence"],
                "missing_requirements": ["comment_ratio"],
            },
            "commerce": {
                "score": 0.2,
                "confidence": 0.21,
                "eligible": True,
                "reasons": ["low score"],
                "missing_requirements": ["partner"],
            },
        }
    )

    result = run_format_fit_router(payload, min_score=0.5, min_confidence=0.6)

    assert result["status"] == "routed"
    assert result["fallback_used"] is False
    assert result["route_count"] == 2
    assert {entry["format"] for entry in result["routes"]} == {"card_news", "shorts_reels"}
    assert all("score" in entry for entry in result["routes"])
    assert all("confidence" in entry for entry in result["routes"])
    assert result["routes"][0]["score"] == 0.6
    assert result["routes"][0]["confidence"] == 0.7
    assert result["routes"][0]["category_id"] == "domestic_news"
    assert result["routes"][0]["risk_status"] == "reviewed"
    assert result["routes"][0]["evidence_status"] == "READY"
    assert result["routes"][0]["source_refs"][0]["source_id"] == "source-1"


def test_ineligible_route_is_not_emitted_as_route():
    payload = _candidate_with_format_fit(
        format_fit={
            "commerce": {
                "score": 0.9,
                "confidence": 0.9,
                "eligible": False,
                "reasons": ["policy block"],
                "missing_requirements": ["policy_clearance"],
            }
        }
    )

    result = run_format_fit_router(payload)

    assert result["status"] == "closed"
    assert result["routes"] == []
    assert result["not_eligible_routes"]
    assert result["not_eligible_routes"][0]["reason_code"] == "ineligible_assessment"


def test_no_input_mutation_for_format_fit_router():
    payload = _candidate_with_format_fit(
        format_fit={
            "card_news": {
                "score": 0.9,
                "confidence": 0.9,
                "eligible": True,
                "reasons": ["ok"],
                "missing_requirements": [],
            }
        }
    )
    snapshot = copy.deepcopy(payload)

    run_format_fit_router(payload, min_score=0.5, min_confidence=0.5)

    assert payload == snapshot


def test_supported_formats_exactly_and_unknown_format_is_ignored():
    payload = _candidate_with_format_fit(
        format_fit={
            "card_news": {
                "score": 0.9,
                "confidence": 0.9,
                "eligible": True,
                "reasons": ["ok"],
                "missing_requirements": [],
            },
            "shorts_reels": {
                "score": 0.9,
                "confidence": 0.9,
                "eligible": True,
                "reasons": ["ok"],
                "missing_requirements": [],
            },
            "commerce": {
                "score": 0.9,
                "confidence": 0.9,
                "eligible": True,
                "reasons": ["ok"],
                "missing_requirements": [],
            },
            "unsupported_format": {
                "score": 1.0,
                "confidence": 1.0,
                "eligible": True,
                "reasons": [],
                "missing_requirements": [],
            },
        }
    )

    result = run_format_fit_router(payload)

    assert result["status"] == "routed"
    assert {entry["format"] for entry in result["routes"]} == {"card_news", "shorts_reels", "commerce"}


class TestFormatFitRouter(unittest.TestCase):
    def test_spark_contract_cases(self):
        cases = [
            value
            for name, value in sorted(globals().items())
            if name.startswith("test_") and callable(value)
        ]
        for case in cases:
            with self.subTest(case=case.__name__):
                case()
