# Claude Fable 5 Work Order — Ruliweb + Dogdrip Collector Implementation

## Objective

Implement both remaining fast community-source collectors in one Claude Fable 5 job. Produce
fixture/cache-ready code and focused zero-network tests. Do not run tests or compile; CTO owns the
shared executor integration and one final joint verification after handoff.

## Exclusive owned files

- `modules/trend_collector/ruliweb_collector.py` (new)
- `tests/test_ruliweb_collector.py` (new)
- `modules/trend_collector/dogdrip_collector.py` (new)
- `tests/test_dogdrip_collector.py` (new)
- `external_workclaude/source_collection_engine_v0_claude/AUTO_CLAUDE_STATUS_RULIWEB_DOGDRIP_IMPLEMENTATION.md` (new)

## Prohibited files and actions

- Do not edit `modules/source_intake/daily_collection_executor.py` or its tests; CTO owns them.
- Do not edit any existing collector/parser/test, config, storage, WorkflowEngine, shared project
  docs, CardNews, Publishing, or unrelated file.
- Do not use browser, Chrome, live network, WebFetch/WebSearch, login, cookies, credentials, proxy,
  CAPTCHA bypass, private APIs, or access-control bypass.
- Do not collect article/post bodies, images, comment bodies, writer identity, user IDs, profiles,
  IP addresses, or other PII/UGC payloads.
- Do not run tests, compile, full workflow, or Git.

## Required reading

1. `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, and this work order.
2. `modules/trend_collector/ppomppu_collector.py` and `tests/test_ppomppu_collector.py` as the
   current fixture-only safety pattern.
3. `modules/trend_collector/theqoo_collector.py` and `modules/common/service_diagnostic.py` only
   for the existing item/status contracts.
4. `config/source_intake_sources.json` only the `ruliweb` and `dogdrip` entries.

## Shared implementation contract

- Classes: `RuliwebCollector`, `DogdripCollector`.
- Dependency-injectable fixture fetcher and deterministic parser.
- Default `collect()` must fail closed with `live_activation_not_approved`; no built-in live fetch,
  endpoint guessing, browser path, or network activation.
- Fixture execution requires both an explicit fixture config gate and an injected fetcher.
- Parse only synthetic public-list fixture metadata: title, same-site canonical link, visible
  published time/category, visible list metrics, and one-based rank.
- Missing visible metrics stay `None`; never infer or fabricate engagement/popularity.
- URL-first then normalized-title dedup; deterministic first occurrence wins.
- Cache paths: `storage/cache/ruliweb_cache.json` and `storage/cache/dogdrip_cache.json`.
- Bounded retry budget no greater than 3; valid cache fallback, then `[]` with honest diagnostic.
- Required status: attempted, success, count, failed_reason, fallback_reason, final_error_type,
  collection_method, used_cache, cache_path, retry_enabled, retry_count, service_diagnostic.
- Output must exclude body/image/comment-body/identity/profile/IP/private fields.
- Keep the two implementations independent; no shared new helper file.

## Test contract

For each collector, write isolated temporary-cache tests covering:

- visible fixture field parsing;
- URL and normalized-title dedup;
- default activation fail-closed and injected fetcher not called;
- valid cache fallback after injected failure;
- malformed fixture diagnostic;
- forbidden body/image/identity fields absent;
- zero default/operational cache leakage.

Do not execute the tests.

## Completion checks and handoff

- Confirm only the five owned files changed.
- Status file: `IMPLEMENTATION_COMPLETE_AWAITING_JOINT_TEST`, decision `GO`, verification `PENDING`.
- List all unexecuted tests and limitations; do not claim tests passed.
- Final message must list files and explicitly confirm no test/compile/network/browser/Git actions.

