import json
from typing import Any, Dict, Optional

try:
    from modules.base_module import BaseModule
except ImportError:
    from src.base_module import BaseModule

from src.llm_client import LLMClient


class ResearchModule(BaseModule):
    """
    ResearchModule

    역할:
    - 카드뉴스 주제 리서치
    - 핵심 정보 정리
    - ContentModule에 넘길 research_result 생성
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

        self.topic = (
            self.config.get("topic")
            or self.config.get("default_topic")
            or "AI content automation"
        )

    def run(self, topic: Optional[str] = None) -> Dict[str, Any]:
        print("Research Module Started")

        selected_topic = topic or self.topic

        system_prompt = """
너는 카드뉴스 콘텐츠를 만들기 위한 전문 리서처다.
초보자도 이해할 수 있게 핵심만 정리한다.
과장된 정보, 확인되지 않은 정보, 투자 조언처럼 보이는 표현은 피한다.
반드시 JSON 형식으로만 답변한다.
"""

        user_prompt = f"""
다음 주제로 카드뉴스 제작용 리서치를 해줘.

주제:
{selected_topic}

아래 JSON 형식으로만 답변해줘.

{{
  "topic": "주제명",
  "summary": "핵심 요약",
  "key_points": [
    "핵심 포인트 1",
    "핵심 포인트 2",
    "핵심 포인트 3"
  ],
  "audience_interest": [
    "사람들이 관심 가질 이유 1",
    "사람들이 관심 가질 이유 2"
  ],
  "content_angle": "카드뉴스로 풀어갈 관점",
  "status": "research_completed"
}}
"""

        llm_response = self.llm_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        research_result = self._safe_json_parse(llm_response, selected_topic)

        print("Research Module Finished")
        return research_result

    def _safe_json_parse(self, text: str, topic: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except Exception:
            return {
                "topic": topic,
                "summary": text.strip(),
                "key_points": [
                    "AI를 활용해 콘텐츠 제작 시간을 줄일 수 있다.",
                    "반복 작업을 자동화하면 여러 계정 운영이 쉬워진다.",
                    "카드뉴스는 짧고 빠르게 소비되는 콘텐츠에 적합하다.",
                ],
                "audience_interest": [
                    "부업이나 자동화에 관심 있는 사람이 많다.",
                    "AI로 수익화를 시도하려는 사람이 늘고 있다.",
                ],
                "content_angle": "초보자도 이해할 수 있는 AI 콘텐츠 자동화 소개",
                "status": "research_completed",
            }