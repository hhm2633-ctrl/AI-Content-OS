"""Quality gate for validated topic input candidates.

This module is intentionally deterministic and pure: it consumes only the
`{"trends": [...], "source_diagnostics": {...}}` output shape and returns a
stable, non-mutating deduped set with source agreement metadata.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TOPIC_INPUT_QUALITY_GATE_VERSION = "topic_input_quality_gate_v1"
TOPIC_INPUT_QUALITY_GATE_SCHEMA = "topic_input_quality_diagnostics_v1"

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "source",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_name",
    "utm_source",
    "utm_term",
    "utm_id",
}


def _fail_closed(reason_code: str, message: str, source_diagnostics: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "candidates": [],
        "quality_diagnostics": {
            "status": "closed",
            "reason_code": reason_code,
            "reason": message,
            "quality_gate_version": TOPIC_INPUT_QUALITY_GATE_VERSION,
            "schema_version": TOPIC_INPUT_QUALITY_GATE_SCHEMA,
            "source_status": source_diagnostics.get("status"),
            "source_reason_code": source_diagnostics.get("reason_code"),
        },
    }


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        return str(value)
    return value


def _normalize_text(value: Any) -> str:
    return " ".join(_coerce_text(value).strip().lower().split())


def _canonicalize_link(link: Any) -> Optional[str]:
    if not isinstance(link, str):
        return None if link is None else ""
    stripped = link.strip()
    if not stripped:
        return ""

    try:
        parsed = urlsplit(stripped)
    except ValueError:
        return None

    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    kept_pairs = [
        (key, value)
        for key, value in query_pairs
        if key.lower().strip() not in TRACKING_QUERY_KEYS
    ]
    kept_pairs.sort(key=lambda item: (item[0], item[1]))

    canonical_query = urlencode(kept_pairs)
    path = parsed.path.rstrip("/") or parsed.path
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            canonical_query,
            "",  # remove fragment and tracking-only fragments by policy
        )
    )


def _extract_source_agreement_source(record: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "source_id": _coerce_text(record.get("source_id")),
        "source_name": _coerce_text(record.get("source_name")),
        "publisher": _coerce_text(record.get("publisher") or record.get("source_name")),
        "source_type": _coerce_text(record.get("source_type")),
        "title": _coerce_text(record.get("title") or record.get("keyword")),
        "link": _coerce_text(record.get("link") or record.get("url")),
        "likes": record.get("likes"),
        "comments": record.get("comments"),
    }


def _agreement_from_sources(sources: MutableMapping[str, Dict[str, Any]]) -> Dict[str, Any]:
    source_list = list(sources.values())
    agreement_count = len(source_list)
    return {
        "agreement_count": agreement_count,
        "agreement_level": "multi_source_observed" if agreement_count > 1 else "single_source",
        "sources": source_list,
    }


def _append_evidence(
    source_by_id: OrderedDict,
    source_id: str,
    evidence: Mapping[str, Any],
) -> bool:
    if source_id in source_by_id:
        return False
    source_by_id[source_id] = dict(evidence)
    return True


def run_topic_input_quality_gate(
    validated_topic_input: Mapping[str, Any],
) -> Dict[str, Any]:
    if not isinstance(validated_topic_input, Mapping):
        return _fail_closed(
            "malformed_adapter_output",
            "validated_topic_input_output must be a dict",
            {},
        )

    trends = validated_topic_input.get("trends")
    source_diagnostics = validated_topic_input.get("source_diagnostics")

    if not isinstance(trends, list):
        return _fail_closed("malformed_adapter_output", "trends must be a list", source_diagnostics or {})
    if not isinstance(source_diagnostics, Mapping):
        return _fail_closed("malformed_adapter_output", "source_diagnostics must be a dict", {})

    if len(trends) == 0:
        return {
            "candidates": [],
            "quality_diagnostics": {
                "status": "closed",
                "reason_code": "no_candidates",
                "reason": "no validated trends were provided",
                "quality_gate_version": TOPIC_INPUT_QUALITY_GATE_VERSION,
                "schema_version": TOPIC_INPUT_QUALITY_GATE_SCHEMA,
                "source_status": source_diagnostics.get("status"),
            },
        }

    candidates: List[Dict[str, Any]] = []
    seen_url: Dict[str, int] = {}
    seen_text: Dict[str, int] = {}
    source_evidence: List[OrderedDict] = []
    dedupe_count = 0

    for index, trend in enumerate(trends):
        if not isinstance(trend, Mapping):
            return _fail_closed(
                "malformed_trend",
                f"trends[{index}] must be an object",
                source_diagnostics,
            )

        source_id = _normalize_text(trend.get("source_id"))
        if not source_id:
            return _fail_closed(
                "malformed_trend",
                f"trends[{index}].source_id must be non-empty",
                source_diagnostics,
            )

        raw_text = trend.get("title") or trend.get("keyword")
        normalized_text = _normalize_text(raw_text)
        if not normalized_text:
            return _fail_closed(
                "malformed_trend",
                f"trends[{index}] must include title or keyword",
                source_diagnostics,
            )

        if "link" in trend:
            link = _canonicalize_link(trend.get("link"))
            if link is None:
                return _fail_closed(
                    "malformed_trend",
                    f"trends[{index}].link must be a string or null",
                    source_diagnostics,
                )
            if link != "":
                url_key = f"url:{link}"
            else:
                url_key = ""
        else:
            url_key = ""

        text_key = f"text:{normalized_text}"

        candidate_index: Optional[int]
        if url_key and url_key in seen_url:
            candidate_index = seen_url[url_key]
        elif text_key in seen_text:
            candidate_index = seen_text[text_key]
        else:
            candidate_index = None

        source_snapshot = _extract_source_agreement_source(trend)

        if candidate_index is None:
            candidate = dict(trend)
            evidences = OrderedDict()
            _append_evidence(evidences, source_id, source_snapshot)
            candidate["source_agreement"] = _agreement_from_sources(evidences)
            candidates.append(candidate)
            source_evidence.append(evidences)
            source_index = len(candidates) - 1

            if url_key:
                seen_url[url_key] = source_index
            seen_text[text_key] = source_index
            continue

        dedupe_count += 1
        evidences = source_evidence[candidate_index]
        _append_evidence(evidences, source_id, source_snapshot)
        candidates[candidate_index]["source_agreement"] = _agreement_from_sources(evidences)

    for candidate in candidates:
        # Compact source evidence should be explicit on every candidate and
        # non-inflating with duplicate rows.
        if "source_agreement" not in candidate:
            evidence = OrderedDict()
            source_id = _normalize_text(candidate.get("source_id"))
            if source_id:
                _append_evidence(evidence, source_id, _extract_source_agreement_source(candidate))
            candidate["source_agreement"] = _agreement_from_sources(evidence)

    return {
        "candidates": candidates,
        "quality_diagnostics": {
            "status": "ok" if candidates else "closed",
            "reason_code": None if candidates else "no_candidates",
            "reason": "validated input was deduped and source agreement was computed" if candidates else "no surviving candidates",
            "quality_gate_version": TOPIC_INPUT_QUALITY_GATE_VERSION,
            "schema_version": TOPIC_INPUT_QUALITY_GATE_SCHEMA,
            "source_status": source_diagnostics.get("status"),
            "input_schema": source_diagnostics.get("schema_version"),
            "input_ready_count": source_diagnostics.get("ready_count"),
            "input_filtered_count": source_diagnostics.get("filtered_count"),
            "input_trend_count": len(trends),
            "candidate_count": len(candidates),
            "dedupe_count": dedupe_count,
        },
    }


__all__ = [
    "run_topic_input_quality_gate",
    "TOPIC_INPUT_QUALITY_GATE_VERSION",
    "TOPIC_INPUT_QUALITY_GATE_SCHEMA",
]
