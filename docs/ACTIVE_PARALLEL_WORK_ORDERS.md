# Active Parallel Work Orders

Updated: 2026-07-11

## Operating Contract

- One writer owns each file.
- Only the CTO integration lane edits shared project-status documents or performs Git operations.
- Workers do not wait on each other unless a listed dependency requires it.
- A worker that finds an out-of-scope defect reports it without editing the affected file.

## Current Objective

Make completed CardNews outputs easy to inspect in the Codex app now, then prepare a safe result-gallery
integration without modifying the user's untracked `site/` work.

## Lane A: Work CTO / Integration

Objective: confirm current CardNews completion state, protect existing user work, review handoffs, and
decide whether the result gallery should later be integrated into `site/`.

Owned files:

- `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`
- `CURRENT_TASK.md`, `ROADMAP.md`, `MODULE_STATUS.md`, `DECISIONS.md`, `CHANGELOG.md`, `PROJECT_SNAPSHOT.md`
- final integration files explicitly adopted after worker handoff

Prohibited actions:

- Do not modify untracked `site/` until its ownership and intended product role are confirmed.
- Do not regenerate CardNews merely to build a viewer.

Completion checks:

- Four PNG paths and `card_news_quality.json` are verified.
- Worker outputs are reviewed for repository accuracy and scope compliance.
- Final integration decision is recorded before code is merged.

Handoff: report current user-visible state, accepted/rejected worker outputs, tests, and next integration gate.

## Lane B: Claude Specialist

Objective: produce a non-code UX and information-architecture specification for a CardNews result gallery.

Owned file:

- `docs/CARD_NEWS_RESULT_GALLERY_SPEC.md`

Required reading:

- `storage/card_news/card_news_quality.json`
- `storage/workflow_results/08_card_news_result.json`
- `modules/card_news/card_news_module.py`
- `modules/publishing/publishing_module.py`

Requirements:

- Specify four-card preview, QA status, warnings, source/fallback labels, open-folder action, and publishing readiness.
- Separate what works now in the Codex file viewer from a future gallery UI.
- Use only confirmed repository fields; label proposals clearly.

Prohibited files/actions:

- Do not edit code, `site/`, shared project documents, storage outputs, or Git state.

Handoff: changed file, confirmed fields used, proposed UI states, unresolved CTO gates, and confirmation that no other file changed.

## Lane C: Codex Worker - Result Manifest

Objective: design and implement a small, tested CardNews result-manifest builder outside `site/` that
normalizes the four PNG paths, QA status, warnings, and publishing readiness for a future UI.

Owned files:

- proposed new `modules/card_news/card_news_result_manifest.py`
- proposed new `tests/test_card_news_result_manifest.py`

Protected files:

- `src/workflow_engine.py`, existing CardNews renderer/QA files, `site/`, shared project documents

Completion checks:

- Missing/malformed files produce a safe fallback manifest.
- Paths are repository-relative and no image bytes are duplicated.
- Focused tests and compile pass.

Handoff: changed files, manifest schema, test results, fallback behavior, and out-of-scope findings.

## Lane D: Codex Worker - Output QA

Objective: independently inspect the four current PNGs and result JSON for app-view readiness.

Owned files: none; read-only review.

Checks:

- Expected square dimensions (current renderer output is 1080x1080), non-empty files, four-card order, no clipping/overlap, CTA visibility.
- QA score/pass, renderer fallback, layout fallback, evidence/social-proof honesty, publishing readiness.
- Identify the exact gap between file viewing and a polished gallery UI.

Handoff: findings ordered by severity, exact file paths, and a go/no-go recommendation. Do not edit files.

## Current Integration Finding

- App individual-file viewing: GO.
- Polished gallery and publish-ready labeling: NO-GO.
- Current outputs are 1080x1080 and visually readable, but semantic copy defects remain.
- `publishing_ready` must be gated off while `manual_image_required=true`.
