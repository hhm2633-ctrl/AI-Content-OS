"""Standalone composition of Stage-1 normalization and Stage-2 categorization.

This module derives only conservative shallow heuristics.  It does not collect
detail pages, call an LLM, write storage, route formats, or touch WorkflowEngine.
Qualitative signals that cannot be supported by the shallow candidate remain
missing and therefore reduce Stage-2 confidence instead of becoming fake zeroes.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple
from urllib.parse import urlsplit

from modules.source_intake.candidate_evidence_bundle import build_candidate_evidence_bundle
from modules.source_intake.candidate_risk_detector import detect_candidate_risks
from modules.source_intake.category_specific_signal_builder import build_category_specific_signals
from modules.source_intake.category_stage2_selector import (
    DEFAULT_CONFIG_PATH,
    run_category_stage2_selector,
)
from modules.source_intake.common_candidate_signals import build_common_candidate_signals
from modules.source_intake.hierarchical_signal_normalizer import (
    run_hierarchical_signal_normalizer,
)
from modules.source_intake.origin_independence_resolver import resolve_origin_independence


CATEGORY_CANDIDATE_PIPELINE_VERSION = "category_candidate_pipeline_v1"


def _closed(reason_code: str, reason: str, diagnostics: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    return {
        "schema_version": CATEGORY_CANDIDATE_PIPELINE_VERSION,
        "status": "closed",
        "reason_code": reason_code,
        "reason": reason,
        "production_wired": False,
        "collection_executed": False,
        "items": [],
        "item_count": 0,
        "diagnostics": copy.deepcopy(dict(diagnostics or {})),
    }


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _load_config(config_path: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with Path(config_path).open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError, TypeError) as exc:
        return None, f"config load failed safely: {type(exc).__name__}"
    return (value, None) if isinstance(value, dict) else (None, "config must be an object")


def _candidate_id(candidate: Mapping[str, Any]) -> str:
    existing = _text(candidate.get("candidate_id"))
    if existing:
        return existing
    stable_parts = [
        _text(candidate.get("link")),
        _text(candidate.get("title") or candidate.get("keyword")),
        _text(candidate.get("source_id")),
    ]
    digest = hashlib.sha256("\n".join(stable_parts).encode("utf-8")).hexdigest()[:20]
    return f"candidate:{digest}"


def _signal(stage1: Mapping[str, Any], name: str) -> Optional[float]:
    record = stage1.get(name)
    if not isinstance(record, Mapping) or record.get("status") != "observed":
        return None
    value = record.get("normalized_value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if 0.0 <= float(value) <= 1.0 else None


def _attention(stage1: Mapping[str, Any]) -> Tuple[Optional[float], Optional[float], List[str]]:
    values: List[float] = []
    confidences: List[float] = []
    used: List[str] = []
    for name in ("rank_position", "views", "comments", "likes"):
        value = _signal(stage1, name)
        if value is None:
            continue
        values.append(value)
        used.append(name)
        record = stage1.get(name, {})
        confidence = record.get("confidence") if isinstance(record, Mapping) else None
        if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
            confidences.append(max(0.0, min(1.0, float(confidence))))
    if not values:
        return None, None, []
    return (
        round(sum(values) / len(values), 6),
        round(sum(confidences) / len(confidences), 6) if confidences else None,
        used,
    )


def _fit_scores(candidate: Mapping[str, Any], config: Mapping[str, Any]) -> Tuple[Dict[str, float], Dict[str, Any]]:
    taxonomy = list(config["taxonomy"])
    rules = config.get("fit_heuristics", {})
    keywords = rules.get("category_keywords", {})
    lane_map = rules.get("lane_category", {})
    source_type_map = rules.get("source_type_category", {})
    full_count = max(1, int(rules.get("keyword_full_match_count", 2)))
    keyword_weight = float(rules.get("keyword_weight", 0.75))
    lane_weight = float(rules.get("lane_weight", 0.2))
    lane_primary_weight = float(rules.get("lane_primary_weight", 0.0))
    lane_primary = rules.get("lane_primary_category", {})
    source_type_weight = float(rules.get("source_type_weight", 0.15))
    searchable = " ".join(
        _text(candidate.get(field)).lower()
        for field in ("title", "keyword", "summary", "board_or_category", "category")
    )
    lane = _text(candidate.get("source_lane_id"))
    source_type = _text(candidate.get("source_type"))
    fits: Dict[str, float] = {}
    details: Dict[str, Any] = {}
    for category_id in taxonomy:
        terms = [term for term in keywords.get(category_id, []) if isinstance(term, str) and term]
        matched = [term for term in terms if term.lower() in searchable]
        lexical = min(len(matched) / full_count, 1.0)
        lane_match = category_id in lane_map.get(lane, [])
        source_match = category_id in source_type_map.get(source_type, [])
        primary_lane_match = lane_primary.get(lane) == category_id
        score = min(
            1.0,
            lexical * keyword_weight
            + (lane_weight if lane_match else 0.0)
            + (lane_primary_weight if primary_lane_match else 0.0)
            + (source_type_weight if source_match else 0.0),
        )
        fits[category_id] = round(score, 6)
        details[category_id] = {
            "matched_keywords": matched,
            "lane_match": lane_match,
            "primary_lane_match": primary_lane_match,
            "source_type_match": source_match,
            "method": "initial_unvalidated_shallow_heuristic",
        }
    return fits, details


def _official_origin_verification(candidate: Mapping[str, Any], config: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    evidence = config.get("evidence", {})
    allowed = [
        domain.lower().strip(".")
        for domain in evidence.get("authoritative_origin_domains", [])
        if isinstance(domain, str)
    ]
    link = _text(candidate.get("link"))
    if not link.startswith("https://"):
        return None
    try:
        parsed_link = urlsplit(link)
        hostname = (parsed_link.hostname or "").lower().strip(".")
        port = parsed_link.port
    except ValueError:
        return None
    if port not in (None, 443) or parsed_link.username is not None or parsed_link.password is not None:
        return None
    if not any(hostname == domain or hostname.endswith(f".{domain}") for domain in allowed):
        return None
    return {
        "verified": False,
        "source_url": link,
        "verification_status": "official_domain_identity_only",
        "original_document_status": "unknown",
        "claim_alignment": None,
        "verification_method": "configured_official_domain_candidate_allowlist",
    }


def _signal_record(value: Optional[float], confidence: Optional[float], provenance: Any, reason: str) -> Dict[str, Any]:
    return {
        "value": value,
        "status": "observed" if value is not None else "missing",
        "provenance": copy.deepcopy(provenance),
        "confidence": float(confidence) if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) else 0.0,
        "reason": reason,
    }


def _unwrap_category_signals(records: Mapping[str, Any]) -> Dict[str, Dict[str, Optional[float]]]:
    output: Dict[str, Dict[str, Optional[float]]] = {}
    for category_id, category in records.items():
        if not isinstance(category, Mapping):
            continue
        output[str(category_id)] = {
            str(name): (record.get("value") if isinstance(record, Mapping) else None)
            for name, record in category.items()
        }
    return output


def _merge_string_lists(*values: Any) -> List[str]:
    output: List[str] = []
    for value in values:
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str) and item.strip() and item.strip() not in output:
                output.append(item.strip())
    return output


def run_category_candidate_pipeline(candidates: Any, config_path: Any = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Normalize and classify a shallow candidate batch without side effects."""
    config, config_error = _load_config(config_path)
    if config_error or config is None:
        return _closed("invalid_config", config_error or "config unavailable")
    post_selection_excluded: List[Dict[str, Any]] = []
    topic_candidates = candidates
    if isinstance(candidates, list):
        topic_candidates = []
        for candidate in candidates:
            if isinstance(candidate, Mapping) and candidate.get("post_selection_only") is True:
                post_selection_excluded.append({
                    "candidate_id": _candidate_id(candidate),
                    "source_id": _text(candidate.get("source_id")),
                    "reason_code": "post_selection_catalog_not_topic_candidate",
                })
                continue
            if isinstance(candidate, Mapping) and candidate.get("editorial_topic_eligible") is False:
                post_selection_excluded.append({
                    "candidate_id": _candidate_id(candidate),
                    "source_id": _text(candidate.get("source_id")),
                    "reason_code": "supporting_source_not_topic_candidate",
                    "topic_selection_role": _text(candidate.get("topic_selection_role")) or None,
                })
                continue
            topic_candidates.append(candidate)
    stage1_result = run_hierarchical_signal_normalizer(topic_candidates)
    if stage1_result.get("status") != "ok":
        return _closed("stage1_closed", stage1_result.get("reason", "Stage 1 closed"), {"stage1": stage1_result})
    results: List[Dict[str, Any]] = []
    for raw in stage1_result.get("items", []):
        candidate = copy.deepcopy(raw)
        candidate["candidate_id"] = _candidate_id(candidate)
        stage1 = candidate["stage1_normalized_signals"]
        attention, attention_confidence, attention_used = _attention(stage1)
        stage1["attention"] = attention
        stage1["attention_confidence"] = attention_confidence
        fit, fit_details = _fit_scores(candidate, config)
        common_result = build_common_candidate_signals(candidate, stage1)
        origin_result = resolve_origin_independence(candidate)
        risk_result = detect_candidate_risks(candidate)
        evidence_bundle = build_candidate_evidence_bundle(candidate)
        origin = copy.deepcopy(origin_result.get("origin_independence", {"score": None}))
        spread = copy.deepcopy(origin_result.get("distribution_spread", {"score": None}))
        common_records = copy.deepcopy(common_result.get("signals", {}))
        attention_record = _signal_record(
            attention,
            attention_confidence,
            {"stage1_components_used": attention_used},
            "mean of observed Stage-1 attention components",
        )
        common_records["attention"] = attention_record
        common_records["reaction_strength"] = copy.deepcopy(attention_record)
        tag_records = common_result.get("tags", {}) if isinstance(common_result.get("tags"), Mapping) else {}
        seasonality_record = tag_records.get("seasonality")
        seasonality_values = seasonality_record.get("value") if isinstance(seasonality_record, Mapping) else None
        common_records["seasonality"] = _signal_record(
            1.0 if isinstance(seasonality_values, list) and seasonality_values else 0.0 if isinstance(seasonality_values, list) else None,
            seasonality_record.get("confidence") if isinstance(seasonality_record, Mapping) else None,
            seasonality_record.get("provenance", {}) if isinstance(seasonality_record, Mapping) else {},
            "presence of an observed seasonality tag",
        )
        category_detail = build_category_specific_signals(
            candidate,
            stage1,
            common_records,
            origin_result,
        )
        candidate["category_fit_all"] = fit
        candidate["origin_independence"] = origin
        candidate["distribution_spread"] = spread
        freshness_record = common_records.get("freshness", {})
        freshness_provenance = (
            freshness_record.get("provenance", {})
            if isinstance(freshness_record, Mapping)
            else {}
        )
        candidate["freshness"] = {
            **copy.deepcopy(freshness_record),
            "score": freshness_record.get("value") if isinstance(freshness_record, Mapping) else None,
            "age_hours": (
                freshness_provenance.get("age_hours")
                if isinstance(freshness_provenance, Mapping)
                else None
            ),
        }
        candidate["category_signals"] = _unwrap_category_signals(
            category_detail.get("category_signals", {})
        )
        candidate["hard_risk_flags"] = _merge_string_lists(
            candidate.get("hard_risk_flags"), risk_result.get("hard_risk_flags")
        )
        candidate["soft_risk_flags"] = _merge_string_lists(
            candidate.get("soft_risk_flags"), risk_result.get("soft_risk_flags")
        )
        candidate["evidence_needs"] = _merge_string_lists(
            candidate.get("evidence_needs"),
            risk_result.get("evidence_needs"),
            evidence_bundle.get("bundle_evidence_needs"),
        )
        candidate["evidence_bundle"] = copy.deepcopy(evidence_bundle)
        candidate["risk_detection_status"] = risk_result.get("risk_status", "undetermined")
        candidate["risk_detector_status"] = risk_result.get("status", "invalid")
        international_record = tag_records.get("international", {})
        commerce_record = tag_records.get("commerce_signal", {})
        candidate["tags"] = {
            "international": international_record.get("value") is True if isinstance(international_record, Mapping) else False,
            "commerce_signal": commerce_record.get("value") is True if isinstance(commerce_record, Mapping) else False,
            "seasonality": seasonality_values[0] if isinstance(seasonality_values, list) and seasonality_values else None,
        }
        official_verification = _official_origin_verification(candidate, config)
        candidate["authoritative_official_origin"] = False
        if official_verification is not None:
            candidate["authoritative_origin_verification"] = official_verification
        stage2 = run_category_stage2_selector(candidate, config_path=config_path)
        stage2["feature_diagnostics"] = {
            "fit": fit_details,
            "attention_components_used": attention_used,
            "shallow_heuristics_only": True,
            "qualitative_missing_remains_missing": True,
            "common_signals": copy.deepcopy(common_result),
            "category_signal_records": copy.deepcopy(category_detail.get("category_signals", {})),
            "risk_detection": copy.deepcopy(risk_result),
            "origin_resolution": copy.deepcopy(origin_result),
            "evidence_bundle": copy.deepcopy(evidence_bundle),
        }
        results.append(stage2)
    return {
        "schema_version": CATEGORY_CANDIDATE_PIPELINE_VERSION,
        "status": "ok",
        "reason_code": "ok",
        "reason": "standalone Stage-1 and Stage-2 candidate processing completed",
        "production_wired": False,
        "collection_executed": False,
        "items": results,
        "item_count": len(results),
        "diagnostics": {
            "stage1": stage1_result.get("diagnostics", {}),
            "post_selection_excluded": post_selection_excluded,
            "post_selection_excluded_count": len(post_selection_excluded),
            "decision_counts": {decision: sum(1 for item in results if item.get("decision") == decision) for decision in ("GO", "NEEDS_EVIDENCE", "WATCH", "REJECT")},
            "calibration_status": config.get("calibration_status"),
        },
    }


__all__ = ["run_category_candidate_pipeline", "CATEGORY_CANDIDATE_PIPELINE_VERSION"]
