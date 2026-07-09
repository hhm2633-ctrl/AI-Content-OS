import json
from typing import Any, Dict, List, Optional

try:
    from modules.base_module import BaseModule
except ImportError:
    from src.base_module import BaseModule

from src.llm_client import LLMClient


class ImagePromptModule(BaseModule):
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
이미지에는 글자를 넣지 않는다.
사람 얼굴, 브랜드 로고, 저작권 캐릭터는 피한다.
한국어 카드뉴스 배경으로 쓰기 좋은 깔끔한 이미지를 기획한다.
반드시 JSON 형식으로만 답변한다.
"""

        user_prompt = f"""
아래 카드뉴스 내용을 바탕으로 슬라이드별 이미지 생성 프롬프트 4개를 만들어줘.

카드뉴스 제목:
{title}

슬라이드:
{slides}

조건:
- 1장은 시선 끄는 후킹 이미지
- 2장은 문제 상황 이미지
- 3장은 해결 구조 이미지
- 4장은 정리/행동 유도 이미지
- 이미지 안에는 글자 없음
- 로고 없음
- 워터마크 없음
- 1:1 정사각형
- 전체 톤은 통일

아래 JSON 형식으로만 답변해줘.

{{
  "title": "카드뉴스 제목",
  "image_prompts": [
    {{
      "page": 1,
      "role": "hook",
      "prompt": "이미지 생성 프롬프트",
      "style": "clean modern instagram card news background",
      "ratio": "1:1"
    }},
    {{
      "page": 2,
      "role": "problem",
      "prompt": "이미지 생성 프롬프트",
      "style": "clean modern instagram card news background",
      "ratio": "1:1"
    }},
    {{
      "page": 3,
      "role": "solution",
      "prompt": "이미지 생성 프롬프트",
      "style": "clean modern instagram card news background",
      "ratio": "1:1"
    }},
    {{
      "page": 4,
      "role": "cta",
      "prompt": "이미지 생성 프롬프트",
      "style": "clean modern instagram card news background",
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

            if not isinstance(result, dict):
                raise ValueError("LLM result is not dict")

            if result.get("status") == "llm_failed":
                raise ValueError(result.get("error", "llm_failed"))

            if "image_prompts" not in result or not isinstance(result["image_prompts"], list):
                raise ValueError("image_prompts missing")

            result["image_prompts"] = self._normalize_prompts(result["image_prompts"], title, slides)
            result["status"] = "image_prompts_created"
            result["fallback_used"] = False
            result["fallback_reason"] = ""

            if not result.get("title"):
                result["title"] = title

            return result

        except Exception as error:
            return {
                "title": title,
                "image_prompts": self._fallback_prompts(title, slides),
                "status": "image_prompts_created",
                "fallback_used": True,
                "fallback_reason": f"llm_or_json_parse_failed: {error}",
            }

    def _normalize_prompts(self, prompts, title: str, slides: List[Dict[str, Any]]):
        fallback = self._fallback_prompts(title, slides)
        normalized = []

        for index in range(4):
            source = prompts[index] if index < len(prompts) and isinstance(prompts[index], dict) else {}

            normalized.append({
                "page": index + 1,
                "role": source.get("role") or fallback[index]["role"],
                "prompt": str(source.get("prompt") or fallback[index]["prompt"]),
                "style": source.get("style") or "clean modern instagram card news background",
                "ratio": "1:1",
            })

        return normalized

    def _fallback_prompts(self, title: str, slides: List[Dict[str, Any]]):
        if not slides:
            slides = [
                {"page": 1, "role": "hook", "headline": title},
                {"page": 2, "role": "problem", "headline": "문제 상황"},
                {"page": 3, "role": "solution", "headline": "해결 구조"},
                {"page": 4, "role": "cta", "headline": "정리"},
            ]

        visual_roles = {
            "hook": "eye-catching modern workspace with floating digital cards and automation flow",
            "problem": "busy desk with scattered notes, repeated tasks, laptop screen glow, clean realistic mood",
            "solution": "organized automation pipeline, connected blocks, simple dashboard, calm productive mood",
            "cta": "finished content calendar, clean checklist, soft light, sense of completion",
        }

        image_prompts = []

        for index in range(4):
            slide = slides[index] if index < len(slides) else {}
            role = slide.get("role", "card")
            headline = slide.get("headline", title)
            scene = visual_roles.get(role, "clean modern digital content creation workspace")

            image_prompts.append({
                "page": index + 1,
                "role": role,
                "prompt": (
                    f"{scene}, topic: {headline}, modern Korean Instagram card news background, "
                    f"clean composition, premium minimal style, soft lighting, 1:1 square image, "
                    f"no text, no logo, no watermark, no people faces, usable as card news background"
                ),
                "style": "clean modern instagram card news background",
                "ratio": "1:1",
            })

        return image_prompts
