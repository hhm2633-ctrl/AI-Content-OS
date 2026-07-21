# Affiliate Revenue Router Phase 1 Contract

Revision: Independent QA NO-GO correction pass (this Sprint). Section 9 records exactly what changed
and why; the rest of this document describes the corrected, current contract.

## 1. Decision and scope

Affiliate Revenue Router Phase 1 is an offline, standalone router that compares candidate
`AffiliateProgram`s and `MerchantOffer`s against a single `RoutingRequest`'s channel/region/category
context and reports which *exactly-referenced* (program, offer) pairings are `eligible`, need
`manual_review`, or are `rejected`. For every `eligible` pairing it produces a `TrackingLinkRequest`
(never a real tracking/affiliate/deep link) and a disclosure text; every `manual_review` pairing
instead gets a `manual_actions` entry (Section 5). It is implemented under `modules/affiliate/` and is
**not** wired into `WorkflowEngine`, `PublishingModule`, `modules/commerce/`, or
`modules/compliance/` -- standalone, on-demand, same pattern as those existing modules.

Phase 1 does **not** call any network API, log in to any affiliate network, load or store a
credential/API key, generate a real affiliate URL/deep link/sub-id, or perform any file I/O of its
own. Its terminal outcome is a structured routing result; a human issues the actual link in each
network's official UI before anything is published.

Design basis: `docs/RESEARCH/AFFILIATE/AFFILIATE_NETWORK_EVIDENCE_MATRIX.md` (2026-07-12,
revalidate 2026-08-11) and `docs/EXTERNAL_ENGINE_PORTFOLIO_STRATEGY.md`'s Affiliate Revenue Router
contract candidate.

## 2. Input contract

### 2.1 RoutingRequest

```json
{
  "request_id": "req-001",
  "channel": "blog",
  "region": "KR",
  "category": "electronics",
  "content_type": "review",
  "candidate_programs": [],
  "candidate_offers": [],
  "current_time": "2026-07-12T09:00:00+09:00",
  "human_approval": false,
  "disclosure_policy_verified": false
}
```

`current_time` must be a timezone-aware ISO-8601 string or `datetime`; if it is missing, naive, or
unparseable, the entire request is returned as `status: "blocked"`. `region`/`channel`/`category` are
normalized (region uppercased, channel/category lowercased) so casing never causes a spurious
mismatch. `human_approval` and `disclosure_policy_verified` both default to `false` (fail-closed) and
never change any candidate's `status` -- they only gate the request-level `publish_ready` verdict
(Section 6).

A request whose `candidate_programs` exceeds 50 entries, whose `candidate_offers` exceeds 200
entries, or whose evaluated (program, offer) pairs would exceed 200, is rejected outright as a
structural contract error (`affiliate_contract_invalid`) before any evaluation runs.

### 2.2 AffiliateProgram

```json
{
  "network_id": "linkprice",
  "program_id": "p1",
  "program_type": "product_affiliate",
  "merchant_id": "m1",
  "region": "KR",
  "currency": "KRW",
  "allowed_channels": ["blog", "instagram"],
  "restricted_categories": ["adult"],
  "attribution_window": "30d",
  "policy_version": "2026.07",
  "policy_evidence_url": "https://...",
  "policy_checked_at": "2026-07-11T09:00:00+09:00",
  "api_status": "confirmed",
  "enrollment": {
    "account_access_confirmed": false,
    "merchant_enrollment_confirmed": false,
    "product_enrollment_confirmed": false,
    "channel_allowed_confirmed": false,
    "evidence_checked_at": null
  }
}
```

`program_type` outside `product_affiliate`/`lead_cpa`/`global_retail`/`global_network` is preserved
and flagged `program_type_unrecognized` (manual review), never silently treated as
`product_affiliate`. `api_status` outside `confirmed`/`manual_only`/`unknown`/`blocked` collapses to
`"unknown"` during normalization -- fail-closed, never a guessed `"confirmed"`.

`enrollment` (new, Section 4) is required for a program to ever reach `eligible` -- see Section 4.
Every boolean sub-field must be an **actual `bool` `True`**; a string `"true"`, `1`, or any other
truthy-looking non-bool value is treated as `False` (NO-GO fix: fake-typed enrollment evidence must
never count).

`(network_id, program_id, merchant_id)` together are the program's identity key -- see Section 3.

### 2.3 MerchantOffer

```json
{
  "offer_id": "o1",
  "network_id": "linkprice",
  "program_id": "p1",
  "merchant_id": "m1",
  "product_id": "prod1",
  "title": "...",
  "canonical_url": "https://merchant.example.com/product/1",
  "image_url": "https://merchant.example.com/img/1.jpg",
  "category": "electronics",
  "region": "KR",
  "currency": "KRW",
  "price": 10000,
  "availability": "in_stock",
  "commission_type": "cps",
  "commission_value": 5.0,
  "valid_from": "2026-07-11T09:00:00+09:00",
  "valid_until": "2026-07-22T09:00:00+09:00",
  "source_url": "https://merchant.example.com/product/1",
  "source_timestamp": "2026-07-12T08:30:00+09:00",
  "rights_status": "owned"
}
```

`network_id`/`program_id`/`merchant_id` (new, required -- NO-GO fix) are the back-reference to the
one `AffiliateProgram` this offer belongs to. `price`/`commission_value` are coerced through a
`safe_number` check: a non-numeric, boolean, negative, `NaN`, or `Infinity` value silently becomes
`None`. `rights_status` means **image-usage permission only** -- it is never read as, and must never
be treated as, program-enrollment approval (Section 4; NO-GO fix rule 23).

## 3. Candidate matching: exact back-reference, not a Cartesian join

`MerchantOffer.network_id`/`program_id`/`merchant_id` must **exactly** match one
`AffiliateProgram.network_id`/`program_id`/`merchant_id` triple for that offer to be evaluated at
all. The old full cross-product of every candidate program against every candidate offer is removed.

- Any of the three back-reference fields empty on the offer -> **rejected**
  (`offer_missing_back_reference`), regardless of what programs were supplied.
- All three present but no `candidate_programs` entry has that exact triple -> **rejected**
  (`no_matching_program_reference`).
- Two programs may legitimately share a `program_id` if their `network_id` (or `merchant_id`)
  differs -- an offer's back-reference must match all three fields together, so it is never confused
  with the wrong program.

`candidate_id = "{network_id}:{program_id}:{merchant_id}:{offer_id}"` (each component sanitized) --
every candidate is fully identifiable by all four keys (NO-GO fix rule 5).

## 4. Priority program handling (capability ceiling + enrollment evidence)

Per the official evidence matrix, a declared `api_status` is capped **down** to a known ceiling; it
is never raised. **A network absent from this table now defaults to an `unknown` ceiling** (NO-GO
fix rules 6/7) -- a self-declared `"confirmed"` for an unregistered network is always ignored, never
trusted at face value:

| `network_id` | Ceiling | Rationale |
|---|---|---|
| `linkprice` | `confirmed` | POC GO 1 -- confirmed domestic product/deep-link API surface |
| `adpick` | `confirmed` | POC GO 2 -- confirmed official JSON API, key-authenticated |
| `naver_shopping_connect` | `manual_only` | Human-assisted only -- no public API/feed confirmed |
| `impact` | `manual_only` | Deferred -- confirmed strong API, but high global policy/PII-link-parameter risk |
| `tos` | `unknown` | Identity unresolved in the evidence matrix -- never guessed |
| *(any other network_id)* | `unknown` | **New default** -- never left uncapped |

`effective_status = min_rank(declared_status, ceiling)` using rank
`blocked(0) < unknown(1) < manual_only(2) < confirmed(3)`.

**Even a `confirmed`-ceiling network cannot reach `eligible` on API existence alone** (NO-GO fix
rule 8). Reaching `eligible` additionally requires *complete* `enrollment` evidence: all four boolean
sub-fields are `True` (real `bool`, never a truthy-looking string/int) **and** `evidence_checked_at`
parses as a timezone-aware date/time. Missing or incomplete enrollment evidence degrades the result
to `manual_review` (`enrollment_evidence_incomplete`) -- never an outright rejection, since a human
can still supply it. This is why even Linkprice/Adpick programs, despite their `confirmed` ceiling,
land in `manual_review` by default until enrollment evidence is actually recorded.

## 5. Gates (fail-closed, most-restrictive-wins)

Program/offer/pairing gate outcomes combine via "most restrictive wins"
(`rejected` < `manual_review` < `eligible`).

### 5.1 Program gates
1. `program_type == "lead_cpa"` -> **rejected** (`lead_cpa_blocked`), unconditionally, first.
2. `api_status` (post-ceiling, Section 4) `blocked`/`unknown` -> **rejected**; `manual_only` ->
   **manual_review**.
3. Missing `policy_version`/`policy_evidence_url`/`policy_checked_at` -> **manual_review**
   (`policy_metadata_incomplete`).
4. `policy_evidence_url` present but not a safe public URL (credential-embedded, `localhost`,
   private/loopback/reserved IP) -> **rejected** (`unsafe_policy_evidence_url`).
5. `policy_evidence_url` present, safe, but its domain does not match this network's confirmed
   official domain allowlist (new, Section 5.4) -> **rejected** (`policy_evidence_domain_mismatch`).
6. `policy_checked_at` present but not timezone-aware -> **manual_review**
   (`policy_checked_at_invalid_timezone`); **in the future** -> **rejected**
   (`policy_checked_at_future`, new); older than 30 days -> **manual_review** (`policy_stale`).
7. Requested `channel` not in `allowed_channels` -> **rejected** (`channel_not_allowed`).
8. Program `region` != request `region` (both normalized uppercase) -> **rejected**
   (`region_mismatch`).
9. Requested `category` in `restricted_categories` -> **rejected** (`restricted_category`).
10. `enrollment` evidence incomplete (Section 4) -> **manual_review**
    (`enrollment_evidence_incomplete`).

### 5.2 Offer gates
1. `canonical_url`/`source_url`/`image_url` present but not a safe public URL -> **rejected**
   (`unsafe_*_url`).
2. Offer `region`/`category` mismatch vs. the request -> **rejected**
   (`offer_region_mismatch`/`offer_category_mismatch`).
3. Any of `price`/`availability`/`commission_value` populated without both `source_url` and a valid
   timezone-aware `source_timestamp` -> **manual_review** (`source_evidence_missing`).
4. `source_timestamp` **in the future** -> **rejected** (`source_timestamp_future`, new). Otherwise,
   age past the conservative freshness windows below (this module's own operational default, not a
   network guarantee) -> **manual_review**: price 6h (`price_stale`), availability 1h
   (`availability_stale`), commission 24h (`commission_stale`).
5. `valid_until` already passed -> **rejected** (`offer_expired`); `valid_from` still in the future ->
   **rejected** (`offer_not_yet_valid`); either present but not timezone-aware -> **manual_review**
   (`offer_validity_timezone_invalid`).
6. `availability == "out_of_stock"` -> **rejected** (`offer_out_of_stock`); anything outside
   `in_stock`/`out_of_stock`/`preorder` -> **manual_review** (`availability_unknown`).
7. `rights_status` missing or outside the allow-list -> `image_usage_approved: false` +
   **manual_review** (`image_rights_unconfirmed`) -- **this blocks only image usage, never program
   eligibility** (rule 23; see Section 4's enrollment gate for the actual eligibility condition).

### 5.3 Pairing gate
- Offer `currency` != program `currency` -> **rejected** (`currency_mismatch`). The
  network/program/merchant back-reference match itself is enforced during candidate construction
  (Section 3), not repeated here.

### 5.4 Official policy domain allowlist (new)

```text
linkprice               -> linkprice.com
adpick                  -> adpick.co.kr
naver_shopping_connect  -> brandconnect.naver.com
impact                  -> help.impact.com
```

A network absent from this table has no confirmed domain to check against and is **not** checked
this way -- this module never invents an official domain for a network the evidence matrix didn't
confirm one for (NO-GO fix rule 14). The generic credential/localhost/private-IP safety check
(Section 5.1 item 4) still applies regardless.

## 6. Output contract

```json
{
  "schema_version": "affiliate_revenue_router_phase_1.v1",
  "request_id": "req-001",
  "status": "routed",
  "eligible_candidates": [],
  "rejected_candidates": [],
  "manual_review_candidates": [],
  "tracking_link_requests": [],
  "disclosure_texts": [],
  "manual_actions": [],
  "blocking_reasons": [],
  "warnings": [],
  "policy_receipts": [],
  "disclosure_policy_verified": false,
  "human_approval": false,
  "publish_ready": false,
  "network_used": false
}
```

Each candidate entry: `candidate_id`, `network_id`, `program_id`, `merchant_id`, `offer_id`, `status`
(`eligible`/`manual_review`/`rejected`), `reasons` (list of `{scope, code, message}`),
`commission_value` (sanitized float or `null`), `image_usage_approved` (bool).

`tracking_link_requests` and `disclosure_texts` are built **only for `eligible` candidates** (NO-GO
fix rule 15). A `manual_review` candidate instead gets one `manual_actions` entry
(`candidate_id`/`network_id`/`program_id`/`merchant_id`/`offer_id`/`action_required`/`reasons`) --
never a tracking artifact (rule 16). A `TrackingLinkRequest` echoes the offer's own `canonical_url`
as `destination_url`, sets `tracking_link_generated: false`, and states that a human must issue the
real link in the network's official UI.

`policy_receipts` records one entry per evaluated program (declared vs. effective `api_status`,
whether the capability ceiling applied, and the policy metadata as supplied) -- `policy_evidence_url`
is replaced with `"***REDACTED_UNSAFE_URL***"` (or `null` if absent) whenever it is not a safe public
URL, even for a program that ends up rejected (NO-GO fix rule 13; never surface a credential-bearing
URL in an audit artifact).

`request_id` is echoed back unchanged **unless** it looks like it might carry a secret, a JWT, or a
filesystem path (three base64url segments joined by dots; a `/`, `\`, or `..`; a
token/secret/api-key/password/credential/auth keyword; or a bare high-entropy 32+ character token) --
in that case it is replaced by a deterministic, irreversible `"opaque:<16-hex-char sha256 prefix>"`
token (NO-GO fix rule 12). The same substitution is applied before building any composite id (e.g.
inside a `TrackingLinkRequest`'s own `request_id`).

## 7. `publish_ready` -- two additional required signals (NO-GO fixes)

`publish_ready` is `true` only when **all** of the following hold:

1. at least one `eligible` candidate exists;
2. top-level `blocking_reasons` is empty;
3. every eligible candidate's `candidate_id` has a matching `disclosure_texts` entry;
4. `disclosure_policy_verified` is `true` (NO-GO fix rule 17: the auto-generated disclosure
   boilerplate existing for every eligible candidate is not, by itself, sufficient -- a human/legal
   reviewer must separately confirm it against the network's actual disclosure policy);
5. `human_approval` is `true` (NO-GO fix rule 18).

A pending `manual_review` candidate elsewhere in the same result does not, by itself, block
`publish_ready` for an *already*-eligible candidate -- it is additional information (surfaced via
`manual_actions`), not a blocker on candidates that already passed every gate.

## 8. Prohibited actions (never implemented here)

Real network API calls, login/OAuth, credential or API-key loading/storage, real affiliate/deep-link
or sub-id generation, browser automation, CPA/lead-form/PII collection, and treating an
unverified/UNKNOWN network fact -- or a self-declared `api_status`/enrollment flag for an
unregistered/unconfirmed network -- as `confirmed`.

## 9. Independent QA NO-GO correction record (this Sprint)

| # | Before | After |
|---|---|---|
| 1-5 | `MerchantOffer` had no `network_id`/`program_id`/`merchant_id`; every candidate program was cross-joined against every candidate offer | Offers carry required back-references; only the exact-matching (program, offer) pair is evaluated; a missing/mismatched reference rejects that offer; `candidate_id` includes all four keys |
| 6-7 | A network absent from the ceiling table passed its declared `api_status` through unchanged (a self-declared `"confirmed"` stood as `"confirmed"`) | Defaults to an `"unknown"` ceiling -- always capped, never trusted at face value |
| 8-10 | A `confirmed`-ceiling program (Linkprice/Adpick) could reach `eligible` from policy/region/channel checks alone | Also requires complete `enrollment` evidence (5 fields); missing/incomplete evidence -> `manual_review`, not `eligible` |
| 11 | No future-timestamp check for `source_timestamp`/`policy_checked_at` (only staleness) | Both rejected outright when in the future |
| 12 | Top-level `request_id` was always echoed verbatim | Secret/JWT/path-shaped ids are replaced with a deterministic, irreversible opaque token |
| 13 | `policy_receipts.policy_evidence_url` echoed the raw value, including unsafe/credential-bearing URLs | Masked to `"***REDACTED_UNSAFE_URL***"` (or `null`) whenever unsafe |
| 14 | No official-domain check on `policy_evidence_url` | Confirmed-domain allowlist per network (Section 5.4); unlisted networks are not checked this way (never invented) |
| 15-16 | `manual_review` candidates got a `TrackingLinkRequest` + disclosure text, same as `eligible` ones | Only `eligible` candidates get those; `manual_review` candidates get a `manual_actions` entry instead |
| 17-18 | `publish_ready` only checked disclosure-text presence (always true by construction) | Also requires explicit `disclosure_policy_verified` **and** `human_approval` |
| 19-20 | No input-size limits | `candidate_programs` <= 50, `candidate_offers` <= 200, evaluated pairs <= 200, else a structured `affiliate_contract_invalid` blocker |
| 21 | A duplicate program/offer id was deduplicated (first wins), no error | Contract blocker: the whole request is rejected |
| 22 | `region` was not case-normalized (`"kr"` vs `"KR"` could spuriously mismatch) | Uppercased everywhere it's compared |
| 23 | Not explicitly documented | `rights_status` means image-usage permission only; the enrollment-evidence gate (Section 4) is the only path to `eligible` |
| 24 | N/A | Still true: no real link/API/network call anywhere in this module |

Note on the evaluated-pairs limit (rules 19/20): because candidate matching is now an exact
back-reference join (Section 3) rather than a Cartesian product, the number of evaluated pairs can
never exceed the number of offers -- the 200-pair limit is therefore currently always reached via (or
before) the 200-offer limit. It is kept as an independently-checked, separately-named constant for
Section 2.1 compliance and to remain a real, independent guard if a future Phase ever reintroduces
any one-offer-to-many-programs fan-out.

Test suite: `tests/test_affiliate_revenue_router.py` grew from 49 to 80 tests covering every row
above plus the original regression set. `py -m unittest tests.test_affiliate_revenue_router -v` and
`py -m compileall modules/affiliate` both pass cleanly.
