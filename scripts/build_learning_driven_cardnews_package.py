"""Build one approval-gated package from a discovery learning blueprint."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from modules.card_news.learning_driven_production_bridge import (
    build_learning_driven_production_package,
)
from modules.media_intelligence.source_editorial_localizer import (
    localize_source_editorial_media,
)


def _pipeline(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    nested = value.get("pipeline_result")
    return nested if isinstance(nested, Mapping) else value


def _find_blueprint(payload: Any, candidate_id: str) -> Mapping[str, Any]:
    plans = _pipeline(payload).get("slide_plans")
    if not isinstance(plans, Mapping):
        return {}
    for account_plans in plans.values():
        for plan in account_plans if isinstance(account_plans, list) else []:
            if (
                isinstance(plan, Mapping)
                and plan.get("candidate_id") == candidate_id
                and isinstance(plan.get("production_blueprint"), Mapping)
            ):
                return plan["production_blueprint"]
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--localize-source-media-root",
        type=Path,
        help=(
            "F: destination for verified source media. When omitted, the "
            "AI_CONTENT_OS_SOURCE_MEDIA_ROOT F: location is used."
        ),
    )
    args = parser.parse_args()
    try:
        discovery = json.loads(args.discovery.read_text(encoding="utf-8"))
        approval = (
            json.loads(args.approval.read_text(encoding="utf-8"))
            if args.approval
            else None
        )
        receipt = (
            approval.get("receipt")
            if isinstance(approval, Mapping)
            and isinstance(approval.get("receipt"), Mapping)
            else approval
        )
        result = build_learning_driven_production_package(
            _find_blueprint(discovery, args.candidate_id),
            receipt,
        )
        if result.get("status") == "production_package_ready":
            media_root = args.localize_source_media_root or (
                Path(
                    os.getenv(
                        "AI_CONTENT_OS_SOURCE_MEDIA_ROOT",
                        r"F:\AI-Content-OS-Data\card_news\source_media",
                    )
                )
                / args.candidate_id
            )
            result = localize_source_editorial_media(
                result,
                media_root,
            )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result = {
            "schema_version": "selected_candidate_production_package_v1",
            "status": "blocked",
            "reason_code": f"input_read_failed:{type(exc).__name__}",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "reason_code": result.get("reason_code"),
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result.get("status") in {
        "production_package_ready",
        "production_package_pending_approval",
    } else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
