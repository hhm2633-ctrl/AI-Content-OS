import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class CompetitorStorage(object):
    """
    Competitor Engine - Storage.

    storage/competitor/competitor_profile.json (이번 실행의 소스별 원본 수집 요약:
    benchmark/community/news 상태)과
    storage/competitor/competitor_profiles.json (Sprint 13: INSTAGRAM_BENCHMARK.md를
    파싱해 만든 계정별 hook/pattern/layout/cta/image_strategy/priority 프로필 목록)과
    storage/competitor/competitor_statistics.json (누적 통계)을 관리한다.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("storage/competitor")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.profile_path = self.output_dir / "competitor_profile.json"
        self.profiles_path = self.output_dir / "competitor_profiles.json"
        self.statistics_path = self.output_dir / "competitor_statistics.json"

    def save(self, profile: Dict[str, Any]) -> None:
        try:
            self._save_json(self.profile_path, profile)
        except Exception as error:
            print(f"Competitor Storage Save Failed: {error}")

    def load_latest(self) -> Dict[str, Any]:
        return self._load_json(self.profile_path, {})

    def save_profiles(self, profiles: List[Dict[str, Any]]) -> None:
        try:
            self._save_json(
                self.profiles_path,
                {
                    "updated_at": datetime.now().isoformat(),
                    "total_count": len(profiles or []),
                    "profiles": profiles or [],
                },
            )
        except Exception as error:
            print(f"Competitor Profiles Save Failed: {error}")

    def load_profiles(self) -> List[Dict[str, Any]]:
        data = self._load_json(self.profiles_path, {"profiles": []})
        profiles = data.get("profiles", [])
        return profiles if isinstance(profiles, list) else []

    def update_statistics(self, profile: Dict[str, Any], profile_count: int) -> Dict[str, Any]:
        statistics = self._load_json(self.statistics_path, self._empty_statistics())

        statistics["total_runs"] = int(statistics.get("total_runs", 0)) + 1
        statistics["total_benchmark_sections"] = len(profile.get("hook_and_cta_map", {}).get("hook_sections", [])) + \
            len(profile.get("hook_and_cta_map", {}).get("cta_sections", []))
        statistics["latest_account_profile_count"] = profile_count

        priority_counts = statistics.get("account_priority_counts", {})
        if not isinstance(priority_counts, dict):
            priority_counts = {}

        for account_profile in profile.get("account_profiles", []) or []:
            priority = str(account_profile.get("priority", "") or "unspecified")
            priority_counts[priority] = int(priority_counts.get(priority, 0)) + 1

        statistics["account_priority_counts"] = priority_counts
        statistics["updated_at"] = datetime.now().isoformat()

        self._save_json(self.statistics_path, statistics)
        return statistics

    def load_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.statistics_path, self._empty_statistics())

    def _empty_statistics(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "total_runs": 0,
            "total_benchmark_sections": 0,
            "latest_account_profile_count": 0,
            "account_priority_counts": {},
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
