from typing import Any, Dict, List, Optional


class CompetitorProfileBuilder(object):
    """
    Competitor Engine - Profile Builder (Sprint 13).

    InstagramBenchmarkParser가 추출한 계정별 신호를
    "account/hook/pattern/layout/cta/image_strategy/priority" 스키마로 정규화한다.
    실제 계정 데이터가 아니라 이미 분석된 benchmark 문서 기반 신호이므로,
    없는 값은 빈 값 그대로 남기고(추측으로 채우지 않음) 실패해도 빈 리스트를 반환한다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def build(self, instagram_accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            return [self._build_profile(account) for account in instagram_accounts or []]
        except Exception as error:
            print(f"Competitor Profile Builder Failed: {error}")
            return []

    def _build_profile(self, account: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "account": account.get("account", ""),
            "category": account.get("category", ""),
            "hook": account.get("hook_signals", []),
            "pattern": account.get("pattern_signal", ""),
            "layout": account.get("layout_signal", ""),
            "cta": account.get("cta_signals", []),
            "image_strategy": account.get("image_strategy_signal", ""),
            "priority": account.get("priority", ""),
            "ai_content_os_applications": account.get("ai_content_os_applications", []),
        }
