# SmartStore Product Registration Contract (Design Draft)

Author: Claude (data-contract architect pass), 2026-07-11
Status: **DESIGN DRAFT. Read-only research + contract proposal. No code, `modules/**`, `tests/**`,
`site/**`, `storage/**`, or shared project document touched. No API key, account, or login used.**

## 0. Purpose and boundaries

This document defines the **target shape** of a SmartStore-specific product registration payload
and how it should be built from Commerce Phase 1's already-verified `commerce_result` output
(`docs/COMMERCE_PHASE_1_CONTRACT.md`, `modules/commerce/commerce_module.py`, read-only references
for this document). It is a **contract design for a future Phase 2A dry-run payload builder**
(`SmartStoreAdapter.dry_run()` per `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.2/§3.7), not
an implementation. Nothing here authorizes real API calls, credential issuance, or automatic
upload — Phase 1's `upload_mode: "manual_only"` / `auto_upload_performed: false` and Phase 2's CTO
approval gate remain unchanged and unaffected by this document.

### Evidence tier legend (applies to every factual claim below)

- `CONFIRMED` — I directly fetched and read real official primary-source content in this pass.
  **No claim in this document reaches this tier for SmartStore** (see §0.1).
- `CONFIRMED (official channel, search-synthesis only)` — a search result's own synthesized text
  cites specific content from an official `apicenter.commerce.naver.com` page or an official
  `github.com/commerce-api-naver/commerce-api` GitHub Discussion, but I did not independently fetch
  and read the full source page myself. Per this task's stricter evidentiary rule, this tier is
  **treated as not-yet-independently-verified** and every field sourced this way still carries a
  `CTO GATE` re-verification requirement before Phase 2 implementation.
- `INFERRED` — derived from Phase 1 code/contract (safe, high-confidence), OR derived from a
  search snippet not independently fetched (lower confidence, explicitly noted which), OR derived
  from a third-party reverse-engineered analysis already present in this repository
  (`external_workmanus/seller_automation/docs/market_naver.md`, itself derived from a third-party
  tool's — "캄파(OSSA)" — analysis of Naver's API, not from Naver directly).
- `UNKNOWN` — not verifiable in this research pass.
- `BLOCKED` — access attempt made and explicitly refused/failed in this session.
- `PROPOSAL` — this document's own design choice (classification, mapping shape, fail-closed
  rule). Not an evidence tier.

### 0.1 Access attempts made in this pass

`BLOCKED`: direct `WebFetch` to `apicenter.commerce.naver.com` failed with "Claude Code is unable
to fetch from apicenter.commerce.naver.com" (tool-level domain block, consistent with the prior
session recorded in `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §0). `WebSearch` with a
`site:apicenter.commerce.naver.com` restriction returned zero results. Unrestricted `WebSearch`
queries returned only third-party sites and `github.com/commerce-api-naver/commerce-api`
Discussion threads, with search-engine-synthesized summaries of that content (not verbatim fetched
pages). No `CONFIRMED` (top-tier) source was obtained for SmartStore in this pass. Every SmartStore
field below therefore carries, at best, `CONFIRMED (official channel, search-synthesis only)` or
`INFERRED`, and a `CTO GATE` before implementation, exactly as `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`
§1 already concluded.

## 1. Field classification: required / optional / conditional

`PROPOSAL` classification, built on the `INFERRED` payload shape from
`external_workmanus/seller_automation/docs/market_naver.md` (third-party reverse-engineered, not
official) cross-checked against the `CONFIRMED (official channel, search-synthesis only)` field
list recovered from `github.com/commerce-api-naver/commerce-api` Discussions (#246, #241, #2216)
in this pass. Where the two sources agree, confidence is higher but the tier is still capped at
`CONFIRMED (official channel, search-synthesis only)` per §0.1.

| Field | Classification | Condition (if conditional) | Blocking reason code if absent |
|---|---|---|---|
| Product name (`originProduct.name`) | **Required** | — | `missing_required_field` |
| Category (`originProduct.leafCategoryId`) | **Required** | Must be a resolved **leaf** category ID from the category-lookup API, not a category label | `platform_category_metadata_unresolved` |
| Options (`detailAttribute.optionInfo`) | **Conditional** | Required when the product has more than one purchasable variant (color/size/weight/volume); a true single-SKU product may register with no option block | `missing_required_field` (if the product's own facts imply variants but none are supplied) |
| Price (`originProduct.salePrice`) | **Required** | Must be fresh per Phase 1's volatility gate at build time, not just at Phase 1 generation time | `stale_volatile_fact` / `missing_required_field` |
| Stock (`originProduct.stockQuantity`) | **Required** | Same freshness condition as price | `stale_volatile_fact` / `missing_required_field` |
| Images — representative (`images.representativeImage`) | **Required** | Must already be hosted at a URL the SmartStore image pipeline accepts (see §4.2) | `missing_required_field` / `image_hosting_not_implemented` |
| Images — additional (`images.optionalImages`) | Optional | — | `missing_fields` entry only, non-blocking |
| Detail description (`originProduct.detailContent`) | **Required** | Non-empty HTML string; JSON-significant characters escaped | `missing_required_field` |
| Certifications / notice info (`detailAttribute.productInfoProvidedNotice`) | **Conditional, but required in practice for nearly every real category** | Required whenever the resolved leaf category has a defined 상품정보제공고시 template (food, cosmetics, electronics, apparel, and most other regulated categories all have one; the only categories without one are a small residual set) | `notice_information_incomplete` |
| Origin / country of origin (`detailAttribute.originAreaInfo`) | **Required** | — | `notice_information_incomplete` |
| Shipping (`originProduct.deliveryInfo`) | **Required** | Delivery type, fee type, and fee amount must all be fresh, source-backed facts | `missing_required_field` / `stale_volatile_fact` |
| Return address (part of `deliveryInfo`/seller shipping profile, exact sub-field `UNKNOWN`) | **Required** | Typically a seller-level profile setting rather than a per-product fact in SmartStore's model (`UNKNOWN`, unconfirmed) — Phase 1 has no equivalent per-product field today | `platform_field_mapping_unknown` |
| Search keywords (`detailAttribute.seoInfo`) | Optional | — | non-blocking; omission only produces a `missing_fields` entry |
| Brand / manufacturer (`detailAttribute.naverShoppingSearchInfo`) | **Required** | — | `missing_required_field` |
| Benefits / discount (`customerBenefit`) | Optional | Only included when a currently-fresh, source-backed benefit exists; never invented | `stale_volatile_fact` if present but expired |
| Minor-purchasable flag (`detailAttribute.minorPurchasable`) | Optional | Category-dependent; defaults are platform-side and out of Phase 1's fact model | not blocking; leave `UNKNOWN`/unset rather than guess |

## 2. Field-mapping table: Phase 1 `commerce_result` → SmartStore payload

`PROPOSAL` shape; right-hand field names are `INFERRED` (third-party reverse-engineered mapping,
cross-referenced against `CONFIRMED (official channel, search-synthesis only)` field names) unless
marked `UNKNOWN`. No field name below is invented by this document — every populated cell traces to
either `market_naver.md`'s reverse-engineered mapping or a GitHub Discussion search snippet cited in
`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1.4/§1.7 or this pass's own search results (§0.1).

| Phase 1 `commerce_result` field | SmartStore payload field | Evidence tier |
|---|---|---|
| `platform_packages.smartstore.product_name` | `originProduct.name` | INFERRED (market_naver.md) + CONFIRMED (official channel, search-synthesis only) field name |
| `product.category` (post category-lookup resolution) | `originProduct.leafCategoryId` | INFERRED + CONFIRMED (official channel, search-synthesis only) |
| `commercial_facts.price` | `originProduct.salePrice` | INFERRED (market_naver.md) + CONFIRMED (official channel, search-synthesis only) |
| `commercial_facts.stock` | `originProduct.stockQuantity` | INFERRED (market_naver.md) |
| `platform_packages.smartstore.detail_description` | `originProduct.detailContent` | INFERRED (market_naver.md) + CONFIRMED (official channel, search-synthesis only) |
| product images (not yet a Phase 1 field — Phase 1 has no image URL/rights field today) | `originProduct.images.representativeImage.url` / `optionalImages[].url` | INFERRED (market_naver.md); Phase 1 input-contract gap, see §5 |
| `product.country_of_origin` | `detailAttribute.originAreaInfo` | INFERRED (market_naver.md) |
| `product.notice_information.*` | `detailAttribute.productInfoProvidedNotice.*` | INFERRED (market_naver.md); exact per-category child-node schema is `UNKNOWN` (a notice type such as `WEAR` selects which child node is used — confirmed via this pass's search synthesis of GitHub Discussions, but the full type enumeration is `UNKNOWN`) |
| `platform_packages.smartstore.options` | `detailAttribute.optionInfo.optionCombinations` / simple option node | INFERRED (market_naver.md); exact schema for simple vs. combination options is `UNKNOWN` beyond the "max 3 standalone options" hint from this pass's search synthesis |
| `platform_packages.smartstore.search_keywords` | `detailAttribute.seoInfo` (exact sub-field name `UNKNOWN`) | INFERRED (market_naver.md notes "태그/SEO" only, no exact field name) |
| `product.brand`, `product.manufacturer` | `detailAttribute.naverShoppingSearchInfo.*` (exact sub-fields `UNKNOWN`) | INFERRED (market_naver.md notes "브랜드/제조사" only) |
| `commercial_facts.benefits` (fresh only) | `customerBenefit` | INFERRED (market_naver.md) |
| `commercial_facts.shipping` | `deliveryInfo` (exact sub-schema `UNKNOWN`) | INFERRED (market_naver.md) |
| return address (no Phase 1 equivalent field exists today) | `UNKNOWN` — likely a seller-account-level profile setting, not a per-request payload field | UNKNOWN |
| listing status / visibility (no Phase 1 equivalent) | `originProduct.statusType`, `smartstoreChannelProduct.channelProductDisplayStatusType` | INFERRED (market_naver.md); this is a platform workflow control, not a product fact, and must never be set to an active/visible value by an automated builder without the human-approval gate in `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.6 |

## 3. Fail-closed rule (restated for this payload-building step)

`PROPOSAL`, restating Phase 1's existing truth/source/freshness gate contract
(`COMMERCE_PHASE_1_CONTRACT.md` §3) as it applies specifically to a future SmartStore payload
builder: **a value may appear in the SmartStore payload if and only if it is present in Phase 1's
`accepted` fact set — i.e. it already passed presence, source, verification, freshness,
consistency, and rights/compliance gating inside `CommerceModule` and is reflected in
`platform_packages.smartstore`.** A payload builder must never independently read `raw` request
data, never re-derive a value from an unverified source, and never fill a SmartStore-required field
(leaf category ID, price, stock, notice info, images) with a default, placeholder, or inferred
value merely because the platform payload has no tolerance for an empty field. If a
platform-required field has no corresponding accepted Phase 1 fact, the correct behavior is to
**block that field and the whole product's SmartStore submission** (`missing_required_field` or
the more specific code from §1), never to synthesize a plausible-looking value. This also applies
to freshness at build time: a fact that was fresh when Phase 1 generated `commerce_result` but has
since passed its `expires_at` must be re-blocked (`stale_volatile_fact`) before it reaches the
SmartStore payload, exactly as `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.10 already proposes.

## 4. SmartStore-specific structural notes

### 4.1 Category resolution is dynamic, not cacheable

`INFERRED` (from `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1.4/§3.2, itself
`CONFIRMED (official channel, search-synthesis only)`): a "전체 카테고리 조회 API" (full category
lookup API) exists and must be called to resolve `leafCategoryId` before every submission —
category IDs must never be cached across runs in a payload builder, since category trees and
per-category notice requirements can change.

### 4.2 Image handling is a Phase 1 input-contract gap

`INFERRED` (market_naver.md, itself third-party/unconfirmed): SmartStore's payload expects image
**URLs**, and the third-party note states images should be uploaded via a Naver image-upload API
first and the *resulting* URL used as `representativeImage.url`, not an arbitrary external URL.
Phase 1's current input contract (`COMMERCE_PHASE_1_CONTRACT.md` §2) has **no image field at all**
— no `product.images`, no image `source_ids`/rights metadata. This is a real gap: a SmartStore
payload builder cannot honestly populate `images.representativeImage` today because Phase 1 never
collects or gates an image fact. `PROPOSAL`: before any Phase 2A SmartStore builder is implemented,
Phase 1's input contract needs an explicit `product.images[]` fact type carrying `source_ids`,
`rights_or_permission`, and a hosted-URL value, gated exactly like every other fact (§3 above). This
document does not implement that extension — it only records the gap the fail-closed rule already
implies.

### 4.3 Option structure is simple-vs-combination, exact schema unresolved

`UNKNOWN`: whether a given product's options map to a "단순옵션" (simple option) or an "옵션조합"
(combination option) structure changes the shape of `optionInfo` materially, and the exact
condition/threshold is not confirmed. `CTO GATE`: resolve this against
`apicenter.commerce.naver.com`'s option documentation directly before a Phase 2A builder assumes
either shape.

### 4.4 No confirmed two-phase approval workflow

`UNKNOWN`, worth flagging explicitly: unlike Coupang (§ Coupang contract, temp-save →
approval-request → approved), no source in this pass or in
`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1 confirms or denies a comparable formal
approval-request step for SmartStore. The reverse-engineered payload in `market_naver.md` sets
`originProduct.statusType: "SALE"` directly at creation, which is consistent with (but does not
prove) a single-step registration model. Treat this as `UNKNOWN`, not as confirmed single-step
behavior — a Phase 2A builder must not assume a product is live/visible immediately after a create
call without direct platform confirmation.

## 5. Fields remaining UNKNOWN or blocked pending platform confirmation

- Exact auth/signature algorithm (`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1.3) — irrelevant to
  payload *shape* but blocks any real submission.
- Exact image upload mechanism and resulting URL format (§4.2) — and the fact that Phase 1 has no
  image fact type at all is a contract gap, not just an `UNKNOWN` field name.
- Exact `productInfoProvidedNotice` per-category child-node schema and the full notice-type
  enumeration (§2).
- Exact `optionInfo` simple-vs-combination schema and selection condition (§4.3).
- Exact `deliveryInfo` and return-address sub-schema, and whether return address is a per-product
  field or a seller-account-level profile setting (§1, §2).
- Exact `seoInfo` and `naverShoppingSearchInfo` sub-field names (§2).
- Whether a two-phase approval workflow exists (§4.4).
- Seller/app registration requirements, approval SLA, and sandbox/test-environment availability
  (`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1.2/§1.12/§1.13) — blocks Phase 2B/2C, not Phase 2A
  payload-shape design.

Every item above is a `CTO GATE` before real implementation, per
`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §4's Phase 2A entry criteria (leave any field dependent on
an unresolved gap explicitly marked `pending_confirmation` in a generated payload artifact rather
than guessed).

## 6. Cross-check against Phase 1's existing SmartStore minimum readiness

`CONFIRMED` (from `COMMERCE_PHASE_1_CONTRACT.md` §6.1, unmodified): Phase 1 already requires
verified `product_name`, `category`, `brand`, `manufacturer`, `country_of_origin`, `options`,
category notice information, and a non-empty detail description before
`platform_packages.smartstore.status` can be `ready_for_manual_upload`. Every field this document
classifies **Required** in §1 either already matches that existing Phase 1 minimum, or (price,
stock, images, shipping) is a field Phase 1 gates at the fact level via `ALWAYS_VOLATILE`/`SENSITIVE`
handling in `CommerceModule` even though it is not yet enumerated in the platform-package minimum
list. This document does not propose loosening or replacing Phase 1's existing gate — it only maps
what a downstream payload builder would need on top of an already-`ready_for_manual_upload` Phase 1
package.
