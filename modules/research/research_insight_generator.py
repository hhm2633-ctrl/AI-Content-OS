import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ResearchInsightGenerator:
    """
    Research Intelligence v1 - LLM 기반 카드뉴스 리서치 근거 생성기.

    ResearchContextBuilder가 만든 research_context(selected_topic + trend 소스
    신호 + topic_intelligence)를 바탕으로, 단순 요약이 아니라 카드뉴스 제작에
    바로 쓸 수 있는 근거와 맥락을 만든다:
    - issue_background (이슈 배경)
    - why_trending_now (왜 지금 뜨는지)
    - audience_interest_points (사람들의 관심 포인트)
    - caution_expressions (주의할 표현)

    LLM 호출은 주입받은 llm_client(src.llm_client.LLMClient)를 통해서만 이뤄지며
    이 클래스는 .env/API Key를 직접 다루지 않는다. LLM 실패/JSON 파싱 실패/
    스키마 불일치 시 예외를 던지지 않고, ContentModule의 _safe_json_parse/
    _fallback_* 패턴과 동일하게 안전한 fallback 콘텐츠를 반환한다
    (fallback-first 계약 유지, workflow_completed 영향 없음).

    fallback summary/key_points는 기존 ResearchModule의 하드코딩 문구와 동일하게
    유지해 LLM을 쓸 수 없는 환경에서도 기존 동작이 그대로 보존되도록 한다.
    """

    BANNED_WORDS_FALLBACK = ["대박", "무조건", "100% 보장", "확정 수익"]
    BRAND_PROFILE_PATH = Path("config/brand_profile.json")

    def __init__(self, config: Optional[Dict[str, Any]] = None, llm_client: Any = None):
        self.config = config or {}
        self.llm_client = llm_client

    def generate(
        self,
        keyword: str,
        title: str,
        research_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            return self._generate(str(keyword or ""), str(title or ""), research_context or {})
        except Exception as error:
            print(f"Research Insight Generation Failed: {error}")
            return self._fallback_insight(keyword, reason=f"insight_generation_exception: {error}")

    def _generate(
        self,
        keyword: str,
        title: str,
        research_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.llm_client is None:
            return self._fallback_insight(keyword, reason="llm_client_not_configured")

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(keyword, title, research_context)

        raw_response = self.llm_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        parsed = self._safe_json_parse(raw_response)

        if parsed is None:
            return self._fallback_insight(keyword, reason="llm_response_not_json")

        if parsed.get("status") == "llm_failed":
            return self._fallback_insight(
                keyword,
                reason=f"llm_call_failed: {parsed.get('error', 'unknown_error')}",
            )

        if not self._has_required_shape(parsed):
            return self._fallback_insight(keyword, reason="llm_response_missing_required_keys")

        return {
            "summary": str(parsed.get("summary", "")).strip() or self._fallback_summary(keyword),
            "key_points": self._normalize_list(parsed.get("key_points"), self._fallback_key_points(keyword)),
            "issue_background": str(parsed.get("issue_background", "")).strip(),
            "why_trending_now": str(parsed.get("why_trending_now", "")).strip(),
            "audience_interest_points": self._normalize_list(parsed.get("audience_interest_points"), []),
            "caution_expressions": self._normalize_list(
                parsed.get("caution_expressions"),
                self._load_banned_words(),
            ),
            "insight_source": "llm",
            "fallback_used": False,
            "reason": "LLM 기반 리서치 근거 생성 성공.",
        }

    def _build_system_prompt(self) -> str:
        return """
너는 인스타그램 카드뉴스 제작을 위한 리서치 애널리스트다.
주어진 주제와 트렌드 수집 신호를 바탕으로, 단순 요약이 아니라 카드뉴스 제작에
바로 쓸 수 있는 근거와 맥락을 만든다.
허위 통계, 확인되지 않은 사실, 과장된 수익/효과 표현은 만들지 않는다.
반드시 JSON 형식으로만 답변한다.
"""

    def _build_user_prompt(
        self,
        keyword: str,
        title: str,
        research_context: Dict[str, Any],
    ) -> str:
        source_signals = research_context.get("source_signals", {})
        fallback_sources = research_context.get("fallback_sources", [])

        source_lines = []

        if isinstance(source_signals, dict):
            for source_id, signal in source_signals.items():
                if not isinstance(signal, dict):
                    continue

                source_lines.append(
                    f"- {source_id}: attempted={signal.get('attempted')}, "
                    f"success={signal.get('success')}, count={signal.get('count')}, "
                    f"is_fallback={signal.get('is_fallback')}"
                )

        source_summary_text = "\n".join(source_lines) if source_lines else "수집 신호 없음"

        return f"""
주제: {keyword}
제목: {title}
카테고리: {research_context.get("category", "")}
클러스터: {research_context.get("cluster", "")}
주제 신뢰도(confidence_score): {research_context.get("confidence_score", "")}
선정 이유: {research_context.get("selection_reason", "")}

트렌드 소스 수집 신호(naver_news/nate_pann/fmkorea/bobaedream):
{source_summary_text}

fallback을 사용한 소스: {fallback_sources}

위 신호를 참고해서 아래 JSON 형식으로만 답변해줘.

{{
  "summary": "카드뉴스용 한 문단 요약",
  "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3", "핵심 포인트 4"],
  "issue_background": "이 주제/이슈가 왜 생겼는지에 대한 배경 설명",
  "why_trending_now": "지금 시점에 이 주제가 왜 뜨고 있는지에 대한 설명",
  "audience_interest_points": ["타깃이 관심 가질 포인트 1", "포인트 2"],
  "caution_expressions": ["과장되거나 조심해야 할 표현 1", "표현 2"]
}}
"""

    def _safe_json_parse(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            result = json.loads(text)

            if isinstance(result, dict):
                return result
        except Exception:
            pass

        return None

    def _has_required_shape(self, parsed: Dict[str, Any]) -> bool:
        return (
            isinstance(parsed.get("summary"), str)
            and isinstance(parsed.get("key_points"), list)
            and isinstance(parsed.get("issue_background"), str)
            and isinstance(parsed.get("why_trending_now"), str)
        )

    def _normalize_list(self, value: Any, fallback: List[str]) -> List[str]:
        if isinstance(value, list) and value:
            cleaned = [str(item).strip() for item in value if str(item).strip()]

            if cleaned:
                return cleaned

        return fallback

    def _fallback_insight(self, keyword: str, reason: str) -> Dict[str, Any]:
        keyword = keyword or "AI content automation"

        return {
            "summary": self._fallback_summary(keyword),
            "key_points": self._fallback_key_points(keyword),
            "issue_background": f"{keyword} 관련 논의가 여러 채널에서 꾸준히 이어지고 있습니다.",
            "why_trending_now": f"{keyword}에 대한 관심이 최근 트렌드 수집 신호에서 반복적으로 확인되고 있습니다.",
            "audience_interest_points": [
                f"{keyword}를 처음 시작하는 방법",
                f"{keyword}로 시간을 아끼는 방법",
            ],
            "caution_expressions": self._load_banned_words(),
            "insight_source": "fallback",
            "fallback_used": True,
            "reason": f"LLM 리서치 근거 생성 실패로 fallback 사용: {reason}",
        }

    def _fallback_summary(self, keyword: str) -> str:
        return f"{keyword} is a useful topic for card news, blog, and shorts content automation."

    def _fallback_key_points(self, keyword: str) -> List[str]:
        return [
            f"{keyword} can attract beginners interested in practical automation.",
            "It is suitable for a short and clear card news format.",
            "It can connect naturally to Instagram content operations.",
            "It can later expand into blog, shorts, and product-linked content.",
        ]

    def _load_banned_words(self) -> List[str]:
        if not self.BRAND_PROFILE_PATH.exists():
            return list(self.BANNED_WORDS_FALLBACK)

        try:
            with open(self.BRAND_PROFILE_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                banned_words = data.get("banned_words")

                if isinstance(banned_words, list) and banned_words:
                    return [str(word) for word in banned_words]
        except Exception:
            pass

        return list(self.BANNED_WORDS_FALLBACK)
