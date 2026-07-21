# CardNews Design Pattern Matrix — 2026-07-15

## Decision boundary

This matrix records two competitor posts and eleven observed slides as design-learning references only. Every source asset is `competitor_reference`, `analysis_only`, and `render_allowed=false`. “Observed” means visible inside the accepted carousel crop; “hypothesis” means a proposed adaptation that has no demonstrated performance effect.

The production contract remains exactly four slides (`hook → problem → solution → cta`) and the existing ten layouts. The patterns below are skin tokens and slot recipes, not new layouts.

## Pattern matrix

| Source | benchmark_observed | Safe abstraction | Existing layout mapping | 4-slide use | Mobile/rights guard | Evidence tier |
|---|---|---|---|---|---|---|
| A — changing physical surfaces | Receipt, glass marker, open book, ruled notebook and paper collage change by slide while numbering, large handwritten title, yellow highlight and doodle grammar repeat. | Fixed information hierarchy with one hero surface and at most one support note; surface variation may change while slot positions stay stable. | `notebook` first; `checklist`/`number_list` for lists; `tutorial`/`timeline` for steps; `dark_editorial` only with an opaque text panel; `comparison` only for real comparison data. | Use 1/4–4/4 progress, one claim per slide, max three steps on solution, one CTA. | Original pixels, material photos, handwriting, doodles and exact palette/composition are prohibited. Use independently licensed/generated textless plates and separate text layers. | observed structure; adaptation is hypothesis_only |
| A — handwritten hierarchy | Heavy handwritten number/title, short lead, central example/check block and small support memo recur. Highlight sits behind text. | Handwritten accent for title/short emphasis only; body stays sans. Highlight becomes an independent underlay. | Skin token over existing layout; no renderer role change. | Hook may use the strongest handwritten accent; problem/solution retain readable sans body; CTA gets one high-contrast action. | Commercial Korean glyph coverage required; fallback to rounded sans. Never bake Korean text into generated background. | benchmark_observed / hypothesis_only |
| A — reward CTA | Final slide uses a large keyword and promises a deliverable. Delivery channel is not visible. | Reward CTA schema may include availability, verified delivery mode and keyword; otherwise fail closed to save or a neutral question. | Existing CTA slide only. | One primary action. Reward comment is allowed only when the deliverable, rights and manual fulfillment are verified. | `fulfillment_channel=unknown` and `dm_automation_observed=false` for this benchmark. No comment/DM/save/share/follow stack. | benchmark_observed; conversion effect prohibited |
| B — repeatable staged template | Pastel/star skin, step medallion, stage title, “when/result” summary, long body/prompt box and takeaway box repeat across topic → hook → script → thumbnail → reuse → combined prompt. | Reusable fixed slots with content replacement; one stage equals one output. | `tutorial` first; `number_list`/`checklist` support; pastel `character_diary` or `notebook` skin for recap. | Hook frames the flow, problem identifies a broken connection, solution compresses to max three linked steps, CTA saves the process or offers a verified template. | Max two content boxes on a 1:1 slide. Remove decorative stars behind text and shorten prompt prose rather than shrinking type. | observed structure; adaptation is hypothesis_only |
| B — cumulative sequence | Each stage advances to the next and the final observed slide previews a combined reward. | Progress metadata and truthful next-slide cue; final takeaway recaps the earlier stages. | Existing role badge/progress/footer slots only. | Rewrite source progress to 1/4–4/4. A cue is allowed only when the next slide actually resolves it. | Platform progress UI is contamination, not a reusable asset. No 5–11 slide output. | benchmark_observed / hypothesis_only |
| B — pastel information hierarchy | Bold sans title and summaries outrank smaller pink body text; boxed hierarchy is stable. | Charcoal primary text, one accent, step badge, context box, primary body box, takeaway box, small decorative accent. | `tutorial`, `number_list`, `character_diary` palette tokens. | Keep short context, one primary content block and one optional caution/tip. | Body/CTA/attribution contrast ≥4.5:1; minimum type 24px; long pale-pink copy is not accepted. | benchmark_observed / hypothesis_only |

## Common slot recipe

The only reusable common slots are:

1. index/role badge
2. title
3. short context
4. primary content
5. proof-or-example
6. caution/tip
7. CTA
8. attribution/footer

Not every slide uses every optional slot. At 1080 and 270px, body, CTA and attribution take priority. Decoration, icons, doodles, texture and support notes are removed first when space is constrained.

## Pattern rejection rules

- No eleventh layout, no five-to-eleven-slide renderer path, and no change to canonical roles.
- No direct or near-copy of source text, prompt bodies, keyword CTA, icons, doodles, handwriting, material photography, watermark, account identity or UI.
- No “high-performing”, “validated”, “proven”, “conversion lift” or similar label based on public UI counts.
- No AI-generated background containing letters, numbers, pseudo-Hangul, logos, UI or watermarks.
- No reward CTA when the promised asset, fulfillment owner, delivery copy, rights or compliance is unverified.

## Recommended learning priority

1. B-style repeatable slots are the first automation candidate because their structure is stable and can be expressed with existing primitives.
2. A-style surface variation is limited to one or two independently created skin variants per four-card set; use a flat light-paper fallback.
3. Full analog-scene fidelity and long prompt reproduction remain out of scope without a separate visual QA and rights-approved asset package.
