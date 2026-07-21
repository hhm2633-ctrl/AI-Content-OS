# AUTO SPARK STATUS — READINESS REGISTRY (Contract-only, 2026-07-15)

- objective: create a fail-closed collector readiness registry for downstream selection checks
- input: `source_intake_status_bundle.json` from refreshed readiness truth
- inputs consumed:
  - `readiness_status_counts`
  - `classification_source_count`
  - `collection_gap_report.json` (sibling file) `source_status_by_readiness`

## Contract
- deterministic load from an explicit bundle path argument
- no implicit network or mutable global state
- canonical readiness states:
  - `ready`
  - `partial`
  - `blocked`
  - `external_blocked`
- only exact `ready` is selectable
- strict fail-closed on:
  - missing/undecodable files
  - malformed JSON or malformed source payload
  - duplicate `source_id`
  - unknown status in source-by-readiness input
  - unknown source lookup
  - count mismatch (`classification_source_count`, `source_count`, and readiness count-sum)
- clear reason code only, without credentials or large payloads

## API
- `load_collector_readiness_registry(source_intake_status_bundle_path) -> CollectorReadinessRegistry`
- `CollectorReadinessRegistry.get(source_id) -> dict`
- `CollectorReadinessRegistry.require_ready(source_id) -> dict or raise`
- reason codes:
  - `missing_file`
  - `malformed_json`
  - `duplicate_source`
  - `unknown_status`
  - `count_mismatch`
  - `unknown_source`
  - `source_not_ready`
  - `ok`
