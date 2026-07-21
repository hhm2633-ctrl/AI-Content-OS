"""Deterministic candidate-to-product matching for Brand Connect second stage.

Matching is provider-neutral text/category/situation matching over the
normalized catalog. Natural fashion/beauty/lifestyle matches earn a
``commerce_fit`` score; luxury runway/editorial information bypasses Commerce
entirely and is never penalized. No affiliate links are issued and no
commercial facts are created here.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping

MATCH_THRESHOLD = 0.35
MAX_MATCHES = 3

EDITORIAL_PATTERN = re.compile(
    r"런웨이|runway|오트\s?쿠튀르|couture|패션쇼|컬렉션|시즌\s?콘셉트|아카이브|에디토리얼|editorial",
    re.IGNORECASE,
)
LUXURY_PATTERN = re.compile(
    r"디올|프라다|샤넬|구찌|루이비통|에르메스|생로랑|발렌시아가|셀린느|보테가", re.IGNORECASE
)
_LUXURY_CONTEXT_PATTERN = re.compile(r"시즌|쇼|컬렉션|역사|헤리티지|철학", re.IGNORECASE)
_NON_COMMERCE_CAMPAIGN_PATTERN = re.compile(r"의류\s*기부|기부\s*캠페인|사회\s*공헌")

# Owner-approved situational bridges: the content situation connects naturally
# to product keywords even when the exact product differs.
SITUATION_RULES = (
    (
        "rain",
        re.compile(r"비\s*(?:가|는|도|를)?\s*(?:오|내리)|비\s*올|장마|폭우|호우|우천"),
        ("우산", "레인부츠", "방수"),
    ),
    ("heat", re.compile(r"더위|폭염|무더위|불볕"), ("양산", "쿨링", "선풍기", "냉감")),
    ("humidity", re.compile(r"습도|습기|꿉꿉"), ("제습", "쿨링")),
    (
        "hair_humidity",
        re.compile(r"비\s*올|장마|습도|습기|앞머리"),
        ("드라이 샴푸", "드라이샴푸", "앞머리", "픽서", "뿌리볼륨", "헤어스프레이"),
    ),
    ("travel", re.compile(r"여행|휴가|바캉스"), ("모자", "선크림", "캐리어", "선글라스")),
)

FAMILY_SIGNALS = {
    "makeup": ("메이크업", "립스틱", "립틴트", "립밤", "쿠션", "파운데이션", "아이섀도", "마스카라"),
    "hair": ("헤어", "머리", "앞머리", "샴푸", "트리트먼트", "왁스", "헤어에센스"),
    "skincare": ("스킨케어", "선크림", "선스틱", "선케어", "크림", "세럼", "에센스", "로션", "마스크팩"),
    "fragrance": ("향수", "퍼퓸", "미스트"),
    "fashion": ("패션", "의류", "셔츠", "티셔츠", "재킷", "자켓", "원피스", "팬츠", "코트", "니트"),
    "accessory": ("모자", "가방", "신발", "양산", "우산", "주얼리", "선글라스", "벨트", "캐리어"),
    "lifestyle": ("생활", "제습", "쿨링", "선풍기", "텀블러", "방수", "넥쿨러"),
}

GENERIC_MATCH_TOKENS = {
    "1+1", "공식", "스토어", "제품", "상품", "출시", "신제품", "신상", "여름", "겨울",
    "패션", "뷰티", "화장품", "메이크업", "헤어", "생활", "남자", "여자", "남성", "여성",
    "초경량", "가벼운", "쿨링", "런칭", "기념", "아이템", "시장", "개", "외", "리뷰",
}

# One-word matching is allowed only for product-specific terms. Other words
# need at least two overlaps so a large catalog cannot turn incidental words
# such as "space" into a T-shirt recommendation.
DIRECT_MATCH_TERMS = {
    "글루타치온", "나이아신아마이드", "레티놀", "히알루론산",
    "비비크림", "쿠션", "파운데이션", "마스카라", "아이라이너", "아이섀도", "속눈썹",
    "선크림", "선스틱", "미스트", "세럼", "에센스", "로션", "핸드크림", "네일", "제모", "왁싱",
    "향수", "퍼퓸", "오드퍼퓸",
    "샴푸", "트리트먼트", "염색", "염색약", "헤어팩", "브러쉬", "브러시", "고데기",
    "앞머리", "드라이샴푸", "픽서", "헤어롤", "뿌리볼륨", "헤어스프레이",
    "티셔츠", "셔츠", "재킷", "자켓", "원피스", "팬츠", "코트", "니트", "크롭", "레이스", "체크", "스트라이프", "냉감",
    "시계", "선글라스", "가방", "신발", "우산", "양산", "캐리어", "유모차",
}

_TOKEN_PATTERN = re.compile(r"[\W_]+", re.UNICODE)
_HANGUL_TOKEN = re.compile(r"^[가-힣]+$")
_KOREAN_SUFFIXES = (
    "으로", "에서", "에게", "까지", "부터", "처럼", "보다",
    "했습니다", "합니다", "됩니다", "입니다", "하는", "되는", "있는", "없는", "관리법", "방법",
    "과", "와", "을", "를", "은", "는", "이", "가", "에", "의", "로", "도", "만", "법",
)
_CARE_INTENT_PATTERN = re.compile(r"관리법|깨끗하게|세척|손질|복구|보관")
_CARE_PRODUCT_PATTERN = re.compile(
    r"클리너|세정|세척|브러시|신발\s*솔|관리|케어|보관|세제|샴푸|에센스|트리트먼트|복구|"
    r"앞머리|픽서|스프레이|뿌리\s*볼륨|헤어롤"
)
_UNDERWEAR_PATTERN = re.compile(r"브라|팬티|속옷|란제리|언더웨어|런닝")
_SLEEPWEAR_PATTERN = re.compile(r"잠옷|파자마|홈웨어|나이티")
_FRAGRANCE_INTENT_PATTERN = re.compile(r"향수|오드퍼퓸|오드뚜왈렛|오드코롱")
_NON_FRAGRANCE_SCENTED_PRODUCT_PATTERN = re.compile(
    r"바디워시|바디로션|비누|디퓨저|샴푸|세제|탈취제|핸드워시|손세정제|페미닌"
)
_VARIANT_QUANTITY_PATTERN = re.compile(r"(?<![0-9a-z가-힣])\d+(?:\.\d+)?\s*(?:ml|g|kg|개|팩|매|입)(?![0-9a-z가-힣])", re.IGNORECASE)
_TRAILING_SKU_PATTERN = re.compile(r"[_\s-]+[0-9a-z]{6,}$", re.IGNORECASE)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def candidate_text(candidate: Mapping[str, Any]) -> str:
    parts = [
        _text(candidate.get("title")),
        _text(candidate.get("category")) or _text(candidate.get("raw_category")),
        _text(candidate.get("context")) or _text(candidate.get("hook")),
    ]
    keywords = candidate.get("keywords")
    if isinstance(keywords, (list, tuple)):
        parts.extend(_text(item) for item in keywords)
    return " ".join(part for part in parts if part)


def _candidate_content_text(candidate: Mapping[str, Any]) -> str:
    parts = [
        _text(candidate.get("title")),
        _text(candidate.get("context")) or _text(candidate.get("hook")),
    ]
    keywords = candidate.get("keywords")
    if isinstance(keywords, (list, tuple)):
        parts.extend(_text(item) for item in keywords)
    return " ".join(part for part in parts if part)


def _tokens(text: str) -> set:
    result = set()
    for raw_token in _TOKEN_PATTERN.split(text.lower()):
        token = raw_token
        if not token:
            continue
        if _HANGUL_TOKEN.fullmatch(token):
            for suffix in _KOREAN_SUFFIXES:
                if token.endswith(suffix):
                    stem = token[:-len(suffix)]
                    token = stem if len(stem) >= 2 else token
                    break
        if len(token) >= 2:
            result.add(token)
    return result


def _brand_matches(text: str, brand: str) -> bool:
    normalized = brand.strip().lower()
    if not normalized:
        return False
    if normalized.isascii() and len(re.sub(r"[^0-9a-z]", "", normalized)) < 3:
        return False
    return bool(re.search(rf"(?<![0-9a-z가-힣]){re.escape(normalized)}(?![0-9a-z가-힣])", text.lower()))


def select_diverse_product_matches(matches: List[Dict[str, Any]], max_matches: int) -> List[Dict[str, Any]]:
    """Keep one pack/size/color-SKU variant per product concept."""

    selected: List[Dict[str, Any]] = []
    seen = set()
    for match in matches:
        name = _TRAILING_SKU_PATTERN.sub("", _text(match.get("name")).lower())
        name = _VARIANT_QUANTITY_PATTERN.sub("", name)
        name = re.sub(r"\s+", " ", name).strip(" ,+_-")
        key = (_text(match.get("brand")).lower(), name)
        if key in seen:
            continue
        seen.add(key)
        selected.append(match)
        if len(selected) >= max(0, int(max_matches)):
            break
    return selected


def _category_family_hints(candidate: Mapping[str, Any]) -> set:
    category = (_text(candidate.get("category")) or _text(candidate.get("raw_category"))).lower()
    if "향수" in category:
        return {"fragrance"}
    if "헤어" in category:
        return {"hair"}
    if "메이크업" in category or "화장" in category:
        return {"makeup"}
    if "뷰티" in category:
        return {"makeup", "hair", "skincare", "fragrance"}
    if "패션" in category or "스타일" in category or "착장" in category:
        return {"fashion", "accessory"}
    if "생활" in category or "여행" in category:
        return {"lifestyle", "accessory"}
    return set()


def _candidate_family_hints(candidate: Mapping[str, Any]) -> set:
    content_text = _candidate_content_text(candidate).lower()
    hints = {
        family
        for family, signals in FAMILY_SIGNALS.items()
        if any(signal in content_text for signal in signals)
    }
    return hints | _category_family_hints(candidate)


def is_editorial_bypass(candidate: Mapping[str, Any]) -> bool:
    """Runway/editorial authority content stays independent of Commerce."""

    if _text(candidate.get("commerce_policy")).lower() in {"editorial", "editorial_bypass"}:
        return True
    text = candidate_text(candidate)
    if EDITORIAL_PATTERN.search(text):
        return True
    if _NON_COMMERCE_CAMPAIGN_PATTERN.search(text):
        return True
    return bool(LUXURY_PATTERN.search(text) and _LUXURY_CONTEXT_PATTERN.search(text))


def _product_text(product: Mapping[str, Any]) -> str:
    cached = product.get("_match_text")
    if isinstance(cached, str):
        return cached
    return " ".join(
        [
            _text(product.get("name")),
            _text(product.get("brand")),
            _text(product.get("category")),
            _text(product.get("product_family")),
            " ".join(k for k in product.get("keywords", []) if isinstance(k, str)),
        ]
    )


def _score_product(
    text: str,
    tokens: set,
    product: Mapping[str, Any],
    candidate_families: set,
    situation_families: set,
) -> Dict[str, Any]:
    product_text = _product_text(product)
    cached_tokens = product.get("_match_tokens")
    product_tokens = cached_tokens if isinstance(cached_tokens, set) else _tokens(product_text)
    basis: List[str] = []
    score = 0.0

    if _CARE_INTENT_PATTERN.search(text) and not _CARE_PRODUCT_PATTERN.search(product_text):
        return {"score": 0.0, "basis": ["intent_mismatch:care"]}
    if _UNDERWEAR_PATTERN.search(product_text) and not _UNDERWEAR_PATTERN.search(text):
        return {"score": 0.0, "basis": ["intent_mismatch:underwear"]}
    if _SLEEPWEAR_PATTERN.search(product_text) and not _SLEEPWEAR_PATTERN.search(text):
        return {"score": 0.0, "basis": ["intent_mismatch:sleepwear"]}
    if (
        _FRAGRANCE_INTENT_PATTERN.search(text)
        and _NON_FRAGRANCE_SCENTED_PRODUCT_PATTERN.search(product_text)
    ):
        return {"score": 0.0, "basis": ["intent_mismatch:fragrance_product"]}

    brand = _text(product.get("brand"))
    if _brand_matches(text, brand):
        score += 0.4
        basis.append("brand_match")

    meaningful_overlap = (tokens & product_tokens) - GENERIC_MATCH_TOKENS
    direct_overlap = meaningful_overlap & DIRECT_MATCH_TERMS
    qualified_overlap = direct_overlap or (meaningful_overlap if len(meaningful_overlap) >= 2 else set())
    if qualified_overlap:
        score += min(0.45, 0.25 + 0.1 * (len(qualified_overlap) - 1))
        basis.append("meaningful_keyword_overlap")

    family = _text(product.get("product_family"))
    family_compatible = bool(family and family in candidate_families)
    if family_compatible and qualified_overlap:
        score += 0.15
        basis.append("category_family_match")

    for rule_name, pattern, targets in SITUATION_RULES:
        if family in situation_families and pattern.search(text) and any(target in product_text for target in targets):
            score += 0.35
            basis.append(f"situational:{rule_name}")
            break

    return {"score": round(min(score, 1.0), 4), "basis": basis}


def match_candidate_to_products(
    candidate: Mapping[str, Any],
    products: List[Mapping[str, Any]],
    threshold: float = MATCH_THRESHOLD,
    max_matches: int = MAX_MATCHES,
) -> Dict[str, Any]:
    """Deterministically score one graded candidate against normalized products."""

    if is_editorial_bypass(candidate):
        return {
            "match_status": "editorial_bypass",
            "commerce_fit": None,
            "penalized": False,
            "matches": [],
        }

    text = candidate_text(candidate)
    tokens = _tokens(_candidate_content_text(candidate))
    category_families = _category_family_hints(candidate)
    candidate_families = _candidate_family_hints(candidate)
    situation_families = category_families or candidate_families
    scored = []
    for product in products if isinstance(products, list) else []:
        if not isinstance(product, Mapping):
            continue
        outcome = _score_product(text, tokens, product, candidate_families, situation_families)
        if outcome["score"] >= threshold:
            scored.append(
                {
                    "product_id": _text(product.get("product_id")),
                    "name": _text(product.get("name")),
                    "brand": _text(product.get("brand")),
                    "product_family": _text(product.get("product_family")),
                    "url": _text(product.get("url")),
                    "score": outcome["score"],
                    "match_basis": outcome["basis"],
                    "link_issued": False,
                }
            )
    scored.sort(key=lambda item: (-item["score"], item["product_id"]))
    matches = select_diverse_product_matches(scored, max_matches)

    if matches:
        return {
            "match_status": "matched",
            "commerce_fit": matches[0]["score"],
            "penalized": False,
            "matches": matches,
        }
    return {
        "match_status": "unmatched",
        "commerce_fit": None,
        "penalized": False,
        "matches": [],
    }


def prepare_products_for_matching(products: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    """Cache catalog text/token work once per second-stage run."""

    prepared = []
    for product in products if isinstance(products, list) else []:
        if not isinstance(product, Mapping):
            continue
        item = dict(product)
        match_text = _product_text(item)
        item["_match_text"] = match_text
        item["_match_tokens"] = _tokens(match_text)
        prepared.append(item)
    return prepared


__all__ = [
    "match_candidate_to_products",
    "is_editorial_bypass",
    "candidate_text",
    "MATCH_THRESHOLD",
    "MAX_MATCHES",
    "SITUATION_RULES",
    "prepare_products_for_matching",
    "select_diverse_product_matches",
]
