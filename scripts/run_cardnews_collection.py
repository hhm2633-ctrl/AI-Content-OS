"""Run CardNews collection through a pending owner-review queue."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.source_intake.cardnews_collection_orchestrator import (
    run_cardnews_collection_orchestrator,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--today")
    parser.add_argument("--output-root", default="storage/source_intake")
    parser.add_argument("--owner-queue")
    parser.add_argument("--account-profile", action="append", dest="account_profiles")
    parser.add_argument("--receipt")
    args = parser.parse_args()
    result = run_cardnews_collection_orchestrator(
        account_profiles=args.account_profiles,
        today=args.today,
        output_root=args.output_root,
        owner_queue_path=args.owner_queue,
    )
    if args.receipt:
        receipt_path = Path(args.receipt)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "reason_code": result.get("reason_code"),
                "owner_queue_path": result.get("owner_queue_path"),
                "owner_review_count": result.get("owner_review_queue", {}).get("request_count", 0),
                "owner_selection_performed": result.get("owner_selection_performed", False),
                "production_performed": result.get("production_performed", False),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.get("status") == "owner_review_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
