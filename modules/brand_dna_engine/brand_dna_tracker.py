import json
from pathlib import Path
from typing import Any, Dict, Optional


class BrandDNATracker(object):
    """
    Brand DNA Engine - Core.

    실행마다 실제로 사용된 hook_type/cta_type/layout_type과 그 layout의
    highlight_color(templates/card_news_layout_rules.json, 읽기 전용)를 관찈해
    "이 브랜드가 실제로 어떤 톤/색상/레이아웃/CTA/Hook을 반복해서 쓰고 있는지"를
    누적 집계한다.

    layout_rules 파일이 없거나 손상되어도 예외를 던지지 않고 색상 정보 없이
    집계를 계속한다.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        layout_rules_path: Optional[Path] = None,
    ):
        self.config = config or {}
        self.layout_rules_path = layout_rules_path or Path("templates/card_news_layout_rules.json")

    def observe(
        self,
        pattern_plan: Dict[str, Any],
        layout_result: Dict[str, Any],
        brand_rule_passed: bool,
        planner_influenced: bool = False,
    ) -> Dict[str, Any]:
        layout_type = str(layout_result.get("layout_type") or pattern_plan.get("layout_type", "") or "")
        highlight_color = self._lookup_highlight_color(layout_type)

        return {
            "hook_type": str(pattern_plan.get("hook_type", "") or ""),
            "cta_type": str(pattern_plan.get("cta_type", "") or ""),
            "layout_type": layout_type,
            "highlight_color": highlight_color,
            "brand_rule_passed": bool(brand_rule_passed),
            # Self Reference Guard (Sprint 16-0): 이번 실행의 pattern_type이 AI
            # Planner Hint로 대체된 결과라면(PatternEngineModule.planner_consumption.
            # pattern.planner_applied), 여기서 관찰하는 hook_type/cta_type도
            # 간접적으로 Planner의 판단을 반영한 것이다. 이 관찰을 "독립적인
            # 실제 브랜드 사용 패턴"과 구분해서 세도록 표시해 둔다 - 그래야 다음
            # 실행의 Planner가 자신이 만든 결과를 다시 근거로 삼는 것을 막을 수
            # 있다(PlannerDecisionEngine의 override 게이트가 이 값을 사용).
            "planner_influenced": bool(planner_influenced),
        }

    def _lookup_highlight_color(self, layout_type: str) -> str:
        if not layout_type:
            return ""

        rules = self._load_layout_rules()
        layout_entry = rules.get("layouts", {}).get(layout_type, {})

        if isinstance(layout_entry, dict):
            return str(layout_entry.get("highlight_color", ""))

        return ""

    def _load_layout_rules(self) -> Dict[str, Any]:
        if not self.layout_rules_path.exists():
            return {}

        try:
            with open(self.layout_rules_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return {}
