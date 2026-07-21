# Halfdone AI Video Campaign Pipeline — Planning Handoff

Date: 2026-07-13

## Source Type

CTO-analyzed external workflow references:

- [Halfdone image/video AI reference](https://halfdoneclub.co/community/image-video-ai/6aea8176-eb26-44d1-aa4a-fabc84a8c82e)
- [Halfdone Freepik Spaces and Kling campaign reference](https://halfdoneclub.co/community/image-video-ai/3b568990-d524-4d9f-89eb-d7cc94ebe6df)
- [Kling 3.0 official user guide](https://app.klingai.com/cn/quickstart/klingai-video-3-model-user-guide)
- [Higgsfield Kling 3.0 guide](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation)
- [Freepik Spaces documentation](https://ru.freepik.com/ai/docs/spaces-faq)
- [Freepik AI terms](https://www.freepik.com/legal/terms-of-use)

This document preserves the completed CTO analysis. It does not copy Halfdone prompts, branded
creative sequences, or proprietary teaching flow. The external materials are reference-only; any
future implementation must use independently designed project contracts and original creative work.

Legend:

- `CONFIRMED`: established by the current repository or the cited official source in the CTO analysis.
- `PROPOSED`: an AI-Content-OS contract or workflow recommendation, not implemented.
- `UNKNOWN`: must be verified again against the current plan, region, account, and terms at pilot time.
- `CTO GATE`: explicit approval is required before the action may proceed.

## CTO Summary

The durable value is the production abstraction, not a dependency on Freepik or Kling:

```text
CampaignBrief -> Storyboard -> ShotSpec[] -> AssetManifest -> render candidate -> QA -> manual handoff
```

`PROPOSED`: adopt `CampaignBrief`, `Storyboard`, `ShotSpec`, and `AssetManifest` as future planning
contracts for campaign-oriented CardNews, Shorts, and Commerce creative. Freepik Spaces may be an
optional manual visual-prototyping board, but must never become the system of record. Kling may be
evaluated later as one replaceable Phase-3 video renderer candidate.

This is a research-only backlog item. It does not authorize a provider integration, external API,
account connection, credit purchase, media generation, automated publishing, or `WorkflowEngine`
coupling. Current Shorts Phase 2A remains an offline editing-package path with
`rendered_video_path: null`, and CardNews production remains operational and unchanged.

## What To Adopt

### 1. Provider-neutral campaign planning contracts

- Convert an approved research/content brief into an explicit campaign objective, audience, claims,
  CTA, brand rules, channel, duration, and disclosure requirements.
- Turn the campaign into a human-reviewable storyboard before requesting any media generation.
- Represent each intended cut as a `ShotSpec` with purpose, timing, composition, subject continuity,
  audio/caption intent, asset dependencies, and acceptance criteria.
- Record every selected or generated asset in an `AssetManifest` with provenance, rights, provider,
  model/version when known, generation time, commercial-use status, and approval state.
- Keep logo and final typography as deterministic post-production overlays when possible; do not rely
  on a generative model to reproduce official marks or claim-bearing text.

### 2. Manual prototyping where it reduces ambiguity

`PROPOSED`: a creative operator may use Freepik Spaces to explore composition, character continuity,
backgrounds, or visual variants before a future pilot. The approved brief, selected prompts in
independent project language, selected asset files, provenance, and approval receipts must return to
AI-Content-OS. A vendor board URL or vendor workspace is never the authoritative project record.

### 3. CardNews manual-image support

The same `CampaignBrief -> Storyboard -> ShotSpec -> AssetManifest` structure can help the current
CardNews manual-image path without changing its four-card `hook -> problem -> solution -> cta`
contract. One `ShotSpec` may describe each card's evidence-safe hero image or background variant.
Only assets that pass topic relevance, permitted copyright status, and asset-role checks may be
offered to the existing CardNews intake. This research does not authorize automatic image generation
or replacement of the Pillow renderer.

### 4. Phase-3 video renderer evaluation

`PROPOSED`: Kling is a candidate renderer for a future approved Shorts Phase 3 because the official
guide describes short-form and multi-shot generation, character/element consistency, native audio,
and multilingual dialogue capabilities. These are vendor capabilities to test, not project
guarantees. The actual resolution, duration, audio behavior, credit cost, model availability, and
regional/commercial terms are `UNKNOWN` until captured during a controlled pilot.

## What To Reject

- Copying Halfdone prompts, storyboards, creative sequences, or course structure into the repository.
- Treating Freepik Spaces, Kling, Higgsfield, or another vendor workspace as the system of record.
- Direct vendor calls from the protected `WorkflowEngine` or coupling CardNews completion to an
  external renderer.
- Generating or imitating competitor logos, trademarked campaign identity, recognizable creators,
  viral choreography, or third-party footage without documented rights.
- Using real-person likeness, voice, motion reference, customer media, or unpublished campaign assets
  without purpose-specific permission and privacy review.
- Assuming native audio matches the approved Korean script, speaker, pronunciation, timing, or claim.
- Assuming a free workspace or credit grants commercial-use rights. The applicable subscription,
  output license, attribution, model, region, and client-work terms must be captured at generation time.
- Fabricating product use, testimonials, prices, stock, discounts, performance, revenue, or platform
  metrics in campaign creative.
- Auto-publishing, connecting social accounts, buying credits, or accepting vendor terms without
  explicit owner approval.
- Describing an upscaled export as native 4K when the actual generated resolution is lower.

## AI-Content-OS Engines Affected

| Area | Future use | Boundary |
|---|---|---|
| Research Intelligence | source-backed campaign facts and caution expressions | no unverified claims or fabricated evidence |
| Content | campaign hook, problem, solution, CTA, and approved copy | generated audio/video cannot alter approved claims |
| Brand DNA | tone, color, banned words, distinct original style | competitor brand imitation is rejected |
| Image Strategy / Prompt | provider-neutral visual intent and manual-image brief | no vendor call or protected-mark generation now |
| CardNews | four image briefs mapped to existing card roles | existing layouts, renderer, QA, and `WorkflowEngine` remain unchanged |
| Shorts | storyboard, scene/shot plan, asset package, renderer candidate | standalone; Phase-3 renderer requires a new CTO gate |
| Publishing | caption, disclosure, manual checklist | no live upload or account automation |
| Commerce / Affiliate | product campaign variants after verified facts | price/stock/reviews/use claims and disclosure remain hard gates |

Future owner: **Shorts / Commerce Creative Production Owner**, with CardNews owner review only when
the manual-image intake path is in scope. The CTO/integration lane owns provider approval, contract
approval, shared-document updates, and any future implementation work order.

## Suggested Data Structures

### Contract mapping

| Contract | Purpose | Minimum inputs | Output / next handoff |
|---|---|---|---|
| `CampaignBrief` | approved campaign intent | evidence refs, audience, objective, channel, CTA, claims, disclosures, brand rules | one approved creative direction |
| `Storyboard` | narrative and timing preview | CampaignBrief, scene roles, duration budget | ordered boards with review status |
| `ShotSpec` | executable intent for one cut/card | board ref, subject, action, camera/composition, timing, copy/audio, continuity, acceptance checks | provider-neutral asset request |
| `AssetManifest` | provenance and production truth | generated/selected asset, source/provider, rights, license, captured time, hashes, QA | approved asset refs for editing/rendering |

Proposed minimum shape:

```json
{
  "campaign_brief": {
    "brief_id": "deterministic-id",
    "objective": "awareness | education | conversion",
    "channel": "card_news | shorts | commerce_campaign",
    "audience": "approved audience description",
    "evidence_refs": [],
    "approved_claims": [],
    "blocked_claims": [],
    "cta": "approved CTA",
    "brand_rules": {"tone": [], "banned_words": [], "competitor_marks_blocked": true},
    "disclosure_required": false,
    "approval_status": "draft | approved | rejected"
  },
  "storyboard": {
    "storyboard_id": "deterministic-id",
    "brief_id": "deterministic-id",
    "target_duration_seconds": 15,
    "boards": [{"board_id": 1, "role": "hook", "duration_seconds": 3}],
    "approval_status": "draft | approved | rejected"
  },
  "shot_specs": [{
    "shot_id": "shot-001",
    "board_id": 1,
    "purpose": "hook",
    "duration_seconds": 3,
    "visual_intent": "original provider-neutral description",
    "subject_continuity_ref": null,
    "audio_mode": "none | approved_voice | native_audio_candidate",
    "caption_ref": null,
    "logo_mode": "postproduction_overlay",
    "acceptance_checks": ["brand_safe", "claim_safe", "rights_ready"]
  }],
  "asset_manifest": [{
    "asset_id": "sha256:...",
    "shot_id": "shot-001",
    "source_mode": "owned | licensed | generated | user_supplied_with_permission",
    "provider": "manual | freepik | kling | other",
    "model_version": "unknown",
    "generated_or_captured_at": null,
    "commercial_license_status": "unknown | verified | blocked",
    "likeness_consent_ref": null,
    "trademark_review": "not_checked | passed | blocked",
    "audio_script_match": "not_applicable | unverified | passed | failed",
    "render_allowed": false,
    "approval_receipt_ref": null
  }]
}
```

The future implementation should add deterministic hashes and approval receipts through the
Content Automation Harness rather than creating a second workflow engine. Any vendor adapter should
return files and metadata into this contract and remain replaceable.

## Workflow Impact

No current runtime impact is authorized.

Future approved path:

```text
existing Research/Content/Brand outputs
  -> CampaignBrief
  -> human approval
  -> Storyboard
  -> ShotSpec[]
  -> optional manual Freepik Spaces prototype
  -> AssetManifest intake
  -> optional Kling Phase-3 render candidate
  -> local provenance, claim, likeness, trademark, audio and visual QA
  -> Shorts Phase-2A-compatible editing package / CardNews manual-image intake
  -> manual approval and publishing preparation
```

Fallback rules:

- Missing provider, credits, license evidence, consent, or approved asset: keep the package usable
  as a manual plan and set `render_allowed: false`.
- Kling or another renderer failure: retain the `ShotSpec` and use a manual editor, approved stock/
  owned assets, or the existing text/kinetic-typography route; do not fail the main workflow.
- Native-audio mismatch: discard or mute the generated audio and use separately approved voice/audio.
- Character or product inconsistency: block the affected shot and regenerate only after a cost gate;
  never silently accept continuity drift.
- CardNews asset failure: preserve `manual_image_required` behavior and the existing safe renderer.
- Commerce fact freshness failure: remove or block the volatile claim; never improvise a price,
  discount, stock, review, ranking, or purchase experience.

## Sprint Impact

No active Sprint scope changes.

The smallest future pilot, only after CTO approval:

1. Use one fictional brand or one owner-authorized product with verified facts.
2. Produce one original 10-15 second vertical campaign and an equivalent CardNews/manual-image
   concept where useful.
3. Limit the storyboard to three `ShotSpec` records.
4. Use no real-person likeness, competitor logo, third-party viral video, or unlicensed music.
5. Use Freepik Spaces only for optional manual composition exploration.
6. Generate at most one provider baseline plus one bounded retry after an explicit credit ceiling.
7. Do not connect an account or publish; download the candidate file and ingest it through
   `AssetManifest`.
8. Compare against a provider-free baseline such as approved still assets plus kinetic typography.
9. Record operator time, consumed credits, first-pass approval, continuity, script/audio accuracy,
   rights completeness, and fallback outcome. These are pilot observations, not promised KPIs.

Pilot exit requires a rights-complete manifest, no unsupported claim, human visual/audio review,
known actual resolution, and a clear cost/quality comparison. Any unresolved license, likeness,
trademark, or claim issue is a stop condition.

## Roadmap Impact

Backlog placement:

- **Adopt now as planning vocabulary:** `CampaignBrief`, `Storyboard`, `ShotSpec`, `AssetManifest`.
- **Roadmap:** optional manual Freepik Spaces prototyping and provider-neutral asset intake.
- **Roadmap / Phase 3 candidate:** controlled Kling renderer pilot behind a provider adapter.
- **Reject now:** core integration, account connection, automatic credit use, live publishing,
  provider workspace as source of truth, and Commerce claims without live verified facts.

Required approval gates before a future pilot or implementation:

1. CTO approves the pilot scope, provider, cost ceiling, and owned files.
2. Project owner approves account/terms/credit use; no credential enters source control.
3. Current commercial license, client-work rights, output ownership, attribution, retention, and
   training/data-use terms are saved with the pilot record.
4. Every likeness, voice, performance, reference video, product image, logo, font, and music input
   has documented rights and purpose-specific consent.
5. Commerce owner confirms product-source freshness, affiliate/sponsorship disclosure, and blocks
   unsupported experience/performance claims.
6. Shorts owner approves renderer QA and fallback; CardNews owner approves any manual-image intake.
7. Human approval is required before any asset becomes render-ready or publish-ready.
8. A separate explicit gate is required for API integration, social-account connection, or live
   publishing; this research grants none of them.

## ROI

| Dimension | Assessment | Reason |
|---|---:|---|
| Reusable planning contract | High | applies across CardNews, Shorts, and later Commerce campaigns |
| Current CardNews core ROI | Medium | improves manual-image briefs but does not replace current renderer |
| Future advertising Shorts value | High | multi-shot campaign production can become a premium output |
| Immediate implementation priority | Low | offline Shorts packaging and current CardNews operations take precedence |
| Vendor and credit risk | High | regeneration cost, plan changes, model variability, and lock-in require controls |
| Rights/compliance risk | High | likeness, trademark, audio, product claims, and commercial licenses all require evidence |
| Reversibility | High when manual | provider-neutral contracts and file-based handoff preserve fallback options |

The best near-term return is standardizing creative handoff objects. Renderer automation should be
funded only after a small manual pilot demonstrates acceptable quality, rights completeness, and
cost per approved asset.

## Implementation Status

**Research-only / backlog. Not implemented.**

- No code, tests, storage output, API integration, account connection, credit purchase, media
  generation, or publishing action is authorized by this document.
- No `WorkflowEngine` change or coupling is proposed.
- Freepik Spaces is not selected as infrastructure.
- Kling is a Phase-3 renderer candidate, not an approved dependency.
- Any future implementation requires a new work order with exclusive file ownership and the gates
  listed above.

## Codex Notes

- The Halfdone sources are preserved as research references only; their prompts and proprietary
  educational flow were not copied.
- Official vendor documentation and terms can change. Re-verify the exact product, model, plan,
  pricing/credits, region, commercial license, data handling, and output resolution at pilot time.
- The official capabilities cited above do not prove acceptable Korean dialogue accuracy, character
  consistency, product fidelity, or production economics. Those remain controlled-pilot questions.
- `Freepik Spaces -> Kling` is one possible operator sequence, not the project architecture. The
  project architecture is provider-neutral contracts plus local evidence and approval records.
- Future owner: Shorts / Commerce Creative Production Owner. CTO/integration retains approval and
  shared-document/Git ownership.
