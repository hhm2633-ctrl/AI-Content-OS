"""
데이터베이스 모델 정의 (SQLAlchemy ORM)
- Device: 접속을 시도한 기기 정보 및 승인 상태
- Setting: 관리자 비밀번호 등 시스템 설정 (key-value)
- Product: 수집된 상품 (STEP 4에서 본격 사용)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Device(Base):
    """접속 기기 정보. 승인된 기기만 시스템 사용이 가능합니다."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 브라우저에 발급한 고유 기기 식별 토큰 (쿠키에 저장됨)
    device_token = Column(String(64), unique=True, index=True, nullable=False)
    # 사용자가 알아보기 쉽게 붙이는 별칭 (예: "내 노트북", "갤럭시폰")
    label = Column(String(120), default="")
    # 최초 접속 시의 IP / User-Agent (식별 참고용)
    first_ip = Column(String(64), default="")
    user_agent = Column(String(400), default="")
    # 승인 상태: False면 대기/차단, True면 사용 가능
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    """시스템 설정 저장용 key-value 테이블."""
    __tablename__ = "settings"

    key = Column(String(80), primary_key=True)
    value = Column(Text, default="")


class Product(Base):
    """수집된 상품 정보 (STEP 4 크롤링 모듈에서 채워집니다)."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_site = Column(String(40), index=True)        # luckyfresh / econfarm / choigozip
    source_product_id = Column(String(120), index=True)  # 도매처 상품 코드
    title = Column(String(500), default="")
    prefix_name = Column(String(200), default="")        # 말머리(특가/신규 등)
    price = Column(Integer, default=0)                   # 대표 도매가(최저가, 원)
    min_price = Column(Integer, default=0)
    max_price = Column(Integer, default=0)
    origin = Column(String(120), default="")             # 원산지
    thumbnail_url = Column(String(800), default="")
    options_json = Column(Text, default="")              # 옵션 정보 JSON
    images_json = Column(Text, default="")               # 이미지 URL 목록 JSON
    detail_html = Column(Text, default="")               # 상세 설명 HTML
    raw_json = Column(Text, default="")                  # 원본 응답 보관
    status = Column(String(20), default="collected")     # collected/processed/listed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SiteCredential(Base):
    """도매 사이트 로그인 계정 (로컬 DB에 보관, 비밀번호는 암호화 저장)."""
    __tablename__ = "site_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site = Column(String(40), unique=True, index=True)   # luckyfresh/econfarm/choigozip
    username = Column(String(200), default="")
    password_enc = Column(Text, default="")              # 암호화된 비밀번호
    enabled = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    note = Column(String(300), default="")


class MarketCredential(Base):
    """마켓(네이버/쿠팡/지마켓/토스) API 키 저장 (로컬 DB, 시크릿은 암호화)."""
    __tablename__ = "market_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(40), unique=True, index=True)   # naver/coupang/gmarket/toss
    client_id = Column(String(300), default="")
    client_secret_enc = Column(Text, default="")           # 암호화된 시크릿
    extra_json = Column(Text, default="")                  # 마켓별 추가 설정(JSON)
    enabled = Column(Boolean, default=True)
    note = Column(String(300), default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Listing(Base):
    """상품을 마켓에 등록한 이력."""
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, index=True)
    market = Column(String(40), index=True)                # naver/...
    market_product_no = Column(String(120), default="")    # 마켓에서 발급한 상품번호
    sale_price = Column(Integer, default=0)
    status = Column(String(20), default="pending")         # pending/success/failed/dryrun
    message = Column(Text, default="")                     # 결과 메시지/오류
    payload_json = Column(Text, default="")                # 전송한 payload 보관
    created_at = Column(DateTime, default=datetime.utcnow)


class ProcessingProfile(Base):
    """가공 설정(마진율/말머리/금지어 등) 저장."""
    __tablename__ = "processing_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(80), default="기본")
    margin_rate = Column(Integer, default=30)              # % 단위
    payment_fee_rate = Column(Integer, default=4)          # % 단위
    round_unit = Column(Integer, default=100)
    min_price = Column(Integer, default=0)
    prefix = Column(String(200), default="")
    suffix = Column(String(200), default="")
    banned_words = Column(Text, default="")               # 콤마 구분
    default_stock = Column(Integer, default=200)
    is_default = Column(Boolean, default=True)
