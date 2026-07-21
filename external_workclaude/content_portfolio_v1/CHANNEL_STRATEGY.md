# Channel Strategy

Per-channel notes on how the six executable content types in this portfolio (CardNews,
Shorts/Reels, Instagram feed, BrandConnect, Commerce guides, Knowledge/Evergreen) should be
sequenced and cross-reused. This is strategy, not implementation -- nothing here wires content
types together in code.

## CardNews -- the hub format

CardNews is the highest-reuse, lowest-friction format because the renderer, layout, and QA
pipeline are already `implemented` (`modules/card_news/`). Strategy: use CardNews as the
canonical first draft of almost every topic in this portfolio -- a Knowledge/Evergreen concept,
a Commerce comparison-criteria guide, and an Instagram informational post can all reuse the
same underlying research and hook/problem/solution/cta shape before being reformatted for
their target channel. `reusable_pattern_tags` in the backlog mark which briefs are designed
for this kind of cross-format reuse.

## Shorts/Reels -- the reach amplifier, currently the most gated

Shorts briefs in this portfolio are scripts and scene plans only. Strategy: treat Shorts as a
second-pass reformat of an already-proven CardNews/Instagram-feed topic (the checklist and
lifestyle topics overlap deliberately), not a source of original topics. This reduces research
cost per Short and lets the team validate a topic's appeal in CardNews form before committing
to real filming. Render/publish automation remains `blocked_by_api` until a Sprint is
authorized (see `.codex/skills/ai-content-os-shorts/SKILL.md`).

## Instagram feed / informational -- the trust and reach layer

Strategy: alternate between pure informational content (builds trust, no monetization) and
CardNews-linked content (drives saves/shares back to the CardNews carousel). Trend-explainer
content (`트렌드 해설`) belongs here specifically because it has the shortest freshness window
(1-2 weeks) and must always trace to a real, currently-collected trend item -- never a
pre-written claim.

## BrandConnect -- entirely gated on a real deal

Strategy: keep the package structure (four deliverable-agnostic slide roles + disclosure +
approval chain) ready so that once a real brand signs, the team can move from contract to
draft in days rather than weeks. Do not originate BrandConnect topics from imagination; every
BrandConnect brief in this backlog is deliberately generic (a deliverable-type description, not
a brand-specific pitch) until a real brand exists.

## Commerce guides / comparisons -- criteria first, product later

Strategy: publish criteria-only comparison guides now (no specific product, no price, no
affiliate link) to build category authority and reusable comparison templates. This is safe to
do immediately (`planning_only`, zero real-data risk) and creates the exact scaffolding needed
the moment a real product source is approved -- at that point the same guide becomes a
`blocked_by_data` item pending sourcing, not a from-scratch rewrite.

## Knowledge/Evergreen -- the credibility layer

Strategy: these are the lowest-risk, highest-reuse-value items precisely because they carry no
monetization pressure and no volatile facts (except the regulation-adjacent subset, which is
explicitly flagged `blocked_by_data`). Use this category to build long-term account authority
that later legitimizes Commerce and BrandConnect content.

## Cross-channel sequencing (recommended, not implemented)

1. Knowledge/Evergreen or CardNews lifestyle topic validates audience interest (lowest cost).
2. A proven topic is reformatted into Instagram feed and/or a Short (reach amplification).
3. A proven, reusable comparison-criteria topic graduates into a Commerce guide once real
   product sourcing is approved.
4. Only after account trust and a real brand relationship exist does BrandConnect activate.

This sequencing exists to keep monetization-adjacent content (Commerce, BrandConnect,
Affiliate) downstream of trust-building content, not a starting point -- consistent with
`MONETIZATION_BOUNDARIES.md`.
