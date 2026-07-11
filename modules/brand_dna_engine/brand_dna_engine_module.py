from datetime import datetime
from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.brand_dna_engine.brand_dna_history import BrandDNAHistory
from modules.brand_dna_engine.brand_dna_interface import BrandDNAInterface
from modules.brand_dna_engine.brand_dna_storage import BrandDNAStorage
from modules.brand_dna_engine.brand_dna_tracker import BrandDNATracker
from modules.brand_dna_engine.brand_profile_loader import BrandProfileLoader
from modules.competitor_learning.competitor_learning_interface import CompetitorLearningInterface


class BrandDNAEngineModule(BaseModule):
    """
    Brand DNA Engine v1.

    config/brand_profile.json(톤/금칙어/타깃)에 더해, 실제 실행마다 사용된
    hook_type/cta_type/layout_type/highlight_color를 누적 관찰해 "이 브랜드가
    실제로 반복해서 사용하는 톤/색상/레이아웃/CTA/Hook"을 storage/brand_dna/에 쌓는다.

    이 Engine은 외부 네트워크/LLM을 호출하지 않으며, 계산 실패 시 브랜드 프로필만
    포함한 안전한 기본 결과를 반환한다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.profile_loader = BrandProfileLoader()
        self.tracker = BrandDNATracker(self.config)
        self.storage = BrandDNAStorage()
        self.history = BrandDNAHistory()
        self.interface = BrandDNAInterface(self.storage)

        # Competitor Learning Interface 연결(Sprint 18): 우리 브랜드 자신의
        # dominant_hook_type/dominant_cta_type/dominant_layout_type 계산 로직은
        # 전혀 건드리지 않고, Instagram Research로 관찰한 "계정별(경쟁 계정)"
        # hook/cta/pattern/layout 통계를 참고 정보로만 덧붙인다.
        self.competitor_learning_interface = CompetitorLearningInterface()

    def run(
        self,
        pattern_result: Optional[Dict[str, Any]] = None,
        content_result: Optional[Dict[str, Any]] = None,
        card_news_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Brand DNA Engine Module Started")

        try:
            result = self._build_result(pattern_result or {}, content_result or {}, card_news_result or {})
        except Exception as error:
            print(f"Brand DNA Engine Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"brand_dna_exception: {error}")

        print("Brand DNA Engine Module Finished")
        return result

    def _build_result(
        self,
        pattern_result: Dict[str, Any],
        content_result: Dict[str, Any],
        card_news_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        brand_profile = self.profile_loader.load()

        pattern_plan = pattern_result.get("pattern_plan") or {}
        layout_result = card_news_result.get("layout_result") or {}
        content_intelligence = content_result.get("content_intelligence") or {}
        brand_rule_passed = bool(content_intelligence.get("brand_rule_passed", True))

        # Self Reference Guard (Sprint 16-0): 이번 실행의 pattern_type/hook_type/
        # cta_type이 AI Planner Hint로 대체된 결과였는지 확인한다
        # (PatternEngineModule.planner_consumption.pattern.planner_applied, Sprint
        # 15-3에서 실제로 기록되기 시작한 필드). 이 관찰이 "독립적인 실제 브랜드
        # 사용 패턴"인지 "Planner 자신이 만든 결과"인지 구분해 tracker에 전달한다.
        planner_consumption = pattern_result.get("planner_consumption") or {}
        planner_influenced = bool((planner_consumption.get("pattern") or {}).get("planner_applied"))

        observation = self.tracker.observe(pattern_plan, layout_result, brand_rule_passed, planner_influenced)

        dna = self.storage.update(brand_profile, observation)
        self.history.record(observation)

        return {
            "status": "brand_dna_updated",
            "brand_profile": brand_profile,
            "observation": observation,
            "dominant_hook_type": dna.get("dominant_hook_type", ""),
            "dominant_cta_type": dna.get("dominant_cta_type", ""),
            "dominant_layout_type": dna.get("dominant_layout_type", ""),
            "dominant_color": dna.get("dominant_color", ""),
            "total_observations": dna.get("total_observations", 0),
            "competitor_learning_reference": self._build_competitor_learning_reference(),
            "fallback_used": False,
            "created_at": datetime.now().isoformat(),
        }

    def _build_competitor_learning_reference(self) -> Dict[str, Any]:
        """
        Competitor Learning DB 참고(Sprint 18): storage/knowledge/
        competitor_statistics.json(CompetitorLearningModule이 이미 계산/저장한
        계정별 hook/cta/pattern/layout 통계)을 읽기 전용으로 참고만 한다. 이
        Engine 자신의 dominant_* 계산/저장 로직은 전혀 바꾸지 않으며, 이
        메서드는 절대 예외를 던지지 않는다.
        """
        try:
            if not self.competitor_learning_interface.is_available():
                return {"available": False, "account_profiles": {}, "account_count": 0}

            competitor_statistics = self.competitor_learning_interface.get_competitor_statistics()
            accounts = competitor_statistics.get("accounts", {})

            return {
                "available": True,
                "account_profiles": accounts if isinstance(accounts, dict) else {},
                "account_count": competitor_statistics.get("account_count", 0),
            }
        except Exception as error:
            print(f"Brand DNA Competitor Learning Reference Failed: {error}")
            return {"available": False, "account_profiles": {}, "account_count": 0, "reason": str(error)}

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        try:
            brand_profile = self.profile_loader.load()
        except Exception:
            brand_profile = {}

        return {
            "status": "brand_dna_updated",
            "brand_profile": brand_profile,
            "observation": {},
            "dominant_hook_type": "",
            "dominant_cta_type": "",
            "dominant_layout_type": "",
            "dominant_color": "",
            "total_observations": 0,
            "competitor_learning_reference": {"available": False, "account_profiles": {}, "account_count": 0},
            "fallback_used": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }
