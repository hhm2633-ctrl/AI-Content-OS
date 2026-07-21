# CTO Work Order — Collection Quality Assessment

## Objective

Implement deterministic offline quality assessment for shallow collection outputs and connect the
summary to the daily collection result. Do not execute tests until Spark Source Agreement is handed
off; final verification is one combined batch.

## CTO-owned files

- `modules/source_intake/collection_quality_assessor.py` (new)
- `tests/test_collection_quality_assessor.py` (new)
- `modules/source_intake/daily_collection_executor.py`
- `tests/test_daily_source_collection_executor.py`
- CTO shared status/docs after verification.

## Protected files/actions

- Spark Source Agreement files and Claude collector files are read-only until handoff.
- No collector/config/storage/WorkflowEngine/unrelated test/browser/network/Git changes.

## Contract

- Public function: `assess_collection_quality(items, source_results=None)`.
- Pure deterministic assessment; never mutate inputs or write files.
- Report item/source counts, live/fallback counts and ratios, usable shallow item count, required
  field completeness, optional evidence-field availability, visible metric availability, and
  explicit missing-field counts.
- `usable_shallow` requires title/keyword, canonical link/url, source ID, and non-fallback state;
  it must not claim card-news readiness or factual verification.
- Status values: `EMPTY`, `LIMITED`, `USABLE_SHALLOW`; thresholds must be explicit in output.
- Missing/malformed inputs fail closed without exceptions or fabricated metrics.
- Add `quality_summary` to daily executor output without changing existing fields/contracts.
- Tests cover empty, all-fallback, mixed, complete, missing fields, unavailable metrics, malformed
  rows, input immutability, and executor summary presence.

## Handoff

- Implement first; no early test/compile.
- After Spark handoff, one combined focused test batch and repository compile check.

