# Four-Slide Adaptation

## Immutable contract

- Output remains exactly four 1080×1080 PNG slides.
- Canonical order remains `hook → problem → solution → cta`.
- Existing ten layouts remain the entire layout inventory.
- Any progress indicator is rewritten as 1/4, 2/4, 3/4, 4/4.
- One slide carries one primary claim or task.
- Solution contains at most three complete steps.
- CTA contains one primary action.

## Shared slot budget

| Slot | Hook | Problem | Solution | CTA |
|---|---|---|---|---|
| index/role badge | 1/4 + HOOK | 2/4 + PROBLEM | 3/4 + SOLUTION | 4/4 + CTA/SAVE |
| title | one large promise/question | one concrete friction | one actionable method | one action-oriented takeaway |
| short context | optional one line | one short situation | optional scope line | optional verified reward context |
| primary content | one result/change without unsupported claim | one problem statement | max three complete steps | one CTA sentence |
| proof-or-example | optional, verified only | optional single example | optional one evidence/example block | not a new claim |
| caution/tip | optional | optional | optional one line | delivery condition only if verified |
| CTA | none | none | next-slide cue only if truthful | one primary action |
| attribution/footer | when evidence is used | when evidence is used | preferred evidence location | separate row; never overlap CTA |

## Source A adaptation

### Safe recipe

1. **Hook** — Use the strongest independent paper/notebook skin, a large sans or licensed handwritten accent title, and one short lead. Do not promise a number that later slides cannot fulfill.
2. **Problem** — Keep the same hierarchy while changing at most one surface token. State one missed point and one example.
3. **Solution** — Present two or three complete actions with number anchors. Keep body in sans and place highlight below glyphs.
4. **CTA** — Resolve the sequence. Use `save` by default. A comment keyword is allowed only if a real deliverable, rights, operator, manual fulfillment channel and delivery copy are verified.

### Preserve

- number anchors;
- stable title/lead/content hierarchy;
- controlled surface variation;
- one application context per slide;
- a truthful final resolution.

### Remove

- four or more examples;
- microcopy inside decoration;
- copied reward keyword or prompt;
- repeated tips;
- simultaneous save, comment, follow, share and DM requests;
- original photography, handwriting, doodles and palette composition.

### Existing layout mapping

`notebook` is the primary mapping. Use `checklist` or `number_list` for lists, `tutorial` or `timeline` for steps, and `dark_editorial` for a glass-like skin only when an opaque panel guarantees contrast. `comparison` is allowed only with real A/B data.

## Source B adaptation

### Safe recipe

1. **Hook** — Name the end-to-end flow in one sentence. Do not reproduce the source prompt or claim that one AI step solves everything.
2. **Problem** — Use one “when/result” pair to show where the workflow disconnects.
3. **Solution** — Compress the observed stages into three linked actions: decide the question, connect hook to script, adapt the final content to each channel.
4. **CTA** — Save the three-step workflow. Offer a template keyword only when a verified template exists and manual fulfillment is ready.

### Preserve

- stage dependency;
- step number and function name;
- short context/expected-output pair;
- one primary content box;
- one takeaway.

### Remove

- full prompt text;
- separate slides for every source stage;
- long pale-pink body text;
- more than two boxes per slide;
- platform progress/UI and raw engagement counts;
- claims that reuse means identical copy across channels.

### Existing layout mapping

Use `tutorial` first, then `number_list` or `checklist`. A pastel recap can use existing `character_diary` or `notebook` skin tokens. No new layout is needed.

## Render asset contract

- Any generated or commissioned background is textless, 1080×1080 and independently rights-approved.
- It contains no Hangul, letters, numbers, logo, watermark or platform UI.
- Metadata records `surface_skin_id`, writable region, focal region, prop bounds, crop anchor, palette and contrast hints.
- Layer order: base → panel/mask → props/shadow → approved doodle/icon → Pillow text/highlight → CTA/brand.
- Handwriting requires commercial-use Korean glyph coverage. Missing glyphs fall back to rounded sans.
- AI asset missing/corrupt → approved flat texture; doodle missing → omit it; all fallbacks still produce four slides.

## 1080/270 acceptance

- title 48–60px, body 32–39px, CTA 32–39px, absolute minimum 24px;
- 65px target safe margin;
- body/CTA/attribution contrast at least 4.5:1;
- A: one hero material plus one support note maximum;
- B: two content boxes maximum and decorative pattern ≤5% visual strength behind text;
- title, body, CTA and attribution remain readable at 270×270;
- every text bbox remains inside the writable region;
- text/panel/prop/brand/CTA overlap, glyph clipping and silent truncation are zero;
- ellipsis appears only at a recorded hard limit;
- decoration is removed before type is reduced.

## Reward CTA fail-closed contract

Recommended planning fields:

`primary_action`, `cta_copy`, `reward_type`, `reward_title`, `reward_available`, `fulfillment_mode`, `fulfillment_channel`, `keyword`, `delivery_copy_verified`, `secondary_action`.

If the reward is unavailable, delivery copy unverified, fulfillment owner missing, rights/compliance blocked, or delivery channel unknown, keyword/DM CTA is prohibited. Use `save` or a neutral question. This benchmark does not prove DM automation.
