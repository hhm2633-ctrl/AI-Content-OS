"""Build a production CardNews renderer request from approved local inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from modules.card_news.production_render_request_builder import (
    build_production_render_request,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--owned-asset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        package = json.loads(args.package.read_text(encoding="utf-8"))
        authorization = json.loads(args.authorization.read_text(encoding="utf-8"))
        result = build_production_render_request(
            package,
            authorization,
            args.owned_asset,
            package_path=args.package,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        result = {
            "schema_version": "cardnews_renderer_request_v1",
            "status": "blocked",
            "reason_code": f"input_read_failed:{type(error).__name__}",
            "render_request": None,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = result.get("render_request") if result.get("status") == "ready" else result
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "reason_code": result["reason_code"],
        "output": str(args.output),
    }, ensure_ascii=False))
    return 0 if result["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
