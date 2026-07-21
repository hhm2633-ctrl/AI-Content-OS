"""Deterministic shallow signals shared by Stage-2 category profiles.

The builder is deliberately evidence-labeled and side-effect free.  It uses
only fields already present on the shallow candidate and normalized Stage-1
reaction records supplied by the caller.  It does not infer facts, classify
risk, select a category, or fetch missing evidence.
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


COMMON_CANDIDATE_SIGNALS_VERSION = "common_candidate_signals_v1"

_NUMERIC_UNIT_PATTERN = re.compile(
    r"(?<![\w])\d[\d,.]*(?:\s*)(?:%|퍼센트|percent|원|달러|usd|krw|억원|만원|천원|조|억|만|천|명|건|회|개|배|"
    r"kg|㎏|g|km|㎞|cm|㎝|mm|㎜|시간|분|초|일|주|개월|년)(?![\w])",
    re.IGNORECASE,
)
_RATIO_PATTERN = re.compile(r"(?<!\d)\d+(?:\.\d+)?\s*(?::|대)\s*\d+(?:\.\d+)?(?!\d)")

_ACTION_MARKERS: Mapping[str, Tuple[re.Pattern[str], ...]] = {
    "how_to": (
        re.compile(r"(?:하는|할|쓰는|고르는|만드는|사용하는)\s*법"),
        re.compile(r"\bhow\s+to\b", re.IGNORECASE),
        re.compile(r"방법|요령|가이드|튜토리얼|꿀팁|팁"),
    ),
    "steps": (
        re.compile(r"단계|순서|절차|첫째|둘째|셋째|먼저|다음으로|마지막으로"),
        re.compile(r"(?:^|\s)\d{1,2}[.)]\s", re.MULTILINE),
        re.compile(r"\bsteps?\b|\bchecklist\b", re.IGNORECASE),
    ),
    "list_or_materials": (
        re.compile(r"체크리스트|준비물|목록|리스트|주의사항|비교표"),
        re.compile(r"(?:^|\s)[-•]\s", re.MULTILINE),
    ),
}

_EXPLANATION_MARKERS: Mapping[str, Tuple[re.Pattern[str], ...]] = {
    "cause": (
        re.compile(r"때문|원인|이유|영향으로|결과로|따라서|그러므로|왜냐하면"),
        re.compile(r"\bbecause\b|\bdue\s+to\b|\btherefore\b", re.IGNORECASE),
    ),
    "definition_or_mechanism": (
        re.compile(r"의미|뜻은|정의|원리는|작동|과정|배경|분석|설명"),
        re.compile(r"\bmeans?\b|\bmechanism\b|\bexplains?\b", re.IGNORECASE),
    ),
    "contrast": (
        re.compile(r"반면|비교하면|차이는|달리|그러나|하지만"),
        re.compile(r"\bwhereas\b|\bhowever\b|\bcompared\s+with\b", re.IGNORECASE),
    ),
}

_INTERNATIONAL_TERMS = (
    "해외", "국제", "글로벌", "외신", "미국", "중국", "일본", "유럽", "영국", "프랑스",
    "독일", "러시아", "우크라이나", "중동", "유엔", "eu", "asia", "global", "world",
)
_COMMERCE_TERMS = (
    "가격", "할인", "구매", "판매", "품절", "재입고", "신상품", "신상", "추천템", "가성비",
    "쿠폰", "특가", "세일", "리뷰", "후기", "장바구니", "배송", "원", "달러", "price",
    "sale", "discount", "buy", "review",
)
_SEASON_TERMS: Mapping[str, Tuple[str, ...]] = {
    "spring": ("봄", "신학기", "벚꽃", "환절기", "spring"),
    "summer": ("여름", "장마", "폭염", "휴가", "바캉스", "summer"),
    "autumn": ("가을", "추석", "단풍", "환절기", "autumn", "fall"),
    "winter": ("겨울", "한파", "크리스마스", "연말", "설날", "winter"),
}


def _record(
    value: Any,
    status: str,
    provenance: Mapping[str, Any],
    confidence: float,
    reason: str,
) -> Dict[str, Any]:
    return {
        "value": value,
        "status": status,
        "provenance": dict(provenance),
        "confidence": round(max(0.0, min(1.0, float(confidence))), 6),
        "reason": reason,
    }


def _missing(reason: str, fields: Sequence[str] = ()) -> Dict[str, Any]:
    return _record(None, "missing", {"fields": list(fields)}, 0.0, reason)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _candidate_text(candidate: Mapping[str, Any]) -> Tuple[str, Dict[str, str]]:
    fields = {
        name: _text(candidate.get(name))
        for name in ("title", "summary")
        if _text(candidate.get(name))
    }
    return "\n".join(fields.values()), fields


def _parse_timestamp(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None


def _measured_age(candidate: Mapping[str, Any]) -> Tuple[Optional[float], Dict[str, Any], float, str]:
    published_raw = _text(candidate.get("published_at"))
    collected_raw = _text(candidate.get("collected_at"))
    if not published_raw or not collected_raw:
        return None, {"fields": ["published_at", "collected_at"]}, 0.0, "both timestamps are required"
    published = _parse_timestamp(published_raw)
    collected = _parse_timestamp(collected_raw)
    if published is None or collected is None:
        return None, {"published_at": published_raw, "collected_at": collected_raw}, 0.0, "timestamp parsing failed"
    if (published.tzinfo is None) != (collected.tzinfo is None):
        return None, {"published_at": published_raw, "collected_at": collected_raw}, 0.0, "mixed timezone awareness is not comparable"
    age_hours = (collected - published).total_seconds() / 3600.0
    if age_hours < 0:
        return None, {"published_at": published_raw, "collected_at": collected_raw}, 0.0, "published_at is later than collected_at"
    confidence = 1.0 if published.tzinfo is not None else 0.8
    return (
        round(age_hours, 6),
        {"published_at": published_raw, "collected_at": collected_raw, "age_hours": round(age_hours, 6)},
        confidence,
        "age measured from supplied timestamps",
    )


def _freshness_and_novelty(candidate: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    age, provenance, confidence, reason = _measured_age(candidate)
    if age is None:
        missing = _record(None, "missing", provenance, confidence, reason)
        return missing, dict(missing)

    if age <= 24:
        freshness = 1.0
    elif age <= 48:
        freshness = 0.75
    elif age <= 72:
        freshness = 0.5
    elif age <= 336:
        freshness = 0.25
    else:
        freshness = 0.1

    if age <= 6:
        novelty = 1.0
    elif age <= 24:
        novelty = 0.8
    elif age <= 72:
        novelty = 0.5
    elif age <= 168:
        novelty = 0.25
    else:
        novelty = 0.1

    return (
        _record(freshness, "measured", provenance, confidence, "fixed age bands; no semantic novelty inferred"),
        _record(novelty, "measured", provenance, confidence, "temporal novelty proxy from fixed age bands"),
    )


def _reaction_velocity(stage1: Mapping[str, Any], age_record: Mapping[str, Any]) -> Dict[str, Any]:
    if age_record.get("status") != "measured":
        return _missing("measured timestamps are required", ("published_at", "collected_at"))
    age_hours = age_record.get("provenance", {}).get("age_hours")
    if not isinstance(age_hours, (int, float)) or isinstance(age_hours, bool):
        return _missing("measured timestamp age is unavailable")

    observed: List[Tuple[str, float, float, Any]] = []
    observed_without_normalized: List[str] = []
    for name in ("comments", "likes", "dislikes"):
        item = stage1.get(name)
        if not isinstance(item, Mapping) or item.get("status") != "observed":
            continue
        normalized = item.get("normalized_value")
        if isinstance(normalized, bool) or not isinstance(normalized, (int, float)) or not 0.0 <= float(normalized) <= 1.0:
            observed_without_normalized.append(name)
            continue
        confidence = item.get("confidence")
        signal_confidence = float(confidence) if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) else 0.0
        observed.append((name, float(normalized), max(0.0, min(1.0, signal_confidence)), item.get("raw_value")))

    if not observed:
        reason = "observed reactions lack Stage-1 normalized values" if observed_without_normalized else "no observed reaction signal"
        return _record(
            None,
            "missing",
            {"reaction_signals": observed_without_normalized},
            0.0,
            reason,
        )

    relative_reaction = sum(item[1] for item in observed) / len(observed)
    # A fixed 24-hour half-window discounts otherwise comparable normalized
    # reactions without introducing raw site-scale thresholds.
    age_factor = 24.0 / (24.0 + float(age_hours))
    value = round(relative_reaction * age_factor, 6)
    timestamp_confidence = age_record.get("confidence", 0.0)
    confidence = (sum(item[2] for item in observed) / len(observed)) * float(timestamp_confidence)
    return _record(
        value,
        "measured",
        {
            "method": "mean_stage1_normalized_reaction_x_24h_age_factor",
            "age_hours": age_hours,
            "signals": [
                {"name": name, "normalized_value": normalized, "raw_value": raw}
                for name, normalized, _confidence, raw in observed
            ],
        },
        confidence,
        "relative reaction velocity proxy; raw cross-site counts were not re-normalized",
    )


def _numeric_evidence(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    text, fields = _candidate_text(candidate)
    if not fields:
        return _missing("title or summary text is required", ("title", "summary"))
    matches_by_field: Dict[str, List[str]] = {}
    for field, value in fields.items():
        matches = [match.group(0) for match in _NUMERIC_UNIT_PATTERN.finditer(value)]
        matches.extend(match.group(0) for match in _RATIO_PATTERN.finditer(value))
        if matches:
            matches_by_field[field] = matches
    count = sum(len(matches) for matches in matches_by_field.values())
    if count == 0:
        value = 0.0
    elif len(matches_by_field) >= 2:
        value = 1.0
    elif count >= 2:
        value = 0.75
    else:
        value = 0.5
    return _record(
        value,
        "observed",
        {"text_fields": sorted(fields), "matches_by_field": matches_by_field},
        1.0 if len(fields) == 2 else 0.75,
        "numeric units or explicit ratios found in shallow text" if count else "no numeric unit or ratio found in supplied shallow text",
    )


def _information_completeness(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    weights = {"title": 0.25, "summary": 0.35, "publisher": 0.15, "published_at": 0.15, "link": 0.1}
    present = [field for field in weights if _text(candidate.get(field))]
    if not present:
        return _missing("no assessable shallow information fields", tuple(weights))
    value = round(sum(weights[field] for field in present), 6)
    missing = [field for field in weights if field not in present]
    return _record(
        value,
        "measured",
        {"weights": weights, "present_fields": present, "missing_fields": missing},
        1.0,
        "weighted presence of shallow information fields",
    )


def _matched_marker_groups(text: str, marker_map: Mapping[str, Tuple[re.Pattern[str], ...]]) -> Dict[str, List[str]]:
    output: Dict[str, List[str]] = {}
    for group, patterns in marker_map.items():
        matches: List[str] = []
        for pattern in patterns:
            matches.extend(match.group(0) for match in pattern.finditer(text))
        if matches:
            output[group] = matches
    return output


def _practical_actionability(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    text, fields = _candidate_text(candidate)
    if not fields:
        return _missing("title or summary text is required", ("title", "summary"))
    groups = _matched_marker_groups(text, _ACTION_MARKERS)
    count = len(groups)
    value = (0.0, 0.5, 0.75, 1.0)[min(count, 3)]
    return _record(
        value,
        "observed",
        {"text_fields": sorted(fields), "matched_marker_groups": groups},
        0.9 if "summary" in fields else 0.65,
        "explicit how-to/list/step structure only; usefulness is not inferred",
    )


def _explainability(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    text, fields = _candidate_text(candidate)
    if not fields:
        return _missing("title or summary text is required", ("title", "summary"))
    groups = _matched_marker_groups(text, _EXPLANATION_MARKERS)
    marker_component = min(len(groups) / 2.0, 1.0)
    summary = fields.get("summary", "")
    if not summary:
        summary_component = 0.0
    elif len(summary) >= 120:
        summary_component = 1.0
    elif len(summary) >= 40:
        summary_component = 0.75
    else:
        summary_component = 0.5
    value = round((marker_component * 0.6) + (summary_component * 0.4), 6)
    return _record(
        value,
        "observed",
        {
            "text_fields": sorted(fields),
            "matched_marker_groups": groups,
            "summary_length": len(summary),
            "components": {"marker": marker_component, "summary_completeness": summary_component},
        },
        0.9 if summary else 0.6,
        "causal/explanatory markers plus shallow summary completeness; factual accuracy is not inferred",
    )


def _term_matches(text: str, terms: Sequence[str]) -> List[str]:
    lowered = text.lower()
    matches: List[str] = []
    for term in terms:
        lowered_term = term.lower()
        if lowered_term == "원":
            # A bare syllable would also match unrelated words such as
            # ``원인``.  Require explicit price-unit evidence for this tag.
            matched = bool(re.search(r"\d[\d,.]*\s*원(?![\w])", text))
        elif lowered_term.isascii() and lowered_term.isalpha():
            matched = bool(re.search(rf"\b{re.escape(lowered_term)}\b", lowered))
        else:
            matched = lowered_term in lowered
        if matched:
            matches.append(term)
    return matches


def _tags(candidate: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    text, fields = _candidate_text(candidate)
    if not fields:
        missing = _missing("title or summary text is required", ("title", "summary"))
        return {"international": dict(missing), "commerce_signal": dict(missing), "seasonality": dict(missing)}
    confidence = 0.9 if "summary" in fields else 0.65
    international_matches = _term_matches(text, _INTERNATIONAL_TERMS)
    commerce_matches = _term_matches(text, _COMMERCE_TERMS)
    season_matches = {
        season: _term_matches(text, terms)
        for season, terms in _SEASON_TERMS.items()
    }
    season_matches = {season: matches for season, matches in season_matches.items() if matches}
    return {
        "international": _record(
            bool(international_matches), "observed", {"text_fields": sorted(fields), "matches": international_matches},
            confidence, "transparent international lexicon match; geopolitical meaning is not inferred",
        ),
        "commerce_signal": _record(
            bool(commerce_matches), "observed", {"text_fields": sorted(fields), "matches": commerce_matches},
            confidence, "transparent commerce lexicon match; purchase intent is not inferred",
        ),
        "seasonality": _record(
            sorted(season_matches), "observed", {"text_fields": sorted(fields), "matches_by_season": season_matches},
            confidence, "transparent season lexicon match; seasonal demand is not inferred",
        ),
    }


def build_common_candidate_signals(candidate: Any, stage1_signals: Any) -> Dict[str, Any]:
    """Build evidence-labeled common signals without mutating either input."""
    if not isinstance(candidate, Mapping) or not isinstance(stage1_signals, Mapping):
        missing = _missing("candidate and stage1_signals must both be objects")
        signal_names = (
            "freshness", "reaction_velocity", "novelty", "numeric_evidence_strength",
            "information_completeness", "practical_actionability", "explainability",
        )
        return {
            "schema_version": COMMON_CANDIDATE_SIGNALS_VERSION,
            "status": "closed",
            "reason_code": "malformed_input",
            "signals": {name: dict(missing) for name in signal_names},
            "tags": {name: dict(missing) for name in ("international", "commerce_signal", "seasonality")},
        }

    freshness, novelty = _freshness_and_novelty(candidate)
    signals = {
        "freshness": freshness,
        "reaction_velocity": _reaction_velocity(stage1_signals, freshness),
        "novelty": novelty,
        "numeric_evidence_strength": _numeric_evidence(candidate),
        "information_completeness": _information_completeness(candidate),
        "practical_actionability": _practical_actionability(candidate),
        "explainability": _explainability(candidate),
    }
    return {
        "schema_version": COMMON_CANDIDATE_SIGNALS_VERSION,
        "status": "ok",
        "signals": signals,
        "tags": _tags(candidate),
    }


__all__ = ["build_common_candidate_signals", "COMMON_CANDIDATE_SIGNALS_VERSION"]
