# QA Report V1.6 -- Publish Blocker Provenance Audit

Overall: **PASS** (audit-quality self-check, not a code test suite -- this task was read-only by
instruction)

## Self-check against the task's requirements

- [x] Read-only only: no file in `modules/`, `src/`, `tests/`, `storage/`, or any documentation
  file was modified. Only 4 new files were written, all inside
  `external_workclaude/content_portfolio_v1/`.
- [x] Every one of the 6 blockers classified into one of the 5 allowed categories
  (`EXPECTED_USER_INPUT_BLOCKER` x3, `EXPECTED_DERIVED_BLOCKER` x2, `INDEPENDENT_TECHNICAL_DEFECT`
  x1, zero `STALE_OR_MISLEADING_BLOCKER`, zero `UNKNOWN`).
- [x] Each blocker's originating module/function identified by reading the actual source
  (`modules/publishing/publishing_module.py`, `modules/compliance/card_news_publish_gate.py`,
  `src/workflow_engine.py`), not inferred from naming alone.
- [x] Each blocker's binding to `output_set_id = f2281e14df8d4ab68a46152e93e9029b` verified by
  direct read of every location the code emits it (top-level `blocker_codes`,
  `operations.blocking_reasons`, `operator_upload_package.blocker_codes`,
  `publish_queue.items[].blocker_codes`, `pre_publish_attestation.compliance_result.blocking_reasons`) --
  not sampled from one location and assumed elsewhere.
- [x] `PUBLISH_MANIFEST_PATH_MISMATCH` judged specifically: confirmed **not** merely a
  derived-emptiness-of-a-blocked-package artifact, but a genuine independent defect (absolute vs.
  repo-relative path handling in `_build_pre_publish_attestation`), reproduced against the exact
  4x `final_cards_invalid` entries present in the real result JSON, and independently corroborated
  by the literal absolute path printed in this session's own V1.5 workflow console log.
- [x] `PUBLISH_COMMITTED_ATTESTATION_INVALID` judged specifically: confirmed to be a pure
  aggregate over the 11 `required_readiness_checks` (source: `rebind_committed_paths`), with the
  exact 5 failing sub-fields identified (`manifest_paths_match`, `rights_passed`,
  `evidence_passed`, `compliance_passed`, `manual_image_clear`) and the 6 passing sub-fields
  identified (`attestation_schema_valid`, `exactly_four_cards`, `card_files_exist`,
  `output_set_match`, `qa_passed`, `upload_mode_manual`) -- not assumed to be schema/identity
  related, confirmed by reading which specific checks were true/false in the real JSON.
- [x] Image Strategy "real image source" judged specifically: confirmed to be a strategy
  recommendation string (`"post_capture"`), not a URL, not a downloaded file, not rights-verified,
  and confirmed never promoted to a publish-ready asset (`render_allowed: false`,
  `classification: technical_fixture_not_publish_approved`, `actual_publish: false` throughout).
- [x] No GO/NO-GO judgment made by inference -- every conclusion above cites the specific JSON
  field or source line it was read from.

## What was NOT done (out of scope, correctly)

- No code fix was applied for the `PUBLISH_MANIFEST_PATH_MISMATCH` independent defect, even though
  its root cause and exact fix location were identified. Per instruction, this audit reports
  reproduction evidence and the owning file/function only.
- No test was added or modified.
- No workflow run was performed in this task (the target output set was already produced by the
  prior V1.5 task's single run).
- No Git operation was performed.

## Files produced (all inside `external_workclaude/content_portfolio_v1/`)

- `PUBLISH_BLOCKER_AUDIT_V1_6.md`
- `PUBLISH_BLOCKER_MATRIX_V1_6.json`
- `ASSET_PROVENANCE_AUDIT_V1_6.md`
- `QA_REPORT_V1_6.md` (this file)
