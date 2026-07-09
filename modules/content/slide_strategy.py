from typing import Any, Dict, List


class SlideStrategy:
    """
    pattern_type별 카드뉴스 슬라이드 구조(blueprint)를 생성한다.

    CardNewsModule과 ImagePromptModule은 이번 Sprint에서 수정하지 않으며,
    여전히 정확히 4장(hook/problem/solution/cta) 구조를 전제로 동작한다.
    따라서 이 클래스는 pattern_type마다 이상적인 개념적 단계(blueprint, 패턴에
    따라 4~5단계)를 정의한 뒤, 그 개념들을 기존 4-슬라이드 role
    (hook/problem/solution/cta)에 맞춰 압축한 slides 목록을 함께 반환한다.
    blueprint는 Content Prompt Builder가 더 구체적인 지시문을 만드는 데 사용된다.
    """

    BLUEPRINTS: Dict[str, List[Dict[str, str]]] = {
        "warning": [
            {"step": "hook", "role": "hook", "purpose": "경고형 후킹으로 시선을 끈다."},
            {"step": "problem", "role": "problem", "purpose": "흔한 실수와 문제 상황을 보여준다."},
            {"step": "reason", "role": "problem", "purpose": "그 실수가 왜 위험한지 이유를 설명한다."},
            {"step": "solution", "role": "solution", "purpose": "위험을 피하는 해결 방법을 제시한다."},
            {"step": "cta", "role": "cta", "purpose": "저장을 유도하는 CTA로 마무리한다."},
        ],
        "tutorial": [
            {"step": "hook", "role": "hook", "purpose": "how-to 후킹으로 시선을 끈다."},
            {"step": "prep", "role": "problem", "purpose": "시작하기 전 준비물이나 전제 조건을 안내한다."},
            {"step": "step1", "role": "solution", "purpose": "핵심 실행 1단계를 설명한다."},
            {"step": "step2", "role": "solution", "purpose": "핵심 실행 2단계를 이어서 설명한다."},
            {"step": "cta", "role": "cta", "purpose": "팔로우 또는 저장 CTA로 마무리한다."},
        ],
        "comparison": [
            {"step": "hook", "role": "hook", "purpose": "비교형 후킹으로 시선을 끈다."},
            {"step": "criteria", "role": "problem", "purpose": "비교 기준을 설명한다."},
            {"step": "option_a_vs_b", "role": "solution", "purpose": "두 옵션의 장단점을 비교한다."},
            {"step": "recommendation", "role": "solution", "purpose": "상황별 추천을 제시한다."},
            {"step": "cta", "role": "cta", "purpose": "댓글로 의견을 묻는 CTA로 마무리한다."},
        ],
        "story": [
            {"step": "hook", "role": "hook", "purpose": "개인 경험 기반 스토리 후킹으로 시선을 끈다."},
            {"step": "problem", "role": "problem", "purpose": "문제 상황과 고민을 보여준다."},
            {"step": "turning_point", "role": "solution", "purpose": "전환점을 설명한다."},
            {"step": "lesson", "role": "solution", "purpose": "전환점에서 얻은 교훈을 전달한다."},
            {"step": "cta", "role": "cta", "purpose": "공감 댓글을 유도하는 CTA로 마무리한다."},
        ],
        "number_list": [
            {"step": "hook", "role": "hook", "purpose": "숫자형 후킹으로 기대감을 준다."},
            {"step": "why_important", "role": "problem", "purpose": "왜 중요한지 짧게 설명한다."},
            {"step": "items", "role": "solution", "purpose": "핵심 항목들을 간결하게 나열한다."},
            {"step": "cta", "role": "cta", "purpose": "저장을 유도하는 CTA로 마무리한다."},
        ],
        "resource": [
            {"step": "hook", "role": "hook", "purpose": "저장 유도형 후킹으로 시선을 끈다."},
            {"step": "criteria", "role": "problem", "purpose": "리소스 선정 기준을 설명한다."},
            {"step": "resources", "role": "solution", "purpose": "실제 추천 리소스를 나열한다."},
            {"step": "cta", "role": "cta", "purpose": "댓글 키워드를 유도하는 CTA로 마무리한다."},
        ],
    }

    DEFAULT_PATTERN_TYPE = "resource"
    CANONICAL_ROLES = ["hook", "problem", "solution", "cta"]

    def __init__(self, config=None):
        self.config = config or {}

    def build(self, pattern_type: str) -> Dict[str, Any]:
        try:
            return self._build(str(pattern_type or ""))
        except Exception:
            return self._build(self.DEFAULT_PATTERN_TYPE)

    def _build(self, pattern_type: str) -> Dict[str, Any]:
        blueprint = self.BLUEPRINTS.get(pattern_type)

        if not blueprint:
            pattern_type = self.DEFAULT_PATTERN_TYPE
            blueprint = self.BLUEPRINTS[self.DEFAULT_PATTERN_TYPE]

        slides = self._compact_to_slides(blueprint)

        return {
            "pattern_type": pattern_type,
            "blueprint": blueprint,
            "slides": slides,
        }

    def _compact_to_slides(self, blueprint: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[str]] = {}

        for step in blueprint:
            role = step.get("role", "solution")
            grouped.setdefault(role, []).append(str(step.get("purpose", "")).strip())

        slides = []

        for index, role in enumerate(self.CANONICAL_ROLES, start=1):
            purposes = grouped.get(role, [])
            purpose_text = " ".join(purpose for purpose in purposes if purpose)

            slides.append(
                {
                    "page": index,
                    "role": role,
                    "purpose": purpose_text or f"{role} 슬라이드를 구성한다.",
                }
            )

        return slides
