# Agency Agents-derived CardNews education

This education layer adapts selected prompt patterns from
`https://github.com/msitarzewski/agency-agents` at commit
`459dce837db3bdfdc4763d3fefd1fd854e73c8f1` (MIT). The owner contract,
`AGENTS.md`, and `docs/CARDNEWS_MULTI_ACCOUNT_DIRECTIVE.md` always take
precedence. These are working heuristics, not fixed owner rules.

## Shared production behavior

- Start from the selected candidate, its supplied sources, and the account angle. Do not start from a product or a predetermined slide template.
- Write one clear visual purpose per slide/scene. Use a short hook, evidence or context, progression, and a natural close only where the topic supports them.
- Keep subject, environment, light, camera, style, crop, safe zone, and negative constraints separate in image prompts.
- Check mobile legibility, visual rhythm, account consistency, and emotional progression. A fixed slide count is forbidden.
- Generated visuals are labeled as generated/re-enactment material and never replace factual evidence.
- Product connection is optional. Runway, brand-show, public-interest news, and pure entertainment may remain information-only.
- Never claim automatic publishing, real performance, personal use, price, stock, delivery, or product function without supplied evidence.

## Account A — news

- Hook: the consequence or the newly public fact, written from the article body rather than headline-only inference.
- Flow: source context, the minimum facts needed to follow the event, what changed, and a neutral close or question when useful.
- Media: original article assets, official material, broadcast/YouTube discovery, documents or explanatory graphics according to the topic. Maps, numbers and timelines are optional, not a house style.
- Motion: crop, highlight, sequence and typography may improve comprehension; generated fake field footage is prohibited.

## Account B — story/relationship/dopamine + entertainment

- Hook: the decision, conflict, or emotionally legible line that makes the reader want the next beat.
- Flow: setup, tension, reaction/choice, consequence, then actual public comments or a question when available. Preserve an observable emotion change between scenes.
- Media: supplied original captures, actual comments, and clearly labeled illustration/re-enactment scenes. Do not fabricate comments or impersonate a real person.
- Tone: a dark topic does not require uniformly dark art. Use contrast and facial/body emotion to carry the arc.

## Account C — fashion

- Hook: the season concept, silhouette, styling shift, celebrity styling angle, or practical situation. Brand/runway information does not need a product CTA.
- Flow: show first, explain briefly, compare only useful differences, then provide one styling takeaway. Keep on-image copy short and put supporting context in the feed caption.
- Media: official show, lookbook, campaign, product and permitted editorial assets first. AI models must be synthetic, consistently identified, and never imply an unrelated celebrity endorsement.
- Commerce: connect a product only when the candidate naturally creates a real-life use case; explain the bridge in plain Korean.

## Account C — beauty

- Hook: a visible beauty concern, sensory cue, current look, product launch, ingredient/scent note, or weather-linked routine.
- Flow: show the concern or desired result, identify the relevant product type, explain use/texture/note from supplied evidence, and close with a choice or routine.
- Media: official product photos, texture/use shots, supplied ingredient or scent notes, and official video. Motion should make spray, liquid, texture, light, or multiple product images easier to understand, not merely simulate movement.
- Commerce: natural matching is encouraged but never forced; distinguish supplied product facts from editorial wording.

## Performance learning

- Treat external examples as references only. Promote a pattern only after owner feedback or real account metrics support it.
- Store why a candidate, hook, media role, and product bridge were chosen so later results can be compared.
- Never invent benchmark numbers or treat a provider prompt's claimed target as our measured result.
