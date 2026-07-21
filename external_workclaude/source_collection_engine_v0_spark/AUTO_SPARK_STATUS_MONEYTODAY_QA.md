# MONEYTODAY Collector Spark QA Status

## Verdict
- **NO_GO**

## Changed files
- `modules/trend_collector/moneytoday_collector.py`
- `tests/test_moneytoday_collector.py`
- `external_workclaude/source_collection_engine_v0_spark/AUTO_SPARK_STATUS_MONEYTODAY_QA.md`

## Test results
- Required command: `py -m unittest tests.test_moneytoday_collector tests.test_daily_source_collection_executor -v`
- Result: **PASS**
- Test count: **9** tests, **0 failures**, **0 errors**
- Notable coverage:
  - `test_moneytoday_collector`: fixture contract parse, normalization, fail-closed behavior, TrendSourceManager compatibility
  - `test_daily_source_collection_executor`: existing executor compatibility baseline

## Compile result
- Required command: `py -m compileall modules/trend_collector modules/source_intake`
- Result: **PASS** (command exited 0)
- Compiled modules include:
  - `modules/trend_collector/source_health_tracker.py`
  - `modules/trend_collector/trend_quality_scorer.py`
  - (all discovered modules in scope compiled without errors)

## Existing MoneyToday edit necessity audit (read-only files)
- `modules/trend_collector/trend_source_manager.py` — **Necessary**
  - Keeps MoneyToday in enabled source pipeline, with dedicated cache/fallback path and summary update hooks.
- `config/trend_sources.json` — **Necessary**
  - Enables MoneyToday as an active trend source and preserves tier/weight contract used by ranking.
- `modules/trend_collector/source_health_tracker.py` — **Necessary**
  - Maintains MoneyToday in source health/latest records and collector statistics tracking.
- `modules/trend_collector/trend_quality_scorer.py` — **Necessary**
  - Defines MoneyToday source score baseline and selection behavior used by downstream ranking.

## Remaining blocker
- Daily shallow collection plan includes `moneytoday`, but `modules/source_intake/daily_collection_executor.py` does not map `moneytoday` in `COLLECTOR_METHODS`.
- Current behavior for shallow plans that include `moneytoday` is still skip-by-design in that executor, so MoneyToday remains uncollected in that specific path until executor mapping is updated.
