from datetime import datetime
from typing import Any, Dict, List, Optional

from modules.base_module import BaseModule
from modules.competitor_engine.benchmark_source import BenchmarkSource
from modules.competitor_engine.community_source import CommunitySource
from modules.competitor_engine.competitor_history import CompetitorHistory
from modules.competitor_engine.competitor_interface import CompetitorInterface
from modules.competitor_engine.competitor_profile_builder import CompetitorProfileBuilder
from modules.competitor_engine.competitor_storage import CompetitorStorage
from modules.competitor_engine.instagram_benchmark_parser import InstagramBenchmarkParser
from modules.competitor_engine.news_source import NewsSource
from modules.competitor_engine.tools_funnel_parser import ToolsFunnelParser


class CompetitorEngineModule(BaseModule):
    """
    Competitor Engine v2 (Sprint 13, Offline-First).

    docs/COMPETITOR_ENGINE.md에서 요구하는 Instagram 분석을 실시간 API/크롤링
    없이, 이미 CTO가 분석해 저장한 `benchmark/*.md` 문서만으로 수행한다:

    - `InstagramBenchmarkParser`: `benchmark/INSTAGRAM_BENCHMARK.md`의 계정별
      섹션(`### 계정명`)을 파싱해 계정별 hook/pattern/layout/cta/image_strategy/
      priority 프로필을 만든다 -> `storage/competitor/competitor_profiles.json`.
    - `ToolsFunnelParser`: `benchmark/TOOLS_AND_FUNNEL_REFERENCES.md`의 도구/퍼널
      참고 자료를 구조화한다.
    - `BenchmarkSource`: `HOOK_LIBRARY.md`/`CTA_LIBRARY.md`/`CONTENT_PATTERNS.md`/
      `AI_CONTENT_STRATEGY.md`의 Hook/CTA/Pattern 섹션을 파싱한다.
    - `CommunitySource`/`NewsSource`: Trend Collector가 이미 수집한
      `storage/trends/trend_result.json`을 재사용한다 (신규 외부 수집 없음).

    실시간 Instagram/Meta API 연동은 Sprint 13 기준 절대 시도하지 않는다
    (ROADMAP.md의 "Requires External API" 섹션 참고). 이 Engine은 원격 API/LLM을
    호출하지 않으며, 개별 소스 실패는 서로 격리되어 하나가 실패해도 나머지는
    계속 수집된다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.benchmark_source = BenchmarkSource(self.config)
        self.community_source = CommunitySource(self.config)
        self.news_source = NewsSource(self.config)
        self.instagram_benchmark_parser = InstagramBenchmarkParser(self.config)
        self.tools_funnel_parser = ToolsFunnelParser(self.config)
        self.profile_builder = CompetitorProfileBuilder(self.config)

        self.storage = CompetitorStorage()
        self.history = CompetitorHistory()
        self.interface = CompetitorInterface(self.storage)

    def run(self) -> Dict[str, Any]:
        print("Competitor Engine Module Started")

        try:
            result = self._build_result()
        except Exception as error:
            print(f"Competitor Engine Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"competitor_engine_exception: {error}")

        print("Competitor Engine Module Finished")
        return result

    def _build_result(self) -> Dict[str, Any]:
        benchmark = self._safe_collect(self.benchmark_source.collect, "benchmark")
        community = self._safe_collect(self.community_source.collect, "community")
        news = self._safe_collect(self.news_source.collect, "news")
        instagram_benchmark = self._safe_collect(self.instagram_benchmark_parser.parse, "instagram_benchmark")
        tools_funnel = self._safe_collect(self.tools_funnel_parser.parse, "tools_funnel")

        hook_sections = [
            section for section in benchmark.get("sections", [])
            if section.get("file") == "HOOK_LIBRARY.md"
        ]
        cta_sections = [
            section for section in benchmark.get("sections", [])
            if section.get("file") == "CTA_LIBRARY.md"
        ]
        other_pattern_sections = [
            section for section in benchmark.get("sections", [])
            if section.get("file") not in ("HOOK_LIBRARY.md", "CTA_LIBRARY.md")
        ]

        account_profiles = self.profile_builder.build(instagram_benchmark.get("accounts", []))

        profile = {
            "status": "competitor_profile_built",
            "benchmark": benchmark,
            "community": community,
            "news": news,
            "instagram_benchmark": instagram_benchmark,
            "tools_funnel": tools_funnel,
            "account_profiles": account_profiles,
            "hook_and_cta_map": {
                "hook_sections": hook_sections,
                "cta_sections": cta_sections,
            },
            "repeated_content_patterns": other_pattern_sections,
            "format_comparison": self._build_format_comparison(account_profiles),
            "gap_analysis_input": {
                "benchmark_hook_count": len(hook_sections),
                "benchmark_cta_count": len(cta_sections),
                "community_signal_available": community.get("status") == "community_collected",
                "news_signal_available": news.get("status") == "news_collected",
                "account_profile_count": len(account_profiles),
                "high_priority_account_count": sum(
                    1 for item in account_profiles if "high" in str(item.get("priority", "")).lower()
                ),
            },
            "fallback_used": bool(instagram_benchmark.get("fallback_used")) and bool(benchmark.get("fallback_used")),
            "created_at": datetime.now().isoformat(),
        }

        self.storage.save(profile)
        self.storage.save_profiles(account_profiles)
        self.storage.update_statistics(profile, len(account_profiles))
        self.history.record(profile)

        return profile

    def _build_format_comparison(self, account_profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        실제 계정 성과 API 없이, 파싱된 벤치마크 계정 프로필 안에서 layout/cta/
        image_strategy 분포를 실제로 비교한다(가짜 수치 없음 - 문서에 있는
        계정 수만 집계).
        """
        layout_counts: Dict[str, int] = {}
        cta_counts: Dict[str, int] = {}
        image_strategy_counts: Dict[str, int] = {}

        for account_profile in account_profiles:
            layout = account_profile.get("layout") or "unspecified"
            layout_counts[layout] = layout_counts.get(layout, 0) + 1

            for cta in account_profile.get("cta", []) or ["unspecified"]:
                cta_counts[cta] = cta_counts.get(cta, 0) + 1

            image_strategy = account_profile.get("image_strategy") or "unspecified"
            image_strategy_counts[image_strategy] = image_strategy_counts.get(image_strategy, 0) + 1

        return {
            "status": "format_comparison_built" if account_profiles else "no_account_profiles",
            "account_count": len(account_profiles),
            "layout_distribution": layout_counts,
            "cta_distribution": cta_counts,
            "image_strategy_distribution": image_strategy_counts,
        }

    def _safe_collect(self, collect_fn, source_name: str) -> Dict[str, Any]:
        try:
            return collect_fn() or {}
        except Exception as error:
            print(f"Competitor Engine {source_name} Source Failed: {error}")
            return {"status": f"{source_name}_error", "fallback_used": True, "reason": str(error)}

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        profile = {
            "status": "competitor_profile_built",
            "benchmark": {"status": "benchmark_unavailable", "sections": [], "fallback_used": True},
            "community": {"status": "community_unavailable", "sources": [], "fallback_used": True},
            "news": {"status": "news_unavailable", "source": {}, "fallback_used": True},
            "instagram_benchmark": {"status": "instagram_benchmark_unavailable", "accounts": [], "fallback_used": True},
            "tools_funnel": {"status": "tools_funnel_unavailable", "references": [], "fallback_used": True},
            "account_profiles": [],
            "hook_and_cta_map": {"hook_sections": [], "cta_sections": []},
            "repeated_content_patterns": [],
            "format_comparison": {
                "status": "no_account_profiles",
                "account_count": 0,
                "layout_distribution": {},
                "cta_distribution": {},
                "image_strategy_distribution": {},
            },
            "gap_analysis_input": {
                "benchmark_hook_count": 0,
                "benchmark_cta_count": 0,
                "community_signal_available": False,
                "news_signal_available": False,
                "account_profile_count": 0,
                "high_priority_account_count": 0,
            },
            "fallback_used": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }

        try:
            self.storage.save(profile)
            self.storage.save_profiles([])
            self.storage.update_statistics(profile, 0)
            self.history.record(profile)
        except Exception as error:
            print(f"Competitor Fallback Persist Failed: {error}")

        return profile
