# AUTO_SPARK_STATUS_COLLECTOR_INJECTION_F

- Verdict: GO

- Changed
  - `modules/source_intake/daily_collection_executor.py`
  - `tests/test_mk_pick_collector.py`
  - `tests/test_edaily_collector.py`
  - `tests/test_theqoo_collector.py`
  - `tests/test_daily_source_collection_executor.py`

- Root cause
  - No stable patchable factory seam and broad fixture plans allowed unrelated/live routes.

- Verification
  - Forward: `16/16 PASS`, `0.342s`
  - Reverse: `16/16 PASS`, `0.280s`

- Network guard
  - Covers `socket.create_connection`, `socket.socket.connect`, `urllib.request.urlopen`
  - No live traces

- Design change
  - Introduced stable module-level direct collector registry.
