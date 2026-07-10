from typing import Any, Dict, Optional

from modules.brand_dna_engine.brand_dna_storage import BrandDNAStorage


class BrandDNAInterface(object):
    """
    Brand DNA Engine - Interface.

    Pattern Engine/Content/CardNews가 향후 "이 브랜드가 실제로 선호하는
    hook/cta/layout/color"를 조회할 수 있는 읽기 전용 API. 실패 시 빈 dict를 반환한다.
    """

    def __init__(self, storage: Optional[BrandDNAStorage] = None):
        self.storage = storage or BrandDNAStorage()

    def get_dna(self) -> Dict[str, Any]:
        try:
            return self.storage.load()
        except Exception as error:
            print(f"Brand DNA Interface get_dna Failed: {error}")
            return {}

    def get_dominant_preferences(self) -> Dict[str, str]:
        try:
            dna = self.storage.load()
            return {
                "hook_type": dna.get("dominant_hook_type", ""),
                "cta_type": dna.get("dominant_cta_type", ""),
                "layout_type": dna.get("dominant_layout_type", ""),
                "color": dna.get("dominant_color", ""),
            }
        except Exception as error:
            print(f"Brand DNA Interface get_dominant_preferences Failed: {error}")
            return {"hook_type": "", "cta_type": "", "layout_type": "", "color": ""}

    def get_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_statistics()
        except Exception as error:
            print(f"Brand DNA Interface get_statistics Failed: {error}")
            return {}
