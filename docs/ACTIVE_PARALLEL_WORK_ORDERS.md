# Active Parallel Work Orders

Updated: 2026-07-22

## Operating Contract

- One writer owns each file.
- Only the CTO integration lane edits shared project-status documents or performs Git operations.
- Workers do not wait on each other unless a listed dependency requires it.
- A worker that finds an out-of-scope defect reports it without editing the affected file.

## Current Objective

Connect the already implemented CardNews planning, authorization, rendering, media-QA, and fallback
components into one fail-closed production path. New feature expansion is out of scope.

## Lane A: CTO / Integration

Objective: disable the unapproved legacy Workflow render path, integrate worker handoffs, run final QA,
and own shared status documents and Git approval gates.

Owned files:

- `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`
- `CURRENT_TASK.md`, `ROADMAP.md`, `MODULE_STATUS.md`, `DECISIONS.md`, `CHANGELOG.md`, `PROJECT_SNAPSHOT.md`
- final integration files explicitly adopted after worker handoff

Prohibited actions:

- Do not render, call image APIs, publish, or resume automation without owner-bound authorization.
- Preserve WorkflowEngine order and `workflow_completed` while production side effects fail closed.

Completion checks:

- Unapproved `py -m src.main` performs zero image API calls and zero CardNews renders.
- Variable-slide production remains available only through the controller-authorized path.
- Worker outputs are integrated without overlapping file ownership.

Handoff: report current user-visible state, accepted/rejected worker outputs, tests, and next integration gate.

## Lane B: Euclid - Approval Truth

Objective: correct production-package status so unapproved packages cannot appear ready.

Owned files:

- `modules/card_news/selected_candidate_production_package.py`
- its focused package test file

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

## Lane C: Heisenberg - CardNews Skill Contract

Objective: replace the stale fixed-four-slide skill instruction with the approved variable-slide contract.

Owned file:

- `.codex/skills/ai-content-os-card-news/SKILL.md`

Protected files:

- `src/workflow_engine.py`, existing CardNews renderer/QA files, `site/`, shared project documents

Completion checks:

- Missing/malformed files produce a safe fallback manifest.
- Paths are repository-relative and no image bytes are duplicated.
- Focused tests and compile pass.

Handoff: changed files, manifest schema, test results, fallback behavior, and out-of-scope findings.

## Lane D: Completed Read-only Toolchain Audit

Objective: classify installed tools by real caller and production status.

Owned files: none; read-only review.

Checks:

- Expected square dimensions (current renderer output is 1080x1080), non-empty files, four-card order, no clipping/overlap, CTA visibility.
- QA score/pass, renderer fallback, layout fallback, evidence/social-proof honesty, publishing readiness.
- Identify the exact gap between file viewing and a polished gallery UI.

Handoff: findings ordered by severity, exact file paths, and a go/no-go recommendation. Do not edit files.

## Current Integration Finding

- Sentence Transformers: connected to same-event clustering with deterministic fallback.
- Satori/resvg and OCR/OpenCLIP: safe adapters exist but the production chain is not yet unified.
- Intel XPU, SeaweedFS, Mixpost, and TryPost remain outside the CardNews critical path.
- The legacy Workflow image-generation/render path is the immediate blocker.

## Integration Completion - 2026-07-22

- Lane A complete: the standard Workflow production side effects are fail-closed and `workflow_completed` is preserved in mocked integration coverage.
- Lane B accepted: explicit approval receipts are required; unapproved packages remain pending/blocked.
- Lane C accepted: the project CardNews skill now defines variable slides and owner authorization gates.
- Local QA integration accepted: controlled Satori/resvg output automatically feeds OCR/OpenCLIP evidence QA without creating owner approval.
- Toolchain classification complete: Sentence Transformers connected; XPU probe-only; SeaweedFS/Mixpost/TryPost outside the critical path.
- Final checks: compile passed and 67 focused tests passed.
- Remaining owner gate: select a candidate from the 174-item report, then separately authorize one representative controlled render.
