# Publish Blocker Provenance Audit V1.6

Read-only audit. No file outside `external_workclaude/content_portfolio_v1/` was modified. Every
claim below is traced to a specific line in `storage/output_sets/card_news/sets/f2281e14df8d4ab68a46152e93e9029b/*`
or the exact source function that produced it -- nothing here is inferred without a direct
cross-reference.

Target output_set_id: **`f2281e14df8d4ab68a46152e93e9029b`**

## Summary classification

| Blocker | Classification |
|---|---|
| `PUBLISH_RIGHTS_BLOCKED` | `EXPECTED_USER_INPUT_BLOCKER` |
| `PUBLISH_EVIDENCE_BLOCKED` | `EXPECTED_USER_INPUT_BLOCKER` |
| `PUBLISH_MANUAL_IMAGE_REQUIRED` | `EXPECTED_USER_INPUT_BLOCKER` |
| `PUBLISH_COMPLIANCE_BLOCKED` | `EXPECTED_DERIVED_BLOCKER` (aggregates rights/evidence/operator-checklist/disclosure state, one of its own inputs is also affected by the independent defect below) |
| `PUBLISH_MANIFEST_PATH_MISMATCH` | **`INDEPENDENT_TECHNICAL_DEFECT`** |
| `PUBLISH_COMMITTED_ATTESTATION_INVALID` | `EXPECTED_DERIVED_BLOCKER` (pure aggregate of the other 5 checks -- see below) |

No blocker is `STALE_OR_MISLEADING_BLOCKER` or `UNKNOWN` -- every one traces cleanly to a live,
correctly-bound cause for this exact `output_set_id`.

---

## 1. `PUBLISH_RIGHTS_BLOCKED` -- `EXPECTED_USER_INPUT_BLOCKER`

- **Originating module/function**: `modules/publishing/publishing_module.py::_resolve_package_readiness` (line ~404, `rights_passed = ...`), fed by `modules/compliance/card_news_publish_gate.py::CardNewsPublishGate._check_assets` / `_result`.
- **Input condition**: the attestation's `assets[]` all carry `"classification": "technical_fixture_not_publish_approved"`. This classification is **hardcoded** in `src/workflow_engine.py::_build_pre_publish_attestation`'s intake construction: `"classification": "technical_fixture"` for every card, unconditionally -- there is currently no code path in the workflow that ever submits a card as `"publishable_asset"` with real rights evidence.
- **Direct cause**: no real, operator-supplied rights evidence (origin, rights_status, reviewed_at, verified reference) exists for this run's cards, because none was ever provided as input -- there is no real image asset to attach rights to in the first place (see Asset Provenance Audit).
- **Derived from another blocker?** No -- this is evaluated directly against the (always-empty-of-real-data) `rights` field.
- **Auto-resolves once a rights-approved image arrives?** Only partially. A real, rights-approved image alone is not sufficient: `_build_pre_publish_attestation` would also need a code change to stop hardcoding `classification: "technical_fixture"` and to actually pass real `rights_evidence`/`origin`/`asset_role` fields once an operator supplies them. Today there is no intake mechanism wired for that at all.
- **Bound to this exact output_set_id?** Yes -- `card-news-f2281e14df8d4ab68a46152e93e9029b` package_id, `output_set_id` matches throughout.
- **Code fix needed?** Not for this audit to make, and arguably not a "fix" so much as an intentionally unbuilt Phase-2 capability (per `docs/COMMERCE_PHASE_1_CONTRACT.md`-style Phase gating elsewhere in this repo, and the CardNews skill's "never fabricate rights approval" rule). If/when a real rights-intake mechanism is designed, the owning file is `src/workflow_engine.py::_build_pre_publish_attestation`.

## 2. `PUBLISH_EVIDENCE_BLOCKED` -- `EXPECTED_USER_INPUT_BLOCKER`

- **Originating module/function**: same call chain as #1; `evidence_passed` computed from `manifest.get("evidence", {})`, fed by `CardNewsPublishGate._check_evidence` against an intake `"evidence": []` (hardcoded empty list in `_build_pre_publish_attestation`).
- **Direct cause**: no evidence records exist because no real asset exists to attest evidence for.
- **Derived from another blocker?** No, independent check against the (empty) evidence list.
- **Auto-resolves with a rights-approved image?** Same caveat as #1 -- needs both real evidence input and the corresponding intake-wiring code change.
- **Bound to this output_set_id?** Yes.

## 3. `PUBLISH_MANUAL_IMAGE_REQUIRED` -- `EXPECTED_USER_INPUT_BLOCKER`

- **Originating module/function**: `PublishingModule.run()`'s own image-sourcing check, surfaced again in `_resolve_package_readiness` as `manual_image_clear = not operations["publishing_blocked"]`.
- **Input condition**: `storage/image_strategy/image_strategy_result.json` -- `content_type: "community"`, `image_source: "post_capture"`, `need_ai_image: false`. The 09 result's own `image_sourcing_status` states plainly: `"reason": "content_type 'community'은 실제 이미지가 필요하지만 아직 소싱되지 않음."` and `"real_image_used_count": 0`.
- **Direct cause**: this content type requires a real captured image (a screenshot of the source community post) and none has been sourced; the render used a solid-color background instead (see Asset Provenance Audit).
- **Derived from another blocker?** No -- this is the one blocker with the most direct, single-cause trigger of the six.
- **Auto-resolves once a rights-approved image arrives?** **Yes, most likely of the six** -- once a real `post_capture` image is supplied and CardNewsModule renders with it, `real_image_used_count` should become > 0 and `image_sourcing_status.manual_image_required` should flip to `false`, with no code change needed for this specific check.
- **Bound to this output_set_id?** Yes.

## 4. `PUBLISH_COMPLIANCE_BLOCKED` -- `EXPECTED_DERIVED_BLOCKER`

- **Originating module/function**: `_resolve_package_readiness`'s `compliance_passed` computation (canonical-attestation branch), which requires `compliance.get("status") == "valid"`, `publish_ready is True`, `blocking_reasons == []`, `release_guard.ready is True`, and `not technical_fixture_blocked`.
- **Direct cause**: `release_guard.ready` is `False` because `CardNewsPublishGate._result()` folds in *every* other gate's failures (technical-fixture classification, `commercial_relationship_unreviewed`, `operator_attestation_invalid`, `operator_checklist_incomplete`, `final_cards_invalid` x4, `publishable_asset_missing`) into one `blockers` list, and `release_guard.issue_codes` is exactly that list (confirmed byte-for-byte against `pre_publish_attestation.release_guard.issue_codes` in the result JSON).
- **Derived from another blocker?** Yes -- this is a genuine aggregate: part of its cause is the same missing-rights/evidence/operator-review input as #1/#2, and part of its cause is the independent `final_cards_invalid` defect described in #5. It is not a separately-triggerable failure mode on its own.
- **Auto-resolves with a rights-approved image?** Only once **both** the missing operator/rights/evidence input is supplied **and** the `PUBLISH_MANIFEST_PATH_MISMATCH` defect (#5) is fixed -- since `final_cards_invalid` (part of the same `release_guard.issue_codes` list) will keep firing regardless of rights approval until that code path is corrected.
- **Bound to this output_set_id?** Yes.

## 5. `PUBLISH_MANIFEST_PATH_MISMATCH` -- `INDEPENDENT_TECHNICAL_DEFECT`

This is the one genuinely independent defect found in this audit. Full trace:

- **Originating check**: `_resolve_package_readiness` line ~399: `manifest_paths_match = len(manifest_paths) == 4 and card_paths == manifest_paths`, where `manifest_paths` comes from the embedded `card_news_manifest` (the pre-publish attestation)'s `"cards"` field.
- **Expected path** (what `card_paths` -- the real, committed card paths -- actually are): the four canonical, repo-relative, immutable paths
  `storage/output_sets/card_news/sets/f2281e14df8d4ab68a46152e93e9029b/cards/card_news_{1..4}.png` (confirmed present, decodable, 1080x1080 in the V1.5 audit).
- **Actual path compared against**: the attestation's `"cards"` field is **`[]`** (confirmed directly in `09_publishing_result.json`'s embedded `pre_publish_attestation.cards`). `len([]) == 4` is trivially false, so the check fails regardless of what the real card paths are.
- **Why is `"cards": []`?** Traced to `CardNewsPublishGate._check_final_cards` (`modules/compliance/card_news_publish_gate.py`), which only keeps a card in the returned `normalized` list (which becomes the attestation's `"cards"`) if `_repo_relative_path(path)` is true. `_repo_relative_path` explicitly rejects any absolute path: `if not reference or Path(reference).is_absolute(): return False`.
- **Why is the path absolute at that point?** `src/workflow_engine.py::_run_card_news_output_transaction` builds `transaction = CardNewsOutputSetTransaction(Path("."))`, whose `self.root = Path(repository_root).resolve()` is an **absolute** path. It then sets `self.card_news_module.card_dir = run_dir / "card_news"` (also absolute, since it is a child of `transaction.store`, itself a child of the absolute `self.root`). `CardNewsModule._create_card`/`_create_card_with_layout` compute `output_path = self.card_dir / f"card_news_{page_number}.png"` and return `str(output_path)` -- an **absolute filesystem path string** -- as `card_path`. This is independently confirmed by the actual V1.5 console log line captured this session: `Card News Saved (layout-aware, notebook): C:\Users\...\storage\output_sets\card_news\.runs\f2281e14df8d4ab68a46152e93e9029b\card_news\card_news_1.png`.
- **When is `_build_pre_publish_attestation` called relative to staging?** Before `transaction.stage()` -- i.e., while `card_news_result["cards"][*]["card_path"]` still holds this absolute, run-scoped path. `_build_pre_publish_attestation` copies that value verbatim into the `"final_cards"` intake it hands to `CardNewsPublishGate`. Result: `_check_final_cards` rejects all four cards on the `is_absolute()` check, appends 4x `{"code": "final_cards_invalid", "card_index": N}` (confirmed: exactly 4 occurrences of `final_cards_invalid` in the result JSON, at indices 0-3), and the attestation's `"cards"` list is left empty.
- **Does staging's path-rewrite fix this later?** No. `CardNewsOutputSetTransaction.stage()`'s `_rewrite_paths` does correctly rewrite the *other* place the same absolute string leaked into the payload (`pre_publish_attestation.assets[].asset_path`, confirmed already showing the corrected canonical path in the committed result) -- but it can only rewrite strings that already exist in the payload. It cannot reconstruct a list (`attestation.cards`) that `CardNewsPublishGate` already decided to leave empty before staging ever ran.
- **Blocked package derived-emptiness, or independent defect?** **Independent defect, confirmed.** This is not merely "the manifest is intentionally blank because the package is blocked" -- it fires purely because of a path-format mismatch (absolute vs. repo-relative) at attestation-build time, and it **would keep firing even on a fully rights-approved, fully evidenced future submission**, because the sequencing bug (build attestation before staging, using the pre-staging absolute path) is unrelated to whether rights/evidence/compliance ever get approved.
- **Owning file/function if a fix is ever authorized**: `src/workflow_engine.py::_build_pre_publish_attestation` and/or `_run_card_news_output_transaction` (the sequencing of when the attestation is built relative to `transaction.stage()`, or making the intake's `final_cards[].path` repo-relative before handing it to `CardNewsPublishGate`). This audit does not implement that fix -- read-only per instruction.
- **Minimum test if a fix is ever made**: a unit test asserting that `WorkflowEngine._build_pre_publish_attestation`'s resulting attestation's `"cards"` list is non-empty and repo-relative when called with realistic `.runs`-scoped absolute card paths, mirroring this exact reproduction.

## 6. `PUBLISH_COMMITTED_ATTESTATION_INVALID` -- `EXPECTED_DERIVED_BLOCKER`

- **Originating function**: `modules/publishing/publishing_module.py::rebind_committed_paths` (line ~67-79), **not** `_resolve_package_readiness`.
- **Exact logic**: `attestation_invalid = any(readiness_checks.get(key) is not True for key in required_readiness_checks)` across all 11 keys: `attestation_schema_valid, exactly_four_cards, card_files_exist, manifest_paths_match, output_set_match, rights_passed, evidence_passed, compliance_passed, qa_passed, manual_image_clear, upload_mode_manual`.
- **Which of the 11 actually fail for this run?** Only 5: `manifest_paths_match`, `rights_passed`, `evidence_passed`, `compliance_passed`, `manual_image_clear` (confirmed directly against `09_publishing_result.json`'s `readiness_checks`). The other 6 -- including `attestation_schema_valid: true` and `output_set_match: true` -- all pass.
- **Schema/output_set_id/asset-path failure, or rights/evidence/compliance-driven?** **Confirmed rights/evidence/compliance/manifest-driven, not a schema or identity defect.** The schema is valid, the output_set_id is correctly bound throughout, and the asset paths (post-rewrite) are correct. This blocker is purely a downstream aggregate flag -- it adds no new information beyond "one or more of the other checks is false."
- **Derived from another blocker?** Yes, by definition (100% derived, mechanically).
- **Auto-resolves with a rights-approved image?** Only once all five of its constituent failing checks clear -- meaning both the user-input items (#1/#2/#3-adjacent) and the independent `manifest_paths_match` defect (#5) must be resolved.

---

## Binding integrity check (all 6 blockers)

Every blocker code, in every location it appears (`09_publishing_result.json` top-level
`blocker_codes`, `operations.blocking_reasons`, `operator_upload_package.blocker_codes`,
`publish_queue.items[].blocker_codes`, `pre_publish_attestation.compliance_result.blocking_reasons`),
carries the identical `output_set_id: "f2281e14df8d4ab68a46152e93e9029b"` -- confirmed by direct
read, not sampled. No blocker in this run is a stale carryover from a different output set.

## Final judgment

No guess was made about GO/NO-GO. Real publish must remain blocked for this output set because:
(a) three genuine `EXPECTED_USER_INPUT_BLOCKER`s are open (no real image, no real rights, no real
evidence), and (b) one `INDEPENDENT_TECHNICAL_DEFECT` (`PUBLISH_MANIFEST_PATH_MISMATCH`) exists
that would **continue to block a legitimately-approved future submission** even after the user
input above is supplied, until `src/workflow_engine.py`'s attestation-build sequencing is
corrected. That fix was not made in this audit (read-only, no code changes).
