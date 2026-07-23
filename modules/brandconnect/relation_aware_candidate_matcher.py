"""Relation-aware candidate-to-product matching for Brand Connect.

Layers supplied relation/story signals (``derived_terms``, season context,
practical topic, product role) over the existing exact matcher so natural
bridges such as care→product function can surface generically — no owner
examples are hard-coded. Scoring stays conservative: a relation contribution
needs at least two distinct meaningful term overlaps, a relation-only match
additionally needs agreement across at least two signal fields, and editorial
bypass always wins. Every match keeps a traceable basis; nothing is invented.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping

from modules.brandconnect.brandconnect_candidate_matcher import (
    DIRECT_MATCH_TERMS,
    GENERIC_MATCH_TOKENS,
    SITUATION_RULES,
    candidate_text,
    is_editorial_bypass,
    match_candidate_to_products,
    select_diverse_product_matches,
)
from modules.brandconnect.owner_association_learning import learned_association_signals

RELATION_MATCH_THRESHOLD = 0.45
RELATION_BONUS_CAP = 0.4
MAX_MATCHES = 3
MIN_OVERLAP_TERMS = 2
MIN_STANDALONE_FIELDS = 2

RELATION_FIELDS = ("derived_terms", "season_context", "practical_topic", "product_role")
PRODUCT_SUPPORT_FIELD = "product_text"

# Season/daypart words appear in nearly every relation row, so they can never
# count as evidence on their own; they only confirm an already-supported match.
_SEASON_TOKENS = {
    "여름", "겨울", "봄", "가을", "사계절", "연중", "환절기", "장마철",
    "아침", "저녁", "출근", "등교", "외출", "매일", "일상", "주말",
}
_TOKEN_PATTERN = re.compile(r"[\W_]+", re.UNICODE)
_HANGUL_TOKEN = re.compile(r"^[가-힣]+$")
_KOREAN_SUFFIXES = (
    "으로", "에서", "에게", "까지", "부터", "처럼", "보다",
    "했습니다", "합니다", "됩니다", "입니다", "하는", "되는", "있는", "없는", "관리법", "방법", "할",
    "과", "와", "을", "를", "은", "는", "이", "가", "에", "의", "로", "도", "만", "법",
)
_SEMANTIC_CANONICAL = {
    "손": "hand",
    "핸드": "hand",
    "발": "foot",
    "풋": "foot",
}
_RELATION_BOILERPLATE_TOKENS = {
    "확인", "포인트", "콘텐츠", "연결", "상품", "제품", "후보", "관련",
    "추천", "선택", "정보", "활용", "사용", "일상", "루틴", "정리",
    "grooming", "beauty", "skincare", "fashion", "lifestyle", "korea",
    "top", "프리미엄", "판매", "순간", "특가",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _tokens(text: str) -> set:
    result = set()
    for token in _TOKEN_PATTERN.split(text.lower()):
        if not token:
            continue
        if token == "관리법":
            token = "관리"
        if _HANGUL_TOKEN.fullmatch(token):
            for suffix in _KOREAN_SUFFIXES:
                if token.endswith(suffix):
                    stem = token[:-len(suffix)]
                    token = stem if len(stem) >= 2 else ""
                    break
        if not token:
            continue
        token = _SEMANTIC_CANONICAL.get(token, token)
        if len(token) >= 2:
            result.add(token)
    return result


def _meaningful(tokens: set) -> set:
    return {
        t for t in tokens
        if t not in GENERIC_MATCH_TOKENS
        and t not in _SEASON_TOKENS
        and t not in _RELATION_BOILERPLATE_TOKENS
    }


def _season_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(
            _text(value.get(key))
            for key in ("best_context", "season", "weather", "daily_environment", "environment_signal")
        )
    return _text(value)


def _relation_candidate_text(candidate: Mapping[str, Any]) -> str:
    """Use owner-facing topic words, excluding source/category boilerplate."""

    parts = [_text(candidate.get("title"))]
    keywords = candidate.get("keywords")
    if isinstance(keywords, (list, tuple)):
        parts.extend(_text(item) for item in keywords)
    return " ".join(part for part in parts if part)


def _association_terms(signals: List[Mapping[str, Any]]) -> set:
    terms = set()
    for signal in signals:
        values = signal.get("association_terms")
        if isinstance(values, (list, tuple)):
            terms.update(_meaningful(_tokens(" ".join(_text(value) for value in values))))
    return terms


def _evaluate_owner_association(
    signals: List[Mapping[str, Any]],
    product: Mapping[str, Any],
) -> Dict[str, Any]:
    product_text = " ".join(
        [
            _text(product.get("name")),
            _text(product.get("brand")),
            _text(product.get("category")),
            _text(product.get("product_family")),
            " ".join(_text(item) for item in product.get("keywords", []) if isinstance(item, str)),
        ]
    )
    product_tokens = _meaningful(_tokens(product_text))
    best: Dict[str, Any] = {"score": 0.0, "terms": [], "signal": None}
    relation_scores = {
        "material_craft": 0.68,
        "activity_tool": 0.68,
        "scene_function": 0.65,
        "body_context": 0.6,
        "fandom_merch": 0.6,
        "object_adjacent": 0.58,
        "visual_similarity": 0.55,
        "name_wordplay": 0.55,
        "color_wordplay": 0.5,
        "visible_accessory": 0.62,
    }
    for signal in signals:
        signal_terms = _meaningful(
            _tokens(" ".join(_text(item) for item in signal.get("association_terms", [])))
        )
        overlap = sorted(signal_terms & product_tokens)
        if not overlap:
            continue
        score = relation_scores.get(_text(signal.get("relation_type")), 0.0)
        if len(overlap) >= 2:
            score = min(0.75, score + 0.05)
        if score > best["score"]:
            best = {"score": score, "terms": overlap, "signal": signal}
    return best


def _base_candidate_content_text(candidate: Mapping[str, Any]) -> str:
    """Mirror the exact matcher's content-only token input.

    Keeping this separate from relation stemming lets the prepared index form
    a conservative superset of every product the exact matcher could score.
    """

    parts = [
        _text(candidate.get("title")),
        _text(candidate.get("context")) or _text(candidate.get("hook")),
    ]
    keywords = candidate.get("keywords")
    if isinstance(keywords, (list, tuple)):
        parts.extend(_text(item) for item in keywords)
    return " ".join(part for part in parts if part)


def _raw_match_tokens(text: str) -> set:
    """Mirror the base matcher's conservative Korean-particle normalization."""

    return _tokens(text)


def _candidate_relation_families(candidate: Mapping[str, Any]) -> set:
    text = _text(candidate.get("title")).lower()
    families = set()
    signals = {
        "accessory": ("신발", "운동화", "가방", "우산", "양산", "시계", "선글라스"),
        "hair": ("머리", "헤어", "샴푸", "장발", "숏컷", "염색", "앞머리"),
        "fragrance": ("향수", "퍼퓸", "오드퍼퓸"),
        "makeup": ("메이크업", "눈 화장", "립", "쿠션", "파운데이션"),
        "skincare": ("피부", "스킨", "손", "핸드", "제모", "왁싱", "보습"),
        "fashion": ("셔츠", "티셔츠", "재킷", "자켓", "원피스", "팬츠", "코트", "니트", "룩"),
    }
    for family, terms in signals.items():
        if any(term in text for term in terms):
            families.add(family)
    if "accessory" in families:
        families.add("lifestyle")
    if families:
        return families
    category = (_text(candidate.get("category")) or _text(candidate.get("raw_category"))).lower()
    if "뷰티" in category or "화장" in category:
        return {"makeup", "hair", "skincare", "fragrance"}
    if "패션" in category:
        return {"fashion", "accessory"}
    if "생활" in category:
        return {"lifestyle", "accessory"}
    return set()


def relation_signal_fields(record: Any) -> Dict[str, str]:
    """Extract the four relation signal fields from a raw shard row or an
    engine-normalized story record; absent fields stay empty."""

    if not isinstance(record, Mapping):
        return {}
    derived = record.get("derived_terms")
    return {
        "derived_terms": " ".join(_text(t) for t in derived if _text(t)) if isinstance(derived, (list, tuple)) else "",
        "season_context": _season_text(record.get("season_context")),
        "practical_topic": _text(record.get("practical_topic")),
        "product_role": _text(record.get("product_role")),
    }


def prepare_relation_index(
    relation_index: Any,
    products: List[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Pre-tokenize relation rows once and build a candidate-term lookup.

    The second stage can contain thousands of products and many graded
    candidates. Re-tokenizing every story row for every candidate would push
    the local bridge past its bounded timeout, so this cache is built once per
    stage run and stays entirely in memory.
    """

    relations = relation_index if isinstance(relation_index, Mapping) else {}
    product_by_id = {
        _text(str(product.get("product_id", ""))): product
        for product in products if isinstance(product, Mapping)
        if _text(str(product.get("product_id", "")))
    }
    records: Dict[str, Dict[str, Any]] = {}
    term_to_product_ids: Dict[str, set] = {}
    base_term_to_product_ids: Dict[str, set] = {}
    brand_term_to_product_ids: Dict[str, set] = {}
    unindexed_brand_product_ids: set = set()
    situation_to_product_ids: Dict[str, set] = {}
    for product_id, relation in relations.items():
        clean_id = _text(str(product_id))
        product = product_by_id.get(clean_id)
        if not clean_id or not isinstance(relation, Mapping) or product is None:
            continue
        fields = relation_signal_fields(relation)
        fields[PRODUCT_SUPPORT_FIELD] = " ".join(
            _text(product.get(key)) for key in ("name", "brand", "product_family")
        )
        terms_by_field = {
            field: _meaningful(_tokens(text))
            for field, text in fields.items() if text
        }
        record = {
            "_prepared_relation": True,
            "_terms_by_field": terms_by_field,
            "_season_tokens": set().union(*(
                _tokens(text) for text in fields.values() if text
            )) & _SEASON_TOKENS,
        }
        records[clean_id] = record
        for term in set().union(*terms_by_field.values()) if terms_by_field else set():
            term_to_product_ids.setdefault(term, set()).add(clean_id)
    # Exact-match retrieval covers the full catalog, including products that
    # have no relation row. The final base matcher still applies every score,
    # family, intent-mismatch, and threshold rule; this only avoids products
    # that cannot possibly contribute evidence.
    for product_id, product in product_by_id.items():
        product_tokens = product.get("_match_tokens")
        if not isinstance(product_tokens, set):
            product_tokens = _raw_match_tokens(" ".join([
                *(
                    _text(product.get(key))
                    for key in ("name", "brand", "category", "product_family")
                ),
                " ".join(
                    _text(keyword)
                    for keyword in product.get("keywords", [])
                    if isinstance(keyword, str)
                ),
            ]))
        for term in product_tokens:
            base_term_to_product_ids.setdefault(term, set()).add(product_id)
        brand = _text(product.get("brand"))
        brand_terms = _raw_match_tokens(brand)
        for term in brand_terms:
            brand_term_to_product_ids.setdefault(term, set()).add(product_id)
        if brand and not brand_terms:
            # Punctuation-only token splits can still pass the base matcher's
            # literal brand boundary check (for example, ``A.B.C``).
            unindexed_brand_product_ids.add(product_id)
        product_text = _text(product.get("_match_text")) or " ".join(
            _text(product.get(key))
            for key in ("name", "brand", "category", "product_family")
        )
        for rule_name, _pattern, targets in SITUATION_RULES:
            if any(target in product_text for target in targets):
                situation_to_product_ids.setdefault(rule_name, set()).add(product_id)
    return {
        "_prepared_relation_index": True,
        "records": records,
        "term_to_product_ids": term_to_product_ids,
        "product_by_id": product_by_id,
        "base_term_to_product_ids": base_term_to_product_ids,
        "brand_term_to_product_ids": brand_term_to_product_ids,
        "unindexed_brand_product_ids": unindexed_brand_product_ids,
        "situation_to_product_ids": situation_to_product_ids,
    }


def _lookup_relation_product_ids(candidate_tokens: set, term_lookup: Mapping[str, set]) -> set:
    """Retrieve every term allowed by ``_term_overlap`` without a full scan."""

    hit_counts: Dict[str, int] = {}
    for token in candidate_tokens:
        matching_terms = {token}
        if len(token) >= 3:
            matching_terms.add(token[:-1])
        if len(token) >= 4:
            matching_terms.add(token[:-2])
        for term in matching_terms:
            for product_id in term_lookup.get(term, set()):
                hit_counts[product_id] = hit_counts.get(product_id, 0) + 1
    # `_evaluate_relation` rejects fewer than two distinct overlaps, so
    # frequent one-token hits can be discarded before any product iteration.
    return {
        product_id for product_id, count in hit_counts.items()
        if count >= MIN_OVERLAP_TERMS
    }


def _narrow_base_products(
    candidate: Mapping[str, Any],
    products: List[Mapping[str, Any]],
    prepared_index: Mapping[str, Any],
) -> List[Mapping[str, Any]]:
    """Return a deterministic conservative superset for exact scoring."""

    content_tokens = _raw_match_tokens(_base_candidate_content_text(candidate))
    all_text = candidate_text(candidate)
    all_tokens = _raw_match_tokens(all_text)
    product_ids = set()
    term_lookup = prepared_index.get("base_term_to_product_ids", {})
    for token in content_tokens:
        product_ids.update(term_lookup.get(token, set()))
    brand_lookup = prepared_index.get("brand_term_to_product_ids", {})
    for token in all_tokens:
        product_ids.update(brand_lookup.get(token, set()))
    product_ids.update(prepared_index.get("unindexed_brand_product_ids", set()))
    situation_lookup = prepared_index.get("situation_to_product_ids", {})
    for rule_name, pattern, _targets in SITUATION_RULES:
        if pattern.search(all_text):
            product_ids.update(situation_lookup.get(rule_name, set()))
    if not product_ids:
        return []
    return [
        product for product in products
        if _text(str(product.get("product_id", ""))) in product_ids
    ]


def _term_overlap(candidate_tokens: set, field_terms: set) -> set:
    """Match exact tokens, allowing up to two trailing characters on the
    candidate side so Korean particles (셔츠를, 세척과) still count as the term."""

    hits = set()
    for term in field_terms:
        for token in candidate_tokens:
            if token == term or (token.startswith(term) and len(token) <= len(term) + 2):
                hits.add(term)
                break
    return hits


def _evaluate_relation(
    candidate_tokens: set,
    candidate_season: set,
    record: Any,
    product: Mapping[str, Any],
) -> Dict[str, Any]:
    if isinstance(record, Mapping) and record.get("_prepared_relation") is True:
        terms_by_field = record.get("_terms_by_field", {})
        relation_season = record.get("_season_tokens", set())
    else:
        fields = relation_signal_fields(record)
        fields[PRODUCT_SUPPORT_FIELD] = " ".join(
            _text(product.get(key)) for key in ("name", "brand", "product_family")
        )
        terms_by_field = {
            field: _meaningful(_tokens(text))
            for field, text in fields.items() if text
        }
        relation_season = set().union(*(
            _tokens(text) for text in fields.values() if text
        )) & _SEASON_TOKENS
    overlaps: set = set()
    contributing_fields: set = set()
    season_congruent = False
    for field, field_terms in terms_by_field.items():
        hit = _term_overlap(candidate_tokens, field_terms)
        if hit:
            overlaps |= hit
            contributing_fields.add(field)
    season_congruent = bool(candidate_season & relation_season)

    relation_fields_used = contributing_fields & set(RELATION_FIELDS)
    if len(overlaps) < MIN_OVERLAP_TERMS or not relation_fields_used:
        return {"bonus": 0.0, "standalone": 0.0, "overlaps": [], "fields": [], "season_congruent": False}

    bonus = min(0.1 * len(overlaps), RELATION_BONUS_CAP)
    if season_congruent:
        bonus = min(bonus + 0.05, RELATION_BONUS_CAP)
    standalone = 0.0
    if len(contributing_fields) >= MIN_STANDALONE_FIELDS and relation_fields_used:
        standalone = min(0.25 + 0.1 * len(overlaps), 0.6)
        if season_congruent:
            standalone = min(standalone + 0.05, 0.65)
    return {
        "bonus": round(bonus, 4),
        "standalone": round(standalone, 4),
        "overlaps": sorted(overlaps),
        "fields": sorted(contributing_fields),
        "season_congruent": season_congruent,
    }


def match_candidate_with_relations(
    candidate: Mapping[str, Any],
    products: List[Mapping[str, Any]],
    relation_index: Any = None,
    threshold: float = RELATION_MATCH_THRESHOLD,
    max_matches: int = MAX_MATCHES,
) -> Dict[str, Any]:
    """Combine exact matching with supplied relation signals, conservatively."""

    if is_editorial_bypass(candidate):
        return {
            "match_status": "editorial_bypass",
            "commerce_fit": None,
            "penalized": False,
            "matches": [],
            "relation_signals_used": False,
        }

    text = _relation_candidate_text(candidate)
    association_signals = learned_association_signals(candidate)
    learned_terms = _association_terms(association_signals)
    candidate_tokens = _meaningful(_tokens(text)) | learned_terms
    candidate_season = _tokens(text) & _SEASON_TOKENS
    candidate_families = _candidate_relation_families(candidate)
    prepared_relation_index = (
        relation_index if isinstance(relation_index, Mapping)
        and relation_index.get("_prepared_relation_index") is True else None
    )
    relations = (
        prepared_relation_index.get("records", {})
        if prepared_relation_index is not None
        else relation_index if isinstance(relation_index, Mapping) else {}
    )
    base_products = (
        _narrow_base_products(candidate, products, prepared_relation_index)
        if prepared_relation_index is not None else products
    )
    base = match_candidate_to_products(candidate, base_products)
    base_by_id = {match["product_id"]: match for match in base["matches"]}
    potential_product_ids = None
    if prepared_relation_index is not None:
        term_lookup = prepared_relation_index.get("term_to_product_ids", {})
        potential_product_ids = set(base_by_id)
        potential_product_ids.update(
            _lookup_relation_product_ids(candidate_tokens, term_lookup)
        )
        for term in learned_terms:
            potential_product_ids.update(
                prepared_relation_index.get("base_term_to_product_ids", {}).get(term, set())
            )
        product_by_id = prepared_relation_index.get("product_by_id", {})
        candidate_products = [
            product_by_id[product_id]
            for product_id in sorted(potential_product_ids)
            if product_id in product_by_id
        ]
    else:
        candidate_products = products if isinstance(products, list) else []

    combined: Dict[str, Dict[str, Any]] = {}
    relation_used = False
    for product in candidate_products:
        if not isinstance(product, Mapping):
            continue
        product_id = _text(str(product.get("product_id", "")))
        if not product_id:
            continue
        base_match = base_by_id.get(product_id)
        relation = _evaluate_relation(
            candidate_tokens,
            candidate_season,
            relations.get(product_id),
            product,
        )
        owner_association = _evaluate_owner_association(association_signals, product)

        score = 0.0
        basis: List[str] = []
        if base_match:
            score = base_match["score"]
            basis = list(base_match["match_basis"])
        if relation["overlaps"]:
            if base_match:
                score = min(1.0, score + relation["bonus"])
            elif relation["standalone"] > 0:
                product_family = _text(product.get("product_family")).lower()
                specific_product_term = bool(set(relation["overlaps"]) & DIRECT_MATCH_TERMS)
                if (
                    candidate_families
                    and product_family not in candidate_families
                    and not specific_product_term
                ):
                    relation = {**relation, "overlaps": [], "fields": []}
                    continue
                score = relation["standalone"]
            else:
                # single-field relation agreement alone is not enough evidence
                relation = {**relation, "overlaps": [], "fields": []}
        if relation["overlaps"]:
            relation_used = True
            basis.append("relation_fields:" + "+".join(relation["fields"]))
            basis.extend(f"relation_term:{term}" for term in relation["overlaps"][:5])
            if relation["season_congruent"]:
                basis.append("relation_season_congruent")
        if owner_association["score"] > score:
            score = owner_association["score"]
        if owner_association["score"] > 0:
            relation_used = True
            signal = owner_association["signal"] or {}
            basis.append(f"owner_association:{signal.get('relation_type')}")
            basis.append(f"association_reference:{signal.get('reference_id')}")
            basis.extend(
                f"association_term:{term}" for term in owner_association["terms"][:5]
            )
            if signal.get("humor_allowed") is True:
                basis.append("association_tone:playful_allowed")

        # Base exact matches already passed the base matcher's threshold and are
        # always kept; the stricter threshold gates relation-only matches.
        if basis and (base_match is not None or score >= threshold):
            combined[product_id] = {
                "product_id": product_id,
                "name": _text(product.get("name")),
                "brand": _text(product.get("brand")),
                "product_family": _text(product.get("product_family")),
                "url": _text(product.get("url")),
                "score": round(score, 4),
                "match_basis": basis,
                "link_issued": False,
            }

    matches = sorted(combined.values(), key=lambda item: (-item["score"], item["product_id"]))
    matches = select_diverse_product_matches(matches, max_matches)
    if matches:
        return {
            "match_status": "matched",
            "commerce_fit": matches[0]["score"],
            "penalized": False,
            "matches": matches,
            "relation_signals_used": relation_used,
            "owner_association_signals": association_signals,
        }
    return {
        "match_status": "unmatched",
        "commerce_fit": None,
        "penalized": False,
        "matches": [],
        "relation_signals_used": relation_used,
        "owner_association_signals": association_signals,
    }


__all__ = [
    "match_candidate_with_relations",
    "relation_signal_fields",
    "prepare_relation_index",
    "RELATION_MATCH_THRESHOLD",
    "RELATION_BONUS_CAP",
    "MIN_OVERLAP_TERMS",
    "MIN_STANDALONE_FIELDS",
    "RELATION_FIELDS",
    "PRODUCT_SUPPORT_FIELD",
]
