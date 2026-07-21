# Auto Status: SPARK Source Intake Release Candidate

## Lane
- Lane: SC-S
- Objective: add Daum/News1 direct-factory reachability and add fail-closed Source Intake RC gate validation/tests.
- Date: 2026-07-15
- Decision: GO

## Exact diff summary
- `modules/source_intake/daily_collection_executor.py`
  - Added `DaumNewsCollector` import.
  - Added direct-factory mappings for `daum_news` and `news1` in `DIRECT_COLLECTOR_FACTORIES`.
- `modules/source_intake/source_intake_release_candidate.py`
  - Added `TrendSourceManager` fallback when no `source_manager` is passed.
  - Fixed consistency-root resolution so explicit date-folder status path resolves to its parent day root (`.../<today>/<file>` no longer double-nests).
  - No change to fail-closed behavior: any defect still returns `candidates: []` and zero candidate_count.
- `tests/test_daily_source_collection_executor.py`
  - Added direct-factory reachability test for `daum_news` and `news1` with zero-network fakes.
  - Added explicit-manager precedence test confirming manager methods override direct factories.
- `tests/test_source_intake_release_candidate.py` (new)
  - Added focused RC tests for:
    - callable callability matrix before/after and `daum_news`/`news1` additions
    - mapped-but-uncallable rejection
    - partial/blocked external-blocked fail-closed behavior
    - explicit sibling path mismatch
    - stale and malformed artifact rejection
    - pipeline exception catch/fail-closed

## Callable source matrix snapshot
- Before (manager-only phase):
  - `daum_news`: `callable=false`, `path=null`
  - `news1`: `callable=false`, `path=null`
- After (manager + direct factories):
  - `daum_news`: `callable=true`, `path=direct_factory`
  - `news1`: `callable=true`, `path=direct_factory`
- `added_by_factory`: `["daum_news", "news1"]`
- `removed_by_factory`: `[]`

## Verification commands run
1. `py -m unittest tests.test_daily_source_collection_executor tests.test_source_intake_release_candidate -v`
   - Result: 14 tests, **14 passed**.
2. `py -m unittest tests.test_collector_readiness_registry tests.test_validated_topic_input_adapter tests.test_topic_input_quality_gate tests.test_validated_topic_candidate_pipeline -v`
   - Result: 9 tests, **9 passed**.
3. `py -m compileall modules/source_intake tests/test_daily_source_collection_executor.py tests/test_source_intake_release_candidate.py`
   - Result: compile completed successfully (exit code 0).

## Failure path coverage implemented
- `mapped_unreachable`, `readiness_callability_mismatch`, `non_ready_sources_blocked`, `pipeline_exception`, and `gap_path_sibling_mismatch` are all surfaced as deterministic no-candidate fail-closed outcomes in tests.

## Zero-network evidence
- Daily executor tests already patch `socket.create_connection`, `socket.socket.connect`, and `urllib.request.urlopen` to prevent live I/O.
- Daum/News1 direct-factory test uses patched `DaumNewsCollector` and `News1Collector` classes returning local fake payloads.

## Remaining unsupported/blocked sources
- Sources still mapped-only and not direct-factory-backed remain blocked unless runtime manager implements matching methods (e.g., `naver_news` in mapped-unreachable coverage).
- No WorkflowEngine/Git/network/API changes were made in this lane.

## No-work items and blockers
- None remaining for this lane scope.
