# Auto Spark Isolation A Status

GO

Root Cause:
- `execute_daily_shallow_collection` used a broad/fragile collector selection path where direct-collector fallback was only partially gated, and manager invocation detection used dictionary-only checks. When collector-focused tests ran together, `newsis`/`theqoo`/`mk_economy` were not consistently routed to patched direct collectors, causing empty call lists or false flags.

Changes:
- Updated `modules/source_intake/daily_collection_executor.py`
  - Added `theqoo` and `mk_economy` to `_DIRECT_FALLBACK_MANAGERLESS_IDS` to cover isolated wiring expectations.
  - Simplified direct collector gating: keep `allow_direct_collectors` tied to explicit input (`source_manager is None`), and avoid broad auto-direct behavior for generic managers.
  - Changed direct routing decision to target only expected fallback cases (explicit managerless list and explicit missing manager methods for `newsis`/`theqoo`).
  - Kept manager-method usage detection on `hasattr(...)` so inherited/real methods resolve correctly while preserving fallback behavior.

Execution Results:
- Together command: `py -m unittest tests.test_mk_pick_collector tests.test_newsis_collector tests.test_theqoo_collector -v`
  - Result: OK
  - Passed: 9
  - Failed: 0

- Individual modules:
  - `py -m unittest tests.test_mk_pick_collector -v`: Passed 3
  - `py -m unittest tests.test_newsis_collector -v`: Passed 3
  - `py -m unittest tests.test_theqoo_collector -v`: Passed 3

Changed Files:
- modules/source_intake/daily_collection_executor.py
- external_workclaude/source_collection_engine_v0_spark/AUTO_SPARK_STATUS_ISOLATION_A.md