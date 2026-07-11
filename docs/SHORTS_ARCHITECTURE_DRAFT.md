# Shorts Phase 0 — Architecture and Contract Draft

Status: **PHASE 0 APPROVED WITH CTO CONSTRAINTS. Contract-only; no code implemented and no `WorkflowEngine` wiring.**

Legend: `CONFIRMED` = verified directly against current repository code/docs. `ASSUMPTION` =
reasonable proposal not yet verified against a real dependency or CTO decision. `CTO GATE` =
requires explicit CTO approval before any implementation Sprint may start.

---

## 1. Purpose, User Outcome, Scope, Non-Goals

### Purpose

Define, on paper only, how a future Shorts/Reels pipeline would reuse AI-Content-OS's existing
Topic/Research/Content/Brand DNA/CardNews/Publishing outputs to produce a **script + scene +
asset + caption + audio + render plan**, without building any renderer, without touching
`WorkflowEngine`, and without requiring any external API key.

### User Outcome (Phase 0)

The project owner gets a fully-specified, human-reviewable **Shorts production brief** (script,
scene breakdown, asset requirements, captions, audio plan, and a manual operator checklist) for a
given topic — enough to hand to a human editor (or a manual CapCut/Edits workflow) today, with no
automated rendering. `CONFIRMED`: this mirrors the existing Sprint-13 `image_sourcing_status`
manual-checklist pattern in `modules/card_news/card_news_module.py` /
`modules/publishing/publishing_module.py`, which already ships a `manual_image_required` +
`checklist` fallback for real-image sourcing gaps.

### Scope (Phase 0 only)

- Data contracts (JSON schemas) for every stage from Brief to Publish-Preparation.
- Deterministic, offline, no-API-key stage logic design (rule-based, reusing existing
  Pattern/Hook/CTA vocabulary — see §2).
- A manual operator checklist covering every place a human must do real work (assets, voice,
  music, captions, render review, rights, upload).
- A phased roadmap from "contract only" to "optional production renderer," each phase gated.

### Explicit Non-Goals (Phase 0)

- No actual script/caption generation code, no actual rendering, no actual TTS/transcription
  calls, no actual video file output.
- No `WorkflowEngine` wiring (`CONFIRMED` gate from
  `.codex/skills/ai-content-os-shorts/SKILL.md`: "Do not wire Shorts into `WorkflowEngine` during
  planning").
- No duplication or modification of `CardNewsModule`, its Pillow renderer, or
  `CardNewsQualityChecker` (`CONFIRMED` gate from this task's Protected Boundaries).
- No new top-level Engine created in this Phase — this document only *proposes* a future
  `modules/shorts/` module tree; nothing is created.
- No claim that Shorts is implemented, tested, or operational.

### Current Repository State This Draft Was Written Against

`CONFIRMED`: CardNews Intelligence (**M7**), Production Quality (**M8**), and operational
validation (**M7-next**) are complete. The closure evidence is four visually inspected PNGs,
Production QA 0.85/pass with `rendering_fallback_used: false`, 38 focused production-quality
tests, a clean compile check, and a preserved `workflow_completed` result. Shorts work starts only
as a standalone path and must not reopen or modify the protected CardNews pipeline.

---

## 2. Inputs Reused From Existing Engines

Every field below is either `CONFIRMED` (read directly from the named module's actual `run()`
output in this repository) or `ASSUMPTION` (a proposed new field/behavior). No Shorts stage
invents a field name that collides with an existing one.

### 2.1 From `modules/topic_engine/topic_engine_module.py` (`topic_result.selected_topic`)

`CONFIRMED` fields: `keyword`, `title`, `angle`, `target`, `reason`, `score`, `source`, and
(when sourced from Trend) `quality_score`, `selection_reason`, `collection_method`.

### 2.2 From `modules/research/research_module.py` (`research_result`)

`CONFIRMED` fields: `keyword`, `title`, `summary`, `key_points` (list[str]), `topic_angle`,
`target`, `topic_intelligence` (dict, from Pattern Engine), `pattern_plan`, `research_context`
(includes `category`, `cluster`, `confidence_score`), `research_insight` (`issue_background`,
`why_trending_now`, `audience_interest_points`, `caution_expressions`, `fallback_used`).

### 2.3 From `modules/content/content_module.py` (`content_result`)

`CONFIRMED` fields: `title`, `slides` (list of `{page, role, headline, body}`, canonical role
order `hook -> problem -> solution -> cta`, `modules/content/content_output_normalizer.py`),
`caption`, `hashtags`, `status` (`"content_created"`), `content_intelligence.quality_score`,
`pattern_prompt_meta.pattern_type` (`number_list`/`warning`/`comparison`/`tutorial`/`story`/
`resource`/`funnel`, `modules/pattern_engine/pattern_selector.py`), `pattern_prompt_meta.cta_type`
(`save`/`comment`/`dm`/`profile`/`follow`, `modules/pattern_engine/cta_selector.py`), and the
derived `hook_type` vocabulary (`attention`/`saveable_tip`/`authority`/`contrarian`/`pain_point`,
`modules/pattern_engine/hook_selector.py`).

**Reuse plan**: the existing 4-slide `hook -> problem -> solution -> cta` structure becomes the
Shorts script's default scene backbone — the same narrative shape CardNews already uses
(`CONFIRMED`: `modules/card_news/story_flow_planner.py` already does an equivalent narrative-role
mapping for CardNews; the Shorts Script Planner would need its own equivalent file, not an import
of that one, per the "no CardNews duplication" boundary).

### 2.4 From `modules/brand_dna_engine/` + `config/brand_profile.json`

`CONFIRMED` fields (`brand_dna_engine_module.py::run()`): `dominant_hook_type`,
`dominant_cta_type`, `dominant_layout_type`, `dominant_color`. `CONFIRMED` fields
(`config/brand_profile.json`): `brand_name`, `voice`, `tone_keywords`, `banned_words`,
`target_audience`, `cta_style`.

### 2.5 From `modules/card_news/` (Evidence/Social Proof *pattern* reuse, not code reuse)

`ASSUMPTION` (explicit design choice, not a code dependency): the Shorts Asset Planner reuses the
same **vocabulary and gating philosophy** already proven in
`modules/card_news/evidence_selector.py` (`candidate_found`/`topic_relevant`/`render_allowed`/
`asset_role` gates, and the `copyright_status` allow-list:
`owned`/`licensed`/`public_domain`/`official_reuse_allowed`/`user_supplied_with_permission` vs.
blocked `third_party_unlicensed_reference`/`unknown`/`restricted`) — as a **new, separate file**
in `modules/shorts/`, never importing from `modules/card_news/`. This keeps the "no CardNews
duplication" boundary while not reinventing an already-reviewed safety pattern from scratch.

### 2.6 From `modules/publishing/publishing_module.py` (`publishing_result`)

`CONFIRMED` fields: `platform`, `upload_mode`, `card_paths` (→ Shorts equivalent:
`render_file_path`), `caption`, `hashtags`, `full_caption`, `image_sourcing_status` (→ Shorts
equivalent: `asset_sourcing_status`), `manual_image_required` (→ `manual_asset_required`),
`next_action`, `planner_strategy` (AI Planner influence summary — read-only copy pattern).

### 2.7 Not Reused (by design)

Shorts does **not** read `card_news_result` directly (different content form, different asset
needs) except for the vocabulary-reuse noted in §2.5. Shorts does **not** call
`PlannerConsumerAdapter` in Phase 0 (`ASSUMPTION`: deferred to a later phase, since AI Planner's
`COORDINATED_ENGINES` list in `modules/ai_planner/planner_contract.py` does not currently include
a Shorts engine — adding it is a `CTO GATE`, not a Phase 0 decision).

---

## 3. Proposed Output Contracts

All contracts below are `ASSUMPTION` (new, proposed schemas). Every stage follows the existing
project convention: a `status` string, a `fallback_used` boolean, and (when `fallback_used` is
true) a human-readable `reason` — matching every existing Engine in this repository.

### 3.1 Shorts Brief (`shorts_brief_result`)

```json
{
  "module": "ShortsBriefBuilder",
  "status": "shorts_brief_created",
  "source_content_ref": {"title": "...", "caption_hash": "ASSUMPTION: reuse ContentPerformanceHistory.build_content_id()-style title+caption hash"},
  "topic": {"keyword": "...", "title": "...", "angle": "...", "target": "..."},
  "research_summary": "...",
  "key_points": ["..."],
  "pattern_type": "tutorial",
  "hook_type": "pain_point",
  "cta_type": "save",
  "brand_voice": {"tone_keywords": ["..."], "banned_words": ["..."], "target_audience": "...", "cta_style": "..."},
  "dominant_brand_style": {"dominant_hook_type": "...", "dominant_cta_type": "...", "dominant_color": "..."},
  "fallback_used": false,
  "reason": ""
}
```

### 3.2 Shorts Script (`shorts_script_result`)

```json
{
  "module": "ShortsScriptPlanner",
  "status": "shorts_script_created",
  "duration_target_seconds": 30,
  "script_lines": [
    {"line_id": 1, "role": "hook", "text": "...", "estimated_seconds": 3.0},
    {"line_id": 2, "role": "problem", "text": "...", "estimated_seconds": 5.0}
  ],
  "total_estimated_seconds": 27.5,
  "duration_limit_ok": true,
  "trimmed_line_count": 0,
  "fallback_used": false
}
```

### 3.3 Scene Plan (`shorts_scene_plan_result`)

```json
{
  "module": "ShortsScenePlanner",
  "status": "shorts_scene_plan_created",
  "scenes": [
    {"scene_id": 1, "script_line_ids": [1], "visual_type": "text_over_background", "asset_ref": null, "duration_seconds": 3.0, "transition": "cut"}
  ],
  "scene_count": 4,
  "layout_source": "rule_table (new module, see section 2.5)",
  "fallback_used": false
}
```

### 3.4 Asset Plan (`shorts_asset_plan_result`)

```json
{
  "module": "ShortsAssetPlanner",
  "status": "shorts_asset_plan_created",
  "assets": [
    {
      "scene_id": 1,
      "asset_type": "background_video",
      "candidate_found": false,
      "topic_relevant": null,
      "copyright_status": "unknown",
      "render_allowed": false,
      "manual_action_required": true,
      "reason": "No real asset source connected in Phase 0"
    }
  ],
  "manual_asset_required_count": 1,
  "fallback_used": true,
  "reason": "Phase 0 has no automated real-asset sourcing (see section 7)"
}
```

### 3.5 Captions (`shorts_caption_result`)

```json
{
  "module": "ShortsCaptionPlanner",
  "status": "shorts_captions_created",
  "caption_source": "script_text_only",
  "captions": [{"scene_id": 1, "start_seconds": 0.0, "end_seconds": 3.0, "text": "..."}],
  "transcription_used": false,
  "transcription_provider": null,
  "fallback_used": false
}
```

### 3.6 Audio Plan (`shorts_audio_plan_result`)

```json
{
  "module": "ShortsAudioPlanner",
  "status": "shorts_audio_plan_created",
  "voice_source": "manual_recording_required",
  "tts_provider": null,
  "tts_available": false,
  "music_source": "manual_licensed_track_required",
  "music_track_ref": null,
  "manual_action_required": true,
  "fallback_used": true,
  "reason": "No TTS/music provider connected in Phase 0 (CTO GATE, see section 7)"
}
```

### 3.7 Render Plan (`shorts_render_plan_result`)

```json
{
  "module": "ShortsRenderPlanner",
  "status": "shorts_render_plan_created",
  "render_target": "vertical_1080x1920",
  "scene_count": 4,
  "estimated_duration_seconds": 27.5,
  "renderer": "not_selected",
  "manual_edit_tool_reference": "CapCut / Edits (benchmark/TOOLS_AND_FUNNEL_REFERENCES.md, CONFIRMED reference, tool selection is CTO GATE)",
  "fallback_used": true,
  "reason": "No render engine implemented in Phase 0 - manual editing required"
}
```

### 3.8 QA Result (`shorts_qa_result`)

```json
{
  "module": "ShortsQualityChecker",
  "status": "shorts_qa_completed",
  "qa_score": 0.0,
  "passed": false,
  "checks": {
    "duration_within_limit": true,
    "caption_sync_ok": null,
    "asset_provenance_ok": true,
    "unlicensed_asset_not_used": true,
    "prohibited_fake_transcript_absent": true,
    "manual_checklist_complete": false
  },
  "warnings": ["Manual asset/audio/render checklist not yet completed"],
  "recommendations": ["Complete manual operator checklist (section 6) before publishing"]
}
```

### 3.9 Publish-Preparation Result (`shorts_publish_prep_result`)

```json
{
  "module": "ShortsPublishPreparationModule",
  "status": "shorts_publish_prep_ready",
  "platform": "instagram_reels",
  "upload_mode": "manual",
  "render_file_path": null,
  "caption": "...",
  "hashtags": ["..."],
  "manual_checklist": ["..."],
  "manual_action_required": true,
  "created_at": "..."
}
```

---

## 4. Module Boundaries and Minimal Future File Map

`ASSUMPTION` — none of the below exists yet; this is the proposed shape only, following the
existing `modules/<engine>/` + `storage/<engine>/` convention already used by every Engine in
this repository (e.g. `modules/competitor_learning/`, `CONFIRMED` standalone-not-in-
`WorkflowEngine.run()` precedent).

```text
modules/shorts/                      (proposed, not created)
  shorts_brief_builder.py
  shorts_script_planner.py
  shorts_scene_planner.py
  shorts_asset_planner.py
  shorts_caption_planner.py
  shorts_audio_planner.py
  shorts_render_planner.py
  shorts_quality_checker.py
  shorts_publish_preparation_module.py
  shorts_module.py                   (orchestrator; standalone/on-demand like
                                       modules/competitor_learning/competitor_learning_module.py —
                                       NOT called from WorkflowEngine.run())

storage/shorts/                      (proposed; needs a .gitignore allow-list entry,
                                       same pattern as storage/planner/.gitkeep)
  shorts_brief.json / shorts_script.json / ... (per-stage outputs)

tests/
  test_shorts_*.py                   (future, risk-based, no test-count target —
                                       same approach as tests/test_card_news_production_quality.py)
```

### Boundary Rules

| Rule | Status |
|---|---|
| No import of `modules/card_news/*` into `modules/shorts/*` | `CTO GATE` (hard requirement per Protected Boundaries) |
| `modules/shorts/shorts_module.py` never called from `src/workflow_engine.py` in Phase 0 | `CTO GATE` |
| No renaming of any existing module/folder/class/function | `CTO GATE` |
| Each Shorts stage file is independently unit-testable with no network/LLM call | `ASSUMPTION` (design goal) |

---

## 5. Deterministic Offline/Fallback Behavior

Every stage must degrade the same way every existing Engine in this repository does: never raise
past its own `run()`, always return a safe dict with `fallback_used` + `reason`.

| Dependency | Failure Mode | Fallback Behavior | Recorded As |
|---|---|---|---|
| Topic/Research/Content/Brand DNA read | Missing/malformed source file | Use safe empty defaults, same pattern as `ResearchModule._fallback_result()` | `fallback_used: true`, `reason` |
| Script duration budget | Script exceeds target seconds | Trim trailing script lines (never mid-sentence), same "remove sentence, not truncate silently" principle as CardNews M8's `_fit_lines`/`SENTENCE_SPLIT_PATTERN` fix | `trimmed_line_count`, `duration_limit_ok: false` before trim |
| Real asset sourcing | No real video/image/icon available | `manual_action_required: true`, asset marked `candidate_found: false`, never substitute an AI-generated or unrelated asset silently | `shorts_asset_plan_result.assets[].reason` |
| Transcription (e.g. AssemblyAI, per `benchmark/TOOLS_AND_FUNNEL_REFERENCES.md` "Bla View" reference) | No API key / call fails | Captions derived from script text only, `transcription_used: false` | `shorts_caption_result.transcription_provider: null` |
| TTS | No provider connected | `voice_source: "manual_recording_required"` | `shorts_audio_plan_result.reason` |
| Music | No licensed source connected | `music_source: "manual_licensed_track_required"` | `shorts_audio_plan_result.reason` |
| Render engine | Not implemented in Phase 0 | `renderer: "not_selected"`, manual edit tool reference only | `shorts_render_plan_result.reason` |
| Publish API | Not implemented (`ROADMAP.md` "Requires External API") | `upload_mode: "manual"`, checklist-only | `shorts_publish_prep_result.manual_checklist` |

No stage may reach `WorkflowEngine.run()`'s outer handler — this is moot in Phase 0 since
nothing is wired in, but the same fail-safe discipline applies to keep future wiring low-risk.

---

## 6. Manual Operator Checklist (Phase 0 Deliverable)

Every Shorts brief this pipeline produces ships with a checklist like this one (rendered from
`shorts_publish_prep_result.manual_checklist`):

- [ ] **Assets**: source or approve every scene's background/visual asset; confirm
      `copyright_status` for each (owned/licensed/public domain/official reuse/user-supplied with
      permission only — never publish an `unknown`/`restricted`/`third_party_unlicensed_reference`
      asset).
- [ ] **Voice**: record or generate narration via an approved TTS provider (see section 7); review for
      tone/brand-voice match against `config/brand_profile.json`.
- [ ] **Music**: attach a licensed/royalty-free track; confirm license terms permit the intended
      platform and monetization status.
- [ ] **Captions**: verify caption timing against the actual final audio/video (script-estimated
      timing is not guaranteed accurate).
- [ ] **Render review**: watch the full rendered output before upload; confirm no silent text
      truncation, no mismatched captions, no placeholder/watermarked assets.
- [ ] **Rights**: confirm no real person's likeness/voice is used without consent; confirm no
      copyrighted third-party footage without a license.
- [ ] **Upload**: confirm target platform, account, and caption/hashtag text before manual upload
      (Phase 0 has no automated publish step).

---

## 7. External Dependency Gates (No API Key Required for Phase 0)

Phase 0 defines these dependencies and their fallback contracts only — it calls none of them.
Every row below requires an explicit `CTO GATE` before any Sprint may add a real integration, per
`ROADMAP.md`'s "Requires External API" precedent.

| Dependency | Purpose | Candidate Reference | License/Cost/Data-Handling/Replaceability | API Key in Phase 0 |
|---|---|---|---|---|
| Transcription | Extract/verify spoken text for captions | AssemblyAI, referenced via "Bla View" in `benchmark/TOOLS_AND_FUNNEL_REFERENCES.md` (`CONFIRMED` reference exists in repo docs; `ASSUMPTION` on suitability) | `CTO GATE`: license/pricing/data-retention terms not verified in this repo; must be confirmed before use; swappable for any other STT API without contract changes (transcription output only feeds `captions[].text`) | No |
| TTS (voice) | Generate narration audio | Not yet identified in repo docs | `CTO GATE`: no vendor confirmed; must document license/cost/data handling before selection | No |
| Video generation/editing | Turn scene plan into a rendered video | CapCut / Edits, referenced in `benchmark/TOOLS_AND_FUNNEL_REFERENCES.md` §2 (manual tool workflow: "CapCut edit -> import to Edits -> add link -> upload") (`CONFIRMED` reference) | `CTO GATE`: these are manual desktop/mobile apps, not an API — Phase 0-2 assume **manual** use of such a tool, not automated calls; no cost/license risk to the codebase since no integration exists | No |
| Music | Background audio track | Not yet identified | `CTO GATE`: must be a licensed/royalty-free source; no vendor selected | No |
| Stock assets | Background image/video when no real asset exists | Not yet identified | `CTO GATE`: must guarantee `copyright_status` in the same allow-list as §2.5; no vendor selected | No |
| Platform publishing API | Automated Reels/Shorts upload | Instagram/Meta Graph API (`CONFIRMED` already gated project-wide in `ROADMAP.md` "Requires External API") | Already governed by existing project policy — Offline-First principle applies unchanged | No |

---

## 8. Copyright, Likeness, Disclosure, Privacy, Platform-Policy, Credential Constraints

- **Copyright**: reuse the exact `copyright_status` allow-list already established for CardNews
  Evidence (`owned`/`licensed`/`public_domain`/`official_reuse_allowed`/
  `user_supplied_with_permission` render-allowed; everything else blocked). No asset may be used
  in a render without a `render_allowed: true` gate, mirroring
  `modules/card_news/evidence_selector.py`'s design (not its code).
- **Likeness**: no synthetic voice/face/likeness of a real, identifiable person may be generated
  or used without documented consent. This is a hard `CTO GATE` before any TTS/avatar feature is
  proposed.
- **Disclosure**: any AI-generated voice, footage, or fully-synthetic scene must be disclosed in
  the caption or on-screen per current platform policy at time of implementation (platform
  policies change — re-verify at implementation time, do not hardcode a disclosure string now).
- **Privacy**: no real third-party comment/DM/personal data may be surfaced in a Short, mirroring
  the Social Proof masking/PII-scrub discipline already implemented in
  `modules/card_news/social_proof_selector.py` (`_mask_account_handle`/`_scrub_sensitive_info`) —
  same principle, new file, if/when Shorts ever needs a comment-reaction feature.
- **Platform policy**: Instagram/Meta Reels policy (length limits, audio licensing, disclosure
  requirements) must be re-checked at implementation time; this draft does not hardcode current
  policy values since they can change independent of this repository.
- **Credential handling**: no API key/credential for any dependency in §7 may be committed,
  logged, or hardcoded. If a future Sprint adds a real provider, its key must follow the existing
  `.env`-based pattern already used for `OPENAI_API_KEY` (`CONFIRMED`, `CLAUDE.md`: "`.env` holds
  `OPENAI_API_KEY` and is gitignored. Never commit it or print its contents.").

---

## 9. Risk-Based Test Plan (Future Sprint, Not Written in Phase 0)

No test-count target — each future test should map to one specific risk, following the pattern
established in `tests/test_card_news_production_quality.py` (38 targeted tests, no padding).

| Risk | Test Approach |
|---|---|
| Unit contract drift | Each stage's output dict has every required key with the correct type, for both success and fallback paths |
| Fallback paths never raise | Call every stage with empty/malformed/missing input; assert no exception escapes `run()` |
| Duration/caption limits | Script exceeding `duration_target_seconds` trims trailing lines, never mid-sentence (reuse the M8 "no silent truncation" regression-test pattern) |
| Asset provenance | An asset with `copyright_status` outside the allow-list can never reach `render_allowed: true` |
| No fabricated transcript/comment data | Transcription/caption stage never invents text when the real transcript source is unavailable — `transcription_used` must be `false` in that case |
| Manual checklist completeness | `shorts_publish_prep_result.manual_checklist` is non-empty whenever any upstream stage set `manual_action_required: true` |
| Future end-to-end verification | Once a real Sprint implements these stages, a full local run (`shorts_module.py` invoked standalone, not via `WorkflowEngine`) must produce all 9 result JSONs and a non-empty manual checklist, with zero external API calls attempted unless explicitly enabled by config |

---

## 10. Phased Roadmap

Each phase is independently approvable; no phase may start before the prior phase's exit
criteria are met and explicitly approved.

| Phase | Scope | Entry Criteria | Exit Criteria | Dependencies | Rollback Boundary |
|---|---|---|---|---|---|
| **Phase 0** (this document) | Contracts + fallback design only, no code | M7/M8 CardNews complete (`CONFIRMED`) | This draft reviewed and approved by CTO/Work | None | Delete/revise this doc; no code exists to roll back |
| **Phase 1** (proposed) | Implement Brief/Script/Scene/Caption/Audio-plan/Render-plan/QA/Publish-prep stages as real, offline, rule-based code (no rendering, no external API calls) — mirrors AlphaCut's "adopt Layout/Template/Highlight first" priority (`CONFIRMED`, `docs/RESEARCH/AlphaCut.md`) | Phase 0 approved | All 9 contracts implemented, unit-tested (risk-based, §9), `py -m compileall` clean, standalone script runs end-to-end producing all 9 JSONs with zero API calls | None (pure local logic + existing local Engine outputs) | Delete `modules/shorts/`; zero impact on `WorkflowEngine` or any other Engine |
| **Phase 2** (proposed) | Add one transcription and one TTS integration, gated behind explicit config flags, each individually approved (§7) | Phase 1 shipped and stable | Each integration has a documented license/cost/data-handling decision on record in `DECISIONS.md`; both remain fully optional (absence never blocks Phase 1 output) | External API keys (`CTO GATE` per integration) | Disable config flag; pipeline reverts to Phase 1 manual-only behavior |
| **Phase 3** (optional) | Evaluate an actual video render path — either a manual-tool export format (e.g. an EDL/project file importable into CapCut/Edits, avoiding building a renderer at all) or a minimal internal renderer, following AlphaCut's "Timeline/Animation/Video Renderer: adopt later" guidance (`CONFIRMED`) | Phase 2 stable, explicit CTO approval to build/integrate a renderer | A single real Shorts video produced and manually reviewed against the QA checklist (§6, §9) | Renderer choice (`CTO GATE`, full license/cost/replaceability writeup required per Protected Boundaries) | Fall back to Phase 2's manual-editing-tool workflow; no renderer code required to exist |
| **Phase 4** (optional, gated by `ROADMAP.md`) | `WorkflowEngine` wiring + platform publish API | Phase 3 stable, explicit CTO approval, `ROADMAP.md` "Requires External API" section updated first | Full pipeline reachable from `py -m src.main` without breaking `workflow_completed` | Instagram/Meta Graph API + OAuth (`CTO GATE`, same policy as existing Instagram Intelligence Phase's deferred Closed Loop) | Keep Shorts standalone/on-demand indefinitely if this phase is never approved |

---

## 11. Open Questions and CTO Approval Gates

| # | Question | Type |
|---|---|---|
| 1 | Should Shorts scripts be generated via LLM (like `ContentModule`'s `LLMClient`) or purely rule-based from existing `content_result.slides`? | `CTO GATE` |
| 2 | Which TTS and transcription vendors, if any, are approved for Phase 2 — and under what license/cost terms? | `CTO GATE` |
| 3 | Should Phase 3 build a minimal internal renderer at all, or standardize on manual CapCut/Edits export forever (avoiding a renderer entirely)? | `CTO GATE` |
| 4 | Should AI Planner (`modules/ai_planner/`) be extended to cover Shorts hint consumption, and if so, in which phase? | `CTO GATE` |
| 5 | Should Shorts reuse `content_result` directly (1 Shorts per CardNews topic) or should Topic Engine support a Shorts-specific topic selection path? | `CTO GATE` |
| 6 | What are the current (at implementation time) Instagram Reels duration limits, disclosure requirements, and audio licensing rules? | `ASSUMPTION` — must be re-verified at implementation time, not assumed from this draft |
| 7 | Is `storage/shorts/` allow-listed in `.gitignore` the same way `storage/planner/` was, before any code writes there? | `CTO GATE` (mechanical, but must be an explicit step in Phase 1) |

### CTO Resolution for Phase 1

Approved constraints for the next implementation Sprint:

1. Script creation is deterministic and rule-based from the existing `content_result`; no new LLM call.
2. No TTS, transcription, music, stock-asset, rendering, or publishing provider is selected or integrated.
3. No internal video renderer, AI Planner extension, or `WorkflowEngine` wiring is allowed.
4. One Shorts plan is derived from one existing Content result; no Shorts-specific Topic selection path.
5. `storage/shorts/` runtime outputs must remain gitignored, with only `.gitkeep` tracked if needed.
6. Phase 1 may implement the nine contracts as a standalone/on-demand module with focused tests,
   but it may not claim that a real video was rendered or published.

Questions 1, 3, 4, 5, and 7 are resolved by these constraints for Phase 1. Questions 2 and 6 remain
closed external-dependency gates and must not block the offline implementation.

---

## Summary for Reviewers

This draft defines 9 output contracts, a proposed (not created) `modules/shorts/` file map, a
full offline/fallback behavior table, a manual operator checklist, an external-dependency gate
table with no API key required in Phase 0, explicit copyright/likeness/privacy/platform-policy
constraints, a risk-based future test plan, and a 5-phase roadmap with entry/exit/rollback
criteria. No pipeline code, no `WorkflowEngine` change, and no CardNews duplication were
introduced. All vendor/tool selections remain open `CTO GATE` items.
