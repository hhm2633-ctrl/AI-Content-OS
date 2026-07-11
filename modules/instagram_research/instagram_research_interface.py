from typing import Any, Dict, List

from .instagram_storage import InstagramResearchStorage


class InstagramResearchInterface:
    """Read-only accessor for other engines (Competitor/Knowledge/Planner) to
    check whether an Instagram research dataset exists and read its summary.

    This interface deliberately does NOT feed data into any engine's
    learning/scoring logic. It is a preparation point only, per Sprint 17-0
    scope: no automatic learning, no Planner score changes, no Brand DNA
    updates from this dataset.
    """

    def __init__(self, storage: InstagramResearchStorage = None):
        self.storage = storage or InstagramResearchStorage()

    def get_dataset_status(self) -> Dict[str, Any]:
        try:
            run = self.storage.load_research_run()
            posts = self.storage.load_posts()
            return {
                "available": bool(posts),
                "total_posts": len(posts) if isinstance(posts, list) else 0,
                "current_run_accounts": run.get("current_run_accounts", []) if isinstance(run, dict) else [],
                "last_checked_at": run.get("checked_at") if isinstance(run, dict) else None,
                "auto_learning_connected": False,
            }
        except Exception:
            return {
                "available": False,
                "total_posts": 0,
                "current_run_accounts": [],
                "last_checked_at": None,
                "auto_learning_connected": False,
            }

    def get_capability_audit(self) -> Dict[str, Any]:
        try:
            return self.storage.load_capability_audit()
        except Exception:
            return {}

    def get_accounts(self) -> List[Dict[str, Any]]:
        try:
            return self.storage.load_accounts()
        except Exception:
            return []

    def get_posts(self, limit: int = None, account_handle: str = None) -> List[Dict[str, Any]]:
        try:
            posts = self.storage.load_posts()
            if not isinstance(posts, list):
                return []
            if account_handle:
                posts = [
                    post for post in posts
                    if isinstance(post, dict) and post.get("account_handle") == account_handle
                ]
            return posts[:limit] if limit else posts
        except Exception:
            return []

    def get_classifications(self) -> List[Dict[str, Any]]:
        try:
            classifications = self.storage.load_classifications()
            return classifications if isinstance(classifications, list) else []
        except Exception:
            return []

    def get_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_statistics()
        except Exception:
            return {}
