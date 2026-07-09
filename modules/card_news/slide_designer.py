from typing import Any, Dict, List, Optional


class SlideDesigner:
    """
    슬라이드 role(hook/problem/solution/cta)과 layout_rule을 기준으로
    슬라이드별 Title 위치, Body 위치, Image 비율, 강조 박스, CTA 영역을 결정한다.

    이 결과는 참고용 메타데이터(layout_result.slide_designs)로만 사용되며,
    CardNewsModule의 실제 Pillow 렌더링 로직은 이번 Sprint에서 변경하지 않는다.
    계산에 실패해도 예외를 던지지 않고 빈 리스트를 반환한다.
    """

    ROLE_POSITIONS = {
        "hook": {"title_position": "center", "body_position": "below_title"},
        "problem": {"title_position": "top", "body_position": "middle"},
        "solution": {"title_position": "top", "body_position": "middle"},
        "cta": {"title_position": "top", "body_position": "bottom"},
    }

    DEFAULT_POSITION = {"title_position": "top", "body_position": "middle"}
    HIGHLIGHT_BOX_ROLES = {"problem", "solution"}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def design(
        self,
        slides: Optional[List[Dict[str, Any]]],
        layout_rule: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        try:
            return self._design(slides or [], layout_rule or {})
        except Exception:
            return []

    def _design(
        self,
        slides: List[Dict[str, Any]],
        layout_rule: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        image_ratio = layout_rule.get("image_ratio", "1:1")
        cta_position = layout_rule.get("cta_position", "bottom_center")
        designs = []

        for slide in slides:
            if not isinstance(slide, dict):
                continue

            role = str(slide.get("role", "solution"))
            position = self.ROLE_POSITIONS.get(role, self.DEFAULT_POSITION)

            designs.append(
                {
                    "page": slide.get("page"),
                    "role": role,
                    "title_position": position["title_position"],
                    "body_position": position["body_position"],
                    "image_ratio": image_ratio,
                    "highlight_box": role in self.HIGHLIGHT_BOX_ROLES,
                    "cta_area": role == "cta",
                    "cta_position": cta_position if role == "cta" else None,
                }
            )

        return designs
