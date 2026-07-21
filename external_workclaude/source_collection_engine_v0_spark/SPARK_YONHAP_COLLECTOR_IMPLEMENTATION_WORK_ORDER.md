# Spark Work Order — Yonhap Collector Implementation Only

## Objective

Implement the fixture-driven Yonhap headline-list collector selected by the CTO recovery audit.
Write production code and its focused tests, but do not execute any test or compile command. Final
verification happens once after the separate CTO executor-integration lane is also complete.

## Exclusive owned files

- `modules/trend_collector/yonhap_collector.py` (new)
- `tests/test_yonhap_collector.py` (new)
- `external_workclaude/source_collection_engine_v0_spark/AUTO_SPARK_STATUS_YONHAP_IMPLEMENTATION.md` (new)

## Prohibited files and actions

- Do not edit `modules/source_intake/daily_collection_executor.py` or its test; CTO owns them.
- Do not edit any other collector, config, storage, WorkflowEngine, TopicEngine, shared project doc,
  Claude/CTO audit output, or existing test.
- Do not use browser/live network/login/cookies/credentials/proxy/captcha bypass/private APIs.
- Do not collect article bodies, images, comments, user IDs, profiles, or other UGC/PII.
- Do not run tests, compile, full workflow, or Git.

## Required reading

1. `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, and this work order.
2. `external_workclaude/source_collector_work_orders/2026-07-15/SOURCE_IMPLEMENTATION_DECISION_MATRIX.json`
   only the `implementation_contract` for `yonhap`.
3. `modules/trend_collector/news1_collector.py`, `newsis_collector.py`, `retry_policy.py`, and
   `modules/common/service_diagnostic.py` as local contracts.
4. `tests/test_news1_collector.py` and `tests/test_newsis_collector.py` for fixture style only.

## Implementation contract

- Class: `YonhapCollector` with dependency-injectable fetch behavior and deterministic parsers.
- Exact live list URL must remain disabled/unpinned until a manual robots/terms check. The default
  production fetch path must fail closed with an explicit `live_activation_not_approved` diagnostic
  rather than guessing an endpoint.
- Parse only synthetic/approved public-list fixture shapes: headline title, canonical link, visible
  published time, category, and one-based list rank.
- Output existing trend-item fields only. Publisher is `연합뉴스`; missing visible fields stay empty.
- Dedup canonical URL first, normalized title second, deterministic first occurrence wins.
- Never create views/likes/comments/popularity or article body/image/user data.
- Reuse bounded retry semantics without increasing retry counts. Cache path must be
  `storage/cache/yonhap_cache.json`; valid cache is allowed, then return `[]` with diagnostic.
- Required `last_status`: attempted, success, count, failed_reason, fallback_reason,
  final_error_type, collection_method, used_cache, cache_path, retry_enabled, retry_count, and
  service_diagnostic.
- Tests must be zero-network and cover fixture parsing, URL/title dedup, forbidden-field absence,
  disabled live activation, valid-cache fallback, malformed fixture, and diagnostic honesty.
- Do not execute those tests in this lane.

## Completion and handoff

- Prove only the three owned files were changed by this lane.
- Status file must say `IMPLEMENTATION_COMPLETE_AWAITING_JOINT_TEST`, list unexecuted test names,
  limitations, and no claim that tests passed.
- Finish with implementation `GO` or `NO_GO`; verification remains `PENDING`.

