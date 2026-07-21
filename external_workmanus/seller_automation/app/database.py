"""
데이터베이스 연결 및 초기화 모듈.
- 동기(sync) 엔진을 사용해 단순하고 안정적으로 구성했습니다.
- 최초 실행 시 테이블 생성 및 관리자 비밀번호 기본값을 세팅합니다.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from . import config
from .passwords import hash_password, verify_password
from .models import Base, Setting

engine = create_engine(config.DB_URL_SYNC, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Session:
    """요청마다 DB 세션을 생성/반납하는 의존성."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """테이블 생성 및 기본 설정 초기화."""
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        # 관리자 비밀번호 해시가 없으면 기본값으로 생성
        pw = db.get(Setting, "admin_password_hash")
        if pw is None:
            hashed = hash_password(config.DEFAULT_ADMIN_PASSWORD)
            db.add(Setting(key="admin_password_hash", value=hashed))
            db.commit()
            print("=" * 60)
            print(" [최초 실행] 관리자 비밀번호가 설정되었습니다.")
            print(f"   기본 비밀번호: {config.DEFAULT_ADMIN_PASSWORD}")
            print("   로그인 후 반드시 비밀번호를 변경하세요.")
            print("=" * 60)
    finally:
        db.close()


def verify_admin_password(db: Session, password: str) -> bool:
    rec = db.get(Setting, "admin_password_hash")
    if not rec:
        return False
    return verify_password(password, rec.value)


def set_admin_password(db: Session, new_password: str) -> None:
    rec = db.get(Setting, "admin_password_hash")
    hashed = hash_password(new_password)
    if rec:
        rec.value = hashed
    else:
        db.add(Setting(key="admin_password_hash", value=hashed))
    db.commit()
