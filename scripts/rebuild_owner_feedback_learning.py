"""Rebuild and report the compact CardNews owner-learning index."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.agent_console.owner_feedback_learning import ensure_owner_learning_index


def main() -> int:
    result = ensure_owner_learning_index()
    print(json.dumps({
        "schema_version": result.get("schema_version"),
        "stats": result.get("stats", {}),
        "errors": result.get("errors", []),
        "feedback_log_reloaded": result.get("feedback_log_reloaded", False),
    }, ensure_ascii=False, indent=2))
    return 0 if not result.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
