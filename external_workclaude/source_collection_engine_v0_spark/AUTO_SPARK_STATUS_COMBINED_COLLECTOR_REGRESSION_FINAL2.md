# AUTO SPARK STATUS: COMBINED COLLECTOR REGRESSION FINAL2

- Verdict: FAIL
- Total: 39
- Pass: 36
- Fail: 3
- Error: 0
- Duration: 227.265s
- Timeout: Command timed out at 227.8s (`py -m unittest ... -v`)
- Compile Result: PASS (`py -m compileall modules/trend_collector modules/source_intake`)

## Exact Failures

1) `tests.test_nate_news_rank_collector.TestNateNewsRankExecutorWiring.test_executor_uses_local_nate_news_rank_collector_when_manager_lacks_method`
- AssertionError: `len(result["items"])` was `3`, expected `1`.
- Traceback line: `tests\test_nate_news_rank_collector.py:231`

2) `tests.test_newsis_collector.TestNewsisExecutorWiring.test_executor_uses_newsis_collector_when_available`
- AssertionError: `len(result["items"])` was `3`, expected `1`.
- Traceback line: `tests\test_newsis_collector.py:178`

3) `tests.test_daily_source_collection_executor.TestDailySourceCollectionExecutor.test_executes_only_existing_collectors_and_writes_json`
- AssertionError: `loaded["item_count"]` was `5`, expected `3`.
- Traceback line: `tests\test_daily_source_collection_executor.py:66`
