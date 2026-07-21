# Halfdone AI Avatar and Video Tools Research Handoff

## Source Type

- External workflow reference: Halfdone Club, Higgsfield AI Influencer/Motion Control
  - <https://halfdoneclub.co/community/image-video-ai/72dac4af-e7c1-4a0a-a470-f46e3ba62f0b>
- External workflow reference: Halfdone Club, DomoAI Talking Avatar/Video-to-Video
  - <https://halfdoneclub.co/community/image-video-ai/739fd40b-0f43-494f-99cd-9ad23a002d5c>
- Official provider evidence used by the CTO review:
  - [Higgsfield AI Influencer](https://higgsfield.ai/ai-influencer)
  - [Higgsfield Terms of Use](https://higgsfield.ai/terms-of-use-agreement)
  - [Higgsfield Trust](https://higgsfield.ai/trust)
  - [Higgsfield Earn](https://higgsfield.ai/blog/Higgsfield-Earn-Talent-And-Collaboration-Monetization)
  - [DomoAI Talking Avatar API](https://docs.domoai.app/api-reference/ai-video/talking-avatar)
  - [DomoAI Video-to-Video Guide](https://help.domoai.app/en/articles/12958715-video-to-video)
  - [DomoAI API Pricing](https://docs.domoai.app/pricing)
  - [DomoAI Terms of Service](https://domoai.app/terms-of-service)
  - [DomoAI Privacy Policy](https://domoai.app/privacy-policy)
  - [DomoAI Enterprise API Privacy Policy](https://docs.domoai.app/guides/privacy/privacy-policy)

This document preserves the completed CTO analysis. It does not reproduce the Halfdone prompts or course
flow, and it does not independently authorize use of either provider.

## CTO Summary

AI influencer and talking-avatar tools can become useful optional asset providers for future Shorts/Reels.
They are not needed by the current CardNews-first protected pipeline and must not be connected to
`WorkflowEngine`.

Higgsfield is the stronger manual creative candidate for character generation, identity continuity, and
reference-motion transfer. Its official product description supports generating a character, keeping the
identity consistent, and applying movement from a reference video through Motion Control
([Higgsfield AI Influencer](https://higgsfield.ai/ai-influencer)). It is appropriate only for an approved,
rights-cleared manual experiment.

DomoAI is the stronger future integration candidate because its official Talking Avatar API accepts image,
audio, and prompt inputs ([DomoAI Talking Avatar API](https://docs.domoai.app/api-reference/ai-video/talking-avatar)).
Its API availability does not constitute project approval. Current pricing and contractual conditions must
be captured again at pilot time because provider prices and policies can change
([DomoAI API Pricing](https://docs.domoai.app/pricing)).

Higgsfield Earn is a campaign and rewards workflow, not guaranteed Instagram or YouTube monetization.
Account verification, campaign eligibility, posting requirements, performance tracking, and payout review
remain external conditions ([Higgsfield Earn](https://higgsfield.ai/blog/Higgsfield-Earn-Talent-And-Collaboration-Monetization)).
No revenue, reach, retention, engagement, or approval outcome may be inferred from connecting an account.

### Provider Comparison

| Area | Higgsfield | DomoAI | CTO verdict |
|---|---|---|---|
| Best-fit role | Character creation and reference-motion experiment | Talking-avatar and optional style-transfer provider candidate | Keep both optional and replaceable |
| Current use mode | Manual UI pilot only | Manual pilot first; API evaluation later | No current integration |
| Integration evidence | No approved project API contract | Public Talking Avatar API documentation exists | DomoAI has the clearer future adapter path |
| Primary risk | Likeness/motion-reference rights and broad content/data terms | Face/voice rights, data handling, commercial/service-bureau terms | Rights and contract review precede upload |
| Failure fallback | Do not generate; use a non-avatar manual asset | Do not call provider; use a non-avatar manual asset | Shorts package remains usable without either provider |

## What To Adopt

- Treat a persistent virtual presenter as an optional Shorts asset, never as a required pipeline stage.
- Reuse the existing Shorts script, scene, caption, brand, asset-provenance, and manual publishing contracts.
- Keep character brief, input rights, consent evidence, provider/model, generation time, commercial-use status,
  disclosure requirement, and fallback reason with each returned asset.
- Separate provider generation from local caption, branding, rendering, QA, and publish preparation.
- Require a human to review identity drift, face/hand artifacts, Korean lip sync, pronunciation, approved-script
  fidelity, safe areas, disclosure, and unsupported claims.
- Preserve a provider-neutral adapter boundary so Higgsfield, DomoAI, or a later provider can be removed without
  changing Shorts planning contracts.
- Use only fictional characters or people whose documented release expressly covers the intended AI derivative,
  motion transfer, voice use, commercial use, platforms, territory, and duration.

## What To Reject

- Direct provider calls from `WorkflowEngine` or any CardNews protected-core module.
- A required dependency on Higgsfield, DomoAI, Higgsfield Earn, or a provider-specific output schema.
- Real-person face swaps, impersonation, undisclosed synthetic presenters, or fabricated testimonials.
- Third-party viral videos, influencer footage, choreography, voices, or likenesses used as references without
  documented rights.
- Customer, employee, minor, confidential campaign, or sensitive biometric material uploaded under a generic
  consent assumption.
- Automatic account linking, campaign enrollment, credit purchase, upload, publishing, or monetization claims.
- Copying Halfdone prompts, course structure, or protected instructional material into the repository.
- Encoding a single gender, ethnicity, skin tone, or beauty standard as the default presenter persona.
- Treating provider output, similarity scores, moderation, or commercial-use statements as legal clearance.

## AI-Content-OS Engines Affected

- **Shorts standalone pipeline — future owner:** `Shorts Provider Owner` (future role), under CTO integration
  approval. This is the only intended consumer.
- **Research/Content/Brand DNA — read-only inputs:** approved claims, script, tone, banned words, and CTA are
  inherited; no provider may rewrite factual claims or invent performance evidence.
- **Shorts Asset/QA/Publish Preparation — future boundary:** validates provenance and marks all provider failures
  as manual-action events. Publishing remains manual unless separately approved.
- **WorkflowEngine and CardNews — unaffected:** no imports, calls, stage additions, schema changes, or provider
  dependencies are authorized.

Exact safe boundary:

```text
Existing ShortsEditingPackage
  -> approved fictional-character or consented-talent brief
  -> optional ExternalVideoAssetProvider (standalone, future)
  -> downloaded provider asset + provenance/rights record
  -> local validation, captions, branding, render QA
  -> manual publish preparation

Provider unavailable / rights unresolved / quality failed
  -> non-avatar image, kinetic-typography, or manual-editor asset
  -> same local QA and manual publish preparation
```

The proposed `ExternalVideoAssetProvider` is an architecture boundary only. No interface, module, credential,
storage output, or network call is authorized by this research document.

## Suggested Data Structures

Planning proposal only:

```json
{
  "provider_asset": {
    "provider": "not_selected",
    "provider_mode": "manual_or_future_api",
    "model": null,
    "generated_at": null,
    "source_scene_ids": [],
    "input_rights": {
      "character_image": "unverified",
      "motion_reference": "unverified",
      "voice_or_audio": "unverified"
    },
    "consent_record_ref": null,
    "commercial_use_status": "unverified",
    "service_bureau_status": "unverified",
    "data_handling_review": "not_completed",
    "ai_disclosure_required": true,
    "render_allowed": false,
    "fallback_used": true,
    "reason": "Provider and rights gates have not been approved"
  }
}
```

`render_allowed` must remain `false` until all relevant rights, consent, privacy, contract, asset-quality, and
disclosure gates pass. A provider's successful generation response is not sufficient.

## Workflow Impact

There is no current workflow impact. A future approved implementation must remain standalone and consume a copy
of the Shorts editing package; it must not be inserted into `src/workflow_engine.py`.

Provider calls must be optional and failure-tolerant. Timeout, credit exhaustion, moderation rejection, account
failure, provider outage, policy change, quality rejection, or unresolved rights must yield a structured reason
and a manual fallback. None may convert the protected CardNews workflow from `workflow_completed` to a failure.

Higgsfield states that users are responsible for having necessary rights in uploaded content and likenesses
([Higgsfield Trust](https://higgsfield.ai/trust)). Its terms also require careful review of permissions and the
license granted over user content, including possible service improvement and promotional uses
([Higgsfield Terms of Use](https://higgsfield.ai/terms-of-use-agreement)). Therefore no private or client media
may be used in a pilot.

DomoAI input and output use must be reviewed against its current general terms, privacy policy, and any applicable
Enterprise agreement before a commercial production or customer-facing service
([Terms](https://domoai.app/terms-of-service), [Privacy](https://domoai.app/privacy-policy),
[Enterprise API Privacy](https://docs.domoai.app/guides/privacy/privacy-policy)). In particular, a general
commercial-use statement does not resolve whether agency, managed-service, outsourcing, resale, or service-bureau
use is permitted for the project's intended business model.

## Sprint Impact

No current Sprint should be opened from this document. It is a backlog reference for a later Shorts provider
evaluation after the existing offline Shorts contracts and manual editing package have been operationally
validated.

### Smallest Future Pilot

Only after explicit CTO approval:

1. Use one clearly disclosed fictional virtual host that does not intentionally resemble a real person.
2. Use one 10-15 second vertical script from the existing Shorts contract.
3. Use owner-created, synthetic, or separately documented motion reference material; do not use third-party viral
   footage.
4. Use only approved audio: owner recording, licensed talent, or a separately approved TTS source.
5. Generate manually with one provider; do not link a social account, enroll in Earn, publish, or purchase credits
   without the separate approvals below.
6. Return the file through the existing Phase 2A asset/provenance validation boundary.
7. Compare it with a provider-free kinetic-typography or talking-card baseline using observed production time,
   actual captured cost, first-pass QA outcome, rights completeness, and reviewer decision. Do not invent targets
   or results before the pilot.

## Roadmap Impact

Backlog only:

1. Validate the current standalone Shorts planning and editing-package contracts.
2. Approve a rights-safe manual pilot and collect real cost/quality evidence.
3. Review provider terms, privacy, data retention/deletion, commercial use, service-bureau use, and vendor exit.
4. Decide whether an `ExternalVideoAssetProvider` contract has sufficient ROI.
5. Only then consider a provider adapter in a separately approved Sprint.

No future step implies `WorkflowEngine`, AI Planner, CardNews, account, or publishing integration.

## ROI

Potential ROI is strongest for recurring virtual-presenter Shorts, product explainers, short CTA inserts, and
managed video packages. It is weak for the current CardNews-first priority and uncertain until the project records
real approval rate, generation/retry cost, operator time, rights-review burden, and fallback frequency.

The provider-neutral boundary protects ROI by keeping the existing Shorts package usable when a vendor changes
price, policy, model behavior, availability, or output quality. No quantitative ROI claim is established by this
research.

## Implementation Status

**Research-only / backlog.**

- Manual pilot: not approved.
- Provider selection: not approved.
- API or UI automation: not approved.
- Account linking or credit purchase: not approved.
- Media generation or upload: not performed.
- Publishing or monetization: not approved.
- `ExternalVideoAssetProvider`: architecture proposal only; not implemented.
- `WorkflowEngine` integration: prohibited.

Future owner: **Shorts Provider Owner**, assigned by the CTO integration lane when a provider-evaluation Sprint is
explicitly approved. Until that assignment, the CTO integration lane owns scope and approval decisions.

## Codex Notes

Approval gates for any future work:

1. **CTO scope gate:** provider evaluation Sprint, owned files, fallback contract, and standalone boundary.
2. **Rights and consent gate:** traceable releases for likeness, voice, performance, motion reference, source
   media, and AI derivatives.
3. **Privacy/data gate:** approved data category, retention/deletion terms, training/improvement use, promotional
   use, subprocessor/vendor chain, incident response, and prohibition on sensitive/private inputs.
4. **Commercial-use gate:** current terms captured at approval time, including output ownership/license,
   attribution, campaign use, resale, agency/managed-service, outsourcing, and service-bureau permission.
5. **Cost gate:** current pricing/credits, retry policy, expected operator effort, budget cap, and no silent purchase.
6. **Quality/disclosure gate:** Korean audio and lip-sync review, identity stability, artifact review, factual-script
   match, AI disclosure, and no deceptive endorsement or testimonial.
7. **Account/publishing gate:** account owner approval, credential handling, platform policy review, manual-first
   publishing, and no guaranteed monetization or fabricated performance.
8. **Security/engineering gate:** official API documentation, credential storage, rate limits, timeout/retry,
   diagnostics, replaceability, and provider-free fallback.

Unresolved evidence that must be rechecked at pilot time:

- Current provider pricing, credits, rate limits, model availability, output limits, and API support.
- Applicable contract version and whether the intended customer-facing or managed-service model is permitted.
- Data retention, deletion, training, promotional-use, and subprocessor terms for the selected plan.
- Current platform disclosure, synthetic-media, endorsement, advertising, and monetization policies.

The Halfdone pages are reference material only. Their prompts and instructional sequence are not repository assets.
