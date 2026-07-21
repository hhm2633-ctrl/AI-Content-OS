# CTO Work Order — PPOMPPU Collector and Executor Integration

## Objective

Implement a zero-live-network, fixture/cache-ready `PpomppuCollector` and connect both PPOMPPU and
the separately implemented DCInside collector to the daily shallow executor. Tests run only after
both lanes finish.

## CTO-owned files

- `modules/trend_collector/ppomppu_collector.py` (new)
- `tests/test_ppomppu_collector.py` (new)
- `modules/source_intake/daily_collection_executor.py`
- `tests/test_daily_source_collection_executor.py`
- CTO-owned shared status/docs after verification.

## Protected files/actions

- Spark-owned DCInside collector/test/status and existing `dcinside_parser.py` are read-only.
- No config, storage outputs, WorkflowEngine, unrelated collectors/tests, browser/live network,
  credentials, publishing, Git, or early tests/compile.

## Implementation contract

- Class: `PpomppuCollector`; dependency-injectable fixture fetcher and deterministic list parser.
- Default collection fails closed with `live_activation_not_approved`; no endpoint guessing.
- Parse synthetic public-list fixture fields only: title, canonical link, visible time/category,
  visible list metrics, one-based rank. No body/image/user/comment-body data.
- Cache: `storage/cache/ppomppu_cache.json`; bounded retry and honest diagnostics.
- URL-first/title-second deterministic dedup; no fabricated metrics.
- Executor manager methods retain precedence; direct factories support both new collectors.

## Completion checks and handoff

- Implement first without tests/compile.
- After Spark handoff, integration review then one combined focused test batch and compile.
- Report changed files, test result, live-activation boundary, and residual limitations.

