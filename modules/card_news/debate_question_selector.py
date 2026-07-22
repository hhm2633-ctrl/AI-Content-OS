import re
from typing import Any, Dict, Optional


class DebateQuestionSelector:
    """
    CardNews Intelligence (Phase M7 - 실제 사용 연결) - Debate Engine.

    마지막(CTA) 슬라이드에 덧붙일 짧은 질문을 pattern_type 기준으로 고른다.
    `modules/content/cta_strategy.py::CTAStrategy`의 cta_line/cta_type 선택
    로직은 전혀 건드리지 않는다 - 이 질문은 CTA 문구를 대체하지 않고 그 위에
    "추가로" 덧붙는 것이다.

    충돌 방지: 기존 cta_type이 이미 댓글/토론을 유도하는 목적(`comment`)이면
    중복이므로 애초에 질문을 만들지 않는다(`should_apply=False`). save/
    profile/dm/follow/share/link_click 등 다른 cta_type은 기존 CTA를 보존한
    채 debate 질문을 보조 문장으로 추가할 수 있다고 판단한다
    (`should_apply=True`) - 실제 글자 수 제한 확인은 CardNewsModule이 최종
    본문 길이를 알고 있는 시점(Text Optimizer 이후)에서 별도로 한다.

    질문 문구는 사실 단정이나 공격 유도가 아니라 쟁점에 대한 의견 차이를
    묻는 중립적 질문만 사용한다(`_is_safe_question`으로 방어적으로 재확인).
    """

    REDUNDANT_CTA_TYPES = ("comment",)

    CTA_INTENT_PATTERNS = {
        "save": re.compile(r"(?:저장|북마크|\bsave\b)", re.IGNORECASE),
        "comment": re.compile(r"(?:댓글|의견|생각|\bcomment\b)", re.IGNORECASE),
        "share": re.compile(r"(?:공유|보내\s*주세요|\bshare\b)", re.IGNORECASE),
        "follow": re.compile(r"(?:팔로우|구독|\bfollow\b)", re.IGNORECASE),
        "profile": re.compile(r"(?:프로필|\bprofile\b)", re.IGNORECASE),
        "dm": re.compile(r"(?:디엠|메시지|\bdm\b|\bmessage\b)", re.IGNORECASE),
        "link_click": re.compile(r"(?:링크|클릭|바이오|\bclick\b)", re.IGNORECASE),
    }

    QUESTION_BY_PATTERN: Dict[str, str] = {
        "warning": "이 조치가 적절했다고 보시나요?",
        "tutorial": "여러분 생각은 어떠세요?",
        "comparison": "어느 쪽 주장에 더 공감하시나요?",
        "story": "여러분 생각은?",
        "number_list": "가장 공감되는 항목은 무엇인가요?",
        "resource": "어떤 게 제일 유용했나요?",
        "funnel": "궁금한 점 있으신가요?",
    }
    DEFAULT_QUESTION = "책임의 범위는 어디까지라고 보시나요?"

    # 방어적 안전 필터: 사실 단정/공격 유도로 흔히 쓰이는 표현이 질문에
    # 섞여 있으면(향후 템플릿이 실수로 추가되는 경우 대비) 안전하지 않다고
    # 판단한다. 현재 QUESTION_BY_PATTERN/DEFAULT_QUESTION은 전부 이 필터를
    # 통과하도록 작성되어 있다.
    UNSAFE_KEYWORDS = ("틀렸다", "잘못됐다", "사기", "거짓말", "멍청", "무능")

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def select(
        self,
        pattern_type: Optional[str] = None,
        cta_type: Optional[str] = None,
        cta_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            return self._select(
                str(pattern_type or ""),
                str(cta_type or ""),
                str(cta_text or ""),
            )
        except Exception as error:
            return {
                "question": "",
                "pattern_type": "",
                "cta_type": "",
                "should_apply": False,
                "skip_reason": f"debate question 선택 실패: {error}",
            }

    def _select(self, pattern_type: str, cta_type: str, cta_text: str = "") -> Dict[str, Any]:
        question = self.QUESTION_BY_PATTERN.get(pattern_type, self.DEFAULT_QUESTION)
        detected_cta_intents = [
            intent
            for intent, pattern in self.CTA_INTENT_PATTERNS.items()
            if pattern.search(cta_text)
        ]

        if not self._is_safe_question(question):
            return {
                "question": "",
                "pattern_type": pattern_type,
                "cta_type": cta_type,
                "detected_cta_intents": detected_cta_intents,
                "should_apply": False,
                "skip_reason": "질문이 안전 필터를 통과하지 못해 적용하지 않음.",
            }

        if cta_type in self.REDUNDANT_CTA_TYPES:
            return {
                "question": question,
                "pattern_type": pattern_type,
                "cta_type": cta_type,
                "detected_cta_intents": detected_cta_intents,
                "should_apply": False,
                "skip_reason": f"cta_type '{cta_type}'가 이미 댓글/토론 유도 목적이라 중복 방지를 위해 적용하지 않음.",
            }

        matched = pattern_type in self.QUESTION_BY_PATTERN

        return {
            "question": question,
            "pattern_type": pattern_type,
            "cta_type": cta_type,
            "detected_cta_intents": detected_cta_intents,
            "should_apply": True,
            "skip_reason": "",
            "reason": (
                f"pattern_type '{pattern_type}' 기준으로 질문을 선택함."
                if matched
                else "pattern_type을 알 수 없어 기본 질문을 사용함."
            ),
        }

    def _is_safe_question(self, question: str) -> bool:
        return not any(keyword in question for keyword in self.UNSAFE_KEYWORDS)
