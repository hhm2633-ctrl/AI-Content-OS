# Isolation B Status

## Root Cause
1) Nate rank wiring failure was caused by `hasattr` checks treating inherited `TrendSourceManager` methods as implemented, so `_ExecutorManager` test fixture bypassed local `NateNewsRankCollector` injection and never used patched collector.
2) Daily executor baseline `item_count` risk came from broad fallback/manager-method detection that could allow unintended direct routing paths to leak into shared plan execution; this was prevented by requiring explicit manager method presence.

## Fix
- Added explicit manager-method presence helper in `modules/source_intake/daily_collection_executor.py`:
  - `_has_manager_collector_method(manager, method_name)` now checks only methods defined on the concrete manager class (`vars(type(manager))`).
- Updated `execute_daily_shallow_collection` routing:
  - Replaced direct `hasattr` usage for `has_manager_method` with the explicit helper.
  - Kept existing direct-fallback map logic while ensuring `newsis`/`theqoo` use explicit method presence.
  - Added direct fallback condition for `nate_news_rank` when manager is `TrendSourceManager`-based and lacks an explicit override, so tests can force local collector fallback without affecting generic fake managers.

## Changed Files
- `modules/source_intake/daily_collection_executor.py`

## Test Runs
- `py -m unittest tests.test_nate_news_rank_collector tests.test_daily_source_collection_executor -v` => OK (9 passed)
- `py -m unittest tests.test_daily_source_collection_executor tests.test_nate_news_rank_collector -v` => OK (9 passed)

## GO/NO_GO
- GO