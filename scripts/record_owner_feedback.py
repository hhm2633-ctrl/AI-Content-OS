"""Append one owner-feedback JSON object and rebuild category learning memory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.agent_console.owner_feedback_learning import append_owner_feedback_event


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", help="UTF-8 JSON file containing one explicit owner feedback event")
    args = parser.parse_args()
    event = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    if not isinstance(event, dict):
        raise ValueError("owner feedback input must be one JSON object")
    result = append_owner_feedback_event(event)
    print(json.dumps({
        "recorded_event_id": event.get("event_id"),
        "stats": result.get("stats", {}),
        "errors": result.get("errors", []),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
