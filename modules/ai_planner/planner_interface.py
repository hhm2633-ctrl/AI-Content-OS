import json
from pathlib import Path
from typing import Any, Dict, Optional

from modules.ai_planner.planner_contract import PlannerContract
from modules.brand_dna_engine.brand_dna_interface import BrandDNAInterface
from modules.brand_dna_engine.brand_profile_loader import BrandProfileLoader
from modules.competitor_engine.competitor_interface import CompetitorInterface
from modules.knowledge_engine.knowledge_interface import KnowledgeInterface
from modules.performance_score.performance_score_interface import PerformanceScoreInterface
from modules.trend_memory.trend_memory_interface import TrendMemoryInterface


class PlannerInterface(object):
    """
    AI Planner - Interface (Sprint 15-0, Architecture Only; extended Sprint 15-0A).

    다른 Engine/향후 Sprint/Codex 검수가 AI Planner의 계약과(존재한다면) 최신
    결과를 조회할 수 있도록 준비하는 읽기 전용 API.

    Sprint 15-0에는 실제 Decision Engine이 없고 별도의 Storage 클래스도 없으므로
    (PlannerModule은 아무것도 저장하지 않는 Skeleton이다), `get_latest_result()`는
    지금은 사실상 항상 빈 dict를 반환한다 - 이는 버그가 아니라 "아직 결정된 것이
    없다"는 정직한 상태다. 향후 Sprint가 실제 Storage를 추가하면 이 메서드는
    코드 변경 없이 그 결과를 읽어오기 시작한다.

    Sprint 15-0A에서 `load_historical_inputs()`를 추가했다: 이는 판단/선택 로직이
    아니라 순수 읽기 전용 데이터 조회다 - 이미 존재하는 각 Engine의 Interface
    (`KnowledgeInterface`, `TrendMemoryInterface`, `CompetitorInterface`,
    `BrandDNAInterface`, `PerformanceScoreInterface`)를 그대로 재사용해
    `PlanningContext`의 Historical Input 5종을 채운다. 새로운 저장 구조를 만들지
    않으며, 각 Engine이 이미 `storage/`에 쌓아 둔 실제 데이터만 읽는다. 이 Engine들이
    `modules/ai_planner/`를 import하지 않으므로 순환 의존성은 없다.

    `load_brand_profile()`도 Sprint 15-0A에서 추가했다 (Codex 검수 지적 반영):
    Runtime Input 중 `brand_profile`은 `trend_result`/`topic_result`와 달리
    `WorkflowEngine.run()`의 이전 단계 결과가 아니라 `config/brand_profile.json`
    정적 설정이다. Brand DNA Engine이 이미 사용하는
    `BrandProfileLoader`(`modules/brand_dna_engine/brand_profile_loader.py`)를
    그대로 재사용해 읽으며, 새로운 로더나 저장 구조를 만들지 않는다.

    모든 메서드는 예외를 던지지 않고 안전한 기본값을 반환한다.
    """

    def __init__(self, result_path: Optional[Path] = None):
        self.result_path = Path(result_path) if result_path else Path("storage/planner/planner_result.json")

        self.knowledge_interface = KnowledgeInterface()
        self.trend_memory_interface = TrendMemoryInterface()
        self.competitor_interface = CompetitorInterface()
        self.brand_dna_interface = BrandDNAInterface()
        self.performance_score_interface = PerformanceScoreInterface()
        self.brand_profile_loader = BrandProfileLoader()

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

    def load_historical_inputs(self) -> Dict[str, Any]:
        """
        `PlannerContract.HISTORICAL_INPUT_FIELDS` 5종을 실제 storage에서 읽어
        채운다. 각 항목은 이미 구현된 다른 Engine의 Interface를 통해서만 읽으며,
        여기서 새로운 판단/집계 로직을 추가하지 않는다 - 순수 읽기 전용 조회다.

        어떤 Engine의 Interface 호출이 실패해도 그 항목만 빈 dict로 처리하고
        나머지는 계속 진행한다 - 하나의 실패가 전체를 막지 않는다.
        """
        return {
            "knowledge_history": self._safe_load(self.knowledge_interface.get_statistics),
            "trend_memory_history": self._safe_load(
                lambda: {"recent": self.trend_memory_interface.get_recent(limit=10)}
            ),
            "competitor_history": self._safe_load(
                lambda: {
                    "account_profiles": self.competitor_interface.get_account_profiles(),
                    "statistics": self.competitor_interface.get_statistics(),
                }
            ),
            "brand_dna_history": self._safe_load(self.brand_dna_interface.get_dna),
            "performance_history": self._safe_load(self.performance_score_interface.get_statistics),
        }

    def load_brand_profile(self) -> Dict[str, Any]:
        """
        Runtime Input `brand_profile`을 위한 명시적 로더. `trend_result`/
        `topic_result`와 달리 이전 WorkflowEngine 단계의 결과가 아니라
        `config/brand_profile.json` 설정값이므로, 별도 메서드로 그 출처를
        명확히 한다. `BrandProfileLoader`는 파일이 없거나 손상되어도 예외 없이
        안전한 기본 프로필을 반환한다.
        """
        try:
            result = self.brand_profile_loader.load()
            return result if isinstance(result, dict) else {}
        except Exception as error:
            print(f"Planner Interface load_brand_profile Failed: {error}")
            return {}

    def _safe_load(self, loader) -> Dict[str, Any]:
        try:
            result = loader()
            return result if isinstance(result, dict) else {}
        except Exception as error:
            print(f"Planner Interface load_historical_inputs Failed: {error}")
            return {}
