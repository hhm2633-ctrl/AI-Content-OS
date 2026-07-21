"""Build evidence-labelled shallow signals for the seven Stage-2 categories.

The builder is intentionally offline and conservative.  It derives only signals
that are directly observable in the supplied shallow candidate, Stage-1 records,
common-signal records, or origin-resolution result.  Missing evidence is never
converted to zero and absence of a risk indicator is never treated as clearance.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, Iterable, Mapping, Optional


CATEGORY_SPECIFIC_SIGNAL_BUILDER_VERSION = "category_specific_signal_builder_v1"

CATEGORY_SIGNAL_NAMES = {
    "major_news_policy": (
        "origin_evidence_strength", "public_impact", "freshness",
        "information_completeness", "attention", "explainability",
    ),
    "incident_conflict": (
        "factual_evidence", "public_interest", "risk_clearance",
        "cross_source_confirmation", "freshness", "attention",
    ),
    "economy_market": (
        "numeric_evidence", "everyday_impact", "source_reliability",
        "timeliness", "explainability", "source_agreement",
    ),
    "entertainment_relationship": (
        "independent_confirmation", "reaction_velocity", "freshness",
        "narrative_explainability", "public_relevance",
        "evidence_feasibility", "novelty",
    ),
    "community_buzz": (
        "reaction_strength", "spread_velocity", "cross_community_recurrence",
        "explainability", "news_evidence_bridge", "novelty",
    ),
    "beauty_fashion": (
        "recurrence", "positive_reaction", "practical_specificity",
        "visuality", "seasonality", "evidence_feasibility",
    ),
    "lifestyle_knowledge": (
        "utility_actionability", "completeness", "source_evidence",
        "durability_recurrence", "seasonality_timing", "attention",
    ),
}

COMMUNITY_SOURCE_IDS = {
    "nate_pann", "fmkorea", "bobaedream", "dcinside", "theqoo",
    "ppomppu", "ruliweb", "dogdrip",
}
NEWS_SOURCE_IDS = {
    "naver_news", "daum_news", "nate_news_rank", "yonhap", "newsis",
    "news1", "hankyung_economy", "mk_economy", "moneytoday", "edaily",
}

TEXT_FIELDS = ("title", "keyword", "summary", "board_or_category", "category")

POLICY_SCOPE_PATTERNS = (
    r"전\s*국민", r"전국(?:적|으로)?", r"모든\s+(?:시민|주민|근로자|학생)",
    r"지원\s*대상", r"적용\s*대상", r"전국\s*시행",
)
POLICY_POPULATION_PATTERN = re.compile(
    r"(?:약\s*)?\d[\d,.]*\s*(?:만|천)?\s*(?:명|가구|사업자|근로자|학생|국민|주민)"
)
PUBLIC_SERVICE_TERMS = (
    "공공서비스", "복지 서비스", "교육 지원", "의료 지원", "주거 지원",
    "교통 지원", "보육 지원", "재난 지원", "사회보험", "기초연금",
)

INCIDENT_OFFICIAL_PATTERNS = (
    r"경찰(?:은|이|가|에 따르면|\s*발표)", r"소방(?:당국|청|서)(?:은|이|가|에 따르면)?",
    r"구조\s*당국", r"재난\s*당국", r"행정안전부(?:는|가|에 따르면)?",
)
PUBLIC_SAFETY_TERMS = (
    "대피령", "대피 명령", "재난문자", "안전 안내", "통제 구간",
    "교통 통제", "인명 피해", "안전사고", "구조 작업",
)
VICTIM_COUNT_PATTERN = re.compile(
    r"\d[\d,]*\s*명(?:이|의)?\s*(?:사망|부상|실종|피해|구조|대피)"
)
EMERGENCY_TERMS = ("비상 대응", "긴급 구조", "긴급 대피", "응급 대응", "비상사태")

ECONOMY_MARKER_GROUPS = {
    "prices": ("물가", "소비자물가", "가격 인상", "가격 인하", "생활비", "장바구니"),
    "taxes": ("세금", "세율", "소득세", "부가세", "재산세", "종부세"),
    "rates": ("기준금리", "대출금리", "예금금리", "이자 부담"),
    "housing": ("주택 가격", "집값", "전세", "월세", "주거비", "분양가"),
    "jobs": ("고용", "실업", "일자리", "채용", "임금", "최저임금"),
    "bills": ("전기요금", "가스요금", "수도요금", "통신비", "보험료", "공과금"),
}

ATTRIBUTED_OFFICIAL_PATTERNS = (
    r"공식\s*입장", r"소속사(?:는|가|\s*측은|\s*측이).{0,30}(?:밝혔|발표|전했|설명)",
    r"관계자(?:는|가).{0,30}(?:밝혔|전했|설명)",
    r"본인(?:은|이).{0,30}(?:밝혔|전했|설명)",
    r"제작사(?:는|가|\s*측은).{0,30}(?:밝혔|발표|전했|설명)",
)

BEAUTY_PRODUCT_TERMS = (
    "화장품", "선크림", "파운데이션", "쿠션", "립스틱", "틴트", "세럼",
    "크림", "토너", "샴푸", "트리트먼트", "재킷", "셔츠", "바지",
    "원피스", "스커트", "신발", "가방",
)
BEAUTY_USE_PATTERNS = (
    r"(?:사용|바르|입|신|매|고르)는\s*법", r"사용법", r"착용법", r"코디(?:법|하는 법)",
    r"\d+\s*(?:단계|번|회|분|시간|ml|g)", r"(?:먼저|다음|마지막으로).{1,40}",
)

LIFESTYLE_ACTION_PATTERNS = (
    r"하는\s*법", r"사용법", r"방법", r"순서", r"\d+\s*단계", r"체크리스트",
    r"준비물", r"(?:먼저|다음|마지막으로).{1,40}", r"\b(?:step|how\s*to)\b",
)
EVERGREEN_PATTERNS = (
    r"매(?:년|달|주|일)", r"정기적으로", r"주기적으로", r"상시", r"반복(?:해서|적으로)",
    r"언제든", r"기본\s*원칙", r"계속\s*활용",
)


def _missing(reason: str) -> Dict[str, Any]:
    return {
        "value": None,
        "status": "missing",
        "provenance": [],
        "confidence": 0.0,
        "reason": reason,
    }


def _observed(value: float, provenance: Any, confidence: float, reason: str) -> Dict[str, Any]:
    return {
        "value": round(max(0.0, min(1.0, float(value))), 6),
        "status": "observed",
        "provenance": copy.deepcopy(provenance),
        "confidence": round(max(0.0, min(1.0, float(confidence))), 6),
        "reason": reason,
    }


def _blank_category_signals(reason: str = "unsupported_by_shallow_evidence") -> Dict[str, Dict[str, Any]]:
    return {
        category_id: {name: _missing(reason) for name in names}
        for category_id, names in CATEGORY_SIGNAL_NAMES.items()
    }


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _candidate_text(candidate: Mapping[str, Any]) -> str:
    return " ".join(_text(candidate.get(field)) for field in TEXT_FIELDS if _text(candidate.get(field)))


def _matches(text: str, patterns: Iterable[str]) -> list[str]:
    found = []
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            found.append(match.group(0))
    return found


def _term_matches(text: str, terms: Iterable[str]) -> list[str]:
    return [term for term in terms if term.casefold() in text.casefold()]


def _copy_common(common: Mapping[str, Any], *names: str) -> Optional[Dict[str, Any]]:
    for name in names:
        record = common.get(name)
        if not isinstance(record, Mapping):
            continue
        value = record.get("value")
        confidence = record.get("confidence")
        if (
            isinstance(value, (int, float)) and not isinstance(value, bool)
            and 0.0 <= float(value) <= 1.0
            and isinstance(confidence, (int, float)) and not isinstance(confidence, bool)
            and 0.0 <= float(confidence) <= 1.0
            and record.get("status") in {"observed", "supported", "measured"}
            and "provenance" in record and isinstance(record.get("reason"), str)
        ):
            return copy.deepcopy(dict(record))
    return None


def _origin_record(origin_result: Mapping[str, Any], reason: str) -> Optional[Dict[str, Any]]:
    origin = origin_result.get("origin_independence")
    if not isinstance(origin, Mapping):
        return None
    value = origin.get("score")
    confidence = origin.get("confidence")
    if (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and 0.0 <= float(value) <= 1.0
    ):
        return _observed(
            float(value),
            {
                "source": "origin_result.origin_independence",
                "independent_origin_count": origin.get("independent_origin_count"),
                "origin_groups": copy.deepcopy(origin.get("origin_groups", [])),
                "details": copy.deepcopy(origin.get("provenance", [])),
            },
            float(confidence) if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) else 0.5,
            reason,
        )
    return None


def _source_ids(candidate: Mapping[str, Any]) -> set[str]:
    records = [candidate]
    refs = candidate.get("source_refs")
    if isinstance(refs, list):
        records.extend(item for item in refs if isinstance(item, Mapping))
    agreement = candidate.get("source_agreement")
    if isinstance(agreement, Mapping) and isinstance(agreement.get("sources"), list):
        records.extend(item for item in agreement["sources"] if isinstance(item, Mapping))
    return {
        _text(record.get("source_id")).casefold()
        for record in records
        if _text(record.get("source_id"))
    }


def _stage1_likes(stage1: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    likes = stage1.get("likes")
    if not isinstance(likes, Mapping) or likes.get("status") != "observed":
        return None
    value = likes.get("normalized_value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
        return None
    confidence = likes.get("confidence")
    return _observed(
        float(value),
        {
            "source": "stage1_signals.likes",
            "basis": likes.get("basis"),
            "sample_size": likes.get("sample_size"),
            "raw_value": likes.get("raw_value"),
            "value_origin": likes.get("value_origin"),
        },
        float(confidence) if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) else 0.5,
        "normalized likes are an observed positive-reaction signal",
    )


def build_category_specific_signals(
    candidate: Any,
    stage1_signals: Any,
    common_signals: Any,
    origin_result: Any,
) -> Dict[str, Any]:
    """Return deterministic provenance-bearing records for all configured signals."""

    signals = _blank_category_signals()
    if not all(isinstance(value, Mapping) for value in (candidate, stage1_signals, common_signals, origin_result)):
        return {
            "schema_version": CATEGORY_SPECIFIC_SIGNAL_BUILDER_VERSION,
            "status": "closed",
            "reason_code": "invalid_input",
            "category_signals": _blank_category_signals("invalid_input"),
        }

    text = _candidate_text(candidate)
    summary = _text(candidate.get("summary"))

    # Generic records are copied only when another calculator supplied a valid,
    # provenance-bearing value.  Category fit is never accepted as a signal.
    generic_map = {
        ("major_news_policy", "freshness"): ("freshness",),
        ("major_news_policy", "information_completeness"): ("information_completeness", "completeness"),
        ("major_news_policy", "attention"): ("attention", "reaction_strength"),
        ("major_news_policy", "explainability"): ("explainability",),
        ("incident_conflict", "freshness"): ("freshness",),
        ("incident_conflict", "attention"): ("attention", "reaction_strength"),
        ("economy_market", "numeric_evidence"): ("numeric_evidence", "numeric_evidence_strength"),
        ("economy_market", "timeliness"): ("freshness", "timeliness"),
        ("economy_market", "explainability"): ("explainability",),
        ("entertainment_relationship", "reaction_velocity"): ("reaction_velocity",),
        ("entertainment_relationship", "freshness"): ("freshness",),
        ("entertainment_relationship", "novelty"): ("novelty",),
        ("community_buzz", "reaction_strength"): ("reaction_strength", "attention"),
        ("community_buzz", "spread_velocity"): ("reaction_velocity", "spread_velocity"),
        ("community_buzz", "explainability"): ("explainability",),
        ("community_buzz", "novelty"): ("novelty",),
        ("beauty_fashion", "recurrence"): ("recurrence",),
        ("beauty_fashion", "seasonality"): ("seasonality",),
        ("beauty_fashion", "evidence_feasibility"): ("evidence_feasibility",),
        ("lifestyle_knowledge", "completeness"): ("information_completeness", "completeness"),
        ("lifestyle_knowledge", "seasonality_timing"): ("seasonality", "seasonality_timing"),
        ("lifestyle_knowledge", "attention"): ("attention", "reaction_strength"),
    }
    for (category_id, signal_name), aliases in generic_map.items():
        record = _copy_common(common_signals, *aliases)
        if record is not None:
            signals[category_id][signal_name] = record

    origin = _origin_record(origin_result, "resolved factual-origin evidence")
    if origin is not None:
        for category_id, signal_name in (
            ("major_news_policy", "origin_evidence_strength"),
            ("incident_conflict", "factual_evidence"),
            ("incident_conflict", "cross_source_confirmation"),
            ("economy_market", "source_reliability"),
            ("economy_market", "source_agreement"),
            ("entertainment_relationship", "independent_confirmation"),
            ("lifestyle_knowledge", "source_evidence"),
        ):
            signals[category_id][signal_name] = copy.deepcopy(origin)

    policy_scope = _matches(text, POLICY_SCOPE_PATTERNS)
    policy_population = POLICY_POPULATION_PATTERN.findall(text)
    policy_services = _term_matches(text, PUBLIC_SERVICE_TERMS)
    policy_groups = sum(bool(items) for items in (policy_scope, policy_population, policy_services))
    if policy_groups:
        signals["major_news_policy"]["public_impact"] = _observed(
            min(1.0, 0.4 + 0.2 * policy_groups),
            {"source": "candidate_shallow_text", "scope": policy_scope,
             "affected_population": policy_population, "public_services": policy_services},
            0.75 if policy_groups >= 2 else 0.6,
            "explicit public scope, affected-population, or public-service evidence",
        )

    incident_official = _matches(text, INCIDENT_OFFICIAL_PATTERNS)
    incident_safety = _term_matches(text, PUBLIC_SAFETY_TERMS)
    incident_victims = VICTIM_COUNT_PATTERN.findall(text)
    incident_emergency = _term_matches(text, EMERGENCY_TERMS)
    incident_groups = sum(bool(items) for items in (
        incident_official, incident_safety, incident_victims, incident_emergency,
    ))
    if incident_groups:
        signals["incident_conflict"]["public_interest"] = _observed(
            min(1.0, 0.35 + 0.2 * incident_groups),
            {"source": "candidate_shallow_text", "official": incident_official,
             "public_safety": incident_safety, "victim_count": incident_victims,
             "emergency": incident_emergency},
            0.8 if incident_groups >= 2 else 0.6,
            "explicit official, public-safety, victim-count, or emergency evidence",
        )

    economy_groups = {
        name: _term_matches(text, terms)
        for name, terms in ECONOMY_MARKER_GROUPS.items()
    }
    observed_economy_groups = {name: hits for name, hits in economy_groups.items() if hits}
    if observed_economy_groups:
        signals["economy_market"]["everyday_impact"] = _observed(
            min(1.0, 0.4 + 0.2 * len(observed_economy_groups)),
            {"source": "candidate_shallow_text", "domains": observed_economy_groups},
            0.65 if len(observed_economy_groups) == 1 else 0.8,
            "explicit household price, tax, rate, housing, job, or bill evidence",
        )

    if len(summary) >= 20:
        sentence_count = len([part for part in re.split(r"[.!?。]+", summary) if part.strip()])
        narrative_value = 0.55 if len(summary) < 60 and sentence_count < 2 else 0.75
        signals["entertainment_relationship"]["narrative_explainability"] = _observed(
            narrative_value,
            {"source": "candidate.summary", "character_count": len(summary),
             "sentence_count": sentence_count},
            0.65,
            "supplied summary provides a shallow narrative description",
        )
        attributed = _matches(summary, ATTRIBUTED_OFFICIAL_PATTERNS)
        if attributed:
            signals["entertainment_relationship"]["evidence_feasibility"] = _observed(
                0.8,
                {"source": "candidate.summary", "attributed_statement_markers": attributed},
                0.75,
                "summary contains an attributed official-statement marker",
            )

    source_ids = _source_ids(candidate)
    community_ids = sorted(source_ids & COMMUNITY_SOURCE_IDS)
    news_ids = sorted(source_ids & NEWS_SOURCE_IDS)
    if len(community_ids) >= 2:
        signals["community_buzz"]["cross_community_recurrence"] = _observed(
            min(1.0, len(community_ids) / 3.0),
            {"source": "supplied_source_references", "community_source_ids": community_ids},
            0.85,
            "at least two distinct approved community sources are supplied",
        )
    if community_ids and news_ids:
        signals["community_buzz"]["news_evidence_bridge"] = _observed(
            1.0,
            {"source": "supplied_source_references", "community_source_ids": community_ids,
             "news_source_ids": news_ids},
            0.85,
            "both community and approved news/wire evidence are supplied",
        )

    product_terms = _term_matches(text, BEAUTY_PRODUCT_TERMS)
    use_details = _matches(text, BEAUTY_USE_PATTERNS)
    if product_terms and use_details:
        signals["beauty_fashion"]["practical_specificity"] = _observed(
            min(1.0, 0.6 + 0.1 * min(len(use_details), 3)),
            {"source": "candidate_shallow_text", "product_terms": product_terms,
             "use_or_step_details": use_details},
            0.75,
            "explicit beauty/fashion product and use-or-step details are supplied",
        )

    media = candidate.get("media_flags")
    if isinstance(media, Mapping):
        observed_flags = {
            key: value for key, value in media.items()
            if key in {"has_image", "has_video", "image_count"}
            and ((isinstance(value, bool)) or (key == "image_count" and isinstance(value, int) and not isinstance(value, bool) and value >= 0))
        }
        if observed_flags:
            has_visual = (
                observed_flags.get("has_image") is True
                or observed_flags.get("has_video") is True
                or observed_flags.get("image_count", 0) > 0
            )
            signals["beauty_fashion"]["visuality"] = _observed(
                1.0 if has_visual else 0.0,
                {"source": "candidate.media_flags", "observed_flags": observed_flags},
                0.95,
                "visual media presence is explicitly observed" if has_visual else "visual media absence is explicitly observed",
            )

    positive_reaction = _stage1_likes(stage1_signals)
    if positive_reaction is not None:
        signals["beauty_fashion"]["positive_reaction"] = positive_reaction

    actionability = _matches(text, LIFESTYLE_ACTION_PATTERNS)
    if actionability:
        signals["lifestyle_knowledge"]["utility_actionability"] = _observed(
            min(1.0, 0.55 + 0.15 * min(len(actionability), 3)),
            {"source": "candidate_shallow_text", "step_or_howto_markers": actionability},
            0.7,
            "explicit step, how-to, checklist, sequence, or preparation markers are supplied",
        )

    durability = _matches(text, EVERGREEN_PATTERNS)
    if durability:
        signals["lifestyle_knowledge"]["durability_recurrence"] = _observed(
            min(1.0, 0.6 + 0.1 * min(len(durability), 3)),
            {"source": "candidate_shallow_text", "evergreen_or_recurrence_markers": durability},
            0.7,
            "explicit evergreen or recurrence evidence is supplied",
        )

    return {
        "schema_version": CATEGORY_SPECIFIC_SIGNAL_BUILDER_VERSION,
        "status": "ok",
        "reason_code": "signals_built",
        "category_signals": signals,
    }


__all__ = [
    "CATEGORY_SIGNAL_NAMES",
    "CATEGORY_SPECIFIC_SIGNAL_BUILDER_VERSION",
    "build_category_specific_signals",
]
