# Spark Work Order — DCInside Collector Implementation Only

## Objective

Implement a zero-live-network, fixture/cache-ready `DcinsideCollector` by reusing the existing
`DcinsideParser`. Do not execute tests or compile; CTO runs one joint verification after the
separate PPOMPPU lane is complete.

## Exclusive owned files

- `modules/trend_collector/dcinside_collector.py` (new)
- `tests/test_dcinside_collector.py` (new)
- `external_workclaude/source_collection_engine_v0_spark/AUTO_SPARK_STATUS_DCINSIDE_IMPLEMENTATION.md` (new)

## Prohibited files and actions

- Do not edit `modules/trend_collector/dcinside_parser.py` or its existing test.
- Do not edit PPOMPPU, executor, config, storage, WorkflowEngine, shared project docs, or any other code/test.
- Do not use browser, live network, login, cookies, credentials, proxy, CAPTCHA bypass, or private APIs.
- Do not collect article bodies, images, writer identity, IP, profiles, or comment bodies.
- Do not run tests, compile, full workflow, or Git.

## Required reading

- `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, this work order.
- `modules/trend_collector/dcinside_parser.py`, `tests/test_dcinside_parser.py`.
- `modules/trend_collector/theqoo_collector.py`, `modules/common/service_diagnostic.py` for local contracts.

## Implementation contract

- Class: `DcinsideCollector`; dependency-injectable fixture fetcher and existing parser reuse.
- Default collection must fail closed with `live_activation_not_approved`; never infer a live board URL.
- Approved fixture input may use an explicit `board_id` and synthetic HTML only.
- Cache: `storage/cache/dcinside_cache.json`; bounded retry count must not exceed existing defaults.
- Preserve visible list metadata only; do not fabricate metrics.
- Dedup canonical URL first, normalized title second, deterministic first occurrence wins.
- Required status: attempted, success, count, failed_reason, fallback_reason, final_error_type,
  collection_method, used_cache, cache_path, retry_enabled, retry_count, service_diagnostic.
- Tests must be zero-network and cover parser delegation, output mapping, URL/title dedup, disabled
  activation, valid cache, malformed fixture, forbidden identity/body fields, and diagnostic honesty.

## Completion checks and handoff

- Only the three owned files changed.
- Status: `IMPLEMENTATION_COMPLETE_AWAITING_JOINT_TEST`; Verification: `PENDING`.
- List unexecuted tests and limitations. No test-pass claim.

