from typing import Any, Dict, Optional

# Verbatim from modules/pattern_engine/{hook_selector,cta_selector,pattern_selector}.py
# Only these values may ever be produced by this classifier.
HOOK_TYPES = ("attention", "saveable_tip", "authority", "contrarian", "pain_point")
CTA_TYPES = ("save", "comment", "dm", "profile", "follow")
PATTERN_TYPES = ("number_list", "warning", "comparison", "tutorial", "story", "resource", "funnel")

CLASSIFIER_VERSION = "instagram_research_classifier_v1"

_HOOK_KEYWORDS = (
    ("pain_point", ("짜증", "답답", "힘드셨", "고민", "안 되죠", "골치", "속상")),
    ("contrarian", ("아니었어요", "아니에요", "사실은", "그게 아니라", "오해", "아닙니다")),
    ("authority", ("년차", "강사", "수석", "전문가", "8년")),
    ("saveable_tip", ("저장", "꿀팁", "정리", "가이드", "방법")),
    ("attention", ("몰랐다면", "실화", "충격", "믿기 힘드", "믿기 어려")),
)

_CTA_KEYWORDS = (
    ("dm", ("dm으로", "dm 보내", "dm으로 보내")),
    ("comment", ("댓글에", "댓글로", "댓글 남겨")),
    ("follow", ("팔로우",)),
    ("profile", ("프로필 링크", "링크에서")),
    ("save", ("저장해",)),
)

_PATTERN_KEYWORDS = (
    ("number_list", ("가지", "단계", "1.", "1️⃣")),
    ("warning", ("주의", "위험", "짜증나",)),
    ("comparison", ("차이", "비교", " vs ")),
    ("funnel", ("dm으로", "댓글 남겨주시면")),
    ("resource", ("무료", "링크", "사이트", "도구")),
    ("tutorial", ("방법", "설정", "가이드", "따라")),
    ("story", ("제가", "저는")),
)


def _classify(caption_text: Optional[str], keyword_table, allowed_values) -> Dict[str, Any]:
    base = {
        "confidence": 0.0,
        "evidence_text": None,
        "classifier_version": CLASSIFIER_VERSION,
        "manually_observed": True,
        "inferred": True,
    }
    if not isinstance(caption_text, str) or not caption_text.strip():
        return {**base, "value": "unknown", "reason": "no_caption_text"}

    lowered = caption_text.lower()
    for value, keywords in keyword_table:
        if value not in allowed_values:
            continue
        for kw in keywords:
            if kw.lower() in lowered:
                return {
                    **base,
                    "value": value,
                    "confidence": 0.55,
                    "evidence_text": kw,
                }
    return {**base, "value": "unknown", "confidence": 0.1, "reason": "no_supported_keyword_match"}


def classify_hook(caption_text: Optional[str]) -> Dict[str, Any]:
    return _classify(caption_text, _HOOK_KEYWORDS, HOOK_TYPES)


def classify_cta(caption_text: Optional[str]) -> Dict[str, Any]:
    return _classify(caption_text, _CTA_KEYWORDS, CTA_TYPES)


def classify_pattern(caption_text: Optional[str]) -> Dict[str, Any]:
    return _classify(caption_text, _PATTERN_KEYWORDS, PATTERN_TYPES)


def classify_post(post: Dict[str, Any]) -> Dict[str, Any]:
    caption_text = post.get("caption_text") if isinstance(post, dict) else None
    return {
        "account_handle": post.get("account_handle") if isinstance(post, dict) else None,
        "post_shortcode": post.get("post_shortcode") if isinstance(post, dict) else None,
        "hook": classify_hook(caption_text),
        "cta": classify_cta(caption_text),
        "pattern": classify_pattern(caption_text),
    }
