from datetime import datetime
from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.brand_dna_engine.brand_dna_history import BrandDNAHistory
from modules.brand_dna_engine.brand_dna_interface import BrandDNAInterface
from modules.brand_dna_engine.brand_dna_storage import BrandDNAStorage
from modules.brand_dna_engine.brand_dna_tracker import BrandDNATracker
from modules.brand_dna_engine.brand_profile_loader import BrandProfileLoader


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

        observation = self.tracker.observe(pattern_plan, layout_result, brand_rule_passed)

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
            "fallback_used": False,
            "created_at": datetime.now().isoformat(),
        }

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
            "fallback_used": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }
