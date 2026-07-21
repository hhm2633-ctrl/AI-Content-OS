"""Normalize candidate selection signals used by category final selection.

This module performs only deterministic, side-effect-free normalization:

* source_count from explicit count fields or distinct supplied URLs/domains,
* reaction_count from explicitly named count fields with alias-safe deduping,
* media_count from supplied image/video/media asset lists,
* signal_provenance describing per-signal extraction decisions.

Missing values remain unknown (None). Invalid values are rejected instead of
invented: booleans, negatives, NaN, malformed containers and non-numeric
strings are not coerced into counts.
"""

from __future__ import annotations

from math import isnan
from typing import Any, Dict, Iterable, List, Mapping, Set, Tuple
from urllib.parse import urlparse


CANDIDATE_SELECTION_SIGNAL_NORMALIZER_VERSION = "candidate_selection_signal_normalizer_v1"


_SOURCE_COUNT_FIELDS: Tuple[str, ...] = ("source_count", "distinct_source_count", "num_sources")
_SOURCE_URL_FIELDS: Tuple[str, ...] = ("source_urls", "urls", "links", "source_links")
_MEDIA_LIST_FIELDS: Tuple[str, ...] = (
    "media",
    "media_urls",
    "assets",
    "asset_urls",
    "images",
    "image_urls",
    "videos",
    "video_urls",
)

_REACTION_FIELD_GROUPS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("comments", ("comment_count", "comments")),
    ("likes", ("like_count", "likes")),
    ("dislikes", ("dislike_count", "dislikes")),
    ("scraps", ("scrap_count", "scraps")),
    ("shares", ("share_count", "shares")),
    ("reactions", ("reaction_count", "public_reaction", "reactions")),
)


def _coerce_nonnegative_count(value: Any) -> Tuple[bool, int | None]:
    if value is None or isinstance(value, bool):
        return False, None

    if isinstance(value, int):
        return (value >= 0), value if value >= 0 else None

    if isinstance(value, float):
        if isnan(value) or value < 0:
            return False, None
        if not value.is_integer():
            return False, None
        return True, int(value)

    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return False, None
        try:
            number = int(text)
            if number < 0:
                return False, None
            return True, number
        except ValueError:
            try:
                number = float(text)
            except ValueError:
                return False, None
            if number < 0 or isnan(number) or not number.is_integer():
                return False, None
            return True, int(number)

    return False, None


def _extract_url_identifier(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None

    parsed = urlparse(text)
    if parsed.scheme and parsed.netloc:
        host = parsed.hostname or ""
        if host:
            return host.lower()
        return None

    lowered = text.lower()
    if "/" in lowered:
        lowered = lowered.split("/", 1)[0]
    if "?" in lowered:
        lowered = lowered.split("?", 1)[0]
    if "#" in lowered:
        lowered = lowered.split("#", 1)[0]

    if "." in lowered and not lowered.startswith("http"):
        return lowered.lstrip("www.").strip()

    return None


def _coerce_nonnegative_count_with_status(candidate: Mapping[str, Any], names: Iterable[str], required: bool = True):
    used: List[str] = []
    for name in names:
        if name not in candidate:
            continue
        valid, coerced = _coerce_nonnegative_count(candidate.get(name))
        if valid:
            return coerced, [name], "coerced"
        used.append(name)

    if used:
        return None, used, "invalid"
    if required:
        return None, list(names), "missing"
    return None, list(used), "missing"


def _normalize_source_count(candidate: Mapping[str, Any]) -> Tuple[int | None, Dict[str, Any]]:
    explicit, fields, status = _coerce_nonnegative_count_with_status(candidate, _SOURCE_COUNT_FIELDS)
    if status == "coerced":
        return explicit, {
            "status": "normalized",
            "source": "explicit_count_fields",
            "fields": fields,
            "reason": "explicit nonnegative count provided",
        }
    if status == "invalid":
        return None, {
            "status": "invalid",
            "reason": "source_count fields were present but invalid",
            "fields": fields,
        }

    present_url_fields = [name for name in _SOURCE_URL_FIELDS if name in candidate]
    if not present_url_fields:
        return None, {
            "status": "missing",
            "reason": "source_count and source URL fields absent",
            "fields": list(_SOURCE_URL_FIELDS),
        }

    raw_values: List[Any] = []
    url_field: List[str] = []
    malformed: List[str] = []
    for name in present_url_fields:
        value = candidate.get(name)
        if not isinstance(value, list):
            malformed.append(name)
            continue
        url_field.append(name)
        raw_values.extend(value)

    if malformed:
        return None, {
            "status": "invalid",
            "reason": "source URL container malformed (expected list)",
            "fields": malformed,
        }

    # Count distinct normalized URL/domain identifiers. Parsed URLs are reduced
    # to domain keys to avoid double-counting URL variants for the same source.
    identifiers: Set[str] = set()
    for value in raw_values:
        if isinstance(value, str):
            token = value.strip()
            if not token:
                continue
            domain = _extract_url_identifier(token)
            identifiers.add(domain or token)

    return len(identifiers), {
        "status": "normalized",
        "source": "distinct_source_urls_or_domains",
        "fields": url_field,
        "item_count": len(raw_values),
        "distinct_count": len(identifiers),
        "reason": "derived from supplied URLs/domains",
    }


def _normalize_reaction_count(candidate: Mapping[str, Any]) -> Tuple[int | None, Dict[str, Any]]:
    total = 0
    used_fields: List[str] = []
    invalid_fields: List[str] = []
    has_any_alias = any(
        alias in candidate
        for _, aliases in _REACTION_FIELD_GROUPS
        for alias in aliases
    )

    for _, aliases in _REACTION_FIELD_GROUPS:
        found = False
        invalid_group = False
        for alias in aliases:
            if alias not in candidate:
                continue
            found = True
            valid, coerced = _coerce_nonnegative_count(candidate.get(alias))
            if not valid:
                invalid_fields.append(alias)
                invalid_group = True
            else:
                used_fields.append(alias)
                total += coerced
            break

        if found and invalid_group:
            return None, {
                "status": "invalid",
                "reason": "reaction alias group malformed",
                "invalid_fields": sorted(set(invalid_fields)),
            }

    if not used_fields:
        if has_any_alias:
            return None, {
                "status": "invalid",
                "reason": "reaction aliases present but no valid values",
                "invalid_fields": sorted(set(invalid_fields)),
            }
        return None, {
            "status": "missing",
            "reason": "no reaction fields present",
            "fields": [name for _, aliases in _REACTION_FIELD_GROUPS for name in aliases],
        }

    return total, {
        "status": "normalized",
        "source": "explicit_reaction_alias_groups",
        "used_fields": used_fields,
        "invalid_fields": sorted(set(invalid_fields)),
        "reason": "sum of non-overlapping reaction aliases",
    }


def _normalize_media_count(candidate: Mapping[str, Any]) -> Tuple[int | None, Dict[str, Any]]:
    explicit, fields, status = _coerce_nonnegative_count_with_status(candidate, ("media_count",))
    if status == "coerced":
        return explicit, {
            "status": "normalized",
            "source": "media_count_field",
            "fields": fields,
            "reason": "explicit media_count provided",
        }
    if status == "invalid":
        return None, {
            "status": "invalid",
            "reason": "media_count fields were present but invalid",
            "fields": fields,
        }

    present_fields = [name for name in _MEDIA_LIST_FIELDS if name in candidate]
    if not present_fields:
        return None, {
            "status": "missing",
            "reason": "media_count and media lists absent",
            "fields": list(_MEDIA_LIST_FIELDS),
        }

    raw_items: List[Any] = []
    for name in present_fields:
        value = candidate.get(name)
        if not isinstance(value, list):
            return None, {
                "status": "invalid",
                "reason": "media lists must be arrays",
                "fields": [name],
            }
        raw_items.extend(value)

    distinct_items = {str(item).strip().lower() for item in raw_items if str(item).strip()}
    return len(distinct_items), {
        "status": "normalized",
        "source": "media_lists",
        "fields": present_fields,
        "item_count": len(raw_items),
        "distinct_items": len(distinct_items),
        "reason": "derived from image/video/media lists",
    }


def normalize_candidate_selection_signals(candidate: Any) -> Dict[str, Any]:
    if not isinstance(candidate, Mapping):
        return {
            "schema_version": CANDIDATE_SELECTION_SIGNAL_NORMALIZER_VERSION,
            "status": "closed",
            "reason_code": "malformed_input",
            "source_count": None,
            "reaction_count": None,
            "media_count": None,
            "signal_provenance": {
                "source_count": {"status": "invalid", "reason": "candidate is not a mapping"},
                "reaction_count": {"status": "invalid", "reason": "candidate is not a mapping"},
                "media_count": {"status": "invalid", "reason": "candidate is not a mapping"},
            },
        }

    source_count, source_provenance = _normalize_source_count(candidate)
    reaction_count, reaction_provenance = _normalize_reaction_count(candidate)
    media_count, media_provenance = _normalize_media_count(candidate)

    normalized = dict(candidate)
    normalized.update({
        "schema_version": CANDIDATE_SELECTION_SIGNAL_NORMALIZER_VERSION,
        "source_count": source_count,
        "reaction_count": reaction_count,
        "media_count": media_count,
        "signal_provenance": {
            "source_count": source_provenance,
            "reaction_count": reaction_provenance,
            "media_count": media_provenance,
        },
    })
    return normalized


__all__ = [
    "normalize_candidate_selection_signals",
    "CANDIDATE_SELECTION_SIGNAL_NORMALIZER_VERSION",
]
