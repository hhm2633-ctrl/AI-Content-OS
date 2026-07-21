"""Bridge the persistent owner-review queue into Agent Console work orders.

The bridge is data-only: it never claims a job, starts an agent, performs
network discovery, publishes content, or issues an affiliate link.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from modules.agent_console.console import AgentConsole


def read_queue(path: str | Path) -> Mapping[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("owner-review queue must be a JSON object")
    return payload


def sync_owner_review_queue(
    *,
    repository_root: str | Path,
    queue_path: str | Path,
    console_root: str | Path,
) -> dict[str, Any]:
    repository = Path(repository_root).resolve()
    queue = Path(queue_path).resolve()
    console_path = Path(console_root).resolve()
    for candidate, label in ((queue, "queue"), (console_path, "console")):
        if candidate != repository and repository not in candidate.parents:
            raise PermissionError(f"{label} path must stay inside the repository")
    coordinator = AgentConsole(console_path, repository_root=repository)
    changes = coordinator.sync_owner_review_queue(read_queue(queue))
    snapshot = coordinator.snapshot()
    return {
        "status": "synced",
        "changes": changes,
        "job_count": len(snapshot.get("jobs", [])),
        "state_path": str(coordinator.state_path),
        "execution_started": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync owner-review work orders into Agent Console")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--queue", default="storage/owner_review/selective_deep_dive_queue.json")
    parser.add_argument("--console-root", default="artifacts/agent_console_v1")
    args = parser.parse_args()
    repository = Path(args.repository_root).resolve()
    result = sync_owner_review_queue(
        repository_root=repository,
        queue_path=repository / args.queue,
        console_root=repository / args.console_root,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

