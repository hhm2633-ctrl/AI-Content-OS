from __future__ import annotations

import copy
import unittest

from modules.source_intake.portfolio_candidate_selector import run_portfolio_candidate_selector


def test_malformed_router_output_is_closed_without_mutation():
    router_result = {"status": "closed", "reason_code": "input_error", "routes": []}
    snapshot = copy.deepcopy(router_result)

    result = run_portfolio_candidate_selector(router_result)

    assert result["status"] == "closed"
    assert result["fallback_used"] is True
    assert result["selected_count"] == 0
    assert router_result == snapshot


def test_bare_route_list_is_rejected_because_router_contract_is_required():
    result = run_portfolio_candidate_selector([])
    assert result["status"] == "closed"
    assert result["fallback_used"] is True


def test_deterministic_ordering_score_confidence_and_candidate_id_tie_break():
    router_result = {
        "status": "routed",
        "routes": [
            {
                "format": "card_news",
                "candidate_id": "c3",
                "score": 0.7,
                "confidence": 0.5,
                "reasons": [],
                "missing_requirements": [],
                "cluster_id": "cl1",
            },
            {
                "format": "card_news",
                "candidate_id": "c2",
                "score": 0.8,
                "confidence": 0.4,
                "reasons": [],
                "missing_requirements": [],
                "cluster_id": "cl2",
            },
            {
                "format": "card_news",
                "candidate_id": "c1",
                "score": 0.8,
                "confidence": 0.4,
                "reasons": [],
                "missing_requirements": [],
                "cluster_id": "cl3",
            },
            {
                "format": "card_news",
                "candidate_id": "c4",
                "score": 0.8,
                "confidence": 0.45,
                "reasons": [],
                "missing_requirements": [],
                "cluster_id": "cl4",
            },
        ],
    }

    result = run_portfolio_candidate_selector(router_result)

    assert result["status"] == "selected"
    selected = result["selected_by_format"]["card_news"]
    assert [item["candidate_id"] for item in selected[:4]] == ["c4", "c1", "c2", "c3"]


def test_per_format_limits_are_honored():
    router_result = {
        "status": "routed",
        "routes": [
            {"format": "card_news", "candidate_id": "c1", "score": 0.9, "confidence": 0.9, "reasons": [], "missing_requirements": [], "cluster_id": "cl1"},
            {"format": "card_news", "candidate_id": "c2", "score": 0.8, "confidence": 0.8, "reasons": [], "missing_requirements": [], "cluster_id": "cl2"},
            {"format": "card_news", "candidate_id": "c3", "score": 0.7, "confidence": 0.7, "reasons": [], "missing_requirements": [], "cluster_id": "cl3"},
            {"format": "commerce", "candidate_id": "c4", "score": 0.9, "confidence": 0.9, "reasons": [], "missing_requirements": [], "cluster_id": "cl4"},
            {"format": "commerce", "candidate_id": "c5", "score": 0.8, "confidence": 0.8, "reasons": [], "missing_requirements": [], "cluster_id": "cl5"},
        ],
    }
    result = run_portfolio_candidate_selector(
        router_result,
        per_format_limits={"card_news": 2, "commerce": 1, "shorts_reels": 1},
    )

    assert len(result["selected_by_format"]["card_news"]) == 2
    assert len(result["selected_by_format"]["commerce"]) == 1
    assert [item["candidate_id"] for item in result["not_selected"] if item["format"] == "card_news"] == ["c3"]
    assert any(item["candidate_id"] == "c5" and item["reason_code"] == "format_limit_exceeded" for item in result["not_selected"])


def test_cluster_dedup_within_format():
    router_result = {
        "status": "routed",
        "routes": [
            {"format": "shorts_reels", "candidate_id": "c1", "score": 0.9, "confidence": 0.9, "reasons": [], "missing_requirements": [], "cluster_id": "cl-a"},
            {"format": "shorts_reels", "candidate_id": "c2", "score": 0.8, "confidence": 0.8, "reasons": [], "missing_requirements": [], "cluster_id": "cl-a"},
            {"format": "shorts_reels", "candidate_id": "c3", "score": 0.85, "confidence": 0.85, "reasons": [], "missing_requirements": [], "cluster_id": "cl-b"},
        ],
    }

    result = run_portfolio_candidate_selector(
        router_result,
        per_format_limits={"shorts_reels": 5, "card_news": 5, "commerce": 5},
    )

    selected = result["selected_by_format"]["shorts_reels"]
    assert [item["candidate_id"] for item in selected] == ["c1", "c3"]
    assert any(item["reason_code"] == "duplicate_cluster" for item in result["not_selected"])


def test_selector_fail_closed_on_malformed_route_payload():
    router_result = {
        "status": "routed",
        "routes": [
            {"format": "card_news", "candidate_id": "c1", "score": "high", "confidence": 0.9, "reasons": [], "missing_requirements": []},
        ],
    }

    result = run_portfolio_candidate_selector(router_result)

    assert result["status"] == "closed"
    assert result["fallback_used"] is True
    assert result["reason_code"] == "malformed_route_metrics"


def test_selector_does_not_mutate_router_output():
    router_result = {
        "status": "routed",
        "routes": [
            {"format": "card_news", "candidate_id": "c1", "score": 0.9, "confidence": 0.9, "reasons": [], "missing_requirements": [], "cluster_id": "cl1"},
        ],
    }
    snapshot = copy.deepcopy(router_result)

    run_portfolio_candidate_selector(router_result)

    assert router_result == snapshot


class TestPortfolioCandidateSelector(unittest.TestCase):
    def test_spark_contract_cases(self):
        cases = [
            value
            for name, value in sorted(globals().items())
            if name.startswith("test_") and callable(value)
        ]
        for case in cases:
            with self.subTest(case=case.__name__):
                case()
