"""Resolve factual origin independence separately from distribution spread.

The resolver is deliberately shallow and offline-only.  It trusts only source,
publisher, link, attribution, and source-reference metadata already supplied on
the candidate.  A portal or community appearance is distribution evidence, not
an additional factual news origin.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Tuple
from urllib.parse import urlsplit


ORIGIN_INDEPENDENCE_RESOLVER_VERSION = "origin_independence_resolver_v1"

PORTAL_SOURCE_IDS = {"naver_news", "daum_news", "nate_news_rank"}
WIRE_SOURCE_IDS = {"yonhap", "newsis", "news1"}
COMMUNITY_SOURCE_IDS = {
    "nate_pann", "fmkorea", "bobaedream", "dcinside", "theqoo",
    "ppomppu", "ruliweb", "dogdrip",
}
DIRECT_NEWS_SOURCE_IDS = {
    "yonhap", "newsis", "news1", "hankyung_economy", "mk_economy",
    "moneytoday", "edaily",
}
APPROVED_SOURCE_IDS = (
    PORTAL_SOURCE_IDS | WIRE_SOURCE_IDS | COMMUNITY_SOURCE_IDS |
    DIRECT_NEWS_SOURCE_IDS
)

SOURCE_DOMAINS = {
    "naver_news": ("news.naver.com", "n.news.naver.com"),
    "daum_news": ("news.daum.net", "v.daum.net"),
    "nate_news_rank": ("news.nate.com",),
    "yonhap": ("yna.co.kr",),
    "newsis": ("newsis.com",),
    "news1": ("news1.kr",),
    "hankyung_economy": ("hankyung.com",),
    "mk_economy": ("mk.co.kr",),
    "moneytoday": ("mt.co.kr",),
    "edaily": ("edaily.co.kr",),
    "nate_pann": ("pann.nate.com",),
    "fmkorea": ("fmkorea.com",),
    "bobaedream": ("bobaedream.co.kr",),
    "dcinside": ("dcinside.com",),
    "theqoo": ("theqoo.net",),
    "ppomppu": ("ppomppu.co.kr",),
    "ruliweb": ("ruliweb.com",),
    "dogdrip": ("dogdrip.net",),
}

PUBLISHER_ALIASES = {
    "yonhap": {"yonhap", "yonhap news", "yna", "연합뉴스"},
    "newsis": {"newsis", "뉴시스"},
    "news1": {"news1", "news 1", "뉴스1", "뉴스 1"},
    "hankyung_economy": {"hankyung", "한경", "한국경제", "한국경제신문"},
    "mk_economy": {"mk", "매경", "매일경제", "매일경제신문"},
    "moneytoday": {"moneytoday", "머니투데이"},
    "edaily": {"edaily", "이데일리"},
}

NON_ORIGIN_PUBLISHER_NAMES = {
    "naver", "naver news", "naver_news", "네이버", "네이버뉴스",
    "daum", "daum news", "daum_news", "다음", "다음뉴스",
    "nate", "nate news", "nate_news_rank", "네이트", "네이트뉴스",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalized(value: Any) -> str:
    return " ".join(_text(value).lower().split())


def _slug(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣._-]+", "-", _normalized(value)).strip("-")


def _host(link: Any) -> str:
    raw = _text(link)
    if not raw:
        return ""
    try:
        return (urlsplit(raw).hostname or "").lower().strip(".")
    except ValueError:
        return ""


def _source_from_host(hostname: str) -> Optional[str]:
    if not hostname:
        return None
    for source_id, domains in SOURCE_DOMAINS.items():
        if any(hostname == domain or hostname.endswith(f".{domain}") for domain in domains):
            return source_id
    return None


def _publisher_sources(value: Any) -> List[str]:
    normalized = _normalized(value)
    if not normalized:
        return []
    matches: List[str] = []
    for source_id, aliases in PUBLISHER_ALIASES.items():
        if normalized in aliases:
            matches.append(source_id)
    return matches


def _attributed_sources(value: Any) -> List[str]:
    normalized = _normalized(value)
    if not normalized:
        return []
    matches: List[str] = []
    for source_id, aliases in PUBLISHER_ALIASES.items():
        found = False
        for alias in aliases:
            if re.fullmatch(r"[a-z0-9 ]+", alias):
                pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
                found = re.search(pattern, normalized) is not None
            else:
                found = len(alias) >= 2 and alias in normalized
            if found:
                break
        if found:
            matches.append(source_id)
    return matches


def _record_from_mapping(value: Mapping[str, Any], location: str) -> Dict[str, Any]:
    return {
        "location": location,
        "source_id": _normalized(value.get("source_id")),
        "source_type": _normalized(value.get("source_type")),
        "publisher": _text(value.get("publisher")),
        "link": _text(value.get("link") or value.get("url")),
        "attribution": _text(value.get("source_attribution") or value.get("attribution")),
    }


def _observations(candidate: Mapping[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    observations = [_record_from_mapping(candidate, "candidate")]
    unresolved: List[str] = []

    agreement = candidate.get("source_agreement")
    if agreement is not None and not isinstance(agreement, Mapping):
        unresolved.append("malformed_source_agreement")
    elif isinstance(agreement, Mapping):
        sources = agreement.get("sources", [])
        if not isinstance(sources, list):
            unresolved.append("malformed_source_agreement_sources")
        else:
            for index, source in enumerate(sources):
                if isinstance(source, Mapping):
                    observations.append(_record_from_mapping(source, f"source_agreement.sources[{index}]"))
                else:
                    unresolved.append(f"malformed_source_agreement_source:{index}")

    refs = candidate.get("source_refs", [])
    if refs is not None and not isinstance(refs, list):
        unresolved.append("malformed_source_refs")
    elif isinstance(refs, list):
        for index, source in enumerate(refs):
            if isinstance(source, Mapping):
                observations.append(_record_from_mapping(source, f"source_refs[{index}]"))
            else:
                unresolved.append(f"malformed_source_ref:{index}")
    return observations, unresolved


def _origin_candidates(observation: Mapping[str, Any]) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """Return ``[(origin source id/group, evidence method)]`` and an unresolved code."""

    source_id = _text(observation.get("source_id"))
    publisher = _text(observation.get("publisher"))
    attribution = _text(observation.get("attribution"))
    linked_source = _source_from_host(_host(observation.get("link")))

    if source_id and source_id not in APPROVED_SOURCE_IDS:
        return [], "unapproved_source_id"

    attributed = _attributed_sources(attribution)
    if attributed:
        return [(item, "supplied_attribution") for item in attributed], None

    publisher_sources = _publisher_sources(publisher)
    if publisher_sources:
        return [(item, "supplied_publisher") for item in publisher_sources], None

    if linked_source in DIRECT_NEWS_SOURCE_IDS:
        return [(linked_source, "supplied_link_domain")], None

    if source_id in WIRE_SOURCE_IDS:
        return [(source_id, "direct_wire_source_id")], None

    if source_id in (DIRECT_NEWS_SOURCE_IDS - WIRE_SOURCE_IDS):
        return [(source_id, "direct_news_source_id")], None

    if source_id in PORTAL_SOURCE_IDS:
        publisher_norm = _normalized(publisher)
        if publisher_norm and publisher_norm not in NON_ORIGIN_PUBLISHER_NAMES:
            publisher_slug = _slug(publisher)
            if publisher_slug:
                return [(f"publisher:{publisher_slug}", "supplied_underlying_publisher")], None
        return [], "portal_underlying_origin_unknown"

    if source_id in COMMUNITY_SOURCE_IDS:
        return [], "community_factual_origin_unknown"

    return [], "factual_origin_unknown"


def _origin_score(count: int) -> Optional[float]:
    if count <= 0:
        return None
    if count == 1:
        return 0.5
    if count == 2:
        return 0.8
    return 1.0


def _spread_score(count: int) -> Optional[float]:
    if count <= 0:
        return None
    return round(min(count / 3.0, 1.0), 6)


def _empty(reason: str, status: str = "closed") -> Dict[str, Any]:
    return {
        "schema_version": ORIGIN_INDEPENDENCE_RESOLVER_VERSION,
        "status": status,
        "reason_code": reason,
        "origin_independence": {
            "score": None,
            "independent_origin_count": 0,
            "origin_groups": [],
            "confidence": 0.0,
            "provenance": [],
            "unresolved": [reason],
        },
        "distribution_spread": {
            "score": None,
            "distribution_count": 0,
            "source_ids": [],
            "confidence": 0.0,
            "provenance": [],
            "unresolved": [reason],
        },
    }


def resolve_origin_independence(candidate: Any) -> Dict[str, Any]:
    """Resolve supplied shallow source metadata without I/O or input mutation."""

    if not isinstance(candidate, Mapping):
        return _empty("invalid_candidate_type")

    observations, parse_unresolved = _observations(candidate)
    origin_methods: Dict[str, set] = {}
    origin_provenance: List[Dict[str, Any]] = []
    origin_unresolved = list(parse_unresolved)
    distributions: Dict[str, set] = {}
    distribution_provenance: List[Dict[str, Any]] = []
    distribution_unresolved = list(parse_unresolved)

    for observation in observations:
        source_id = _text(observation.get("source_id"))
        location = _text(observation.get("location"))
        if source_id in APPROVED_SOURCE_IDS:
            distributions.setdefault(source_id, set()).add(location)
        elif source_id:
            distribution_unresolved.append(f"unapproved_source_id:{location}")
        else:
            distribution_unresolved.append(f"missing_source_id:{location}")

        origins, unresolved = _origin_candidates(observation)
        if unresolved:
            origin_unresolved.append(f"{unresolved}:{location}")
        for group, method in origins:
            origin_methods.setdefault(group, set()).add(method)
            origin_provenance.append({
                "origin_group": group,
                "method": method,
                "location": location,
            })

    for source_id in sorted(distributions):
        distribution_provenance.append({
            "source_id": source_id,
            "locations": sorted(distributions[source_id]),
        })

    origin_groups = sorted(origin_methods)
    distribution_ids = sorted(distributions)
    origin_count = len(origin_groups)
    distribution_count = len(distribution_ids)
    strong_methods = {"direct_wire_source_id", "direct_news_source_id", "supplied_link_domain"}
    strong_count = sum(1 for methods in origin_methods.values() if methods & strong_methods)
    origin_confidence = 0.0 if not origin_groups else round(
        min(1.0, (0.7 * strong_count + 0.55 * (origin_count - strong_count)) / origin_count), 6
    )
    distribution_confidence = 0.0 if not distribution_ids else 1.0

    status = "ok" if origin_groups or distribution_ids else "closed"
    reason_code = "resolved" if origin_groups else "origin_unresolved"
    return {
        "schema_version": ORIGIN_INDEPENDENCE_RESOLVER_VERSION,
        "status": status,
        "reason_code": reason_code,
        "origin_independence": {
            "score": _origin_score(origin_count),
            "independent_origin_count": origin_count,
            "origin_groups": origin_groups,
            "confidence": origin_confidence,
            "provenance": sorted(
                origin_provenance,
                key=lambda row: (row["origin_group"], row["method"], row["location"]),
            ),
            "unresolved": sorted(set(origin_unresolved)),
        },
        "distribution_spread": {
            "score": _spread_score(distribution_count),
            "distribution_count": distribution_count,
            "source_ids": distribution_ids,
            "confidence": distribution_confidence,
            "provenance": distribution_provenance,
            "unresolved": sorted(set(distribution_unresolved)),
        },
    }


__all__ = [
    "ORIGIN_INDEPENDENCE_RESOLVER_VERSION",
    "resolve_origin_independence",
]
