import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI

from modules.common.service_diagnostic import ServiceDiagnostic


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
        self.retry_backoff_seconds = self.config.get("retry_backoff_seconds", [2, 5, 10])
        if not isinstance(self.retry_backoff_seconds, list):
            self.retry_backoff_seconds = [2, 5, 10]
        self.retry_count = int(self.config.get("retry_count", len(self.retry_backoff_seconds)))

        self.log_dir = Path("storage/llm_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.service_diagnostic = ServiceDiagnostic(self.config)

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
        retry_count_used = 0
        max_attempts = 1 + max(0, self.retry_count)

        for attempt in range(1, max_attempts + 1):
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
                    retry_count=retry_count_used,
                    final_error_type="",
                )

                print("LLM Request Finished")
                return text.strip()

            except Exception as error:
                last_error = error
                final_error_type = self.service_diagnostic.classify_error(
                    error,
                    bool(self.api_key),
                )
                print(f"LLM Request Failed: attempt {attempt}")
                print(f"LLM Retry Status: final_error_type={final_error_type}")

                self._save_log(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_text="",
                    status="failed",
                    error_message=final_error_type,
                    retry_count=retry_count_used,
                    final_error_type=final_error_type,
                )

                if attempt < max_attempts and self._is_retryable_error_type(final_error_type):
                    delay = self._retry_delay_for_retry(retry_count_used)
                    retry_count_used += 1
                    print(f"LLM Retry Scheduled: retry_count={retry_count_used}, delay_seconds={delay}")
                    time.sleep(delay)
                    continue

                break

        print("LLM Request Completely Failed")

        service_diagnostic = self._build_and_record_diagnostic(last_error, retry_count_used)
        final_error_type = service_diagnostic.get("error_type", "unknown_error")

        return json.dumps(
            {
                "status": "llm_failed",
                "error": final_error_type,
                "service_diagnostic": service_diagnostic,
            },
            ensure_ascii=False,
        )

    def _is_retryable_error_type(self, error_type: str) -> bool:
        return error_type in {"connection_refused", "timeout", "unknown_error"}

    def _retry_delay_for_retry(self, retry_index: int) -> float:
        try:
            return float(self.retry_backoff_seconds[retry_index])
        except Exception:
            return 10.0

    def _build_and_record_diagnostic(self, error: Any, retry_count: int = 0) -> Dict[str, Any]:
        try:
            diagnostic = self.service_diagnostic.build_service_diagnostic(
                service="llm",
                env_var_name="OPENAI_API_KEY",
                error=error,
                status="fallback_used",
            )
            diagnostic["retry_count"] = int(retry_count)
            diagnostic["final_error_type"] = diagnostic.get("error_type", "unknown_error")
            self.service_diagnostic.record(diagnostic)
            return diagnostic
        except Exception as diagnostic_error:
            print(f"LLM Service Diagnostic Failed: {diagnostic_error}")
            return {
                "service": "llm",
                "status": "fallback_used",
                "error_type": "unknown_error",
                "safe_message": "알 수 없는 오류가 발생했습니다.",
                "api_key_present": bool(self.api_key),
                "retry_count": int(retry_count),
                "final_error_type": "unknown_error",
            }

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
        retry_count: int = 0,
        final_error_type: str = "",
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
            "retry_count": int(retry_count),
            "final_error_type": final_error_type,
        }

        with open(log_path, "w", encoding="utf-8") as file:
            json.dump(log_data, file, ensure_ascii=False, indent=2)
