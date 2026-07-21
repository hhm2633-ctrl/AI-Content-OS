"""Build deterministic commerce relations from the cached product catalog.

This is the missing execution bridge between product-function education and
the relation-aware matcher.  It derives only observable product roles from
the supplied product name/category/keywords.  It never invents use experience,
efficacy, price, stock, reviews, affiliate links, or live platform data.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence


SCHEMA_VERSION = "catalog_function_relations.v1"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _product_text(product: Mapping[str, Any]) -> str:
    keywords = product.get("keywords")
    return " ".join(
        part
        for part in (
            _text(product.get("name")),
            _text(product.get("brand")),
            _text(product.get("category")),
            _text(product.get("product_family")),
            " ".join(_text(value) for value in keywords if _text(value))
            if isinstance(keywords, (list, tuple)) else "",
        )
        if part
    ).lower()


PROFILES: Sequence[Dict[str, Any]] = (
    {
        "id": "hair_humidity_hold",
        "family": "hair",
        "pattern": re.compile(r"드라이\s*샴푸|앞머리|뿌리\s*볼륨|볼륨\s*픽서|헤어\s*픽서|헤어\s*스프레이|헤어롤|구르프|그루프"),
        "derived_terms": ["앞머리", "습기", "볼륨", "고정", "복구"],
        "season_context": {"season": "여름·장마철", "weather": "비·높은 습도", "daily_environment": "출근 전과 외출 중"},
        "practical_topic": "습한 날 앞머리 볼륨을 다시 정돈하는 순서",
        "short_story": "습기에 죽은 앞머리, 다시 살리기",
        "product_role": "수분감 정리·뿌리 볼륨·고정 단계의 상품 후보",
    },
    {
        "id": "hair_shampoo_cleanse",
        "family": "hair",
        "pattern": re.compile(r"샴푸"),
        "derived_terms": ["샴푸", "두피", "세정", "모발"],
        "season_context": {"season": "사계절", "weather": "땀·피지 또는 건조", "daily_environment": "매일 머리 감는 시간"},
        "practical_topic": "가격보다 두피와 모발 상태로 샴푸를 고르는 기준",
        "short_story": "마트 샴푸도 기준이 먼저",
        "product_role": "두피·모발 상태별 세정 단계의 상품 후보",
    },
    {
        "id": "hair_damage_condition",
        "family": "hair",
        "pattern": re.compile(r"트리트먼트|컨디셔너|린스|헤어\s*팩|헤어팩|헤어\s*에센스|헤어\s*오일"),
        "derived_terms": ["손상모", "모발", "윤기", "엉킴", "보습"],
        "season_context": {"season": "사계절", "weather": "건조·자외선", "daily_environment": "샴푸 후와 드라이 전"},
        "practical_topic": "샴푸 뒤 모발 상태에 맞춰 보완 단계를 고르는 기준",
        "short_story": "세정 뒤엔 모발 상태를 본다",
        "product_role": "엉킴·건조·손상모 보완 단계의 상품 후보",
    },
    {
        "id": "fashion_heat_cooling",
        "family": "fashion",
        "pattern": re.compile(r"냉감|아이스|쿨링|드라이|기능성.*(?:티|셔츠)|(?:티|셔츠).*기능성"),
        "exclude": re.compile(r"브라|팬티|속옷|란제리|언더웨어|잠옷|파자마|홈웨어"),
        "derived_terms": ["폭염", "더위", "냉감", "출근", "운동"],
        "season_context": {"season": "여름", "weather": "폭염·땀", "daily_environment": "출근길·일상·운동"},
        "practical_topic": "하루 동선에 맞춰 냉감 상의를 나눠 고르는 방법",
        "short_story": "출근부터 운동까지 냉감 상의",
        "product_role": "출근·일상·운동 상황별 냉감 상의 후보",
    },
    {
        "id": "fashion_crop_layer",
        "family": "fashion",
        "pattern": re.compile(r"크롭|크롭트|숏\s*재킷|숏\s*자켓|윈드\s*브레이커|바람막이"),
        "exclude": re.compile(r"브라|팬티|속옷|란제리|언더웨어|잠옷|파자마|홈웨어"),
        "derived_terms": ["크롭", "재킷", "실루엣", "레이어드", "출국룩"],
        "season_context": {"season": "봄·여름·가을", "weather": "일교차·실내 냉방", "daily_environment": "출근·공항·주말 외출"},
        "practical_topic": "짧은 상의 비율을 일상 옷차림으로 옮기는 방법",
        "short_story": "공항룩 비율만 일상에 옮기기",
        "product_role": "실제 착장 제품이 아닌 비슷한 실루엣의 선택 후보",
    },
)


def build_catalog_function_relations(products: Any) -> Dict[str, Any]:
    """Return matcher relations and story rows for normalized catalog products."""

    relations: Dict[str, Dict[str, Any]] = {}
    story_rows: List[Dict[str, Any]] = []
    profile_counts: Counter[str] = Counter()
    for product in products if isinstance(products, list) else []:
        if not isinstance(product, Mapping):
            continue
        product_id = _text(str(product.get("product_id", "")))
        product_name = _text(product.get("name"))
        if not product_id or not product_name:
            continue
        text = _product_text(product)
        family = _text(product.get("product_family")).lower()
        matched_profiles = [
            profile for profile in PROFILES
            if (not profile["family"] or family == profile["family"])
            and profile["pattern"].search(text)
            and not (profile.get("exclude") and profile["exclude"].search(text))
        ]
        if not matched_profiles:
            continue
        primary = matched_profiles[0]
        derived_terms: List[str] = []
        for profile in matched_profiles:
            profile_counts[profile["id"]] += 1
            for term in profile["derived_terms"]:
                if term not in derived_terms:
                    derived_terms.append(term)
        row = {
            "product_id": product_id,
            "product_name": product_name,
            "profile_ids": [profile["id"] for profile in matched_profiles],
            "derived_terms": derived_terms,
            "season_context": dict(primary["season_context"]),
            "practical_topic": primary["practical_topic"],
            "short_story": primary["short_story"][:29],
            "product_role": primary["product_role"],
            "blog_seed": {
                "status": "idea_only_not_publish_draft",
                "topic": primary["practical_topic"],
            },
            "confidence": 0.75,
            "fallback_used": False,
            "relation_source": "cached_catalog_observable_product_function",
        }
        relations[product_id] = row
        story_rows.append(row)

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ready" if relations else "no_relations",
        "relation_count": len(relations),
        "profile_counts": dict(sorted(profile_counts.items())),
        "relations": relations,
        "story_rows": story_rows,
        "source_contract": "cached_catalog_observable_fields_only",
        "network_used": False,
        "link_issuance": False,
        "publishing": False,
    }


__all__ = ["build_catalog_function_relations", "SCHEMA_VERSION", "PROFILES"]
