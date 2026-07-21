"""
로컬 비밀값(마켓 시크릿, 도매처 비밀번호) 대칭 암호화 모듈.

- data/secret.key(세션 서명키)에서 파생한 키로 Fernet 암호화를 수행합니다.
- 암호화된 값만 DB에 저장하고, 복호화는 메모리에서만 일어납니다.
- 키 파일(secret.key)이 곧 마스터 키이므로, PC 밖으로 유출되지 않도록 보관합니다.
"""
from __future__ import annotations
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from . import config


def _fernet() -> Fernet:
    # secret.key 문자열을 SHA-256으로 정규화 후 Fernet 키(32바이트 urlsafe base64)로 변환
    digest = hashlib.sha256(config.SECRET_KEY.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    if plaintext is None:
        plaintext = ""
    token = _fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""
