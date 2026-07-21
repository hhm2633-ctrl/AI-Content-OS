# Content Inventory -- What AI-Content-OS Can and Cannot Produce Today

Grounded in the actual module list under `modules/` (read-only inspection: `card_news/`,
`shorts/`, `instagram_research/`, `competitor_learning/`, `brandconnect/`, `commerce/`,
`affiliate/`, `knowledge_engine/`, `content/`, `publishing/`) and the current
`docs/ACTIVE_PARALLEL_WORK_ORDERS.md` / `MODULE_STATUS.md` state as of 2026-07-13. Nothing
below claims a capability the repository does not actually have.

Status vocabulary: `implemented`, `offline_ready`, `manual_ready`, `planning_only`,
`blocked_by_data`, `blocked_by_rights`, `blocked_by_api`, `blocked_by_policy`, `not_approved`.

---

## 1. CardNews

- target_channel: Instagram feed (4-image carousel)
- target_audience: general lifestyle/informational Instagram followers, 20s-40s
- user_problem: wants a quick, visually clean answer to a practical everyday question
- content_goal: save/share-worthy 4-slide explainer reusing the canonical hook-problem-solution-cta contract
- input_requirements: topic, optional evidence/citation, `CardNewsModule`-compatible content_result
- evidence_requirements: only required when a slide makes a factual/statistical claim; otherwise general-knowledge copy is acceptable
- image_requirements: `CardNewsModule` fallback background or a rights-cleared photo/illustration
- rights_requirements: image licensing confirmation when a non-fallback image is used; text is self-authored
- freshness_requirements: evergreen for most lifestyle topics; annual re-check for tax/finance/regulation topics
- CTA 유형: save/share, never a direct commerce or account CTA
- monetization 가능성: none directly; reusable as a Commerce/BrandConnect on-ramp
- 필요한 기존 모듈: `modules/content/`, `modules/card_news/` (Pillow renderer, 10 layouts), `modules/image_prompt/`, `modules/image_generation/`
- 아직 없는 기능: none for the offline/manual path -- rendering, layout, QA, and fallback copy all exist and are operational (`MODULE_STATUS.md`: CardNews Intelligence + Production Quality complete, 2026-07-11)
- 현재 실행 가능 상태: **implemented** (rendering pipeline) / **offline_ready** (topic-specific copy needs a human evidence pass before publish)
- 승인 게이트: none beyond normal editorial review; `publishing_ready` must stay false while `manual_image_required=true` (existing contract)
- 예상 제작 난이도: low
- 예상 반복 생산 가치: high -- this is the most reusable, lowest-friction content type in the portfolio

## 2. Shorts/Reels

- target_channel: Instagram Reels / YouTube Shorts
- target_audience: short-form video consumers, 20s-30s
- user_problem: wants the fastest possible answer, consumed passively while scrolling
- content_goal: 15-45s scripted demonstration or checklist video
- input_requirements: script, scene plan, real filmed footage (no synthetic video/audio in this Sprint)
- evidence_requirements: mostly self-evidencing (the demonstration itself); statistics still need a citation
- image_requirements: real filmed clips or rights-cleared B-roll; no stock substitution without a license check
- rights_requirements: footage ownership or license confirmation; music/TTS licensing if used
- freshness_requirements: evergreen; re-verify seasonal footage before reuse
- CTA 유형: save/follow, never a purchase CTA without a separate Commerce approval
- monetization 가능성: none directly; future Commerce tie-in is a later-Sprint candidate
- 필요한 기존 모듈: `modules/shorts/shorts_module.py` (offline planning contract only, per `tests/test_shorts_phase_1.py`)
- 아직 없는 기능: video rendering, TTS, music, transcription, and platform upload are all **not implemented** -- `ai-content-os-shorts` skill explicitly scopes Shorts as Roadmap planning until a Sprint is authorized
- 현재 실행 가능 상태: **offline_ready** for script/scene planning; **blocked_by_api** for rendering, voice, and publish
- 승인 게이트: CTO Sprint authorization required before any rendering/upload automation is built
- 예상 제작 난이도: medium (requires real filming, no automation)
- 예상 반복 생산 가치: medium-high once a manual production rhythm exists

## 3. Instagram 피드 (general feed)

- target_channel: Instagram feed, single image or short carousel
- target_audience: general followers
- user_problem: wants bite-sized information without opening a full CardNews carousel
- content_goal: single-slide or 3-slide informational post
- input_requirements: topic, optional source citation
- evidence_requirements: same fail-closed rule as CardNews; community-sourced material must carry an explicit "community opinion" label
- image_requirements: category-appropriate illustration or licensed photo
- rights_requirements: attribution + PII scrubbing for any community-quoted material
- freshness_requirements: evergreen unless topic is trend-summary (see #9)
- CTA 유형: save/share/comment
- monetization 가능성: none directly (reach/trust building)
- 필요한 기존 모듈: `modules/content/`, `modules/card_news/` (reusable for the image asset), `modules/publishing/`
- 아직 없는 기능: none for the offline path
- 현재 실행 가능 상태: **offline_ready**
- 승인 게이트: none beyond editorial review
- 예상 제작 난이도: low
- 예상 반복 생산 가치: high

## 4. Instagram 정보형 콘텐츠 (informational deep-dive)

- target_channel: Instagram feed, 3-5 slide informational carousel
- target_audience: followers seeking accurate, slightly deeper explanations (consumer rights, refund policy, seasonal health basics)
- user_problem: wants a correct, non-oversimplified answer they can trust and act on
- content_goal: accurate concept/rule explainer with a real-world application example
- input_requirements: topic, and for regulation/consumer-rights topics a current official source
- evidence_requirements: **mandatory** official source for law/consumer-rights/finance content; general informational content may use common-knowledge framing
- image_requirements: infographic-style illustration
- rights_requirements: source attribution when an official document is quoted
- freshness_requirements: annual re-check for regulation-linked topics; evergreen otherwise
- CTA 유형: save/share
- monetization 가능성: none directly
- 필요한 기존 모듈: `modules/content/`, `modules/knowledge_engine/` (for pattern reuse), `modules/card_news/`
- 아직 없는 기능: no live regulation/legal database connection exists -- every regulation-adjacent brief in the backlog is flagged `SOURCE_REQUIRED`/`CURRENT_DATA_REQUIRED`
- 현재 실행 가능 상태: **offline_ready** for non-regulated topics; **blocked_by_data** for regulation/consumer-rights/finance topics until a human sources the current official text
- 승인 게이트: editorial fact-check sign-off for any regulation-adjacent claim
- 예상 제작 난이도: low-medium
- 예상 반복 생산 가치: high

## 5. BrandConnect 캠페인 콘텐츠

- target_channel: Instagram sponsored post/carousel
- target_audience: brand-defined (undefined until a real brand contract exists)
- user_problem: N/A until a real brand and campaign objective exist
- content_goal: campaign package structure ready to fill in once a brand deal is signed
- input_requirements: real brand contract, brand-provided facts/assets, sponsorship terms
- evidence_requirements: brand-provided official material only; no invented brand facts, ever
- image_requirements: brand-provided assets; self-shot footage requires brand written approval
- rights_requirements: brand asset usage rights, trademark/likeness confirmation
- freshness_requirements: campaign-window-bound, set by the brand contract
- CTA 유형: contract-dependent (purchase/visit/participate), gated behind approval
- monetization 가능성: high once a real contract exists; **zero today**
- 필요한 기존 모듈: `modules/brandconnect/` (`brandconnect_contract.py`, `brandconnect_package_builder.py`, `brandconnect_policy_gate.py`)
- 아직 없는 기능: no real brand ever connected; this portfolio invents no virtual brand to fill the gap
- 현재 실행 가능 상태: **not_approved** (package structure only; no real campaign exists)
- 승인 게이트: real brand contract + operator approval + platform sponsored-content policy review, all required before any content is written with real brand facts
- 예상 제작 난이도: high (requires external counterparty)
- 예상 반복 생산 가치: medium (one-off per brand deal, but the package structure itself is reusable)

## 6. Commerce 구매 가이드

- target_channel: Instagram CardNews or blog-style long-form
- target_audience: consumers actively comparing a purchase category
- user_problem: doesn't know which criteria matter before buying
- content_goal: criteria-first buying guide, no specific product recommendation until real product data exists
- input_requirements: category knowledge (materials, specs, use cases) -- no live product feed today
- evidence_requirements: manufacturer/official spec sheets for stable facts; live source for anything volatile
- image_requirements: category illustrations only; no real product photo until sourced and rights-cleared
- rights_requirements: product image rights confirmation before any real product image is used
- freshness_requirements: comparison criteria are evergreen; price/stock/shipping must be re-verified at time of use, never cached
- CTA 유형: "save the comparison criteria," never "buy now" without an approved product+link
- monetization 가능성: affiliate-candidate once a real product and disclosure are in place; **zero today**
- 필요한 기존 모듈: `modules/commerce/commerce_module.py` (Phase 1 offline package generator, currently under Lane C1/Independent QA -- see `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`)
- 아직 없는 기능: no live price/stock/review feed, no real product images, no affiliate link generation
- 현재 실행 가능 상태: **planning_only** (criteria-only guide) / **blocked_by_data** (once a specific product is named)
- 승인 게이트: real product source + rights confirmation + operator purchase-CTA approval
- 예상 제작 난이도: medium
- 예상 반복 생산 가치: high (criteria templates are reusable across many product categories)

## 7. 상품 비교 콘텐츠

Same module dependency and gating as #6 (Commerce 구매 가이드); modeled in the backlog as the
same `commerce_guide` content_type with a comparison-first structure. See
`RIGHTS_AND_ATTRIBUTION_MATRIX.md` and `EVIDENCE_REQUIREMENTS.md` for the shared rule set:
comparison criteria may be published; specific product claims (price/stock/rating/rank) may not,
until sourced.

- 현재 실행 가능 상태: **planning_only** / **blocked_by_data** (identical to #6)
- 아직 없는 기능: identical to #6 -- no live product/review/ranking data source exists

## 8. FAQ·How-to 콘텐츠

- target_channel: Instagram feed or CardNews, reusing the concept-explainer structure
- target_audience: users with a specific procedural question (e.g. "how do I...")
- user_problem: needs a step-by-step answer, not a general overview
- content_goal: numbered how-to steps with a clear completion state
- input_requirements: topic + procedural steps; official-source steps for regulated procedures (e.g. childcare-leave application, tax filing)
- evidence_requirements: procedural accuracy is mandatory for regulation-bound how-tos (`SOURCE_REQUIRED`); general lifestyle how-tos may use common-knowledge steps
- image_requirements: step-illustration graphics
- rights_requirements: none beyond standard image licensing
- freshness_requirements: regulation-bound how-tos need annual re-verification; general how-tos are evergreen
- CTA 유형: save/share
- monetization 가능성: none directly
- 필요한 기존 모듈: `modules/content/`, `modules/card_news/`
- 아직 없는 기능: none for the offline path; represented in the backlog as `cardnews`/`instagram_feed` briefs with a checklist/how-to structure (e.g. CN-011 전세 계약 체크리스트, CN-023 육아휴직 신청 절차 체크리스트)
- 현재 실행 가능 상태: **offline_ready** (general) / **blocked_by_data** (regulation-bound procedures, until sourced)
- 승인 게이트: fact-check sign-off for regulation-bound procedures
- 예상 제작 난이도: low
- 예상 반복 생산 가치: high

## 9. 트렌드 해설 콘텐츠

- target_channel: Instagram feed
- target_audience: followers who want a fast, accurate read on "what's trending"
- user_problem: wants a summary of a real trend without reading the original source
- content_goal: short interpretive summary of an already-collected trend/community item
- input_requirements: an actual `TrendCollectorModule`/Nate Pann/Naver News item with a real, matched source
- evidence_requirements: **mandatory** -- must trace to a real collected item; never described as "currently trending" without a directly matched source (this exact honesty gate is the subject of the active Lane T/R correction in `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`)
- image_requirements: neutral illustration, not a screenshot of the original post unless rights-cleared
- rights_requirements: community text must be labeled as opinion and scrubbed of PII
- freshness_requirements: **very short** -- 1-2 weeks at most; a trend summary older than that is stale
- CTA 유형: save/share/comment
- monetization 가능성: none
- 필요한 기존 모듈: `modules/trend_collector/`, `modules/research/`
- 아직 없는 기능: none structurally, but every brief here inherits the same evidence-honesty gate the Trend/Research lane is actively correcting -- do not treat this content type as safe to mass-produce until that correction lands
- 현재 실행 가능 상태: **blocked_by_data** (a real, current, matched trend item is required at write-time -- this portfolio provides only the format, never a pre-written trend claim)
- 승인 게이트: none beyond the existing evidence-honesty contract
- 예상 제작 난이도: low (once a real trend item exists)
- 예상 반복 생산 가치: high (renewable content type, but only as fast as real trends are collected)

## 10. Knowledge 기반 Evergreen 콘텐츠

- target_channel: Instagram feed or blog
- target_audience: self-improvement / practical-knowledge audience, 20s-40s
- user_problem: uses a concept/term without understanding it precisely
- content_goal: precise, simply-worded concept explainer with a real-life application
- input_requirements: topic + a commonly accepted definition; official source for legal/financial/IP/privacy concepts
- evidence_requirements: official source mandatory for law/finance/copyright/privacy topics; general concepts may use commonly accepted definitions
- image_requirements: infographic-style
- rights_requirements: standard, plus source attribution for quoted official material
- freshness_requirements: evergreen, annual re-check for regulation-adjacent concepts
- CTA 유형: save/share
- monetization 가능성: none directly (builds account authority/trust, which is a precondition for later Commerce/BrandConnect credibility)
- 필요한 기존 모듈: `modules/content/`, `modules/knowledge_engine/`
- 아직 없는 기능: none for the offline path
- 현재 실행 가능 상태: **offline_ready** (general concepts) / **blocked_by_data** (law/finance/IP/privacy concepts, until sourced)
- 승인 게이트: fact-check sign-off for regulation-adjacent concepts
- 예상 제작 난이도: low
- 예상 반복 생산 가치: high

## 11. Affiliate 전환 콘텐츠 후보

- target_channel: Instagram CardNews / Commerce guide with an affiliate CTA
- target_audience: consumers already in a purchase-comparison mindset (shared audience with #6/#7)
- user_problem: wants a trusted recommendation, not just criteria
- content_goal: comparison guide with an eventual affiliate link, once approved
- input_requirements: real product, real affiliate account, real disclosure copy
- evidence_requirements: identical to Commerce (#6/#7), plus a confirmed, owned affiliate account
- image_requirements: rights-cleared product image
- rights_requirements: product image rights + affiliate program terms compliance
- freshness_requirements: price/stock/discount must be re-verified immediately before any publish -- never cached
- CTA 유형: purchase, gated behind disclosure and approval
- monetization 가능성: direct, but **entirely unapproved today**
- 필요한 기존 모듈: `modules/affiliate/` (`affiliate_contract.py`, `affiliate_policy_gate.py`, `affiliate_revenue_router.py`, `affiliate_result.py`, `affiliate_safety_utils.py`) exists as a contract/policy-gate layer; `modules/commerce/` for the underlying product package
- 아직 없는 기능: no real affiliate account is connected anywhere in the repository; no real link has ever been generated
- 현재 실행 가능 상태: **not_approved** -- this portfolio does not stage this content type as a backlog item because there is no real product+account pairing to design against yet; treat #6/#7 Commerce guides as the pre-affiliate on-ramp instead
- 승인 게이트: real affiliate account ownership + disclosure copy + operator approval + platform policy review, all required before any affiliate-labeled brief is written
- 예상 제작 난이도: high (blocked on external account setup)
- 예상 반복 생산 가치: high once unblocked, because it reuses the Commerce comparison-criteria template

## 12. 해외 소싱·Amazon 콘텐츠 후보

- target_channel: not yet defined (would depend on target market -- domestic Korean audience vs. a US/global Amazon audience)
- target_audience: undefined until a market decision is made
- user_problem: undefined
- content_goal: undefined
- input_requirements: an Amazon/overseas-sourcing product feed or API connection, which does not exist in this repository
- evidence_requirements: same fail-closed rule as Commerce, plus cross-border pricing/currency/import-duty facts that are currently entirely unavailable
- image_requirements: same as Commerce, plus cross-border image-rights clearance
- rights_requirements: unresolved -- no Amazon Associates or equivalent program is connected; cross-border seller/brand rights are unresolved
- freshness_requirements: same volatility as Commerce, likely worse given currency/shipping variability
- CTA 유형: undefined
- monetization 가능성: undefined until a program is connected
- 필요한 기존 모듈: none exist for this today -- no `modules/` code references Amazon or any overseas marketplace
- 아직 없는 기능: everything -- no data source, no API, no account, no market decision, no policy review
- 현재 실행 가능 상태: **planning_only** -- this portfolio records the category as a Roadmap candidate only; no backlog brief is written for it because there is nothing real to design against
- 승인 게이트: CTO market decision + program/account approval + full legal/policy review, before any planning beyond this paragraph
- 예상 제작 난이도: unknown (depends on unresolved market decision)
- 예상 반복 생산 가치: unknown

---

## Summary table

| # | Content type | Current state | Backlog briefs |
|---|---|---|---|
| 1 | CardNews | offline_ready | 25 |
| 2 | Shorts/Reels | offline_ready (script) / blocked_by_api (render/publish) | 20 |
| 3 | Instagram 피드 | offline_ready | included in 20 (Instagram feed) |
| 4 | Instagram 정보형 | offline_ready / blocked_by_data (regulated) | included in 20 (Instagram feed) |
| 5 | BrandConnect | not_approved | 15 (package structure only) |
| 6 | Commerce 구매 가이드 | planning_only / blocked_by_data | included in 20 (Commerce) |
| 7 | 상품 비교 콘텐츠 | planning_only / blocked_by_data | included in 20 (Commerce) |
| 8 | FAQ·How-to | offline_ready / blocked_by_data (regulated) | folded into CardNews/Instagram briefs |
| 9 | 트렌드 해설 | blocked_by_data (needs a real current trend item) | folded into Instagram feed briefs (trend_summary tag) |
| 10 | Knowledge/Evergreen | offline_ready / blocked_by_data (regulated) | 20 |
| 11 | Affiliate 전환 후보 | not_approved | 0 (no backlog brief; documented as a gated future extension of Commerce) |
| 12 | 해외 소싱·Amazon | planning_only | 0 (no backlog brief; nothing real to design against) |

120 backlog briefs total across the six categories that have real, executable design work
today (CardNews 25, Shorts 20, Instagram feed 20, BrandConnect 15, Commerce 20,
Knowledge/Evergreen 20). Affiliate-conversion and overseas-sourcing content are documented
above as Roadmap categories, deliberately without invented backlog briefs, because writing a
brief against a non-existent product/account/market would itself violate the data-honesty
requirement this portfolio is built to enforce.
