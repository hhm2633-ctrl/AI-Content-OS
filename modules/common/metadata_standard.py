from datetime import datetime
from typing import Any, Dict, Optional

METADATA_VERSION = "1.0"

# 값의 실제 출처를 구분하는 표준 어휘 (Sprint 16-0, Intelligence Feedback Safety).
# 어떤 Engine이든 새 이름을 만들지 않고 이 네 가지만 재사용한다:
#
# - "runtime": 이번 실행의 실제 입력(trend/topic/content 등)에서 직접 가져온 값.
# - "historical": storage/에 누적된 과거 실행 데이터에서 읽은 값.
# - "estimated": runtime/historical 값을 바탕으로 추세/우선순위 등을 추론한
#   값 - 실측이 아님을 명시한다.
# - "local_quality": 실제 외부 성과 지표(조회수/저장수 등)가 아니라 로컬에서
#   계산한 내부 품질 대리 지표(Performance/Audit/Learning Score 등). 진짜
#   실측처럼 보이지 않도록 항상 이 이름으로 구분한다.
SOURCE_RUNTIME = "runtime"
SOURCE_HISTORICAL = "historical"
SOURCE_ESTIMATED = "estimated"
SOURCE_LOCAL_QUALITY = "local_quality"

VALID_SOURCES = {SOURCE_RUNTIME, SOURCE_HISTORICAL, SOURCE_ESTIMATED, SOURCE_LOCAL_QUALITY}


def build_standard_metadata(
    source: str,
    confidence: Optional[float] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """
    AI-Content-OS 공통 Metadata 표준 (Sprint 16-0).

    Analytics/Performance Score/Content 등 여러 Engine이 각자 다른 모양의
    진단 dict를 새로 만드는 대신 이 표준(`metadata_version`/`source`/
    `confidence`/`generated_at`)을 재사용해 "중복 구조"를 줄인다. 판단 로직이
    없는 순수 포맷팅 헬퍼이며 예외를 던지지 않는다.

    `source`가 `VALID_SOURCES`에 없어도 예외를 던지지 않고 그대로 기록한다
    (이 함수는 값을 검열하지 않는다 - 호출자가 올바른 source를 고르는 책임을
    진다). 실제 실패(예: `extra`에 dict로 병합할 수 없는 값)는 안전한 최소
    dict로 대체한다.
    """
    try:
        metadata: Dict[str, Any] = {
            "metadata_version": METADATA_VERSION,
            "source": str(source) if source is not None else "unknown",
            "confidence": confidence,
            "generated_at": datetime.now().isoformat(),
        }
        metadata.update(extra or {})
        return metadata
    except Exception as error:
        return {
            "metadata_version": METADATA_VERSION,
            "source": "unknown",
            "confidence": None,
            "generated_at": datetime.now().isoformat(),
            "error": f"build_standard_metadata 실패: {error}",
        }
