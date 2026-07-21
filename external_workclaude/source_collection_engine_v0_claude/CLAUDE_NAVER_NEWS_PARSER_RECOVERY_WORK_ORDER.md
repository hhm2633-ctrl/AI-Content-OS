# Claude Work Order — Naver News Parser Recovery

## Objective

Recover Naver News RSS/HTML parsing offline with fixture-driven parser hardening while preserving
API Hub, bounded fallback, cache, and diagnostic behavior. Implementation and tests first; do not
execute tests or compile. Do not use live network or browser access.

## Exclusive owned files

- `modules/trend_collector/naver_news_collector.py`
- `tests/test_naver_news_collector.py`
- `external_workclaude/source_collection_engine_v0_claude/AUTO_CLAUDE_STATUS_NAVER_NEWS_PARSER_RECOVERY.md`

## Prohibited files/actions

- Do not edit config, executor, other collectors/tests, storage, shared docs, WorkflowEngine, or Git.
- No browser, live network, login, credential inspection, tests, compile, or full workflow.

## Required reading

- `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, this work order.
- Current Naver collector/test and `modules/trend_collector/naver_news_parser_v2.py` for compatibility.

## Contract

- Accept RSS XML whose item tags may be namespaced or case-varied without raising.
- Harden HTML extraction against attribute-order changes and extract visible title/link/summary only.
- Preserve API Hub -> RSS -> HTML -> existing fallback chain and all diagnostic reason codes.
- Never fabricate publisher, summary, metrics, or popularity.
- Add focused offline fixtures for the recovered forms and malformed input.

## Handoff

- Status `IMPLEMENTATION_COMPLETE_AWAITING_JOINT_TEST`, verification `PENDING`, decision `GO/NO-GO`.
- List changed files and unexecuted checks.
