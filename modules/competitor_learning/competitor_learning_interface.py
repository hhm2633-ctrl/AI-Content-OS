from typing import Any, Dict, List, Optional

from modules.competitor_learning.competitor_learning_storage import CompetitorLearningStorage


class CompetitorLearningInterface:
    """
    Competitor Learning Engine - Interface (Sprint 18).

    Read-only query API for Pattern Engine / Content Engine / Brand DNA Engine
    to consult the Instagram-Research-derived Knowledge Database, mirroring
    modules/knowledge_engine/knowledge_interface.py::KnowledgeInterface's
    shape. Every method fails safe (empty list/dict/False) - never raises,
    never blocks the caller's own existing selection/fallback logic.
    """

    def __init__(self, storage: Optional[CompetitorLearningStorage] = None):
        self.storage = storage or CompetitorLearningStorage()

    def is_available(self) -> bool:
        try:
            database = self.storage.load_knowledge_database()
            return bool(database.get("entries"))
        except Exception:
            return False

    def get_knowledge_database(self) -> Dict[str, Any]:
        try:
            return self.storage.load_knowledge_database()
        except Exception:
            return {}

    def get_top_hooks(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self._get_by_type("hook", limit)

    def get_top_ctas(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self._get_by_type("cta", limit)

    def get_top_patterns(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self._get_by_type("pattern", limit)

    def get_top_layouts(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self._get_by_type("layout", limit)

    def get_hook_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_hook_statistics()
        except Exception:
            return {}

    def get_cta_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_cta_statistics()
        except Exception:
            return {}

    def get_pattern_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_pattern_statistics()
        except Exception:
            return {}

    def get_layout_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_layout_statistics()
        except Exception:
            return {}

    def get_competitor_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_competitor_statistics()
        except Exception:
            return {}

    def get_account_profile(self, account_handle: str) -> Dict[str, Any]:
        try:
            accounts = self.get_competitor_statistics().get("accounts", {})
            if not isinstance(accounts, dict):
                return {}
            profile = accounts.get(account_handle, {})
            return profile if isinstance(profile, dict) else {}
        except Exception:
            return {}

    def get_dashboard(self) -> Dict[str, Any]:
        try:
            return self.storage.load_dashboard()
        except Exception:
            return {}

    def _get_by_type(self, entry_type: str, limit: int) -> List[Dict[str, Any]]:
        try:
            database = self.storage.load_knowledge_database()
            entries = database.get("entries", [])

            if not isinstance(entries, list):
                return []

            matched = [
                entry for entry in entries
                if isinstance(entry, dict) and entry.get("type") == entry_type
            ]
            matched.sort(key=self._overall_score, reverse=True)
            return matched[:limit]
        except Exception as error:
            print(f"Competitor Learning Interface get_by_type Failed: {error}")
            return []

    def _overall_score(self, entry: Dict[str, Any]) -> float:
        score = entry.get("score") or {}
        try:
            return float(score.get("overall_score", 0.0))
        except Exception:
            return 0.0
