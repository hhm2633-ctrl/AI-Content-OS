"""
서비스 계층: 도매 계정 / 마켓 키 / 가공 설정 저장·조회 + 등록 작업 헬퍼.
DB에 저장하는 비밀값(시크릿/비번)은 crypto로 암호화한다.
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from . import crypto
from .models import (
    SiteCredential, MarketCredential, ProcessingProfile, Product, Listing,
)

# ---------------- 도매 사이트 계정 ----------------
SUPPORTED_SITES = ["luckyfresh", "econfarm", "choigozip"]
SITE_LABELS = {
    "luckyfresh": "럭키프레시",
    "econfarm": "이컨팜",
    "choigozip": "최고집",
}


def get_site_credential(db: Session, site: str) -> Optional[SiteCredential]:
    return db.query(SiteCredential).filter(SiteCredential.site == site).first()


def save_site_credential(db: Session, site: str, username: str, password: str,
                         enabled: bool = True) -> SiteCredential:
    rec = get_site_credential(db, site)
    if not rec:
        rec = SiteCredential(site=site)
        db.add(rec)
    rec.username = username
    if password:  # 비번이 입력된 경우에만 갱신(빈 값이면 기존 유지)
        rec.password_enc = crypto.encrypt(password)
    rec.enabled = enabled
    db.commit()
    return rec


def get_site_login(db: Session, site: str) -> Dict[str, str]:
    rec = get_site_credential(db, site)
    if not rec:
        return {"username": "", "password": ""}
    return {"username": rec.username, "password": crypto.decrypt(rec.password_enc)}


# ---------------- 마켓 API 키 ----------------
SUPPORTED_MARKETS = ["naver", "coupang", "gmarket", "toss"]
MARKET_LABELS = {
    "naver": "네이버 스마트스토어",
    "coupang": "쿠팡",
    "gmarket": "지마켓(ESM)",
    "toss": "토스",
}


def get_market_credential(db: Session, market: str) -> Optional[MarketCredential]:
    return db.query(MarketCredential).filter(MarketCredential.market == market).first()


def save_market_credential(db: Session, market: str, client_id: str,
                           client_secret: str, extra: Optional[dict] = None,
                           enabled: bool = True) -> MarketCredential:
    rec = get_market_credential(db, market)
    if not rec:
        rec = MarketCredential(market=market)
        db.add(rec)
    rec.client_id = client_id
    if client_secret:  # 입력된 경우에만 갱신
        rec.client_secret_enc = crypto.encrypt(client_secret)
    if extra is not None:
        rec.extra_json = json.dumps(extra, ensure_ascii=False)
    rec.enabled = enabled
    db.commit()
    return rec


def get_market_keys(db: Session, market: str) -> Dict[str, str]:
    rec = get_market_credential(db, market)
    if not rec:
        return {"client_id": "", "client_secret": "", "extra": {}}
    return {
        "client_id": rec.client_id,
        "client_secret": crypto.decrypt(rec.client_secret_enc),
        "extra": json.loads(rec.extra_json) if rec.extra_json else {},
    }


def market_key_status(db: Session, market: str) -> bool:
    """키가 등록되어 있는지(빈 값 아님) 여부."""
    rec = get_market_credential(db, market)
    return bool(rec and rec.client_id and rec.client_secret_enc)


# ---------------- 가공 설정 ----------------
def get_default_profile(db: Session) -> ProcessingProfile:
    rec = db.query(ProcessingProfile).filter(ProcessingProfile.is_default == True).first()
    if not rec:
        rec = ProcessingProfile(name="기본", is_default=True)
        db.add(rec)
        db.commit()
    return rec


def save_default_profile(db: Session, **kwargs) -> ProcessingProfile:
    rec = get_default_profile(db)
    for k, v in kwargs.items():
        if hasattr(rec, k) and v is not None:
            setattr(rec, k, v)
    db.commit()
    return rec


# ---------------- 통계 ----------------
def dashboard_stats(db: Session) -> Dict[str, int]:
    total = db.query(Product).count()
    by_site = {}
    for s in SUPPORTED_SITES:
        by_site[s] = db.query(Product).filter(Product.source_site == s).count()
    listed = db.query(Listing).filter(Listing.status == "success").count()
    dryrun = db.query(Listing).filter(Listing.status == "dryrun").count()
    return {"total": total, "by_site": by_site, "listed": listed, "dryrun": dryrun}
