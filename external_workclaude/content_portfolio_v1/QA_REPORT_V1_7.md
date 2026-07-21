# QA Report V1.7 — Manifest Committed-Path Fix

## Scope guard

Only the two authorized files were changed:

```
 M src/workflow_engine.py
?? tests/test_workflow_card_news_output_receipts.py
```

(`tests/test_common_card_news_output_set.py` and `tests/test_card_news_output_set_integrity.py`
were left untouched — the fix did not require adding attack tests there.) No Compliance,
Publishing, or CardNews module was modified. No storage files were hand-edited. No Git operations
were performed. No real publish/API call was made.

## Test run 1 — focused suite

Command:
```
py -m unittest tests.test_workflow_card_news_output_receipts tests.test_common_card_news_output_set tests.test_card_news_output_set_integrity -v
```
Result: **25 tests, 25 passed, 0 failed, 0 errors.** `OK`.

Breakdown:
- `tests/test_workflow_card_news_output_receipts.py`: 8 tests (4 pre-existing + 4 new), all pass.
- `tests/test_common_card_news_output_set.py`: existing tests, all pass, unmodified.
- `tests/test_card_news_output_set_integrity.py`: existing tests, all pass, unmodified.

## Test run 2 — compile check

Command:
```
py -m compileall src modules scripts
```
Result: clean, no syntax/import errors across all three trees.

## Test run 3 — real workflow run (exactly once, no retries)

Command:
```
py -m src.main
```

Post-run verification (via a read-only Python check script against the produced JSON/PNG files,
not a retry of the workflow):

| Checkpoint | Result |
|---|---|
| `workflow_completed` | ✅ true |
| New `output_set_id` | `91a28c88912849b58fa608330a217467` |
| Single ID bound across active pointer / 07 / 08 (card_news) / 08–09 (publishing) / committed set | ✅ all identical |
| `PUBLISH_MANIFEST_PATH_MISMATCH` | ✅ absent from `blocker_codes` |
| Attestation card count | ✅ exactly 4 |
| Attestation card paths repo-relative, no `.runs`/`.staging`, no absolute component | ✅ all 4 |
| Attestation cards' `output_set_id` matches the committed set | ✅ all 4 |
| `PUBLISH_RIGHTS_BLOCKED` retained | ✅ present |
| `PUBLISH_EVIDENCE_BLOCKED` retained | ✅ present |
| `PUBLISH_MANUAL_IMAGE_REQUIRED` retained | ✅ present |
| `PUBLISH_COMMITTED_ATTESTATION_INVALID` retained | ✅ present |
| `actual_publish` | ✅ false |
| `publishing_ready` | ✅ false |
| `package_ready` | ✅ false |
| 4 PNGs exist, decode, exactly 1080x1080 | ✅ all 4 |
| Legacy `final_result.json` (`storage/workflow_results/final_result.json`) | ✅ `status: legacy_receipt_blocked`, `selectable: false`, `publishing_ready: false`, `actual_publish: false` — 0 false-ready |

All 14 checkpoints pass. No follow-up run was performed (per the "run exactly once" constraint).

## Known-safe, unchanged invariants (spot-checked against the real committed output)

- `CardNewsOutputSetTransaction._validate_directory`'s ID-consistency, path-identity, and
  `release_ready`-consistency checks are unaffected — the fix only rewrites embedded manifest/
  readiness/blocker fields inside `08_card_news_result.json` / `09_publishing_result.json`, never
  the `manifest.json`, `active.json`, PNGs, `cards` list, or `card_paths`.
- `_write_compatible_output_set_receipts`'s legacy-mirroring behavior (per-file atomic
  temp+fsync+replace, `publish_queue.json` deletion, `final_result.json` marked
  `legacy_receipt_blocked`/`selectable: false`) is unaffected; the correction now runs before that
  mirroring step so every legacy copy also reflects the corrected attestation.

## Residual risk / things intentionally left for a future task

- Rights/evidence/manual-image blockers remain by design (no rights-intake mechanism exists yet);
  see `MANIFEST_PATH_FIX_V1_7.md` §"Contract needed for the next Rights Intake implementation".
- No attempt was made to reduce the number of legacy receipt file locations
  `_write_compatible_output_set_receipts` writes to — out of scope for this task.

## Verdict

`DEV_SAFE_GO` for the path-sequencing fix itself (compiles clean, all tests pass, single verified
real run matches every required checkpoint). Publish readiness remains and must remain
`PUBLISH_NO_GO` — rights/evidence/manual-image gates are still unimplemented by design.
