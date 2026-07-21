"""Deterministic multi-tag classification and routing, independent of contracts."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parents[2] / "knowledge" / "taxonomy.json"
_TEXT_FIELDS = ("title", "summary", "project_relevance", "user_intent", "publisher")
_CLEAN = re.compile(r"[^0-9a-zA-Z가-힣_+.-]+")


class TaxonomyError(ValueError):
    pass


def normalize_term(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    return _CLEAN.sub("_", text).strip("_.-")


def _get(packet: Any, field: str, default: Any = None) -> Any:
    return packet.get(field, default) if isinstance(packet, Mapping) else getattr(packet, field, default)


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _string_list(value: Any, name: str, empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not empty and not value):
        raise TaxonomyError(f"{name} must be a list")
    if any(not isinstance(item, str) or not item.strip() for item in value) or len(value) != len(set(value)):
        raise TaxonomyError(f"{name} has invalid or duplicate values")
    return value


def validate_taxonomy(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or not isinstance(data.get("schema_version"), str):
        raise TaxonomyError("taxonomy and schema_version are required")
    fallback = data.get("unknown_fallback")
    if not isinstance(fallback, dict) or fallback.get("preserve_explicit_values") is not True:
        raise TaxonomyError("unknown_fallback must preserve explicit values")
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise TaxonomyError("categories must be a non-empty list")
    ids, aliases = [], {}
    for index, item in enumerate(categories):
        if not isinstance(item, dict) or normalize_term(item.get("id")) != item.get("id"):
            raise TaxonomyError(f"invalid category at {index}")
        if item["id"] in ids:
            raise TaxonomyError(f"duplicate category: {item['id']}")
        ids.append(item["id"])
        for field in ("aliases", "keywords", "default_domains"):
            _string_list(item.get(field), f"categories[{index}].{field}", True)
        for term in [item["id"], *item["aliases"]]:
            normalized = normalize_term(term)
            if normalized in aliases and aliases[normalized] != item["id"]:
                raise TaxonomyError(f"ambiguous alias: {term}")
            aliases[normalized] = item["id"]
    domains = _string_list(data.get("domains"), "domains")
    teams = _string_list(data.get("teams"), "teams")
    for item in categories:
        if set(item["default_domains"]) - set(domains):
            raise TaxonomyError(f"unknown domain in {item['id']}")
    rules = data.get("routing_rules")
    if not isinstance(rules, list):
        raise TaxonomyError("routing_rules must be a list")
    seen = set()
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict) or rule.get("category") not in ids or rule["category"] in seen:
            raise TaxonomyError(f"invalid routing rule at {index}")
        seen.add(rule["category"])
        if set(_string_list(rule.get("teams"), f"routing_rules[{index}].teams")) - set(teams):
            raise TaxonomyError(f"unknown team at routing rule {index}")
    defaults = data.get("source_type_defaults", {})
    if not isinstance(defaults, dict) or any(not isinstance(v, list) or set(v) - set(ids) for v in defaults.values()):
        raise TaxonomyError("invalid source_type_defaults")
    return data


def load_taxonomy(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else DEFAULT_TAXONOMY_PATH
    try:
        with target.open("r", encoding="utf-8") as handle:
            return validate_taxonomy(json.load(handle))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaxonomyError(f"cannot load taxonomy: {target}") from exc


def _ordered(values: set[str], order: Sequence[str]) -> list[str]:
    return [item for item in order if item in values] + sorted(values - set(order))


def classify(packet: Any, taxonomy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    tx = validate_taxonomy(dict(taxonomy)) if taxonomy is not None else load_taxonomy()
    category_order = [item["id"] for item in tx["categories"]]
    lookup = {normalize_term(term): item["id"] for item in tx["categories"] for term in [item["id"], *item["aliases"]]}
    explicit_tags = {term for term in (normalize_term(v) for v in _list(_get(packet, "tags", []))) if term}
    categories = {lookup[tag] for tag in explicit_tags if tag in lookup}
    unknown_tags = explicit_tags - set(lookup)
    categories.update(tx.get("source_type_defaults", {}).get(normalize_term(_get(packet, "source_type", "")), []))
    corpus = " ".join(unicodedata.normalize("NFKC", str(_get(packet, f, "") or "")).casefold() for f in _TEXT_FIELDS)
    for item in tx["categories"]:
        if any(unicodedata.normalize("NFKC", keyword).casefold() in corpus for keyword in item["keywords"]):
            categories.add(item["id"])
    known_domains, unknown_domains = set(), set()
    domain_set = set(tx["domains"])
    for domain in (normalize_term(v) for v in _list(_get(packet, "related_domains", []))):
        if domain:
            (known_domains if domain in domain_set else unknown_domains).add(domain)
    by_id = {item["id"]: item for item in tx["categories"]}
    for category in categories:
        known_domains.update(by_id[category]["default_domains"])
    ordered_categories = _ordered(categories, category_order)
    ordered_explicit = sorted(explicit_tags)
    tags = _ordered(set(ordered_categories) | set(ordered_explicit), category_order)
    domains = _ordered(known_domains, tx["domains"]) + sorted(unknown_domains)
    return {"categories": ordered_categories, "tags": tags, "known_tags": ordered_categories, "unknown_tags": sorted(unknown_tags), "related_domains": domains, "known_domains": _ordered(known_domains, tx["domains"]), "unknown_domains": sorted(unknown_domains), "classification_status": "classified" if ordered_categories else "unknown"}


def route(packet: Any, taxonomy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    tx = validate_taxonomy(dict(taxonomy)) if taxonomy is not None else load_taxonomy()
    result = classify(packet, tx)
    rules = {rule["category"]: rule["teams"] for rule in tx["routing_rules"]}
    teams, reasons = set(), {}
    for category in result["categories"]:
        for team in rules.get(category, []):
            teams.add(team); reasons.setdefault(team, []).append(category)
    unknown = set()
    for team in (normalize_term(v) for v in _list(_get(packet, "routed_teams", []))):
        if team in tx["teams"]:
            teams.add(team); reasons.setdefault(team, []).append("explicit")
        elif team:
            unknown.add(team)
    known = _ordered(teams, tx["teams"])
    return {**result, "routed_teams": known + sorted(unknown), "known_routed_teams": known, "unknown_routed_teams": sorted(unknown), "routing_reasons": {team: sorted(set(reasons[team])) for team in known}, "routing_status": "routed" if known else "unrouted"}


def classify_and_route(packet: Any, taxonomy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return route(packet, taxonomy)


class KnowledgeRouter:
    def __init__(self, taxonomy_path: str | Path | None = None, *, taxonomy: Mapping[str, Any] | None = None):
        if taxonomy_path is not None and taxonomy is not None:
            raise TaxonomyError("provide taxonomy_path or taxonomy, not both")
        self.taxonomy = validate_taxonomy(dict(taxonomy)) if taxonomy is not None else load_taxonomy(taxonomy_path)

    def classify(self, packet: Any) -> dict[str, Any]:
        return classify(packet, self.taxonomy)

    def route(self, packet: Any) -> dict[str, Any]:
        return route(packet, self.taxonomy)

    def classify_and_route(self, packet: Any) -> dict[str, Any]:
        return self.route(packet)


__all__ = ["DEFAULT_TAXONOMY_PATH", "KnowledgeRouter", "TaxonomyError", "classify", "classify_and_route", "load_taxonomy", "normalize_term", "route", "validate_taxonomy"]
