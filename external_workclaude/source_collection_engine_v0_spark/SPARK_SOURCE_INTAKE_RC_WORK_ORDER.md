# Codex Spark Work Order — Source Intake Release Candidate

## Objective

Build one zero-network, fail-closed Source Intake release-candidate gate and correct the smallest
general executor wiring defect that currently makes mapped `daum_news` and `news1` unreachable.
The RC must report callable runtime truth, reject stale or inconsistent readiness artifacts, and
compose the existing candidate pipeline only after every preflight gate passes. Do not connect it
to WorkflowEngine or TopicEngine.

## Exclusive owned files

- `modules/source_intake/daily_collection_executor.py`
- `tests/test_daily_source_collection_executor.py`
- `modules/source_intake/source_intake_release_candidate.py` (new)
- `tests/test_source_intake_release_candidate.py` (new)
- `external_workclaude/source_collection_engine_v0_spark/AUTO_SPARK_STATUS_SOURCE_INTAKE_RC.md`
  (new)

No other file may be changed.

## Prohibited files and actions

- Do not edit `modules/trend_collector/`, config, storage outputs, WorkflowEngine, TopicEngine,
  shared project documents, or any Claude-owned file.
- Do not use live network, Browser/Chrome, logins, credentials, external APIs, publishing, or Git.
- Do not weaken assertions, add per-source hardcoded success exceptions, fabricate metrics, or
  auto-promote `partial`, `blocked`, or `external_blocked` sources.
- Do not run `py -m src.main` in this lane.

## Required reading

1. `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, and current work-order board.
2. `daily_collection_executor.py`, `source_intake_consistency_validator.py`,
   `collector_readiness_registry.py`, `validated_topic_input_adapter.py`,
   `topic_input_quality_gate.py`, and `validated_topic_candidate_pipeline.py`.
3. Their focused tests and the latest Spark executor/readiness/candidate status files.
4. The historical `storage/source_intake/2026-07-14/` artifacts only as read-only fixtures.

## Implementation contract

1. Fix `daum_news` and `news1` reachability through the existing general direct-factory seam using
   their existing collector classes. Do not change collector implementations.
2. Preserve explicit manager methods when supplied; direct factories are fallback injection only.
3. Ensure each executor call starts with fresh state and never performs live network in tests.
4. The new RC preflight must derive executable support from actual callable manager methods or
   direct factories, never from `COLLECTOR_METHODS` membership alone.
5. It must detect mapping-only unreachable sources, readiness claims that disagree with callability,
   missing/malformed/stale artifact sets, source-set mismatches, and inconsistent explicit versus
   sibling gap-report paths.
6. It must keep `partial`, `blocked`, and `external_blocked` fail-closed.
7. Only after preflight `GO` may it call the existing validated candidate pipeline. Any defect must
   return compact diagnostics and zero candidates without raising.
8. No scoring, final topic selection, routing, runtime integration, or storage writes.

## Tests and verification

Add tests for:

- Daum and News1 direct-factory reachability with injected zero-network fakes;
- explicit manager method precedence;
- sequential-call state isolation;
- mapped-but-uncallable detection;
- stale/malformed/mismatched artifact rejection;
- readiness versus runtime truth disagreement;
- explicit/sibling gap path mismatch;
- successful preflight-to-candidate composition;
- every failure path returning zero candidates without exception leakage.

Run exactly:

```text
py -m unittest tests.test_daily_source_collection_executor tests.test_source_intake_release_candidate -v
py -m unittest tests.test_collector_readiness_registry tests.test_validated_topic_input_adapter tests.test_topic_input_quality_gate tests.test_validated_topic_candidate_pipeline -v
py -m compileall modules/source_intake tests/test_daily_source_collection_executor.py tests/test_source_intake_release_candidate.py
```

If a failure requires editing a prohibited file, stop and report `NO_GO` without expanding scope.

## Handoff

Write the status file with root cause, exact diff, callable source matrix before/after, commands and
counts, zero-network evidence, remaining unsupported/blocked sources, and `GO` or `NO_GO`. Final
message must list changed files, checks, blockers, and confirm no WorkflowEngine/Git/network work.
