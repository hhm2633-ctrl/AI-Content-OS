# AUTO SPARK STATUS — TOPIC INPUT ADAPTER (Validated source-intake → topic-engine adapter)

- objective: add pure adapter for explicit `daily_shallow_collection` payload/path + already-loaded `CollectorReadinessRegistry` and emit TopicEngine-compatible trend_result shape
- status: implemented
- owned files:
  - modules/source_intake/validated_topic_input_adapter.py (new)
  - tests/test_validated_topic_input_adapter.py (new)
  - external_workclaude/source_collection_engine_v0_spark/AUTO_SPARK_STATUS_TOPIC_INPUT_ADAPTER.md (new)
- key behavior:
  - explicit payload path or dict input only
  - no global files, no network/cache, no mutation
  - fail-closed on malformed top-level payload, malformed items list, and invalid registry
  - deterministic ordering preserved, no selection logic
  - source readiness gating uses `registry.require_ready` through `registry.get`
- test contract: exactly 3 named tests added in `tests.test_validated_topic_input_adapter`
- test results target: not yet run in this run (see handoff)
