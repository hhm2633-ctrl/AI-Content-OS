# Damagoci Coupang Partners Benchmark

Date: 2026-07-12

Scope: public-page competitive analysis only. No login, signup, payment, API call, private-page
inspection, code change, or storage output was performed.

Important boundary: Damagoci's Coupang-related service is analyzed here as **Coupang Partners
affiliate review content + WordPress publishing automation**, not seller product upload. Do not
merge this with the AI-Content-OS Commerce seller-listing lane.

Legend:

- `CONFIRMED`: directly observed from public pages or current AI-Content-OS contracts.
- `INFERRED`: derived from observed claims and likely workflow shape, not directly verified behind
  login.
- `UNKNOWN`: hidden behind login, unavailable from public official text, or requires policy/account
  verification.
- `CTO GATE`: must be verified or approved by CTO before implementation.

## 1. Sources Checked

`CONFIRMED`: Damagoci public pages checked:

- `https://damagoci.com/about`
- `https://damagoci.com/coupang`
- `https://damagoci.com/guide`
- `https://damagoci.com/terms`
- `https://damagoci.com/privacy`

`CONFIRMED`: Coupang Partners official public portal checked:

- `https://partners.coupang.com/`

`UNKNOWN`: Coupang Partners official operating-policy text was not confirmed in this pass. The
official portal returned a JavaScript app shell in the text fetch. Any detailed Coupang Partners
policy claims, disclosure wording, prohibited promotion rules, API allowances, or WordPress
automation permissions remain `CTO GATE`.

## 2. Publicly Confirmed Damagoci Positioning

`CONFIRMED`: Damagoci describes itself as an AI blog automation platform that maximizes productivity
with AI and automation tools.

`CONFIRMED`: The public about page states that Gemini AI automatically generates keyword-based
content and automatically publishes it to WordPress.

`CONFIRMED`: The same page lists a Coupang Partners automation service described as keyword-based
Coupang product review article generation and WordPress publication.

`CONFIRMED`: The public terms define the service as a marketing automation integrated dashboard and
list Coupang Partners automation, Google advertising AI auto-posting, Naver API automatic plugin,
and SEO content automation among provided services.

`CONFIRMED`: The privacy page says optional linked service account information may include a Coupang
Partners ID and WordPress site URL, and says users may directly input information when integrating
APIs.

`CONFIRMED`: `https://damagoci.com/coupang` redirects to login. Detailed in-product Coupang
workflow, product search UI, generated output, WordPress connection flow, and performance dashboard
are not publicly visible.

`CONFIRMED`: The public guide page currently shows service-specific guides, including Coupang
Partners automation, as preparing/coming soon.

## 3. Public Feature Map

| Feature | Status | Evidence |
|---|---|---|
| AI blog automation platform | `CONFIRMED` | About page positioning |
| Keyword research / SEO-oriented writing | `CONFIRMED` | About page says keyword research to SEO optimization |
| Gemini AI content generation | `CONFIRMED` | About page names Gemini AI |
| WordPress automatic publishing | `CONFIRMED` | About page states automatic WordPress publishing |
| Coupang Partners review article generation | `CONFIRMED` | About page service card |
| Coupang Partners dashboard details | `UNKNOWN` | `/coupang` redirects to login |
| Product selection logic | `UNKNOWN` | hidden behind login |
| Evidence collection for product facts | `UNKNOWN` | hidden behind login |
| Affiliate disclosure insertion | `UNKNOWN` | not confirmed in public pages |
| Performance ledger/dashboard | `UNKNOWN` | not confirmed publicly |
| API credentials / integrations | `INFERRED` | privacy page mentions linked service accounts and direct API input |

## 4. Expected Flow

`INFERRED`: Damagoci's likely flow is:

```text
keyword
-> product candidate search/selection
-> product fact/evidence gathering
-> AI review article generation
-> affiliate disclosure insertion
-> affiliate link attribution
-> WordPress draft or publish
-> performance/event ledger
```

`UNKNOWN`: Whether the service creates WordPress drafts first or publishes immediately.

`UNKNOWN`: Whether users approve the article before WordPress publication.

`UNKNOWN`: Whether product data is pulled from Coupang Partners official surfaces, Coupang retail
pages, user-provided URLs, cached data, or another data provider.

`UNKNOWN`: Whether generated review text is constrained to sourced product facts or can invent
experience-like copy.

## 5. Comparison With AI-Content-OS

### 5.1 Research

`CONFIRMED`: AI-Content-OS has Research modules and evidence/fallback work under active governance.

`PROPOSED`: Affiliate content should reuse Research for keyword intent, product evidence summaries,
source freshness, and conflict notes.

Gap:

- AI-Content-OS does not yet have an approved Coupang Partners product-data source.
- Product facts, ratings, review counts, price, discount, stock, and ranking must remain
  `unavailable` until verified.

### 5.2 Content

`CONFIRMED`: AI-Content-OS Content output already feeds CardNews and Publishing.

`PROPOSED`: Affiliate review content can reuse Content structure only after a stricter product
evidence contract is introduced.

Gap:

- Existing general content generation is not enough for affiliate claims.
- The content engine must not generate first-person usage claims unless the user supplies verified
  firsthand experience.

### 5.3 Publishing

`CONFIRMED`: AI-Content-OS Publishing is manual-oriented and must not mark prepared content as
published. The publishing skill requires keeping `upload_mode: manual` unless real API authorization
is explicitly approved.

`PROPOSED`: WordPress integration should begin as `WordPress draft package`, not auto-publish.

Gap:

- No approved WordPress credential storage, draft API integration, rollback, or audit log exists.

### 5.4 Performance

`CONFIRMED`: AI-Content-OS has local quality/performance scoring, but real platform performance
requires external APIs and is separately gated.

`PROPOSED`: Affiliate content should track a ledger with article ID, product IDs, link IDs, source
freshness, disclosure hash, WordPress draft/publish status, and later clicks/conversions only when
official partner reporting is approved.

### 5.5 Commerce

`CONFIRMED`: AI-Content-OS Commerce Phase 1 is a seller-side manual package generator for
SmartStore/Coupang. It explicitly does not create or publish affiliate links, does not call
marketplace APIs, and is not wired into WorkflowEngine.

`PROPOSED`: Do not extend the seller Commerce lane for Damagoci-style affiliate articles. Create a
separate Affiliate Content lane if approved.

## 6. Existing Engine Reuse Map

Core question: **What can AI-Content-OS sell or monetize with the engines already being built,
without creating a mostly new product?**

Answer: `PROPOSED`: AI-Content-OS can package its existing trend, research, content, card-news,
shorts, publishing, performance, knowledge, and truth-gate capabilities into an Affiliate Content
product line. The new work should be a thin contract/adapter layer, not a new generation engine.

| Existing engine / contract | Reuse in Affiliate Content lane | New requirement |
|---|---|---|
| Trend Collector | `PROPOSED`: detect purchase-intent topics, seasonal product themes, gift/holiday demand, problem-solution product categories, and community pain points that can become affiliate content candidates | Add product-intent classification and block non-commercial sensitive topics |
| Research Intelligence | `PROPOSED`: collect product facts, comparison evidence, pros/cons, price/stock freshness status, and source conflict notes | Add approved product source adapters and freshness TTL |
| Content | `PROPOSED`: generate SEO reviews, comparison posts, recommendation articles, buying guides, FAQ, and neutral CTA copy | Add affiliate-safe copy rules: no fabricated experience, no unsupported ranking/discount claims |
| CardNews | `PROPOSED`: turn product evidence into affiliate product card news for Instagram/manual posting | Add affiliate disclosure block and product fact badges |
| Shorts | `PROPOSED`: create product intro Shorts/Reels editing packages from the same evidence snapshot | Add affiliate script disclosure and asset-rights checklist |
| Publishing | `PROPOSED`: produce WordPress draft packages, Instagram caption packages, manual upload checklists, and channel-specific publish queues | Add WordPress draft exporter and affiliate link/disclosure placement checks |
| Performance | `PROPOSED`: track clicks, conversions, revenue, article age, and content format feedback once official reporting source exists | Add RevenueLedger and ConversionFeedbackAdapter |
| Knowledge / Brand DNA | `PROPOSED`: learn channel tone, product category language, reusable hooks, CTA patterns, and what formats convert without inventing claims | Add affiliate-specific banned claims and disclosure memory |
| Commerce truth gate | `PROPOSED`: reuse truth/source/freshness/rights gates to block false prices, fake reviews, unverified rankings, stale stock, and unsupported product claims | Keep separate from seller upload; expose as `AffiliateTruthGate` contract wrapper |

`PROPOSED`: The saleable product is not "Coupang seller automation." It is:

```text
verified affiliate content packages
-> SEO article
-> comparison/landing page
-> card news
-> Shorts package
-> WordPress/Instagram/manual publishing package
-> performance feedback loop
```

## 7. Monetization Products

| Product | Revenue model | Needed input | Reused modules | Minimum new modules | External API | Policy gate | Expected operating cost |
|---|---|---|---|---|---|---|---|
| Coupang Partners SEO article | Subscription, per-article credits, agency package | Keyword, product URL or candidate list, affiliate link/account owner, product facts | Trend, Research, Content, Publishing, Knowledge, Commerce truth gate | `AffiliateProductCandidate`, `AffiliateDisclosure`, `PartnerLinkRegistry`, `WordPressDraftExporter` | Optional later: Coupang Partners/reporting, WordPress draft API | Official affiliate disclosure, product data source, WordPress ownership | Low in Phase A; medium if live product data/API added |
| Comparison / recommendation landing content | Subscription tier, lead-gen package, niche-site package | 2+ products, comparison criteria, target audience, evidence snapshot | Research, Content, CardNews, Publishing, Performance, Knowledge | `AffiliateProductCandidate`, comparison evidence schema, landing-page draft exporter | Optional WordPress/Page builder API | Ranking/comparison claim rules, affiliate disclosure, image rights | Low-medium; evidence verification is the main cost |
| Affiliate card news | Content pack sales, monthly SNS package | Product evidence, approved images or neutral generated visuals, affiliate disclosure | CardNews, Content, Research, Publishing, Brand DNA | CardNews affiliate badge/disclosure contract, product card schema | None in Phase A; optional Instagram Graph later | Image rights, disclosure placement, no fake review/ranking | Low if using manual image/evidence; medium with asset sourcing |
| Affiliate Shorts/Reels | Editing package sales, upsell from SEO/card pack | Product evidence, script angle, licensed assets, affiliate disclosure | Shorts, Content, Research, Publishing, Brand DNA | Affiliate script disclosure, product asset checklist | None in Phase A; optional TTS/video/social API later | Music/asset rights, disclosure in video/caption, no fake experience | Low for script/edit package; high if rendering/TTS/video automation |
| Seller-facing detail-page SaaS | SaaS subscription, per-SKU package | Seller-provided product facts, images, notices, claims, source documents | Commerce Phase 1 truth gate, Research, Content, CardNews optional | Product intake UI/contract, merchant evidence uploader | Seller APIs only after separate CTO gate | Seller data rights, platform listing rules, no real upload by default | Medium; support and fact verification cost high |
| Wholesale/operator dashboard bundle | B2B subscription, managed-service ops | Supplier catalog/export, product evidence, affiliate/seller channel choice | Trend, Research, Commerce truth gate, Publishing, Performance | Catalog importer, channel router, RevenueLedger, operations queue | Optional supplier feed, WordPress, partner reporting | Supplier terms, product rights, PII/credential handling | Medium-high; integration and support heavy |

`PROPOSED`: The lowest-cost launchable product is a networkless Affiliate Content Package. It can
use user-provided product URLs/facts and produce draft copy + card/shorts scripts + manual
publishing checklist without calling Coupang, WordPress, or social APIs.

## 8. Minimum New Build

`PROPOSED`: Build only thin contracts around existing engines first.

### 8.1 AffiliateProductCandidate

Purpose: normalize a product candidate without pretending to know unavailable facts.

Contract sketch:

```json
{
  "candidate_id": "affiliate_candidate_001",
  "keyword": "camping cooler",
  "product_ref": {
    "input_type": "user_url | user_text | approved_feed | unknown",
    "locator": "redacted_or_public_url",
    "source_id": "source_001"
  },
  "facts": {
    "name": {"value": "unavailable", "source_ids": []},
    "brand": {"value": "unavailable", "source_ids": []},
    "price": {"value": null, "volatile": true, "expires_at": null},
    "stock": {"value": null, "volatile": true, "expires_at": null},
    "rating": {"value": null, "volatile": true, "expires_at": null}
  },
  "eligibility": {
    "content_allowed": false,
    "blocked_reasons": ["missing_product_source"]
  }
}
```

### 8.2 AffiliateDisclosure

Purpose: make disclosure mandatory, hash-bound, and policy-source-bound.

Fields:

- `policy_source`
- `disclosure_text`
- `placement`
- `channel`
- `hash`
- `verified_at`
- `expires_at`

`CTO GATE`: official Coupang Partners disclosure source must be confirmed before filling live text.

### 8.3 PartnerLinkRegistry

Purpose: track affiliate links without hiding ownership or attribution.

Fields:

- `link_id`
- `partner_account_owner`
- `destination_product_ref`
- `created_at`
- `source_method`
- `disclosure_hash`
- `status`
- `blocked_reasons`

`PROPOSED`: Phase A can accept user-provided links only. Do not generate links automatically.

### 8.4 WordPressDraftExporter

Purpose: create a draft package first; API posting comes later.

Fields:

- `draft_mode: file_package | wordpress_api_draft`
- `auto_publish_performed: false`
- `title`
- `body_html_path`
- `affiliate_links`
- `disclosure_hash`
- `approval_required`
- `idempotency_key`

### 8.5 RevenueLedger

Purpose: unify performance learning without fabricating results.

Fields:

- `content_id`
- `channel`
- `affiliate_link_ids`
- `published_at`
- `clicks`
- `conversions`
- `revenue`
- `source`
- `last_synced_at`

Default values must be `unavailable` until official data exists.

### 8.6 ConversionFeedbackAdapter

Purpose: convert approved performance data into Knowledge/Brand DNA/Performance learning.

Inputs:

- RevenueLedger rows
- content metadata
- product category
- channel
- disclosure status

Outputs:

- pattern performance notes
- hook/CTA/category feedback
- product category exclusions
- stale-data warnings

`CTO GATE`: no clicks/conversions/revenue import without account ownership and official reporting
source approval.

## 9. Phased ROI

| Phase | Scope | Expected value | Risk | Prerequisites | Stop condition |
|---|---|---|---|---|---|
| Phase A: networkless affiliate content package | User-provided keyword/product facts/link; generate SEO article, card copy, Shorts script, manual publish checklist; no external calls | Fastest monetizable package; validates demand with minimal build | Medium: bad user-provided facts, disclosure uncertainty | Affiliate contract, disclosure placeholder policy, truth gate, manual review | Stop if official disclosure cannot be confirmed or outputs still invent claims |
| Phase B: user-provided affiliate link + WordPress draft | User enters partner link and WordPress site; exporter creates draft package or API draft after approval | Higher utility; closer to Damagoci workflow without full automation | High: credential handling, draft/publish confusion, link ownership | WordPress draft-only approval, secret handling, content hash approval | Stop if WordPress API/storage cannot be made draft-only and reversible |
| Phase C: official API/policy verified product data | Approved source supplies product facts, price/stock freshness, images/rights status | Better quality, less manual work, scalable product comparisons | Critical: policy/account/API risk | Coupang Partners official policy, product data source approval, image rights, rate limits | Stop if source cannot legally support product facts/images or freshness SLA |
| Phase D: clicks/conversions/revenue learning | RevenueLedger imports official performance data into Performance/Knowledge/Brand DNA | Compounding moat; learns which formats convert | High: PII/account reporting, misleading ROI claims | Official reporting access, account owner approval, privacy/retention rules | Stop if data cannot be attributed safely or conversion data is too sparse/noisy |

`PROPOSED`: Phase A is the only immediate build candidate. Phase B is a narrow integration Sprint.
Phase C/D require official-source gates and should not be bundled with Phase A.

## 10. Core Monetization Answer

Question: **현재 개발 중인 엔진을 이용하면 무엇을 거의 새로 만들지 않고 팔거나 수익화할 수 있는가?**

Answer:

`PROPOSED`: AI-Content-OS can sell an **Affiliate Content Package Generator** with almost no new
generation engine work. The existing engines already cover most value creation:

- Trend finds timely product/article angles.
- Research turns user-provided or approved product facts into evidence snapshots.
- Content writes SEO review/comparison/FAQ drafts.
- CardNews creates social product cards.
- Shorts creates short-form editing packages.
- Publishing prepares WordPress/Instagram/manual publishing packages.
- Performance/Knowledge/Brand DNA can learn what works later.
- Commerce truth gates prevent false commercial claims.

The missing product is not another AI writer. The missing product is a **policy-safe affiliate
packaging contract**:

```text
AffiliateProductCandidate
+ AffiliateDisclosure
+ PartnerLinkRegistry
+ WordPressDraftExporter
+ RevenueLedger
+ ConversionFeedbackAdapter
```

This is small enough to build in stages and valuable enough to sell as:

- "쿠팡파트너스 SEO 글 패키지"
- "상품 비교/추천 랜딩 초안"
- "제휴 카드뉴스 세트"
- "제휴 Shorts/Reels 편집 패키지"
- "판매자 상세페이지/제휴 콘텐츠 동시 생성 패키지"

`PROPOSED`: The positioning should be "verified affiliate content operations," not "automatic
posting bot." That gives AI-Content-OS a safer product than Damagoci-style fully automatic
WordPress publishing while still preserving the monetization upside.

## 11. Reusable Contracts

### 11.1 Affiliate Disclosure

`PROPOSED`: Every affiliate artifact must include a disclosure contract:

```json
{
  "affiliate_disclosure": {
    "required": true,
    "policy_source": "CTO_GATE_OFFICIAL_COUPANG_PARTNERS_POLICY",
    "disclosure_text": "unavailable_until_policy_confirmed",
    "placement": "before_first_affiliate_link",
    "hash": "sha256:...",
    "verified_at": null
  }
}
```

`CTO GATE`: Confirm official Coupang Partners disclosure wording and placement rules before any
customer-facing output is generated.

### 11.2 Product Evidence

`PROPOSED`: Product evidence must be source-backed:

```json
{
  "product_evidence": {
    "product_id": "opaque_or_user_supplied",
    "product_name": {"value": "unavailable", "source_ids": []},
    "price": {"value": null, "volatile": true, "expires_at": null},
    "discount": {"value": null, "volatile": true, "expires_at": null},
    "stock": {"value": null, "volatile": true, "expires_at": null},
    "rating": {"value": null, "volatile": true, "expires_at": null},
    "review_count": {"value": null, "volatile": true, "expires_at": null},
    "images": [],
    "blocked_claims": []
  }
}
```

### 11.3 Price Freshness

`PROPOSED`: Price, discount, stock, shipping, rating, review count, and ranking are volatile and
must have `verified_at`, `expires_at`, and a source. Stale values must be omitted or replaced with
"check current price on Coupang" style neutral copy.

### 11.4 Link Attribution

`PROPOSED`: Each affiliate link needs:

- owner account;
- generated link ID or source URL;
- destination product ID;
- disclosure hash;
- generation time;
- WordPress article/draft ID;
- click/conversion ledger fields only after official reporting approval.

### 11.5 WordPress Draft

`PROPOSED`: Start with `draft_only`:

```json
{
  "wordpress_output": {
    "mode": "draft_only",
    "auto_publish_performed": false,
    "draft_id": null,
    "title": "...",
    "body_path": "storage/affiliate/<request_id>/wordpress_draft.html",
    "approval_required": true
  }
}
```

`CTO GATE`: WordPress API credentials, site ownership, draft permissions, and rollback/delete
behavior must be approved before implementation.

### 11.6 Human Approval

`PROPOSED`: Human approval must bind to:

- content hash;
- affiliate disclosure hash;
- product evidence snapshot hash;
- link attribution hash;
- WordPress draft payload hash;
- expiry.

### 11.7 Idempotency

`PROPOSED`: Affiliate idempotency key:

```text
{period}:affiliate_content:{keyword_hash}:{product_set_hash}:{wordpress_site_hash}:{template_version}
```

This prevents duplicate SEO spam and repeated publication for the same keyword/product set.

### 11.8 Performance Feedback

`PROPOSED`: Performance ledger starts empty and local:

```json
{
  "performance_ledger": {
    "article_id": null,
    "wordpress_status": "draft_only",
    "affiliate_clicks": "unavailable",
    "conversions": "unavailable",
    "revenue": "unavailable",
    "source": "not_connected"
  }
}
```

`CTO GATE`: No clicks, conversion, revenue, ranking, or ROI claims without official reporting source
and account ownership.

## 12. Risk Register

| Risk | Severity | Notes |
|---|---:|---|
| Fabricated user experience | Critical | AI must not write "I used this" unless verified first-party experience exists |
| False price/discount/stock | Critical | Volatile facts require source and freshness expiry |
| False ranking/bestseller claims | High | Ranking must be sourced and current |
| Review count/rating hallucination | High | Use `unavailable` without verified source |
| Copyright image misuse | High | Product images need allowed source/permission; hotlink/copy rules require policy review |
| Affiliate disclosure omission | Critical | Official policy text not confirmed in this pass; CTO gate |
| SEO mass-generation spam | High | Idempotency, scheduling caps, duplicate checks, and quality thresholds required |
| WordPress credential leak | High | Needs secret storage design; never store in docs or source |
| Auto-publish without review | High | Start with draft/manual approval |
| Coupang Partners account suspension | High | Policy and account ownership must be verified before any automation |

## 13. Direct Competition / Buy / Build ROI

### Direct Competition

`CONFIRMED`: Damagoci competes with a future AI-Content-OS affiliate-content lane, not the current
seller Commerce lane.

`INFERRED`: Its apparent strength is a focused keyword-to-WordPress automation path for Korean blog
monetization users.

### Buy / Use Damagoci

Potential upside:

- faster learning from a live competitor workflow;
- possibly lower short-term cost than building WordPress and affiliate integrations.

Risks:

- login-only workflow is opaque;
- product evidence quality is unknown;
- affiliate disclosure and policy handling are unknown;
- data/account export and lock-in are unknown.

### Build In AI-Content-OS

Potential upside:

- stronger truth/freshness gates;
- reusable Research/Content/Publishing/Performance contracts;
- better audit ledger and human approval;
- less risk of mixing affiliate content with seller upload.

Cost:

- requires official Coupang Partners policy review;
- requires approved product-data source;
- requires WordPress draft integration design;
- requires affiliate disclosure/link ledger;
- requires performance reporting integration only after account approval.

CTO ROI view:

`PROPOSED`: Do not implement full automation now. The highest ROI next step is a small Affiliate
Content architecture/contract Sprint, not a build Sprint.

## 14. Affiliate Content Lane Recommendation

`PROPOSED`: Create a separate lane:

```text
Affiliate Content Lane
```

Do not call it Commerce Phase 2 or seller Commerce.

Initial scope:

1. Product evidence contract.
2. Affiliate disclosure contract.
3. WordPress draft package contract.
4. Human approval gate.
5. Idempotency + ledger.
6. No auto-publish.
7. No Coupang API/Partners reporting connection until CTO gate.

Out of scope:

- seller product upload;
- inventory/price update;
- order/shipping;
- browser automation;
- mass SEO posting;
- real affiliate link publishing without official policy confirmation.

## 15. CTO Gates

Required before implementation:

1. Confirm official Coupang Partners operating policy, disclosure wording, prohibited channels, and
   automation/API boundaries from official source.
2. Confirm user-owned Coupang Partners account and allowed link-generation method.
3. Confirm product-data source and image-use rights.
4. Confirm WordPress site ownership and draft-only API credentials.
5. Approve affiliate disclosure placement and immutable hash.
6. Approve idempotency and anti-spam posting limits.
7. Approve human review workflow before publish.
8. Approve performance reporting source before recording clicks/conversions/revenue.

## 16. CTO Decision

Decision: `ROADMAP / NARROW SCOPE / BUILD PHASE A FIRST`.

Rationale:

- `CONFIRMED`: Damagoci's public pages indicate a real competitive direction around AI-generated
  Coupang Partners review articles and WordPress publishing.
- `CONFIRMED`: The detailed `/coupang` service is login-only, so implementation details are
  unknown.
- `CONFIRMED`: AI-Content-OS seller Commerce Phase 1 is not the right lane; it forbids affiliate
  links and real platform actions.
- `PROPOSED`: A separate Affiliate Content lane can reuse Trend/Research/Content/CardNews/Shorts/
  Publishing/Performance/Knowledge/Brand DNA and Commerce truth gates without polluting seller
  Commerce.
- `PROPOSED`: The first sellable product is a networkless Affiliate Content Package Generator:
  SEO article + comparison copy + card-news copy + Shorts script + manual publishing checklist
  from user-provided or approved facts.
- `CTO GATE`: Official Coupang Partners policy must be verified before any generated affiliate
  content or WordPress automation is built.

Next step:

`PROPOSED`: Draft `AFFILIATE_CONTENT_CONTRACT.md` as a planning document, then implement only
Phase A after CTO approval. Do not implement WordPress API, Coupang Partners API/reporting,
auto-publish, or performance import until later gates close.
