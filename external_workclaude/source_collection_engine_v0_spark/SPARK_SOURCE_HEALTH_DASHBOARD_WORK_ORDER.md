# Spark Work Order — Source Health / Collector Statistics Dashboard v1

## Objective

Implement the still-planned Source Health / Collector Statistics dashboard as a standalone,
offline-first Source Intake report. This lane must not change collector behavior or the source
truth that Claude Fable 5 is auditing. Implement all code first; run the tests once, in one final
batch, after implementation is complete.

## Exclusive owned files

- `modules/source_intake/source_health_dashboard.py` (new)
- `scripts/build_source_health_dashboard.py` (new)
- `tests/test_source_health_dashboard.py` (new)
- `external_workclaude/source_collection_engine_v0_spark/AUTO_SPARK_STATUS_SOURCE_HEALTH_DASHBOARD.md` (new)

One writer per file. Preserve all unrelated dirty-worktree content.

## Prohibited files and actions

- Do not edit Claude-owned audit/matrix files.
- Do not edit any collector/parser, `daily_collection_executor.py`, release-candidate code,
  config, storage artifact, WorkflowEngine, TopicEngine, shared project document, or existing test.
- Do not use Browser/Chrome, live network, credentials, external APIs, publishing, or Git.
- Do not run `py -m src.main` or the full test suite.

## Required reading

1. `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, and this work order.
2. The active Lane SC-C/SC-S/SC-D sections of `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`.
3. `modules/trend_collector/source_health_tracker.py`.
4. `modules/source_intake/source_intake_schema.py`, `collection_gap_report.py`,
   `source_intake_status_bundle.py`, and their focused tests.
5. The key shapes only from `storage/source_intake/2026-07-14/source_intake_status_bundle.json`,
   `collection_gap_report.json`, `lane_collection_summary.json`, and optional
   `storage/trends/source_health.json` / `collector_statistics.json`. Treat historical artifacts
   as artifact-reported evidence, never as current runtime truth.

## Implementation contract

Create a deterministic builder API and CLI that accept explicit input paths and an explicit output
path. No import-time writes and no default execution.

Dashboard schema: `source_health_dashboard_v1`. It must include:

- `generated_at`, input paths, input dates/timestamps, and `evidence_scope: artifact_reported`;
- freshness diagnostics (`fresh`, `stale`, `unknown`) without pretending stale data is live;
- top-level source/readiness/implementation counts and safe percentages;
- lane summaries and source rows with reported status, counts, fallback/cache/error evidence;
- collector-statistics fields when present, clearly separated from daily status;
- ordered blocker and next-action lists derived only from visible inputs;
- `data_quality` diagnostics listing missing/malformed/contradictory inputs;
- a deterministic `dashboard_status` of `ready`, `partial`, or `blocked`;
- no fabricated metrics, source availability, success, or callability.

Fail closed: malformed required JSON must return/write a valid dashboard with `blocked`, zero unsafe
derived claims, and explicit reason codes. Optional trend-health/statistics files may be absent and
must degrade to `partial` rather than raise. Percentage denominators must be zero-safe. Source rows
and blocker/action ordering must be deterministic.

The CLI must use only the standard library, expose `--status-bundle`, `--gap-report`,
`--lane-summary`, optional `--source-health`, optional `--collector-statistics`, and `--output`, and
print a compact JSON result summary. It must not choose or mutate production storage implicitly.

## Verification — run once after all implementation

Run exactly one combined test command after implementation is complete:

`py -m unittest tests.test_source_health_dashboard tests.test_source_intake_status_bundle tests.test_collection_gap_report tests.test_lane_collection_summary -v`

Then run the non-test compile check:

`py -m compileall modules/source_intake/source_health_dashboard.py scripts/build_source_health_dashboard.py tests/test_source_health_dashboard.py`

Do not run tests during implementation. If the one final test batch fails, fix from the captured
failure output and rerun that same batch once; record both attempts honestly.

## Completion checks and handoff

- Prove only the four owned files changed in this lane.
- Report schema, CLI contract, fail-closed paths, exact test count/result, compile result, and
  remaining limitations.
- Write the status file and finish with `GO` or `NO_GO`.

