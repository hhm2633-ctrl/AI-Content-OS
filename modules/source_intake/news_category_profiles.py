"""News category profiles for the Source Intake layer (V1).

Instead of growing Source Intake into a monolithic engine, this layer splits
news collection into small, independently runnable category profiles
(domestic / incident / entertainment / world / economy / society-policy).
A run only collects the profiles it actually needs ("selective mode") rather
than scanning every source every time.

Contracts (aligned with the repo's fallback-first rules):
- Every profile is shallow-first: ``scan_depth`` is always ``"shallow"`` and
  deep dives are never auto-triggered by this layer (``deep_dive_auto`` is
  always False). A deep dive is a separate, explicit decision downstream.
- Unknown profile ids fail closed: they never raise into the workflow. They
  are recorded under ``unknown_profiles`` and contribute nothing to the plan.
- Sources that the SourceCapabilityMap marks as blocked or
  collector_allowed=false are automatically excluded from collection plans
  and recorded under ``excluded_sources``.
- An empty plan is a valid plan: the caller keeps running with zero sources
  rather than failing the workflow.

Config file: config/news_category_profiles.json (in-code fallback below, per
the repo's config convention — a missing/broken config never raises).
"""

import json
import os
from typing import Any, Dict, List, Optional

from modules.source_intake.source_capability_map import SourceCapabilityMap

CONFIG_PATH = os.path.join("config", "news_category_profiles.json")

SCAN_DEPTH_SHALLOW = "shallow"

DEFAULT_NEWS_CATEGORY_PROFILES: List[Dict[str, Any]] = [
    {
        "profile_id": "domestic_news",
        "purpose": "한국 오늘 주요뉴스/포털 반복 확인",
        "sources": ["naver_news", "daum_news", "nate_news_rank"],
        "channels": ["issue_daily"],
        "risk_flags": [],
        "scan_depth": SCAN_DEPTH_SHALLOW,
        "deep_dive_auto": False,
        "notes": "portal-news centric; the default everyday profile",
    },
    {
        "profile_id": "incident_accident",
        "purpose": "사건/사고/재난/민폐/갑질/분쟁성 이슈",
        "sources": [
            "naver_news", "daum_news", "nate_news_rank",
            "yonhap", "newsis", "news1",
            "bobaedream", "fmkorea",
        ],
        "channels": ["issue_daily", "dopamine_issue"],
        "risk_flags": ["privacy", "defamation", "crime_claim", "graphic_incident"],
        "scan_depth": SCAN_DEPTH_SHALLOW,
        "deep_dive_auto": False,
        "notes": "news-first with community sources as secondary signal",
    },
    {
        "profile_id": "entertainment_news",
        "purpose": "연예/셀럽/방송/아이돌 이슈. 관계/연애 계정 후보 보조.",
        "sources": ["nate_news_rank", "naver_news", "daum_news", "theqoo", "dcinside"],
        "channels": ["love_signal", "dopamine_issue"],
        "risk_flags": ["privacy", "rumor", "minor", "harassment"],
        "scan_depth": SCAN_DEPTH_SHALLOW,
        "deep_dive_auto": False,
        "notes": "rumor/minor risks require compliance review downstream",
    },
    {
        "profile_id": "world_news",
        "purpose": "국제/전쟁/외교/재난/글로벌 이슈",
        "sources": [
            "naver_news", "daum_news", "nate_news_rank",
            "yonhap", "newsis", "news1",
        ],
        "channels": ["issue_daily"],
        "risk_flags": ["war", "death", "graphic_incident", "geopolitical_claim"],
        "scan_depth": SCAN_DEPTH_SHALLOW,
        "deep_dive_auto": False,
        "notes": "Korean portal and wire sources provide international-news coverage",
    },
    {
        "profile_id": "economy_news",
        "purpose": "금리/부동산/환율/물가/기업/시장/정책",
        "sources": [
            "hankyung_economy", "mk_economy", "moneytoday", "edaily",
            "naver_news", "daum_news",
        ],
        "channels": ["issue_daily", "commerce_signal"],
        "risk_flags": ["investment_advice", "price_prediction", "financial_claim"],
        "scan_depth": SCAN_DEPTH_SHALLOW,
        "deep_dive_auto": False,
        "notes": "commerce_signal only — this profile never produces commerce detail pages",
    },
    {
        "profile_id": "society_policy",
        "purpose": "정부정책/복지/노동/교육/법안/제도 변화",
        "sources": ["naver_news", "daum_news", "yonhap", "newsis", "news1"],
        "channels": ["issue_daily"],
        "risk_flags": ["political_persuasion", "policy_misread", "legal_claim"],
        "scan_depth": SCAN_DEPTH_SHALLOW,
        "deep_dive_auto": False,
        "notes": "official/wire sources (yonhap/newsis/news1) preferred over community",
    },
]


class NewsCategoryProfiles:
    """Category-profile registry + selective collection planner.

    Selective mode: callers pass only the profile ids they need to
    ``build_collection_plan`` instead of collecting every source every run.
    """

    def __init__(self, config_path: Optional[str] = None,
                 capability_map: Optional[SourceCapabilityMap] = None):
        self.config_path = config_path or CONFIG_PATH
        self.capability_map = capability_map or SourceCapabilityMap()
        self.profiles = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        entries = DEFAULT_NEWS_CATEGORY_PROFILES

        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)

                loaded = data.get("profiles")
                if isinstance(loaded, list) and loaded:
                    entries = loaded
        except Exception as error:
            print(f"News Category Profiles Config Load Failed (fallback to defaults): {error}")

        profile_map = {}
        for entry in entries:
            if isinstance(entry, dict) and entry.get("profile_id"):
                normalized = dict(entry)
                # Shallow-first invariant: never let config re-enable auto deep dives.
                normalized["scan_depth"] = SCAN_DEPTH_SHALLOW
                normalized["deep_dive_auto"] = False
                profile_map[normalized["profile_id"]] = normalized

        return profile_map

    def list_profiles(self) -> List[str]:
        return list(self.profiles.keys())

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Fail-closed: unknown ids return None, never raise."""
        return self.profiles.get(profile_id)

    def sources_for(self, profile_id: str) -> List[str]:
        profile = self.get_profile(profile_id)
        if not profile:
            return []
        return list(profile.get("sources") or [])

    def channels_for(self, profile_id: str) -> List[str]:
        profile = self.get_profile(profile_id)
        if not profile:
            return []
        return list(profile.get("channels") or [])

    def risk_flags_for(self, profile_id: str) -> List[str]:
        profile = self.get_profile(profile_id)
        if not profile:
            return []
        return list(profile.get("risk_flags") or [])

    def build_collection_plan(self, profile_ids: List[str]) -> Dict[str, Any]:
        """Build a deduplicated, capability-filtered collection plan.

        - Duplicate sources across profiles are collected once.
        - Sources with collector_allowed=false or access_status != ok are
          excluded (recorded, never a failure).
        - Unknown profile ids are recorded under unknown_profiles and skipped
          (fail-closed, workflow keeps running).
        - Empty input or all-unknown input yields an empty plan with
          status "empty_plan", not an exception.
        """
        selected_sources: List[str] = []
        seen_sources = set()
        excluded_sources: List[Dict[str, Any]] = []
        excluded_seen = set()
        unknown_profiles: List[str] = []
        profile_plans: List[Dict[str, Any]] = []

        for profile_id in list(profile_ids or []):
            profile = self.get_profile(profile_id)
            if not profile:
                unknown_profiles.append(profile_id)
                continue

            profile_selected: List[str] = []
            for source_id in profile.get("sources") or []:
                if self.capability_map.is_collector_allowed(source_id):
                    profile_selected.append(source_id)
                    if source_id not in seen_sources:
                        seen_sources.add(source_id)
                        selected_sources.append(source_id)
                elif source_id not in excluded_seen:
                    excluded_seen.add(source_id)
                    excluded_sources.append(self.capability_map.skip_report(source_id))

            profile_plans.append({
                "profile_id": profile_id,
                "selected_sources": profile_selected,
                "channels": list(profile.get("channels") or []),
                "risk_flags": list(profile.get("risk_flags") or []),
                "scan_depth": SCAN_DEPTH_SHALLOW,
                "deep_dive_auto": False,
            })

        return {
            "schema_version": "news_category_collection_plan_v1",
            "mode": "selective",
            "scan_depth": SCAN_DEPTH_SHALLOW,
            "deep_dive_auto": False,
            "requested_profiles": list(profile_ids or []),
            "profiles": profile_plans,
            "sources": selected_sources,
            "excluded_sources": excluded_sources,
            "unknown_profiles": unknown_profiles,
            "status": "ok" if selected_sources else "empty_plan",
            "workflow_impact": "none",
        }
