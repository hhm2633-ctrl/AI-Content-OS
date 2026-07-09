import json
from pathlib import Path
from typing import Any, Dict, Optional

from modules.content.cta_strategy import CTAStrategy
from modules.content.hook_strategy import HookStrategy
from modules.content.pattern_prompt_router import PatternPromptRouter
from modules.content.slide_strategy import SlideStrategy


class ContentPromptBuilder:
    """
    selected_topic/research_result/pattern_plan/hook/cta/slide_strategy/brand_profile을
    모두 사용해 ContentModule의 system_prompt/user_prompt를 만든다.

    research_result에 pattern_plan이 없으면 build()는 None을 반환하며, 호출자인
    ContentModule은 기존(legacy) 방식으로 자동 복귀해야 한다. 이 클래스는 내부에서
    예외를 던지지 않는다 (build()가 항상 dict 또는 None을 반환).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.pattern_prompt_router = PatternPromptRouter(self.config)
        self.hook_strategy = HookStrategy(self.config)
        self.cta_strategy = CTAStrategy(self.config)
        self.slide_strategy = SlideStrategy(self.config)
        self.brand_profile = self._load_brand_profile()

    def build(self, research_result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        try:
            return self._build(research_result or {})
        except Exception as error:
            print(f"Content Prompt Builder Failed: {error}")
            return None

    def _build(self, research_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pattern_plan = research_result.get("pattern_plan") or {}
        topic_intelligence = research_result.get("topic_intelligence") or {}

        if not isinstance(pattern_plan, dict) or not str(pattern_plan.get("pattern_type", "")).strip():
            return None

        keyword = research_result.get("keyword") or research_result.get("topic") or "AI content automation"
        title = research_result.get("title") or f"{keyword} 카드뉴스"
        summary = research_result.get("summary", "")
        key_points = research_result.get("key_points", [])
        target = research_result.get("target", "AI 자동화와 부업에 관심 있는 초보자")
        topic_angle = research_result.get("topic_angle", "")

        hook_result = self.hook_strategy.select(pattern_plan, topic_intelligence)
        cta_result = self.cta_strategy.select(pattern_plan, topic_intelligence)
        slide_plan = self.slide_strategy.build(pattern_plan.get("pattern_type", "resource"))
        prompt_guide = self.pattern_prompt_router.get_guide(pattern_plan.get("pattern_type", "resource"))

        system_prompt = self._build_system_prompt(prompt_guide, hook_result, cta_result)
        user_prompt = self._build_user_prompt(
            keyword=keyword,
            title=title,
            summary=summary,
            key_points=key_points,
            target=target,
            topic_angle=topic_angle,
            pattern_plan=pattern_plan,
            topic_intelligence=topic_intelligence,
            slide_plan=slide_plan,
        )

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "meta": {
                "pattern_type": slide_plan.get("pattern_type", pattern_plan.get("pattern_type", "resource")),
                "hook_type": hook_result.get("hook_type"),
                "cta_type": cta_result.get("cta_type"),
                "layout_type": pattern_plan.get("layout_type", ""),
                "prompt_source": prompt_guide.get("source"),
            },
        }

    def _build_system_prompt(
        self,
        prompt_guide: Dict[str, Any],
        hook_result: Dict[str, Any],
        cta_result: Dict[str, Any],
    ) -> str:
        banned_words = self.brand_profile.get("banned_words", [])
        banned_words_text = ", ".join(banned_words) if banned_words else "허위 수익 보장, 과장 광고, 투자 권유"

        return f"""
너는 인스타그램 카드뉴스 전문 기획자이자 카피라이터다.
브랜드: {self.brand_profile.get("brand_name", "AI-Content-OS")}
브랜드 말투: {self.brand_profile.get("voice", "친근하고 신뢰감 있는 초보자 친화적 말투")}
타깃: {self.brand_profile.get("target_audience", "AI 자동화와 부업에 관심 있는 초보자")}

패턴 가이드: {prompt_guide.get("guide", "")}
Hook 전략: '{hook_result.get("hook_type")}' 타입의 훅을 사용한다. ({hook_result.get("reason", "")})
CTA 전략: '{cta_result.get("cta_type")}' 타입의 CTA를 사용한다. ({cta_result.get("reason", "")})

초보자가 바로 이해할 수 있게 짧고 강하게 쓴다.
다음 표현은 피한다: {banned_words_text}.
각 슬라이드는 headline과 body를 반드시 분리한다.
반드시 JSON 형식으로만 답변한다.
"""

    def _build_user_prompt(
        self,
        keyword: str,
        title: str,
        summary: str,
        key_points: Any,
        target: str,
        topic_angle: str,
        pattern_plan: Dict[str, Any],
        topic_intelligence: Dict[str, Any],
        slide_plan: Dict[str, Any],
    ) -> str:
        slides = slide_plan.get("slides", [])
        slide_lines = [
            f"{slide.get('page')}장 ({slide.get('role')}): {slide.get('purpose', '')}"
            for slide in slides
        ]

        slide_structure_text = "\n".join(slide_lines) if slide_lines else (
            "1장은 강한 후킹\n2장은 문제 설명\n3장은 해결 구조\n4장은 저장/팔로우 유도"
        )

        keywords = topic_intelligence.get("keywords", [])

        return f"""
아래 리서치 내용을 바탕으로 인스타그램 카드뉴스 4장을 만들어줘.

주제:
{keyword}

제목:
{title}

요약:
{summary}

핵심 포인트:
{key_points}

타깃:
{target}

콘텐츠 관점:
{topic_angle}

Pattern Plan (Pattern Engine 선택 결과):
- pattern_type: {pattern_plan.get("pattern_type", "")}
- layout_type: {pattern_plan.get("layout_type", "")}
- 선택 이유: {pattern_plan.get("reason", "")}

Topic Intelligence:
- category: {topic_intelligence.get("category", "")}
- cluster: {topic_intelligence.get("cluster", "")}
- confidence_score: {topic_intelligence.get("confidence_score", "")}
- keywords: {keywords}

슬라이드 구조 (반드시 이 역할 순서와 목적을 따를 것):
{slide_structure_text}

조건:
- headline은 짧게
- body는 1~2문장
- 초보자 말투
- 너무 어려운 용어 금지

아래 JSON 형식으로만 답변해줘.

{{
  "title": "카드뉴스 전체 제목",
  "slides": [
    {{
      "page": 1,
      "role": "hook",
      "headline": "1장 제목",
      "body": "1장 본문"
    }},
    {{
      "page": 2,
      "role": "problem",
      "headline": "2장 제목",
      "body": "2장 본문"
    }},
    {{
      "page": 3,
      "role": "solution",
      "headline": "3장 제목",
      "body": "3장 본문"
    }},
    {{
      "page": 4,
      "role": "cta",
      "headline": "4장 제목",
      "body": "4장 본문"
    }}
  ],
  "caption": "인스타그램 본문 캡션",
  "hashtags": ["#AI콘텐츠", "#콘텐츠자동화", "#카드뉴스", "#부업준비", "#인스타콘텐츠"],
  "status": "content_created"
}}
"""

    def _load_brand_profile(self) -> Dict[str, Any]:
        config_path = Path("config/brand_profile.json")

        if not config_path.exists():
            return self._fallback_brand_profile()

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return self._fallback_brand_profile()

    def _fallback_brand_profile(self) -> Dict[str, Any]:
        return {
            "brand_name": "AI-Content-OS",
            "voice": "친근하고 신뢰감 있는 초보자 친화적 말투",
            "tone_keywords": ["쉬운 설명", "실전형", "신뢰감"],
            "banned_words": ["대박", "무조건", "100% 보장", "확정 수익"],
            "target_audience": "AI 자동화와 부업, 콘텐츠 자동화에 관심 있는 초보자",
            "cta_style": "저장/팔로우를 자연스럽게 유도하되 과도한 강매 느낌은 피함",
        }
