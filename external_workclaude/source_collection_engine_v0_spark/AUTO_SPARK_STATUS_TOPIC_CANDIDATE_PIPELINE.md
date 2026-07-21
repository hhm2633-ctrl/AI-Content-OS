# AUTO SPARK STATUS — TOPIC CANDIDATE PIPELINE (Facade)

- objective: compose registry + adapter + quality gate into one explicit callable
- status: implemented
- owned files:
  - modules/source_intake/validated_topic_candidate_pipeline.py (new)
  - tests/test_validated_topic_candidate_pipeline.py (new)
  - external_workclaude/source_collection_engine_v0_spark/AUTO_SPARK_STATUS_TOPIC_CANDIDATE_PIPELINE.md (new)
- contract:
  - explicit `daily_shallow_collection`, `source_intake_status_bundle_path`,
    and `collection_gap_report_path` inputs
  - strict fail-closed sequencing:
    1) gap-report validation + registry load
    2) validated topic input adapter
    3) topic input quality gate
  - no selection, no scoring, no routing, no runtime integration
- output contract:
  - compact object with `status`, `candidates`, and `stage_diagnostics`
  - `status=closed` on any stage-closed/malformed condition with zero candidates
  - `status=candidate_ready` only when candidates exist
- test contract:
  - `test_ready_multi_source_input_produces_candidate_ready_with_composed_diagnostics`
  - `test_non_ready_or_unknown_only_input_closes_with_zero_candidates`
  - `test_malformed_registry_or_adapter_input_closes_without_exception_leakage_or_fabrication`
