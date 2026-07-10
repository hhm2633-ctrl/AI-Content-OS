from typing import Any, Dict, List, Optional


class AIImageDecision:
    """
    Image Strategy v1 - AI 이미지 생성이 실제로 필요한지 판단한다.

    이번 Chapter의 목표는 "AI 이미지를 잘 만드는 것"이 아니라
    "AI 이미지를 가능한 적게 사용하는 것"이다. 현재 프로젝트에는 뉴스/커뮤니티
    /상품/리뷰용 실제 이미지를 실시간으로 수집하는 모듈이 아직 없으므로, 이
    클래스는 "지금 실제 이미지를 가져올 수 있는가"가 아니라 "이 content_type이
    AI 이미지 대신 실제 이미지를 우선해야 하는가"를 전략적으로 판단한다.

    ImageSourceSelector의 priority 체인에 "ai_image"가 없는 content_type
    (news/community/shopping/review/promotion)은 need_ai_image=False로 보고
    AI 이미지 생성을 건너뛴 뒤 실제 이미지 사용 계획만 만든다.
    priority 체인의 마지막이 "ai_image"인 content_type(education/tutorial/
    ai_tools)은 실제 소스(icon/diagram/official_screenshot)를 아직 자동으로
    확보할 수 없으므로 need_ai_image=True로 판단한다.
    """

    AI_FALLBACK_SOURCE = "ai_image"

    def decide(
        self,
        content_type: str,
        image_source_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        try:
            return self._decide(str(content_type or ""), image_source_result or {})
        except Exception as error:
            return {
                "need_ai_image": True,
                "reason": f"AI 이미지 필요 여부 판단 실패로 안전하게 AI 이미지를 사용함: {error}",
                "image_source": self.AI_FALLBACK_SOURCE,
                "priority": [self.AI_FALLBACK_SOURCE],
                "fallback_used": True,
            }

    def _decide(
        self,
        content_type: str,
        image_source_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        priority: List[str] = list(image_source_result.get("priority") or [self.AI_FALLBACK_SOURCE])
        image_source = image_source_result.get("image_source") or (
            priority[0] if priority else self.AI_FALLBACK_SOURCE
        )

        need_ai_image = self.AI_FALLBACK_SOURCE in priority

        if need_ai_image:
            reason = (
                f"content_type '{content_type}'은 실제 이미지 자동 수집 기능이 아직 없어 "
                f"AI 이미지 생성이 필요함 (priority={priority})."
            )
        else:
            reason = (
                f"content_type '{content_type}'은 실제 이미지({image_source})를 우선 사용해야 하므로 "
                f"AI 이미지 생성을 건너뜀 (priority={priority})."
            )

        return {
            "need_ai_image": need_ai_image,
            "reason": reason,
            "image_source": image_source,
            "priority": priority,
            "fallback_used": False,
        }
