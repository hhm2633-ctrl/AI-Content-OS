# Coupang Product Registration Contract (Design Draft)

Author: Claude (data-contract architect pass), 2026-07-11
Status: **DESIGN DRAFT. Read-only research + contract proposal. No code, `modules/**`, `tests/**`,
`site/**`, `storage/**`, or shared project document touched. No API key, account, or login used.**

## 0. Purpose and boundaries

This document defines the **target shape** of a Coupang-specific product registration payload and
how it should be built from Commerce Phase 1's already-verified `commerce_result` output
(`docs/COMMERCE_PHASE_1_CONTRACT.md`, `modules/commerce/commerce_module.py`, read-only references
for this document). It is a **contract design for a future Phase 2A dry-run payload builder**
(`CoupangAdapter.dry_run()` per `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.3/§3.7), not an
implementation. Nothing here authorizes real API calls, credential issuance, or automatic upload —
Phase 1's `upload_mode: "manual_only"` / `auto_upload_performed: false` and Phase 2's CTO approval
gate remain unchanged and unaffected by this document.

### Evidence tier legend (applies to every factual claim below)

- `CONFIRMED` — I directly fetched and read real official primary-source content in this pass.
  **No claim in this document reaches this tier** (see §0.1) — direct fetch of
  `developers.coupangcorp.com` was refused in-session.
- `CONFIRMED (official channel, search-synthesis only)` — a search result's own synthesized text
  cites specific content from an official `developers.coupangcorp.com` article (title and URL
  returned directly by search, not invented), but I did not independently fetch and read the full
  article myself in this pass. Per this task's stricter evidentiary rule this tier still carries a
  `CTO GATE` before Phase 2 implementation, even where
  `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` (a prior session) reports the same tier with
  somewhat higher internal confidence for Coupang than for Naver.
- `INFERRED` — derived from Phase 1 code/contract (safe, high-confidence), OR derived from a search
  snippet not independently fetched (lower confidence, explicitly noted which).
- `UNKNOWN` — not verifiable in this research pass.
- `BLOCKED` — access attempt made and explicitly refused/failed in this session.
- `PROPOSAL` — this document's own design choice. Not an evidence tier.

### 0.1 Access attempts made in this pass

`BLOCKED`: direct `WebFetch` to `https://developers.coupangcorp.com/hc/en-us/articles/360033877853-Product-Creation`
returned "HTTP 403 Forbidden" (bot/anti-scraping protection, consistent with the prior session
recorded in `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §0). `WebSearch` queries did return
several specific field names in synthesized summaries — `displayCategoryCode`, `sellerProductName`,
`vendorId`, `vendorItemName`, `salePrice`, `maximumBuyCount`, `returnCenterCode`,
`noticeCategoryName` — each traceable to an official `developers.coupangcorp.com` article title in
the same result set, but again not independently fetched and read as a full primary document. Every
Coupang field below is therefore capped at `CONFIRMED (official channel, search-synthesis only)` or
`INFERRED`, with an explicit `CTO GATE` before implementation, exactly as
`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §2 already concluded (that document's own text: "Coupang's
documentation was substantially more directly confirmable... than Naver's").

## 1. Field classification: required / optional / conditional

`PROPOSAL` classification, built on the `CONFIRMED (official channel, search-synthesis only)` field
names recovered from this pass's searches plus the structural facts already established in
`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §2.4/§2.5/§2.7 (the temp-save→approval-request flow, the
confirmed item-level price/stock API split, and the confirmed Category Metadata Query API).

| Field | Classification | Condition (if conditional) | Blocking reason code if absent |
|---|---|---|---|
| Product name (`sellerProductName`) | **Required** | — | `missing_required_field` |
| Item/option name (`items[].itemName` / `vendorItemName`, exact key `UNKNOWN`) | **Required** | Required per purchasable item, even for a single-option product (Coupang's model is item-centric, not product-centric — see §4.1) | `missing_required_field` |
| Category (`displayCategoryCode`) | **Required** | Must be resolved via the Category Metadata Query API, not guessed from a category label | `platform_category_metadata_unresolved` |
| Options (`items[]` array, per-item attributes) | **Conditional** | Required when the product has more than one purchasable variant; still requires at least one `items[]` entry even for a single-SKU product | `missing_required_field` |
| Price — creation-time (`items[].originalPrice` / `items[].salePrice`, exact keys `UNKNOWN`) | **Required** | Must be fresh at build time; **after approval, any price change must go through the dedicated item-level price API, never this creation/modify field** (`CONFIRMED (existence only)` per Phase 2 doc §2.5) | `stale_volatile_fact` / `missing_required_field` |
| Stock (`items[].maximumBuyCount` and a separate quantity field, exact key `UNKNOWN`) | **Required** | Same freshness condition as price; same post-approval item-level-API-only constraint | `stale_volatile_fact` / `missing_required_field` |
| Images (`items[].images[]`, exact schema `UNKNOWN`) | **Required** | At least one representative image per item | `missing_required_field` / `image_hosting_not_implemented` |
| Detail description (`items[].contents[]` or a top-level detail field, exact key `UNKNOWN`) | **Required** | Non-empty; Coupang's detail-content mechanism (HTML block vs. structured content array) is `UNKNOWN` in this pass | `missing_required_field` |
| Certifications / notice info (`items[].notices[]`, fields `noticeCategoryName`/`noticeCategoryDetailName`/`content` per this pass's search synthesis) | **Conditional, required in practice for nearly every real category, and actively tightening** | Required whenever the resolved category's Category Metadata Query response lists required notice fields; Coupang has a `CONFIRMED (existence only)` documented failure mode for mismatched notice info | `notice_information_incomplete` |
| Required purchase options (category-dependent) | **Conditional, newly mandatory** | `CONFIRMED (existence only)` per Phase 2 doc §2.7: a live/moving Coupang policy (effective 2026-02-02) makes certain category-required purchase options mandatory; omission can cause outright registration rejection, not just a soft warning | `required_purchase_option_missing` (new, platform-specific) |
| Shipping / delivery method (`deliveryMethod`, `outboundShippingTimeDay`, exact top-level keys `UNKNOWN` beyond partial names) | **Required** | Must be fresh, source-backed | `missing_required_field` / `stale_volatile_fact` |
| Return center / return address (`returnCenterCode`, `returnZipCode`, `returnAddress`, exact full set `UNKNOWN`) | **Required** | Coupang appears to model this as a registered return-center **code** referencing a seller-level profile, not raw address text inline (per this pass's search synthesis; not independently fetched) | `platform_field_mapping_unknown` if Phase 1 has no equivalent fact, otherwise `missing_required_field` |
| Search keywords (`items[].searchTags`, exact key `UNKNOWN`) | Optional | — | non-blocking; `missing_fields` entry only |
| Fulfillment model (Marketplace vs. 로켓그로스/Rocket Growth hybrid) | **Conditional, structural** | `CONFIRMED (existence only)` per Phase 2 doc §2.4: the modify-product flow behaves differently depending on fulfillment model; Phase 1 has no fulfillment-model concept today (Phase 2 doc §3.16) | `rocket_fulfillment_model_undetermined` (new, platform-specific) |
| `requested` (approval-request trigger boolean) | **Design-controlled, not a product fact** | Per `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.3, a Phase 2A builder must always submit `requested=false` (temp-save only); this is a workflow-control value never sourced from Phase 1 facts | N/A — controlled by the adapter, not blockable at the fact level |

## 2. Field-mapping table: Phase 1 `commerce_result` → Coupang payload

`PROPOSAL` shape; right-hand field names are `CONFIRMED (official channel, search-synthesis only)`
where a specific key name was returned directly in this pass's search results, `INFERRED` where only
a general capability/concept was found (no exact key), and `UNKNOWN` otherwise. No field name below
is invented — every populated cell traces to a search result citing an official
`developers.coupangcorp.com` article title, or to `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §2.

| Phase 1 `commerce_result` field | Coupang payload field | Evidence tier |
|---|---|---|
| `platform_packages.coupang.product_name` | `sellerProductName` | CONFIRMED (official channel, search-synthesis only) |
| `product.category` (post category-metadata resolution) | `displayCategoryCode` | CONFIRMED (official channel, search-synthesis only) |
| `platform_packages.coupang.options` (per option/vendor-item) | `items[].itemName` / `items[].vendorItemName` (exact split between the two `UNKNOWN`) | CONFIRMED (existence of `vendorItemName` concept, official channel search-synthesis) + UNKNOWN exact schema |
| `commercial_facts.price` (creation-time only) | `items[].salePrice` / `items[].originalPrice` (exact key split `UNKNOWN`) | CONFIRMED (existence only, official channel search-synthesis) |
| `commercial_facts.price` (**post-approval changes**) | dedicated item-level price-change endpoint (`.../360034156273-Changing-price-of-each-item-of-a-product`), **not** the fields above | CONFIRMED (Phase 2 doc §2.5) |
| `commercial_facts.stock` (creation-time only) | `items[].maximumBuyCount` and a separate quantity field (`UNKNOWN` exact key) | CONFIRMED (existence only, official channel search-synthesis) |
| `commercial_facts.stock` (**post-approval changes**) | dedicated item-level quantity-change endpoint (`.../360034156253-상품-아이템별-수량-변경`), **not** the creation field | CONFIRMED (Phase 2 doc §2.5) |
| product images (no Phase 1 field today, see §5) | `items[].images[]` (exact schema `UNKNOWN`) | UNKNOWN |
| `platform_packages.coupang.detail_description` | `items[].contents[]` or a top-level detail field (`UNKNOWN` which) | UNKNOWN |
| `product.notice_information.*` | `items[].notices[]` with `noticeCategoryName` / `noticeCategoryDetailName` / `content` sub-fields | CONFIRMED (official channel, search-synthesis only), resolved dynamically via the Category Metadata Query API (Phase 2 doc §2.7) |
| `commercial_facts.shipping` | `deliveryMethod`, `outboundShippingTimeDay` (exact full set `UNKNOWN`) | INFERRED |
| return address (no Phase 1 equivalent field exists today) | `returnCenterCode` (+ `returnZipCode`/`returnAddress`, exact set `UNKNOWN`) | INFERRED |
| `platform_packages.coupang.search_keywords` | `items[].searchTags` (exact key `UNKNOWN`) | INFERRED |
| `product.seller` | `vendorId` | CONFIRMED (official channel, search-synthesis only) |
| approval workflow state (no Phase 1 equivalent — Phase 1 never models "approved"/"temp-save") | `requested` boolean at create/modify time | CONFIRMED (Phase 2 doc §2.4); always `false` in an adapter per §3.3's proposal, never sourced from Phase 1 |
| fulfillment model (no Phase 1 field today) | implicit in which Product Creation/Modify variant is called (standard vs. Rocket Growth hybrid) | CONFIRMED (existence only, Phase 2 doc §2.4); Phase 1 has no source fact for this at all |

## 3. Fail-closed rule (restated for this payload-building step)

`PROPOSAL`, restating Phase 1's existing truth/source/freshness gate contract
(`COMMERCE_PHASE_1_CONTRACT.md` §3) as it applies specifically to a future Coupang payload builder:
**a value may appear in the Coupang payload if and only if it is present in Phase 1's `accepted`
fact set — i.e. it already passed presence, source, verification, freshness, consistency, and
rights/compliance gating inside `CommerceModule` and is reflected in `platform_packages.coupang`.**
A payload builder must never independently read `raw` request data, never re-derive a value from an
unverified source, and never fill a Coupang-required field (`displayCategoryCode`,
`sellerProductName`, item price/stock, notices, required purchase options) with a default,
placeholder, or inferred value merely because the platform payload has no tolerance for an empty
field. If a platform-required field has no corresponding accepted Phase 1 fact, the correct behavior
is to **block that field and the whole product's Coupang submission** (`missing_required_field` or
the more specific code from §1), never to synthesize a plausible-looking value. This applies with
particular force to Coupang's **post-approval item-level price/stock split** (§2): a builder must
never write a stale creation-time price/stock value into the item-level endpoints either — every
write, at either stage, is subject to the same freshness re-check Phase 1 already performs, re-run
at build/submission time rather than trusted from `commerce_result.generated_at`, exactly as
`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.10 already proposes.

## 4. Coupang-specific structural notes

### 4.1 Item-centric model, not product-centric

`CONFIRMED (existence only)` per Phase 2 doc §2.4/§2.5: Coupang's payload is built around an
`items[]` array — even a single-variant product registers as one `items[]` entry with its own
`vendorItemId` (issued only after approval). This is materially different from a flat product
record and means Phase 1's `platform_packages.coupang.options` (currently a simple list of option
value strings, per `commerce_module.py::_package`) must map to **one array entry per purchasable
item**, not a flat option list — a real structural transform, not a rename.

### 4.2 Two-phase workflow: temp-save then approval-request

`CONFIRMED (existence only)` per Phase 2 doc §2.4: a product is created in a temporary-save state;
a separate approval-request step (`requested=true`, or a distinct call) moves it toward listing
exposure. Per `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.3's proposal (restated here as this
contract's own requirement): **a payload builder must always submit `requested=false`** so a
human/dry-run gate always sits between temp-save and the approval-request step, regardless of what
the raw API technically permits in one call.

### 4.3 Post-approval price/stock changes are structurally separate

`CONFIRMED` per Phase 2 doc §2.5, one of the best-evidenced facts in this entire research area: once
a product reaches "승인완료" (Approval Completed) status, the general Product Modification API
**cannot** alter price/inventory — those changes must go through dedicated item-level endpoints
(`vendorItemId`-scoped). A Coupang payload/update builder must branch on product lifecycle state:
pre-approval facts go through create/modify; post-approval price/stock facts go through the
item-level endpoints exclusively. Writing a stale or newly-changed price to the wrong endpoint after
approval is a documented, confirmed failure mode, not a hypothetical one.

### 4.4 Required purchase options: a live, moving policy

`CONFIRMED (existence only)` per Phase 2 doc §2.7, dated 2026-02-02: certain categories now mandate
required purchase-option entry, with escalating enforcement (registration rejection on omission).
`PROPOSAL`: this document introduces `required_purchase_option_missing` as a new platform-specific
`blocked_reasons` code (distinct from the generic `missing_required_field`) precisely because this
is a *policy-driven*, category-conditional requirement layered on top of the base schema, and
because it is explicitly called out as a moving target that needs re-verification close to
implementation time (Phase 2 doc §2.7's own note), not a one-time-confirmed static fact.

### 4.5 Rate-limit and retry implications for a payload builder

`CONFIRMED` per Phase 2 doc §2.11: Coupang applies stricter, block-triggering rate limits
specifically to product create/edit/query and price/stock-change endpoints (since 2023-10-12). Any
future adapter built from this contract must not retry aggressively against exactly the endpoints
this document maps to (§2) — this is a `PROPOSAL` constraint on the *adapter*, not on the contract
shape itself, but is recorded here because it directly affects how confidently a payload builder can
assume a submission "went through" without conservative backoff.

## 5. Fields remaining UNKNOWN or blocked pending platform confirmation

- Exact `items[]` sub-schema: the precise split between `itemName`/`vendorItemName`, exact
  price/quantity key names, exact `images[]`/`contents[]`/`notices[]` sub-schemas (§1, §2).
- Exact image requirements (dimensions, format, count, background rules) and upload mechanism
  (`UNKNOWN` per Phase 2 doc §2.6) — and, as with SmartStore, Phase 1 has **no image fact type at
  all** in its current input contract (`COMMERCE_PHASE_1_CONTRACT.md` §2), which is a genuine
  contract gap this document does not resolve, only records.
- Exact detail-description mechanism (HTML block vs. structured `contents[]` array) (§2).
- Exact return-center/shipping-place schema and whether it is a per-product field or a seller-profile
  reference (§1, §2).
- Exact `deliveryMethod`/shipping sub-schema beyond the partial names found (§2).
- Exact `searchTags` key name and any per-tag constraints (§2).
- HMAC signing details are `CONFIRMED` (Phase 2 doc §2.3) but out of scope for payload *shape* — they
  block real submission, not this contract's field design.
- Fulfillment-model taxonomy (Marketplace vs. Rocket Growth hybrid) — Phase 1 has no concept of this
  at all today (Phase 2 doc §3.16); this contract's `rocket_fulfillment_model_undetermined` code is a
  placeholder pending that taxonomy being defined, not a fully resolved classification.
- Approval SLA/turnaround and sandbox/test-environment availability (Phase 2 doc §2.12/§4) — blocks
  Phase 2B/2C, not Phase 2A payload-shape design.

Every item above is a `CTO GATE` before real implementation, per
`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §4's Phase 2A entry criteria (leave any field dependent on
an unresolved gap explicitly marked `pending_confirmation` in a generated payload artifact rather
than guessed).

## 6. Cross-check against Phase 1's existing Coupang minimum readiness

`CONFIRMED` (from `COMMERCE_PHASE_1_CONTRACT.md` §6.2, unmodified): Phase 1 already requires
verified `product_name`, `category`, `brand`, `manufacturer`, `model_name`, `country_of_origin`,
vendor-option text, category notice information, and a non-empty detail description before
`platform_packages.coupang.status` can be `ready_for_manual_upload`. Every field this document
classifies **Required** in §1 either already matches that existing Phase 1 minimum, or (price,
stock, images, shipping, required purchase options) is a field Phase 1 gates at the fact level via
`ALWAYS_VOLATILE`/`SENSITIVE` handling in `CommerceModule` even though it is not yet enumerated in
the platform-package minimum list, or (fulfillment model, required purchase options) is a genuinely
new Coupang-specific concept Phase 1's current `PLATFORM_NOTICE` constant
(`("manufacturer", "country_of_origin", "model_name")` for Coupang) does not yet cover. This
document does not propose loosening or replacing Phase 1's existing gate — it only maps what a
downstream payload builder would need on top of an already-`ready_for_manual_upload` Phase 1
package, and flags where Coupang's real requirements (§4.4) already exceed what Phase 1's current
`PLATFORM_NOTICE` set checks.
