# Spark Work Order — Source Agreement Implementation

## Objective

Implement deterministic offline source-agreement clustering for shallow collection items. Write
production code and focused tests, but do not execute tests or compile. CTO runs one joint batch
after the independent collection-quality lane finishes.

## Exclusive owned files

- `modules/source_intake/source_agreement.py` (new)
- `tests/test_source_agreement.py` (new)
- `external_workclaude/source_collection_engine_v0_spark/AUTO_SPARK_STATUS_SOURCE_AGREEMENT.md` (new)

## Prohibited files/actions

- Do not edit collectors, executor, config, storage, WorkflowEngine, shared docs, Claude-owned files,
  CTO quality files, or any existing test.
- No browser/network/login/credentials, no test/compile/workflow/Git.

## Required reading

- `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, this work order.
- `modules/source_intake/validated_topic_candidate_pipeline.py`,
  `modules/source_intake/topic_input_quality_gate.py`, and their focused tests for output style only.

## Contract

- Public function: `build_source_agreement(items, min_distinct_sources=2, title_similarity_threshold=0.6)`.
- Pure offline/deterministic; never modify inputs or write files.
- Normalize canonical URLs by removing fragments and tracking query parameters deterministically.
- Cluster exact canonical URL first, then normalized-title token similarity.
- A cluster is agreed only when it contains at least `min_distinct_sources` distinct non-empty
  `source_id` values. Repeats from one source never create agreement.
- Preserve first-occurrence representative title/link and source order; do not fabricate claims.
- Output counts for total clusters, agreed clusters/items, single-source clusters/items, plus cluster
  rows containing source IDs, distinct source count, agreement status, and member indexes.
- Missing/malformed fields must fail closed into single-source/unattributed rows, never exceptions.
- Tests cover URL agreement, title agreement, same-source duplicate rejection, threshold boundary,
  deterministic order, malformed input, input immutability, and empty input.

## Handoff

- Only three owned files changed.
- Status `IMPLEMENTATION_COMPLETE_AWAITING_JOINT_TEST`, verification `PENDING`, decision `GO`.
- List unexecuted tests; no pass claim.

