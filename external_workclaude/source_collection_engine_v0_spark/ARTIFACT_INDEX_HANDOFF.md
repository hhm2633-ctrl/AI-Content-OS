## implemented
- Added `modules/source_intake/source_intake_artifact_index.py`
  - `build_source_intake_artifact_index(today=None, root=None)` now returns per-artifact
    status for expected source-intake outputs:
    - `present`
    - `size_bytes`
    - `last_modified`
    - `path`
  - Missing files are tolerated; output includes `present_artifacts` and `missing_artifacts`.
- Added `run_source_intake_artifact_index(today=None, root=None)` that writes
  `storage/source_intake/<today>/source_intake_artifact_index.json` and returns write status.
- Added `tests/test_source_intake_artifact_index.py`
  - all missing artifacts
  - some artifacts present
  - run writes persisted JSON
  - no `commerce_detail` in result payload

## not implemented
- No scheduler/CLI hook yet.
- No integration wiring in workflow orchestration yet (index exists only as a standalone task).

## next light Spark tasks only
- Add a tiny status CLI/entry call site that triggers `run_source_intake_artifact_index`.
- Add a smoke test that validates output against `storage/source_intake/2026-07-14` when available.
