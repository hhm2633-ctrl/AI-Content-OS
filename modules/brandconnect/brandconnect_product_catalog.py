"""Deterministic normalization of a caller-supplied Brand Connect catalog snapshot.

The catalog always arrives from an authorized UI snapshot supplied by the
caller. This module never logs in, scrapes, or fetches anything, and it never
invents price, stock, or review facts — only supplied fields survive
normalization. A missing or malformed catalog stays explicitly incomplete.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Mapping

CATALOG_SCHEMA_VERSION = "brandconnect_catalog.v1"
DEFAULT_CATALOG_SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "owner_review"
    / "brandconnect_catalog_snapshot.json"
)
CATALOG_REUSE_POLICY = "cached_snapshot_first_explicit_refresh_only"

FAMILY_KEYWORDS = {
    "makeup": ("메이크업", "립스틱", "립틴트", "립밤", "쿠션", "파운데이션", "아이섀도", "마스카라"),
    "hair": ("헤어", "샴푸", "트리트먼트", "왁스", "헤어에센스"),
    "skincare": ("스킨", "크림", "세럼", "에센스", "선크림", "선스틱", "선케어", "로션", "마스크팩"),
    "fragrance": ("향수", "퍼퓸", "미스트"),
    "fashion": ("셔츠", "자켓", "재킷", "원피스", "드레스", "팬츠", "코트", "니트", "티셔츠"),
    "accessory": ("모자", "가방", "신발", "양산", "우산", "주얼리", "선글라스", "벨트"),
    "lifestyle": ("제습", "쿨링", "선풍기", "캐리어", "텀블러", "방수"),
}
_CATEGORY_FAMILY_RULES = (
    (re.compile(r"패션잡화|신발|주얼리"), "accessory"),
    (re.compile(r"여성패션|남성패션|패션의류|의류"), "fashion"),
    (re.compile(r"생활/건강|생활·건강|가구/인테리어"), "lifestyle"),
    (re.compile(r"여가/여행|스포츠/레저|취미/펫"), "lifestyle"),
)
_MALE_PATTERN = re.compile(r"남성|남자|맨즈|men", re.IGNORECASE)
_FEMALE_PATTERN = re.compile(r"여성|여자|우먼|women", re.IGNORECASE)

# Commercial fact fields that are copied only when the snapshot supplies them.
SUPPLIED_FACT_FIELDS = ("price", "stock_status", "review_count", "rating")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _text_list(value: Any) -> List[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_text(item) for item in value if _text(item)]


def derive_product_family(text: str, category: str = "") -> str:
    for pattern, family in _CATEGORY_FAMILY_RULES:
        if pattern.search(category.lower()):
            return family
    lowered = text.lower()
    if "풋샴푸" in lowered or "발을씻자" in lowered:
        return "skincare"
    for family, keywords in FAMILY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return family
    return ""


def derive_audience(text: str) -> str:
    male = bool(_MALE_PATTERN.search(text))
    female = bool(_FEMALE_PATTERN.search(text))
    if male and not female:
        return "male"
    if female and not male:
        return "female"
    return "unisex"


def _normalize_product(raw: Mapping[str, Any]) -> Dict[str, Any]:
    name = _text(raw.get("name"))
    brand = _text(raw.get("brand"))
    category = _text(raw.get("category")).lower()
    describing = " ".join([name, brand, category, " ".join(_text_list(raw.get("keywords")))])
    product = {
        "product_id": _text(raw.get("product_id")) or _text(raw.get("smartstore_product_id")),
        "name": name,
        "brand": brand,
        "category": category,
        "product_family": _text(raw.get("product_family")).lower() or derive_product_family(describing, category),
        "audience": _text(raw.get("audience")).lower() or derive_audience(describing),
        "keywords": _text_list(raw.get("keywords")),
        "url": _text(raw.get("url")) or _text(raw.get("source_ref")),
        "supplied_facts_only": True,
    }
    for field in SUPPLIED_FACT_FIELDS:
        if field in raw:
            product[field] = deepcopy(raw[field])
    return product


def normalize_brandconnect_catalog(snapshot: Any) -> Dict[str, Any]:
    """Normalize and dedupe a UI-snapshot catalog; never fill missing facts."""

    result = {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "status": "ready",
        "complete": True,
        "source": "",
        "captured_at": None,
        "products": [],
        "product_count": 0,
        "dropped": [],
    }

    if snapshot is None:
        result.update(status="catalog_missing", complete=False)
        return result

    if isinstance(snapshot, Mapping):
        result["source"] = _text(snapshot.get("source")) or "caller_supplied_snapshot"
        result["captured_at"] = snapshot.get("captured_at")
        raw_products = snapshot.get("products")
    elif isinstance(snapshot, list):
        result["source"] = "caller_supplied_snapshot"
        raw_products = snapshot
    else:
        result.update(status="malformed_catalog", complete=False)
        return result

    if not isinstance(raw_products, list) or not raw_products:
        result.update(status="catalog_missing", complete=False)
        return result

    seen_ids = set()
    seen_identity = set()
    for index, raw in enumerate(raw_products):
        if not isinstance(raw, Mapping):
            result["dropped"].append({"index": index, "reason": "malformed_product"})
            continue
        product = _normalize_product(raw)
        if not product["product_id"] or not product["name"]:
            result["dropped"].append({"index": index, "reason": "missing_id_or_name"})
            continue
        identity = (product["brand"].lower(), re.sub(r"\s+", " ", product["name"].lower()))
        if product["product_id"] in seen_ids or identity in seen_identity:
            result["dropped"].append(
                {"index": index, "product_id": product["product_id"], "reason": "duplicate_product"}
            )
            continue
        seen_ids.add(product["product_id"])
        seen_identity.add(identity)
        result["products"].append(product)

    result["product_count"] = len(result["products"])
    if not result["products"]:
        result.update(status="catalog_missing", complete=False)
    return result


def load_cached_brandconnect_catalog(snapshot_path: Any = None) -> Dict[str, Any]:
    """Load the saved owner-authorized snapshot without any network fallback.

    A missing or malformed cache remains explicitly incomplete.  The function
    never attempts a live refresh: replacing the snapshot is a separate,
    explicit owner action performed by the save script's ``--refresh`` mode.
    """

    path = Path(snapshot_path) if snapshot_path is not None else DEFAULT_CATALOG_SNAPSHOT_PATH
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        result = normalize_brandconnect_catalog(None)
        cache_hit = False
    except (OSError, UnicodeError, json.JSONDecodeError):
        result = normalize_brandconnect_catalog("malformed_cache")
        cache_hit = False
    else:
        result = normalize_brandconnect_catalog(raw)
        cache_hit = bool(result["complete"])

    result.update(
        cache_hit=cache_hit,
        catalog_reuse_policy=CATALOG_REUSE_POLICY,
        refresh_requested=False,
        network_used=False,
    )
    return result


__all__ = [
    "normalize_brandconnect_catalog",
    "derive_product_family",
    "derive_audience",
    "CATALOG_SCHEMA_VERSION",
    "FAMILY_KEYWORDS",
    "SUPPLIED_FACT_FIELDS",
    "DEFAULT_CATALOG_SNAPSHOT_PATH",
    "CATALOG_REUSE_POLICY",
    "load_cached_brandconnect_catalog",
]
