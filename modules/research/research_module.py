import json
from datetime import datetime
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
    - 카드뉴스 주제의 기초 리서치 생성
    - 현재는 안정적인 LLM 기반 리서치 구조
    - 이후 뉴스/커뮤니티 크롤링 모듈과 연결 가능
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.llm_client = llm_client or getattr(self, "llm_client", None) or LLMClient(
            self.config.get("llm", self.config)
        )

        self.default_topic = self.config.get(
            "topic",
            "AI content automation",
        )

    def run(self) -> Dict[str, Any]:
        print("Research Module Started")

        topic = self.default_topic
        today = datetime.now().strftime("%Y-%m-%d")

        system_prompt = """
너는 인스타그램 카드뉴스용 리서치 전문가다.
초보자가 이해할 수 있도록 쉽게 정리한다.
허위 정보, 과장된 수익 보장, 투자 권유 표현은 피한다.
반드시 JSON 형식으로만 답변한다.
"""

        user_prompt = f"""
오늘 날짜:
{today}

리서치 주제:
{topic}

아래 목적에 맞게 카드뉴스 제작용 리서치를 만들어줘.

목적:
- 인스타그램 카드뉴스 제작
- 초보자가 이해 가능한 쉬운 설명
- 사람들이 저장하거나 공유할 만한 정보
- 부업, 자동화, 콘텐츠 제작 관점에서 활용 가능

아래 JSON 형식으로만 답변해줘.

{{
  "topic": "{topic}",
  "summary": "주제에 대한 짧은 요약",
  "key_points": [
    "핵심 포인트 1",
    "핵심 포인트 2",
    "핵심 포인트 3",
    "핵심 포인트 4"
  ],
  "audience_interest": [
    "사람들이 관심 가질 이유 1",
    "사람들이 관심 가질 이유 2",
    "사람들이 관심 가질 이유 3"
  ],
  "content_angle": "카드뉴스로 풀어갈 관점",
  "risk_notes": [
    "주의할 점 1",
    "주의할 점 2"
  ],
  "status": "research_completed"
}}
"""

        llm_response = self.llm_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        research_result = self._safe_json_parse(
            text=llm_response,
            topic=topic,
            today=today,
        )

        print("Research Module Finished")
        return research_result

    def _safe_json_parse(
        self,
        text: str,
        topic: str,
        today: str,
    ) -> Dict[str, Any]:
        try:
            result = json.loads(text)

            if "topic" not in result:
                result["topic"] = topic

            if "status" not in result:
                result["status"] = "research_completed"

            result["created_at"] = today

            return result

        except Exception:
            return {
                "topic": topic,
                "summary": (
                    "AI 콘텐츠 자동화는 주제 선정, 리서치, 문안 작성, 이미지 생성, "
                    "카드뉴스 제작 과정을 나누어 반복 작업을 줄이는 방식입니다."
                ),
                "key_points": [
                    "처음부터 완전 자동화를 목표로 하기보다 작은 흐름부터 만드는 것이 중요합니다.",
                    "카드뉴스 제작은 주제, 문안, 이미지, 발행 순서로 나누면 관리하기 쉽습니다.",
                    "AI는 반복 작업을 줄이는 도구이며, 최종 검수는 사람이 해야 합니다.",
                    "수익화보다 먼저 꾸준히 발행 가능한 시스템을 만드는 것이 우선입니다.",
                ],
                "audience_interest": [
                    "콘텐츠 제작 시간을 줄일 수 있습니다.",
                    "초보자도 작은 자동화 흐름부터 시작할 수 있습니다.",
                    "인스타그램, 블로그, 쇼츠 등 여러 채널로 확장할 수 있습니다.",
                ],
                "content_angle": (
                    "AI 콘텐츠 자동화를 초보자가 하루 한 개 카드뉴스부터 시작하는 관점으로 설명합니다."
                ),
                "risk_notes": [
                    "AI 결과물은 반드시 사람이 검수해야 합니다.",
                    "수익 보장처럼 보이는 표현은 피해야 합니다.",
                ],
                "created_at": today,
                "status": "research_completed",
            }