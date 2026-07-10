from datetime import datetime
from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.trend_memory.trend_memory_checker import TrendMemoryChecker
from modules.trend_memory.trend_memory_history import TrendMemoryHistory
from modules.trend_memory.trend_memory_interface import TrendMemoryInterface
from modules.trend_memory.trend_memory_storage import TrendMemoryStorage


class TrendMemoryModule(BaseModule):
    """
    Trend Memory v1.

    이번 실행에서 실제로 선택된 Topic/Hook/CTA/Layout/Image 조합을 기록하고, 최근
    실행들과 비교해 topic_repeat_risk 및 요소별 반복 횟수를 계산한다. 생성 자체를
    막지는 않는다(WorkflowEngine 구조 변경 금지) — 반복 위험 신호만 기록해 향후
    Pattern Engine/Topic Engine이 참고할 수 있게 한다.

    이 Engine은 외부 네트워크/LLM을 호출하지 않으며, 검사 실패 시 안전한
    low-risk 기본값을 반환한다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.checker = TrendMemoryChecker(self.config)
        self.storage = TrendMemoryStorage()
        self.history = TrendMemoryHistory()
        self.interface = TrendMemoryInterface(self.storage)

    def run(
        self,
        pattern_result: Optional[Dict[str, Any]] = None,
        card_news_result: Optional[Dict[str, Any]] = None,
        image_strategy_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Trend Memory Module Started")

        try:
            result = self._build_result(pattern_result or {}, card_news_result or {}, image_strategy_result or {})
        except Exception as error:
            print(f"Trend Memory Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"trend_memory_exception: {error}")

        print("Trend Memory Module Finished")
        return result

    def _build_result(
        self,
        pattern_result: Dict[str, Any],
        card_news_result: Dict[str, Any],
        image_strategy_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        selected_topic = pattern_result.get("selected_topic") or {}
        pattern_plan = pattern_result.get("pattern_plan") or {}
        layout_result = card_news_result.get("layout_result") or {}

        current = {
            "topic_title": str(selected_topic.get("title", "")),
            "hook_type": str(pattern_plan.get("hook_type", "")),
            "cta_type": str(pattern_plan.get("cta_type", "")),
            "layout_type": str(layout_result.get("layout_type") or pattern_plan.get("layout_type", "")),
            "image_source": str(image_strategy_result.get("image_source", "")),
        }

        recent_records = self.storage.load_recent(limit=30)
        check_result = self.checker.check(current, recent_records)

        entry = {"recorded_at": datetime.now().isoformat(), **current}
        append_result = self.storage.append(entry)

        self.history.record(check_result)

        return {
            "status": "trend_memory_recorded",
            "current": current,
            "topic_repeat_risk": check_result.get("topic_repeat_risk", "low"),
            "topic_similarity": check_result.get("topic_similarity", 0.0),
            "matched_topic": check_result.get("matched_topic", ""),
            "element_repeat_counts": check_result.get("element_repeat_counts", {}),
            "total_memory_count": append_result.get("total_count", 0),
            "fallback_used": False,
            "created_at": datetime.now().isoformat(),
        }

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        return {
            "status": "trend_memory_recorded",
            "current": {},
            "topic_repeat_risk": "low",
            "topic_similarity": 0.0,
            "matched_topic": "",
            "element_repeat_counts": {},
            "total_memory_count": 0,
            "fallback_used": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }
