from typing import Any, Dict, Optional


class CTAStrategy:
    """
    CTA Library(benchmark/CTA_LIBRARY.md) 기반으로 pattern_type/topic_intelligence에
    가장 적합한 cta_type을 선택한다. Pattern Engine의 cta_type(5종: save, comment,
    dm, profile, follow)보다 넓은 7종 팔레트를 사용해 Content Engine 단계에서 한 번
    더 다듬는다. link_click은 CTA_LIBRARY.md 기준 Reels/Shorts 전용 CTA라 카드뉴스
    pattern_type 매핑에는 사용하지 않고 향후 영상 워크플로를 위해 남겨둔다.
    실패해도 예외를 던지지 않고 안전한 기본값을 반환한다.
    """

    CTA_TYPES = [
        "save",
        "comment",
        "follow",
        "profile",
        "dm",
        "share",
        "link_click",
    ]

    PATTERN_CTA_MAP = {
        "warning": "save",
        "tutorial": "follow",
        "comparison": "comment",
        "story": "dm",
        "number_list": "share",
        "resource": "profile",
    }

    DEFAULT_CTA_TYPE = "save"

    def __init__(self, config=None):
        self.config = config or {}

    def select(
        self,
        pattern_plan: Optional[Dict[str, Any]],
        topic_intelligence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            return self._select(pattern_plan or {}, topic_intelligence or {})
        except Exception:
            return {
                "cta_type": self.DEFAULT_CTA_TYPE,
                "reason": "CTA 선택 계산 실패로 기본 CTA로 대체함.",
            }

    def _select(
        self,
        pattern_plan: Dict[str, Any],
        topic_intelligence: Dict[str, Any],
    ) -> Dict[str, Any]:
        pattern_type = str(pattern_plan.get("pattern_type", ""))
        upstream_cta = str(pattern_plan.get("cta_type", ""))

        if pattern_type in self.PATTERN_CTA_MAP:
            cta_type = self.PATTERN_CTA_MAP[pattern_type]
            reason = (
                f"pattern_type '{pattern_type}' 콘텐츠 목적에 맞춰 Content Engine이 "
                f"'{cta_type}' CTA로 세분화함."
            )
        elif upstream_cta in self.CTA_TYPES:
            cta_type = upstream_cta
            reason = f"Content Engine 매핑에 없어 Pattern Engine의 '{cta_type}' CTA를 사용함."
        else:
            cta_type = self.DEFAULT_CTA_TYPE
            reason = "pattern_type/cta_type 정보가 부족해 기본 CTA로 대체함."

        return {"cta_type": cta_type, "reason": reason}
