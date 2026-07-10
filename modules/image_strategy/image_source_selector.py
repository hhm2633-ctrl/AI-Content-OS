from typing import Any, Dict, List


class ImageSourceSelector:
    """
    Image Strategy v1 - content_type별 이미지 소스 우선순위를 결정한다.

    news -> 뉴스 이미지
    community -> 게시글 캡처 -> 댓글 캡처
    shopping -> 실제 상품 이미지
    review -> 실제 사진
    promotion -> 실제 상품/서비스 이미지 -> 실제 사진 (shopping/review에 준해 확장)
    education/tutorial -> 아이콘 -> 도표 -> AI
    ai_tools -> 공식 스크린샷 -> AI

    알 수 없는 content_type은 education과 동일한 기본 체인으로 처리한다.
    """

    SOURCE_PRIORITY: Dict[str, List[str]] = {
        "news": ["news_image"],
        "community": ["post_capture", "comment_capture"],
        "shopping": ["product_image"],
        "review": ["real_photo"],
        "promotion": ["product_image", "real_photo"],
        "education": ["icon", "diagram", "ai_image"],
        "tutorial": ["icon", "diagram", "ai_image"],
        "ai_tools": ["official_screenshot", "ai_image"],
    }

    DEFAULT_PRIORITY = ["icon", "diagram", "ai_image"]

    def select(self, content_type: str) -> Dict[str, Any]:
        try:
            return self._select(str(content_type or ""))
        except Exception as error:
            return {
                "image_source": "ai_image",
                "priority": list(self.DEFAULT_PRIORITY),
                "reason": f"이미지 소스 우선순위 계산 실패로 기본 체인을 사용함: {error}",
                "fallback_used": True,
            }

    def _select(self, content_type: str) -> Dict[str, Any]:
        known = content_type in self.SOURCE_PRIORITY
        priority = list(self.SOURCE_PRIORITY.get(content_type, self.DEFAULT_PRIORITY))

        return {
            "image_source": priority[0] if priority else "ai_image",
            "priority": priority,
            "reason": (
                f"content_type '{content_type}'의 우선순위 이미지 소스 체인을 적용함: {priority}"
                if known
                else f"content_type '{content_type}'을 알 수 없어 기본 체인을 적용함: {priority}"
            ),
            "fallback_used": not known,
        }
