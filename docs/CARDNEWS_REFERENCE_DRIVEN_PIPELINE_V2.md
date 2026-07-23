# CardNews Reference-Driven Production Pipeline V2

Status: architecture approved for implementation planning, not yet implemented or runtime verified
Date: 2026-07-23

## Decision

The current abstract-tag path is rejected as the primary design-learning path.

`owner learning record -> centered_panel / warning / bold_condensed -> renderer defaults`

It proves that metadata can travel through the pipeline, but it does not reproduce the visual
grammar observed in the owner corpus. A successful render consuming abstract tags is not evidence
that the owner references affected production quality.

V2 selects one owner-approved primary reference per slide and preserves its concrete geometry to the
renderer.

`owner analysis -> reference specimen -> geometry blueprint -> content fit -> render tree -> visual QA`

## Non-Goals

- Do not re-analyze the existing owner-source corpus.
- Do not modify, move, rename, or delete owner-source files.
- Do not create a new renderer or reorder WorkflowEngine.
- Do not add an eleventh legacy layout name.
- Do not claim measured Instagram performance.
- Do not mix unrelated celebrities, screenshots, or source media into a topic.
- Do not render, publish, or perform Git writes without the existing owner gates.

## Root Cause

`ProductionProfileCompiler` walks broad nested records, routes prose into fields, and normalizes
visual guidance to a small renderer vocabulary. This intentionally loses the source layout's region
coordinates, image occupancy, title footprint, overlap, alignment, accent geometry, and slide role.

`compile_learning_driven_blueprint` accepts the resulting profile as a dictionary and marks it
consumed when present. It does not require a primary reference specimen or concrete geometry.

`build_production_render_request` can apply palette, typography, and a few composition values, but it
cannot reconstruct a source layout that was discarded upstream.

## V2 Data Contracts

### 1. Reference Specimen

One immutable record per usable owner-analyzed reference.

Required fields:

- `reference_id`
- `source_claim_ids`
- `source_relative_path`
- `analysis_record_ids`
- `account_fit`
- `format_fit`
- `slide_role_fit`
- `topic_fit`
- `emotion_fit`
- `media_requirements`
- `blueprint_id`
- `approval_status`
- `owner_approval_receipt_id`
- `reference_only`
- `measured_performance_claimed: false`

Only `approval_status: owner_approved` specimens are production-selectable.

### 2. Layout Blueprint

One versioned, content-free geometry contract derived from an approved specimen.

Required fields:

- `blueprint_id`
- `blueprint_version`
- `canvas`
- `layout_family`
- `regions`
- `style_tokens`
- `fit_constraints`
- `geometry_hash`
- `provenance`

Each region contains:

- `region_id`
- `role`
- `box_norm: [x, y, width, height]`
- `z_index`
- `alignment`
- `padding_norm`
- `background`
- `border`
- `radius_norm`
- `overlap_policy`
- `required`

Supported region roles initially include:

- `primary_media`
- `secondary_media`
- `headline`
- `subheadline`
- `body`
- `metric`
- `quote`
- `real_comment`
- `source_label`
- `commerce_sticker`
- `cta`
- `account_mark`
- `accent`

`box_norm` values are normalized to the canvas. Prose such as "large title near the bottom" is not
a geometry contract.

### 3. Reference Selection Result

The selector returns complete candidates, not independently selected design fields.

Required output:

- `primary_reference_id`
- `primary_blueprint_id`
- `ranked_alternatives`
- `selection_reasons`
- `rejection_reasons`
- `account_match`
- `slide_role_match`
- `media_fit`
- `copy_fit`
- `topic_fit`
- `emotion_fit`
- `selection_hash`

V2 prohibits assembling one slide from the layout of one reference, palette of another, typography
of a third, and emotion of a fourth. A secondary reference may supply an explicitly approved
non-geometry token only after the primary blueprint is complete, and the override must be recorded.

### 4. Content Fit Result

Content is fitted to the selected blueprint before render request construction.

Checks:

- required media count and aspect ratio
- headline line count and occupancy
- body sentence count and occupancy
- numeric/quote/comment region requirements
- source-label space
- mobile safe area
- subject crop
- slide-role compatibility
- source-topic relevance

Allowed outcomes:

- `fit`
- `select_alternative_reference`
- `split_content_into_additional_slide`
- `reduce_nonessential_copy`
- `blocked`

It may not shrink text below the mobile readability floor or silently omit source-backed facts.

### 5. Render Request

Every slide sent to Satori contains:

- `primary_reference_id`
- `blueprint_id`
- `blueprint_version`
- `geometry_hash`
- `regions`
- `style_tokens`
- `content_bindings`
- `media_bindings`
- `reference_consumption_receipt`

The renderer binds content into supplied regions. When V2 geometry is present, account defaults and
the legacy `centered_panel` path may not override it.

## Selection Order

1. Account promise and slide role.
2. Available source media count, aspect ratio, and subject position.
3. Content structure: hook, evidence, comparison, quote, comment, flow, conclusion, or commerce.
4. Topic and issue context.
5. Emotional direction and intensity.
6. Copy occupancy.
7. Season and palette compatibility.
8. Recent-use diversity.

Layout is selected before palette variation. Palette variation cannot repair an incompatible
geometry.

## Fail-Closed Rules

Production render is blocked when:

1. No owner-approved primary reference exists.
2. The selected specimen has no complete geometry blueprint.
3. Required regions or media bindings are missing.
4. Copy or media cannot fit without violating readability or crop constraints.
5. Source-topic contamination is detected.
6. The render request does not preserve reference ID, blueprint version, and geometry hash.
7. The renderer reports zero consumed geometry regions.
8. The generated tree differs from the blueprint beyond the allowed region tolerance.

The standard Workflow remains fallback-first and `workflow_completed` remains protected. These
production blocks are data states, not Workflow failures.

## QA Contract

### Structural QA

- region count and required roles
- normalized box bounds
- overlap-policy compliance
- geometry hash match
- content-binding completeness
- media-binding completeness
- no legacy-layout override

### Visual QA

- region intersection-over-union against the blueprint
- title occupancy and line count
- media occupancy and crop
- safe-area compliance
- palette token use
- Korean font file actually loaded
- OCR readability
- OpenCLIP topic relevance
- blankness and repeated-image detection
- cross-slide rhythm and layout repetition

Automatic QA is evidence only. It cannot create owner visual approval or publishing readiness.

## Storage

Repository, lightweight:

- `knowledge/design_references/reference_specimen_registry.json`
- `knowledge/design_references/layout_blueprints.json`
- schema and selector code

F: data root, large:

- source screenshots
- derived review crops
- generated preview images
- render artifacts
- visual-diff artifacts

The repository stores paths and hashes, not duplicated image bytes.

## Implementation Slices

### Slice 1: Registry and Blueprint Schema

Add:

- `modules/design_learning/reference_specimen_registry.py`
- `modules/design_learning/layout_blueprint_contract.py`
- focused schema and approval tests

No renderer changes.

### Slice 2: Complete-Reference Selector

Replace abstract field selection for production with:

- `modules/design_learning/reference_recipe_selector.py`
- ranked complete-reference output
- deterministic rejection reasons

Keep `ProductionProfileCompiler` temporarily for diagnostics and compatibility only.

### Slice 3: Blueprint and Content Fit

Add:

- `modules/card_news/reference_blueprint_adapter.py`
- `modules/card_news/reference_content_fit.py`
- per-slide primary reference selection

Do not render when fit fails.

### Slice 4: Geometry Render Consumption

Modify:

- `modules/card_news/learning_design_compiler.py`
- `modules/card_news/production_render_request_builder.py`
- `modules/tool_adapters/cardnews_renderer_runtime.py` only if its current tree contract cannot
  preserve supplied region geometry

The request and renderer receipts must enumerate consumed regions.

### Slice 5: Structural and Visual Regression

Add:

- geometry-contract tests
- reference-selection tests
- content-fit tests
- render-request consumption tests
- one owner-authorized representative render
- side-by-side owner visual review

Full compile, full tests, and `py -m src.main` run occur once at final combined QA unless the owner
requests an earlier check.

## Acceptance Criteria

The redesign is not complete until a current representative render proves all of the following:

- one approved owner reference is named per slide
- its blueprint regions reach the Satori tree without reduction to abstract tags
- the receipt lists consumed geometry regions
- no unrelated source facts or images appear
- Korean typography uses an actual loaded font
- automatic structural and visual QA pass
- owner visually accepts the result

Passing unit tests or producing PNG files alone is insufficient.
