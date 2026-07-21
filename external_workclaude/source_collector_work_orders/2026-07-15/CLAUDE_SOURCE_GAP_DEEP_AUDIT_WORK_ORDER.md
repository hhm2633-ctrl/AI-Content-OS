# Claude Fable 5 Work Order — Source Gap Deep Audit

## Objective

Audit the repository's real source-intake capability, separate stale artifact claims from callable
runtime truth, classify every configured source by policy, technical feasibility, and CardNews ROI,
then produce exactly one evidence-backed next-source implementation contract. Do not implement it.

## Exclusive owned files

- `external_workclaude/source_collector_work_orders/2026-07-15/CLAUDE_SOURCE_GAP_DEEP_AUDIT.md`
- `external_workclaude/source_collector_work_orders/2026-07-15/SOURCE_IMPLEMENTATION_DECISION_MATRIX.json`

No other file may be changed.

## Prohibited files and actions

- Do not edit production code, tests, config, storage, shared project documents, or WorkflowEngine.
- Do not run Git commands.
- Do not open or control Browser/Chrome.
- Do not log in, use cookies/credentials/tokens, bypass robots/captcha, reverse engineer private
  APIs, or collect live comments, user identifiers, profiles, or other personal/UGC data.
- Do not create raw HTML/JSON fixtures or implement a collector.

## Required reading

1. `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, and its Mandatory Reading Order.
2. `.claude/skills/cto_operating_system/SKILL.md`, `.claude/skills/planning.md`,
   `.claude/skills/domain/trend_engine.md`, and `.claude/skills/review.md`.
3. `config/source_intake_sources.json`, `config/news_category_profiles.json`, and
   `config/trend_sources.json`.
4. `modules/source_intake/daily_collection_plan.py`, `daily_collection_executor.py`,
   `source_capability_map.py`, `collector_readiness_registry.py`, and
   `validated_topic_candidate_pipeline.py`.
5. Current collector/parser inventory and focused tests under `modules/trend_collector/` and
   `tests/`.
6. `storage/source_intake/2026-07-14/` gap/status/queue artifacts, treating them as historical
   evidence rather than current truth.
7. Existing 2026-07-15 Naver recon contracts and Spark readiness/executor/candidate reports.

## Mandatory truth checks

- Distinguish `COLLECTOR_METHODS` membership from actual callability. A source is executable only
  when the manager method is callable or a direct factory exists.
- Recheck the current suspected wiring defect: `daum_news` and `news1` are mapped but have neither
  a callable `TrendSourceManager` method nor a direct factory in the current executor.
- Do not mistake `dcinside_parser.py` for a production collector or the Instiz diagnostic for a
  collector.
- Record that `mk_economy` is limited to the approved MK Pick surface.
- Treat Naver comments/reactions as `FIXTURE_ONLY` unless a new explicit compliance approval exists.
- `access_status: ok` and HTTP 200 are not permission to collect or republish.

## Deliverables

The Markdown audit must include:

- actual callable truth versus stale artifact truth;
- every configured source and every daily-plan source;
- collector/parser/diagnostic/executor/fallback status;
- robots/terms/authentication/privacy/copyright risk;
- lane coverage and CardNews ROI;
- one decision per source: `GO`, `FIXTURE_ONLY`, `BLOCKED`, or `DEFER`;
- exactly one selected next source and a full implementation contract covering allowed surface,
  fields, rank semantics, schema, dedup, timestamps, attribution, retry/cache/fallback, diagnostics,
  executor connection point, expected production/test files, and later verification commands;
- an explicit implementation `GO` or `NO_GO` gate.

The JSON matrix must use schema version `source_implementation_decision_matrix_v1`, contain each
configured source exactly once, and include top-level actual supported/unsupported lists, stale
artifact paths, selected next source, decision, reason, and implementation contract. Each source
entry must record configuration/plan/collector/callable-executor state, implementation scope,
artifact staleness, evidence paths, policy and access evidence, credential/PII/robots risks, lane
coverage, ROI/feasibility/safety scores, decision, reason, and next action.

## Selection and completion gates

Select one source only when it has a public and policy-safe surface, needs no login/credentials,
does not depend on user/comment data, supports deterministic offline tests, improves weak lane
coverage, and fits existing schemas with a small reversible change. If no candidate satisfies the
gate, select the closest candidate but mark it `FIXTURE_ONLY` or `BLOCKED` and declare `NO_GO`.

Validate the JSON with a real parser, prove config-source omissions and duplicates are zero, prove
only the two owned files changed, and report in Korean: files, actual/stale difference, decision
counts, selected source, GO/NO_GO, blockers, and validation.
