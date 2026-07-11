import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class CompetitorLearningStorage:
    """
    Competitor Learning Engine - Storage (Sprint 18).

    Persists CompetitorLearningModule outputs under storage/knowledge/
    (Knowledge Database + 5 statistics files - additive to the existing
    modules/knowledge_engine/ files already living in that directory; those
    use different filenames, so there is no collision or overwrite) and
    storage/dashboard/ (daily learning report).

    Never raises: a failed read returns a safe default, matching every other
    Storage class in this codebase (KnowledgeStorage, BrandDNAStorage,
    InstagramResearchStorage).
    """

    def __init__(self, knowledge_dir: Optional[Path] = None, dashboard_dir: Optional[Path] = None):
        self.knowledge_dir = knowledge_dir or Path("storage/knowledge")
        self.dashboard_dir = dashboard_dir or Path("storage/dashboard")
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.dashboard_dir.mkdir(parents=True, exist_ok=True)

        self.knowledge_database_path = self.knowledge_dir / "knowledge_database.json"
        self.hook_statistics_path = self.knowledge_dir / "hook_statistics.json"
        self.cta_statistics_path = self.knowledge_dir / "cta_statistics.json"
        self.pattern_statistics_path = self.knowledge_dir / "pattern_statistics.json"
        self.layout_statistics_path = self.knowledge_dir / "layout_statistics.json"
        self.competitor_statistics_path = self.knowledge_dir / "competitor_statistics.json"
        self.history_path = self.knowledge_dir / "competitor_learning_history.json"
        self.dashboard_path = self.dashboard_dir / "daily_learning_report.json"

    def load_knowledge_database(self) -> Dict[str, Any]:
        return self._load_json(self.knowledge_database_path, self._empty_knowledge_database())

    def save_knowledge_database(self, entries: List[Dict[str, Any]], statistics: Dict[str, Any]) -> Dict[str, Any]:
        entries = entries if isinstance(entries, list) else []
        statistics = statistics if isinstance(statistics, dict) else {}

        previous = self.load_knowledge_database()
        previous_ids = {
            record.get("knowledge_id")
            for record in previous.get("entries", [])
            if isinstance(record, dict)
        }
        new_count = sum(1 for entry in entries if entry.get("knowledge_id") not in previous_ids)

        data = {
            "updated_at": datetime.now().isoformat(),
            "total_count": len(entries),
            "new_count": new_count,
            "entries": entries,
            "caption_summary": statistics.get("caption_summary", {}),
            "sample_size": statistics.get("sample_size", 0),
        }
        self._save_json(self.knowledge_database_path, data)
        return data

    def save_hook_statistics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_stats(self.hook_statistics_path, stats)

    def save_cta_statistics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_stats(self.cta_statistics_path, stats)

    def save_pattern_statistics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_stats(self.pattern_statistics_path, stats)

    def save_layout_statistics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_stats(self.layout_statistics_path, stats)

    def save_competitor_statistics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_stats(self.competitor_statistics_path, stats)

    def load_hook_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.hook_statistics_path, {})

    def load_cta_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.cta_statistics_path, {})

    def load_pattern_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.pattern_statistics_path, {})

    def load_layout_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.layout_statistics_path, {})

    def load_competitor_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.competitor_statistics_path, {})

    def record_history(self, run_summary: Dict[str, Any]) -> None:
        try:
            data = self._load_json(self.history_path, {"records": []})
            records = data.get("records", [])
            if not isinstance(records, list):
                records = []

            records.append({**(run_summary or {}), "recorded_at": datetime.now().isoformat()})
            records = records[-500:]

            self._save_json(self.history_path, {"records": records})
        except Exception as error:
            print(f"Competitor Learning History Record Failed: {error}")

    def load_history(self) -> Dict[str, Any]:
        return self._load_json(self.history_path, {"records": []})

    def save_dashboard(self, report: Dict[str, Any]) -> bool:
        try:
            self._save_json(self.dashboard_path, report or {})
            return True
        except Exception as error:
            print(f"Competitor Learning Dashboard Save Failed: {error}")
            return False

    def load_dashboard(self) -> Dict[str, Any]:
        return self._load_json(self.dashboard_path, {})

    def _save_stats(self, path: Path, stats: Dict[str, Any]) -> Dict[str, Any]:
        stats = dict(stats) if isinstance(stats, dict) else {}
        stats["updated_at"] = datetime.now().isoformat()
        self._save_json(path, stats)
        return stats

    def _empty_knowledge_database(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "total_count": 0,
            "new_count": 0,
            "entries": [],
            "caption_summary": {},
            "sample_size": 0,
        }

    def _load_json(self, path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return dict(default)

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return dict(default)

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
