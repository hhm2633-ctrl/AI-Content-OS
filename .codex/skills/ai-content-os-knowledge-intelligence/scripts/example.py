#!/usr/bin/env python3
"""Read-only validator for learning pattern JSONL registries."""

import argparse
import json
from pathlib import Path
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("registry", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo))
    from modules.knowledge.pattern_registry import PatternRegistry, PatternRegistryError
    try:
        patterns = PatternRegistry(args.registry).load_all()
    except PatternRegistryError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps({
        "valid": True,
        "records": len(patterns),
        "statuses": sorted({item.status.value for item in patterns}),
        "source_free_promotions": sum(item.status.value == "PROMOTED" and not item.source_claim_ids for item in patterns),
    }, ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
