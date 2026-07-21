# AUTO_SPARK_STATUS_COMBINED_COLLECTOR_REGRESSION_FINAL

## Verdict
FAILED

- **Total tests**: 39
- **Pass**: 37
- **Fail**: 2
- **Error**: 0
- **Duration**: 113.634s
- **Timeout status**: No timeout

## Compile result
- Command: `py -m compileall modules/trend_collector modules/source_intake`
- Exit code: 0
- Status: PASS

## Exact failures

1. `tests.test_edaily_collector.TestEdailyExecutorWiring.test_executor_uses_edaily_collector_when_manager_lacks_method`
   - `AssertionError: 0 != 1`
   - Location: `tests/test_edaily_collector.py:218`
   - Symptom: expected `len(called) == 1`, observed `0`

2. `tests.test_hankyung_economy_collector.TestHankyungEconomyExecutorWiring.test_executor_uses_hankyung_economy_collector_when_manager_lacks_method`
   - `AssertionError: [] is not true`
   - Location: `tests/test_hankyung_economy_collector.py:225`
   - Symptom: `called` list remained empty
