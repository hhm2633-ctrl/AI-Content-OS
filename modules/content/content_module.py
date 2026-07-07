import json
from typing import Any, Dict, Optional

try:
    from modules.base_module import BaseModule
except ImportError:
    from src.base_module import BaseModule

from src.llm_client import LLMClient


class ContentModule(BaseModule):
    """
    ContentModule

    역할:
    - ResearchModule 결과를 카드뉴스 문안으로 변환
    - CardNewsModule이 사용할 수 있는 구조 생성
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, llm_client: Optional[LLMClient] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}
        self.llm_client = llm_client or getattr(self, "llm_client", None) or LLMClient(
            self.config.get("llm", self.config)
        )

    def run(self, research_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        print("Content Module Started")

        research_result = research_result or {}

        topic = research_result.get("topic", "AI content automation")
        summary = research_result.get("summary", "")
        key_points = research_result.get("key_points", [])
        audience_interest = research_result.get("audience_interest", [])
        content_angle = research_result.get("content_angle", "")

        system_prompt = """
너는 인스타그램 카드뉴스 전문 카피라이터다.
짧고 명확하게 쓴다.
초보자가 바로 이해할 수 있게 쓴다.
과장 광고, 허위 수익 보장, 투자 권유 표현은 피한다.
반드시 JSON 형식으로만 답변한다.
"""

        user_prompt = f"""
아래 리서치 내용을 바탕으로 카드뉴스 초안을 만들어줘.

주제:
{topic}

요약:
{summary}

핵심 포인트:
{key_points}

사람들이 관심 가질 이유:
{audience_interest}

콘텐츠 관점:
{content_angle}

아래 JSON 형식으로만 답변해줘.

{{
  "title": "카드뉴스 제목",
  "slides": [
    {{
      "page": 1,
      "headline": "1장 제목",
      "body": "1장 본문"
    }},
    {{
      "page": 2,
      "headline": "2장 제목",
      "body": "2장 본문"
    }},
    {{
      "page": 3,
      "headline": "3장 제목",
      "body": "3장 본문"
    }},
    {{
      "page": 4,
      "headline": "4장 제목",
      "body": "4장 본문"
    }}
  ],
  "caption": "인스타그램 본문 캡션",
  "hashtags": [
    "#AI콘텐츠",
    "#콘텐츠자동화",
    "#카드뉴스"
  ],
  "status": "content_created"
}}
"""

        llm_response = self.llm_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        content_result = self._safe_json_parse(llm_response, topic)

        print("Content Module Finished")
        return content_result

    def _safe_json_parse(self, text: str, topic: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except Exception:
            return {
                "title": f"{topic}에 대한 카드뉴스 초안",
                "slides": [
                    {
                        "page": 1,
                        "headline": "왜 지금 이 주제가 중요할까?",
                        "body": "AI를 활용한 콘텐츠 자동화는 반복 작업을 줄이고 제작 속도를 높이는 데 도움이 됩니다.",
                    },
                    {
                        "page": 2,
                        "headline": "핵심은 자동화 구조입니다",
                        "body": "주제 선정, 리서치, 글 작성, 이미지 구성, 발행까지 흐름을 나누어야 안정적으로 운영할 수 있습니다.",
                    },
                    {
                        "page": 3,
                        "headline": "초보자도 시작할 수 있습니다",
                        "body": "처음부터 완전 자동화를 목표로 하기보다, 하나씩 모듈을 연결하며 안정성을 높이는 방식이 좋습니다.",
                    },
                    {
                        "page": 4,
                        "headline": "작게 만들고 계속 개선하세요",
                        "body": "처음에는 카드뉴스 1개를 정확히 만드는 것이 중요합니다. 이후 계정 수와 발행량을 늘리면 됩니다.",
                    },
                ],
                "caption": "AI 콘텐츠 자동화는 작은 구조부터 시작하는 것이 중요합니다.",
                "hashtags": ["#AI콘텐츠", "#콘텐츠자동화", "#카드뉴스"],
                "status": "content_created",
            }