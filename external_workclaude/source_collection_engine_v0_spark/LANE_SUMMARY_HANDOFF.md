# not implemented
- Not implemented: path fallback for gap input that has no plan and no gap-report keys.

# tests
- Added: `tests/test_lane_collection_summary.py`
  - fake gap report summary + readiness + ordering
  - smoke test on `storage/source_intake/2026-07-14/collection_gap_report.json` if present
- Command target for QA: `py -m unittest tests.test_lane_collection_summary tests.test_collection_gap_report -v`

# next light Spark tasks
- Expose `build_lane_collection_summary(...)` via CLI/task entry point.
- Add optional `top_n` parameter to limit `top_missing_sources` length if needed by downstream consumers.
- Add a short smoke test for daily-shallow path fallback conversion.
