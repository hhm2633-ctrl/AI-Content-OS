from typing import Any, Dict, List, Optional


class VisualRhythmSelector:
    """
    CardNews Intelligence (Phase M8: Production Quality) - Human Visual Rhythm.

    모든 슬라이드를 동일한 템플릿 복사본처럼 만들지 않기 위해, 이미
    StoryFlowPlanner가 계산한 narrative_role(cover/problem/evidence/
    explanation/social_proof/counterpoint/conclusion/debate_cta)에 따라
    시각 스타일 태그를 결정론적으로 배정한다. 무작위가 아니라 story role
    기준이며, 같은 입력에는 항상 같은 결과가 나온다.

    이 결과는 참고용 메타데이터(visual_rhythm_result)로만 쓰인다 - 실제
    Pillow 렌더링 코드(_draw_layout_card 등)는 이번 단계에서 바꾸지 않는다.
    """

    NARRATIVE_TO_STYLE: Dict[str, str] = {
        "cover": "title_focus",
        "problem": "short_line_focus",
        "evidence": "image_focus",
        "explanation": "short_line_focus",
        "social_proof": "quote_card",
        "counterpoint": "comparison",
        "conclusion": "whitespace_focus",
        "debate_cta": "cta_focus",
    }
    DEFAULT_STYLE = "short_line_focus"
    SUPPORTED_STYLES = (
        "image_focus", "title_focus", "short_line_focus", "quote_card",
        "comparison", "whitespace_focus", "cta_focus",
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def select(self, applied_roles: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        try:
            return self._select(applied_roles or [])
        except Exception as error:
            return {
                "assignments": [],
                "distinct_style_count": 0,
                "varied": False,
                "reason": f"visual rhythm 선택 실패: {error}",
            }

    def _select(self, applied_roles: List[Dict[str, Any]]) -> Dict[str, Any]:
        assignments = []

        for item in applied_roles:
            if not isinstance(item, dict):
                continue

            narrative_role = item.get("narrative_role")
            style = self.NARRATIVE_TO_STYLE.get(narrative_role, self.DEFAULT_STYLE)

            assignments.append({
                "page": item.get("page"),
                "role": item.get("role"),
                "narrative_role": narrative_role,
                "visual_style": style,
            })

        distinct_styles = {item["visual_style"] for item in assignments}
        varied = len(distinct_styles) >= 2 if len(assignments) >= 2 else bool(assignments)

        return {
            "assignments": assignments,
            "distinct_style_count": len(distinct_styles),
            "varied": varied,
            "reason": (
                f"{len(distinct_styles)}개의 서로 다른 시각 스타일이 서사 role 기준으로 결정론적으로 배정됨."
                if varied
                else "슬라이드가 없거나 스타일이 다양화되지 않음."
            ),
        }
