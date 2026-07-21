"""Validate and atomically save an owner-authorized Brand Connect UI snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.brandconnect.brandconnect_product_catalog import (
    CATALOG_REUSE_POLICY,
    load_cached_brandconnect_catalog,
    normalize_brandconnect_catalog,
)


OUTPUT = ROOT / "storage" / "owner_review" / "brandconnect_catalog_snapshot.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Save an owner-authorized Brand Connect catalog snapshot."
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Explicitly replace an existing snapshot with JSON read from stdin.",
    )
    args = parser.parse_args(argv)

    if OUTPUT.exists() and not args.refresh:
        cached = load_cached_brandconnect_catalog(OUTPUT)
        if not cached["complete"]:
            raise ValueError("existing catalog cache is invalid; explicit --refresh is required")
        print(json.dumps({
            "saved": False,
            "reused": True,
            "product_count": cached["product_count"],
            "catalog_reuse_policy": CATALOG_REUSE_POLICY,
            "network_used": False,
        }))
        return 0

    raw = json.load(sys.stdin)
    normalized = normalize_brandconnect_catalog(raw)
    if not normalized["complete"]:
        raise ValueError(f"catalog rejected: {normalized['status']}")
    snapshot = {
        "schema_version": "brandconnect_authorized_ui_snapshot.v1",
        "source": raw.get("source", "naver_brandconnect_authorized_ui_snapshot"),
        "captured_at": raw.get("captured_at"),
        "products": raw.get("products", []),
        "product_count": normalized["product_count"],
        "catalog_reuse_policy": CATALOG_REUSE_POLICY,
        "refresh_mode": "explicit" if args.refresh else "initial_snapshot",
        "link_issuance": False,
        "publishing": False,
        "network_used": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    print(json.dumps({
        "saved": True,
        "reused": False,
        "product_count": normalized["product_count"],
        "catalog_reuse_policy": CATALOG_REUSE_POLICY,
        "network_used": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
