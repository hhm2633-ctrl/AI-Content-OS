# BrandConnect / Shopping Connect Phase 1 Contract

Date: 2026-07-12  
Status: human-assisted, offline package builder only  
Schema: `brandconnect_phase_1.v1`

## 1. Decision and boundary

Phase 1 converts a manually supplied Naver Brand Connect campaign brief into reviewable creator and
seller packages. It does not log in, apply to a campaign, issue or alter a Shopping Connect link,
scrape Naver, send a message, publish content, or obtain statistics. `network_used` and
`actual_publish` are always `false`.

The two accepted modes are deliberately separate:

- `creator_campaign`: campaign compensation such as cash/manuscript fee and product provision.
- `shopping_connect`: a SmartStore product promotion whose creator income is a separately configured
  affiliate commission. Phase 1 never invents a rate or treats campaign compensation as commission.

The builder may reuse upstream content artifacts, but it is not a replacement Trend/Research,
Content, CardNews, Shorts, Publishing, Commerce, Compliance, or Affiliate engine. Compliance and
Affiliate results enter only through adapter-status fields. Their current NO-GO/unavailable state is
fail-closed.

## 2. Evidence classification

### Officially confirmed

The project evidence matrix records the following from Naver's official creator, seller, terms, and
operating-policy pages (checked 2026-07-12):

- creators can receive campaign compensation as cash/manuscript fee, product provision, or both;
- Shopping Connect is a separate sales-commission path and its product-specific promotion link is
  issued in the Naver Brand Connect UI;
- the seller path is tied to SmartStore, and sellers select participating products and configure the
  use-fee/commission terms;
- economic-interest disclosure is required;
- link manipulation, rewarded/invalid clicks, abnormal traffic, rights violations, PII exposure,
  misleading or exaggerated claims, authority resale/sharing, and external disclosure of Naver's
  Shopping Connect statistics are prohibited;
- product participation and payout conditions can change, including during a month;
- confirmed purchases are measured by calendar month, then cancellations and returns are excluded
  before settlement; this supports a draft ledger lifecycle, not synthetic performance data.

Official sources:

- https://brandconnect.naver.com/about/creator
- https://brandconnect.naver.com/about/partner
- https://brandconnect.naver.com/service/term/creator
- https://brandconnect.naver.com/service/term/affiliate/creator
- https://brandconnect.naver.com/service/policy/affiliate/creator (`2025.03` displayed policy)

### UNKNOWN and therefore not automated

The public login/link-issuance API, public product feed, report export API/schema, machine-readable
policy-change feed, exact account eligibility, current campaign-specific channel acceptance, and any
current product rate/status not supplied with evidence remain `UNKNOWN`. The first four official
pages above were blocked from automated retrieval during this review; their claims are taken only
from the dated project evidence matrix. The operating-policy page was retrievable. Phase 1 must not
upgrade any UNKNOWN to confirmed.

## 3. Input contract

The request is a JSON-serializable mapping. Required common fields identify the request, mode,
channel, campaign, evidence time, deadline, disclosure, content requirements, rights/claim/traffic
evidence, creator/seller/product identities, and ownership evidence. Caller-declared readiness booleans
are compatibility input only and never constitute approval. A campaign brief normalizes at least:

`required_keywords`, `required_keyword_count`, `required_image_count`, `required_video`,
`required_map`, `required_link`, `disclosure_required`, `deadline`, and `compensation`.

Times must include a timezone. Missing campaign terms, missing or naive timestamps, and expired
deadlines fail closed. Product status and configured commission/use-fee inputs require `checked_at`;
the output retains `recheck_required: true` because they may change during the month. Rates, sales,
orders, conversion, or performance must never be inferred.

Shopping Connect additionally identifies the SmartStore product and its manual link state. A
human-attached link is accepted only as an opaque value for review; it is never generated, shortened,
rewritten, refreshed, or validated by network access.

The accepted redacted test shape is an opaque `https://naver.me/REDACTED_PATH`: exact HTTPS scheme,
exact `naver.me` host, and a nonempty opaque path, with no credentials, query, or fragment. Invalid
links are omitted/redacted rather than echoed. The system preserves an accepted string without parsing
tracking components, following redirects, resolving a destination, sending HEAD/GET requests, or
clicking it. The receipt records `manual_link_attached`, `link_source`, `attached_by`, `attached_at`,
`owner_scope`, `owner_creator_id`, `owner_product_id`, `tamper_checked`, and
`disclosure_present`. Creator/product owner mismatch, cross-creator or cross-product reuse, and any
generated sub-id/hash fail closed. Outputs, logs, and the ledger must never add an expanded
destination or expose/query-derive `NaPm`, `trx`, or `hk` material.

## 4. Required output

Every result contains:

- `creator_delivery_package`: channel deliverables and a normalized requirement checklist;
- `seller_campaign_package`: seller identity boundary, SmartStore product, configured commission/use
  fee, and creator campaign brief as distinct records;
- `manual_actions`: Naver UI link issuance/attachment, disclosure placement, policy/rate recheck,
  and final approval steps;
- `policy_receipts`: source, evidence status/version/check time, and gate decisions;
- `disclosure_text`: supplied economic-interest wording, never a claim of legal approval;
- `revenue_ledger_draft`: creator campaign compensation and affiliate commission as separate lines;
- `blocking_reasons`, `warnings`, and `publish_ready`;
- `network_used: false` and `actual_publish: false`.

For Shopping Connect the contract always emits `manual_link_required: true` and
`link_generation_location: naver_brandconnect_ui`. A draft ledger may model
`purchase_confirmed`, `cancelled`, `returned`, `settlement_confirmed`, and `paid` transitions, but
amounts/counts remain null unless supplied later by an approved source. It is neither Naver
statistics nor evidence of revenue.

## 5. Policy gates

The most restrictive result wins. Blocking checks cover missing or unapproved disclosure; restricted
channel/category; false, exaggerated, or misleading claims; exposed PII; invalid content/image
rights; missing campaign terms; invalid or expired deadlines; stale/monthly rate recheck; absent or
tampered manual link; attempted external statistics disclosure; rewarded clicks or abnormal traffic;
authority sharing/resale; and internal errors. Secret-like values and local paths must not be echoed
into outputs or errors.

Boolean flags are not accepted as proof that content is safe. Phase 1 deterministically scans the
title/body/claim text for conservative PII, deceptive/exaggerated-claim, and rewarded-click patterns,
then requires the corresponding manual-review evidence. A clean scan is not a legal or factual
approval; ambiguous content remains a human gate.

Approval is receipt-based. Compliance, Affiliate, human approval, and approved disclosure-copy
receipts use `status`, `schema_version`, `receipt_id`, `input_hash`, `checked_at`, `issuer`, and
`trusted`. `trusted` defaults to `false`. Missing fields, unapproved status/issuer/schema, mismatched
input hash, or future `checked_at` fail closed. The disclosure rendered into the package must be an
approved exact copy covered by its receipt. Creator, seller, and SmartStore product identities plus
their ownership evidence are mandatory; self-declared identity strings alone do not establish scope.

`publish_ready` is true only when trusted upstream receipts validate all four gates and there are no
policy blocks:

```text
compliance_ready AND affiliate_ready AND human_link_attached AND human_approval
```

The positive Phase 1 path is therefore still manual. The current Compliance and Affiliate upstreams
are explicitly NO-GO, so Phase 1 cannot emit `publish_ready: true` for any input. This invariant stays
in force until a separately reviewed contract revision approves their issuers and schemas.

All supplied timestamps are bounded by the evaluation time. Future policy checks, link attachments,
or approval receipts are rejected. Normalization, copying, mapping access, and failure rendering are
inside one exception-safe boundary: hostile mapping/deepcopy behavior must produce only a redacted
`internal_error_fail_closed`, never a raw exception, request identifier, secret, or local path.

## 6. Revenue separation

Creator flow:

1. Campaign compensation is captured from the creator campaign contract.
2. Shopping Connect affiliate commission is captured independently from current, sourced product
   terms.
3. Neither is estimated and neither is merged into the other.

Seller flow:

1. The SmartStore product is a seller-owned contract record.
2. Configured commission/use fee is a volatile seller term with `checked_at` and recheck.
3. Creator recruitment/delivery brief remains a separate campaign record.

The ledger draft preserves these boundaries and cancellation/return reversals without generating
sales, clicks, purchases, settlement values, or Naver statistics. It is constructed from an explicit
allowlist. Inputs such as `estimated_sales`, `tracking_id`, estimated compensation, estimated reward,
or estimated commission are discarded. The request correlation identifier is a one-way digest and
cannot be used to recover a caller secret.

## 7. CTO gate before integration

Phase 1 may be integrated only after the CTO confirms the final Compliance adapter contract, the
Affiliate Revenue Router handoff, policy evidence freshness, allowed channels/categories, disclosure
copy and placement, rights provenance, secret handling, and the manual Naver UI operating procedure.
Any API adapter, browser control, real link issuance, statistics import, or publishing requires a
separate explicit approval and refreshed official evidence.

## 8. Phase 2 direction memo: Hybrid Execution candidate

Phase 1 remains human-assisted and offline, but this does **not** make BrandConnect permanently
manual-only. Phase 2 should treat it as a conditional `Hybrid Execution` candidate and choose the
least risky execution surface supported by current official evidence:

1. If Naver confirms a suitable official API, an approved API adapter is the preferred execution
   path.
2. If a required operation remains UI-only, link issuance, campaign application preparation, and
   draft entry may be evaluated behind a separately approved `BrowserAssistAdapter`.
3. Final campaign application, link issuance, publishing, and message transmission always stop at a
   human-approval edge before the external side effect.

No browser implementation is authorized by this memo. Before a Phase 2 BrowserAssist spike, the CTO
must approve all of the following contracts:

- credentials never enter an LLM prompt, model-visible context, task result, log, or repository;
- browser authentication uses an opaque credential lease or trusted autofill boundary;
- permissions are task-scoped and limited to the named Naver site and approved action;
- every external action produces an action audit and post-action readback receipt;
- approval is bound to the exact account, campaign, product, link task, content revision, and action;
- rollback, expiry, revocation, failure recovery, and account-owner responsibility are defined.

CAPTCHA or terms bypass, bot-evasion, automatic link clicking or redirect resolution, tracking
parameter inspection/manipulation, credential sharing, and bulk posting remain prohibited. Until an
official API or a BrowserAssist contract passes refreshed policy, security, account-owner, and
Independent QA gates, the implemented Phase 1 invariants remain unchanged:
`network_used: false`, `actual_publish: false`, and no external side effects.
