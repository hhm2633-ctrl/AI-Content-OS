"""
승인 기기 인증 핵심 로직.

동작 흐름:
1. 처음 접속한 브라우저에는 고유한 device_token 쿠키를 발급하고 DB에 '미승인' 상태로 등록한다.
2. 관리자가 로그인하여 해당 기기를 '승인'해야만 그 기기에서 기능을 사용할 수 있다.
3. 로그인 세션은 서명된 쿠키(itsdangerous)로 관리한다.

즉, 비밀번호를 알더라도 '승인된 기기'가 아니면 로그인 자체가 차단되어
내가 허락한 기기에서만 시스템을 쓸 수 있다.
"""
import secrets
from datetime import datetime

from fastapi import Request, Response
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.orm import Session

from . import config
from .models import Device

_serializer = URLSafeTimedSerializer(config.SECRET_KEY, salt="session")

DEVICE_COOKIE = "sa_device"


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


def get_or_create_device(request: Request, response: Response, db: Session) -> Device:
    """요청에서 기기 토큰을 읽거나, 없으면 새 토큰을 발급하고 DB에 등록한다."""
    token = request.cookies.get(DEVICE_COOKIE)
    device = None
    if token:
        device = db.query(Device).filter(Device.device_token == token).first()

    if device is None:
        token = secrets.token_hex(24)
        device = Device(
            device_token=token,
            first_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent", "")[:400],
            approved=not config.REQUIRE_DEVICE_APPROVAL,  # 승인 불요 설정이면 바로 승인
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        # 기기 토큰 쿠키 발급 (1년)
        response.set_cookie(
            DEVICE_COOKIE, token,
            max_age=60 * 60 * 24 * 365,
            httponly=True, samesite="lax",
        )
    else:
        device.last_seen = datetime.utcnow()
        db.commit()

    return device


def is_device_approved(device: Device) -> bool:
    return bool(device and device.approved)


# ---- 로그인 세션 관리 ----

def create_session_cookie(response: Response, device_token: str) -> None:
    """로그인 성공 시 서명된 세션 쿠키를 발급한다."""
    value = _serializer.dumps({"device": device_token, "auth": True})
    response.set_cookie(
        config.SESSION_COOKIE, value,
        max_age=config.SESSION_MAX_AGE,
        httponly=True, samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(config.SESSION_COOKIE)


def read_session(request: Request) -> dict | None:
    raw = request.cookies.get(config.SESSION_COOKIE)
    if not raw:
        return None
    try:
        return _serializer.loads(raw, max_age=config.SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def is_logged_in(request: Request, db: Session) -> bool:
    """세션이 유효하고, 그 세션의 기기가 여전히 승인 상태인지 확인."""
    sess = read_session(request)
    if not sess or not sess.get("auth"):
        return False
    device = db.query(Device).filter(Device.device_token == sess.get("device")).first()
    return is_device_approved(device)
