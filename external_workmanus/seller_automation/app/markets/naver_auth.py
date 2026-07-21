"""
네이버 커머스 API 인증 모듈.

캄파(CAMPA) OSSA_Token 디컴파일 분석으로 검증한 표준 네이버 커머스 API 전자서명 방식:
  1) timestamp = 현재 UTC 밀리초 (안전하게 -1분 보정)
  2) 서명 평문 = clientId + "_" + timestamp
  3) signature = bcrypt.hashpw(평문, salt=clientSecret) 결과를 Base64 인코딩
  4) POST https://api.commerce.naver.com/external/v1/oauth2/token
     (client_id, timestamp, client_secret_sign=signature, grant_type=client_credentials, type=SELF)
  5) access_token 획득 후 만료 전까지 캐시 재사용

주의: 네이버 커머스 API의 client_secret 자체가 bcrypt salt 형식($2a$10$...22자)이므로
      bcrypt.hashpw(평문, clientSecret) 호출이 그대로 동작한다.
"""
from __future__ import annotations
import base64
import time
import threading
from dataclasses import dataclass
from typing import Optional

import bcrypt
import requests

API_BASE = "https://api.commerce.naver.com/external"
TOKEN_URL = f"{API_BASE}/v1/oauth2/token"


def make_signature(client_id: str, client_secret: str, timestamp_ms: int) -> str:
    """네이버 커머스 API 전자서명 생성 (bcrypt + base64)."""
    plain = f"{client_id}_{timestamp_ms}"
    hashed = bcrypt.hashpw(plain.encode("utf-8"), client_secret.encode("utf-8"))
    return base64.b64encode(hashed).decode("utf-8")


@dataclass
class TokenCache:
    access_token: str = ""
    expires_at: float = 0.0  # epoch seconds


class NaverAuth:
    """client_id/secret 한 쌍에 대한 토큰 발급/캐시 관리."""

    def __init__(self, client_id: str, client_secret: str, timeout: int = 20):
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._cache = TokenCache()
        self._lock = threading.Lock()

    def get_token(self, force: bool = False) -> str:
        with self._lock:
            now = time.time()
            # 만료 60초 전이면 갱신
            if not force and self._cache.access_token and now < self._cache.expires_at - 60:
                return self._cache.access_token
            return self._issue_token()

    def _issue_token(self) -> str:
        timestamp = int((time.time() - 60) * 1000)  # -1분 보정, 밀리초
        signature = make_signature(self.client_id, self.client_secret, timestamp)
        payload = {
            "client_id": self.client_id,
            "timestamp": timestamp,
            "client_secret_sign": signature,
            "grant_type": "client_credentials",
            "type": "SELF",
        }
        resp = requests.post(
            TOKEN_URL, data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise NaverAuthError(
                f"토큰 발급 실패 (HTTP {resp.status_code}): {resp.text[:300]}"
            )
        data = resp.json()
        token = data.get("access_token", "")
        expires_in = int(data.get("expires_in", 10800))  # 보통 3시간
        if not token:
            raise NaverAuthError(f"토큰이 비어 있습니다: {data}")
        self._cache.access_token = token
        self._cache.expires_at = time.time() + expires_in
        return token


class NaverAuthError(Exception):
    pass
