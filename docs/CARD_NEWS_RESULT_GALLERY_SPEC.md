# CardNews Result Gallery — UX & Information Architecture Spec

Author: Claude Specialist (Lane B, `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`)
Status: **DRAFT, spec-only. No code, no `site/` file, no shared status document touched.**

Legend: `CONFIRMED` = verified directly against current repository code/data at the time of
writing. `ASSUMPTION` = proposed UI/behavior not yet built or approved. `CTO GATE` = requires
explicit CTO decision before any implementation Sprint may start.

---

## 0. Scope and Non-Goals

### Scope

A non-code UX and information-architecture spec for a **CardNews Result Gallery** — the
future surface (likely inside `site/`, ownership not decided by this document — see §12) that
lets a human review one CardNews run's four PNGs, its QA status, and its publish-readiness
without opening raw JSON files by hand.

### Non-Goals

- No React/HTML/CSS/JS is written here.
- No claim that a gallery exists today. Individual-file PNG viewing already works (§1); a
  *gallery* (grid/carousel + QA panel + GO/NO-GO badge) does not exist yet.
- No modification to `modules/card_news/`, `modules/publishing/`, `site/`, or any shared status
  document. Every field this spec references is read-only input.
- No new manifest builder is written here — `modules/card_news/card_news_result_manifest.py`
  already exists (`CONFIRMED`, built by Lane C per `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`) and its
  real schema is documented in §10, not redesigned from scratch.

### Source of Truth Used for This Spec

`CONFIRMED` — read directly, same day, for this document:

| File | Role |
|---|---|
| `storage/card_news/card_news_quality.json` | Standalone QA result for the latest run |
| `storage/workflow_results/08_card_news_result.json` | Full CardNews stage output for the latest run |
| `storage/workflow_results/09_publishing_result.json` | Publishing gate output the manifest also reads (read via code, not directly required, but its shape is exercised by `card_news_result_manifest.py`) |
| `modules/card_news/card_news_module.py` | Renderer entry point, `_build_image_sourcing_status()` |
| `modules/card_news/card_news_quality_checker.py` | Full 39-key `checks` taxonomy and scoring |
| `modules/card_news/card_news_result_manifest.py` | Already-implemented manifest builder (Lane C) |
| `modules/publishing/publishing_module.py` | Publishing gate (`operations.publishing_blocked`) |
| `tests/test_card_news_result_manifest.py` | Confirmed fallback/edge-case behavior of the manifest |
| `.codex/skills/ai-content-os-card-news/SKILL.md`, `.claude/skills/domain/cardnews.md` | Domain conventions (note: the Claude skill file's QA-check count is stale versus the actual 39-key checker read directly for this spec — repository code was trusted over the skill doc, per instruction) |

---

## 1. Current State: Individual PNG Viewing (What Already Works)

`CONFIRMED` (per `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`'s "Current Integration Finding": *"App
individual-file viewing: GO."*) and independently verified in this same working session by
opening `storage/card_news/card_news_1.png` through `card_news_4.png` directly:

- Each of the four PNGs (`storage/card_news/card_news_{1..4}.png`, `CONFIRMED` 1080×1080,
  `card_news_quality.json.checks.resolution_ok: true`) can be opened today as a plain image file
  in the current app/Codex file viewer. No gallery code is required for this baseline capability.
- What is **not** available today: a single screen showing all four in sequence with QA/warning
  context alongside them. A reviewer must currently open each PNG individually and separately
  read `storage/card_news/card_news_quality.json` / `storage/workflow_results/08_card_news_result.json`
  to get the full picture.
- This gap — *file-open works, contextualized review does not* — is exactly what §2–§9 below
  specify.

---

## 2. Information Architecture Overview

```text
CardNewsModule.run()                 (CONFIRMED, existing, unmodified by this spec)
  -> storage/card_news/card_news_{1..4}.png
  -> storage/workflow_results/08_card_news_result.json
       (layout_result, rendering_result, design_quality_result, evidence_result,
        social_proof_result, story_flow_result, debate_result, typography_result,
        visual_rhythm_result, mobile_readability_result, attribution_present,
        image_sourcing_status, card_news_quality)
  -> storage/card_news/card_news_quality.json   (standalone copy of card_news_quality)

PublishingModule.run()               (CONFIRMED, existing, unmodified by this spec)
  -> storage/workflow_results/09_publishing_result.json
       (status: publishing_ready | publishing_blocked, operations.{publishing_blocked,
        blocking_reasons, real_image_used_count, required_action}, manual_image_required)

build_card_news_result_manifest()    (CONFIRMED, already implemented — Lane C)
  -> UI-friendly, safe-fallback dict: {schema_version, status, title, cards[], qa{}, publishing{},
     source_files{}}
       (this is the ONLY contract the Gallery UI needs to depend on — §10)

CardNews Result Gallery (proposed)   (ASSUMPTION — this document's subject, not built)
  -> consumes the manifest dict above, renders §4–§9 UI states
```

The Gallery must depend on the **manifest**, not on the raw stage JSONs directly — this keeps the
Gallery decoupled from any future field rename inside `card_news_result`/`publishing_result`
(`ASSUMPTION`, standard UI-boundary practice; reinforced by the manifest's own safe-fallback
design, §10–§11).

---

## 3. Responsibility Boundary: CardNews Generation vs. the Gallery

| Concern | Owner | Confirmed / Proposed |
|---|---|---|
| Render 4 PNGs, compute QA/typography/mobile/evidence/social-proof results | `CardNewsModule` + its helpers | `CONFIRMED`, existing |
| Compute publish GO/NO-GO (`publishing_ready`/`publishing_blocked`, `blocking_reasons`) | `PublishingModule` | `CONFIRMED`, existing |
| Normalize the above into one safe, UI-friendly dict | `card_news_result_manifest.py` | `CONFIRMED`, existing (Lane C) |
| Render the manifest as a reviewable screen (grid, carousel, badges, warnings list) | Gallery UI (future `site/` surface, ownership TBD) | `ASSUMPTION`, this spec |
| Decide *whether* to publish, resolve `manual_image_required`, source real images | Human operator | `CONFIRMED` (existing manual-checklist contract, `image_sourcing_status.checklist`) |
| Re-render cards, fix copy defects, re-run the workflow | CardNews content/generation lane (Codex worker), never the Gallery | `CONFIRMED`/`ASSUMPTION` boundary: the Gallery is **read-only**, exactly like the Codex file viewer today. It must never trigger regeneration, edit `content_result`, or write to `storage/`. |

**Hard boundary** (`CTO GATE` recommendation, not yet decided): the Gallery should never call
`CardNewsModule`, `PublishingModule`, or `WorkflowEngine` directly — it only reads the manifest
(and, for zoom/inspection, the four static PNG files). This mirrors the read-only precedent
already set by Lane D ("Codex Worker - Output QA", read-only) and Lane F ("Visual QA", read-only)
in `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`.

---

## 4. Screen Structure — Four-Card Sequential Preview (Proposed)

`ASSUMPTION` — no such screen exists yet. Proposed structure only.

### 4.1 Desktop

```text
┌─────────────────────────────────────────────────────────────────┐
│ Title: {manifest.title}                    [GO/NO-GO Badge]     │  <- §7
├─────────────────────────────────────────────────────────────────┤
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                     │
│ │ Card 1 │ │ Card 2 │ │ Card 3 │ │ Card 4 │   <- 4-up grid,      │
│ │ hook   │ │problem │ │solution│ │  cta   │      1080x1080 each, │
│ │        │ │        │ │        │ │        │      role label     │
│ └────────┘ └────────┘ └────────┘ └────────┘      under each      │
├─────────────────────────────────────────────────────────────────┤
│ QA Score: {qa.score}   Passed: {qa.passed}        <- §5          │
│ Warnings: [ ... list ... ]                                       │
├─────────────────────────────────────────────────────────────────┤
│ Publishing: {publishing.status}   Next action: {next_action}     │  <- §7
│ ⚠ manual_image_required: {publishing.manual_image_required}      │  <- §6
├─────────────────────────────────────────────────────────────────┤
│ Source / Evidence / Social Proof panel (collapsed by default)    │  <- §9
└─────────────────────────────────────────────────────────────────┘
```

- All four cards visible without scrolling on a standard desktop viewport (`ASSUMPTION`: target
  ≥1280px width, four 1080×1080 sources scaled to thumbnail size, e.g. 240×240 each).
  Clicking/tapping a card opens it at full/native resolution — reusing the same "open individual
  PNG" capability already confirmed in §1, not a new image-rendering path.
- Role label under each card comes directly from `manifest.cards[i].role` (`CONFIRMED` field:
  fixed order `hook`/`problem`/`solution`/`cta`, `CONFIRMED` from
  `card_news_result_manifest.py::CARD_ROLES`).

### 4.2 Mobile

```text
┌───────────────────────┐
│ Title                 │
│ [GO/NO-GO Badge]       │
├───────────────────────┤
│ ┌───────────────────┐ │
│ │   Card 1 (hook)    │ │  <- single-card carousel,
│ │                    │ │     swipe or dot-indicator
│ └───────────────────┘ │     to move between 1-4
│   ● ○ ○ ○              │
├───────────────────────┤
│ QA Score / Warnings    │  (collapsible)
├───────────────────────┤
│ Publishing status      │  (collapsible)
├───────────────────────┤
│ Source/Evidence panel  │  (collapsed by default)
└───────────────────────┘
```

- `ASSUMPTION`: mobile defaults to one card at a time (carousel) instead of a 4-up grid, since
  four 1080×1080 sources at readable thumbnail size do not fit a typical mobile viewport without
  becoming illegibly small — this directly serves the same "모바일 축소 시 주요 제목 판독 가능"
  concern already enforced at the renderer level (`mobile_readability_result`, §8).
- Collapsible sections default to collapsed on mobile to keep the four cards as the primary
  above-the-fold content, consistent with card-news's own "cover must not look like a body
  summary" principle already applied at the renderer level.

---

## 5. QA Score and Warning Display

`CONFIRMED` data source: `manifest.qa` (`{passed, score, warnings}`), backed by
`card_news_quality.json` / `card_news_result.card_news_quality`.

| Manifest field | Type | Confirmed example (latest run) | Proposed display |
|---|---|---|---|
| `qa.score` | float 0.0–1.0 or `null` | `1.0` | Numeric badge, e.g. "QA 100%" or "QA 1.00/1.00"; `null` renders as "QA: unavailable", never as `0%` (avoids implying a real failing score when the data simply wasn't computed) |
| `qa.passed` | bool | `true` | Pass/Fail chip, color-coded (`ASSUMPTION`: green/red), always shown next to the score, never replacing it |
| `qa.warnings` | list[str] | `[]` (this run: clean) | Expandable list, one row per warning string, verbatim (no paraphrasing — every warning already carries context in the checker's own message, e.g. "layout fallback") |

### Warning Taxonomy (for grouping/iconography only — text itself must remain verbatim)

`CONFIRMED` from `card_news_quality_checker.py`'s 39-key `checks` dict, grouped for the Gallery's
benefit (grouping is `ASSUMPTION`; the underlying facts are `CONFIRMED`):

| Group | Representative checks | Notes |
|---|---|---|
| File/structural | `png_exists`, `card_count_ok`, `file_size_ok`, `resolution_ok` | Hard failures — should be the most severe visual treatment if ever false |
| Layout/rendering fallback | `layout_fallback_used`, `rendering_fallback_used`, `fallback_used` | See §8 — must stay visually distinct from each other |
| Content structure | `story_flow_applied`, `slide_continuity_ok`, `cta_slide_exists`, `highlight_exists` | |
| Evidence & Social Proof | `evidence_available`, `evidence_applied`, `social_proof_available`, `social_proof_applied` | See §9 — conditional pass, must not read as "missing = broken" |
| Debate/CTA | `debate_should_apply`, `debate_required`, `debate_applied` | See §5.1 |
| Attribution | `attribution_needed`, `attribution_present` | See §9 |
| Typography/Mobile/Contrast | `typography_hierarchy_ok`, `cover_readability_ok`, `mobile_readability_ok`, `visual_rhythm_ok`, `text_overflow_free`, `contrast_ok`, `source_legible`, `cta_focus_ok` | |
| Rights/safety | `prohibited_fake_screenshot_absent`, `unlicensed_asset_not_rendered` | Should render as a hard-stop indicator if ever false — these encode the copyright/fabrication guarantees from CardNews M7 |

### 5.1 Debate "Required vs. Applied" Nuance (must not misdiagnose intentional skips)

`CONFIRMED`: `debate_required = debate_should_apply AND NOT skip_reason`
(`card_news_quality_checker.py`). This distinguishes an **intentional** skip (e.g. the CTA type
was already comment-inducing, so adding a debate question would be redundant —
`debate_result.skip_reason` non-empty) from an **actual defect** (debate should have applied and
did not, `skip_reason` empty). The Gallery must only surface a debate-related warning when
`debate_required: true AND debate_applied: false` — never when `debate_should_apply: true` but a
legitimate `skip_reason` exists. This directly reflects the ROADMAP M7-next correction: "의도된
Debate skip과 실제 미적용 결함 진단 분리."

---

## 6. `manual_image_required` Display

`CONFIRMED` source: `manifest.publishing.manual_image_required` (bool), backed by
`card_news_result.image_sourcing_status` (`CardNewsModule._build_image_sourcing_status()`).

Confirmed real example (latest run, community-type topic with no real image sourced):

```json
{
  "manual_image_required": true,
  "recommended_source": "post_capture",
  "real_image_used_count": 0,
  "checklist": [
    "권장 이미지 소스(post_capture)를 수동으로 수집해 카드뉴스에 반영하세요.",
    "실제 이미지가 없어 이번 렌더링은 solid-color 배경으로 대체되었습니다."
  ],
  "reason": "content_type 'community'은 실제 이미지가 필요하지만 아직 소싱되지 않음."
}
```

Note: this full object (`recommended_source`, `checklist`, `reason`) lives in
`card_news_result.image_sourcing_status`, **not** in the manifest — the manifest currently only
exposes the boolean `manual_image_required` (`CONFIRMED`, `card_news_result_manifest.py` line
89/114). See §10.3 for the proposed manifest extension to carry the checklist through.

### Proposed Display (`ASSUMPTION`)

- A dedicated banner/chip, always visible when `true`, never silently folded into the general
  warnings list (image sourcing is an operator action item, not a QA nitpick).
- Banner text: "실제 이미지 필요 — 권장 소스: {recommended_source}" with an expandable checklist
  (each `checklist[]` string as a literal checkbox item — do not paraphrase, since the checklist
  text is already the exact operator instruction).
- When `false`, no banner — do not show an empty-state "no action needed" banner either, to avoid
  clutter (silence is the correct signal here, consistent with the rest of this project's
  fallback-first "record only when something needs attention" convention).

---

## 7. `publishing.ready` / GO-NO-GO Display

`CONFIRMED` sources:

- `card_news_result` is not itself GO/NO-GO — GO/NO-GO is decided by `PublishingModule`
  (`operations.publishing_blocked`, `blocking_reasons: ["manual_image_required",
  "real_image_used_count_zero"]`, computed in `_resolve_publishing_gate()`), then re-derived once
  more, defensively, inside the manifest builder (`manifest.publishing.ready`,
  `card_news_result_manifest.py` line 110: `publishing_status_ready AND four_cards_available AND
  NOT manual_image_required`).
- `publishing_result.status` is one of exactly two confirmed values: `"publishing_ready"` or
  `"publishing_blocked"` (`CONFIRMED`, `publishing_module.py` line 284-288).

### Proposed GO/NO-GO Badge (`ASSUMPTION`)

| Condition (manifest fields) | Badge |
|---|---|
| `manifest.status == "ready"` (implies `publishing.ready == true`, all 4 cards exist, QA passed) | **GO** — green |
| `manifest.status == "incomplete"` and `publishing.manual_image_required == true` | **NO-GO — manual image required** — amber, links to §6 checklist |
| `manifest.status == "incomplete"` and `qa.passed == false` | **NO-GO — QA failed** — red, links to §5 warnings |
| `manifest.status == "incomplete"` and cards missing/incomplete | **NO-GO — cards incomplete** — red, links to §11 error state |

`manifest.publishing.next_action` (`CONFIRMED` field, verbatim string from
`publishing_result.next_action`) should always be shown as the badge's supporting text — it
already contains the exact next human step (e.g. "실제 이미지를 반영하고 이미지 체크리스트를
완료한 뒤 발행 준비 상태를 다시 확인").

**Gap identified** (`CTO GATE`, not implemented by this spec): `publishing_result.operations`
carries a richer `blocking_reasons` array (e.g. distinguishing "no manual image sourced yet" from
"zero real images used at all") than the manifest currently surfaces. The Gallery cannot show
*why*, specifically, publishing is blocked beyond the single `manual_image_required` boolean and
the `next_action` string, unless the manifest is extended (§10.3) or the Gallery reads
`publishing_result.operations` directly (which would break the "Gallery only depends on the
manifest" boundary in §3 — not recommended without a CTO decision).

---

## 8. Layout vs. Rendering Fallback — Must Stay Visually Distinct

`CONFIRMED`: `card_news_quality_checker.py` computes two **separate** booleans (this was the
exact fix behind the ROADMAP M7-next correction — "안전한 레이아웃 대체와 실제 렌더링 fallback
진단 분리"):

| Field | Meaning | Severity |
|---|---|---|
| `layout_fallback_used` | `LayoutSelector`/`LayoutRuleEngine` could not compute an intelligent layout choice and used the default layout rule. The card still renders correctly, just with a less-personalized layout. | Low — cosmetic, non-blocking |
| `rendering_fallback_used` | The layout-aware Pillow rendering path itself (`_create_card_with_layout`) raised and the renderer fell back to the plain default `_create_background`/`_draw_card` path for one or more cards. Still a valid, readable PNG, but the intended layout/typography/visual-rhythm treatment was not applied to those cards. | Medium — worth operator attention, not a hard failure |
| `fallback_used` (combined, `layout_fallback_used OR rendering_fallback_used`) | Legacy combined flag, still present for backward compatibility | Kept as an umbrella flag only |

### Proposed Display (`ASSUMPTION`)

- Two independent, separately labeled indicators (not one merged "fallback occurred" icon) —
  e.g. "레이아웃: 기본값 사용" (amber, informational) vs. "렌더링: 일부 카드 기본 렌더러 사용"
  (orange, worth reviewing which card(s)). Never collapse these into a single generic warning,
  since conflating them was the exact defect this project already had to reopen and fix once.
- If per-card fallback attribution becomes available in a future manifest version (currently the
  manifest does not track *which* of the 4 cards used the rendering fallback — only the
  aggregate `rendering_result.fallback_used`, `CONFIRMED` gap), flag this as a `CTO GATE` for a
  future manifest schema bump, not something to guess at in the UI.

---

## 9. Source / Evidence / Social Proof Status

`CONFIRMED` sources: `card_news_result.evidence_result`, `evidence_applied`,
`social_proof_result`, `social_proof_applied`, `attribution_present`. **None of these fields are
currently exposed in the manifest** (`CONFIRMED` gap — manifest only carries `qa` and
`publishing`); this section specifies the display *if/when* they are added, and flags the gap.

### 9.1 Evidence

Confirmed real example (latest run — 9 Instagram screenshots were candidates, all rejected):

```json
{
  "evidence_available": false,
  "top_evidence_asset": null,
  "candidate_found_count": 9,
  "topic_relevant_count": 0,
  "render_allowed_count": 0
}
```

Each rejected asset carries `selection_status` (e.g. `"rejected_irrelevant"`) and a human-readable
`rejection_reason` (e.g. "주제 관련 용어 일치 0건/점수 0.0로 기준(최소 2건, 점수 0.34) 미달.").

Proposed display (`ASSUMPTION`):

- When `evidence_available: false`, show a neutral informational line — **not** a warning icon —
  e.g. "이번 주제와 관련된 실제 증거 자료 없음 (검토된 후보 9건, 기준 미달)". This must read as
  *normal, honest state*, not a defect, matching the project-wide "data genuinely unavailable is
  never penalized" QA principle (§5, conditional checks).
- When `evidence_available: true` and `evidence_applied: true`, show the applied asset's
  `source_name` + `asset_type` (never the raw `source_url` in the main UI — `CONFIRMED` design
  intent from CardNews M7/M8: "긴 URL은 출력하지 않는다"; if a link-out is wanted, put it behind
  an explicit "원문 보기" action, not inline text — `ASSUMPTION`).
- Never show `competitor_reference`-classified assets as if they were used evidence, even in a
  "candidates considered" list, without the explicit `analysis_only: true` /
  `render_allowed: false` labels attached (`CONFIRMED` fields already carry this distinction).

### 9.2 Social Proof

Confirmed real example (latest run — no real third-party comment data exists):

```json
{
  "available": false,
  "unavailable_reason": "실제 댓글/반응 텍스트 필드(comment_text/reply_text/reaction_text/quote_text)를 가진 데이터가 어떤 소스에도 없음 - ...",
  "candidate_count": 0,
  "selected": []
}
```

Proposed display (`ASSUMPTION`): identical honest-neutral treatment as §9.1 — "실제 댓글/반응
데이터 없음" as an informational line, never a warning. If `selected` is ever non-empty in a
future run, each item already carries `is_opinion: true`, `label` (e.g. "커뮤니티 반응"), and
`masked_account_handle` (`CONFIRMED` fields from CardNews M7) — the Gallery must show the label
and masked handle exactly as provided and must never display the unmasked `account_handle` field
that also exists on the same object (present for internal/audit use only).

### 9.3 Attribution

`attribution_present` (`CONFIRMED`, currently `false` in the latest run since neither evidence nor
social proof was applied) should be shown as a small "출처 표시됨" chip only when `true`, attached
to the specific card that carries it (the Gallery would need per-card attribution data to place
this correctly — currently only a single aggregate boolean exists at the result level, `CONFIRMED`
gap, same category as the layout/rendering fallback per-card gap in §8).

**Gap identified** (`CTO GATE`): none of §9.1–§9.3's fields exist in the manifest today. Adding
them is a manifest-schema decision, owned by whoever owns
`modules/card_news/card_news_result_manifest.py` (Lane C per current assignment), not this spec.

---

## 10. Manifest Fields for `site/` (Confirmed Schema + Proposed Extensions)

### 10.1 Confirmed Current Schema (`schema_version: 1`)

`CONFIRMED`, read directly from `card_news_result_manifest.py` and its test suite
(`tests/test_card_news_result_manifest.py`):

```json
{
  "schema_version": 1,
  "status": "ready | incomplete",
  "title": "string",
  "cards": [
    {
      "index": 1,
      "role": "hook | problem | solution | cta",
      "path": "storage/card_news/card_news_1.png | null",
      "exists": true,
      "headline": "string",
      "status": "created | missing"
    }
  ],
  "qa": {
    "passed": true,
    "score": 1.0,
    "warnings": ["string", "..."]
  },
  "publishing": {
    "ready": true,
    "status": "publishing_ready | publishing_blocked | unavailable",
    "platform": "instagram",
    "upload_mode": "manual",
    "manual_image_required": false,
    "next_action": "string"
  },
  "source_files": {
    "card_news_result": "storage/workflow_results/08_card_news_result.json",
    "quality": "storage/card_news/card_news_quality.json",
    "publishing": "storage/workflow_results/09_publishing_result.json"
  }
}
```

### 10.2 Confirmed Safety Guarantees (from the manifest's own tests)

| Guarantee | Confirmed by |
|---|---|
| Missing/malformed source JSON never raises — manifest returns a safe `status: "incomplete"` dict | `test_missing_and_malformed_files_return_safe_fallback` |
| `cards` array is always exactly 4 entries, in fixed `hook/problem/solution/cta` order, even if source data is empty, reversed, or partial | `test_builds_ordered_repository_relative_manifest` (reversed input still sorts to `[1,2,3,4]`) |
| A `card_path` pointing outside the repository root is rejected (`path: null`), never followed | `test_rejects_card_path_outside_repository` |
| `manual_image_required: true` forces `publishing.ready: false` and `status: "incomplete"` regardless of any other field | `test_manual_image_requirement_blocks_all_ready_states` |
| All paths returned are repository-relative POSIX strings, never absolute/OS-specific | `_repository_relative()`, exercised by all tests above |

These guarantees mean the Gallery can safely render **every** state in §11 (loading/empty/error)
purely from `manifest.status` + `manifest.qa` + `manifest.cards[].exists`, without needing its own
duplicate file-existence or JSON-parsing logic.

### 10.3 Proposed Extensions (`ASSUMPTION`, `CTO GATE` — not implemented by this spec)

Gaps identified while writing §6, §8, §9 above, listed here for the manifest's owner (Lane C) to
evaluate, not implemented here:

| Proposed field | Would answer | Source (already exists in `card_news_result`) |
|---|---|---|
| `publishing.blocking_reasons: string[]` | "정확히 왜 막혔는가" (§7 gap) | `publishing_result.operations.blocking_reasons` |
| `publishing.real_image_used_count: int` | Same as above, numeric detail | `publishing_result.operations.real_image_used_count` |
| `image_sourcing.checklist: string[]` + `recommended_source: string` | Full manual-image checklist, not just the boolean (§6 gap) | `card_news_result.image_sourcing_status` |
| `evidence.available` / `evidence.applied` / `evidence.top_asset_summary` | §9.1 | `card_news_result.evidence_result`, `evidence_applied` |
| `social_proof.available` / `social_proof.applied` | §9.2 | `card_news_result.social_proof_result`, `social_proof_applied` |
| `attribution.present` | §9.3 | `card_news_result.attribution_present` |
| `cards[].layout_fallback_used` / `cards[].rendering_fallback_used` (per-card, not just aggregate) | §8 per-card attribution gap | Not currently tracked per-card anywhere — would require a `CardNewsModule` change, out of this spec's and Lane C's scope without a separate CTO decision |

Each row is a **candidate**, not a request to implement. Whether/when to add them, and to bump
`schema_version` accordingly, is `CTO GATE`.

---

## 11. Empty, Error, and Loading States

`ASSUMPTION` for all UI treatment; the underlying data conditions are `CONFIRMED` from the
manifest's fallback design and its tests (§10.2).

| State | Trigger (confirmed data condition) | Manifest signal | Proposed UI treatment |
|---|---|---|---|
| **Empty** (no run yet) | `storage/workflow_results/08_card_news_result.json` does not exist (e.g. before the first workflow run) | `status: "incomplete"`, all `cards[].path: null`, `cards[].status: "missing"`, `qa.passed: false`, warning `"card news result file is missing: 08_card_news_result.json"` | Full-screen empty state: "아직 생성된 카드뉴스가 없습니다" + (if applicable) a link to trigger/observe the workflow — **not** a broken-looking error screen |
| **Error — malformed data** | Any source JSON exists but fails to parse (`json.JSONDecodeError`) or is not a JSON object | `status: "incomplete"`, warning `"... file could not be read: ... (JSONDecodeError)"` | Distinct from Empty — show the exact warning string, since it names the broken file; treat as an operator-actionable bug report, not a normal empty state |
| **Error — card file missing/invalid path** | A `card_path` is absent, points outside the repo, or the file does not exist on disk | Per-card `exists: false`, `path: null` possibly with a card-specific warning (`"card {index} path is invalid or outside the repository"`) | Show a placeholder tile for that specific card slot (broken-image icon + role label) rather than failing the whole gallery — the other 3 cards, if valid, should still render |
| **Loading** | The manifest build itself is a synchronous, point-in-time file read — there is no confirmed "workflow in progress" signal exposed to the manifest today | Not applicable — no data-level "in progress" state exists | `ASSUMPTION` only: a UI-level spinner while the manifest fetch itself is pending (network/IO latency), not a workflow-progress indicator. Do not fabricate a progress percentage — there is no real source for one. If "is the workflow currently running" becomes a real requirement, that is a `CTO GATE` for a separate signal (e.g. a lock file or run-status endpoint), not something this manifest currently provides. |

---

## 12. Unresolved CTO Gates (Summary)

| # | Gate | Where raised |
|---|---|---|
| 1 | Whether/where the Gallery lives inside `site/`, and whether `site/`'s ownership/product role is confirmed before any gallery code is written | §3, `docs/ACTIVE_PARALLEL_WORK_ORDERS.md` Lane A already flags this as unresolved |
| 2 | Whether to extend the manifest to `schema_version: 2` with the fields proposed in §10.3 | §10.3 |
| 3 | Whether to expose `publishing_result.operations.blocking_reasons` to the UI at all, and if so, through the manifest or a direct read (breaking the manifest-only boundary) | §7 |
| 4 | Whether per-card fallback/attribution tracking (§8, §9.3) is worth a `CardNewsModule` change, given it currently only exists in aggregate | §8, §9.3 |
| 5 | Whether a real "workflow in progress" signal is worth building for a Loading state, or whether point-in-time manifest reads are sufficient indefinitely | §11 |

---

## Summary for Reviewers

This spec documents what already works (individual PNG viewing, §1), the already-implemented
manifest contract the Gallery should depend on (§10.1–10.2, built by Lane C), and a full proposed
UI structure (§4) plus display rules for QA (§5), manual-image gating (§6), publish GO/NO-GO (§7),
fallback-severity separation (§8), and evidence/social-proof/attribution honesty (§9) — each rule
traced to a real, currently-produced field. Five gaps between the current manifest and this
spec's full display needs are listed as candidate extensions (§10.3) and CTO gates (§12), not
implemented. No code, `site/` file, or shared status document was modified.
