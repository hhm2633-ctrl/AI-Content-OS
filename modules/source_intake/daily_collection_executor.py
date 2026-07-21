"""Execute shallow collection from a daily source collection plan.

This is still a shallow-first executor, not a deep-dive crawler. It only calls
existing safe TrendSourceManager collectors for sources that already have a
collector implementation and records the rest as skipped.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

from modules.source_intake.daily_collection_plan import build_daily_collection_plan
from modules.source_intake.collection_quality_assessor import assess_collection_quality
from modules.source_intake.source_agreement import build_source_agreement
from modules.source_intake.source_capability_map import SourceCapabilityMap
from modules.source_intake.source_intake_schema import SOURCE_INTAKE_STORAGE_ROOT
from modules.trend_collector.daum_news_collector import DaumNewsCollector
from modules.trend_collector.dcinside_collector import DcinsideCollector
from modules.trend_collector.dogdrip_collector import DogdripCollector
from modules.trend_collector.fashionn_collector import FashionNCollector
from modules.trend_collector.fashionbiz_collector import FashionBizCollector
from modules.trend_collector.apparelnews_collector import ApparelNewsCollector
from modules.trend_collector.beautynury_collector import BeautynuryCollector
from modules.trend_collector.cosin_collector import CosinCollector
from modules.trend_collector.allure_beauty_collector import AllureBeautyCollector
from modules.trend_collector.vogue_beauty_collector import VogueBeautyCollector
from modules.trend_collector.wkorea_beauty_collector import WKoreaBeautyCollector
from modules.trend_collector.gq_grooming_collector import GqGroomingCollector
from modules.trend_collector.glowpick_ranking_collector import GlowpickRankingCollector
from modules.trend_collector.musinsa_beauty_collector import MusinsaBeautyCollector
from modules.trend_collector.musinsa_boutique_collector import MusinsaBoutiqueCollector
from modules.trend_collector.musinsa_monthly_ranking_collector import MusinsaMonthlyRankingCollector
from modules.trend_collector.oliveyoung_ranking_collector import OliveYoungRankingCollector
from modules.trend_collector.news1_collector import News1Collector
from modules.trend_collector.newsis_collector import NewsisCollector
from modules.trend_collector.yonhap_collector import YonhapCollector
from modules.trend_collector.nate_news_rank_collector import NateNewsRankCollector
from modules.trend_collector.edaily_collector import EdailyCollector
from modules.trend_collector.theqoo_collector import TheQooCollector
from modules.trend_collector.hankyung_economy_collector import HankyungEconomyCollector
from modules.trend_collector.mk_pick_collector import MkPickCollector
from modules.trend_collector.moneytoday_collector import MoneyTodayCollector
from modules.trend_collector.ppomppu_collector import PpomppuCollector
from modules.trend_collector.ruliweb_collector import RuliwebCollector
from modules.trend_collector.trend_source_manager import TrendSourceManager


COLLECTOR_METHODS = {
    "naver_news": "_collect_naver_news",
    "nate_pann": "_collect_nate_pann",
    "nate_news_rank": "_collect_nate_news_rank",
    "news1": "_collect_news1",
    "newsis": "_collect_newsis",
    "yonhap": "_collect_yonhap",
    "daum_news": "_collect_daum_news",
    "fmkorea": "_collect_fmkorea",
    "bobaedream": "_collect_bobaedream",
    "theqoo": "_collect_theqoo",
    "edaily": "_collect_edaily",
    "hankyung_economy": "_collect_hankyung_economy",
    "mk_economy": "_collect_mk_economy",
    "moneytoday": "_collect_moneytoday",
    "dcinside": "_collect_dcinside",
    "ppomppu": "_collect_ppomppu",
    "ruliweb": "_collect_ruliweb",
    "dogdrip": "_collect_dogdrip",
    "fashionn": "_collect_fashionn",
    "fashionbiz": "_collect_fashionbiz",
    "apparelnews": "_collect_apparelnews",
    "beautynury": "_collect_beautynury",
    "cosin": "_collect_cosin",
    "allure_beauty": "_collect_allure_beauty",
    "vogue_beauty": "_collect_vogue_beauty",
    "wkorea_beauty": "_collect_wkorea_beauty",
    "gq_grooming": "_collect_gq_grooming",
    "glowpick_ranking": "_collect_glowpick_ranking",
    "musinsa_beauty": "_collect_musinsa_beauty",
    "musinsa_boutique": "_collect_musinsa_boutique",
    "musinsa_monthly_ranking": "_collect_musinsa_monthly_ranking",
    "oliveyoung_ranking": "_collect_oliveyoung_ranking",
}
DIRECT_COLLECTOR_FACTORIES = {
    "daum_news": lambda source_entry, config: DaumNewsCollector(),
    "news1": lambda source_entry, config: News1Collector(config=config),
    "mk_economy": lambda source_entry, config: MkPickCollector(config=config),
    "nate_news_rank": lambda source_entry, config: NateNewsRankCollector(
        config={
            **config,
            "live_collection_enabled": bool(source_entry.get("allow_live_fetch", False)),
        }
    ),
    "newsis": lambda source_entry, config: NewsisCollector(config=config),
    "yonhap": lambda source_entry, config: YonhapCollector(
        config={**config, "allow_live_fetch": bool(source_entry.get("allow_live_fetch", False))}
    ),
    "theqoo": lambda source_entry, config: TheQooCollector(config=config),
    "edaily": lambda source_entry, config: EdailyCollector(config=config),
    "hankyung_economy": lambda source_entry, config: HankyungEconomyCollector(config=config),
    "dcinside": lambda source_entry, config: DcinsideCollector(config=config),
    "ppomppu": lambda source_entry, config: PpomppuCollector(config=config),
    "ruliweb": lambda source_entry, config: RuliwebCollector(config=config),
    "dogdrip": lambda source_entry, config: DogdripCollector(config=config),
    "fashionn": lambda source_entry, config: FashionNCollector(config=config),
    "fashionbiz": lambda source_entry, config: FashionBizCollector(
        config={**config, "allow_live_fetch": bool(source_entry.get("allow_live_fetch", False))}
    ),
    "apparelnews": lambda source_entry, config: ApparelNewsCollector(
        config={**config, "allow_live_fetch": bool(source_entry.get("allow_live_fetch", False))}
    ),
    "beautynury": lambda source_entry, config: BeautynuryCollector(
        config={**config, "allow_live_fetch": bool(source_entry.get("allow_live_fetch", False))}
    ),
    "cosin": lambda source_entry, config: CosinCollector(
        config={**config, "allow_live_fetch": bool(source_entry.get("allow_live_fetch", False))}
    ),
    "allure_beauty": lambda source_entry, config: AllureBeautyCollector(
        config={**config, "allow_live_fetch": bool(source_entry.get("allow_live_fetch", False))}
    ),
    "vogue_beauty": lambda source_entry, config: VogueBeautyCollector(
        config={**config, "allow_live_fetch": bool(source_entry.get("allow_live_fetch", False))}
    ),
    "wkorea_beauty": lambda source_entry, config: WKoreaBeautyCollector(
        config={**config, "allow_live_fetch": bool(source_entry.get("allow_live_fetch", False))}
    ),
    "gq_grooming": lambda source_entry, config: GqGroomingCollector(
        config={**config, "allow_live_fetch": bool(source_entry.get("allow_live_fetch", False))}
    ),
    "glowpick_ranking": lambda source_entry, config: GlowpickRankingCollector(config=config),
    "musinsa_beauty": lambda source_entry, config: MusinsaBeautyCollector(config=config),
    "musinsa_boutique": lambda source_entry, config: MusinsaBoutiqueCollector(config=config),
    "musinsa_monthly_ranking": lambda source_entry, config: MusinsaMonthlyRankingCollector(config=config),
    "oliveyoung_ranking": lambda source_entry, config: OliveYoungRankingCollector(config=config),
}

DIRECT_STATUS_FIELDS = (
    "collection_method",
    "failed_reason",
    "fallback_reason",
    "final_error_type",
    "error_message",
    "used_cache",
    "retry_enabled",
    "retry_count",
    "service_diagnostic",
)

# Optional portfolio metadata copied from the source capability contract.
# These fields describe how a source may be used; they do not manufacture a
# trend score or make retailer/catalog items editorial topics by themselves.
SOURCE_ROLE_FIELDS = (
    "account_portfolio",
    "account_c_vertical",
    "account_c_source_role",
    "topic_selection_role",
    "account_c_audience",
    "beauty_topic_categories",
    "editorial_topic_eligible",
    "supporting_topic_signal",
    "post_selection_only",
    "commercial_influence",
)

# Canonical shallow-item schema (additive normalization only). Collectors keep
# their native fields; a missing canonical field is filled from an equivalent
# field already present on the same item, or with an explicit None when the
# value was not observed. Existing keys are never overwritten and values are
# never invented.
ITEM_SCHEMA_VERSION = "shallow_item_canonical_v1"

CANONICAL_FIELD_ALIASES = {
    "title": ("keyword", "headline"),
    "summary": ("snippet",),
    "link": ("url",),
    "url": ("link",),
    "publisher": (),
    "published_at": ("published_date", "published_at_iso"),
    "rank_position": ("rank",),
    "board_or_category": ("category", "board"),
}

ENGAGEMENT_METRIC_ALIASES = {
    "views": (),
    "comments": ("comment_count",),
    "likes": ("recommend_count",),
    "dislikes": (),
}


def _normalize_shallow_item(
    item: Dict[str, Any],
    expected_metrics: List[str],
    collected_at_default: str,
) -> None:
    item.setdefault("collected_at", collected_at_default)

    for canonical, aliases in CANONICAL_FIELD_ALIASES.items():
        if canonical in item:
            continue
        for alias in aliases:
            if alias in item:
                item[canonical] = item[alias]
                break
        else:
            item[canonical] = None

    nested = item.get("visible_metrics")
    nested = nested if isinstance(nested, dict) else None
    observed: Dict[str, Any] = {}
    for canonical, aliases in ENGAGEMENT_METRIC_ALIASES.items():
        if canonical in item:
            observed[canonical] = item[canonical]
            continue
        alias_hit = next((alias for alias in aliases if alias in item), None)
        if alias_hit is not None:
            item[canonical] = item[alias_hit]
            observed[canonical] = item[canonical]
            continue
        if nested is not None and canonical in nested:
            item[canonical] = nested[canonical]
            observed[canonical] = nested[canonical]
            continue
        if canonical in expected_metrics:
            # Expected on this source's list page but not observed in this
            # run: keep it visible as an explicit null, never a fabricated 0.
            item[canonical] = None
            observed[canonical] = None
    if nested is None and observed:
        item["visible_metrics"] = dict(observed)


def _collect_direct(
    source_id: str,
    source_entry: Dict[str, Any],
    config: Dict[str, Any],
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    collector_or_items = DIRECT_COLLECTOR_FACTORIES[source_id](source_entry, config)
    collect_method = getattr(collector_or_items, "collect", None)
    if callable(collect_method):
        items = list(collect_method(source_entry) or [])
        status = getattr(collector_or_items, "last_status", {})
        return items, dict(status) if isinstance(status, dict) else {}

    return list(collector_or_items or []), {}


def _copy_direct_status(result: Dict[str, Any], status: Dict[str, Any]) -> None:
    for field in DIRECT_STATUS_FIELDS:
        if field in status:
            result[field] = status[field]


def _has_manager_collector_method(manager: Any, method_name: str) -> bool:
    method = getattr(manager, method_name, None)
    return callable(method)


def _manager_source_status(manager: Any, source_id: str) -> Dict[str, Any]:
    summaries = getattr(manager, "last_collection_summary", None)
    if not isinstance(summaries, dict):
        return {}
    status = summaries.get(source_id)
    return dict(status) if isinstance(status, dict) else {}


def _coerce_today(today: Optional[Any]) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    if isinstance(today, (datetime, date)):
        return today.isoformat()
    return str(today)


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _source_entry(capability_map: SourceCapabilityMap, source_id: str) -> Dict[str, Any]:
    entry = capability_map.get(source_id) or {}
    return {
        "source_id": source_id,
        "name": entry.get("name", source_id),
        "type": entry.get("source_type", entry.get("type", "unknown")),
        "tier": int(entry.get("tier", 50) or 50),
        "weight": int(entry.get("weight", 0) or 0),
        "url": entry.get("url", ""),
        "allow_live_fetch": bool(entry.get("allow_live_fetch", False)),
    }


def execute_daily_shallow_collection(
    account_profiles: Optional[List[str]] = None,
    today: Optional[Any] = None,
    output_root: Optional[str] = None,
    source_manager: Optional[Any] = None,
    capability_map: Optional[SourceCapabilityMap] = None,
    allow_direct_collectors: bool = False,
) -> Dict[str, Any]:
    """Execute shallow collection for sources supported by existing collectors.

    Unsupported sources are explicitly skipped. Collector exceptions are captured
    per source and never raised to callers.
    """
    today_str = _coerce_today(today)
    base_root = output_root or SOURCE_INTAKE_STORAGE_ROOT
    target_dir = os.path.join(base_root, today_str)
    output_path = os.path.join(target_dir, "daily_shallow_collection.json")

    capabilities = capability_map or SourceCapabilityMap()
    manager = source_manager or TrendSourceManager()
    allow_direct_collectors = allow_direct_collectors or source_manager is None
    plan = build_daily_collection_plan(
        account_profiles=account_profiles,
        source_capabilities=capabilities,
        today=today_str,
    )

    seen_sources = set()
    collected_items: List[Dict[str, Any]] = []
    source_results: List[Dict[str, Any]] = []

    for lane in plan.get("lanes", []):
        lane_id = lane.get("lane_id")
        for source_id in lane.get("shallow_profiles", []):
            if source_id in seen_sources:
                continue
            seen_sources.add(source_id)

            method_name = COLLECTOR_METHODS.get(source_id)
            if not method_name:
                source_results.append({
                    "source_id": source_id,
                    "lane_id": lane_id,
                    "attempted": False,
                    "success": False,
                    "skipped": True,
                    "skip_reason": "collector_not_implemented",
                    "count": 0,
                })
                continue

            try:
                direct_status: Dict[str, Any] = {}
                has_manager_method = _has_manager_collector_method(manager, method_name)
                source_entry = _source_entry(capabilities, source_id)
                manager_config = dict(getattr(manager, "config", {}))

                if has_manager_method:
                    items = list(getattr(manager, method_name)(source_entry) or [])
                    direct_status = _manager_source_status(manager, source_id)
                elif allow_direct_collectors and source_id in DIRECT_COLLECTOR_FACTORIES:
                    items, direct_status = _collect_direct(
                        source_id, source_entry, manager_config
                    )
                else:
                    source_results.append({
                        "source_id": source_id,
                        "lane_id": lane_id,
                        "attempted": False,
                        "success": False,
                        "skipped": True,
                        "skip_reason": "collector_not_implemented",
                        "count": 0,
                    })
                    continue

                expected_metrics = list(
                    (capabilities.get(source_id) or {}).get("expected_metrics") or []
                )
                capability_entry = capabilities.get(source_id) or {}
                normalized_at = datetime.now().isoformat()
                for item in items:
                    item.setdefault("source_id", source_id)
                    item.setdefault("source_lane_id", lane_id)
                    for field in SOURCE_ROLE_FIELDS:
                        if field in capability_entry:
                            item.setdefault(field, capability_entry[field])
                    _normalize_shallow_item(item, expected_metrics, normalized_at)
                collected_items.extend(items)
                source_result = {
                    "source_id": source_id,
                    "lane_id": lane_id,
                    "attempted": True,
                    "success": bool(items),
                    "skipped": False,
                    "count": len(items),
                }
                _copy_direct_status(source_result, direct_status)
                source_results.append(source_result)
            except Exception as error:
                source_results.append({
                    "source_id": source_id,
                    "lane_id": lane_id,
                    "attempted": True,
                    "success": False,
                    "skipped": False,
                    "error": str(error),
                    "count": 0,
                })

    result = {
        "schema_version": "daily_shallow_collection_v1",
        "date": today_str,
        "status": "completed",
        "item_schema": {
            "version": ITEM_SCHEMA_VERSION,
            "canonical_fields": [
                "source_id", "source_lane_id", "title", "summary", "link",
                "url", "publisher", "published_at", "collected_at",
                "rank_position", "board_or_category", "views", "comments",
                "likes", "dislikes", "visible_metrics",
            ],
            "normalization": (
                "missing canonical fields are filled from same-item aliases "
                "or explicit null; observed values are never overwritten or "
                "fabricated; engagement fields appear only when observed or "
                "expected for the source"
            ),
        },
        "plan": plan,
        "source_results": source_results,
        "items": collected_items,
        "item_count": len(collected_items),
        "quality_summary": assess_collection_quality(collected_items, source_results),
        "source_agreement_summary": build_source_agreement(collected_items),
        "output_path": output_path,
    }
    _write_json(output_path, result)
    return result
