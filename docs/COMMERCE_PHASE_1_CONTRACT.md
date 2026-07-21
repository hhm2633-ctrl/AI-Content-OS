# Commerce Phase 1 Contract

## 1. Decision and scope

Commerce Phase 1 is an offline, standalone content-package generator for SmartStore and Coupang.
It converts user-supplied, source-backed product facts into platform-specific copy and a manual
upload checklist. It may read existing Knowledge, Brand DNA, and Content patterns, but it does not
write to those stores and is not connected to `WorkflowEngine`.

Phase 1 does **not** log in, crawl a marketplace, call a marketplace API, use OAuth, create or
publish an affiliate link, automate a browser, or upload/update a listing. Its terminal outcome is
either a manual-upload package or an honestly blocked package.

## 2. Input contract

The module accepts one `commerce_request` object.

```json
{
  "request_id": "merchant-defined-id",
  "requested_at": "ISO-8601 timestamp with timezone",
  "target_platforms": ["smartstore", "coupang"],
  "product": {
    "product_id": "merchant SKU or stable local identifier",
    "brand": "verified brand",
    "manufacturer": "verified manufacturer",
    "model_name": "verified model/model number",
    "category": "verified category",
    "product_name": "verified base product name",
    "seller": "verified seller",
    "country_of_origin": "verified origin",
    "facts": [],
    "options": [],
    "specifications": [],
    "usage": [],
    "cautions": [],
    "notice_information": {}
  },
  "commercial_facts": {
    "price": null,
    "discount": null,
    "stock": null,
    "shipping": null,
    "benefits": []
  },
  "claims": [],
  "reviews": [],
  "sales_metrics": [],
  "sources": [],
  "freshness_policy": {},
  "search_seed_keywords": [],
  "learned_data": {
    "knowledge_enabled": true,
    "brand_dna_enabled": true,
    "content_patterns_enabled": true
  }
}
```

Each fact-like item (`facts`, `options`, `specifications`, `usage`, `cautions`, commercial facts,
claims, reviews, and sales metrics) must carry or reference:

- `field_id`: stable identifier within the request.
- `value`: the exact supplied value; null means unavailable.
- `source_ids`: one or more entries in `sources`.
- `verified_at`: ISO-8601 timestamp with timezone.
- `verification_method`: `document`, `merchant_input`, `manufacturer_source`,
  `marketplace_export`, or another explicit non-inferred method.
- `volatile`: boolean. Price, discount, benefit, shipping promise, stock, sales count, rating,
  review count, and ranking are always volatile.
- `expires_at`: required for a volatile fact unless the applicable `freshness_policy` supplies a
  deterministic maximum age.

Each `sources` entry contains `source_id`, `source_type`, `source_name`, `source_locator`,
`retrieved_at`, and `rights_or_permission`. All six fields are required for every source record;
a source without a recognized permission value is unusable for every fact. Recognized string
values are `merchant_authorized`, `merchant_owned`, `owned`, `licensed`, `permitted`, `granted`,
and `permission_confirmed`. A structured permission object is accepted only when `confirmed: true`
or `status` is one of `owned`, `licensed`, `permitted`, or `granted`. Credentials and secret tokens
are forbidden.
`source_locator` may be a URL, local document path, merchant record ID, or export ID, but the
generated customer-facing copy must not expose private local paths or credentials.

## 3. Truth, source, and freshness gates

A value is usable only when all applicable gates pass:

1. **Presence:** the value is non-empty and has the required type/unit/currency.
2. **Source:** every referenced source exists and identifies the origin of the value.
3. **Verification:** `verified_at` and `verification_method` are present.
4. **Freshness:** a volatile value is not past `expires_at` and does not exceed its configured
   maximum age at generation time.
5. **Consistency:** conflicting source values are not silently reconciled; the field is blocked
   until a human selects or re-verifies the authoritative value.
6. **Rights/compliance:** review quotes, images, certifications, and claims have documented use
   permission and required attribution/disclosure.

Unverified, stale, contradictory, or unsupported values must never be guessed, generalized, or
rephrased as fact. In particular, the generator must not invent price, discount, efficacy,
certification, review, rating, sales volume, ranking, purchase claim, benefit, stock, delivery
promise, scarcity, or option availability. Such fields are omitted from customer-facing copy,
listed in `missing_fields`, and produce a relevant `blocked_reasons` entry. `unavailable` is the
canonical internal value when confirmation is absent.

Stable facts may remain usable under the request's policy, but the generation result still records
their source and verification time. A headline, benefit, FAQ, CTA, keyword, or product name cannot
bypass these gates merely because it is marketing copy.

`search_seed_keywords` is customer-facing copy, not trusted metadata. A plain seed cannot establish
a product claim. Seeds containing or implying price/discount, stock/scarcity, sales volume,
ranking, rating/review, efficacy/treatment, certification/approval, shipping promise, or guaranteed
benefit are rejected fail-closed with `unsupported_claim` and are never emitted. Non-claim
descriptive seeds may be used only after normalization and prohibited-expression review.
Normalization must apply Unicode compatibility normalization (NFKC), case folding, removal of
zero-width characters, and whitespace/punctuation folding before matching Korean and English
claim synonyms. Formatting differences must never turn a prohibited claim into an allowed seed.
Semantic ranking, sales-volume, endorsement, and discount phrases are included even when they do
not use the canonical nouns. Examples that must fail closed include `BEST SELLER`, `No. 1`,
`NUMBER ONE`, percentage-`OFF` offers, `TOP PICK`, `판매 일등`, and `가장 많이 팔린`.

## 4. Read-only learned-data application

Commerce may read, never update, the following local inputs:

- Knowledge through the existing read-only Knowledge interface or an immutable snapshot.
- Brand DNA preferences and `config/brand_profile.json` for voice, tone, CTA style, and banned
  words.
- Existing Content patterns for structural guidance only.

Learned data may influence wording, order, tone, hook shape, CTA style, and keyword candidates. It
must not supply or override product facts, commercial facts, claims, reviews, rankings, or platform
policy. Product truth always wins over a learned pattern.

Every result includes `learned_data_metadata`:

```json
{
  "application_mode": "read_only",
  "knowledge": {
    "enabled": true,
    "available": true,
    "source_path_or_interface": "KnowledgeInterface",
    "snapshot_updated_at": "ISO-8601 or null",
    "record_ids": [],
    "applied_record_ids": [],
    "fallback_used": false,
    "reason": ""
  },
  "brand_dna": {
    "enabled": true,
    "available": true,
    "source_path_or_interface": "BrandDNAInterface/brand_profile",
    "snapshot_updated_at": "ISO-8601 or null",
    "applied_preferences": [],
    "fallback_used": false,
    "reason": ""
  },
  "content_patterns": {
    "enabled": true,
    "available": true,
    "source_path_or_interface": "existing Content contracts",
    "snapshot_updated_at": "ISO-8601 or null",
    "applied_patterns": [],
    "fallback_used": false,
    "reason": ""
  },
  "writes_performed": false
}
```

Missing/corrupt learned data is a non-fatal fallback: generate from verified product facts and the
safe default tone, record the reason, and never mutate the source store.

## 5. Canonical detail-page content

`detail_page` contains these ordered sections:

1. `headline`: verified product/category value proposition without unverified superlatives.
2. `problem`: a customer situation, not an invented diagnosis or guaranteed problem statement.
3. `benefits`: benefits directly traceable to verified facts/claims; each item has `source_ids`.
4. `features`: factual product characteristics with provenance.
5. `specifications`: value/unit pairs; unavailable required specs remain missing rather than filled.
6. `usage`: supplied instructions only; safety-relevant omissions block readiness.
7. `cautions`: supplied warnings, restrictions, storage/safety notes, and required disclaimers.
8. `faq`: answers constrained to verified inputs; unanswered questions state that confirmation is
   required.
9. `cta`: a manual-purchase CTA without false urgency, scarcity, discount, or guarantee.

Every section has `status` (`ready`, `partial`, `blocked`), `items` or `text`, and `source_ids`.
Empty required sections are retained as blocked metadata but omitted from publishable detail text.

## 6. Output contract

The canonical result is saved under `storage/commerce/<request_id>/commerce_result.json` with
UTF-8 text companions in the same request directory. Implementations must sanitize `request_id`
before using it as a path component and must not overwrite a different request implicitly.
The same normalized identifier is the only identifier allowed in `result.request_id`, every
`manual_upload_text_path`, `output_paths`, and any other customer-visible or persisted metadata
path. The raw identifier must never be interpolated into an output path.
An already-safe identifier containing only the approved ASCII identifier characters may remain
stable. An identifier containing path separators, traversal, control/Unicode ambiguity, or
secret-like material must be replaced by an irreversible opaque identifier derived from a
cryptographic digest; sanitizing it by merely replacing separators is insufficient because secret
fragments could remain customer-visible.

```json
{
  "module": "CommerceModule",
  "phase": "commerce_phase_1",
  "request_id": "...",
  "generated_at": "ISO-8601 timestamp with timezone",
  "status": "ready_for_manual_upload | partial | blocked",
  "upload_mode": "manual_only",
  "auto_upload_performed": false,
  "source_summary": {},
  "freshness_summary": {},
  "learned_data_metadata": {},
  "detail_page": {},
  "platform_packages": {
    "smartstore": {},
    "coupang": {}
  },
  "manual_upload_checklist": [],
  "missing_fields": [],
  "blocked_reasons": [],
  "output_paths": []
}
```

`missing_fields` entries contain `field`, `platforms`, `required`, `reason`, and
`required_action`. `blocked_reasons` entries contain `code`, `field`, `platforms`, `severity`,
`message`, and `required_action`. Stable codes include `missing_required_field`,
`missing_source`, `missing_source_rights`, `missing_verification_time`, `stale_volatile_fact`, `conflicting_sources`,
`unsupported_claim`, `review_rights_unconfirmed`, `notice_information_incomplete`, and
`external_upload_not_approved`.

`status` is `blocked` when any platform-required or safety/compliance field fails; `partial` when
safe copy exists but at least one requested optional field is omitted; otherwise it is
`ready_for_manual_upload`. The latter never means platform-published.
Verified non-blank `product.brand`, `product.product_name`, and `product.seller` are canonical hard
gates. Missing or blank values produce structured `missing_required_field` entries. Their
`platforms` scope is limited to the platforms requested by the current request.
Each identity fact must explicitly cover every requested platform. An accepted SmartStore-only
identity fact cannot satisfy the corresponding Coupang hard gate, and the resulting blocker is
scoped only to the uncovered platform.

### 6.1 SmartStore package

`platform_packages.smartstore` contains:

- `status` and platform-specific `missing_fields`/`blocked_reasons`.
- `product_name`: verified brand/model/category components plus safe descriptive terms.
- `search_keywords`: deduplicated candidates derived from verified facts and supplied seeds; no
  unverified performance/ranking/discount terms.
- `options`: verified option names, values, SKU mapping, and availability only when fresh.
- `detail_description`: ordered text generated from the canonical detail-page sections.
- `notice_information`: supplied category-appropriate product disclosure fields, with omissions
  blocked rather than invented.
- `manual_upload_text_path`: `storage/commerce/<request_id>/smartstore_package.txt`.

Phase 1 minimum SmartStore readiness requires verified `product_name`, `category`, `brand`,
`manufacturer`, `country_of_origin`, `options`, category notice information, and a non-empty
detail description. SmartStore-specific missing fields and blockers remain inside this package;
they must not be copied from Coupang merely for schema symmetry.
`category` and at least one verified option applicable to SmartStore are hard ready gates.

### 6.2 Coupang package

`platform_packages.coupang` contains:

- `status` and platform-specific `missing_fields`/`blocked_reasons`.
- `product_name`: verified brand/model/category components and compliant factual descriptors.
- `search_keywords`: the same truth-gated candidate policy, formatted separately for Coupang.
- `options`: verified vendor item/option text only; no invented inventory or option mapping.
- `detail_description`: Coupang-specific ordering/formatting of the canonical sections without
  changing their claims.
- `notice_information`: supplied category disclosure text, retaining missing required fields as
  blockers.
- `manual_upload_text_path`: `storage/commerce/<request_id>/coupang_package.txt`.

Phase 1 minimum Coupang readiness requires verified `product_name`, `category`, `brand`,
`manufacturer`, `model_name`, `country_of_origin`, vendor-option text, category notice information,
and a non-empty detail description. Coupang uses its own field labels, keyword representation, and
detail ordering. A field required only by Coupang blocks only the Coupang package unless it is also
a canonical product-safety requirement.
`category` and at least one verified option applicable to Coupang are hard ready gates.

The two packages are separately rendered and separately gated. A ready SmartStore package does not
make a blocked Coupang package ready, and platform formatting must not change underlying facts.

## 7. Manual upload checklist

Checklist items contain `check_id`, `platform`, `label`, `required`, `completed` (always `false` at
generation unless backed by explicit user input), and `instructions`. At minimum:

- Recheck product identity, seller, model, category, and option mapping against the source.
- Re-verify current price, discount, benefits, shipping promise, and stock immediately before
  upload; omit any value that is no longer fresh.
- Confirm claims, certifications, cautions, and category notice information.
- Confirm review quotation authenticity, permission, attribution, and absence of personal data; if
  not confirmed, do not upload the quote.
- Confirm product/image rights and required platform disclosures.
- Review product name and search keywords for prohibited or unsupported claims.
- Preview each platform's detail text and option/notice layout in the seller UI.
- Record the human reviewer and review time outside the generated copy.
- Upload manually in the relevant seller UI and separately record the resulting listing ID/status.

The checklist is preparation data only. Phase 1 never marks upload execution complete.

## 8. Failure and storage behavior

Malformed input, missing learned data, or file-write failure must be represented as result data
where possible rather than product-copy fabrication. Input validation happens before customer-facing
copy generation. A storage failure sets `status: blocked` and records a `storage_write_failed`
reason; it must not redirect output into Knowledge, Brand DNA, Publishing, or workflow storage.
All Commerce artifacts remain under `storage/commerce/`. Saving a request is atomic at the package
level: write every JSON/text companion to a temporary request directory, flush/close all files, and
only then replace the final request directory. If any write or replace fails, remove the temporary
directory, leave no newly generated partial package, return no successful output paths, and record
`storage_write_failed`. An already-complete package for the same request must remain intact when a
replacement attempt fails.
The staged `commerce_result.json` must already contain the same final `output_paths` returned to the
caller. Persisted and runtime metadata must not disagree after a successful atomic replacement.

Temporary-directory cleanup is part of the storage contract. If cleanup itself fails, the result
must additionally record a structured `storage_cleanup_failed` blocker. Customer-visible
`storage_error` is a fixed sanitized diagnostic code/message only. Raw exception text, absolute
operating-system paths, credentials, tokens, source locators, and other secret-like strings must
never be copied into result JSON.

## 9. Phase 2 CTO approval gate

Any real SmartStore/Coupang connection remains Phase 2 and requires explicit CTO approval before
implementation. Approval requires, at minimum:

- named workflow owner and measurable ROI;
- official platform API/partner capability and policy review;
- user-approved seller/account ownership, authentication, secret storage, and least privilege;
- product-data source approval, freshness SLA, conflict resolution, and stale-data rollback;
- legal/compliance review for claims, notices, images, reviews, and affiliate disclosure;
- sandbox/staging test plan, idempotency, audit log, dry-run, rollback, rate-limit, cost, and vendor
  failure controls;
- explicit decision on whether listing creation, update, inventory, price, and order scopes are
  individually allowed.

Until that gate is approved and recorded, `upload_mode` remains `manual_only`,
`auto_upload_performed` remains `false`, and any request for automated upload receives
`external_upload_not_approved`.
