## not implemented
- `build_source_intake_status_bundle(...)` is standalone and has no scheduler/CLI entry yet.
- No consumer contract is enforced for downstream status display yet.

## tests
- Added: `tests/test_source_intake_status_bundle.py`
  - all-present fake directory
  - missing artifact handling
  - run helper writes `source_intake_status_bundle.json`
  - smoke test against `storage/source_intake/2026-07-14` when all artifacts exist
  - no `commerce_detail` in produced bundle
- Validation: `py -m unittest tests.test_source_intake_status_bundle -v`

## next light Spark tasks only
- Add one CLI command path that calls `run_source_intake_status_bundle(...)`.
- Normalize `top_queue_sources` payload to objects if downstream needs rank/status context.
