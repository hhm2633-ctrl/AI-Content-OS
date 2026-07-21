"""Create or refresh the local Agent Console v1 dashboard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from modules.agent_console.console import AgentConsole


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the local Agent Console dashboard")
    parser.add_argument("--root", default="artifacts/agent_console_v1")
    args = parser.parse_args()
    console = AgentConsole(Path(args.root))
    console._save()  # explicit local artifact refresh; no agent or API is executed
    print(json.dumps({"status": "written", "dashboard": str(console.dashboard_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
