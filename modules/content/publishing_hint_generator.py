from typing import Any, Dict, List, Optional


class PublishingHintGenerator:
    """
    콘텐츠 목적(pattern_plan/cta_type)에 따라 발행 전 확인할 힌트를 생성한다.

    save/comment/follow/profile/dm 중 추천 행동, caption 방향, hashtag 방향,
    업로드 전 사람이 확인할 체크포인트를 제공한다. 계산에 실패해도 예외를 던지지
    않고 안전한 기본 힌트를 반환한다.
    """

    RECOMMENDED_ACTIONS = ["save", "comment", "follow", "profile", "dm"]
    DEFAULT_ACTION = "save"

    CAPTION_DIRECTIONS = {
        "save": "저장 필요성을 강조하는 문장을 캡션 앞부분에 배치하세요.",
        "comment": "질문을 던지거나 의견을 묻는 문장으로 댓글을 유도하세요.",
        "follow": "시리즈/연재를 암시해 팔로우 유도 문장을 넣으세요.",
        "profile": "프로필 링크로 이동을 유도하는 문장을 넣으세요.",
        "dm": "DM 상담/신청을 유도하는 문장을 넣으세요.",
    }

    HASHTAG_DIRECTIONS = {
        "warning": "경고/주의 관련 해시태그(#주의사항 #실수방지)를 우선 배치하세요.",
        "tutorial": "하우투/단계별 해시태그(#방법 #가이드 #초보)를 우선 배치하세요.",
        "comparison": "비교 관련 해시태그(#비교 #추천)를 우선 배치하세요.",
        "story": "경험/공감 해시태그(#경험담 #일상)를 우선 배치하세요.",
        "number_list": "리스트형 해시태그(#TOP5 #꿀팁)를 우선 배치하세요.",
        "resource": "리소스/무료자료 해시태그(#무료자료 #추천템)를 우선 배치하세요.",
    }
    DEFAULT_HASHTAG_DIRECTION = "핵심 키워드와 브랜드 해시태그를 우선 배치하세요."

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def generate(
        self,
        content_result: Optional[Dict[str, Any]],
        pattern_plan: Optional[Dict[str, Any]] = None,
        cta_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            return self._generate(content_result or {}, pattern_plan or {}, cta_type)
        except Exception:
            return self._fallback_hint()

    def _generate(
        self,
        content_result: Dict[str, Any],
        pattern_plan: Dict[str, Any],
        cta_type: Optional[str],
    ) -> Dict[str, Any]:
        resolved_cta = cta_type or pattern_plan.get("cta_type") or self._infer_cta_from_content(content_result)
        recommended_action = resolved_cta if resolved_cta in self.RECOMMENDED_ACTIONS else self.DEFAULT_ACTION

        caption_direction = self.CAPTION_DIRECTIONS.get(
            recommended_action,
            self.CAPTION_DIRECTIONS[self.DEFAULT_ACTION],
        )
        hashtag_direction = self.HASHTAG_DIRECTIONS.get(
            str(pattern_plan.get("pattern_type", "")),
            self.DEFAULT_HASHTAG_DIRECTION,
        )
        checklist = self._checklist(content_result)

        return {
            "recommended_action": recommended_action,
            "caption_direction": caption_direction,
            "hashtag_direction": hashtag_direction,
            "checklist": checklist,
            "reason": f"cta_type '{resolved_cta}' 기준으로 '{recommended_action}' 행동을 추천함.",
        }

    def _infer_cta_from_content(self, content_result: Dict[str, Any]) -> str:
        slides = content_result.get("slides", [])
        cta_text = ""

        if isinstance(slides, list):
            for slide in slides:
                if isinstance(slide, dict) and slide.get("role") == "cta":
                    cta_text = f"{slide.get('headline', '')} {slide.get('body', '')}"
                    break

        cta_text_lower = cta_text.lower()

        if "저장" in cta_text_lower or "save" in cta_text_lower:
            return "save"
        if "팔로우" in cta_text_lower or "follow" in cta_text_lower:
            return "follow"
        if "댓글" in cta_text_lower or "comment" in cta_text_lower:
            return "comment"
        if "dm" in cta_text_lower:
            return "dm"
        if "프로필" in cta_text_lower or "profile" in cta_text_lower:
            return "profile"

        return self.DEFAULT_ACTION

    def _checklist(self, content_result: Dict[str, Any]) -> List[str]:
        slides = content_result.get("slides", [])
        slide_count = len(slides) if isinstance(slides, list) else 0

        return [
            "제목과 첫 슬라이드 헤드라인이 일치/자연스러운지 확인",
            f"슬라이드 {slide_count}장의 오탈자와 줄바꿈을 확인",
            "허위/과장 표현이 없는지 다시 확인",
            "caption과 hashtag가 계정 톤에 맞는지 확인",
            "이미지와 텍스트가 겹치지 않는지 카드뉴스 미리보기로 확인",
        ]

    def _fallback_hint(self) -> Dict[str, Any]:
        return {
            "recommended_action": self.DEFAULT_ACTION,
            "caption_direction": self.CAPTION_DIRECTIONS[self.DEFAULT_ACTION],
            "hashtag_direction": self.DEFAULT_HASHTAG_DIRECTION,
            "checklist": [
                "발행 힌트 계산 실패로 기본 체크리스트를 사용합니다.",
                "제목/캡션/해시태그를 수동으로 다시 확인하세요.",
            ],
            "reason": "publishing hint 계산 실패로 기본값 사용.",
        }
