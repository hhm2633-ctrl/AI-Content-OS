"""Import owner-supplied CSV/JSON performance measurements without API access."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.analytics_engine.promotion_candidate_builder import PromotionCandidateBuilder
from modules.learning.performance_ledger import PerformanceLedger


def load_import_file(path: Path) -> List[Dict[str, Any]]:
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            payload = payload.get("records")
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise ValueError("JSON import must be an array or an object containing a records array")
        return [dict(item) for item in payload]
    raise ValueError("input must be .csv or .json")


def parse_thresholds(values: List[str]) -> Dict[str, float]:
    thresholds: Dict[str, float] = {}
    for value in values:
        key, separator, raw = value.partition("=")
        if not separator or not key.strip():
            raise ValueError("metric threshold must use metric=value")
        thresholds[key.strip()] = float(raw)
    return thresholds


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("storage/learning/performance_ledger.json"),
    )
    parser.add_argument(
        "--promotion-candidates",
        type=Path,
        default=Path("storage/learning/promotion_candidates.json"),
    )
    parser.add_argument("--metric-threshold", action="append", default=[])
    parser.add_argument("--minimum-sample-size", type=int, default=1)
    args = parser.parse_args()

    input_path = args.input.resolve()
    raw = input_path.read_bytes()
    rows = load_import_file(input_path)
    source_type = "manual_csv" if input_path.suffix.casefold() == ".csv" else "manual_json"
    ledger = PerformanceLedger(args.ledger)
    batch = ledger.import_external(
        rows,
        source_type=source_type,
        source_name=input_path.name,
        source_hash=hashlib.sha256(raw).hexdigest(),
    )

    thresholds = parse_thresholds(args.metric_threshold)
    pattern_ids = sorted(
        {
            pattern_id
            for record in ledger.external_records()
            for pattern_id in (record.get("pattern_ids") or [])
            if any(
                pattern_id in str(row.get("pattern_ids") or row.get("pattern_id") or "")
                for row in rows
            )
        }
    )
    builder = PromotionCandidateBuilder(args.promotion_candidates)
    candidates = [
        builder.build(
            pattern_id=pattern_id,
            records=ledger.external_records(pattern_id=pattern_id),
            metric_thresholds=thresholds,
            minimum_sample_size=args.minimum_sample_size,
        )
        for pattern_id in pattern_ids
    ]
    print(
        json.dumps(
            {
                "status": "external_performance_imported",
                "actual_publish": False,
                "external_api_called": False,
                "pattern_registry_called": False,
                "import_batch": batch,
                "promotion_candidates": candidates,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
