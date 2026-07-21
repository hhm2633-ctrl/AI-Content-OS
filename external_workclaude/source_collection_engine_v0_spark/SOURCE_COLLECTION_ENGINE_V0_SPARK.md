# Daily Source Collection Engine V0 Spark Handoff

## implemented
- Added `modules/source_intake/daily_collection_plan.py` with `build_daily_collection_plan(account_profiles, source_capabilities=None, today=None)`.
- Added deterministic lane planning for:
  - `news_society_economy`
  - `entertainment_news`
  - `dopamine_community`
  - `beauty_fashion`
  - `lifestyle_knowledge`
- Added per-lane outputs:
  - `lane_id`
  - `shallow_profiles`
  - `excluded_sources` (with skip reasons from capability map)
  - `shallow_only=true`
  - `deep_dive_enabled=false`
  - `deep_dive_trigger_policy` with numeric threshold + repeat-source requirement
  - `storage_policy` using `storage/source_intake` and `source_data_root()` external root
- Added fail-closed handling for unknown lane IDs.
- Added `tests/test_daily_source_collection_plan.py` for required lane coverage, fail-closed behavior, blocked-source recording, policies, storage policy pathing, and no `commerce_detail` wording.

## not implemented
- Did not update any shared docs in `CHANGELOG.md`, `PROJECT_SNAPSHOT.md`, or other restricted doc files.

## tests run
- `py -m unittest tests.test_daily_source_collection_plan tests.test_source_intake_schema tests.test_source_intake_metrics tests.test_news_category_profiles -v`
- `py -m compileall modules/source_intake`

## next Claude task
- If accepted, integrate this plan schema into the next workflow stage that consumes daily source collection plans and adds strict persistence fields for downstream execution.
