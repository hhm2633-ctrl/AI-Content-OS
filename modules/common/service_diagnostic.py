import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class ServiceDiagnostic:
    """
    외부 서비스(LLM, Image API, Naver News, Nate Pann 등) 연결 실패를 안전하게
    진단하기 위한 공용 헬퍼.

    보안 원칙:
    - 환경변수는 "존재 여부"만 확인한다. 값(API Key 원문)은 절대 읽어서
      반환/로그/저장하지 않는다.
    - 진단 결과(safe_message)는 항상 미리 정의된 고정 문구만 사용한다.
      예외 메시지 원문을 그대로 노출하지 않는다.
    - mask_secrets()는 혹시라도 원문 에러 텍스트를 다뤄야 할 상황을 대비한
      마지막 방어선이며, sk-... 형태의 키/Bearer 토큰/"api_key=..." 패턴을
      마스킹한다.

    분류되는 오류 유형(error_type):
    missing_api_key, connection_refused, timeout, auth_failed,
    rate_limited, unknown_error

    이 모듈의 모든 공개 메서드는 예외를 던지지 않는다 (workflow_failed를
    유발하지 않기 위함).
    """

    ERROR_TYPES = (
        "missing_api_key",
        "connection_refused",
        "timeout",
        "auth_failed",
        "rate_limited",
        "unknown_error",
    )

    SAFE_MESSAGES: Dict[str, str] = {
        "missing_api_key": "API Key 환경변수가 설정되어 있지 않습니다.",
        "connection_refused": "서버 연결이 거부되었습니다. 네트워크/방화벽 상태를 확인하세요.",
        "timeout": "요청이 시간 초과되었습니다. 네트워크 상태를 확인하세요.",
        "auth_failed": "인증에 실패했습니다. API Key가 유효한지 확인하세요.",
        "rate_limited": "요청 한도를 초과했습니다. 잠시 후 다시 시도하세요.",
        "unknown_error": "알 수 없는 오류가 발생했습니다.",
    }

    # 기존 트렌드 수집기(NaverNewsCollector/NatePannCollector)의 세부 실패
    # 사유를 공용 error_type taxonomy로 매핑한다.
    REASON_TYPE_MAP: Dict[str, str] = {
        "connection_refused": "connection_refused",
        "timeout": "timeout",
        "http_401": "auth_failed",
        "http_403": "auth_failed",
        "http_403_forbidden": "auth_failed",
        "http_429": "rate_limited",
        "network_error": "unknown_error",
        "parse_failed": "unknown_error",
        "parse_error": "unknown_error",
        "no_results": "unknown_error",
        "empty_result": "unknown_error",
        "unknown_error": "unknown_error",
    }

    DIAGNOSTIC_PATH = Path("storage/runtime/service_diagnostic.json")
    MAX_RECORDS = 200

    _SECRET_PATTERNS = (
        re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
        re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{8,}"),
        re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)([^\s,;'\"]{4,})"),
        re.compile(r"(?i)(token\s*[:=]\s*)([^\s,;'\"]{4,})"),
        re.compile(r"(?i)(password\s*[:=]\s*)([^\s,;'\"]{4,})"),
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    # ------------------------------------------------------------------
    # 환경변수 존재 여부 확인 (값은 절대 반환하지 않음)
    # ------------------------------------------------------------------
    def check_env_key(self, env_var_name: str) -> bool:
        try:
            value = os.getenv(env_var_name)
            return bool(value and value.strip())
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 민감정보 마스킹 (방어선)
    # ------------------------------------------------------------------
    def mask_secrets(self, text: str) -> str:
        try:
            masked = str(text)

            for pattern in self._SECRET_PATTERNS:
                masked = pattern.sub(self._mask_replacement, masked)

            return masked
        except Exception:
            return "***error_message_unavailable***"

    def _mask_replacement(self, match: "re.Match") -> str:
        groups = match.groups()

        if len(groups) >= 2:
            return f"{groups[0]}***MASKED***"

        return "***MASKED***"

    def _safe_error_text(self, error: Any) -> str:
        try:
            text = str(error) if error is not None else ""
        except Exception:
            text = ""

        return self.mask_secrets(text)

    # ------------------------------------------------------------------
    # API Key 기반 서비스(LLM, Image) 오류 분류
    # ------------------------------------------------------------------
    def classify_error(self, error: Any, api_key_present: Optional[bool] = None) -> str:
        try:
            return self._classify_error(error, api_key_present)
        except Exception:
            return "unknown_error"

    def _classify_error(self, error: Any, api_key_present: Optional[bool]) -> str:
        if api_key_present is False:
            return "missing_api_key"

        message_lower = self._safe_error_text(error).lower()
        status_code = self._extract_status_code(error)

        if status_code == 401 or "unauthorized" in message_lower or "invalid api key" in message_lower or "invalid_api_key" in message_lower:
            return "auth_failed"

        if status_code == 429 or "rate limit" in message_lower or "too many requests" in message_lower:
            return "rate_limited"

        if status_code == 403:
            return "auth_failed"

        if "refused" in message_lower or "10061" in message_lower or "connectionrefused" in message_lower:
            return "connection_refused"

        if "timed out" in message_lower or "timeout" in message_lower:
            return "timeout"

        return "unknown_error"

    def _extract_status_code(self, error: Any) -> Optional[int]:
        for attr in ("status_code", "code", "http_status"):
            value = getattr(error, attr, None)

            if isinstance(value, int):
                return value

        return None

    def build_service_diagnostic(
        self,
        service: str,
        env_var_name: str,
        error: Any = None,
        status: str = "fallback_used",
    ) -> Dict[str, Any]:
        try:
            api_key_present = self.check_env_key(env_var_name)

            if not api_key_present:
                error_type = "missing_api_key"
            elif error is not None:
                error_type = self.classify_error(error, api_key_present)
            else:
                error_type = ""

            safe_message = (
                self.SAFE_MESSAGES.get(error_type, self.SAFE_MESSAGES["unknown_error"])
                if error_type
                else ""
            )

            return {
                "service": service,
                "status": status,
                "error_type": error_type,
                "safe_message": safe_message,
                "api_key_present": api_key_present,
            }
        except Exception:
            return {
                "service": service,
                "status": status,
                "error_type": "unknown_error",
                "safe_message": self.SAFE_MESSAGES["unknown_error"],
                "api_key_present": False,
            }

    # ------------------------------------------------------------------
    # 네트워크 전용 서비스(Naver News, Nate Pann 등 API Key 없는 서비스) 진단
    # ------------------------------------------------------------------
    def map_reason_to_error_type(self, reason: str) -> str:
        try:
            return self.REASON_TYPE_MAP.get(str(reason or ""), "unknown_error")
        except Exception:
            return "unknown_error"

    def build_diagnostic_from_reason(
        self,
        service: str,
        reason: str,
        status: str = "fallback_used",
    ) -> Dict[str, Any]:
        try:
            if status == "ok" or not reason:
                return {
                    "service": service,
                    "status": "ok",
                    "error_type": "",
                    "safe_message": "",
                    "api_key_present": None,
                }

            error_type = self.map_reason_to_error_type(reason)
            safe_message = self.SAFE_MESSAGES.get(error_type, self.SAFE_MESSAGES["unknown_error"])

            return {
                "service": service,
                "status": status,
                "error_type": error_type,
                "safe_message": safe_message,
                "api_key_present": None,
            }
        except Exception:
            return {
                "service": service,
                "status": status,
                "error_type": "unknown_error",
                "safe_message": self.SAFE_MESSAGES["unknown_error"],
                "api_key_present": None,
            }

    # ------------------------------------------------------------------
    # storage/runtime/service_diagnostic.json 저장 (append, bounded history)
    # ------------------------------------------------------------------
    def record(self, diagnostic: Optional[Dict[str, Any]]) -> None:
        try:
            self._record(diagnostic or {})
        except Exception as error:
            print(f"Service Diagnostic Save Failed: {error}")

    def _record(self, diagnostic: Dict[str, Any]) -> None:
        if not diagnostic:
            return

        self.DIAGNOSTIC_PATH.parent.mkdir(parents=True, exist_ok=True)

        existing = self._load_existing()
        records = existing.get("records", [])

        if not isinstance(records, list):
            records = []

        records.append(
            {
                "recorded_at": datetime.now().isoformat(),
                "diagnostic": diagnostic,
            }
        )

        if len(records) > self.MAX_RECORDS:
            records = records[-self.MAX_RECORDS:]

        with open(self.DIAGNOSTIC_PATH, "w", encoding="utf-8") as file:
            json.dump(
                {"updated_at": datetime.now().isoformat(), "records": records},
                file,
                ensure_ascii=False,
                indent=2,
            )

    def _load_existing(self) -> Dict[str, Any]:
        if not self.DIAGNOSTIC_PATH.exists():
            return {"updated_at": None, "records": []}

        try:
            with open(self.DIAGNOSTIC_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return {"updated_at": None, "records": []}
