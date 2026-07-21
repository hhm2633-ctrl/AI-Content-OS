from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from typing import Any, Dict, List, Mapping, MutableSequence, Sequence


SOURCE_AGREEMENT_VERSION = "source_agreement_v1"

TRACKING_QUERY_BLACKLIST = {
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


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _normalize_text(value: Any) -> str:
    return " ".join(_coerce_str(value).strip().lower().split())


def _tokenize_title(value: Any) -> List[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return []
    return normalized.split()


def _url_canonical(raw_url: Any) -> str:
    if not isinstance(raw_url, str):
        return ""

    text = raw_url.strip()
    if not text:
        return ""

    parsed = urlsplit(text)

    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_pairs = [
        (key, value)
        for key, value in query_pairs
        if key.lower().strip() not in TRACKING_QUERY_BLACKLIST
    ]
    filtered_pairs.sort(key=lambda item: (item[0], item[1]))

    canonical_query = urlencode(filtered_pairs)
    path = parsed.path

    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, canonical_query, ""))


def _title_similarity(a: Sequence[str], b: Sequence[str]) -> float:
    if not a or not b:
        return 0.0

    left = set(a)
    right = set(b)
    if not left and not right:
        return 0.0

    intersection = len(left & right)
    union = len(left | right)
    if union <= 0:
        return 0.0

    return intersection / union


def _build_cluster_row(
    representative: Dict[str, Any],
    member_items: List[Dict[str, Any]],
    index: int,
    min_distinct_sources: int,
) -> Dict[str, Any]:
    sources: List[str] = []
    source_seen = set()
    attributed_count = 0
    unattributed_count = 0

    for item in member_items:
        source_id = item.get("source_id") or ""
        if source_id:
            normalized = _normalize_text(source_id)
        else:
            normalized = ""

        if not normalized:
            unattributed_count += 1
            continue

        if normalized not in source_seen:
            source_seen.add(normalized)
            sources.append(normalized)
        attributed_count += 1

    distinct_source_count = len(sources)
    agreement = distinct_source_count >= max(1, int(min_distinct_sources))

    return {
        "cluster_index": index,
        "agreement_status": "agreed" if agreement else "single_source",
        "agreed": agreement,
        "source_ids": sources,
        "distinct_source_count": distinct_source_count,
        "attributed_item_count": attributed_count,
        "unattributed_item_count": unattributed_count,
        "representative_index": representative["index"],
        "representative_title": representative["title"],
        "representative_link": representative["link"],
        "member_indexes": [item["index"] for item in member_items],
        "member_count": len(member_items),
    }


def build_source_agreement(
    items: Any,
    min_distinct_sources: int = 2,
    title_similarity_threshold: float = 0.6,
) -> Dict[str, Any]:
    """Build deterministic source agreement clusters from candidate trend items.

    Contract: offline-only, deterministic, no mutation, no I/O.
    """

    if not isinstance(min_distinct_sources, int):
        min_distinct_sources = 2
    if not isinstance(title_similarity_threshold, (int, float)):
        title_similarity_threshold = 0.6

    min_distinct_sources = max(1, int(min_distinct_sources))

    if not isinstance(items, list):
        return {
            "status": "closed",
            "reason_code": "malformed_items",
            "reason": "items must be a list",
            "source_agreement_version": SOURCE_AGREEMENT_VERSION,
            "total_items": 0,
            "clusters": [],
            "summary": {
                "total_clusters": 0,
                "agreed_clusters": 0,
                "single_source_clusters": 0,
                "agreed_items": 0,
                "single_source_items": 0,
            },
        }

    if not items:
        return {
            "status": "closed",
            "reason_code": "no_items",
            "reason": "no source candidates provided",
            "source_agreement_version": SOURCE_AGREEMENT_VERSION,
            "total_items": 0,
            "clusters": [],
            "summary": {
                "total_clusters": 0,
                "agreed_clusters": 0,
                "single_source_clusters": 0,
                "agreed_items": 0,
                "single_source_items": 0,
            },
        }

    prepared: List[Dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            title = ""
            link = ""
            source_id = ""
        else:
            title = _coerce_str(item.get("title") or item.get("keyword") or "")
            link = _coerce_str(item.get("link") or item.get("url") or "")
            source_id = _coerce_str(item.get("source_id") or "")

        prepared.append(
            {
                "index": index,
                "title": title,
                "title_tokens": _tokenize_title(title),
                "link": link,
                "canonical_link": _url_canonical(link),
                "source_id": source_id,
                "source_id_norm": _normalize_text(source_id),
            }
        )

    clusters: List[Dict[str, Any]] = []

    for current in prepared:
        found_cluster = None

        if current["canonical_link"]:
            for cluster in clusters:
                if cluster.get("canonical_key") == current["canonical_link"]:
                    found_cluster = cluster
                    break

        if found_cluster is None:
            for cluster in clusters:
                # Title similarity fallback uses representative title tokens.
                if _title_similarity(current["title_tokens"], cluster["rep_tokens"]) >= float(title_similarity_threshold):
                    found_cluster = cluster
                    break

        if found_cluster is None:
            cluster = {
                "canonical_key": current["canonical_link"],
                "rep_tokens": current["title_tokens"],
                "representative": {
                    "index": current["index"],
                    "title": current["title"],
                    "link": current["link"],
                },
                "members": [],
            }
            clusters.append(cluster)
            found_cluster = cluster

        found_cluster["members"].append(current)

    final_clusters = []
    summary = {
        "total_clusters": len(clusters),
        "agreed_clusters": 0,
        "single_source_clusters": 0,
        "agreed_items": 0,
        "single_source_items": 0,
    }

    for idx, cluster in enumerate(clusters):
        row = _build_cluster_row(
            representative={
                "index": cluster["representative"]["index"],
                "title": cluster["representative"]["title"],
                "link": cluster["representative"]["link"],
            },
            member_items=cluster["members"],
            index=idx,
            min_distinct_sources=min_distinct_sources,
        )
        if row["agreed"]:
            summary["agreed_clusters"] += 1
            summary["agreed_items"] += row["member_count"]
        else:
            summary["single_source_clusters"] += 1
            summary["single_source_items"] += row["member_count"]

        final_clusters.append(row)

    return {
        "status": "ok",
        "reason_code": None,
        "reason": "source agreement clusters computed",
        "source_agreement_version": SOURCE_AGREEMENT_VERSION,
        "total_items": len(prepared),
        "clusters": final_clusters,
        "summary": summary,
    }


__all__ = ["build_source_agreement", "SOURCE_AGREEMENT_VERSION"]
