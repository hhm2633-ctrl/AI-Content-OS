import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .instagram_post_schema import contains_sensitive_keys


class SensitiveDataRejectedError(ValueError):
    """Raised when a record contains a credential/session-like field."""


class InstagramResearchStorage:
    def __init__(self, base_dir: str = "storage/research/instagram"):
        self.base_dir = Path(base_dir)
        self.screenshots_dir = self.base_dir / "screenshots"
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

        self.capability_audit_path = self.base_dir / "capability_audit.json"
        self.accounts_path = self.base_dir / "accounts.json"
        self.posts_path = self.base_dir / "posts.json"
        self.classifications_path = self.base_dir / "classifications.json"
        self.statistics_path = self.base_dir / "statistics.json"
        self.research_run_path = self.base_dir / "research_run.json"
        self.dashboard_path = self.base_dir / "research_dashboard.txt"

    def _load_json(self, path: Path, default: Any) -> Any:
        try:
            if not path.exists():
                return default
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, ValueError):
            return default

    def _save_json(self, path: Path, data: Any) -> bool:
        if contains_sensitive_keys(data):
            raise SensitiveDataRejectedError(
                f"Refusing to write sensitive credential/session-like field to {path}"
            )
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False

    def save_capability_audit(self, data: Dict[str, Any]) -> bool:
        return self._save_json(self.capability_audit_path, data)

    def load_capability_audit(self) -> Dict[str, Any]:
        return self._load_json(self.capability_audit_path, {})

    def save_accounts(self, data: List[Dict[str, Any]]) -> bool:
        return self._save_json(self.accounts_path, data)

    def load_accounts(self) -> List[Dict[str, Any]]:
        return self._load_json(self.accounts_path, [])

    def save_posts(self, data: List[Dict[str, Any]]) -> bool:
        return self._save_json(self.posts_path, data)

    def load_posts(self) -> List[Dict[str, Any]]:
        return self._load_json(self.posts_path, [])

    def save_classifications(self, data: List[Dict[str, Any]]) -> bool:
        return self._save_json(self.classifications_path, data)

    def load_classifications(self) -> List[Dict[str, Any]]:
        return self._load_json(self.classifications_path, [])

    def save_statistics(self, data: Dict[str, Any]) -> bool:
        return self._save_json(self.statistics_path, data)

    def load_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.statistics_path, {})

    def save_research_run(self, data: Dict[str, Any]) -> bool:
        return self._save_json(self.research_run_path, data)

    def load_research_run(self) -> Dict[str, Any]:
        return self._load_json(self.research_run_path, {})

    def save_dashboard_text(self, text: str) -> bool:
        try:
            self.dashboard_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.dashboard_path, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except OSError:
            return False

    def load_dashboard_text(self) -> Optional[str]:
        try:
            if not self.dashboard_path.exists():
                return None
            with open(self.dashboard_path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def safe_screenshot_path(self, filename: str) -> Optional[str]:
        """Returns a path string confined to the screenshots dir, or None if unsafe."""
        if not isinstance(filename, str) or not filename.strip():
            return None
        name = Path(filename).name  # strips any directory traversal component
        if name in ("", ".", ".."):
            return None
        return str(self.screenshots_dir / name)
