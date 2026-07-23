# Active Parallel Work Orders

Updated: 2026-07-24

## Current Objective - Supplemental Meme / Reaction / GIF Pipeline

Audit and connect the owner-approved supplemental-media path across all CardNews
accounts: documented public sources, bounded retrieval, source/provenance,
topic-emotion ranking, GIF frame handling, production selection, Satori
rendering, and local QA. This work must not publish, upload, issue links, resume
automation, or perform Git writes.

## Lane A: CTO / Integration - Active

Objective: own the executable contract, file boundaries, production selector
integration, focused tests, current local render evidence, and final report.

Owned files:

- `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`
- integration files selected after the two read-only audits
- focused tests for those integration files

Completion checks:

- Every configured source is classified as documented, callable, or blocked.
- Supplemental media is used only when primary topic media is insufficient.
- Topic, emotion, source URL, license/rights scope, local path, and media type
  remain attached through the render request.
- Animated GIF input has an explicit static-card frame policy and future motion
  metadata without pretending a static PNG is animated.
- Current focused tests and one controlled local result prove the exact path.

## Lane B: Popper - Read-only Source and Caller Audit

Objective: identify public meme/GIF/reaction sources in owner learning records,
configuration, collectors, selectors, and render consumers.

Owned files: none.

Handoff: source-by-source executable-status table and exact missing call links.

## Lane C: Euler - Read-only Local Toolchain Audit

Objective: classify installed GIF/image/video/search/ranking tools and their
real production callers.

Owned files: none.

Handoff: installed/callable/connected matrix and exact missing dependencies.

## Current Objective - Story Comment Spotlight Integration

Connect the existing identity-masked community comment crops to the Account B
cover-selection and render path. The first card must use one or two readable
real-comment crops rather than a full community webpage screenshot.

## Lane A: CTO / Integration - Active

Objective: preserve comment screenshot provenance, rank eligible crops with
bounded local OCR reaction evidence, compose the story cover, bind it to
Reference V2, preserve package evidence, and produce one controlled local
render.

Owned files:

- `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`
- `modules/card_news/story_comment_spotlight.py`
- `modules/source_intake/selected_candidate_production_flow.py`
- `modules/card_news/selected_candidate_production_package.py`
- focused tests for these files

Prohibited actions:

- Do not modify source screenshots.
- Do not use unmasked or crop-ineligible comments.
- Do not publish, upload, resume automation, or perform Git writes.

Completion checks:

- The cover media is a deterministic composite of one or two real masked
  comment crops.
- OCR reaction extraction is a ranking signal only; collected comment text
  remains the copy source.
- The package preserves all eligible comment evidence and the two spotlight
  selections.
- A current controlled render visibly excludes page chrome and advertising.

## Lane B: Mendel - Completed Read-only Reuse Audit

Objective: identify existing comment DOM crop, OCR, ranking, and production
integration points without editing.

Handoff accepted: DOM crop and masking already work; the missing contract was
`screenshot_path` preservation, ranking, and Account B cover binding.

## Operating Contract

- One writer owns each file.
- Only the CTO integration lane edits shared project-status documents or performs Git operations.
- Workers do not wait on each other unless a listed dependency requires it.
- A worker that finds an out-of-scope defect reports it without editing the affected file.

## Current Objective

Replace the failed abstract-tag design path with the reference-driven geometry pipeline defined in
`docs/CARDNEWS_REFERENCE_DRIVEN_PIPELINE_V2.md`. Existing owner analysis remains canonical. Runtime
selection must choose an owner-approved primary reference specimen and carry its normalized regions,
style tokens, media contract, and provenance to Satori without reducing it to labels such as
`centered_panel` or `warning`. The shared A/B/C pool remains capped at 40 approved reference
profiles; batch size is not a layout-count limit.

## Lane A: CTO / Integration - Active

Objective: own the V2 specimen registry, geometry blueprint contract, approved-reference selector,
CardNews integration, shared documents, final QA, and all Git approval gates.

Owned files:

- `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`
- `modules/design_learning/`
- `modules/card_news/layout_selector.py`
- `modules/card_news/learning_design_compiler.py`
- `modules/card_news/production_render_request_builder.py`
- `modules/card_news/card_news_module.py`
- design-learning CLI and focused tests explicitly added for this objective
- shared project-status documents during final integration only

Prohibited actions:

- Do not modify, move, rename, or delete files under `F:/AI-Content-OS-Data/owner_source`.
- Do not treat screenshot observations as measured Instagram performance.
- Do not auto-promote a learned layout without explicit owner approval evidence.
- Do not render, publish, resume automation, call an external write API, or perform Git writes.

Completion checks:

- Deterministic batches contain at most 10 unique source images and preserve source-relative paths.
- One analysis record preserves source identity, design, layout, palette, typography, body-content
  insight, normalized regions, media contract, and project-use fields without collapsing them into
  a single label.
- Only owner-approved fixed layout profiles are eligible for runtime selection, with a shared
  A/B/C pool capped at 40 profiles rather than ten profiles.
- Every rendered slide records one primary reference ID, blueprint version, geometry hash, and
  directly consumed regions. Cross-reference field mixing is prohibited in V2.
- Missing required geometry, text-fit failure, media-fit failure, source-topic contamination, or
  unconsumed reference fields blocks the production render instead of falling back silently.
- Missing/corrupt learning data fails soft to the existing CardNews layout selector.
- Selection output explains account/context matches and never claims real performance evidence.

Handoff: changed files, executable call chain, untested boundaries, focused QA result, and next
10-image analysis gate.

## Lane B: Cicero - Read-only Loss Audit

Objective: identify the exact functions where owner-reference structure is reduced to abstract
fields before rendering, then report the smallest V2 correction surface.

Owned files: none; read-only review.

Required reading:

- `modules/design_learning/production_profile_compiler.py`
- `modules/card_news/learning_design_compiler.py`
- `modules/card_news/production_render_request_builder.py`
- relevant focused tests
- `templates/card_news_layout_rules.json`

Prohibited files/actions:

- Do not edit any file, run tests, render, run Git, inspect screenshot pixels, or analyze all
  owner-source images.
- Do not change WorkflowEngine or propose external API dependencies.

Completion checks:

- Report the field-to-loss-point-to-render-consumer chain, minimal changed files, and five
  fail-closed contracts.

Handoff: short Korean report with findings ordered by severity and exact file/function references.

## Previous Objective - Completed 2026-07-22

Connect the already implemented CardNews planning, authorization, rendering, media-QA, and fallback
components into one fail-closed production path. New feature expansion was out of scope.

## Previous Lane A: CTO / Integration

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

## Previous Lane B: Euclid - Approval Truth

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

## Previous Lane C: Heisenberg - CardNews Skill Contract

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

## Previous Lane D: Completed Read-only Toolchain Audit

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
