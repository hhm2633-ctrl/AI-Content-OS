"""Build a production CardNews renderer request from approved local inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from modules.card_news.production_render_request_builder import (
    build_production_render_request,
)


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def resolve_owned_asset(package, explicit_path=None):
    """Resolve package-owned local media; an explicit path remains the override."""

    if explicit_path is not None:
        return Path(explicit_path)
    candidates = []
    slides = package.get("slides") if isinstance(package, dict) else []
    for slide in slides if isinstance(slides, list) else []:
        if not isinstance(slide, dict):
            continue
        visual_spec = slide.get("visual_spec") if isinstance(slide.get("visual_spec"), dict) else {}
        candidate = visual_spec.get("source_media_candidate")
        if isinstance(candidate, dict):
            candidates.append(candidate)
    evidence = package.get("evidence") if isinstance(package, dict) else {}
    assets = evidence.get("assets") if isinstance(evidence, dict) else []
    candidates.extend(item for item in assets if isinstance(item, dict))
    for candidate in candidates:
        rights_status = _text(candidate.get("rights_status")).lower()
        if rights_status in {"", "blocked", "reference_only", "unknown"}:
            continue
        if candidate.get("render_allowed") is False:
            continue
        for key in ("local_path", "owned_asset_path", "locator", "path", "asset_path"):
            value = _text(candidate.get(key))
            if value and Path(value).is_file():
                return Path(value)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument(
        "--owned-asset",
        type=Path,
        help="approved local asset override; otherwise resolve from package evidence/slides",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        package = json.loads(args.package.read_text(encoding="utf-8"))
        authorization = json.loads(args.authorization.read_text(encoding="utf-8"))
        owned_asset = resolve_owned_asset(package, args.owned_asset)
        if owned_asset is None:
            raise FileNotFoundError("no approved local owned asset is present in the package")
        result = build_production_render_request(
            package,
            authorization,
            owned_asset,
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
