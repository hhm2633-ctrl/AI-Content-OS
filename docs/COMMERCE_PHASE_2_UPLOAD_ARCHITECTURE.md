# Commerce Phase 2 — Upload Architecture and Official API Research

Author: Claude Commerce Architecture Specialist
Status: **RESEARCH + DESIGN DRAFT. No code, tests, `site/`, storage, credentials, seller accounts,
or shared status document touched. No API key issued. No product/order operation performed.**

Legend: `CONFIRMED` = an official-domain page/document was located and its stated content is
treated as fact. `UNKNOWN` = no official-domain confirmation obtained. `PROPOSAL` = architecture
suggestion, not built. `CTO GATE` = requires explicit CTO approval before implementation.
`BLOCKED` = cannot proceed under current conditions.

---

## 0. Research Methodology and a Confirmed Access Limitation

`CONFIRMED` (observed directly in this session, not a claim about the platforms — a claim about
this research environment): direct page fetches to both primary official domains failed in this
environment —

- `apicenter.commerce.naver.com` — every direct fetch attempt returned "Claude Code is unable to
  fetch from apicenter.commerce.naver.com" (domain-level block in this tool environment, not a
  site error).
- `developers.coupangcorp.com` — every direct fetch attempt returned HTTP 403 (bot/anti-scraping
  protection on the Zendesk-hosted help-center pages).
- `web.archive.org` was also unreachable in this environment, so no archived-snapshot fallback was
  available either.

**What this means for every `CONFIRMED` tag below**: I was not able to directly read full primary
source text for either platform's Commerce API. Every fact below is instead **`CONFIRMED` in a
calibrated sense** — I verified that an official-domain page exists (exact title + exact URL,
returned directly by search results, not invented) covering that capability, and I report what
search-engine synthesis of that page's indexed content states. I did **not** verbatim-quote full
payload schemas, exact field lists, or exact numeric limits unless a search result's own summary
stated them explicitly. Any fact sourced only from a blog/agency/reseller site (e.g. `esellers.co.kr`,
`plto.com`, `ezadmin.co.kr`, `winselling.co.kr`, `next-engine.co.kr`, `behalfkr.com`,
`pearsonp.com`, `geekseller.com`, `sidesaram.com`, `bati.ai`, `sagein.net`, `newstruck.net`,
`codedosa.com`, `sir.kr`, `coudae.info`) is explicitly marked `UNKNOWN` per the task's rule — not
used as evidence — and reported separately, only as a directional pointer, never as fact.

`CTO GATE` (methodology, applies to every section below): **before any Phase 2A/2B implementation
work begins, a human with normal authenticated browser access must directly re-open every cited
URL below and confirm the paraphrased content matches the real page.** This document is a
research starting point assembled under an access constraint, not a substitute for that direct
read. Where a search result explicitly quoted a specific technical detail (e.g. an exact error
code, an exact endpoint name), it is marked `CONFIRMED` with higher confidence and the source
URL; where only a general capability was implied, it is marked `CONFIRMED (existence only)` with
a note that field-level detail is `UNKNOWN`.

One official-channel exception worth noting: `github.com/commerce-api-naver/commerce-api` is
Naver's own official GitHub organization for Commerce API technical support (`CONFIRMED` directly
— its README states this explicitly, and it links to `apicenter.commerce.naver.com` as the
canonical doc site). Facts sourced from **Discussions threads in that specific official
repository** are treated as `CONFIRMED (official channel)`, distinct from third-party blogs, even
though a GitHub Discussion is Q&A-style rather than formal documentation.

---

## 1. Naver SmartStore — Naver Commerce API

### 1.1 Official Commerce API Existence

`CONFIRMED`. The **Naver Commerce API Center** (네이버 커머스API센터) is the official developer
portal at `https://apicenter.commerce.naver.com`, with an official technical-support GitHub
organization at `https://github.com/commerce-api-naver/commerce-api` (Discussions: 공지사항,
릴리즈 노트, 묻고 답하기; Wiki: service-level usage guide manuals). Source:
`github.com/commerce-api-naver/commerce-api` README, retrieved 2026-07-11.

`CONFIRMED (existence only)`: search results consistently describe this as *"온라인 쇼핑몰 운영에
필요한 대부분의 작업(주문 조회, 상품 관리, 재고 갱신, 배송 처리 등)을 외부 시스템에서 제어할 수
있도록 제공되는 공식 API"* — i.e. it covers product management, order inquiry, inventory update,
and shipping processing as one integrated API surface (not separate products). Confirmed URL:
`apicenter.commerce.naver.com`, retrieved via search 2026-07-11.

### 1.2 Seller Account and Application (App) Registration Requirements

`UNKNOWN` (sourced only from third-party guides — `esellers.co.kr`, `sidesaram.com`,
`guide.bati.ai` — not from `apicenter.commerce.naver.com` or the official GitHub directly; per
task rule, not treated as fact). Reported third-party claims for the record only, **not relied
upon**:

- A claim that Commerce API access requires the store's "통합매니저" (Integrated Manager) role.
- A claim of a registration flow: API Center sign-up → developer-account/company-name entry →
  application registration (with IP allow-listing and "API group" selections) → issuance of an
  application ID/secret.
- A claim that at most one application can be registered per store, and that periodic
  re-authentication of the store application + IP re-registration is required.

`CTO GATE`: confirm the actual seller/app registration requirements by direct read of
`apicenter.commerce.naver.com` (this document's §0 access-limitation gate) before assuming any of
the above.

### 1.3 Authentication Method (OAuth or Other)

`UNKNOWN` (sourced only from third-party technical blogs, not from an official domain in this
research pass — no official-domain hit was returned for the specific auth mechanism query).
Reported third-party claims for the record only, **not relied upon** as CONFIRMED:

- A claim that token issuance uses an OAuth2.0 `client_credentials`-shaped grant against
  `https://api.commerce.naver.com/external/v1/oauth2/token`.
- A claim of a **non-standard "전자서명" (electronic signature) requirement layered on top of
  OAuth2.0**: `client_id` and a `timestamp` are concatenated, hashed with `bcrypt`, and
  base64-encoded to form a `client_secret_sign` value, submitted alongside `client_id`,
  `timestamp`, `grant_type=client_credentials`, and `type` as query parameters.

This is a specific enough technical claim (a non-standard signature scheme layered on OAuth2) that
it is plausible and *not* the kind of thing casually invented by multiple independent technical
blog authors — but it was not confirmed against an official domain in this research pass, so it
remains `UNKNOWN` under the task's evidentiary rule. `CTO GATE`: this exact signature algorithm
must be confirmed against `apicenter.commerce.naver.com`'s formal auth documentation before any
Phase 2B code writes a single line of signing logic — an incorrect signature algorithm is a
hard integration blocker, not a cosmetic risk.

### 1.4 Product Registration / Modification API

`CONFIRMED (official channel)`, via `github.com/commerce-api-naver/commerce-api` Discussions
(#246, #2127), retrieved 2026-07-11: a product-registration API exists; required inputs discussed
include product name, sale price, stock quantity, and category ID, plus shipping method/shipping
fee type. A "전체 카테고리 조회 API" (full category lookup API) exists to resolve valid category
IDs before registration. Detail content is submitted as an HTML string within JSON, with
JSON-significant characters (e.g. quotes) requiring escaping.

`UNKNOWN`: exact endpoint paths, exact required/optional field enumeration, exact request/response
schema. Not available from this research pass' sources.

### 1.5 Option / Price / Stock API

`CONFIRMED (existence only)`: product registration inputs include price and stock quantity
(§1.4). `UNKNOWN`: whether option/price/stock have **dedicated separate update endpoints**
(distinct from the create/modify product endpoint) — Coupang's API is `CONFIRMED` to separate
these (§2.5); whether Naver Commerce API does the same is `UNKNOWN` from this research pass.

### 1.6 Image Upload Method

`UNKNOWN` (the only specific claim found — representative/optional image fields as URL inputs —
came from `coudae.info`, a third-party tool vendor's manual, not an official domain; per task
rule, not treated as fact). `CTO GATE`: confirm actual image upload mechanism (URL reference vs.
binary multipart upload vs. a dedicated image-hosting API) against official documentation before
any Phase 2A payload design assumes a specific mechanism.

### 1.7 Notice Information (고시정보) and Category-Required Fields

`UNKNOWN`. No official-domain source was returned in this research pass enumerating the specific
notice-information fields per category. `CONFIRMED (existence only)`: a category lookup API
exists (§1.4) that is the likely mechanism for resolving category-specific requirements, by direct
analogy to Coupang's confirmed Category Metadata Query API (§2.7) — but this is an **inference by
platform-pattern analogy, not a confirmed Naver-specific fact**, and is labeled as such.

### 1.8 Order Collection API

`CONFIRMED (existence only)`: an order-collection/inquiry capability exists — search results
reference a "상품주문 조회" concept and note that orders collected via the API include newly
paid/settled orders and orders in "배송 준비" (preparing shipment) status. Source: search
synthesis citing the official GitHub Discussions org and `apicenter.commerce.naver.com`, retrieved
2026-07-11. `UNKNOWN`: exact endpoint name, pagination/polling model, exact order-state
enumeration.

### 1.9 Dispatch / Shipping / Invoice (송장) Processing API

`CONFIRMED (official channel)`, via GitHub Discussion #1646 in the official
`commerce-api-naver/commerce-api` org, retrieved 2026-07-11: a "Modified Product Order History
Search"-type API exists, queryable with a `lastChangedType` parameter (e.g. a `DISPATCHED` value)
to retrieve orders for which dispatch/invoice-number entry has been completed — i.e. dispatch
processing and its confirmation are both API-addressable. `UNKNOWN`: the exact formal endpoint
name/path and the exact invoice-registration request schema.

### 1.10 Cancel / Exchange / Return API

`CONFIRMED (official channel)`, via GitHub Discussion #1431 in the official
`commerce-api-naver/commerce-api` org, retrieved 2026-07-11: order-detail inquiry provides
cancel/return/exchange claim information, and the API surface supports at least: return approval,
return hold, return-hold release, return rejection (withdrawal), exchange pickup-completion,
exchange re-shipment processing, exchange hold, exchange-hold release, and exchange rejection
(withdrawal). `UNKNOWN`: exact endpoint names/payloads.

### 1.11 Rate Limits and Error Handling

`CONFIRMED (official channel)`, via GitHub Discussions #6, #1538, #1648 in the official
`commerce-api-naver/commerce-api` org, retrieved 2026-07-11:

- Exceeding the call limit returns an error with code `GW.RATE_LIMIT` and message "요청이 많아
  서비스를 일시적으로 사용할 수 없습니다" (paraphrased: "too many requests, service temporarily
  unavailable"), surfaced as HTTP 429.
- Naver Commerce API applies a **token bucket rate-limiting algorithm**, per tier, capping calls
  processable per second; excess requests are rejected.
- HTTP 429 responses include `GNCP-GW-RateLimit-*`/`GNCP-GW-Quota-*` prefixed headers (e.g.
  `GNCP-GW-RateLimit-Burst-Capacity`, `GNCP-GW-RateLimit-Replenish-Rate`,
  `GNCP-GW-RateLimit-Remaining`), i.e. the actual numeric limit is discoverable at runtime via
  response headers rather than being a single fixed published number.

`UNKNOWN`: the exact numeric default limit (calls/second) for a newly-approved application tier.

### 1.12 API Usage Approval / Review Conditions

`UNKNOWN`. No official-domain source in this research pass described a formal review/approval SLA
or explicit approval criteria for Naver Commerce API access beyond the (unconfirmed, §1.2)
third-party claim of an "통합매니저" role requirement and per-store application-count limits.
`CTO GATE`: confirm actual approval process, review turnaround, and any policy prerequisites
(e.g. business registration status, mail-order sales license) against
`apicenter.commerce.naver.com` directly.

### 1.13 Test / Sandbox Environment

`UNKNOWN`. No official-domain confirmation of a sandbox/testbed environment was found in this
research pass. This is a material gap for Phase 2B (§4) — if no sandbox exists, "테스트 계정
연결" in Phase 2B may have to mean a real, low-risk seller account rather than an isolated sandbox,
which changes the risk profile materially. `CTO GATE`: confirm sandbox availability before Phase
2B scoping.

### 1.14 Naver SmartStore — Summary Table

| Item | Status |
|---|---|
| Official Commerce API exists | `CONFIRMED` |
| Seller/app registration requirements | `UNKNOWN` (third-party only) |
| Auth method (OAuth2 + custom signature) | `UNKNOWN` (third-party only, plausible but unverified) |
| Product create/modify API | `CONFIRMED (official channel)`, fields `UNKNOWN` |
| Option/price/stock API | `CONFIRMED (existence only)`, separate-endpoint structure `UNKNOWN` |
| Image upload mechanism | `UNKNOWN` |
| Notice info / category-required fields | `UNKNOWN` |
| Order collection API | `CONFIRMED (existence only)` |
| Dispatch/shipping/invoice API | `CONFIRMED (official channel)`, schema `UNKNOWN` |
| Cancel/exchange/return API | `CONFIRMED (official channel)`, schema `UNKNOWN` |
| Rate limits / error handling | `CONFIRMED (official channel)`, exact numeric limit `UNKNOWN` |
| Approval/review conditions | `UNKNOWN` |
| Sandbox/test environment | `UNKNOWN` |

---

## 2. Coupang — Coupang Open API

### 2.1 Official Open API Existence

`CONFIRMED`. The official developer portal is `https://developers.coupangcorp.com` (English,
Korean, Simplified/Traditional Chinese supported), retrieved via search 2026-07-11. It hosts
categorized API documentation (Product API, Return API, order/shipment APIs, authentication
guides, notices).

### 2.2 Wing Seller Account Requirements

`CONFIRMED (existence only)`: to use Coupang Open API, a seller must first sign up as a seller and
obtain an Open API key from **Wing** (`wing.coupang.com`), the seller portal — there is no
additional separate "apply for API access" process beyond having a Wing seller account and issuing
a key. Source: `developers.coupangcorp.com/hc/en-us/articles/360033917473-Coupang-OPEN-API`,
retrieved via search 2026-07-11.

`CONFIRMED (existence only)`: a business registration number is required to sign up as a Wing
seller in Korea. Source: same article. `UNKNOWN` (third-party sourced only —
`behalfkr.com`/`pearsonp.com`/`geekseller.com` — for non-Korean/global sellers): claimed
requirements such as a foreign business license/EIN letter, bank statement with SWIFT code, and
identity documents. Not treated as confirmed fact per task rule.

`UNKNOWN` (mentioned by third-party sources only, e.g. `behalfkr.com`): a claim that Korean law
requires a "통신판매업 신고" (Mail Order Sales License) for all online sellers including Coupang
sellers — plausible given this is a widely-known general Korean e-commerce regulatory requirement
independent of Coupang specifically, but not confirmed against an official Coupang document in
this pass, and out of this document's scope to verify Korean commerce law generally (`CTO GATE`:
confirm via legal/compliance review, §5).

### 2.3 API Key Issuance and Signing Method (HMAC)

`CONFIRMED`, via `developers.coupangcorp.com/hc/en-us/articles/20405856965145-What-is-an-OpenAPI-key`
and `developers.coupangcorp.com/hc/en-us/articles/360033461914-Creating-HMAC-Signature`, both
retrieved via search 2026-07-11:

- Authentication uses **HMAC** (keyed-hash message authentication code, described as an RFC2014-
  standard construction) requiring an **Access Key** (`CLIENT_KEY`, identifies the caller) and a
  **Secret Key** (used to compute the HMAC signature).
- Signature generation inputs include a timestamp, HTTP method, request path, and query string.
- A generated HMAC signature is valid for a limited window — reported as **up to 5 minutes**.
- An invalid signature returns an explicit "invalid signature" error.
- Official multi-language sample code is provided for Java, Node.js, PHP, C#, Python, and Classic
  ASP.

`CONFIRMED (existence only)`: only one Open API key can be issued per seller ID (company code),
and no more than two "Integrators" (i.e. distinct API-consuming systems/credentials tied to one
seller) may be registered. Source: same articles, retrieved via search 2026-07-11. `UNKNOWN`
(specific numeric/eligibility claims only found without a single clear official citation in the
synthesized text — treat as unverified pending direct read): a claim that new sellers must
successfully deliver at least three orders before becoming eligible to request an Open API key,
and that a key cannot be issued while a store is still in the "opening" process.

### 2.4 Product Creation / Modification API

`CONFIRMED (existence only)`, via `developers.coupangcorp.com/hc/en-us/articles/360033877853-Product-Creation`
and `.../360034156073-Modify-Product`, plus a documented "상품 API 워크플로우" (Product API
Workflow) overview page, all retrieved via search 2026-07-11. Confirmed workflow concept: a
product is created in a **temporary-save (임시저장) state**, then a **separate approval-request
step** (승인 요청) moves it toward listing exposure; the create/modify endpoints accept a
`requested` boolean parameter that, when `true`, automatically triggers the sale-approval request
in the same call. `UNKNOWN`: exact field-level payload schema.

`CONFIRMED (existence only)`: Coupang also documents a distinct combined product-modification flow
for sellers running "로켓그로스" (Rocket Growth) alongside standard Marketplace listings on the
same product, implying the modification API's behavior is fulfillment-model-dependent — a
material integration detail for scoping. Source:
`developers.coupangcorp.com/hc/ko/articles/39407792403609-...`, retrieved via search 2026-07-11.

### 2.5 Option / Price / Stock API

`CONFIRMED`, via multiple distinct official article titles returned directly in search results
(URLs below), retrieved 2026-07-11 — Coupang exposes **dedicated, separate endpoints** for
item-level (`vendorItemId`, i.e. option-level) changes, distinct from the create/modify-product
endpoint:

- `.../360034156273-Changing-price-of-each-item-of-a-product` (가격 변경)
- `.../360034156253-상품-아이템별-수량-변경` (수량/재고 변경)
- `.../360033645114-Query-quantity-price-status-by-product-items` (조회)
- Additional confirmed-existing endpoints per the "Product API" workflow: resume sales
  (재판매), stop sales (판매중지), and change discount base price by item.

`CONFIRMED (existence only)`: for a product already in "승인완료" (Approval Completed) status,
price/inventory changes **must** go through these dedicated item-level APIs — the general Product
Modification API explicitly cannot alter price/inventory once a product is approved. Source:
`developers.coupangcorp.com/hc/en-us/articles/360022938354-Price-and-inventory-does-not-change`
and the Product Modification article, retrieved via search 2026-07-11. This is an important,
specific, directly-relevant architectural constraint (§3.9).

`CONFIRMED (existence only)`: item-level `vendorItemId` values are issued only after a sales
(approval) request is itself approved — i.e. there is a real ordering dependency: create → request
approval → approval completes → `vendorItemId` exists → item-level price/stock APIs become usable.
Source: same articles.

### 2.6 Product Image Requirements

`UNKNOWN`. No official-domain source with specific image requirements (dimensions, format, count,
background rules) was returned in this research pass. `CTO GATE`: confirm via direct read of the
Product Creation / OPEN API Product Listing Guide articles before Phase 2A payload design assumes
specific image constraints.

### 2.7 Category / Notice Information (고시정보) Requirements

`CONFIRMED (existence only)`, via `developers.coupangcorp.com/hc/en-us/articles/360034035713-Category-Metadata-Query`
and `.../900001714583-...notification-information-error...`, retrieved via search 2026-07-11: a
**Category Metadata Query API** exists that, given a `displayCategoryCode`, returns the
category's required notice fields, option structure, required documents, and certification
information list — i.e. notice-information requirements are category-dependent and must be
resolved dynamically per category, not hardcoded. A documented failure mode exists
("상품등록 시 고시정보 에러") when submitted notice information does not match what the category
metadata requires.

`CONFIRMED (existence only)`, via `developers.coupangcorp.com/hc/ko/articles/54700630775577-...`
(공지, dated per the article title as taking effect **2026-02-02**), retrieved via search
2026-07-11: Coupang has an active/upcoming policy of **mandatory required-purchase-option entry**
per category, with escalating enforcement — omitted required purchase options can cause API
registration requests to be rejected or final registration to fail. This is a live, dated policy
change directly relevant to any Phase 2A/2B payload builder and should be re-verified close to
implementation time given it is a moving policy, not a static one.

### 2.8 Order Collection API

`CONFIRMED (existence only)`: an Order API category exists on the official portal (confirmed by
category-listing search results, e.g. "Product API"/"Return API" section pages under
`developers.coupangcorp.com/hc/en-us/sections/...`). `UNKNOWN`: exact order-query endpoint
name/schema in this research pass (not directly returned by the queries run).

### 2.9 Dispatch / Invoice (송장) / Shipping Processing API

`CONFIRMED (official channel)`, via `developers.coupangcorp.com/hc/ko/articles/360033793014-송장업로드-처리`,
retrieved via search 2026-07-11:

- An invoice-upload API exists that transitions an order to a "배송지시" (dispatch-instructed)
  state.
- Invoice upload is only valid for orders currently in "상품준비중" (preparing-product) status.
- Submitting a duplicate invoice number within a **6-month** window triggers a documented
  duplicate-invoice error.

`CONFIRMED (existence only)`: a separate 발주서 (purchase/dispatch order document) upload step
precedes invoice upload, followed by an 출고전표 (outbound slip)-based fulfillment-processing step
— i.e. the confirmed flow shape is purchase-order → outbound processing → invoice upload →
dispatch-instructed state, though exact endpoint names for the purchase-order/outbound-slip steps
are `UNKNOWN` from this pass.

### 2.10 Cancel / Exchange / Return API

`CONFIRMED`, via several distinct official article titles returned directly in search results,
retrieved 2026-07-11:

- `.../360033919613-Return-Cancellation-Request-List-Query` — returns receipt info, order ID,
  status, requester detail, cancellation reason, return delivery info, and return items.
- `.../360033843154-Cancel-an-order` — cancel-order API; response includes receipt ID, type,
  vendor item IDs, and failed item IDs (i.e. partial-failure per-item reporting is a confirmed
  response shape).
- `.../360034027374-Query-return-withdrawal-history-by-receiptID` and
  `.../360034027354-...by-date-range` — return-withdrawal history queries, with the date-range
  variant documented as queryable over a maximum 7-day window.
- A distinct `Return API` documentation section exists
  (`.../sections/360004302273-Return-API`), confirming returns are a first-class, separately
  documented API surface, not folded into the order API.

`UNKNOWN`: exact exchange-specific (as opposed to return/cancel) endpoint names — search results
referenced exchange-related operations only via a third-party GitHub Python wrapper
(`github.com/kyungdongseo/coupang`, an unofficial community project, not authoritative) rather
than an official article title; treat exchange-API specifics as `UNKNOWN` pending direct official
confirmation.

### 2.11 Rate Limits and Error Handling

`CONFIRMED`, via `developers.coupangcorp.com/hc/en-us/articles/20414599556889-Introduction-of-Open-API-rate-limit-policy`
and `.../23902034110617-Notice-on-strengthening-OpenAPI-speed-limit-policy-October-12-2023`, both
official-domain article titles returned directly in search results, retrieved 2026-07-11:

- Exceeding the per-second call limit returns **HTTP 429 Too Many Requests**.
- The default rate-limit trigger is reported as **more than 5 API calls per second per
  `vendorId`**, with a note that the exact threshold can vary by system and vendor.
- Since **2023-10-12**, Coupang has progressively strengthened rate limiting specifically for
  product-related Open APIs (create/edit/query, and quantity/price/sales-status change) — repeated
  excessive calls to these specific endpoints can result in **immediate blocking**, a stricter
  consequence than a simple 429 backoff-and-retry pattern.

This last point is architecturally significant for Phase 2 (§3.13, §4): a naive retry-on-429 loop
against product/price/stock endpoints risks an account-level block, not just a delayed request —
retry logic for these specific endpoints must be conservative, not aggressive.

### 2.12 API Usage Approval / Restriction Conditions

`CONFIRMED (existence only)`: product listing approval is a distinct workflow step from API key
issuance itself (§2.4) — i.e. having an API key does not mean every product auto-publishes; each
product individually passes through the create → approval-request → approval-completed flow, and
a documented failure mode exists where "승인 내용에 문제가 있을 경우 승인 요청이 처리되지 않을 수
있습니다" (approval requests can fail to process if there is a problem with the approval content).
`UNKNOWN`: a specific published SLA/turnaround time for approval was not found in this research
pass.

`UNKNOWN` (only from third-party sourcing, §2.3): the claimed "3 delivered orders before Open API
key eligibility" and "key not issuable during store-opening" conditions.

### 2.13 Coupang — Summary Table

| Item | Status |
|---|---|
| Official Open API exists | `CONFIRMED` |
| Wing seller account required, business registration number required (Korea) | `CONFIRMED (existence only)` |
| Global/non-Korean seller document requirements | `UNKNOWN` (third-party only) |
| HMAC signing method, key components, 5-minute signature validity | `CONFIRMED` |
| One key per seller ID, max 2 integrators | `CONFIRMED (existence only)` |
| 3-delivered-orders / store-opening key-eligibility restriction | `UNKNOWN` (unverified specificity) |
| Product create/modify API, temp-save → approval-request flow | `CONFIRMED (existence only)`, field schema `UNKNOWN` |
| Item-level (option) price/stock API, separate from product-modify API | `CONFIRMED` |
| Post-approval price/stock changes must use item-level API | `CONFIRMED (existence only)` |
| Image requirements | `UNKNOWN` |
| Category Metadata Query API for notice/option/cert requirements | `CONFIRMED (existence only)` |
| Mandatory required-purchase-option policy (effective 2026-02-02) | `CONFIRMED (existence only)`, live/moving policy |
| Order collection API | `CONFIRMED (existence only)`, schema `UNKNOWN` |
| Invoice upload / dispatch-instructed state / 6-month duplicate window | `CONFIRMED` |
| Purchase-order/outbound-slip step names | `CONFIRMED (existence only)`, exact endpoints `UNKNOWN` |
| Return/cancel API (list query, cancel-order, withdrawal history, 7-day window) | `CONFIRMED` |
| Exchange-specific API | `UNKNOWN` |
| Rate limit: 429, ~5 calls/sec/vendorId default, product-API strict blocking since 2023-10-12 | `CONFIRMED` |
| Approval SLA/turnaround | `UNKNOWN` |

---

## 3. Common Commerce Upload Architecture

`PROPOSAL` throughout this section unless otherwise marked. Built as an **additive extension of
the existing, `CONFIRMED` Commerce Phase 1 contract** (`docs/COMMERCE_PHASE_1_CONTRACT.md`,
`modules/commerce/`) — Phase 1's truth/source/freshness gates, `blocked_reasons` taxonomy, and
`manual_upload_checklist` shape are reused, never replaced.

### 3.1 Adapter Structure Between Phase 1 Output and Platform APIs

```text
CommerceModule.run()                         (CONFIRMED, existing, Phase 1, unmodified)
  -> commerce_result.platform_packages.smartstore   (verified copy package)
  -> commerce_result.platform_packages.coupang      (verified copy package)

PlatformUploadAdapter (PROPOSAL, new, Phase 2)
  base class defining: validate() -> dry_run() -> submit() -> poll_status() -> record_audit_log()
  |
  +-- SmartStoreAdapter (PROPOSAL)   consumes platform_packages.smartstore only
  +-- CoupangAdapter (PROPOSAL)      consumes platform_packages.coupang only
```

`PROPOSAL`: neither adapter ever reads or regenerates product copy — they only **translate an
already-`ready_for_manual_upload`-gated Phase 1 package** into each platform's request shape.
Product truth, freshness, and compliance gating remain entirely Phase 1's responsibility
(`CONFIRMED` boundary already established in `COMMERCE_PHASE_1_CONTRACT.md` §3) — an adapter must
refuse to submit any package whose Phase 1 `status` is not `ready_for_manual_upload` (§3.4).

### 3.2 `SmartStoreAdapter` Responsibilities

`PROPOSAL`: (1) resolve the current category ID via the confirmed-to-exist category lookup API
(§1.4) before every submission — never cache a category ID across runs, since categories/policy
can change; (2) map Phase 1's `notice_information` fields to whatever category-specific notice
schema the platform returns (§1.7, currently `UNKNOWN` in detail — this mapping cannot be finalized
until that gap is closed); (3) perform the confirmed OAuth2 + signature flow (§1.3, `UNKNOWN` in
exact algorithm — blocks real implementation until verified); (4) never assume image-upload
mechanism until §1.6 is resolved.

### 3.3 `CoupangAdapter` Responsibilities

`PROPOSAL`, better-grounded than §3.2 given deeper `CONFIRMED` coverage in §2: (1) compute HMAC
signatures per the confirmed method (§2.3) with a request timestamp fresh enough to stay inside
the confirmed 5-minute signature validity window; (2) resolve category metadata (§2.7) before
every submission for the same reason as §3.2; (3) submit product creation with `requested=false`
first (temp-save only) — **never** default to auto-requesting approval in the same call, so a
human/dry-run gate (§3.5–§3.6) always sits between creation and the approval-request step,
regardless of what the raw API technically allows; (4) route all post-approval price/stock changes
through the confirmed dedicated item-level endpoints (§2.5), never the general product-modify
endpoint, since that would silently fail or be rejected per §2.5's confirmed constraint.

### 3.4 Credential Storage

`PROPOSAL`, reusing the `CONFIRMED` existing project convention: `.env`-based secret storage,
identical in spirit to the already-documented `OPENAI_API_KEY` handling
(`CONFIRMED`, `CLAUDE.md`: *".env holds OPENAI_API_KEY and is gitignored. Never commit it or print
its contents."*). Proposed new variables (names only, no values, never issued by this document):
`NAVER_COMMERCE_APP_ID`, `NAVER_COMMERCE_APP_SECRET`, `COUPANG_ACCESS_KEY`,
`COUPANG_SECRET_KEY`. `CTO GATE`: whether these should live in `.env` (simplest, matches existing
pattern) or a dedicated secret manager is a real decision once real order/PII data starts flowing
through the same process (§3.15) — `.env` was an acceptable choice for a single LLM API key; two
marketplace credential pairs plus eventual order/customer data materially raises the blast radius
of a credential leak, and this document does not assume `.env` remains sufficient at that point.

### 3.5 Pre-Registration Validation Gate

`PROPOSAL`: a strict pipeline stage between Phase 1's `commerce_result` and any adapter call —

```text
1. commerce_result.status == "ready_for_manual_upload"          (CONFIRMED Phase 1 field)
2. platform_packages.<platform>.status == "ready"                (CONFIRMED Phase 1 field)
3. Every volatile fact's freshness re-checked against NOW, not against commerce_result's
   original generated_at (PROPOSAL — "freshness at generation time" != "freshness at upload time",
   §3.9)
4. Category/notice metadata re-fetched live from the platform (§1.7/§2.7) and diffed against
   Phase 1's notice_information — any platform-required field Phase 1 didn't populate blocks here
5. Human approval recorded (§3.6), unless in an explicitly approved auto-registration mode (§3.7,
   CTO GATE)
```

Any failure at any step produces a `blocked_reasons` entry using the same taxonomy shape already
established in Phase 1 (`COMMERCE_PHASE_1_CONTRACT.md` §6) plus new Phase-2-specific codes
(`PROPOSAL`): `platform_category_metadata_mismatch`, `freshness_expired_since_generation`,
`external_upload_not_approved` (`CONFIRMED` code name already reserved in Phase 1 §9).

### 3.6 Human Approval Mode

`PROPOSAL`: the default and, until `CTO GATE`-approved otherwise, the **only** mode. A human
reviews the exact outbound request payload (not just the Phase 1 copy — the actual
platform-shaped JSON an adapter would send) and the dry-run diff (§3.5) before any network call to
either platform is made. Approval is recorded outside the generated copy, mirroring Phase 1's
existing checklist item: *"Record the human reviewer and review time outside the generated
copy"* (`CONFIRMED`, `COMMERCE_PHASE_1_CONTRACT.md` §7).

### 3.7 Dry-Run Mode

`PROPOSAL`: an adapter mode that performs every step through §3.5 (validation, live category
metadata fetch, signature computation) but **stops before the network call that would actually
create/modify a listing** — instead emitting the fully-formed request payload as an inspectable
artifact under `storage/commerce/<request_id>/`. This is the confirmed minimum viable Phase 2A
deliverable (§4).

### 3.8 Automatic Registration Mode

`CTO GATE`, not `PROPOSAL` — this document does not propose enabling this mode; it only defines
what it would require if approved: (1) a per-scope explicit allow-list (listing creation, listing
update, inventory, price, order actions — individually toggled, per Phase 1 §9's own requirement);
(2) a proven track record of Phase 2C (§4) human-approved single-item registrations with zero
policy-rejection incidents; (3) real-time platform error-rate monitoring wired to an automatic
kill-switch. Until explicitly approved, every `CommerceModule`/adapter result must continue to set
`upload_mode: "manual_only"` (or, once dry-run exists, a
`upload_mode: "dry_run"`/`"human_approved_single"` value — never `"automatic"`) and
`auto_upload_performed: false`, exactly mirroring the `CONFIRMED` Phase 1 contract's existing
fields.

### 3.9 Idempotency and Duplicate-Listing Prevention

`PROPOSAL`: every outbound create request carries a stable idempotency key derived the same way
Phase 1-adjacent code already derives stable content IDs elsewhere in this project
(`CONFIRMED` precedent: `ContentPerformanceHistory.build_content_id()` hashes stable content
fields, not a timestamp, specifically to make deduplication actually work — the exact prior
project bug this pattern was already introduced to fix, per `MODULE_STATUS.md`'s Instagram
Intelligence Phase 3 entry). `PROPOSAL`: hash `request_id` + `product.product_id` (both already
present in the `CONFIRMED` Phase 1 input contract) as the idempotency key; before any create call,
query the platform (or a local `storage/commerce/` ledger, whichever is more reliable once §1.8/
§2.8's order-and-listing query APIs are better understood) for an existing listing with that key,
and refuse to create a second listing if one already exists — surface `duplicate_listing_detected`
as a new `blocked_reasons` code instead.

### 3.10 Price / Stock / Shipping-Fee Freshness Re-Verification

`PROPOSAL`, extending `CONFIRMED` Phase 1 machinery rather than inventing new machinery: Phase 1
already requires `expires_at` on every volatile fact (price/discount/stock/shipping are
`CONFIRMED` always-volatile fields per `COMMERCE_PHASE_1_CONTRACT.md` §2) and already blocks a
value once its `expires_at` has passed. §3.5 step 3 above is the Phase 2 extension: re-run that
exact same freshness check **at upload time**, not just at Phase 1 generation time, since real
elapsed time between package generation and actual upload could exceed a short `expires_at`
window. If any previously-fresh value has since expired, the adapter must re-block that field
rather than silently uploading a stale price/stock/shipping value.

### 3.11 Image Copyright and Product-Fact Provenance

`PROPOSAL`, extending the `CONFIRMED` existing Phase 1 rule (source/rights required per
`COMMERCE_PHASE_1_CONTRACT.md` §3 gate 6) to the upload step: an adapter must refuse to include an
image whose Phase 1 record lacks `rights_or_permission`, mirroring exactly the same
`render_allowed`-style gate already proven and reviewed in CardNews Evidence Selection
(`CONFIRMED` precedent, `modules/card_news/evidence_selector.py`'s `copyright_status` allow-list —
reuse the *pattern*, a small `IMAGE_RIGHTS_ALLOWED` set, not the code, consistent with this
project's established "reuse pattern across engines, never import across unrelated modules"
convention already applied for Shorts in `docs/SHORTS_ARCHITECTURE_DRAFT.md`).

### 3.12 Upload Request/Response Audit Log

`PROPOSAL`: every adapter call (dry-run or real) appends one record to
`storage/commerce/<request_id>/upload_audit_log.jsonl` — `{timestamp, platform, mode
(dry_run|human_approved|automatic), request_payload_hash, response_status, response_summary,
reviewer (if human_approved), idempotency_key}`. **Never log the raw HMAC secret, signature, or
OAuth token itself** — only the payload hash and outcome, consistent with the `CONFIRMED`
project-wide credential-handling rule (§3.4).

### 3.13 Partial Failure and Retry

`PROPOSAL`, directly informed by §2.5's and §2.11's confirmed platform behavior: Coupang's
confirmed cancel-order response shape already reports **per-item** failure (`failedVendorItemIds`
alongside successful ones) — any retry logic must be item-scoped, not whole-request-scoped, to
avoid re-submitting already-succeeded items. Given the `CONFIRMED` finding that Coupang applies
**stricter, block-triggering** rate limiting specifically to product create/edit/query and
price/stock-change endpoints (§2.11), retry backoff for exactly those endpoint categories must be
conservative (`PROPOSAL`: exponential backoff with a low retry ceiling, e.g. 2–3 attempts, never a
tight retry loop) — reusing this project's `CONFIRMED` existing `RetryPolicy` pattern
(`modules/trend_collector/retry_policy.py`) as the structural template, not its trend-specific
tuning.

### 3.14 Rollback and Listing Deactivation

`PROPOSAL`: a `deactivate_listing()` adapter method as the confirmed-necessary counterpart to
creation — since Coupang's confirmed item-level API includes an explicit "판매중지" (stop-sales)
endpoint (§2.5), rollback on Coupang should call that endpoint rather than attempting a hard
delete. Naver's equivalent mechanism is `UNKNOWN` (§1.5 gap) and must be confirmed before any
rollback logic is written for that platform.

### 3.15 Order / Purchase-Order / Invoice Status State Machine

`PROPOSAL`, built directly from `CONFIRMED` facts in §1.9/§1.10 and §2.9/§2.10 rather than
invented from scratch:

```text
Coupang (CONFIRMED-shaped, per §2.9):
  order_received -> 상품준비중(preparing) -> [invoice uploaded] -> 배송지시(dispatch-instructed)
                                            -> ... -> delivered
  (cancel/return can branch off at multiple points per §2.10's confirmed query surface)

Naver (CONFIRMED-shaped, per §1.9, less detail known):
  order_received -> ... -> [dispatch + invoice number recorded] -> DISPATCHED (queryable state)
  (cancel/exchange/return states per §1.10: approval/hold/reject/pickup-complete/re-ship, exact
  full state graph UNKNOWN)
```

`PROPOSAL`: implement Coupang's state machine first, given materially deeper `CONFIRMED` coverage;
treat Naver's as a stub pending the §1.9/§1.10 documentation gaps closing.

### 3.16 Per-Vendor (위탁업체) Purchase-Order Document Generation

`PROPOSAL`: out of scope for Phase 2A–2C (§4) — this requires knowing which of this project's
future product sources are drop-shipped/vendor-fulfilled vs. self-fulfilled, a business-model
decision not yet made anywhere in the repository (`CONFIRMED`: no vendor/fulfillment-model concept
exists in the current Phase 1 contract or `modules/commerce/`). `CTO GATE`: define the
fulfillment-model taxonomy before this item can be scoped at all.

### 3.17 Personal Data and Shipping-Address Protection

`PROPOSAL`: order/shipping data (once §3.15 order sync exists) is real customer PII — buyer name,
address, phone number. This must **never** be written into any location this project already
treats as broadly-readable/loggable (e.g. the general `storage/` tree structure used elsewhere is
not access-controlled — `CONFIRMED` observation, every other Engine's `storage/<engine>/` output is
plain JSON on disk with no encryption layer in this codebase today). `CTO GATE`: decide whether
order/PII data may live in the same `storage/commerce/` tree at all, or requires a
separately-access-controlled location, encryption at rest, and a retention/deletion policy —
this is a real legal/compliance decision (§5), not an engineering default this document can set.

### 3.18 CS / Return Status Synchronization

`PROPOSAL`: reuse §3.15's state machine as the single source of truth; a synchronization job polls
each platform's confirmed return/cancel query APIs (§1.10, §2.10) on an interval and reconciles
local state — never let a human-facing CS view show a status derived from anything other than a
fresh platform query, given returns/cancels are exactly the kind of volatile fact Phase 1's own
gates (§3.10) already treat with maximum suspicion.

### 3.19 Fee / Margin Re-Verification

`PROPOSAL`: platform commission/fee schedules are `UNKNOWN` in this research pass (not
investigated — out of the 22 required research sub-items, fee-schedule specifics were not part of
either platform's required list, but margin re-verification was explicitly required in §3 of the
task). `PROPOSAL`: before any price is submitted, re-derive net margin as
`price - platform_fee_estimate - shipping_cost` using a per-platform fee-rate constant that is
itself `CTO GATE`-sourced (official fee schedule, not estimated) — block submission if net margin
falls below a `CTO GATE`-defined floor. This is intentionally deferred pending a dedicated fee-
schedule research pass, since guessing a fee percentage here would violate this document's own
"do not assume unconfirmed facts" principle.

---

## 4. Phased Implementation Plan

| Phase | Scope | Entry criteria | Exit criteria | Rollback |
|---|---|---|---|---|
| **2A** — Dry-run payload generation | `PROPOSAL`: implement `SmartStoreAdapter.dry_run()` / `CoupangAdapter.dry_run()` (§3.7) — build the exact platform-shaped request payload from a `ready_for_manual_upload` Phase 1 package, using only `CONFIRMED` field mappings; leave any field dependent on an `UNKNOWN` gap (§1.6 image mechanism, §1.7 notice schema, §1.3 auth) explicitly marked `pending_confirmation` in the payload rather than guessed | Phase 1 contract stable (`CONFIRMED`, already true); no credentials required | Payload artifact reproducibly generated for a real Phase 1 output, reviewed by a human against the actual seller-UI fields it claims to represent, zero network calls made | Delete the adapter files; zero effect on Phase 1 or any other module |
| **2B** — Sandbox / test-account connection | Connect real credentials (§3.4) to whatever test surface each platform actually offers — `CONFIRMED` unresolved for Naver (§1.13 `UNKNOWN`), `UNKNOWN` for Coupang too (not found this pass) — **this phase cannot be scoped precisely until that gap closes** | 2A complete; `CTO GATE` credential/account approval (§5) | A dry-run payload from 2A successfully validates against the real platform's validation endpoint (if one exists) without creating a live listing | Revoke/rotate the test credential; no production data touched |
| **2C** — Human-approved single-item registration | First real, human-reviewed, single-product registration on one platform | 2B complete; `CTO GATE` first-test-product selection (§5) | One real listing created, verified in the seller UI, price/stock confirmed correct, no policy violation | Use the platform's confirmed stop-sales/deactivation capability (§3.14); document the incident regardless of outcome |
| **2D** — Order/shipping sync | Implement §3.15's state machine (Coupang first, per deeper `CONFIRMED` coverage) and §3.18's CS sync | 2C complete with zero incidents over a `CTO GATE`-defined minimum observation period | Real order state correctly reflected locally, verified against the seller UI for every observed order | Disable the sync job; state reverts to manual seller-UI-only tracking |
| **2E** — Limited automatic registration | `CTO GATE` (§3.8) — this document does not propose enabling this phase | 2C+2D stable over an extended period, explicit per-scope CTO approval | N/A — not scoped by this document | N/A — not scoped by this document |

---

## 5. CTO Approval Gates

`CTO GATE` for every row — none are pre-approved by this document.

| Gate | What is needed |
|---|---|
| Accounts | A real Naver SmartStore seller account and a real Coupang Wing seller account, both under confirmed business ownership — this document did not create, access, or assume access to either. |
| API credentials | Naver Commerce API application ID/secret; Coupang Access Key/Secret Key — neither issued by this document (explicitly prohibited by the task). |
| Cost | `UNKNOWN` — neither platform's fee schedule was researched in this pass (§3.19); official API access itself was not found to require a separate paid tier in either platform's confirmed material, but this is not the same as confirming it is free — re-verify directly. |
| Terms/policy risk | Coupang's confirmed, live, dated (2026-02-02) required-purchase-option policy (§2.7) shows platform policy is actively moving — any Phase 2 implementation must budget for policy re-verification as an ongoing cost, not a one-time check. Naver's approval/terms conditions are largely `UNKNOWN` (§1.12) and must be confirmed before any account is opened for this purpose. |
| Personal-data risk | Order/shipping PII handling (§3.17) has no existing storage/access-control precedent in this codebase — requires an explicit decision before §4 Phase 2D. |
| Automation scope | Per-capability sign-off (listing create/update, inventory, price, order actions) individually, exactly as Phase 1's own §9 already requires — this document adds no new default beyond what Phase 1 already mandates. |
| First real product-data readiness | A real product with fully `CONFIRMED`-sourced facts already passing Phase 1's existing truth/source/freshness gates (`ready_for_manual_upload`, zero `blocked_reasons`) — Phase 2 must never be the first place a product's facts are verified. |
| First test-product selection | `PROPOSAL` criteria (not a decision): low commercial risk (low price, no safety-critical category, no regulated-category notice requirements beyond the basics already modeled in Phase 1's `NOTICE_FIELDS`), single option/no complex variant matrix, already-owned or already-licensed images only (§3.11). |

---

## Summary for Reviewers

Both platforms have `CONFIRMED`, real, official Commerce/Open APIs covering product, order,
fulfillment, and returns — Coupang's documentation was substantially more directly confirmable in
this research pass (HMAC auth, item-level price/stock separation, rate-limit specifics, invoice
flow, return API) than Naver's (whose auth mechanism, image upload method, and notice-field schema
all remain `UNKNOWN` pending direct primary-source access this environment could not obtain).
Neither platform's sandbox availability was confirmed. The proposed architecture layers adapters,
validation, dry-run, and audit logging on top of the existing, unmodified Phase 1 contract, with
automatic registration explicitly left as an unapproved `CTO GATE` rather than a designed default.
Phase 2A (dry-run payload generation) is the only phase implementable today without new
credentials, accounts, or unresolved-gap assumptions. No code, test, `site/`, storage, credential,
account, or shared status document was touched in producing this research and design document.
