from datetime import datetime
from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.competitor_learning.competitor_learning_dashboard import CompetitorLearningDashboard
from modules.competitor_learning.competitor_learning_extractor import CompetitorLearningExtractor
from modules.competitor_learning.competitor_learning_score import CompetitorLearningScorer
from modules.competitor_learning.competitor_learning_statistics import CompetitorLearningStatistics
from modules.competitor_learning.competitor_learning_storage import CompetitorLearningStorage


class CompetitorLearningModule(BaseModule):
    """
    Competitor Learning Engine (Sprint 18).

    Converts modules/instagram_research/'s already-saved, manually-observed
    competitor posts into a Knowledge Database that Pattern Engine, Content
    Engine, and Brand DNA Engine can consult (via CompetitorLearningInterface)
    when choosing hook/cta/pattern.

    This module does NOT modify modules/instagram_research/ - it only reads
    through that module's public InstagramResearchInterface/classify_post().
    It also is NOT wired into WorkflowEngine.run(): it is a separate, offline,
    on-demand learning step, run whenever new Instagram Research data has been
    collected (mirroring scripts/update_project_snapshot.py's standalone-entry-
    point shape, not the linear pipeline). No crawler, no Playwright, no
    browser automation, no network/LLM calls of its own.

    run() never raises: any internal failure degrades to a safe, empty-but-
    valid result with fallback_used=True, exactly like every other Engine's
    run() in this codebase.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        storage: Optional[CompetitorLearningStorage] = None,
    ):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.extractor = CompetitorLearningExtractor()
        self.statistics_builder = CompetitorLearningStatistics()
        self.scorer = CompetitorLearningScorer()
        self.storage = storage or CompetitorLearningStorage()
        self.dashboard_builder = CompetitorLearningDashboard()

    def run(self) -> Dict[str, Any]:
        print("Competitor Learning Module Started")

        try:
            result = self._run()
        except Exception as error:
            print(f"Competitor Learning Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"competitor_learning_exception: {error}")

        print("Competitor Learning Module Finished")
        return result

    def _run(self) -> Dict[str, Any]:
        observations = self.extractor.extract()
        statistics = self.statistics_builder.compute(observations)
        entries = self.scorer.build_entries(statistics)

        knowledge_database = self.storage.save_knowledge_database(entries, statistics)
        self.storage.save_hook_statistics(statistics["hook_statistics"])
        self.storage.save_cta_statistics(statistics["cta_statistics"])
        self.storage.save_pattern_statistics(statistics["pattern_statistics"])
        self.storage.save_layout_statistics(statistics["layout_statistics"])
        self.storage.save_competitor_statistics(statistics["competitor_statistics"])

        dashboard_report = self.dashboard_builder.build(statistics, knowledge_database)
        self.storage.save_dashboard(dashboard_report)

        account_count = (statistics.get("competitor_statistics") or {}).get("account_count", 0)
        sample_size = statistics.get("sample_size", 0)

        self.storage.record_history({
            "sample_size": sample_size,
            "entry_count": len(entries),
            "new_count": knowledge_database.get("new_count", 0),
            "account_count": account_count,
        })

        return {
            "status": "competitor_learning_completed",
            "sample_size": sample_size,
            "entry_count": len(entries),
            "new_count": knowledge_database.get("new_count", 0),
            "account_count": account_count,
            "knowledge_database": knowledge_database,
            "statistics": statistics,
            "dashboard": dashboard_report,
            "fallback_used": sample_size == 0,
            "reason": "" if sample_size else "instagram_research 데이터가 아직 없어 빈 Knowledge Database를 기록함.",
            "created_at": datetime.now().isoformat(),
        }

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        return {
            "status": "competitor_learning_completed",
            "sample_size": 0,
            "entry_count": 0,
            "new_count": 0,
            "account_count": 0,
            "knowledge_database": {},
            "statistics": {},
            "dashboard": {},
            "fallback_used": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }
