import json
from typing import Any, Dict, List, Optional

try:
    from modules.base_module import BaseModule
except ImportError:
    from src.base_module import BaseModule

from src.llm_client import LLMClient


class ImagePromptModule(BaseModule):
    """
    ImagePromptModule

    역할:
    - ContentModule 결과를 바탕으로 카드뉴스용 이미지 프롬프트 생성
    - ImageGenerationModule이 사용할 수 있는 구조 생성
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

    def run(self, content_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        print("Image Prompt Module Started")

        content_result = content_result or {}

        title = content_result.get("title", "AI content automation")
        slides = content_result.get("slides", [])

        system_prompt = """
너는 인스타그램 카드뉴스용 이미지 프롬프트 전문가다.
한국어 카드뉴스에 어울리는 깔끔한 시각 콘셉트를 만든다.
이미지에는 글자를 넣지 않는 방향으로 프롬프트를 작성한다.
사람 얼굴, 브랜드 로고, 저작권 캐릭터는 피한다.
반드시 JSON 형식으로만 답변한다.
"""

        user_prompt = f"""
아래 카드뉴스 내용을 바탕으로 각 장에 어울리는 이미지 생성 프롬프트를 만들어줘.

카드뉴스 제목:
{title}

슬라이드:
{slides}

아래 JSON 형식으로만 답변해줘.

{{
  "title": "카드뉴스 제목",
  "image_prompts": [
    {{
      "page": 1,
      "prompt": "이미지 생성 프롬프트",
      "style": "clean modern instagram card news",
      "ratio": "1:1"
    }},
    {{
      "page": 2,
      "prompt": "이미지 생성 프롬프트",
      "style": "clean modern instagram card news",
      "ratio": "1:1"
    }},
    {{
      "page": 3,
      "prompt": "이미지 생성 프롬프트",
      "style": "clean modern instagram card news",
      "ratio": "1:1"
    }},
    {{
      "page": 4,
      "prompt": "이미지 생성 프롬프트",
      "style": "clean modern instagram card news",
      "ratio": "1:1"
    }}
  ],
  "status": "image_prompts_created"
}}
"""

        llm_response = self.llm_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        image_prompt_result = self._safe_json_parse(
            text=llm_response,
            title=title,
            slides=slides,
        )

        print("Image Prompt Module Finished")
        return image_prompt_result

    def _safe_json_parse(
        self,
        text: str,
        title: str,
        slides: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        try:
            result = json.loads(text)

            if "image_prompts" not in result:
                raise ValueError("image_prompts key missing")

            return result

        except Exception:
            image_prompts = []

            if not slides:
                slides = [
                    {"page": 1, "headline": "AI 콘텐츠 자동화"},
                    {"page": 2, "headline": "자동화 구조"},
                    {"page": 3, "headline": "초보자 시작"},
                    {"page": 4, "headline": "작게 만들고 개선"},
                ]

            for slide in slides:
                page = slide.get("page", len(image_prompts) + 1)
                headline = slide.get("headline", title)

                image_prompts.append(
                    {
                        "page": page,
                        "prompt": (
                            f"Minimal modern digital illustration for Korean Instagram card news, "
                            f"topic: {headline}, clean layout, soft lighting, simple objects, "
                            f"no text, no logo, no watermark, square composition"
                        ),
                        "style": "clean modern instagram card news",
                        "ratio": "1:1",
                    }
                )

            return {
                "title": title,
                "image_prompts": image_prompts,
                "status": "image_prompts_created",
            }