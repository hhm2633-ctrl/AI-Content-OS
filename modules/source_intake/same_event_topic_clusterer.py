"""Conservative shallow clustering for same-event / same-topic candidates.

This module performs conservative, offline-only grouping across shallow collection
items using normalized title signals, publication-time proximity, and source identity
including origin/distribution metadata. A bounded local semantic score may add a
small proxy bonus only after every existing deterministic hard gate passes.

No fact-checking, no external APIs, and no account/category routing are performed.
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from modules.source_intake.origin_independence_resolver import resolve_origin_independence
from modules.tool_adapters.sentence_transformers_runtime import (
    DEFAULT_SIMILARITY_TIMEOUT_SECONDS,
    MAX_SIMILARITY_PAIRS,
    score_text_pairs,
)


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "source_intake_clustering.json"
SAME_EVENT_TOPIC_CLUSTERER_VERSION = "same_event_topic_clusterer_v1"
SEMANTIC_SCORE_FLOOR = 0.70
SEMANTIC_MAX_BONUS = 0.06
SEMANTIC_SCORE_SEMANTICS = "internal_semantic_similarity_proxy"

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

KNOWN_PUNCT_PATTERN = re.compile(r"[^0-9a-zA-Z가-힣_]+")

_TITLE_NOISE_TOKENS = {
    "속보",
    "단독",
    "보도",
    "보도자료",
    "연합뉴스",
    "연합",
    "뉴스",
    "news",
    "기사",
    "기자",
    "오늘",
    "어제",
    "오후",
    "오전",
    "입장",
    "발표",
    "공개",
    "알려졌다",
    "전했다",
    "밝혔다",
    "제공",
    "관련",
    "특파원",
    "특보",
    "브리핑",
    "네이버",
    "다음",
    "nate",
    "naver",
    "daum",
    "yonhap",
    "newsis",
    "news1",
    "mk",
    "한경",
    "매일경제",
    "이데일리",
    "이데일리경제",
    "머니투데이",
    "edaily",
}

_TITLE_REWRITE_CANONICAL = {
    "정상화": "정상운행재개",
    "정상": "정상운행재개",
    "재개": "정상운행재개",
    "복구": "정상운행재개",
    "복귀": "정상운행재개",
}


def _rewrite_normalized_terms(terms: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(
        _TITLE_REWRITE_CANONICAL.get(token, token)
        for token in terms
        if isinstance(token, str)
    )


def _is_noise_term(value: str) -> bool:
    return value in _TITLE_NOISE_TOKENS


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _normalize_text(value: Any) -> str:
    return " ".join(_coerce_text(value).strip().lower().split())


def _tokenize_terms(value: Any, min_len: int = 2, *, strip_noise: bool = True) -> List[str]:
    text = _normalize_text(value)
    if not text:
        return []
    tokens = KNOWN_PUNCT_PATTERN.sub(" ", text).split()
    terms = [token for token in tokens if len(token) >= min_len]
    if not strip_noise:
        return terms
    return [token for token in terms if not _is_noise_term(token)]


def _canonicalize_link(link: Any) -> str:
    if not isinstance(link, str):
        return ""
    raw = link.strip()
    if not raw:
        return ""

    try:
        parsed = urlsplit(raw)
    except ValueError:
        return raw

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    kept_pairs = [
        (key, value)
        for key, value in pairs
        if key.lower().strip() not in TRACKING_QUERY_KEYS
    ]
    kept_pairs.sort(key=lambda item: (item[0], item[1]))
    canonical_query = urlencode(kept_pairs)
    path = (parsed.path or "").rstrip("/")

    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            canonical_query,
            "",
        )
    )


def _ordered_unique(values: Iterable[Any]) -> List[Any]:
    ordered: OrderedDict[str, Any] = OrderedDict()
    for value in values:
        if value is None:
            continue
        raw = str(value).strip()
        if not raw or raw.lower() == "none":
            continue
        if raw not in ordered:
            ordered[raw] = value
    return list(ordered.values())


def _parse_timestamp(value: Any) -> Optional[datetime]:
    text = _coerce_text(value)
    if not text:
        return None

    candidates = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ]

    text = text.replace("Z", "+00:00").strip()
    for fmt in candidates:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue

        if fmt.endswith("%z") and parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=None)
        return parsed

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _time_gap_hours(left: Optional[datetime], right: Optional[datetime]) -> Optional[float]:
    if left is None or right is None:
        return None
    if (left.tzinfo is None) != (right.tzinfo is None):
        # Mixed aware/naive timestamps are treated as incomparable.
        return None
    return abs((left - right).total_seconds()) / 3600.0


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    a = set(left)
    b = set(right)
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return round(len(a & b) / len(union), 6)


def _to_iso_or_empty(value: Optional[datetime]) -> str:
    return value.isoformat() if value else ""


def _load_config(config_path: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        path = Path(config_path)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except OSError as exc:
        return None, f"config_missing_or_unreadable:{type(exc).__name__}"
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return None, f"config_invalid_json:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, "config_not_a_dict"
    return payload, None


@dataclass(frozen=True)
class _PreparedItem:
    index: int
    candidate: Mapping[str, Any]
    candidate_id: str
    source_id: str
    source_id_norm: str
    source_lane_id: str
    source_type: str
    category: str
    board_or_category: str
    title: str
    title_terms: Tuple[str, ...]
    title_terms_raw: Tuple[str, ...]
    summary_terms: Tuple[str, ...]
    link: str
    canonical_link: str
    published_raw: str
    published_at: Optional[datetime]
    source_observations: List[Dict[str, Any]]
    origin_groups: Tuple[str, ...]
    distribution_sources: Tuple[str, ...]
    independent_origin_count: int
    category_hints: Tuple[str, ...]


def _source_observations(candidate: Mapping[str, Any], index: int, candidate_id: str) -> List[Dict[str, Any]]:
    def add(location: str, source_record: Mapping[str, Any], bucket: str) -> None:
        records.append(
            {
                "observation_location": location,
                "source_bucket": bucket,
                "candidate_index": index,
                "candidate_id": candidate_id,
                "source_id": _coerce_text(source_record.get("source_id")).strip(),
                "source_type": _coerce_text(source_record.get("source_type")),
                "source_name": _coerce_text(
                    source_record.get("source_name") or source_record.get("publisher") or source_record.get("source_id")
                ),
                "publisher": _coerce_text(source_record.get("publisher") or source_record.get("source_name")),
                "title": _coerce_text(source_record.get("title")),
                "link": _coerce_text(source_record.get("link") or source_record.get("url")),
                "published_at": _coerce_text(
                    source_record.get("published_at")
                    or source_record.get("published_date")
                    or source_record.get("published")
                ),
                "collection_timestamp": _coerce_text(source_record.get("collected_at")),
            }
        )

    records: List[Dict[str, Any]] = []

    add("candidate", candidate, "candidate")
    agreement = candidate.get("source_agreement")
    if isinstance(agreement, Mapping):
        for idx, source in enumerate(agreement.get("sources") or []):
            if isinstance(source, Mapping):
                add(f"source_agreement.sources[{idx}]", source, "source_agreement")
            else:
                records.append(
                    {
                        "observation_location": f"source_agreement.sources[{idx}]",
                        "source_bucket": "source_agreement",
                        "candidate_index": index,
                        "candidate_id": candidate_id,
                        "source_id": "",
                        "source_type": "",
                        "source_name": "",
                        "publisher": "",
                        "title": "",
                        "link": "",
                        "published_at": "",
                        "collection_timestamp": "",
                        "payload_type": "malformed_source_agreement_source",
                    }
                )

    for idx, source in enumerate(candidate.get("source_refs") or []):
        if isinstance(source, Mapping):
            add(f"source_refs[{idx}]", source, "source_ref")
        else:
            records.append(
                {
                    "observation_location": f"source_refs[{idx}]",
                    "source_bucket": "source_ref",
                    "candidate_index": index,
                    "candidate_id": candidate_id,
                    "source_id": "",
                    "source_type": "",
                    "source_name": "",
                    "publisher": "",
                    "title": "",
                    "link": "",
                    "published_at": "",
                    "collection_timestamp": "",
                    "payload_type": "malformed_source_ref",
                }
            )

    return records


def _pick_best_time(values: Sequence[Tuple[str, Optional[datetime]]]) -> Tuple[str, Optional[datetime]]:
    times = [entry for entry in values if entry[1] is not None]
    if not times:
        return "", None
    earliest = min(times, key=lambda entry: entry[1])
    return earliest


def _build_category_hints(candidate: Mapping[str, Any]) -> Tuple[str, ...]:
    hints = []
    for key in (
        candidate.get("category"),
        candidate.get("board_or_category"),
        candidate.get("source_lane_id"),
        candidate.get("source_type"),
        candidate.get("source_id"),
    ):
        text = _normalize_text(key)
        if text:
            hints.append(text)
    hints.extend(_tokenize_terms(candidate.get("title") or candidate.get("keyword") or "", min_len=2))
    return tuple(_ordered_unique(hints))


def _candidate_text_pool(candidate: Mapping[str, Any]) -> str:
    fields = (
        candidate.get("title"),
        candidate.get("keyword"),
        candidate.get("summary"),
        candidate.get("board_or_category"),
        candidate.get("category"),
    )
    return " ".join(_coerce_text(field) for field in fields).strip()


def _prepare_items(items: Sequence[Any], config: Mapping[str, Any]) -> Tuple[List[_PreparedItem], List[Dict[str, Any]]]:
    prepared: List[_PreparedItem] = []
    diagnostics: List[Dict[str, Any]] = []

    for index, raw in enumerate(items):
        if not isinstance(raw, Mapping):
            diagnostics.append(
                {
                    "item_index": index,
                    "status": "skip_non_mapping_item",
                    "reason": "item_must_be_object",
                }
            )
            continue

        candidate = dict(raw)
        candidate_id = _normalize_text(candidate.get("candidate_id") or str(index + 1))
        if not candidate_id:
            candidate_id = f"candidate_{index}"
        title = _coerce_text(candidate.get("title") or candidate.get("keyword"))
        if not title:
            diagnostics.append(
                {
                    "item_index": index,
                    "candidate_id": candidate_id,
                    "status": "skip_empty_title",
                    "reason": "title_or_keyword_required",
                }
            )
            continue

        source_id = _coerce_text(candidate.get("source_id"))
        source_id_norm = _normalize_text(source_id)
        source_lane_id = _coerce_text(candidate.get("source_lane_id"))
        source_type = _normalize_text(candidate.get("source_type"))
        category = _normalize_text(candidate.get("category"))
        board_or_category = _normalize_text(candidate.get("board_or_category"))
        link = _coerce_text(candidate.get("link") or candidate.get("url"))
        canonical_link = _canonicalize_link(link)
        title_terms = tuple(_tokenize_terms(title, min_len=2))
        title_terms_raw = tuple(_tokenize_terms(title, min_len=2, strip_noise=False))
        summary_terms = tuple(_tokenize_terms(_candidate_text_pool(candidate), min_len=2))

        published_candidates: List[Tuple[str, Optional[datetime]]] = []
        for raw_published in (
            candidate.get("published_at"),
            candidate.get("published_date"),
            candidate.get("published"),
        ):
            raw = _coerce_text(raw_published)
            if raw:
                parsed = _parse_timestamp(raw)
                if parsed is not None:
                    published_candidates.append((raw, parsed))
        published_raw, published_at = _pick_best_time(published_candidates)

        origin_result = resolve_origin_independence(candidate)
        origin_data = origin_result.get("origin_independence") if isinstance(origin_result, Mapping) else {}
        spread_data = origin_result.get("distribution_spread") if isinstance(origin_result, Mapping) else {}
        origin_groups = tuple(_ordered_unique(origin_data.get("origin_groups", [])))
        distribution_sources = tuple(_ordered_unique(spread_data.get("source_ids", [])))
        independent_origin_count = int(origin_data.get("independent_origin_count") or 0)

        prepared.append(
            _PreparedItem(
                index=index,
                candidate=candidate,
                candidate_id=candidate_id,
                source_id=source_id,
                source_id_norm=source_id_norm,
                source_lane_id=source_lane_id,
                source_type=source_type,
                category=category,
                board_or_category=board_or_category,
                title=title,
                title_terms=title_terms,
                title_terms_raw=title_terms_raw,
                summary_terms=summary_terms,
                link=link,
                canonical_link=canonical_link,
                published_raw=published_raw,
                published_at=published_at,
                source_observations=_source_observations(candidate, index, candidate_id),
                origin_groups=tuple(origin_groups),
                distribution_sources=tuple(distribution_sources),
                independent_origin_count=independent_origin_count,
                category_hints=_build_category_hints(candidate),
            )
        )

    return prepared, diagnostics


def _rule_matches(item: _PreparedItem, rule: Mapping[str, Any], hints_lower: str) -> bool:
    if not isinstance(rule, Mapping):
        return False

    checks: List[bool] = []

    source_ids = rule.get("source_id_in")
    if isinstance(source_ids, list):
        checks.append(item.source_id_norm in {str(source).strip().lower() for source in source_ids})

    lane_ids = rule.get("lane_id_in")
    if isinstance(lane_ids, list):
        checks.append(item.source_lane_id in lane_ids or item.source_lane_id.lower() in {str(v).lower() for v in lane_ids})

    category_tokens = rule.get("category_tokens_any")
    if isinstance(category_tokens, list):
        lowered = set(_tokenize_terms(hints_lower, min_len=2))
        checks.append(any(_normalize_text(token) in lowered for token in category_tokens))

    source_type_tokens = rule.get("source_type_tokens_any")
    if isinstance(source_type_tokens, list):
        lowered_type = set(_tokenize_terms(item.source_type, min_len=2))
        checks.append(any(_normalize_text(token) in lowered_type for token in source_type_tokens))

    return any(checks)


def _select_profile(item: _PreparedItem, config: Mapping[str, Any]) -> str:
    rules = config.get("selection_rules") or []
    combined_hints = " ".join((item.board_or_category, item.category, item.source_type, item.source_lane_id)).lower()
    for rule in rules:
        if _rule_matches(item, rule, combined_hints):
            profile_id = _normalize_text(rule.get("profile_id"))
            if profile_id and profile_id in config.get("profiles", {}):
                return profile_id

    return _normalize_text(config.get("default_profile_id") or "strict_news_incident")


def _profile(item: _PreparedItem, config: Mapping[str, Any]) -> Mapping[str, Any]:
    profiles = config.get("profiles") if isinstance(config.get("profiles"), Mapping) else {}
    if not isinstance(profiles, Mapping):
        profiles = {}

    profile_id = _select_profile(item, config)
    selected = profiles.get(profile_id)
    if not isinstance(selected, Mapping):
        selected = {
            "match": {
                "title_similarity_min": 0.7,
                "title_term_overlap_min": 1,
                "time_window_hours": 12.0,
                "allow_missing_publication_time": True,
                "missing_publication_score": 0.25,
                "require_time_or_source_identity": True,
                "match_score_min": 0.65,
            },
            "weights": {"title": 0.5, "time": 0.2, "source_identity": 0.2, "origin_overlap": 0.1},
            "match_requirements": {"require_source_identity": False},
        }
    return selected


def _term_overlap_score(a: _PreparedItem, b: _PreparedItem) -> Tuple[float, int]:
    a_terms = set(_rewrite_normalized_terms(a.title_terms))
    b_terms = set(_rewrite_normalized_terms(b.title_terms))
    if not a_terms or not b_terms:
        return 0.0, 0
    if not (a_terms - _TITLE_NOISE_TOKENS) or not (b_terms - _TITLE_NOISE_TOKENS):
        a_terms = set(_rewrite_normalized_terms(a.title_terms_raw))
        b_terms = set(_rewrite_normalized_terms(b.title_terms_raw))
        if not a_terms or not b_terms:
            return 0.0, 0
        if not (a_terms - _TITLE_NOISE_TOKENS) or not (b_terms - _TITLE_NOISE_TOKENS):
            return 0.0, 0
    overlap_count = len(a_terms & b_terms)
    union_count = len(a_terms | b_terms)
    if union_count == 0:
        return 0.0, overlap_count
    return round(overlap_count / union_count, 6), overlap_count


def _source_identity_and_distributions(a: _PreparedItem, b: _PreparedItem) -> Tuple[float, List[str], float]:
    reasons: List[str] = []
    source_overlap = 0.0
    if a.source_id_norm and b.source_id_norm and a.source_id_norm == b.source_id_norm:
        source_overlap = 0.35
        reasons.append("same_source_id")

    origin_overlap = set(a.origin_groups) & set(b.origin_groups)
    if origin_overlap:
        source_overlap = max(source_overlap, 1.0)
        reasons.append(f"origin_group_overlap:{sorted(origin_overlap)[0]}")

    distribution_overlap = set(a.distribution_sources) & set(b.distribution_sources)
    if distribution_overlap:
        source_overlap = max(source_overlap, 0.55)
        reasons.append(f"distribution_overlap:{sorted(distribution_overlap)[0]}")

    return source_overlap, reasons, float(len(origin_overlap))


def _time_score(a: _PreparedItem, b: _PreparedItem, profile: Mapping[str, Any]) -> Tuple[float, bool, float, Optional[str], List[str]]:
    time_window = float(profile.get("match", {}).get("time_window_hours", 12.0))
    allow_missing = bool(profile.get("match", {}).get("allow_missing_publication_time", True))
    missing_score = float(profile.get("match", {}).get("missing_publication_score", 0.2))

    gap = _time_gap_hours(a.published_at, b.published_at)
    if gap is None:
        if allow_missing:
            return missing_score, False, 0.0, None, ["publication_time_missing_used_for_matching"]
        return 0.0, False, gap if isinstance(gap, float) else 0.0, "missing_publication_time", ["publication_time_missing"]

    if gap <= 0:
        return 1.0, True, gap, None, ["publication_time_exact_match"]
    if gap <= time_window:
        return round(1.0 - (gap / max(time_window, 1e-9)), 6), True, gap, None, [f"publication_time_within_window:{time_window:g}h"]

    return 0.0, False, gap, "outside_time_window", [f"publication_time_gap_exceeds:{time_window:g}h"]


def _match_pair(
    a: _PreparedItem,
    b: _PreparedItem,
    config: Mapping[str, Any],
    *,
    semantic_similarity: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    profile_id = _select_profile(a, config)
    profile = _profile(a, config)
    match_cfg = profile.get("match", {})
    weights = profile.get("weights", {})

    reasons: List[str] = []
    provenance: List[str] = []

    title_similarity, overlap_count = _term_overlap_score(a, b)
    if a.canonical_link and b.canonical_link and a.canonical_link == b.canonical_link and a.canonical_link:
        reasons.append("canonical_link_exact_match")
        title_similarity = max(title_similarity, 0.95)
    else:
        reasons.append(f"title_jaccard:{title_similarity:.3f}")

    if title_similarity < float(match_cfg.get("title_similarity_min", 0.7)):
        return None

    if overlap_count < int(match_cfg.get("title_term_overlap_min", 1)):
        return None

    source_identity_score, source_reasons, origin_overlap_count = _source_identity_and_distributions(a, b)
    time_score_value, time_in_window, gap_hours, time_reason, time_reasons = _time_score(a, b, profile)
    reasons.extend(source_reasons)
    reasons.extend(time_reasons)
    provenance.extend(
        [
            f"source_id_a={a.source_id}",
            f"source_id_b={b.source_id}",
            f"profile={profile_id}",
        ]
    )
    if a.published_raw or b.published_raw:
        provenance.append(f"published_at_a={a.published_raw}")
        provenance.append(f"published_at_b={b.published_raw}")
    if gap_hours is not None and gap_hours > 0:
        provenance.append(f"gap_hours={round(gap_hours, 4)}")

    require_time_or_source = bool(match_cfg.get("require_time_or_source_identity", True))
    require_source_identity = bool(profile.get("match_requirements", {}).get("require_source_identity", False))

    if source_identity_score <= 0 and require_source_identity:
        return None

    if require_time_or_source and not time_in_window and source_identity_score <= 0.0:
        return None

    weight_title = float(weights.get("title", 0.5))
    weight_time = float(weights.get("time", 0.2))
    weight_source = float(weights.get("source_identity", 0.2))
    weight_origin = float(weights.get("origin_overlap", 0.1))

    origin_overlap_score = 1.0 if origin_overlap_count > 0 else 0.0
    base_score = min(
        1.0,
        weight_title * title_similarity
        + weight_time * time_score_value
        + weight_source * source_identity_score
        + weight_origin * origin_overlap_score,
    )
    semantic_bonus = 0.0
    if (
        isinstance(semantic_similarity, (int, float))
        and not isinstance(semantic_similarity, bool)
        and SEMANTIC_SCORE_FLOOR <= float(semantic_similarity) <= 1.0
    ):
        normalized = (float(semantic_similarity) - SEMANTIC_SCORE_FLOOR) / (
            1.0 - SEMANTIC_SCORE_FLOOR
        )
        semantic_bonus = round(min(SEMANTIC_MAX_BONUS, normalized * SEMANTIC_MAX_BONUS), 6)
        reasons.append(f"semantic_proxy:{float(semantic_similarity):.3f}")
        provenance.append(f"semantic_score_semantics={SEMANTIC_SCORE_SEMANTICS}")
    score = min(1.0, base_score + semantic_bonus)

    if score < float(match_cfg.get("match_score_min", 0.65)):
        return None

    link_score_min = float(match_cfg.get("link_score_min", match_cfg.get("match_score_min", 0.65)))
    is_strong_link = score >= link_score_min

    if time_reason and (time_in_window is False):
        reasons.append(f"time_match_failed:{time_reason}")

    return {
        "profile": profile_id,
        "score": round(score, 6),
        "base_score": round(base_score, 6),
        "title_similarity": round(title_similarity, 6),
        "semantic_similarity": (
            round(float(semantic_similarity), 6)
            if isinstance(semantic_similarity, (int, float))
            and not isinstance(semantic_similarity, bool)
            else None
        ),
        "semantic_bonus": semantic_bonus,
        "semantic_score_semantics": (
            SEMANTIC_SCORE_SEMANTICS if semantic_similarity is not None else None
        ),
        "time_match": time_in_window,
        "gap_hours": gap_hours,
        "source_identity_score": round(source_identity_score, 6),
        "origin_overlap_count": int(origin_overlap_count),
        "reasons": reasons,
        "provenance": provenance,
        "is_strong_link": is_strong_link,
    }


def _eligible_for_semantic_signal(
    a: _PreparedItem,
    b: _PreparedItem,
    config: Mapping[str, Any],
) -> bool:
    """Keep every existing deterministic hard gate ahead of semantic scoring."""

    profile = _profile(a, config)
    match_cfg = profile.get("match", {})
    title_similarity, overlap_count = _term_overlap_score(a, b)
    if a.canonical_link and b.canonical_link and a.canonical_link == b.canonical_link:
        title_similarity = max(title_similarity, 0.95)
    if title_similarity < float(match_cfg.get("title_similarity_min", 0.7)):
        return False
    if overlap_count < int(match_cfg.get("title_term_overlap_min", 1)):
        return False

    source_identity_score, _, _ = _source_identity_and_distributions(a, b)
    _, time_in_window, _, _, _ = _time_score(a, b, profile)
    if (
        bool(profile.get("match_requirements", {}).get("require_source_identity", False))
        and source_identity_score <= 0
    ):
        return False
    if (
        bool(match_cfg.get("require_time_or_source_identity", True))
        and not time_in_window
        and source_identity_score <= 0
    ):
        return False
    return True


def _semantic_scores_for_pairs(
    prepared_items: Sequence[_PreparedItem],
    config: Mapping[str, Any],
    *,
    semantic_scorer: Optional[Callable[..., Mapping[str, Any]]],
    timeout_seconds: float,
) -> tuple[Dict[Tuple[int, int], float], Dict[str, Any]]:
    eligible: List[Tuple[int, int]] = []
    text_pairs: List[Tuple[str, str]] = []
    for left in range(len(prepared_items)):
        for right in range(left + 1, len(prepared_items)):
            if not _eligible_for_semantic_signal(
                prepared_items[left], prepared_items[right], config
            ):
                continue
            eligible.append((left, right))
            text_pairs.append((prepared_items[left].title, prepared_items[right].title))

    if semantic_scorer is None:
        return {}, {
            "status": "disabled",
            "eligible_pair_count": len(eligible),
            "scored_pair_count": 0,
            "fallback": "existing_deterministic_similarity",
            "score_semantics": SEMANTIC_SCORE_SEMANTICS,
        }
    limited_pairs = text_pairs[:MAX_SIMILARITY_PAIRS]
    limited_indexes = eligible[:MAX_SIMILARITY_PAIRS]
    if not limited_pairs:
        return {}, {
            "status": "not_needed",
            "eligible_pair_count": 0,
            "scored_pair_count": 0,
            "fallback": None,
            "score_semantics": SEMANTIC_SCORE_SEMANTICS,
        }
    try:
        receipt = semantic_scorer(limited_pairs, timeout_seconds=timeout_seconds)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return {}, {
            "status": "failed",
            "eligible_pair_count": len(eligible),
            "scored_pair_count": 0,
            "skipped_due_limit": max(0, len(eligible) - len(limited_indexes)),
            "errors": [f"semantic_scorer_error:{type(exc).__name__}"],
            "fallback": "existing_deterministic_similarity",
            "score_semantics": SEMANTIC_SCORE_SEMANTICS,
        }

    raw_scores = receipt.get("scores") if isinstance(receipt, Mapping) else None
    completed = (
        isinstance(receipt, Mapping)
        and receipt.get("status") == "completed"
        and isinstance(raw_scores, list)
        and len(raw_scores) == len(limited_indexes)
    )
    if not completed:
        return {}, {
            "status": str(receipt.get("status") or "unavailable")
            if isinstance(receipt, Mapping)
            else "unavailable",
            "eligible_pair_count": len(eligible),
            "scored_pair_count": 0,
            "skipped_due_limit": max(0, len(eligible) - len(limited_indexes)),
            "errors": list(receipt.get("errors") or [])
            if isinstance(receipt, Mapping)
            else ["semantic_receipt_invalid"],
            "fallback": "existing_deterministic_similarity",
            "score_semantics": SEMANTIC_SCORE_SEMANTICS,
        }

    scores: Dict[Tuple[int, int], float] = {}
    for pair_index, raw_score in zip(limited_indexes, raw_scores):
        if (
            isinstance(raw_score, (int, float))
            and not isinstance(raw_score, bool)
            and -1.0 <= float(raw_score) <= 1.0
        ):
            scores[pair_index] = float(raw_score)
    return scores, {
        "status": "completed",
        "eligible_pair_count": len(eligible),
        "scored_pair_count": len(scores),
        "skipped_due_limit": max(0, len(eligible) - len(limited_indexes)),
        "fallback": None,
        "score_semantics": SEMANTIC_SCORE_SEMANTICS,
        "not_fact_rights_or_performance_evidence": True,
    }


class _UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, index: int) -> int:
        if self.parent[index] != index:
            self.parent[index] = self.find(self.parent[index])
        return self.parent[index]

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            self.parent[left_root] = right_root
            return
        if self.rank[right_root] < self.rank[left_root]:
            self.parent[right_root] = left_root
            return
        self.parent[right_root] = left_root
        self.rank[left_root] += 1


def _build_cluster_record(
    cluster_index: int,
    member_positions: List[int],
    prepared: List[_PreparedItem],
    edges: List[Dict[str, Any]],
) -> Dict[str, Any]:
    members = [prepared[position] for position in member_positions]
    members.sort(key=lambda item: item.index)
    representative = members[0]
    candidate_ids = [item.candidate_id for item in members]
    item_indexes = [item.index for item in members]

    all_observations: List[Dict[str, Any]] = []
    for item in members:
        all_observations.extend(item.source_observations)

    all_category_hints = _ordered_unique(
        hint for item in members for hint in item.category_hints
    )
    parsed_times = [item.published_at for item in members if item.published_at]
    earliest = min(parsed_times) if parsed_times else None
    latest = max(parsed_times) if parsed_times else None
    span_hours: Optional[float] = None
    if earliest and latest:
        span_hours = round((latest - earliest).total_seconds() / 3600.0, 6)

    origin_groups = _ordered_unique(
        group for item in members for group in item.origin_groups
    )
    distribution_sources = _ordered_unique(
        source_id for item in members for source_id in item.distribution_sources
    )
    independent_source_ids = _ordered_unique(
        source_id for source in all_observations for source_id in [_normalize_text(source.get("source_id"))]
    )
    source_diversity = len([sid for sid in independent_source_ids if sid])

    cluster_origin_count = len(origin_groups)
    distribution_count = len(distribution_sources)
    repost_count = max(0, distribution_count - cluster_origin_count)

    edge_scores = [edge["score"] for edge in edges if edge.get("score") is not None]
    if edge_scores:
        confidence = round(sum(edge_scores) / len(edge_scores), 6)
    else:
        confidence = 0.0

    match_reasons = _ordered_unique(
        reason
        for edge in edges
        for reason in edge.get("reasons", [])
    )
    match_provenance = [
        {
            "pair": f"{edge['a_candidate_id']}|{edge['b_candidate_id']}",
            "score": edge["score"],
            "profile": edge["profile"],
            "reasons": edge["reasons"],
            "provenance": edge["provenance"],
        }
        for edge in edges
    ]

    recurrence = {
        "is_repeated": len(members) > 1,
        "repeat_count": max(0, len(members) - 1),
        "source_observation_count": len(all_observations),
        "source_diversity_count": source_diversity,
        "time_span_hours": span_hours,
    }

    profile_id_candidates = _ordered_unique(edge["profile"] for edge in edges)

    return {
        "cluster_id": f"cluster:{cluster_index:04d}",
        "cluster_index": cluster_index,
        "cluster_size": len(members),
        "profile_ids": profile_id_candidates,
        "representative_candidate_id": representative.candidate_id,
        "representative_title": representative.title,
        "representative_link": representative.link,
        "earliest_publication_time": _to_iso_or_empty(earliest),
        "latest_publication_time": _to_iso_or_empty(latest),
        "category_hints": all_category_hints,
        "candidate_ids": candidate_ids,
        "indexes": item_indexes,
        "source_observations": all_observations,
        "origin_count": cluster_origin_count,
        "distribution_count": distribution_count,
        "repost_count": repost_count,
        "independent_origin_count": cluster_origin_count,
        "recurrence": recurrence,
        "source_observations_count": len(all_observations),
        "origin_groups": origin_groups,
        "distribution_sources": distribution_sources,
        "match_reasons": match_reasons,
        "match_provenance": match_provenance,
        "confidence": confidence,
        "status": "clustered" if len(members) > 1 else "singleton",
    }


def run_same_event_topic_clustering(
    items: Any,
    *,
    config_path: Any = DEFAULT_CONFIG_PATH,
    semantic_scorer: Optional[Callable[..., Mapping[str, Any]]] = score_text_pairs,
    semantic_timeout_seconds: float = DEFAULT_SIMILARITY_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Cluster shallow candidates by conservative same-event/topic signals.

    Returns a non-mutating JSON payload with explicit match reasons/provenance.
    """

    if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray, Mapping)):
        return {
            "schema_version": SAME_EVENT_TOPIC_CLUSTERER_VERSION,
            "status": "closed",
            "reason_code": "invalid_items",
            "reason": "items must be a sequence",
            "cluster_count": 0,
            "clusters": [],
            "summary": {
                "input_count": 0,
                "prepared_count": 0,
                "skip_count": 0,
                "singleton_count": 0,
                "matched_count": 0,
                "edge_count": 0,
            },
            "diagnostics": {
                "config_path": str(config_path),
                "candidate_diagnostics": [{"status": "invalid_items", "reason": "items must be a sequence"}],
            },
        }

    config, config_error = _load_config(config_path)
    if config_error is not None or not isinstance(config, Mapping):
        return {
            "schema_version": SAME_EVENT_TOPIC_CLUSTERER_VERSION,
            "status": "closed",
            "reason_code": "invalid_config",
            "reason": config_error or "configuration missing",
            "cluster_count": 0,
            "clusters": [],
            "summary": {
                "input_count": len(items),
                "prepared_count": 0,
                "skip_count": len(items),
                "singleton_count": 0,
                "matched_count": 0,
                "edge_count": 0,
            },
            "diagnostics": {
                "config_path": str(config_path),
            },
        }

    prepared_items, diagnostics = _prepare_items(list(items), config)
    if not prepared_items:
        return {
            "schema_version": SAME_EVENT_TOPIC_CLUSTERER_VERSION,
            "status": "closed",
            "reason_code": "no_usable_items",
            "reason": "No usable candidates after deterministic normalization.",
            "cluster_count": 0,
            "clusters": [],
            "summary": {
                "input_count": len(items),
                "prepared_count": 0,
                "skip_count": len(items),
                "singleton_count": 0,
                "matched_count": 0,
                "edge_count": 0,
            },
            "diagnostics": {"config_path": str(config_path), "candidate_diagnostics": diagnostics},
        }

    semantic_scores, semantic_diagnostics = _semantic_scores_for_pairs(
        prepared_items,
        config,
        semantic_scorer=semantic_scorer,
        timeout_seconds=semantic_timeout_seconds,
    )

    uf = _UnionFind(len(prepared_items))
    pairwise_matches: List[Dict[str, Any]] = []
    for left in range(len(prepared_items)):
        for right in range(left + 1, len(prepared_items)):
            left_item = prepared_items[left]
            right_item = prepared_items[right]
            match = _match_pair(
                left_item,
                right_item,
                config,
                semantic_similarity=semantic_scores.get((left, right)),
            )
            if not match:
                continue
            if not match.get("is_strong_link"):
                continue
            pairwise_matches.append(
                {
                    "a_index": left,
                    "b_index": right,
                    "a_candidate_id": left_item.candidate_id,
                    "b_candidate_id": right_item.candidate_id,
                    **match,
                }
            )
            uf.union(left, right)

    groups: MutableMapping[int, List[int]] = {}
    for index in range(len(prepared_items)):
        groups.setdefault(uf.find(index), []).append(index)

    clusters: List[Dict[str, Any]] = []
    for cluster_index, (_, member_positions) in enumerate(sorted(groups.items(), key=lambda row: row[0])):
        ordered_positions = sorted(member_positions)
        group_edges = [
            edge
            for edge in pairwise_matches
            if edge["a_index"] in ordered_positions and edge["b_index"] in ordered_positions
        ]

        clusters.append(
            _build_cluster_record(
                cluster_index=cluster_index,
                member_positions=ordered_positions,
                prepared=prepared_items,
                edges=group_edges,
            )
        )

    matched_clusters = sum(1 for cluster in clusters if cluster["cluster_size"] > 1)
    singleton_clusters = sum(1 for cluster in clusters if cluster["cluster_size"] == 1)

    clusters.sort(key=lambda cluster: (cluster["cluster_size"], cluster["cluster_id"]), reverse=True)
    for index, cluster in enumerate(clusters):
        cluster["cluster_id"] = f"cluster:{index:04d}"
        cluster["cluster_index"] = index

    return {
        "schema_version": SAME_EVENT_TOPIC_CLUSTERER_VERSION,
        "status": "ok",
        "reason_code": None,
        "reason": "same-event/topic clusters computed",
        "cluster_count": len(clusters),
        "clusters": clusters,
        "summary": {
            "input_count": len(items),
            "prepared_count": len(prepared_items),
            "skip_count": len(items) - len(prepared_items),
            "singleton_count": singleton_clusters,
            "matched_count": matched_clusters,
            "edge_count": len(pairwise_matches),
        },
        "diagnostics": {
            "config_path": str(config_path),
            "default_profile_id": config.get("default_profile_id"),
            "candidate_diagnostics": diagnostics,
            "match_profile_count": len((config.get("profiles") or {})),
            "semantic_similarity": semantic_diagnostics,
        },
    }


__all__ = ["run_same_event_topic_clustering", "DEFAULT_CONFIG_PATH", "SAME_EVENT_TOPIC_CLUSTERER_VERSION"]
