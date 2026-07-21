# CardNews Design Learning QA Report

## Final verdict

**CONDITIONAL GO — analysis intake only.**

The RC is acceptable as a design-learning reference because it preserves post binding, crop/contamination boundaries, rights restrictions, evidence-tier honesty, the four-slide contract and the existing ten-layout limit. It is **NO-GO** as a production render asset package, factual evidence package, rights package, social-proof package or measured-performance dataset.

## Acceptance summary

| Gate | Result | Evidence |
|---|---|---|
| Inventory and same-post binding | PASS | 2 posts, 11 observed slides, 11 unique SHA-256 files; A=6/10–10/10, B=4/11–9/11. B 4/11 is the supplied 0668 file and not a third post. |
| Crop and contamination boundary | PASS | A observed bbox `(0,169,652,816)`; B `(0,263,652,816)` in 652×1280 coordinates. Detection is required; in-frame page counter/mute overlay is excluded. |
| Performance honesty | PASS | Public UI values are retained only as raw, unlabeled snapshots with no causal or ranking use. |
| Rights/render boundary | PASS | Every source is competitor-reference, third-party unlicensed, analysis-only and render-blocked. |
| Existing product contract | PASS | Exactly four roles and existing ten layouts; only style tokens/slot recipes are proposed. |
| Vertical-fit labeling | PASS | All fit judgments are hypothesis-only; news/medical/financial/legal authority, density and attribution risks are stated. |
| Implementable slot separation | PASS | Common slots are index/role, title, short context, primary content, proof/example, caution/tip, CTA and attribution/footer. Decoration is removed first. |

## Source integrity

- Source A contains five scoped files and one observed post sequence.
- Source B contains five files in the 270 folder plus exactly one preceding file from the 0668 path, all bound to one post sequence.
- Other files under the 0668 directory are explicitly out of scope.
- SHA-256 dedup found no identical files in the scoped eleven-file set.
- File uniqueness is not treated as post independence.

## Crop QA

Coordinates use original 652×1280 pixels, top-left origin, exclusive end.

| Source | Observed bbox | Range | Detection |
|---|---|---|---|
| A, all five files | `{x:0,y:169,width:652,height:816}` | `x=[0,652), y=[169,985)` | required |
| B, 270 folder | `{x:0,y:263,width:652,height:816}` | `x=[0,652), y=[263,1079)` | required |
| B, preceding 4/11 file | `{x:0,y:263,width:652,height:816}` | `x=[0,652), y=[263,1079)` | required |

Reasons for re-detection:

- A and B differ by 94px in y start;
- top ad/caption/audio UI can shift future screenshots;
- dark A photography defeats brightness-only detection;
- page counters and mute icons can remain inside the frame.

The detector must validate continuous frame boundaries and the 652:816 aspect. Failure produces `manual_crop_required`; it must never fall back to learning from the raw screenshot.

## Contamination exclusions

- top government-funding ad on A;
- top sauce.solution ad/recommendation on B;
- Instagram account/profile/verification chrome;
- audio metadata;
- likes/comments/shares/saves or other reaction UI;
- bottom navigation/action controls;
- in-frame page counter and mute icon;
- logos, watermarks and platform UI.

## Rights and similarity QA

Allowed: progression, hierarchy, functional slots, one-stage/one-output sequence, decoration-removal order, and independently re-created spacing logic.

Prohibited: screenshots, original photos, prompt/caption/copy, handle, logo, watermark, music, handwritten marks, doodles, icons, exact palette, exact box composition, near-copy or source-pixel reuse. Attribution does not create a reuse license.

Any later production design needs new, independently rights-approved assets plus similarity review.

## Performance and evidence QA

- No observed count is labeled likes, comments, saves, reach, CTR or conversion because the screenshot meaning and measurement context are incomplete.
- No design is labeled high-performing, proven or validated.
- A keyword reward may have influenced visible interactions, but neither channel nor automation is observed.
- Source A/B provide no factual evidence for content claims and no social-proof text.
- Real performance learning remains held until authorized post-level metrics exist.

## 1080/270 production acceptance for any future adapter

- exact four decodable 1080×1080 PNG;
- canonical role/order and 1/4–4/4 progress;
- body/CTA/attribution contrast ≥4.5:1 and absolute type minimum 24px;
- title/body/CTA/attribution readable at 270×270;
- no bbox overflow, overlap, glyph clipping or silent loss;
- no AI-baked pseudo-Hangul, letters, numbers, logo, watermark or UI;
- decoration removed before type reduction;
- reward CTA fail-closed when deliverable/fulfillment/rights/compliance is incomplete.

## Verification performed

- Six existing role lanes provided read-only, non-overlapping reviews.
- Independent QA supplied exact post binding and crop coordinates.
- Catalog inventory records all eleven scoped files, their SHA-256 values, sizes and dimensions.
- `SOURCE_CATALOG.json` is the machine-readable single source for sample binding, crop and rights metadata.

No module, test, storage, shared document, WorkflowEngine, Git state, API or publishing state was changed. No workflow or production registration was run because this RC is documentation-only and those actions were explicitly prohibited.

## Residual holds

- No production skin or slot registration.
- No eleventh layout or multi-slide expansion.
- No external automation, DM, comment bot, API or performance loop.
- No raw-source render use.
- No performance promotion until authorized metrics and a separate validation design exist.
