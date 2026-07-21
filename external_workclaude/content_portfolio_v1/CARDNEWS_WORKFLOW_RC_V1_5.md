# CardNews Workflow RC V1.5

## Final verdict

- **DEV_SAFE_GO** -- the workflow, the CardNews output-set transaction, and the receipt system
  all behaved correctly on a single live run: `workflow_completed`, all IDs consistent, all
  fail-closed gates held.
- **PUBLISH_NO_GO** -- no rights-approved real image or rights record exists for this run's
  cards. Per instruction, `PUBLISH_GO` cannot be issued without one, and none of this task's
  steps attempted to obtain or fabricate one.

## Execution record

- `git status --short` recorded before and after the run (see `WORKFLOW_CHANGED_FILES_V1_5.md`).
- `py -m compileall src modules scripts` -- exit 0, no errors.
- `py -m src.main` -- run **exactly once**, exit 0, final status `workflow_completed`.
- No retry, no code fix, no restore/reset/checkout, no Git write operation, no real publish/
  login/upload, no credential printed or added.

## output_set_id

`f2281e14df8d4ab68a46152e93e9029b`

## workflow_completed

Confirmed -- printed `workflow_completed` twice (module-level and `Final Status:` banner) and
persisted in `storage/workflow_results/99_final_result.json`.

## PNG status

- Exactly 4 cards referenced in `08_card_news_result.json`, indices 1-4.
- All 4 decode successfully via Pillow (`.verify()` + reopen).
- All 4 are exactly 1080x1080 PNG.
- All 4 paths point to the immutable committed location
  `storage/output_sets/card_news/sets/f2281e14df8d4ab68a46152e93e9029b/cards/card_news_{1..4}.png`
  -- none point into `.runs/`, `.staging/`, or a loose `storage/card_news/*.png` path.

## Receipt truth (checkpoints 2-3, 7-9, 12)

| Field | Value |
|---|---|
| active pointer `output_set_id` | `f2281e14df8d4ab68a46152e93e9029b` |
| `07_card_news_result.json` id | matches |
| `08_card_news_result.json` id | matches |
| `08_publishing_result.json` id | matches |
| `09_publishing_result.json` id | matches |
| `card_news_quality.json` (inside committed set) id | matches |
| `99_final_result.json` id | matches |
| loose/`.runs`/`.staging` path exposure across all of the above | **0** |
| global `storage/publishing/publish_queue.json` | does not exist |
| legacy `storage/workflow_results/final_result.json` | `status: legacy_receipt_blocked`, `selectable: false`, `publishing_ready: false`, `actual_publish: false` |

## Publishing status (checkpoints 10-11)

`08_publishing_result.json` and `09_publishing_result.json` agree exactly on `status`,
`publishing_ready`, `package_ready`, and `actual_publish`. Both report:

- `status: publishing_blocked`
- `package_ready: false`
- `publishing_ready: false`
- `actual_publish: false`

Blocker codes: `PUBLISH_MANIFEST_PATH_MISMATCH`, `PUBLISH_RIGHTS_BLOCKED`,
`PUBLISH_EVIDENCE_BLOCKED`, `PUBLISH_COMPLIANCE_BLOCKED`, `PUBLISH_MANUAL_IMAGE_REQUIRED`,
`PUBLISH_COMMITTED_ATTESTATION_INVALID`. This is the correct, fail-closed outcome for a run with
no confirmed image rights -- not a defect.

## Fallback

- Naver News: collection failed (`parse_failed` on all 5 seed keywords), fell back to
  `settings_keyword_fallback`, recorded in `storage/trends/trend_result.json` and
  `storage/workflow_results/01_trend_result.json` (`fallback_used: true`,
  `fallback_reason: "parse_failed"`).
- Nate Pann: collection failed (`network_error`), recorded in the same collection summary.
- Image Prompt / Image Generation modules were both skipped this run because Image Strategy
  selected a real image source instead -- recorded in
  `storage/workflow_results/06_image_prompt_result.json` /
  `07_image_generation_result.json` (`"...Skipped: Image Strategy selected a real image
  source"`).
- No workflow failure resulted from any of the above -- `workflow_completed` was still reached,
  consistent with the fallback-first contract.

## Changed files

See `WORKFLOW_CHANGED_FILES_V1_5.md` for the full before/after comparison.

## Remaining blockers

- `PUBLISH_RIGHTS_BLOCKED` / `PUBLISH_MANUAL_IMAGE_REQUIRED` / `PUBLISH_EVIDENCE_BLOCKED` /
  `PUBLISH_COMPLIANCE_BLOCKED` -- no confirmed image rights or evidence exist for this run's
  cards; real publish stays blocked until an operator supplies and confirms them.
- `PUBLISH_MANIFEST_PATH_MISMATCH` / `PUBLISH_COMMITTED_ATTESTATION_INVALID` -- these also
  appeared identically in the pre-run legacy receipt snapshot from the prior session, so this is
  an existing, already-fail-closed state, not a new regression introduced by this run.
- No code defect found. No fix was made or needed this task -- this was QA-only, per
  instruction.
