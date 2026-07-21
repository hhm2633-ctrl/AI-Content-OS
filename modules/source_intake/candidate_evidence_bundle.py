"""Build a shallow, provenance-bearing candidate evidence bundle.

This module does no collection and does not verify the truth of a claim.  It
separates factual-origin candidates from distribution appearances, records only
supplied HTTPS official-domain URLs as official-document *candidates*, and keeps
claim-to-evidence alignment explicitly unresolved for later review.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Dict, Iterable, Mapping, Optional
from urllib.parse import urlsplit, urlunsplit

from modules.source_intake.origin_independence_resolver import (
    resolve_origin_independence,
)


CANDIDATE_EVIDENCE_BUNDLE_VERSION = "candidate_evidence_bundle_v1"

# Domain identity only.  A match makes the supplied URL a document candidate;
# it does not establish that the page is original, current, or claim-aligned.
OFFICIAL_DOMAIN_SUFFIXES = (
    "go.kr",
    "korea.kr",
    "assembly.go.kr",
    "scourt.go.kr",
    "bok.or.kr",
    "kostat.go.kr",
    "dart.fss.or.kr",
)

URL_FIELDS = ("link", "url", "source_url", "official_url", "document_url")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _ordered_unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen = set()
    for value in values:
        normalized = _text(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def _closed(reason_code: str) -> Dict[str, Any]:
    return {
        "schema_version": CANDIDATE_EVIDENCE_BUNDLE_VERSION,
        "status": "closed",
        "reason_code": reason_code,
        "candidate_id": None,
        "factual_origin_evidence": {
            "status": "unknown", "score": None, "independent_origin_count": 0,
            "origin_groups": [], "items": [], "confidence": 0.0,
            "provenance": [], "unresolved": [reason_code],
        },
        "distribution_evidence": {
            "status": "unknown", "score": None, "distribution_count": 0,
            "source_ids": [], "items": [], "confidence": 0.0,
            "provenance": [], "unresolved": [reason_code],
        },
        "official_document_candidates": [],
        "claims": [],
        "bundle_evidence_needs": ["manual_evidence_bundle_review"],
        "warnings": [reason_code],
    }


def _source_observations(candidate: Mapping[str, Any]) -> tuple[list[Dict[str, Any]], list[str]]:
    """Return supplied source records and malformed-location warnings."""
    observations = [{"location": "candidate", "record": candidate}]
    warnings: list[str] = []

    refs = candidate.get("source_refs")
    if refs is not None:
        if not isinstance(refs, list):
            warnings.append("malformed_source_refs")
        else:
            for index, record in enumerate(refs):
                if isinstance(record, Mapping):
                    observations.append({"location": f"source_refs[{index}]", "record": record})
                else:
                    warnings.append(f"malformed_source_ref:{index}")

    agreement = candidate.get("source_agreement")
    if agreement is not None:
        if not isinstance(agreement, Mapping):
            warnings.append("malformed_source_agreement")
        else:
            sources = agreement.get("sources")
            if sources is not None:
                if not isinstance(sources, list):
                    warnings.append("malformed_source_agreement_sources")
                else:
                    for index, record in enumerate(sources):
                        if isinstance(record, Mapping):
                            observations.append({
                                "location": f"source_agreement.sources[{index}]",
                                "record": record,
                            })
                        else:
                            warnings.append(f"malformed_source_agreement_source:{index}")
    return observations, warnings


def _canonical_https_url(value: Any) -> Optional[tuple[str, str]]:
    raw = _text(value)
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        hostname = (parsed.hostname or "").lower().strip(".")
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() != "https" or not hostname or parsed.username or parsed.password:
        return None
    netloc = hostname
    if port and port != 443:
        netloc = f"{hostname}:{port}"
    normalized = urlunsplit(("https", netloc, parsed.path or "/", parsed.query, ""))
    return normalized, hostname


def _is_official_host(hostname: str) -> bool:
    return any(
        hostname == suffix or hostname.endswith(f".{suffix}")
        for suffix in OFFICIAL_DOMAIN_SUFFIXES
    )


def _official_documents(observations: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    by_url: Dict[str, Dict[str, Any]] = {}
    for observation in observations:
        location = observation["location"]
        record = observation["record"]
        for field in URL_FIELDS:
            parsed = _canonical_https_url(record.get(field))
            if parsed is None:
                continue
            url, hostname = parsed
            if not _is_official_host(hostname):
                continue
            evidence = by_url.setdefault(url, {
                "evidence_id": _stable_id("official-document", url),
                "evidence_type": "official_document_candidate",
                "url": url,
                "hostname": hostname,
                "verification_status": "official_domain_identity_only",
                "original_document_status": "unknown",
                "claim_alignment": None,
                "confidence": 0.9,
                "provenance": [],
                "reason": "supplied HTTPS URL matches an official-domain suffix; document content was not fetched",
            })
            evidence["provenance"].append({"location": location, "field": field})
    for item in by_url.values():
        item["provenance"].sort(key=lambda row: (row["location"], row["field"]))
    return sorted(by_url.values(), key=lambda item: (item["url"], item["evidence_id"]))


def _origin_axis(origin_result: Mapping[str, Any]) -> Dict[str, Any]:
    origin = origin_result.get("origin_independence")
    if not isinstance(origin, Mapping):
        return _closed("invalid_origin_result")["factual_origin_evidence"]
    groups = [item for item in origin.get("origin_groups", []) if isinstance(item, str)]
    provenance = copy.deepcopy(origin.get("provenance", [])) if isinstance(origin.get("provenance"), list) else []
    provenance_by_group: Dict[str, list[Dict[str, Any]]] = {group: [] for group in groups}
    for row in provenance:
        if isinstance(row, Mapping) and row.get("origin_group") in provenance_by_group:
            provenance_by_group[row["origin_group"]].append(copy.deepcopy(dict(row)))
    items = [
        {
            "evidence_id": _stable_id("factual-origin", group),
            "evidence_type": "factual_origin_candidate",
            "origin_group": group,
            "claim_alignment": None,
            "confidence": origin.get("confidence", 0.0),
            "provenance": sorted(
                provenance_by_group[group],
                key=lambda row: (str(row.get("method", "")), str(row.get("location", ""))),
            ),
            "reason": "origin identity resolved from supplied shallow metadata; claim content was not verified",
        }
        for group in sorted(groups)
    ]
    return {
        "status": "candidate_evidence_available" if groups else "unknown",
        "score": copy.deepcopy(origin.get("score")),
        "independent_origin_count": len(groups),
        "origin_groups": sorted(groups),
        "items": items,
        "confidence": copy.deepcopy(origin.get("confidence", 0.0)),
        "provenance": provenance,
        "unresolved": sorted(set(
            item for item in origin.get("unresolved", []) if isinstance(item, str)
        )),
    }


def _distribution_axis(origin_result: Mapping[str, Any]) -> Dict[str, Any]:
    spread = origin_result.get("distribution_spread")
    if not isinstance(spread, Mapping):
        return _closed("invalid_origin_result")["distribution_evidence"]
    source_ids = sorted({item for item in spread.get("source_ids", []) if isinstance(item, str)})
    provenance = copy.deepcopy(spread.get("provenance", [])) if isinstance(spread.get("provenance"), list) else []
    provenance_by_source: Dict[str, list[Dict[str, Any]]] = {source_id: [] for source_id in source_ids}
    for row in provenance:
        if isinstance(row, Mapping) and row.get("source_id") in provenance_by_source:
            provenance_by_source[row["source_id"]].append(copy.deepcopy(dict(row)))
    items = [
        {
            "evidence_id": _stable_id("distribution", source_id),
            "evidence_type": "distribution_appearance",
            "source_id": source_id,
            "factual_origin": False,
            "confidence": spread.get("confidence", 0.0),
            "provenance": provenance_by_source[source_id],
            "reason": "appearance/spread evidence only; it is not an independent factual origin",
        }
        for source_id in source_ids
    ]
    return {
        "status": "distribution_observed" if source_ids else "unknown",
        "score": copy.deepcopy(spread.get("score")),
        "distribution_count": len(source_ids),
        "source_ids": source_ids,
        "items": items,
        "confidence": copy.deepcopy(spread.get("confidence", 0.0)),
        "provenance": provenance,
        "unresolved": sorted(set(
            item for item in spread.get("unresolved", []) if isinstance(item, str)
        )),
    }


def _string_list(value: Any) -> Optional[list[str]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return _ordered_unique(value)


def _claim_inputs(candidate: Mapping[str, Any]) -> tuple[Optional[list[Dict[str, Any]]], list[str]]:
    supplied = candidate.get("claims")
    warnings: list[str] = []
    if supplied is None:
        claim_text = _text(candidate.get("title") or candidate.get("keyword"))
        if not claim_text:
            return [], ["no_supplied_claim"]
        return [{
            "claim_id": _text(candidate.get("candidate_id")) or "candidate-claim",
            "text": claim_text,
            "evidence_needs": [],
            "requires_official_document": False,
            "provenance": "candidate.title_or_keyword",
        }], warnings
    if not isinstance(supplied, list):
        return None, ["malformed_claims"]
    claims: list[Dict[str, Any]] = []
    for index, raw in enumerate(supplied):
        if isinstance(raw, str):
            text = _text(raw)
            if not text:
                return None, [f"malformed_claim:{index}"]
            claims.append({
                "claim_id": f"claim-{index + 1}", "text": text,
                "evidence_needs": [], "requires_official_document": False,
                "provenance": f"candidate.claims[{index}]",
            })
            continue
        if not isinstance(raw, Mapping) or not _text(raw.get("text") or raw.get("claim")):
            return None, [f"malformed_claim:{index}"]
        needs = _string_list(raw.get("evidence_needs"))
        if needs is None:
            return None, [f"malformed_claim_evidence_needs:{index}"]
        claims.append({
            "claim_id": _text(raw.get("claim_id")) or f"claim-{index + 1}",
            "text": _text(raw.get("text") or raw.get("claim")),
            "evidence_needs": needs,
            "requires_official_document": raw.get("requires_official_document") is True,
            "provenance": f"candidate.claims[{index}]",
        })
    return claims, warnings


def _claims(
    candidate: Mapping[str, Any],
    factual: Mapping[str, Any],
    official_documents: list[Dict[str, Any]],
) -> tuple[Optional[list[Dict[str, Any]]], list[str]]:
    raw_claims, warnings = _claim_inputs(candidate)
    if raw_claims is None:
        return None, warnings
    global_needs = _string_list(candidate.get("evidence_needs"))
    if global_needs is None:
        return None, ["malformed_candidate_evidence_needs"]

    evidence_ids = [item["evidence_id"] for item in factual.get("items", [])]
    official_ids = [item["evidence_id"] for item in official_documents]
    origin_count = factual.get("independent_origin_count", 0)
    results: list[Dict[str, Any]] = []
    for raw in raw_claims:
        needs = list(global_needs) + list(raw["evidence_needs"])
        if not isinstance(origin_count, int) or origin_count < 2:
            needs.append("independent_factual_origin")
        if raw["requires_official_document"]:
            # A supplied official-domain URL is only a document candidate.  Its
            # originalness and claim alignment are unknown until separately
            # verified, so it cannot satisfy this evidence need by itself.
            needs.append("official_original_document")
        # Source identity alone cannot establish that its content supports this
        # particular claim, even when multiple origins or an official URL exist.
        needs.append("claim_to_evidence_alignment_review")
        needs = _ordered_unique(needs)
        results.append({
            "claim_id": raw["claim_id"],
            "claim_text": raw["text"],
            "status": "needs_evidence" if needs else "unknown",
            "evidence_needs": needs,
            "candidate_evidence_ids": evidence_ids + official_ids,
            "verified_evidence_ids": [],
            "claim_alignment": None,
            "confidence": 0.0,
            "provenance": raw["provenance"],
            "reason": "candidate source evidence is available for review but claim alignment is unverified",
        })
    return results, warnings


def build_candidate_evidence_bundle(candidate: Any) -> Dict[str, Any]:
    """Build an offline evidence bundle from supplied shallow metadata only."""
    if not isinstance(candidate, Mapping):
        return _closed("invalid_candidate")

    observations, warnings = _source_observations(candidate)
    origin_result = resolve_origin_independence(candidate)
    factual = _origin_axis(origin_result)
    distribution = _distribution_axis(origin_result)
    official_documents = _official_documents(observations)
    claims, claim_warnings = _claims(candidate, factual, official_documents)
    warnings.extend(claim_warnings)
    if claims is None:
        result = _closed(claim_warnings[0] if claim_warnings else "invalid_claims")
        result["candidate_id"] = copy.deepcopy(candidate.get("candidate_id"))
        result["factual_origin_evidence"] = factual
        result["distribution_evidence"] = distribution
        result["official_document_candidates"] = official_documents
        result["warnings"] = sorted(set(warnings))
        return result

    bundle_needs = _ordered_unique(
        need for claim in claims for need in claim["evidence_needs"]
    )
    if not claims:
        bundle_needs.append("supplied_claim_required")
    status = "ok" if not any(warning.startswith("malformed_") for warning in warnings) else "partial"
    return {
        "schema_version": CANDIDATE_EVIDENCE_BUNDLE_VERSION,
        "status": status,
        "reason_code": "bundle_built" if status == "ok" else "bundle_built_with_unresolved_metadata",
        "candidate_id": copy.deepcopy(candidate.get("candidate_id")),
        "factual_origin_evidence": factual,
        "distribution_evidence": distribution,
        "official_document_candidates": official_documents,
        "claims": claims,
        "bundle_evidence_needs": bundle_needs,
        "warnings": sorted(set(warnings)),
    }


__all__ = [
    "CANDIDATE_EVIDENCE_BUNDLE_VERSION",
    "OFFICIAL_DOMAIN_SUFFIXES",
    "build_candidate_evidence_bundle",
]
