import os
import time
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI


class LLMClient:
    """
    AI-Content-OS 공통 LLM 클라이언트
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        load_dotenv()

        self.config = config or {}

        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY가 없습니다. .env 파일에 OPENAI_API_KEY를 넣어주세요."
            )

        self.client = OpenAI(api_key=self.api_key)

        self.model = (
            self.config.get("model")
            or self.config.get("llm_model")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4.1-mini"
        )

        self.temperature = float(
            self.config.get("temperature", os.getenv("OPENAI_TEMPERATURE", 0.7))
        )

        self.max_retries = int(
            self.config.get("max_retries", os.getenv("OPENAI_MAX_RETRIES", 3))
        )

        self.retry_delay = float(
            self.config.get("retry_delay", os.getenv("OPENAI_RETRY_DELAY", 2))
        )

    def generate_text(
        self,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """
        텍스트 생성 함수

        지원 방식:
        - generate_text(prompt="...")
        - generate_text(user_prompt="...")
        - generate_text(system_prompt="...", user_prompt="...")
        """

        final_prompt = user_prompt if user_prompt is not None else prompt

        if final_prompt is None:
            final_prompt = kwargs.get("input") or kwargs.get("message")

        if not final_prompt or not str(final_prompt).strip():
            raise ValueError("prompt 또는 user_prompt가 비어 있습니다.")

        selected_model = model or self.model
        selected_temperature = (
            self.temperature if temperature is None else float(temperature)
        )

        input_messages = []

        if system_prompt:
            input_messages.append(
                {
                    "role": "system",
                    "content": str(system_prompt),
                }
            )

        input_messages.append(
            {
                "role": "user",
                "content": str(final_prompt),
            }
        )

        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.responses.create(
                    model=selected_model,
                    input=input_messages,
                    temperature=selected_temperature,
                )

                text = getattr(response, "output_text", None)

                if not text:
                    raise RuntimeError("OpenAI 응답은 왔지만 output_text가 비어 있습니다.")

                return text.strip()

            except Exception as error:
                last_error = error
                print(
                    f"[LLMClient] OpenAI 호출 실패 "
                    f"({attempt}/{self.max_retries}): {error}"
                )

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)

        raise RuntimeError(f"OpenAI 호출 최종 실패: {last_error}")

    def generate(
        self,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        return self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            **kwargs,
        )

    def chat(
        self,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        return self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            **kwargs,
        )

    def complete(
        self,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        return self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            **kwargs,
        )