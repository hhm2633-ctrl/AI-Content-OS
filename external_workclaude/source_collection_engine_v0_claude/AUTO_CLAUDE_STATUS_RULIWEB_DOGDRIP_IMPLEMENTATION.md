# AUTO CLAUDE STATUS — Ruliweb + Dogdrip Collector Implementation

- **Status:** `IMPLEMENTATION_COMPLETE_AWAITING_JOINT_TEST`
- **Decision:** `GO`
- **Verification:** `PENDING`
- **Date:** 2026-07-15
- **Executor:** Claude Fable 5 (background job)
- **Work order:** `CLAUDE_RULIWEB_DOGDRIP_COLLECTOR_IMPLEMENTATION_WORK_ORDER.md`

## Files delivered (five owned files only)

1. `modules/trend_collector/ruliweb_collector.py` (new) — `RuliwebCollector`
2. `tests/test_ruliweb_collector.py` (new)
3. `modules/trend_collector/dogdrip_collector.py` (new) — `DogdripCollector`
4. `tests/test_dogdrip_collector.py` (new)
5. `external_workclaude/source_collection_engine_v0_claude/AUTO_CLAUDE_STATUS_RULIWEB_DOGDRIP_IMPLEMENTATION.md` (this file)

No other file was created or modified. `modules/source_intake/daily_collection_executor.py`,
existing collectors/parsers/tests, configs, storage, WorkflowEngine, and shared project docs were
not touched.

## Contract compliance

- Classes `RuliwebCollector` / `DogdripCollector`, mirroring the `PpomppuCollector`
  fixture-only safety pattern; the two implementations are fully independent (no shared new
  helper file).
- Dependency-injectable `fetcher` and deterministic `parser`.
- Default `collect()` fails closed with `live_activation_not_approved`; there is no built-in
  live fetch, endpoint guessing, browser path, or network activation code anywhere in either
  collector.
- Fixture execution requires BOTH `fixture_collection_enabled: true` in config AND an injected
  callable fetcher; either one missing → fail-closed path.
- Parses only synthetic public-list fixture metadata: title, same-site canonical link
  (off-site links normalize to empty), visible published time/category, visible list metrics
  (`views`, `comments`, `likes` per `config/source_intake_sources.json` expected_metrics),
  one-based `rank_position`.
- Missing visible metrics stay `None`; nothing is inferred or fabricated.
- URL-first then normalized-title (casefold) dedup; deterministic first occurrence wins.
- Cache paths: `storage/cache/ruliweb_cache.json`, `storage/cache/dogdrip_cache.json`
  (config-overridable; tests use isolated temp caches).
- Retry budget bounded: `max_retries` clamped to [0, 3]; fallback order is fixture →
  valid TTL-checked cache → `[]` with honest diagnostic.
- `last_status` carries all required keys: `attempted`, `success`, `count`, `failed_reason`,
  `fallback_reason`, `final_error_type`, `collection_method`, `used_cache`, `cache_path`,
  `retry_enabled`, `retry_count`, `service_diagnostic`
  (via `modules/common/service_diagnostic.py::build_diagnostic_from_reason`).
- Output items contain no body/image/comment-body/identity/profile/IP/private fields.

## Unexecuted tests (written, NOT run — joint verification pending)

`tests/test_ruliweb_collector.py` — `TestRuliwebCollector`:

1. `test_parses_visible_fixture_fields_without_network`
2. `test_dedupes_url_then_normalized_title`
3. `test_default_activation_is_fail_closed` (injected fetcher asserted not called)
4. `test_fixture_gate_without_fetcher_never_collects`
5. `test_valid_cache_is_used_after_injected_fixture_failure`
6. `test_malformed_fixture_records_parse_failure`
7. `test_forbidden_body_identity_and_image_fields_are_absent`
8. `test_no_default_or_operational_cache_leakage`

`tests/test_dogdrip_collector.py` — `TestDogdripCollector`: the same eight cases for
`DogdripCollector` (`storage/_tmp_dogdrip_collector` temp cache).

None of these tests were executed. No compile check, full workflow run, network/browser access,
or Git command was performed. Correctness claims are code-reading-level only.

## Known limitations

- Parsers are regex-based against synthetic fixture HTML (same approach as
  `ppomppu_collector.py`); real Ruliweb/Dogdrip markup was never fetched or inspected in this
  job, so fixture selectors are pattern-based (`subject`/`deco`/`/read/` for Ruliweb,
  `title`/`link-reset`/`/dogdrip` for Dogdrip) and may need adjustment when CTO supplies real
  captured fixtures.
- Collectors are not wired into `daily_collection_executor.py` or `TrendSourceManager`;
  shared executor integration is CTO-owned per the work order.
- `dislikes` is intentionally not emitted (not in either source's `expected_metrics`).
- Files were written in an isolated worktree
  (`.claude/worktrees/ruliweb-dogdrip-collectors`, branch
  `worktree-ruliweb-dogdrip-collectors`) because the background-session guard blocks direct
  writes to the shared checkout; no commit/push was made (Git actions prohibited by the work
  order). CTO can copy or cherry-pick the five files from the worktree during joint
  verification.

## Handoff

CTO owns: shared executor integration, running the test suites, compile check, and one final
joint verification. Verification remains `PENDING` until then.

