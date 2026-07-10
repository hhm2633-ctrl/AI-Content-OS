import json
from pathlib import Path
from typing import Any, Dict, Optional

from modules.ai_planner.planner_contract import PlannerContract


class PlannerInterface(object):
    """
    AI Planner - Interface (Sprint 15-0, Architecture Only).

    다른 Engine/향후 Sprint/Codex 검수가 AI Planner의 계약과(존재한다면) 최신
    결과를 조회할 수 있도록 준비하는 읽기 전용 API.

    Sprint 15-0에는 실제 Decision Engine이 없고 별도의 Storage 클래스도 없으므로
    (PlannerModule은 아무것도 저장하지 않는 Skeleton이다), `get_latest_result()`는
    지금은 사실상 항상 빈 dict를 반환한다 - 이는 버그가 아니라 "아직 결정된 것이
    없다"는 정직한 상태다. 향후 Sprint가 실제 Storage를 추가하면 이 메서드는
    코드 변경 없이 그 결과를 읽어오기 시작한다.

    모든 메서드는 예외를 던지지 않고 안전한 기본값을 반환한다.
    """

    def __init__(self, result_path: Optional[Path] = None):
        self.result_path = Path(result_path) if result_path else Path("storage/planner/planner_result.json")

    def get_latest_result(self) -> Dict[str, Any]:
        try:
            if not self.result_path.exists():
                return {}

            with open(self.result_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception as error:
            print(f"Planner Interface get_latest_result Failed: {error}")

        return {}

    def get_contract(self) -> Dict[str, Any]:
        try:
            return PlannerContract.describe()
        except Exception as error:
            print(f"Planner Interface get_contract Failed: {error}")
            return {}
