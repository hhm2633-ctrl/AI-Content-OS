#!/usr/bin/env python3
"""Inject the owner-approved AI-Content-OS operating contract at session start."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    hook_dir = Path(__file__).resolve().parent
    contract_path = hook_dir / "OWNER_OPERATING_CONTRACT.md"
    try:
        contract = contract_path.read_text(encoding="utf-8").strip()
    except OSError:
        contract = "AI-Content-OS owner contract file is missing; stop and report the missing guard."
    owners = []
    lock_path = hook_dir / "active_locks.json"
    if lock_path.is_file():
        try:
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            owners = [
                str(entry.get("owner"))
                for entry in payload.get("active", [])
                if isinstance(entry, dict) and entry.get("owner")
            ]
        except (OSError, json.JSONDecodeError):
            owners = []
    lock_note = ", ".join(owners) if owners else "none"
    context = f"{contract}\n\nActive external writer locks: {lock_note}."
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                }
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
