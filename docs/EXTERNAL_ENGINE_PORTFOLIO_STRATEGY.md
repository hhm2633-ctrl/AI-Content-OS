# External Engine Portfolio Strategy

Date: 2026-07-12

Scope: CTO portfolio strategy for AI-Content-OS. This is not a repository-by-repository summary.
No external repository was cloned. No code, tests, shared status documents, `site/`, `storage/`, or
Git state were modified.

External targets:

- `Daewooki/naver-bc-automation`: <https://github.com/Daewooki/naver-bc-automation>
- `tchung1970/amazon-cli`: <https://github.com/tchung1970/amazon-cli>
- `harry0703/MoneyPrinterTurbo`: <https://github.com/harry0703/MoneyPrinterTurbo>
- `Builderlog`: <https://builderlog.net/ko/resources/>,
  <https://builderlog.net/ko/studio/>, <https://builderlog.net/ko/analyzer/>,
  <https://builderlog.net/ko/prompts/>
- `DAF / 대한AI팩토리`: <https://daehanaifactory.com/>
- Prior local/external research: Manus `seller_automation`, Reels reference-product analysis,
  Damagoci/Coupang Partners benchmark, Builderlog/DAF screenshots and public pages.

Legend:

- `CONFIRMED`: observed from the official GitHub page/raw file during this pass.
- `INFERRED`: reasoned from available evidence or CTO-provided evaluation axis.
- `UNKNOWN`: not verified in this pass.
- `CTO GATE`: requires explicit CTO approval or official policy/security verification before build.

## 1. CTO Executive Decision

| External engine | Decision | Why |
|---|---|---|
| Naver BC automation | `Borrow selectively` for market/vertical workflow; `Clean-room rebuild` contracts; `Reject` stealth/session/coordinate publishing code | `CONFIRMED`: repo targets automatic Naver BrandConnect review posting, product URL input, GPT writing, image scraping/upload, hashtags, web dashboard, stealth plugin, session storage, and automatic publishing. Those prove market demand and workflow shape. They also prove policy/account risk. |
| amazon-cli | `Borrow selectively` ASIN candidate/enrich/rank/cache pattern; `Clean-room rebuild` official API adapter; `Reject` production HTML scraping | `UNKNOWN`: official repo content could not be fetched in this pass. `INFERRED`: CTO-provided axis points to useful product-candidate and cache patterns, but production scraping must not be adopted without policy/API review. |
| MoneyPrinterTurbo | `Borrow selectively` MIT rendering/subtitle helper spike; `Reject` full clone, bundled media, Upload-Post automation, and plaintext-key configuration | `CONFIRMED`: repo is MIT-labeled on GitHub, one-click AI short-video generation, Web/API UI, scripts/materials/subtitles/music, many model providers, Pexels/Pixabay/Coverr materials, and optional Upload-Post cross-posting. It is too broad and risky to clone. |
| Builderlog | `Adopt` GTM/product pattern; `Reject` content/data/code copying | `CONFIRMED / CTO-PROVIDED`: free prompt/resource library, RSS, KO/EN, Threads funnel, product-to-prompt studio, analyzer, and prompt curator validate demand for public kits and build-in-public acquisition. Data source and terms remain `UNKNOWN`. |
| DAF | `Adopt` freemium/local-first workbench pattern; `Reject` closed launcher/input automation copying | `CONFIRMED`: Windows/macOS blog workbench, free tools, paid keyword radar, trial, user-final-publish stance. Keyword source, local processing, updater security, and input-assistant method remain `UNKNOWN`. |
| Manus seller_automation | `Adopt` operator workflow lessons; `Reject` browser automation as default | `INFERRED` from prior audit: it validates seller/affiliate operations demand, but safe target is verified payload + user approval + allowed transfer, not raw automated upload. |
| Reels reference products | `Adopt` reference-board and pattern-brief product shape; `Reject` unverified public metrics as training data | `CONFIRMED / CTO-PROVIDED`: public reference boards and reel metadata are useful product signals. Data source, rights, category accuracy, and metric provenance remain `UNKNOWN`. |
| CodeGraph-style dev tooling | `Adopt` as isolated development-tool POC only | `INFERRED`: graphing code/contracts can help developers inspect AI-Content-OS, but it is not a customer-facing content product and must not touch production workflows without a separate gate. |

Portfolio decision:

```text
Build AI-Content-OS as a product-intelligence + content-factory + channel-execution + revenue-learning OS.
Borrow patterns, not automation behavior.
Clean-room rebuild contracts and adapters.
Reject stealth publishing, uncontrolled scraping, bundled-media reuse, and direct cross-post/upload defaults.
```

Builderlog decision:

```text
Treat Builderlog as direct market validation and GTM pattern evidence, not as a technology supplier.
Borrow the funnel/product pattern clean-room.
Do not copy Builderlog content, prompt text, code, category heuristics, or public dataset.
```

DAF decision:

```text
Treat DAF as market validation for a local-first creator/blog workbench and freemium pricing ladder.
Borrow workflow, packaging, and pricing patterns clean-room.
Do not copy closed-product code, launcher behavior, UI, data sources, or automation internals.
```

Canonical build / buy / adopt / reject table:

| Candidate | Classification | Adopt | Reject / block | CTO gate |
|---|---|---|---|---|
| Affiliate Revenue Router | `Build` | route domestic affiliate, CPA, and global affiliate offers into separate ledgers and disclosure rules | one blended revenue model, unverified payout claims | affiliate policy and disclosure review |
| Sponsored Campaign Compliance Checker | `Build now` | campaign-brief validator and pass/fail/manual report | legal certainty claims, auto-publishing | disclosure/legal checklist review |
| Photo-to-Evidence Content Draft | `Build` | user photos + verified facts + rights into blog/card/shorts briefs | unlicensed media reuse, unverifiable experience claims | image rights and privacy gate |
| Creator Input Assistant | `Build as manual handoff` | approved package to channel-specific manual checklist | live DOM/RPA/browser posting by default | channel policy and credential gate |
| Local-first Creator Workbench | `Build later` | local package/workspace UX and privacy posture | unsigned launcher/updater or opaque credential storage | security design gate |
| Reels Intelligence | `Build staged harness` | reference -> pattern -> adaptation -> Shorts package -> performance feedback | scraping/login automation, metric claims from unknown source | Instagram/Graph/public-data gate |
| Shorts render/subtitle helpers | `Borrow selectively` | MIT-reviewed helper behind adapter | full MoneyPrinterTurbo clone, bundled media, Upload-Post | license/security/rights gate |
| Seller Automation SaaS | `Build later` | verified payloads, manual/draft transfers, official adapters | stealth, raw browser automation, unapproved upload | platform policy gate |
| Product Intelligence | `Build` | ProductCandidate, ProductSnapshot, OfferSnapshot with freshness | production HTML scraping | official API/provider gate |
| CodeGraph developer tool | `Isolated POC` | read-only architecture/code map for developers | runtime dependency in content workflow | dev-tool isolation gate |

## 2. Evidence Notes

`CONFIRMED`: `Daewooki/naver-bc-automation` public README says it automatically posts Naver Shopping
Connect/BrandConnect product reviews to Naver Blog. It lists product URL input, GPT-based SEO review
writing, image scraping/upload, hashtag generation, web dashboard, stealth plugin bot-detection
workaround, discount/review/rating collection, session persistence, Playwright Chromium setup, and
automatic publish flow.

`CONFIRMED`: The same README warns that excessive automation can violate Naver terms, accounts may
be sanctioned for too many posts in a short time, and users are responsible for results.

`CONFIRMED`: `harry0703/MoneyPrinterTurbo` public GitHub page says a user can provide a topic or
keyword and automatically generate video copy, materials, subtitles, background music, and an HD
short video. It lists Web UI, API, 9:16 and 16:9 video, batch generation, TTS, subtitles, background
music, material sources including Pexels/Pixabay/Coverr, many LLM providers, and optional
Upload-Post cross-posting to TikTok/Instagram/YouTube Shorts.

`CONFIRMED`: MoneyPrinterTurbo's public config example contains many API-key fields and Upload-Post
settings, including an `upload_post_auto_upload` option that defaults false. Keys are represented
as plaintext config fields in the sample.

`UNKNOWN`: `tchung1970/amazon-cli` official GitHub page and remote metadata could not be fetched in
this environment. Treat all repo-specific details as unverified until a later official-source pass.

`CONFIRMED / CTO-PROVIDED`: Builderlog exposes a free prompt/resource library, RSS, Korean/English
surface, and a Threads build-in-public funnel. Its studio flow maps Product info into a blog
research/SEO prompt, 5-slide card brief, and UGC video shot-list prompt. It references affiliate
platforms including global affiliate, Shopping Connect, and Coupang, and excludes hands-on
experience phrasing when direct-use confirmation is missing. A finished content kit is marked as
preparing.

`CONFIRMED / CTO-PROVIDED`: Builderlog Threads Analyzer uses a 49-sample dataset toward a 10k
target, time decay, comments x2, repost/share x3, follower/account metrics, local queue, and CSV.
Its Prompt Curator checks GitHub origin/activity/license/cost and turns the result into Claude/GPT/
Gemini adoption prompts.

`CONFIRMED / CTO-PROVIDED`: Builderlog's operating checklist includes queue depletion,
cross-output dedupe, failure alert, draft default, frequency, fact guard, rollback, and
language/channel parity.

`UNKNOWN`: Builderlog's Threads public-data collection method, metric accuracy, and platform-terms
position were not independently verified in this pass. The 49-sample analyzer must not be used for
market-size or performance conclusions.

`CONFIRMED`: DAF is a Windows/macOS installable blog workbench. The public page describes four
tools: Keyword Radar, photo writing, blog input assistant, and sponsored condition checking. Photo
writing, blog input assistant, and sponsored condition checking are presented as free tools, while
Keyword Radar advanced features are paid.

`CONFIRMED`: DAF pricing is shown as an open monthly subscription of 19,900 KRW, down from 59,000
KRW, and a 30-day coupon of 29,900 KRW, down from 99,000 KRW. Email verification gives three days
of paid-feature trial.

`CONFIRMED`: DAF positions Keyword Radar around region, industry, category, real-time trend
keywords, topic candidates, and title candidates. DAF states the user makes the final expression
and publishing decision, does not provide mass posting, interaction manipulation, or performance
guarantees, and says external service passwords are not stored on DAF servers.

`CONFIRMED`: DAF launcher login is required for tool installation/update, tools are installed
per-program, and simultaneous execution is limited to one program.

`UNKNOWN`: DAF keyword source/API, real-time accuracy, data freshness, whether photo/manuscript
processing is fully local or sent to external AI, launcher code signing, auto-update security,
credential storage, real users/revenue/retention, and whether the input assistant is DOM/RPA,
clipboard, or manual handoff.

`CONFIRMED / CTO-PROVIDED`: Today's five screenshots are treated as product/market evidence for
the consolidated portfolio decisions in this document, not as permission to copy UI, content,
datasets, code, or automation behavior.

## 3. Common Four-Layer Architecture

### 3.1 Product Intelligence Plane

Purpose: find, normalize, verify, compare, and refresh product opportunities before content or
channel execution.

Core contracts:

- `ProductCandidate`
- `ProductSnapshot`
- `OfferSnapshot`
- `AffiliateOpportunity`
- evidence/freshness/rights metadata

Responsibilities:

- product/ASIN/SKU/link candidate intake;
- evidence collection and source status;
- price, discount, stock, rating, review count, rank, image-rights freshness;
- conflict detection;
- opportunity scoring;
- policy gate status.

External pattern mapping:

- Naver BC: `INFERRED`: vertical workflow starts from a product/review link and turns it into a
  content candidate.
- amazon-cli: `INFERRED`: ASIN candidate/enrich/rank/cache pattern belongs here.
- MoneyPrinterTurbo: `INFERRED`: topic-to-material search is analogous, but for video assets
  rather than commerce products.

### 3.2 Content Factory

Purpose: turn verified opportunities into multi-format content packages.

Pipeline:

```text
Research -> Content -> CardNews / Shorts / SEO
```

Responsibilities:

- evidence-backed SEO article;
- comparison/recommendation copy;
- product card news;
- scene plan and short-form scripts;
- FAQ and objection handling;
- disclosure and attribution insertion.

### 3.3 Channel Execution

Purpose: prepare or execute channel-specific artifacts under strict mode controls.

Channel modes:

- seller listing;
- affiliate blog;
- social publishing;
- draft adapters;
- manual adapters;
- live adapters, only after CTO approval.

Execution mode ladder:

```text
package_only -> draft_only -> manual_review -> human_approved_single -> live_limited
```

Default: `package_only` or `draft_only`. Never default to live upload.

### 3.4 Revenue Learning

Purpose: close the loop with performance data without fabricating metrics.

Ledger inputs:

- click;
- conversion;
- revenue;
- cost;
- variant;
- channel;
- product/category;
- content format.

Responsibilities:

- local cost ledger;
- conversion/revenue feedback ledger;
- variant comparison;
- Knowledge/Brand DNA updates;
- stop-loss and stale-offer detection.

## 4. Business Lines

| Business line | Customer | Price / revenue model | Existing reuse | New development | Main risk | MVP order |
|---|---|---|---|---|---|---|
| Seller Automation SaaS | Small sellers, consignment sellers, operators | Monthly SaaS, per-SKU package, managed setup | Commerce truth gate, Research, Content, Publishing checklist | Seller data intake, official API/draft adapters, dashboard, credential vault | Platform policy, stale price/stock, listing-side effects | 4 |
| Affiliate Content Factory | Affiliate bloggers, niche-site operators, agencies | Subscription, per-content credits, managed article/card/short packages | Trend, Research, Content, CardNews, Shorts, Publishing, Knowledge, Brand DNA, Performance | AffiliateOpportunity, Disclosure, PartnerLinkRegistry, WordPressDraftExporter, RevenueLedger | Disclosure, false reviews, SEO spam, link/account policy | 1 |
| Shorts / Video Production SaaS or managed service | Creators, ecommerce brands, agencies | Per-video credits, monthly pack, managed editing | Shorts planning, Content, CardNews assets, Publishing checklist, Performance | ScenePlan, AssetManifest, TimedCaption, RenderProfile, renderer spike | Rights, TTS/music licenses, high compute/cost | 2 |
| Product Intelligence / competitive research | Sellers, agencies, product researchers | B2B subscription, reports, API/export | Trend, Research Intelligence, Knowledge, Performance, Commerce truth gate | ProductSnapshot, OfferSnapshot, competitor source adapters, freshness scheduler | Scraping/API policy, evidence quality, rate limits | 3 |
| Consignment operator dashboard | Wholesale/consignment operators, small teams | B2B SaaS, setup fee, operations seat pricing | Product Intelligence, Commerce truth gate, Publishing, Revenue ledger | Catalog importer, task queue, source health, role-based dashboard | Supplier terms, credentials, PII, support load | 5 |

CTO prioritization:

1. Affiliate Content Factory.
2. Shorts / Video package.
3. Product Intelligence.
4. Seller Automation SaaS.
5. Consignment operator dashboard.

Reason: Affiliate and Shorts products reuse the highest percentage of current AI-Content-OS engines
and avoid the highest-risk seller listing side effects.

Canonical execution portfolio:

| Business opportunity | Reused engines | New contracts needed | Main risks | Approval gate | Revenue model |
|---|---|---|---|---|---|
| Affiliate Content Factory | Trend, Research, Content, CardNews, Shorts, Publishing QA, Performance | `AffiliateOpportunity`, `AffiliateRevenueRouter`, `Disclosure`, `PartnerLinkRegistry`, `RevenueLedger` | false reviews, stale price/stock, disclosure, affiliate policy | domestic/CPA/global affiliate policy gate | subscription, per-content credits, managed package |
| Sponsored Campaign Compliance Checker | Research, Publishing QA, Commerce truth gate, Harness | `CampaignBrief`, `CampaignRequirement`, `ComplianceCheckResult`, `ManualActionChecklist` | disclosure law, keyword/count errors, image/video/map requirements | legal/disclosure checklist gate | free entry, paid workspace/report |
| Photo-to-Evidence Content Draft | Research, Content, Brand DNA, CardNews, Shorts | `UserAssetEvidence`, `RightsBoundary`, `AdaptationBrief`, `AssetManifest` | image rights, PII, unverifiable personal experience | rights/privacy gate | free brief, paid multi-format package |
| Reels Intelligence / Shorts Package | Trend, Instagram Research, Competitor Learning, Shorts, Publishing, Performance | `ReelReference`, `MetricSnapshot`, `PatternSignature`, `PerformanceLink` | scraping terms, metric provenance, category errors, creative copying | Instagram data and rights gate | creator subscription, agency dashboard, managed production |
| Product Intelligence / Competitive Research | Trend, Research Intelligence, Knowledge, Commerce truth gate | `ProductCandidate`, `ProductSnapshot`, `OfferSnapshot`, `SourceHealth` | HTML scraping, freshness, source reliability | official API/provider gate | B2B reports, workspace, API/export |
| Seller Automation SaaS | Commerce truth gate, Research, Content, Publishing QA | `SellerPayload`, `ChannelTask`, `PublishReceipt`, `RollbackReceipt` | platform policy, account risk, stale offer, credential storage | platform/manual/draft gate | SaaS, setup fee, managed ops |
| Local-first Creator Workbench | Trend, Research, Content, CardNews, Shorts, Publishing QA | `WorkspacePackage`, `LocalCredentialPolicy`, `UpdateReceipt` | local PII, updater signing, credential storage | security/release gate | freemium, team workspace |
| Developer Architecture Tooling | Harness docs, module contracts, QA reports | `CodeGraphSnapshot`, `DependencyEdge`, `InspectionReport` | leaking secrets, stale architecture graph, scope creep | dev-tool isolation gate | internal productivity first; later enterprise add-on |

Affiliate Revenue Router:

`PROPOSED`: Split affiliate monetization into three explicit routes instead of one generic
"affiliate" lane.

| Route | Examples | Required fields | Blocked claims | Ledger |
|---|---|---|---|---|
| Domestic affiliate | Coupang Partners, Shopping Connect-style offers | local disclosure, product URL, partner link, captured_at | price/rank/review claims without freshness | `RevenueLedger` with local currency and channel |
| CPA / lead-gen | sign-up, quote, reservation, app install | offer terms, conversion definition, payout window | guaranteed approval, guaranteed income | `RevenueLedger` with pending/confirmed/reversed states |
| Global affiliate | Amazon/global networks | locale, tax/currency, regional disclosure, official API/source | universal availability, exchange-rate certainty | `RevenueLedger` with currency, locale, and source |

`UNKNOWN`: Current official policies, payout reversals, cookie windows, and reporting APIs differ by
network and must be verified before any automated recommendation or revenue forecast.

Builderlog-adjusted GTM lesson:

`INFERRED`: Builderlog is not mainly a supplier to buy. It is a live proof that creators and
operators understand the value of prompt kits, reference libraries, small public trend datasets,
and build-in-public distribution. AI-Content-OS should answer with a stronger artifact-first
product, not with a clone.

Competitive gap:

| Dimension | Builderlog | AI-Content-OS target |
|---|---|---|
| Core offer | prompt generation plus small public trend/reference dataset | evidence-backed actual content artifacts |
| Content outputs | prompts, briefs, and preparing content kit | CardNews, Shorts package, SEO package, publishing-ready artifacts |
| Data posture | public trend/analyzer surface; current accuracy/terms unknown | provenance, freshness, rights, and source-health gates |
| Publishing | prompt/workflow assistance | draft/manual/live ladder with approval and read-back gates |
| Learning loop | public build-in-public dataset and prompt iteration | performance/revenue/cost ledgers tied to produced artifacts |

Build-in-public GTM:

- free Prompt Kit for trend, affiliate, card-news, Shorts, and publishing prep;
- public Quality/Failure log showing blocked claims, fallback events, and artifact QA;
- weekly Trend/Pattern brief with source confidence and "not investment/performance proof" labels;
- beta waitlist for creator, agency, affiliate, and seller operators;
- free audit/report that turns one topic/product/account into a paid workspace trial;
- bilingual RSS and Threads funnel that publishes learning without exposing private user data.

MVP free vs paid boundary:

| Free public surface | Paid workspace |
|---|---|
| prompt/resource library | saved brand/workspace memory |
| sample trend/pattern briefs | private competitor watchlists and custom cohorts |
| public QA/failure log | artifact QA dashboard and approval ledger |
| one-off audit/report | repeatable content factory runs |
| generic affiliate/card/Shorts prompts | evidence-backed affiliate kit, card-news export, Shorts package |
| RSS/Threads learn-in-public notes | team queue, performance/revenue feedback, cost ledger |

Expanded revenue products:

- creator toolkit: prompt kit, reference board, content calendar, Shorts/card package export;
- affiliate content kit: product info to SEO article, card brief, UGC video shot-list, disclosure;
- agency workspace: team queue, client briefs, approval ledger, bilingual outputs;
- brand intelligence: competitor/reference monitoring, weekly pattern report, failure/quality log;
- seller automation: manual/draft-first commerce packages after policy gates;
- managed production: done-with-you artifact creation using the same truth/provenance gates.

DAF-adjusted immediate product candidates:

| Product candidate | Input | AI-Content-OS reuse | Output | Gate |
|---|---|---|---|---|
| Sponsored Campaign Compliance Checker | campaign brief, required keywords/count/images/video/map/disclosure | Research, Publishing QA, Commerce truth gate, Harness approval | pass/fail/manual checklist and missing-condition report | disclosure law and platform policy |
| Photo-to-Evidence Content Draft | user photos, verified facts, rights notes, target channel | Research, Content, Brand DNA, CardNews, Shorts | blog/card/shorts briefs with rights/evidence labels | image rights and factuality |
| Creator Input Assistant | approved package and channel target | Publishing QA, ChannelTask, approval ledger | manual handoff package, not live auto publish | no credential or live posting by default |
| Local-first Creator Workbench | local project package, user assets, offline checklist | Trend, Research, Content, CardNews, Shorts, Publishing QA | installable/workspace-style bundle or local folder package | local PII and update security |

DAF-adjusted freemium ladder:

| Free entry | Paid expansion |
|---|---|
| compliance checker for campaign briefs | keyword intelligence and freshness scoring |
| photo brief with evidence/rights checklist | multi-format blog/card/shorts package |
| manual input checklist | team/agency workspace and queue |
| one-off blog/card report | recurring brand/affiliate/seller workspace |

Pricing note:

`INFERRED`: DAF's 19,900 KRW monthly open price and 29,900 KRW 30-day coupon are useful early
benchmarks for willingness-to-try, not sufficient evidence for AI-Content-OS pricing. AI-Content-OS
should not overfit to that price because its target product can include multi-format artifacts,
evidence/rights validation, publishing QA, and performance/revenue learning.

DAF competitive gap:

| Dimension | DAF | AI-Content-OS target |
|---|---|---|
| Primary surface | blog-only installed workbench | multi-format content OS |
| Content support | keyword, photo draft, input assist, campaign condition check | blog/card/shorts/affiliate/seller packages |
| Safety claim | user final decision, no mass posting/manipulation/performance guarantee | deterministic gates, evidence, rights, approval, read-back, rollback |
| Data posture | keyword source/freshness unknown | source-health, freshness, provenance, fallback/cache |
| Monetization | free blog tools plus paid keyword radar | free compliance/photo brief plus paid intelligence/package/workspace |
| Learning loop | unknown | performance/revenue/cost ledgers |

Build / buy for DAF:

- Closed product, so code copying is not available.
- Workflow, pricing, local-first packaging, and freemium pattern: `clean-room GO`.
- Product purchase or partnership: `CTO GATE` after actual trial, workflow fit, security, and ROI
  review.
- Direct launcher, updater, credential, or input-assistant behavior: `NO-GO` until inspected.

DAF-informed 30-day MVP:

```text
Networkless Sponsored Campaign Compliance Checker
```

Build:

- campaign checklist schema;
- deterministic validator;
- pass/fail/manual status;
- missing-condition report;
- reuse current CardNews evidence contracts and Commerce truth-gate concepts where compatible.

Stop criteria:

- campaign disclosure obligations cannot be represented safely;
- checklist produces legal certainty claims instead of operational guidance;
- image rights cannot be captured;
- keyword freshness is required but unavailable.

## 5. Repository Decisions

### 5.1 Naver BC Automation

Decision:

- Market/vertical workflow: `GO`.
- Clean-room contracts: `GO`.
- Stealth/session/coordinate/browser publishing code: `NO-GO`.
- Direct code port: `NO-GO`.

`CONFIRMED` value:

- Product/review link as the operator input.
- Web dashboard as workflow UI.
- AI review generation.
- Image collection/upload and hashtag generation as user-expected workflow steps.
- Clear demand around brand/commerce review automation.

`CONFIRMED` rejection signals:

- Stealth plugin positioned as a bot-detection workaround.
- Session persistence for 7-30 days.
- Automatic publish flow.
- README warnings about terms/account sanctions.

Clean-room contracts to borrow:

- `ChannelTask` for Naver Blog review package.
- `ProductSnapshot` with discount/review/rating marked volatile.
- `Disclosure` / sponsorship disclosure for review content.
- `PublishReceipt` only after read-back verification, not after button click.

### 5.2 amazon-cli

Decision:

- ASIN candidate/enrich/rank/cache pattern: `GO` as architecture idea.
- HTML scraping in production: `NO-GO`.
- Official API adapter: required.
- Direct code port: `UNKNOWN / blocked until official repo review`.

`UNKNOWN`:

- Official repository content was not fetched.
- License, implementation language, scraping behavior, cache schema, and API use are unverified.

`INFERRED` reusable pattern:

- `ProductCandidate` from ASIN/search keyword.
- `ProductSnapshot` enrichment.
- `OfferSnapshot` rank/price/availability cache.
- Local cache to reduce repeat lookups.

CTO requirement:

- Use official Amazon Product Advertising API or another approved source where applicable.
- If only HTML scraping exists, use it as a product-research anti-pattern, not production code.

### 5.3 MoneyPrinterTurbo

Decision:

- Full clone: `NO-GO`.
- MIT render/subtitle helper selective spike: `GO`, after license review.
- Bundled media/fonts/songs: `NO-GO`.
- Upload-Post / cross-post automation: `NO-GO` until platform and account approval.
- Plaintext-key config pattern: `NO-GO` for AI-Content-OS production.

`CONFIRMED` value:

- Topic/keyword to script/materials/subtitles/music/video.
- Web UI and API split.
- 9:16 and 16:9 output profiles.
- Batch generation and selection.
- Subtitle generation via Edge timestamps or Whisper.
- Material source abstraction.
- Many LLM/TTS provider adapters.

`CONFIRMED` rejection signals:

- README/config show optional cross-posting via Upload-Post.
- Config example exposes numerous API-key fields as config values.
- README notes bundled background music may include YouTube-derived material and says delete if
  infringing.

Selective spike candidates:

- `ScenePlan` to timeline.
- `TimedCaption` generation/normalization.
- `RenderProfile` for 9:16 / 16:9.
- Subtitle styling/position model.
- Local-material-only render path.

## 6. Common Contract Candidates

| Contract | Purpose | First business line |
|---|---|---|
| `AffiliateOpportunity` | Keyword/product/content opportunity with policy and revenue potential | Affiliate Content Factory |
| `AffiliateRevenueRouter` | separates domestic affiliate, CPA, and global affiliate revenue routes | Affiliate Content Factory |
| `ProductSnapshot` | Stable product facts and evidence refs | Affiliate, Seller, Product Intelligence |
| `OfferSnapshot` | Volatile offer facts: price, discount, stock, shipping, ranking, rating | Affiliate, Seller, Product Intelligence |
| `Disclosure` | Sponsorship/affiliate/AI-generated/content disclosure text, placement, hash | Affiliate, Naver BC-style review, social |
| `ClaimRiskGate` | blocks numeric, financial, experience, and performance claims without proof | Affiliate, Sponsored, Seller, Reels |
| `CampaignBrief` | sponsored campaign source requirements and operator intent | Sponsored Campaign Checker |
| `CampaignRequirement` | required keywords/count/images/video/map/disclosure/link checklist item | Sponsored Campaign Checker |
| `ComplianceCheckResult` | pass/fail/manual result with missing items and publish gate | Sponsored Campaign Checker |
| `ManualActionChecklist` | channel-specific handoff steps after approval | Creator Input Assistant |
| `ScenePlan` | Shorts/video scenes, duration, intent, asset refs | Shorts / Video |
| `AssetManifest` | Image/video/music/font assets with rights provenance | CardNews, Shorts, SEO |
| `TimedCaption` | Caption text with timing, style, language, source | Shorts / Video |
| `RenderProfile` | aspect ratio, resolution, codec, subtitle style, output policy | Shorts / Video |
| `ReelReference` | public or authorized reel reference with rights boundary and provenance | Reels Intelligence |
| `MetricSnapshot` | metric values captured at one time with source method and confidence | Reels, Performance |
| `PatternSignature` | abstract hook/scene/CTA pattern without copying the original | Reels, Shorts |
| `PerformanceLink` | connects produced content to authorized or user-provided performance data | Revenue Learning |
| `ChannelTask` | package/draft/manual/live channel operation request | Publishing, Seller, Affiliate |
| `PublishReceipt` | read-back verified post/listing/upload result | Channel Execution |
| `RevenueLedger` | click/conversion/revenue/channel/content result | Revenue Learning |
| `CostLedger` | LLM, image, video, API, labor, proxy/vendor costs | Revenue Learning / CTO ops |
| `CodeGraphSnapshot` | read-only developer graph of modules/contracts/dependencies | Developer tooling only |

## 7. Differentiation Moat

External tools tend to optimize for "make and post quickly." AI-Content-OS should own "make,
verify, approve, publish, read back, and learn safely."

Moat contracts:

- evidence truth gate;
- human approval gate;
- idempotency key per content/product/channel/period;
- read-back verification before marking published;
- rights provenance for images, music, fonts, review quotes, and screenshots;
- cost ledger by run, variant, model, and channel;
- performance closed loop into Knowledge and Brand DNA;
- fallback-first workflow that blocks unsafe output instead of fabricating claims.

Builderlog-specific defensive line:

- truth/provenance beats generic prompt output;
- actual artifact QA beats "copy this prompt";
- idempotent production runs beat one-off prompt sessions;
- rights and disclosure boundaries beat fast-but-risky reference reuse;
- cost/revenue ledger beats vanity metric scoring;
- human approval and rollback receipts beat silent auto-publishing.

Competitive implication:

`PROPOSED`: We should not compete by copying one-click bots. We should compete by becoming the
operator-safe content and commerce OS that teams can trust with real accounts and repeatable
production.

## 8. 30 / 60 / 90 Day Execution Portfolio

This table is the canonical execution plan that consolidates Builderlog, DAF, MoneyPrinterTurbo,
Manus seller automation, Damagoci, Reels intelligence, and the open-source portfolio analysis.

| Window | Build | Adopt / borrow | Reject / defer | Success metric | Stop criteria |
|---|---|---|---|---|---|
| 30 days | Networkless Sponsored Campaign Compliance Checker; Affiliate Revenue Router contract; Photo-to-Evidence draft schema; ClaimRiskGate for numeric/financial/experience claims; public Prompt Kit and Quality/Failure log | DAF freemium entry pattern; Builderlog build-in-public funnel; existing Trend/Research/Content/CardNews reuse | live publishing, browser automation, external metric ingestion, seller upload | first usable report package, pass/fail/manual status, 3-5 beta audits, zero unverified numeric claims | compliance cannot be represented, briefs stay generic, disclosure policy unclear |
| 60 days | Affiliate Content Kit with domestic/CPA/global route separation; Reels staged harness package; WordPress/manual draft exporter; Cost/Revenue ledger skeleton; Shorts edit package | MoneyPrinterTurbo subtitle/render helper only after license spike; Builderlog weekly brief/RSS cadence | Upload-Post, bundled media, HTML scraping, live API adapters | brief-to-package conversion, publish-ready draft rate, user approval completion, cost per package | provider costs exceed price, rights cannot be proven, no paid intent |
| 90 days | Performance/Revenue feedback loop; official/authorized product and social metric adapters; agency workspace queue; Product Intelligence reports; seller manual/draft payload preflight | official APIs and approved partner data only | unapproved scraping, credentialed browser sessions, mass posting, performance guarantees | paid conversion, repeat workspace use, revenue attribution, measurable time saved | metrics cannot be tied safely, policy gates block key channels, support burden exceeds revenue |

## 8.1 Prior Roadmap Notes

### 30 Days

Objective: package existing engines into the lowest-risk sellable line.

Build:

- AffiliateOpportunity contract.
- ProductSnapshot / OfferSnapshot skeleton with all volatile fields defaulting to `unavailable`.
- Disclosure contract with CTO-gated policy source.
- WordPress draft file exporter, not API.
- CardNews/Shorts package reuse from existing engines.
- CostLedger skeleton.

Stop criteria:

- cannot confirm affiliate disclosure rules;
- output still invents price/rating/review/ranking;
- product evidence cannot be represented without scraping;
- package cannot stay networkless.

### 60 Days

Objective: add draft adapters and selective video helper spike.

Build:

- WordPress draft adapter behind human approval.
- PartnerLinkRegistry for user-provided links.
- ScenePlan / TimedCaption / RenderProfile prototype using clean-room or MIT-reviewed helper code.
- AssetManifest with rights provenance.
- Product Intelligence source adapter design using official APIs only.

Stop criteria:

- WordPress draft cannot be made reversible/read-back verified;
- video helper requires bundled media with unclear rights;
- provider costs exceed package price;
- no paying user for affiliate package.

### 90 Days

Objective: revenue learning and selective live adapters only after gates.

Build:

- RevenueLedger and ConversionFeedbackAdapter.
- official reporting import, if approved.
- read-back verification for WordPress/social.
- seller/affiliate channel router.
- consignment dashboard discovery prototype.

Stop criteria:

- performance data cannot be tied to content without policy/privacy risk;
- live adapters lack rollback or account-owner approval;
- seller automation policy gates remain unresolved;
- support burden exceeds revenue.

## 9. License, Policy, And Security Gates

### 9.1 Open Source Acquisition Policy

Principle:

- `PROPOSED`: AI-Content-OS should not rebuild already-proven generic capabilities when a safe
  open-source acquisition path exists.
- `PROPOSED`: "Public GitHub" is not permission to copy. Before any source, dependency, fork,
  submodule, or vendor import, verify LICENSE, copyright notices, dependency licenses, bundled
  asset rights, security posture, and platform-policy exposure.
- `PROPOSED`: Every external engine must be classified as one of:
  `full fork`, `submodule`, `dependency`, `selective vendoring`, `clean-room rebuild`, or `reject`.
- `PROPOSED`: Current status is research only. No clone, fork, submodule, vendored code, package
  dependency, or copied asset should be added until active QA finishes and the CTO opens a separate
  approved acquisition lane.

Selection rules:

- Prefer `dependency` when the upstream is maintained, narrowly scoped, well licensed, and does
  not bring unsafe UI automation, bundled assets, or credential patterns.
- Prefer `selective vendoring` only for small, stable helper functions where dependency use is
  impractical and LICENSE/NOTICE preservation is easy.
- Prefer `clean-room rebuild` for workflow contracts, policy-sensitive automation, platform
  adapters, credential handling, and business logic that defines AI-Content-OS differentiation.
- Use `reject` for stealth, bot-evasion, false-experience content generation, unapproved scraping,
  unlicensed assets, plaintext production credentials, or automatic live posting without
  read-back/rollback.

Repository acquisition decisions:

- `MoneyPrinterTurbo`: `CONFIRMED`: GitHub labels the repository MIT. `PROPOSED`: do not full fork.
  Consider render/subtitle helpers behind an AI-Content-OS adapter as `dependency` or
  `selective vendoring` only after license review. Preserve LICENSE/NOTICE, record the exact
  upstream commit SHA, and document the functions/classes used. Do not import bundled music, fonts,
  stock assets, Upload-Post integration, plaintext-key config, or the full UI.
- `amazon-cli`: `CTO-PROVIDED`: MIT. `PROPOSED`: production adoption is `NO-GO` if the useful code
  depends on Amazon HTML scraping. Use only parser fixtures and ProductCandidate/OfferSnapshot
  contract references for research. Production must use an official API or approved data provider
  adapter.
- `naver-bc-automation`: `CONFIRMED`: README contains MIT wording, but a formal LICENSE file was
  not independently verified in this pass. `PROPOSED`: no code copy before explicit license
  confirmation. Rebuild only the workflow/contracts clean-room. Stealth, false-experience content,
  session persistence, coordinate/browser auto-publishing, and bot-evasion are permanent exclusion
  candidates.

Acquisition matrix:

| Function | Upstream | License status | 가져올 단위 | 제외 자산/동작 | 보안검사 | Integration adapter | Upgrade strategy | Rollback | CTO gate |
|---|---|---|---|---|---|---|---|---|---|
| Subtitle timing / formatting helper | MoneyPrinterTurbo | `CONFIRMED`: MIT label on GitHub; verify LICENSE before use | `dependency` or `selective vendoring` helper only | bundled fonts/media, UI, Upload-Post | dependency scan, license scan, no plaintext keys | `TimedCaptionAdapter` | pin version or commit SHA; review changelog before bump | remove adapter and use local clean-room fallback | required before code import |
| Render profile helper | MoneyPrinterTurbo | same as above | small helper behind adapter | bundled songs, stock videos/images | asset provenance check, codec dependency review | `RenderProfileAdapter` | pinned upstream SHA, fixture render regression | disable helper, keep package-only output | required before spike |
| Material provider abstraction pattern | MoneyPrinterTurbo | same as above | clean-room contract only | Pexels/Pixabay/Coverr direct defaults without keys/policy | API key handling, rights policy | `AssetProviderAdapter` | provider-by-provider approval | block provider, keep local assets | required before network use |
| Upload/cross-post workflow | MoneyPrinterTurbo Upload-Post | `NO-GO` regardless of repo license until platform approval | none | Upload-Post, live posting, stored platform credentials | credential vault required if ever reconsidered | none now | not applicable | not applicable | CTO explicit approval only |
| ASIN candidate/enrich/cache parser fixtures | amazon-cli | `CTO-PROVIDED`: MIT; repo details unverified here | fixtures/research notes only | production HTML scraping | ToS review, parser-safety review | `ProductCandidateFixtureAdapter` for tests only | no upstream runtime dependency | delete fixture notes | required before any code use |
| Amazon offer data | amazon-cli pattern | license not enough; policy controls | clean-room official API adapter | scraping, fragile DOM selectors | API credential handling, rate-limit controls | `OfferSnapshotAmazonOfficialAdapter` | official API version tracking | disable adapter, mark stale | required before live data |
| Brand/review workflow contract | naver-bc-automation | README MIT wording only; LICENSE not verified | clean-room contract | copied code, stealth, session store, auto-publish | policy review, account-safety review | `ChannelTask` / `Disclosure` / `PublishReceipt` | own contracts only | remove channel package | required before implementation |
| Naver browser automation | naver-bc-automation | irrelevant due policy risk | none | stealth, bot evasion, coordinate/session publishing | prohibited | none | not applicable | not applicable | permanent NO-GO candidate |

If `third_party/` or `vendor/` is approved later, add `THIRD_PARTY_NOTICES.md` before import. It
should include:

- upstream repository URL;
- upstream commit SHA or release version;
- license name and copied LICENSE/NOTICE location;
- files/functions/classes used;
- modifications made;
- transitive dependency summary;
- excluded assets and why;
- security review date;
- CTO approval reference;
- rollback owner and removal steps.

Upstream tracking and fork cost:

- `dependency`: lowest local maintenance, but version drift and supply-chain risk require lockfile,
  vulnerability scan, changelog review, and reproducible fixtures.
- `submodule`: useful only for large upstreams that must remain visibly separate; higher workflow
  friction and review burden. Not recommended for the current three engines.
- `selective vendoring`: best for tiny stable helpers; requires NOTICE preservation, local tests,
  and manual upstream diff review.
- `full fork`: highest maintenance cost and broadest policy/security inheritance. Reject for the
  current three repositories.
- `clean-room rebuild`: highest initial design work but lowest long-term policy and product-risk
  coupling. Preferred for contracts, workflow orchestration, approval gates, and channel adapters.

License gates:

- Verify every external repo license from official GitHub before code reuse.
- Treat README "MIT" as insufficient until LICENSE file is reviewed.
- Do not copy bundled assets, songs, fonts, screenshots, sample media, or generated examples.
- Prefer clean-room contracts over source reuse.

Policy gates:

- Naver terms and account-safety review before any blog automation.
- Coupang/Amazon official product/affiliate API policy review before product data automation.
- TikTok/Instagram/YouTube API and disclosure policy review before upload/post adapters.
- WordPress site ownership and permission review before draft API.

Security gates:

- no plaintext production keys in repo docs/source;
- no long-lived browser sessions without explicit security design;
- no stealth/bot evasion;
- no coordinate-based UI automation for production;
- no automatic live upload without read-back and rollback;
- no external media use without rights provenance.

## 10. Non-Overlapping Follow-Up Lanes

These lanes avoid current active M7/M8/CardNews, Commerce, Shorts, site, storage, and Git conflicts.

### Lane P1: Portfolio Contract Architecture

Owned files:

- new planning doc only, e.g. `docs/PRODUCT_INTELLIGENCE_PLANE_CONTRACTS.md`

No code. Defines `ProductCandidate`, `ProductSnapshot`, `OfferSnapshot`, `AffiliateOpportunity`.

### Lane P2: Affiliate Content Package Design

Owned files:

- new planning doc only, e.g. `docs/AFFILIATE_CONTENT_PACKAGE_CONTRACT.md`

No Commerce seller files. Defines disclosure, link registry, draft package, idempotency.

### Lane P3: Shorts Render Helper Spike Plan

Owned files:

- new research doc only, e.g. `docs/RESEARCH/SHORTS/MONEYPRINTERTURBO_RENDER_SPIKE.md`

No `modules/shorts/**` edits. Focus on license, render profile, captions, asset rights.

### Lane P4: Channel Execution Safety Spec

Owned files:

- new planning doc only, e.g. `docs/CHANNEL_EXECUTION_SAFETY_SPEC.md`

No Publishing code. Defines package/draft/manual/live adapters, read-back verification, rollback.

### Lane P5: Revenue Learning Ledger Spec

Owned files:

- new planning doc only, e.g. `docs/REVENUE_LEARNING_LEDGER_SPEC.md`

No Performance code. Defines `RevenueLedger`, `CostLedger`, attribution, data-retention gates.

## 11. CTO Handoff

Decision:

`Build` the AI-Content-OS four-layer portfolio.

`Borrow selectively` from external repositories at the pattern level.

`Clean-room rebuild` all contracts, data models, adapters, approvals, and ledgers.

`Reject` direct automation behavior that depends on stealth, session persistence, unapproved
scraping, bundled media, plaintext production keys, or direct cross-post/upload defaults.

Recommended first paid product:

```text
Affiliate Content Factory Phase A
```

Why:

- highest reuse of existing engines;
- lowest platform-side-effect risk;
- immediate packaging value;
- naturally extends into CardNews, Shorts, SEO, and Performance later;
- avoids seller-listing policy risk while Commerce remains under QA/gates.

Next CTO action:

Approve Lane P2 as a planning-only Sprint, then decide whether Phase A should become the first
monetization build lane.
