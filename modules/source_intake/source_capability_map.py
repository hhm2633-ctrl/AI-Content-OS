"""Source capability map for the Source Intake layer.

Declares, per source, which visible metrics can realistically be expected from
the shallow (list-level) scan, what the access status was at the last manual
check, and which channels the source usually feeds. Collectors must only be
built for sources with access_status == "ok"; blocked sources are recorded so
they never surface as collector failures that could break the workflow.

Config file: config/source_intake_sources.json (in-code fallback below, per
the repo's config convention — a missing/broken config never raises).
"""

import json
import os
from typing import Any, Dict, List, Optional

ACCESS_OK = "ok"
ACCESS_BLOCKED = "blocked"

CONFIG_PATH = os.path.join("config", "source_intake_sources.json")

# Last manual accessibility check: 2026-07-14 (PowerShell Invoke-WebRequest).
DEFAULT_SOURCE_CAPABILITIES: List[Dict[str, Any]] = [
    # --- portal / aggregated news ---
    {"source_id": "naver_news", "url": "https://news.naver.com/", "source_type": "news",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position", "comments"],
     "channel_candidates": ["issue_daily", "dopamine_issue"]},
    {"source_id": "daum_news", "url": "https://news.daum.net/", "source_type": "news",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position", "comments"],
     "channel_candidates": ["issue_daily", "dopamine_issue"]},
    {"source_id": "nate_news_rank", "url": "https://news.nate.com/rank/?mid=n1000", "source_type": "news",
     "access_status": ACCESS_OK, "collector_allowed": True, "allow_live_fetch": True,
     "expected_metrics": ["rank_position", "comments"],
     "channel_candidates": ["issue_daily", "dopamine_issue"]},
    # --- wire services ---
    {"source_id": "yonhap", "url": "https://www.yna.co.kr/", "source_type": "news_wire",
     "access_status": ACCESS_OK, "collector_allowed": True, "allow_live_fetch": True,
     "expected_metrics": ["rank_position"],
     "channel_candidates": ["issue_daily"]},
    {"source_id": "newsis", "url": "https://www.newsis.com/", "source_type": "news_wire",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position"],
     "channel_candidates": ["issue_daily"]},
    {"source_id": "news1", "url": "https://www.news1.kr/", "source_type": "news_wire",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position"],
     "channel_candidates": ["issue_daily"]},
    # --- economy news ---
    {"source_id": "hankyung_economy", "url": "https://www.hankyung.com/economy", "source_type": "news_economy",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position"],
     "channel_candidates": ["issue_daily", "commerce_signal"]},
    {"source_id": "mk_economy", "url": "https://www.mk.co.kr/economy/", "source_type": "news_economy",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position"],
     "channel_candidates": ["issue_daily", "commerce_signal"]},
    {"source_id": "moneytoday", "url": "https://www.mt.co.kr/", "source_type": "news_economy",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position"],
     "channel_candidates": ["issue_daily", "commerce_signal"]},
    {"source_id": "edaily", "url": "https://www.edaily.co.kr/", "source_type": "news_economy",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position"],
     "channel_candidates": ["issue_daily", "commerce_signal"]},
    # --- communities ---
    {"source_id": "nate_pann", "url": "https://pann.nate.com/talk/ranking", "source_type": "community",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position", "views", "comments", "likes"],
     "channel_candidates": ["issue_daily", "love_signal", "dopamine_issue"]},
    {"source_id": "fmkorea", "url": "https://www.fmkorea.com/best", "source_type": "community",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position", "comments", "likes"],
     "channel_candidates": ["issue_daily", "dopamine_issue"]},
    {"source_id": "bobaedream", "url": "https://www.bobaedream.co.kr/list?code=best", "source_type": "community",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position", "views", "comments", "likes"],
     "channel_candidates": ["issue_daily", "dopamine_issue"]},
    {"source_id": "dcinside", "url": "https://www.dcinside.com/", "source_type": "community",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position", "views", "comments", "likes"],
     "channel_candidates": ["dopamine_issue", "issue_daily"]},
    {"source_id": "theqoo", "url": "https://theqoo.net/hot", "source_type": "community",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position", "views", "comments"],
     "channel_candidates": ["love_signal", "style_weather", "dopamine_issue"]},
    {"source_id": "ppomppu", "url": "https://www.ppomppu.co.kr/hot.php", "source_type": "community",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position", "views", "comments", "likes", "dislikes"],
     "channel_candidates": ["commerce_signal", "issue_daily"]},
    {"source_id": "ruliweb", "url": "https://bbs.ruliweb.com/best/humor", "source_type": "community",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position", "views", "comments", "likes"],
     "channel_candidates": ["dopamine_issue"]},
    {"source_id": "dogdrip", "url": "https://www.dogdrip.net/dogdrip", "source_type": "community",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position", "views", "comments", "likes"],
     "channel_candidates": ["dopamine_issue"]},
    # --- Account C fashion / beauty specialist sources ---
    {"source_id": "fashionn", "url": "https://www.fashionn.com/", "source_type": "fashion_editorial",
     "access_status": ACCESS_OK, "collector_allowed": True,
     "expected_metrics": ["rank_position"],
     "channel_candidates": ["style_weather"],
     "signal_scope": "public_editorial_list_order",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "fashion",
     "account_c_source_role": "editorial_information", "topic_selection_role": "primary_editorial",
     "editorial_topic_eligible": True, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "medium",
     "universal_trend_claimed": False},
    {"source_id": "fashionbiz", "url": "https://fashionbiz.co.kr/", "source_type": "fashion_editorial",
     "access_status": ACCESS_OK, "collector_allowed": True, "allow_live_fetch": True,
     "expected_metrics": ["rank_position"], "channel_candidates": ["style_weather"],
     "signal_scope": "public_editorial_list_order",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "fashion",
     "account_c_source_role": "editorial_information", "topic_selection_role": "primary_editorial",
     "editorial_topic_eligible": True, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "low",
     "universal_trend_claimed": False},
    {"source_id": "apparelnews", "url": "https://www.apparelnews.co.kr/", "source_type": "fashion_editorial",
     "access_status": ACCESS_OK, "collector_allowed": True, "allow_live_fetch": True,
     "expected_metrics": ["rank_position"], "channel_candidates": ["style_weather"],
     "signal_scope": "public_editorial_list_order",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "fashion",
     "account_c_source_role": "editorial_information", "topic_selection_role": "primary_editorial",
     "editorial_topic_eligible": True, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "low",
     "universal_trend_claimed": False},
    {"source_id": "beautynury", "url": "https://www.beautynury.com/news/lists/cat/10", "source_type": "beauty_industry_editorial",
     "access_status": ACCESS_BLOCKED, "collector_allowed": False, "allow_live_fetch": False,
     "blocked_reason": "python_tls_handshake_failed_2026_07_16",
     "expected_metrics": ["rank_position"], "channel_candidates": ["style_weather"],
     "signal_scope": "public_editorial_list_order",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "beauty",
     "account_c_source_role": "industry_reference", "topic_selection_role": "supporting_industry",
     "editorial_topic_eligible": False, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "low",
     "universal_trend_claimed": False},
    {"source_id": "cosin", "url": "https://www.cosinkorea.com/news/article_list_all.html", "source_type": "beauty_industry_editorial",
     "access_status": ACCESS_OK, "collector_allowed": True, "allow_live_fetch": True,
     "expected_metrics": ["rank_position"], "channel_candidates": ["style_weather"],
     "signal_scope": "public_editorial_list_order",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "beauty",
     "account_c_source_role": "industry_reference", "topic_selection_role": "supporting_industry",
     "editorial_topic_eligible": False, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "low",
     "universal_trend_claimed": False},
    {"source_id": "allure_beauty", "url": "https://www.allurekorea.com/beauty/", "source_type": "beauty_consumer_editorial",
     "access_status": ACCESS_OK, "collector_allowed": True, "allow_live_fetch": True,
     "expected_metrics": ["rank_position"], "channel_candidates": ["style_weather"],
     "signal_scope": "consumer_beauty_editorial_list_order",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "beauty",
     "account_c_source_role": "consumer_editorial", "topic_selection_role": "primary_consumer_editorial",
     "account_c_audience": "women_general",
     "beauty_topic_categories": ["skincare", "makeup", "hair", "body", "fragrance", "nail", "celebrity_beauty"],
     "editorial_topic_eligible": True, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "medium", "universal_trend_claimed": False},
    {"source_id": "vogue_beauty", "url": "https://www.vogue.co.kr/beauty", "source_type": "beauty_consumer_editorial",
     "access_status": ACCESS_OK, "collector_allowed": True, "allow_live_fetch": True,
     "expected_metrics": ["rank_position"], "channel_candidates": ["style_weather"],
     "signal_scope": "consumer_beauty_editorial_list_order",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "beauty",
     "account_c_source_role": "consumer_editorial", "topic_selection_role": "primary_consumer_editorial",
     "account_c_audience": "women_general",
     "beauty_topic_categories": ["skincare", "makeup", "hair", "body", "fragrance", "nail", "celebrity_beauty"],
     "editorial_topic_eligible": True, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "medium", "universal_trend_claimed": False},
    {"source_id": "wkorea_beauty", "url": "https://www.wkorea.com/beauty/", "source_type": "beauty_consumer_editorial",
     "access_status": ACCESS_OK, "collector_allowed": True, "allow_live_fetch": True,
     "expected_metrics": ["rank_position"], "channel_candidates": ["style_weather"],
     "signal_scope": "consumer_beauty_editorial_list_order",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "beauty",
     "account_c_source_role": "consumer_editorial", "topic_selection_role": "primary_consumer_editorial",
     "account_c_audience": "women_general",
     "beauty_topic_categories": ["skincare", "makeup", "hair", "body", "fragrance", "nail", "celebrity_beauty"],
     "editorial_topic_eligible": True, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "medium", "universal_trend_claimed": False},
    {"source_id": "gq_grooming", "url": "https://www.gqkorea.co.kr/style/grooming/", "source_type": "beauty_consumer_editorial",
     "access_status": ACCESS_OK, "collector_allowed": True, "allow_live_fetch": True,
     "expected_metrics": ["rank_position"], "channel_candidates": ["style_weather"],
     "signal_scope": "consumer_beauty_editorial_list_order",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "beauty",
     "account_c_source_role": "consumer_editorial", "topic_selection_role": "primary_consumer_editorial",
     "account_c_audience": "men",
     "beauty_topic_categories": ["grooming", "skincare", "hair_scalp", "shaving", "body", "fragrance"],
     "editorial_topic_eligible": True, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "medium", "universal_trend_claimed": False},
    {"source_id": "musinsa_monthly_ranking", "url": "https://www.musinsa.com/main/musinsa/ranking", "source_type": "platform_ranking",
     "access_status": ACCESS_BLOCKED, "collector_allowed": False,
     "blocked_reason": "public_shell_without_product_metadata",
     "expected_metrics": ["rank_position"],
     "channel_candidates": ["style_weather"],
     "signal_scope": "platform_specific_monthly_ranking",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "fashion",
     "account_c_source_role": "platform_demand", "topic_selection_role": "supporting_demand",
     "editorial_topic_eligible": False, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "high",
     "universal_trend_claimed": False},
    {"source_id": "oliveyoung_ranking", "url": "https://www.oliveyoung.co.kr/store/main/getBestList.do", "source_type": "retailer_ranking",
     "access_status": ACCESS_BLOCKED, "collector_allowed": False,
     "blocked_reason": "http_403_live_check_2026_07_16",
     "expected_metrics": ["rank_position"],
     "channel_candidates": ["style_weather"],
     "signal_scope": "retailer_specific",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "beauty",
     "account_c_source_role": "retailer_demand", "topic_selection_role": "supporting_retail",
     "editorial_topic_eligible": False, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "high",
     "promotion_sensitive": True,
     "universal_trend_claimed": False},
    {"source_id": "musinsa_boutique", "url": "https://www.musinsa.com/main/boutique", "source_type": "luxury_reference_catalog",
     "access_status": ACCESS_BLOCKED, "collector_allowed": False,
     "blocked_reason": "public_shell_without_product_metadata",
     "expected_metrics": ["rank_position"], "channel_candidates": ["style_weather"],
     "signal_scope": "platform_specific_catalog",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "fashion",
     "account_c_source_role": "luxury_reference", "topic_selection_role": "post_selection_catalog",
     "editorial_topic_eligible": False, "supporting_topic_signal": False,
     "post_selection_only": True, "commercial_influence": "high",
     "universal_trend_claimed": False},
    {"source_id": "musinsa_beauty", "url": "https://www.musinsa.com/main/beauty", "source_type": "beauty_retail_catalog",
     "access_status": ACCESS_BLOCKED, "collector_allowed": False,
     "blocked_reason": "public_shell_without_product_metadata",
     "expected_metrics": ["rank_position"], "channel_candidates": ["style_weather"],
     "signal_scope": "platform_specific_retail",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "beauty",
     "account_c_source_role": "retailer_demand", "topic_selection_role": "supporting_retail",
     "editorial_topic_eligible": False, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "high",
     "promotion_sensitive": True, "universal_trend_claimed": False},
    {"source_id": "glowpick_ranking", "url": "https://www.glowpick.com/products/brand-new", "source_type": "consumer_review_ranking",
     "access_status": ACCESS_BLOCKED, "collector_allowed": False,
     "blocked_reason": "nextjs_stream_without_parseable_product_metadata",
     "expected_metrics": ["rank_position", "rating", "review_count"],
     "channel_candidates": ["style_weather"],
     "signal_scope": "platform_specific_consumer_aggregate",
     "account_portfolio": "account_c_beauty_fashion", "account_c_vertical": "beauty",
     "account_c_source_role": "consumer_review_evidence", "topic_selection_role": "supporting_consumer_evidence",
     "editorial_topic_eligible": False, "supporting_topic_signal": True,
     "post_selection_only": False, "commercial_influence": "medium",
     "promotion_sensitive": True, "experience_review_sensitive": True,
     "universal_trend_claimed": False},
]


class SourceCapabilityMap:
    """Loads config/source_intake_sources.json with an in-code fallback."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or CONFIG_PATH
        self.sources = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        entries = DEFAULT_SOURCE_CAPABILITIES

        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)

                loaded = data.get("sources")
                if isinstance(loaded, list) and loaded:
                    entries = loaded
        except Exception as error:
            print(f"Source Intake Capability Config Load Failed (fallback to defaults): {error}")

        capability_map = {}
        for entry in entries:
            if isinstance(entry, dict) and entry.get("source_id"):
                capability_map[entry["source_id"]] = entry

        return capability_map

    def get(self, source_id: str) -> Dict[str, Any]:
        """Always returns a usable dict, even for unknown sources."""
        entry = self.sources.get(source_id)

        if entry:
            return entry

        return {
            "source_id": source_id,
            "url": "",
            "source_type": "unknown",
            "access_status": ACCESS_BLOCKED,
            "collector_allowed": False,
            "blocked_reason": "unknown_source",
            "expected_metrics": [],
            "channel_candidates": [],
        }

    def is_collector_allowed(self, source_id: str) -> bool:
        entry = self.get(source_id)
        return bool(entry.get("collector_allowed")) and entry.get("access_status") == ACCESS_OK

    def expected_metrics(self, source_id: str) -> List[str]:
        return list(self.get(source_id).get("expected_metrics") or [])

    def channel_candidates(self, source_id: str) -> List[str]:
        return list(self.get(source_id).get("channel_candidates") or [])

    def collectable_sources(self) -> List[Dict[str, Any]]:
        return [
            entry for entry in self.sources.values()
            if bool(entry.get("collector_allowed")) and entry.get("access_status") == ACCESS_OK
        ]

    def blocked_sources(self) -> List[Dict[str, Any]]:
        return [
            entry for entry in self.sources.values()
            if entry.get("access_status") != ACCESS_OK
        ]

    def skip_report(self, source_id: str) -> Dict[str, Any]:
        """Non-fatal skip record for blocked sources (never a workflow failure)."""
        entry = self.get(source_id)

        return {
            "source_id": source_id,
            "attempted": False,
            "success": False,
            "skipped": True,
            "skip_reason": entry.get("blocked_reason", "access_blocked"),
            "access_status": entry.get("access_status", ACCESS_BLOCKED),
            "workflow_impact": "none",
        }
