from typing import Any, Dict

# CardNews Intelligence (Phase M8: Production Quality) - Typography 계층.
#
# 슬라이드 역할별 글자 계층을 명확히 데이터로 관리한다. 실제 Pillow 렌더링
# 코드(card_news_module.py의 폰트 크기 상수: headline=60, body=39, small=28,
# brand=26)는 이번 단계에서 바꾸지 않는다 - 이 규칙은 "검증 기준"으로
# 쓰인다(CardNewsQualityChecker/MobileReadabilityChecker가 실제 텍스트
# 길이와 비교), 그리고 텍스트 준비 단계(CardNewsTextOptimizer의 문장 수
# 제한)의 기준으로도 재사용된다.
TYPOGRAPHY_ROLES: Dict[str, Dict[str, Any]] = {
    "cover_title": {
        "max_chars": 24,
        "max_lines": 2,
        "font_size_range": (52, 64),
        "line_spacing": 1.2,
        "paragraph_spacing": 0,
        "alignment": "left",
        "max_emphasis": 1,
    },
    "slide_title": {
        "max_chars": 18,
        "max_lines": 2,
        "font_size_range": (48, 60),
        "line_spacing": 1.2,
        "paragraph_spacing": 0,
        "alignment": "left",
        "max_emphasis": 1,
    },
    "body": {
        "max_chars": 96,
        "max_lines": 4,
        "font_size_range": (32, 39),
        "line_spacing": 1.35,
        "paragraph_spacing": 8,
        "alignment": "left",
        "max_emphasis": 1,
    },
    "quote": {
        "max_chars": 60,
        "max_lines": 3,
        "font_size_range": (30, 36),
        "line_spacing": 1.3,
        "paragraph_spacing": 8,
        "alignment": "left",
        "max_emphasis": 0,
    },
    "source": {
        "max_chars": 40,
        "max_lines": 1,
        # Phase M8 실제 렌더링 반영: 최소값이 MIN_SAFE_FONT_SIZE(24) 미만이면
        # 모바일 축소 상태에서 판독 불가능해진다 - 22는 그 기준보다 작았던
        # 실수라 24로 올림.
        "font_size_range": (24, 26),
        "line_spacing": 1.1,
        "paragraph_spacing": 0,
        "alignment": "left",
        "max_emphasis": 0,
    },
    "cta": {
        "max_chars": 48,
        "max_lines": 2,
        "font_size_range": (32, 39),
        "line_spacing": 1.3,
        "paragraph_spacing": 6,
        "alignment": "left",
        "max_emphasis": 1,
    },
    "page_number": {
        "max_chars": 6,
        "max_lines": 1,
        "font_size_range": (24, 30),
        "line_spacing": 1.0,
        "paragraph_spacing": 0,
        "alignment": "left",
        "max_emphasis": 0,
    },
}

# 모바일 축소 상태에서 판독 가능하다고 보는 최소 폰트 크기 기준.
MIN_SAFE_FONT_SIZE = 24


def resolve_typography_role(canonical_role: str, narrative_role: str, is_headline: bool) -> str:
    """
    슬라이드의 canonical role(hook/problem/solution/cta)과 StoryFlowPlanner가
    부여한 narrative_role(cover/evidence/social_proof/debate_cta 등)을 보고
    이 텍스트가 TYPOGRAPHY_ROLES의 어떤 계층에 해당하는지 결정한다. 실제
    슬라이드 구조를 바꾸지 않는 순수 분류 함수다.
    """
    if canonical_role == "hook":
        return "cover_title" if is_headline else "body"

    if is_headline:
        return "slide_title"

    if narrative_role == "social_proof":
        return "quote"

    if narrative_role == "debate_cta" or canonical_role == "cta":
        return "cta"

    return "body"


def check_text_against_role(text: str, typography_role: str) -> Dict[str, Any]:
    """
    실제 텍스트 길이/줄 수를 TYPOGRAPHY_ROLES 기준과 비교한다. 새 렌더링을
    하지 않고, 이미 만들어진 텍스트에 대한 순수 검증만 수행한다.
    """
    rule = TYPOGRAPHY_ROLES.get(typography_role, TYPOGRAPHY_ROLES["body"])
    text = str(text or "")

    length_ok = len(text) <= rule["max_chars"]
    line_count = text.count("\n") + 1 if text else 0
    lines_ok = line_count <= rule["max_lines"]

    return {
        "typography_role": typography_role,
        "length": len(text),
        "max_chars": rule["max_chars"],
        "length_ok": length_ok,
        "line_count": line_count,
        "max_lines": rule["max_lines"],
        "lines_ok": lines_ok,
        "ok": bool(length_ok and lines_ok),
    }
