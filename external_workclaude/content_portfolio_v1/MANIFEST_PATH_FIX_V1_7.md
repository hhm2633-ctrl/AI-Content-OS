# Manifest Committed-Path Fix V1.7

## Exact code root cause

`WorkflowEngine._run_card_news_output_transaction` builds the CardNews pre-publish attestation
(`_build_pre_publish_attestation`) **before** `transaction.stage()` runs, using
`card_news_result["cards"][*]["card_path"]` values that, at that point, are still the run-scoped
paths CardNewsModule just wrote them to. `CardNewsOutputSetTransaction`'s own `self.root` is
`Path(repository_root).resolve()` (absolute), so
`self.card_news_module.card_dir = run_dir / "card_news"` is also absolute, and
`CardNewsModule._create_card`/`_create_card_with_layout` return `str(output_path)` -- an absolute
filesystem path string -- as `card_path`.

`CardNewsPublishGate._check_final_cards` (`modules/compliance/card_news_publish_gate.py`, not
modified) correctly rejects any absolute path via `_repo_relative_path`'s
`Path(reference).is_absolute()` check. Every one of the four cards was therefore rejected with
`final_cards_invalid` (confirmed: exactly 4 such entries in the real V1.5/V1.6 result JSON, one
per card index), leaving the attestation's `"cards"` list permanently empty for that run.
Downstream, `PublishingModule._resolve_package_readiness`'s
`manifest_paths_match = len(manifest_paths) == 4 and card_paths == manifest_paths` then always
failed (`len([]) == 4` is false), firing `PUBLISH_MANIFEST_PATH_MISMATCH` regardless of whether
rights/evidence would otherwise have passed. Full original trace:
`external_workclaude/content_portfolio_v1/PUBLISH_BLOCKER_AUDIT_V1_6.md` §5.

## What was fixed -- the call order / path-binding change

No change was made to `modules/compliance/card_news_publish_gate.py`,
`modules/publishing/publishing_module.py`, or `modules/card_news/card_news_module.py` (all
forbidden and, in fact, unnecessary -- the defect was purely a sequencing issue in
`src/workflow_engine.py`).

Added a new step, `WorkflowEngine._correct_committed_attestation`, called in
`_run_card_news_output_transaction` immediately after `transaction.promote()` and
`CardNewsOutputSetTransaction.resolve_active()` both succeed (i.e., strictly after the transaction
has genuinely committed -- if `stage()`, `rebind_publishing()`, or `promote()` ever raises, this
new code is never reached, so it can never produce a "successful" attestation from a failed
commit; new test `test_commit_failure_after_staging_never_reaches_attestation_correction`
confirms this).

At that point the four PNGs genuinely exist at their immutable, repo-relative committed paths
(`storage/output_sets/card_news/sets/<id>/cards/card_news_{1..4}.png`, already rewritten to this
canonical form by `CardNewsOutputSetTransaction.stage()`'s existing `_rewrite_paths` logic). The
new method:

1. Calls the same, unmodified `_build_pre_publish_attestation` again, now using
   `card_news_result["cards"]` (already canonical, repo-relative, `.runs`/`.staging`-free) --
   this calls the real, unmodified `CardNewsPublishGate` a second time with correct inputs; it
   does not fake or bypass the compliance decision.
2. Calls the same, unmodified `PublishingModule._resolve_package_readiness` again with the
   corrected attestation, producing a fresh `readiness_checks`/`blocking_reasons` where
   `manifest_paths_match` is now `True` and every other check (`rights_passed`, `evidence_passed`,
   `compliance_passed`, `manual_image_clear`) is untouched and still correctly `False`.
3. Calls the same, unmodified `PublishingModule.rebind_committed_paths` again with the corrected
   `readiness_checks`, which recomputes `attestation_invalid` (still `True`, since rights/
   evidence/manual-image still fail) and re-adds `PUBLISH_COMMITTED_ATTESTATION_INVALID`
   accordingly -- reusing the exact existing aggregation logic rather than re-implementing it.
4. Persists the corrected `card_news_result`/`publishing_result` into the already-committed JSON
   files via a new, minimal `_atomic_write_committed_json` helper (temp file + `fsync` +
   `os.replace`-with-retry, mirroring the existing `_write_compatible_output_set_receipts` style)
   -- so the correction is visible both in the immutable committed output set and in every
   legacy/global receipt `_write_compatible_output_set_receipts` mirrors afterward.

This correction only ever touches the embedded `card_news_manifest` / `pre_publish_attestation` /
`readiness_checks` / `blocker_codes` / `package_readiness` / `operations` fields inside the two
JSON files -- it never touches `manifest.json`, `active.json`, any PNG, the top-level `cards`
list, or `card_paths` (all already correct), so
`CardNewsOutputSetTransaction._validate_directory`'s existing invariants (ID binding, `card_paths`
identity, `release_ready` consistency, no `.runs` leakage) remain satisfied -- verified directly
against the real post-run committed files (see Verification below) and by the full existing
21-test suite continuing to pass unmodified.

## Changed files

- `src/workflow_engine.py` -- added `_correct_committed_attestation` and
  `_atomic_write_committed_json`; added one call site in `_run_card_news_output_transaction`.
  No other method changed.
- `tests/test_workflow_card_news_output_receipts.py` -- added 5 new tests (see below). No
  existing test modified.
- `tests/test_common_card_news_output_set.py`, `tests/test_card_news_output_set_integrity.py` --
  **not modified**; not needed.

## Tests added (all 8 required scenarios covered)

1. `test_build_pre_publish_attestation_rejects_scratch_and_absolute_paths_but_accepts_committed_relative`
   -- (a) absolute `.runs`-scoped path rejected (reproduces the original defect directly), (b)
   real, existing, repo-relative committed-style path accepted, producing exactly 4 populated
   cards with no `.runs`/`.staging`/absolute component. Covers required items 1 and 2.
2. `test_resolve_package_readiness_output_set_id_mismatch_fails_closed` -- a mismatched
   `output_set_id` between the CardNews result and the attestation still fails closed. Covers
   required item 4.
3. `test_manifest_path_mismatch_resolved_after_commit_while_rights_blockers_persist` -- full
   `_run_card_news_output_transaction` integration test: confirms `manifest_paths_match` becomes
   true, `PUBLISH_MANIFEST_PATH_MISMATCH` disappears, `PUBLISH_RIGHTS_BLOCKED`/
   `PUBLISH_EVIDENCE_BLOCKED`/`PUBLISH_MANUAL_IMAGE_REQUIRED`/
   `PUBLISH_COMMITTED_ATTESTATION_INVALID` all persist, `actual_publish`/`publishing_ready`/
   `package_ready` stay false, and the correction is visible in both the committed output-set
   files and the mirrored legacy `workflow_results` receipts. Covers required items 3, 6, 7.
4. `test_commit_failure_after_staging_never_reaches_attestation_correction` -- failing the active-
   pointer write after CardNews has already rendered real files: no output set becomes active, no
   partial commit remains, and the correction step never runs. Covers required item 5.
5. All 4 pre-existing tests (`test_receipts_complete_before_loose_pngs_are_removed`,
   `test_interrupted_receipt_update_has_no_missing_file_or_png_gap`,
   `test_concurrent_reader_never_sees_missing_receipt_or_false_ready_mix`,
   `test_partial_generation_failure_leaves_no_run_scratch_and_no_mixed_state`) and all 15 tests in
   `tests/test_common_card_news_output_set.py` / `tests/test_card_news_output_set_integrity.py`
   pass unmodified. Covers required item 8.

**Testing note**: `CardNewsPublishGate` resolves repo-relative paths against its own hardcoded
`_REPOSITORY_ROOT` module constant (not a parameter), so the new tests that need the compliance
gate to see real fixture files patch that constant to the test's isolated temp root via
`unittest.mock.patch("modules.compliance.card_news_publish_gate._REPOSITORY_ROOT", self.root.resolve())`
-- a test-time override of runtime state in `tests/test_workflow_card_news_output_receipts.py`
only; `modules/compliance/card_news_publish_gate.py`'s source was never touched. (The `.resolve()`
was necessary: an earlier attempt without it failed because Windows `%TEMP%` returns an 8.3
short-name path that doesn't string-match the same directory's long-form resolved path, which is
what `Path.resolve(strict=True)` always produces internally.)

## Verification

- `py -m unittest tests.test_workflow_card_news_output_receipts tests.test_common_card_news_output_set tests.test_card_news_output_set_integrity -v`
  -> **25/25 passed**, `OK`.
- `py -m compileall src modules scripts` -> clean, no errors.
- `py -m src.main` run **exactly once** after the above passed.

## New output_set_id

`91a28c88912849b58fa608330a217467`

## Post-run confirmation (real production run, not a test)

- `workflow_completed`: confirmed.
- Single ID binding: `active.json`, `07_card_news_result.json`, `08_card_news_result.json`,
  `08_publishing_result.json`, `09_publishing_result.json`, and the committed
  `09_publishing_result.json` all carry `91a28c88912849b58fa608330a217467`.
- `PUBLISH_MANIFEST_PATH_MISMATCH`: **removed** -- confirmed absent from the committed
  `blocker_codes`.
- The 4 attestation card paths are exactly
  `storage/output_sets/card_news/sets/91a28c88912849b58fa608330a217467/cards/card_news_{1..4}.png`
  -- repo-relative, no `.runs`/`.staging`/absolute component, each bound to the exact
  `output_set_id`.
- Remaining blockers, confirmed present: `PUBLISH_RIGHTS_BLOCKED`, `PUBLISH_EVIDENCE_BLOCKED`,
  `PUBLISH_COMPLIANCE_BLOCKED`, `PUBLISH_MANUAL_IMAGE_REQUIRED`,
  `PUBLISH_COMMITTED_ATTESTATION_INVALID`.
- `actual_publish`, `publishing_ready`, `package_ready`: all `false`.
- 4 PNGs: exist, decode successfully, exactly 1080x1080.
- Legacy `final_result.json`: `status: legacy_receipt_blocked`, `selectable: false`,
  `publishing_ready: false`, `actual_publish: false` -- 0 false-ready.

## Blockers removed vs. intentionally kept

- **Removed**: `PUBLISH_MANIFEST_PATH_MISMATCH`.
- **Kept, by design, because no real evidence exists yet**: `PUBLISH_RIGHTS_BLOCKED`,
  `PUBLISH_EVIDENCE_BLOCKED`, `PUBLISH_COMPLIANCE_BLOCKED`, `PUBLISH_MANUAL_IMAGE_REQUIRED`, and
  the aggregate `PUBLISH_COMMITTED_ATTESTATION_INVALID`. Nothing about rights, evidence, operator
  review, or image sourcing was implemented or changed in this task -- per instruction, this fix
  is scoped to the path-sequencing defect only.

## Contract needed for the next Rights Intake implementation

Whoever implements the real rights-intake mechanism (out of scope here) will need, at minimum:

1. A way for an operator to submit real `origin`/`role`/`rights_status`/`rights_evidence`
   (reference, review_status, reviewed_at) per card, replacing
   `_build_pre_publish_attestation`'s current hardcoded `"classification": "technical_fixture"`
   for at least the cards that should become `"publishable_asset"`.
2. Real `evidence[]` entries (source_url or a bound local record, `reference_verified`,
   `topic_relevant`/`topic_relevance_note`, `authenticity_status`) linked to each publishable
   asset's `asset_id`, replacing the current hardcoded `"evidence": []`.
3. A real `operator_checklist` (`operator_id`, `reviewed_at`, and the five required boolean
   checks: `source_opened`, `rights_reviewed`, `claims_reviewed`, `attribution_reviewed`,
   `final_asset_reviewed`), replacing the current hardcoded `"operator_checklist": {}`.
4. A real `campaign`/`disclosures` review when applicable, replacing the current hardcoded
   `"commercial_relationship_reviewed": False`.
5. This intake must still only ever be built from the **committed, repo-relative** card paths
   (the same fix point this task established) -- never from `.runs`/`.staging`/absolute paths.
   Reusing `_correct_committed_attestation`'s post-commit timing (rather than the pre-commit
   timing this fix moved away from) is the natural integration point.
