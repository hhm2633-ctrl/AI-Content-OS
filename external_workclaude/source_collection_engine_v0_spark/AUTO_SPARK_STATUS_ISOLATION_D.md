AUTO_SPARK_STATUS_ISOLATION_D.md

Root cause (from prior handoff): Source intake executor dispatch path was incorrectly relying on manager method availability during wiring, causing collection path instability under fallback conditions.

Changed file:
- modules/source_intake/daily_collection_executor.py

Verification runs:
1) Command: py -m unittest tests.test_edaily_collector tests.test_hankyung_economy_collector -v
   - Result: OK
   - Ran: 8 tests in 20.301s
2) Command: py -m unittest tests.test_hankyung_economy_collector tests.test_edaily_collector -v
   - Result: OK
   - Ran: 8 tests in 20.334s

GO/NO_GO: GO
