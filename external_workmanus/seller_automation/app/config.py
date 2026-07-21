"""
애플리케이션 설정 모듈
- 모든 경로/비밀키/기본값을 한 곳에서 관리합니다.
- Windows 11 PC로 옮겨도 그대로 동작하도록 상대 경로 기반으로 구성했습니다.
"""
import os
import secrets
from pathlib import Path

# 프로젝트 루트 (이 파일 기준 상위 2단계: app/ -> seller_automation/)
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# SQLite 데이터베이스 파일 경로
DB_PATH = DATA_DIR / "seller.db"
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"
DB_URL_SYNC = f"sqlite:///{DB_PATH}"

# 세션 서명용 비밀키.
# 최초 1회 자동 생성되어 data/secret.key 에 저장됩니다. (PC 이동 시 그대로 유지)
_SECRET_FILE = DATA_DIR / "secret.key"
if _SECRET_FILE.exists():
    SECRET_KEY = _SECRET_FILE.read_text().strip()
else:
    SECRET_KEY = secrets.token_hex(32)
    _SECRET_FILE.write_text(SECRET_KEY)

# 세션 쿠키 이름 / 유효기간(초)
SESSION_COOKIE = "sa_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12시간

# 서버 바인딩 정보 (로컬 네트워크 전체에 노출하려면 0.0.0.0)
HOST = os.environ.get("SA_HOST", "0.0.0.0")
PORT = int(os.environ.get("SA_PORT", "8000"))

# 관리자 초기 비밀번호 (최초 실행 시 콘솔에 안내, 이후 변경 가능)
DEFAULT_ADMIN_PASSWORD = os.environ.get("SA_ADMIN_PW", "admin1234")

# 신규 기기가 접속했을 때 자동 승인 대기 상태로 등록할지 여부.
# True 이면 관리자가 승인하기 전까지는 접근이 차단됩니다.
REQUIRE_DEVICE_APPROVAL = True
