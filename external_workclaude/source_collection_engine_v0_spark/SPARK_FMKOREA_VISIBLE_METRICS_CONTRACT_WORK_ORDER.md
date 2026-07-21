# Spark Work Order — FMKorea Visible Metrics Contract

## Objective

Make the Source Intake configuration honest about FMKorea list-page visible metrics. The collector
already records views as unavailable because that value is not visible; align the expected-metrics
contract and its focused test. Do not execute tests or compile.

## Exclusive owned files

- `config/source_intake_sources.json`
- `tests/test_source_intake_metrics.py`
- `external_workclaude/source_collection_engine_v0_spark/AUTO_SPARK_STATUS_FMKOREA_VISIBLE_METRICS.md`

## Prohibited files/actions

- Change only the `fmkorea` expected-metrics assertion/config entry; do not alter other sources.
- Do not edit collectors, executor, storage, shared docs, WorkflowEngine, or Git.
- No network/browser, tests, compile, or full workflow.

## Required reading

- `AGENTS.md`, this work order, `config/source_intake_sources.json`,
  `tests/test_source_intake_metrics.py`, and the FMKorea collector's visible-metric parser.

## Contract

- Expected FMKorea metrics must contain only values visible on the collected list page.
- Preserve rank/comments/likes expectations and do not fabricate views.
- Keep JSON schema/source ordering unchanged.

## Handoff

- Status `IMPLEMENTATION_COMPLETE_AWAITING_JOINT_TEST`, verification `PENDING`, decision `GO/NO-GO`.
