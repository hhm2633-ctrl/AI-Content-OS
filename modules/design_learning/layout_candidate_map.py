from typing import Tuple

from modules.card_news.layout_rule_engine import LayoutRuleEngine


def known_layout_ids() -> Tuple[str, ...]:
    """Single source of truth for the 10 existing CardNews layout IDs.

    Reads from LayoutRuleEngine so design_learning never maintains its own
    copy of the layout list and can't drift from modules/card_news.
    """
    try:
        layouts = tuple(LayoutRuleEngine().supported_layouts())
        return layouts if layouts else tuple(LayoutRuleEngine.FALLBACK_RULES.keys())
    except Exception:
        return tuple(LayoutRuleEngine.FALLBACK_RULES.keys())
