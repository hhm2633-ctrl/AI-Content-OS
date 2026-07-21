"""Deterministic shallow risk-indicator detection for source-intake candidates.

The detector intentionally reports indicators rather than factual conclusions.  It
does not fetch detail pages and absence of a match never produces a ``safe`` state.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


RISK_DETECTOR_SCHEMA_VERSION = "candidate_risk_detector_v1"
DEFAULT_RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "source_intake_risk_rules.json"
RISK_STATUSES = frozenset({"blocked", "needs_evidence", "undetermined"})
_TEXT_FIELDS = ("title", "keyword", "summary", "board_or_category", "board", "category")


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _strings(item)


def _field_text(candidate: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in _TEXT_FIELDS:
        parts = [part.strip() for part in _strings(candidate.get(field)) if part.strip()]
        if parts:
            result[field] = " ".join(parts).casefold()
    return result


def _ordered_unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _indicator(field: str, term: str, rule: str, severity: str) -> dict[str, str]:
    return {"field": field, "term": term, "rule": rule, "severity": severity}


def _term_hits(text_by_field: Mapping[str, str], terms: Iterable[str]) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    normalized_terms = _ordered_unique(str(term).strip().casefold() for term in terms)
    for field, text in text_by_field.items():
        for term in normalized_terms:
            if term and term in text:
                hits.append((field, term))
    return hits


def _regex_hits(text_by_field: Mapping[str, str], patterns: Iterable[str]) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for field, text in text_by_field.items():
        for pattern in patterns:
            try:
                match = re.search(str(pattern), text, flags=re.IGNORECASE)
            except re.error:
                continue
            if match:
                hits.append((field, match.group(0)))
    return hits


def _valid_rule_config(config: Any) -> bool:
    if not isinstance(config, Mapping):
        return False
    if not isinstance(config.get("hard_rules"), list) or not isinstance(config.get("soft_rules"), list):
        return False
    for severity in ("hard_rules", "soft_rules"):
        for rule in config[severity]:
            if (
                not isinstance(rule, Mapping)
                or not isinstance(rule.get("id"), str)
                or not isinstance(rule.get("flag"), str)
            ):
                return False
            if not isinstance(rule.get("evidence_need"), str):
                return False
            if severity == "hard_rules":
                groups = rule.get("all_term_groups")
                if not isinstance(groups, list) or len(groups) < 2 or not all(isinstance(group, list) for group in groups):
                    return False
            elif not isinstance(rule.get("terms"), list):
                return False
    return True


def _closed_result(reason: str) -> dict[str, Any]:
    return {
        "schema_version": RISK_DETECTOR_SCHEMA_VERSION,
        "status": "invalid",
        "reason_code": reason,
        "risk_status": "undetermined",
        "hard_risk_flags": [],
        "soft_risk_flags": [],
        "evidence_needs": ["manual_shallow_risk_review"],
        "matched_indicators": [],
        "calibration": "initial_unvalidated",
    }


def detect_candidate_risks(
    candidate: Mapping[str, Any],
    *,
    rules_path: str | Path = DEFAULT_RULES_PATH,
) -> dict[str, Any]:
    """Return shallow risk indicators without mutating ``candidate``.

    Hard rules require configured combinations (all term groups, plus any required
    regex group).  Soft rules are keyword indicators only and therefore always
    request corroborating evidence rather than assert that a claim is true.
    """

    if not isinstance(candidate, Mapping):
        return _closed_result("invalid_candidate")

    try:
        config = json.loads(Path(rules_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return _closed_result("risk_rules_unavailable")
    if not _valid_rule_config(config):
        return _closed_result("invalid_risk_rules")

    text_by_field = _field_text(candidate)
    hard_flags: list[str] = []
    soft_flags: list[str] = []
    evidence_needs: list[str] = []
    indicators: list[dict[str, str]] = []

    for rule in config["hard_rules"]:
        groups = rule.get("all_term_groups", [])
        if not isinstance(groups, list) or len(groups) < 2:
            continue
        group_hits = [_term_hits(text_by_field, group) for group in groups if isinstance(group, list)]
        if len(group_hits) != len(groups) or any(not hits for hits in group_hits):
            continue
        regexes = rule.get("regex_any", [])
        regex_hits = _regex_hits(text_by_field, regexes) if isinstance(regexes, list) else []
        if rule.get("require_regex") is True and not regex_hits:
            continue
        hard_flags.append(rule["flag"])
        evidence_needs.append(rule["evidence_need"])
        for field, term in [hit for hits in group_hits for hit in hits] + regex_hits:
            indicators.append(_indicator(field, term, rule["id"], "hard"))

    for rule in config["soft_rules"]:
        terms = rule.get("terms", [])
        hits = _term_hits(text_by_field, terms) if isinstance(terms, list) else []
        regexes = rule.get("regex_any", [])
        if isinstance(regexes, list):
            hits.extend(_regex_hits(text_by_field, regexes))
        if not hits:
            continue
        soft_flags.append(rule["flag"])
        evidence_needs.append(rule["evidence_need"])
        for field, term in hits:
            indicators.append(_indicator(field, term, rule["id"], "soft"))

    hard_flags = _ordered_unique(hard_flags)
    soft_flags = _ordered_unique(soft_flags)
    evidence_needs = _ordered_unique(evidence_needs)
    unique_indicators: list[dict[str, str]] = []
    seen = set()
    for item in indicators:
        key = (item["field"], item["term"], item["rule"], item["severity"])
        if key not in seen:
            seen.add(key)
            unique_indicators.append(item)

    if hard_flags:
        risk_status = "blocked"
    elif soft_flags:
        risk_status = "needs_evidence"
    else:
        risk_status = "undetermined"

    return {
        "schema_version": RISK_DETECTOR_SCHEMA_VERSION,
        "config_schema_version": config.get("schema_version"),
        "status": "ok",
        "reason_code": "indicators_detected" if hard_flags or soft_flags else "no_shallow_indicator_detected",
        "risk_status": risk_status,
        "hard_risk_flags": hard_flags,
        "soft_risk_flags": soft_flags,
        "evidence_needs": evidence_needs,
        "matched_indicators": unique_indicators,
        "calibration": config.get("calibration", "initial_unvalidated"),
    }


__all__ = [
    "DEFAULT_RULES_PATH",
    "RISK_DETECTOR_SCHEMA_VERSION",
    "RISK_STATUSES",
    "detect_candidate_risks",
]
