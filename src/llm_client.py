import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI


class LLMClient:
    """
    AI-Content-OS LLMClient

    역할:
    - OpenAI 텍스트 생성 공통 클라이언트
    - 모든 모듈이 같은 방식으로 LLM을 호출하도록 통일
    - 실패 시 재시도
    - 응답 로그 저장
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = self.config.get("model", "gpt-4o-mini")
        self.temperature = float(self.config.get("temperature", 0.7))
        self.max_tokens = int(self.config.get("max_tokens", 1500))
        self.retry_count = int(self.config.get("retry_count", 2))
        self.retry_delay = float(self.config.get("retry_delay", 2))

        self.log_dir = Path("storage/llm_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        if not self.api_key:
            print("WARNING: OPENAI_API_KEY가 없습니다. .env 파일을 확인하세요.")

        self.client = OpenAI(api_key=self.api_key)

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        기존 모듈 호환용 메서드

        ContentModule, ImagePromptModule, ResearchModule이 사용한다.
        """

        used_temperature = (
            self.temperature if temperature is None else float(temperature)
        )

        used_max_tokens = (
            self.max_tokens if max_tokens is None else int(max_tokens)
        )

        last_error = None

        for attempt in range(1, self.retry_count + 2):
            try:
                print(f"LLM Request Started: attempt {attempt}")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt.strip(),
                        },
                        {
                            "role": "user",
                            "content": user_prompt.strip(),
                        },
                    ],
                    temperature=used_temperature,
                    max_tokens=used_max_tokens,
                )

                text = response.choices[0].message.content or ""

                self._save_log(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_text=text,
                    status="success",
                    error_message=None,
                )

                print("LLM Request Finished")
                return text.strip()

            except Exception as error:
                last_error = error
                print(f"LLM Request Failed: attempt {attempt}")
                print(error)

                self._save_log(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_text="",
                    status="failed",
                    error_message=str(error),
                )

                if attempt <= self.retry_count:
                    time.sleep(self.retry_delay)

        print("LLM Request Completely Failed")

        return json.dumps(
            {
                "status": "llm_failed",
                "error": str(last_error),
            },
            ensure_ascii=False,
        )

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        JSON 응답이 필요한 모듈에서 사용할 수 있는 보조 메서드
        아직 기존 모듈을 깨지 않기 위해 선택 기능으로 둔다.
        """

        text = self.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        try:
            return json.loads(text)
        except Exception:
            if fallback is not None:
                return fallback

            return {
                "status": "json_parse_failed",
                "raw_text": text,
            }

    def _save_log(
        self,
        system_prompt: str,
        user_prompt: str,
        response_text: str,
        status: str,
        error_message: Optional[str],
    ) -> None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_path = self.log_dir / f"llm_log_{timestamp}.json"

        log_data = {
            "status": status,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "response_text": response_text,
            "error_message": error_message,
        }

        with open(log_path, "w", encoding="utf-8") as file:
            json.dump(log_data, file, ensure_ascii=False, indent=2)