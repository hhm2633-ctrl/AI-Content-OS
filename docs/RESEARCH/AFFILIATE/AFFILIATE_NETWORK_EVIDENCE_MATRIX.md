# Affiliate Network Evidence Matrix and Phase-1 POC Input Contract

## 1. Decision, scope, and evidence labels

Date: 2026-07-12  
Evidence checked at: `2026-07-12T00:00:00+09:00`  
Mandatory revalidation date: `2026-08-11`  
Status: research and input-contract proposal only. No registration, login, credential issuance, API call, browser automation, link publication, lead collection, or payout operation was performed.

This registry covers the 19 names supplied by the CTO. It is separate from seller upload and does not authorize a runtime Affiliate Engine.

- `CONFIRMED`: actual content from an official operator, developer, help, policy, or government page was retrieved and supports the specific claim.
- `UNKNOWN`: the capability, identity, current policy, or public URL was not confirmed from an official source in this pass.
- `PROPOSED`: an AI-Content-OS design recommendation, not a platform fact.

Search snippets, third-party articles, community posts, and plausible product behavior are not evidence. A platform-level capability does not mean every advertiser/program enables it. Account approval, program contract, region, and channel restrictions remain independent gates.

## 2. Classification of all 19 candidates

| # | Candidate | Primary group | Identity/status | Phase-1 disposition |
|---:|---|---|---|---|
| 1 | 링크프라이스 | 국내 상품제휴 | `CONFIRMED` official affiliate network pages | **POC GO 1**: offline contract/fixture only |
| 2 | 애드픽 | 국내 상품제휴 | `CONFIRMED` official Adpick/Adpick Biz pages | **POC GO 2**: offline contract/fixture only |
| 3 | 텐핑 | 국내 상품제휴 | `CONFIRMED` CPS/participation campaigns and generated promotion URLs | HOLD: mixed CPS/CPA requires campaign-type split |
| 4 | 리더스CPA | 국내 CPA·리드 | `UNKNOWN` official public evidence not retrieved | EXCLUDE pending identity/policy proof |
| 5 | DBDBDeep | 국내 CPA·리드 | `CONFIRMED` service identity; public integration/policy capabilities `UNKNOWN` | HOLD |
| 6 | 모비온 | 국내 CPA·리드 | `CONFIRMED` official advertiser API; affiliate/lead-publisher fit `UNKNOWN` | HOLD |
| 7 | 애드릭스(ADLIX) | 국내 CPA·리드 | `CONFIRMED` official CPA service description; API/report/policy URLs `UNKNOWN` | HOLD |
| 8 | TOS | 국내 CPA·리드 | identity `UNKNOWN` | EXCLUDE; never infer which “TOS” was intended |
| 9 | 오늘의집 파트너스 | 국내 상품제휴 | affiliate program identity/API/policy `UNKNOWN` in official public pages retrieved | HOLD |
| 10 | 네이버 브랜드커넥트/쇼핑커넥트 | 국내 상품제휴 | `CONFIRMED` official service, creator terms, operating policy | **Human-assisted 1** |
| 11 | AliExpress Affiliate | 글로벌 리테일 | `CONFIRMED` official affiliate API invocation/OAuth docs; current program policy `UNKNOWN` | HOLD |
| 12 | TEMU Affiliate | 글로벌 리테일 | `CONFIRMED` official affiliate links/codes/dashboard and market variance | HOLD |
| 13 | Amazon Associates | 글로벌 리테일 | `CONFIRMED` PA API/data feeds/reporting/policies | DEFER: high policy/freshness burden |
| 14 | CJ Affiliate | 글로벌 네트워크 | `CONFIRMED` developer APIs/product feed/link search | DEFER |
| 15 | Awin | 글로벌 네트워크 | `CONFIRMED` APIs, bulk deeplinks, reports, product feeds | DEFER |
| 16 | Impact | 글로벌 네트워크 | `CONFIRMED` tracking/deep links, catalog API/feed, report/API export | DEFER after deep review |
| 17 | Rakuten Advertising | 글로벌 네트워크 | `CONFIRMED` deep-link/product-search/report APIs | DEFER |
| 18 | ShareASale | 글로벌 네트워크 | historical official materials found; current standalone API/policy/lifecycle `UNKNOWN` | EXCLUDE pending current official confirmation |
| 19 | FlexOffers | 글로벌 네트워크 | `CONFIRMED` official public REST API and official API feature notices | DEFER |

Overlap note: 텐핑 and 애드픽 support more than one commercial model. They are placed in the group most relevant to the proposed first POC; every campaign still requires an explicit `compensation_model` such as `CPS`, `CPA`, `CPL`, `CPI`, or `CPC`.

## 3. Official evidence registry

`—` means `UNKNOWN`, not “no capability.” `policy_version` records only an explicit date/version visible in retrieved official content; otherwise it remains `UNKNOWN`.

| Candidate | API | Product/feed | Deep link/link issuance | Reporting | Policy / official evidence URLs | policy_version | evidence_checked_at |
|---|---|---|---|---|---|---|---|
| 링크프라이스 | `CONFIRMED`: hot-deal, reward, deep-link, mobile APIs | `CONFIRMED`: hot-deal/product data described | `CONFIRMED`: URL-to-performance-link conversion | `CONFIRMED`: affiliate guide points to reports; report export/API schema `UNKNOWN` | [Open API/plus services](https://www.linkprice.com/affiliate/views/affiliate_marketing/plus_service_api.html), [affiliate guide](https://www.linkprice.com/views/affiliateguide/guide02.html), [affiliate benefits](https://www.linkprice.com/affiliate/views/affiliate_marketing/affiliate_benefit.html) | `UNKNOWN` | 2026-07-12 |
| 애드픽 | `CONFIRMED`: official JSON GET API; API key required | `CONFIRMED`: malls and product search | `CONFIRMED`: commission-link creation | `CONFIRMED`: performance lookup is described by API guide; exact retention/export contract `UNKNOWN` | [API guide](https://biz.adpick.co.kr/?ac=api&sub=guide), [Biz policy](https://biz.adpick.co.kr/?ac=help&sub=policy&tab=terms), [Biz overview](https://biz.adpick.co.kr/) | `UNKNOWN` | 2026-07-12 |
| 텐핑 | public API `UNKNOWN` | public feed `UNKNOWN` | `CONFIRMED`: official “소문내기 URL” generation/extension | `CONFIRMED`: official UI describes daily/content/purchaser statistics; export API `UNKNOWN` | [Tenping service](https://tenping.kr/), [advertiser service](https://biz.tenping.net/), [terms](https://biz.tenping.net/Common/Terms), [privacy](https://landing.tenping.kr/Common/Privacy) | `UNKNOWN` | 2026-07-12 |
| 리더스CPA | — | — | — | — | official identity/policy URL not confirmed | `UNKNOWN` | 2026-07-12 |
| DBDBDeep | API `UNKNOWN` | feed `UNKNOWN` | link method `UNKNOWN` | reporting `UNKNOWN` | [official service page](https://www.dbdbdeep.com/me2/cs/dbdbdeep.php) | `UNKNOWN` | 2026-07-12 |
| 모비온 | `CONFIRMED`: bearer-token API, IP allowlisting, 120 calls/min | affiliate product feed `UNKNOWN` | affiliate deep link `UNKNOWN` | `CONFIRMED`: advertiser statistics/query API; publisher-lead reporting fit `UNKNOWN` | [Mobon API](https://api-document.mobon.net/) | `UNKNOWN` | 2026-07-12 |
| 애드릭스(ADLIX) | — | — | — | public report contract `UNKNOWN` | [official site](https://www.adlix.co.kr/), [CPA guide](https://www.adlix.co.kr/guide/guide1.asp) | `UNKNOWN` | 2026-07-12 |
| TOS | — | — | — | — | no identity assigned | `UNKNOWN` | 2026-07-12 |
| 오늘의집 파트너스 | — | — | — | — | affiliate operator/program page not confirmed | `UNKNOWN` | 2026-07-12 |
| 네이버 브랜드커넥트/쇼핑커넥트 | public API `UNKNOWN` | public feed `UNKNOWN` | `CONFIRMED`: creator issues product-specific promotion links in the Naver UI | `CONFIRMED`: campaign compensation and sales-based settlement exist; public report export/API `UNKNOWN` | [creator overview](https://brandconnect.naver.com/about/creator), [seller/partner overview](https://brandconnect.naver.com/about/partner), [creator terms](https://brandconnect.naver.com/service/term/affiliate/creator), [creator operating policy](https://brandconnect.naver.com/service/policy/affiliate/creator) | `2025.03` | 2026-07-12 |
| AliExpress Affiliate | `CONFIRMED`: official affiliate API invocation and OAuth docs | capability details beyond retrieved pages `UNKNOWN` | API-generated affiliate link capability inferred by API name is **not** promoted; endpoint details require recheck | report API `UNKNOWN` | [affiliate API invocation](https://developer.alibaba.com/docs/doc.htm?articleId=118934&docType=1&treeId=674), [OAuth](https://developer.alibaba.com/docs/doc.htm?articleId=120687&docType=1&treeId=727) | pages published circa 2021; current policy `UNKNOWN` | 2026-07-12 |
| TEMU Affiliate | public affiliate API `UNKNOWN` | `CONFIRMED`: dashboard can expose hot items/product links; feed `UNKNOWN` | `CONFIRMED`: referral links/codes | `CONFIRMED`: official earnings dashboard; export/API `UNKNOWN` | [Affiliate FAQ](https://www.temu.com/ca/affiliate_question.html), [Affiliate recruitment](https://www.temu.com/affiliate_recruit.html), [Partner terms entry](https://partner.temu.com/documentation?menu_code=d8425dcd25b04658843e622e178a3b42), [Partner privacy](https://partner.temu.com/protocol/temu_partner_platform_privacy_policy_20241215.pdf) | privacy policy `2024-10-30`; local affiliate terms vary | 2026-07-12 |
| Amazon Associates | `CONFIRMED`: Creators API/PA API | `CONFIRMED`: PA API and data feeds, with separate license and access conditions | `CONFIRMED`: Special Links/link formats | `CONFIRMED`: reports and downloadable reports; reporting API not confirmed | [Operating Agreement](https://affiliate-program.amazon.com/help/operating/agreement/), [Program Policies](https://affiliate-program.amazon.com/help/operating/policies), [Reporting help](https://affiliate-program.amazon.com/help/node/topic/G37BNSA75FNE9HF4), [PA API help](https://affiliate-program.amazon.com/help/node/topic/GM6Z4B6SQMSG7D8U) | policies updated `2026-04-14` | 2026-07-12 |
| CJ Affiliate | `CONFIRMED`: publisher APIs | `CONFIRMED`: GraphQL Product Feed API | `CONFIRMED`: Link Search API; arbitrary URL deep-link behavior not confirmed | `CONFIRMED`: Commission Detail API and performance tooling | [Developer Portal](https://developers.cj.com/), [Product feeds](https://developers.cj.com/docs/data-imports/product-feeds), [publisher overview](https://www.cj.com/publisher) | `UNKNOWN` | 2026-07-12 |
| Awin | `CONFIRMED`: publisher/advertiser REST APIs | `CONFIRMED`: downloadable/custom product feeds | `CONFIRMED`: Link Builder API creates bulk deeplinks | `CONFIRMED`: transaction and aggregated/performance reports | [API introduction](https://help.awin.com/apidocs/introduction-1), [API index](https://help.awin.com/apis), [product feed access](https://success.awin.com/articles/en_US/Knowledge/How-can-I-access-a-Product-Feed), [tracking policy](https://www.awin.com/docs.awin.com/Legal/Awin%2BTracking%2BPolicy.pdf) | API intro updated `2026-03-02`; tracking policy exact version `UNKNOWN` | 2026-07-12 |
| Impact | `CONFIRMED`: partner tracking-link/catalog/report APIs | `CONFIRMED`: catalog item API and downloadable/API/FTP catalogs | `CONFIRMED`: program-controlled deep links/tracking links | `CONFIRMED`: UI downloads/schedules and API export | [tracking-link overview](https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/tracking/tracking-links/create-and-manage-links/tracking-links-overview), [seller tracking/catalog APIs](https://help.impact.com/en/support/solutions/articles/155000004726-create-tracking-links-for-seller-programs), [link parameters](https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/tracking/tracking-links/create-and-manage-links/add-reporting-information-to-your-tracking-links), [partner reports](https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/reporting-for-partners/report-management/view-and-customize-reports-for-partners), [Sub ID report/API export](https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/reporting-for-partners/performance-reports-for-partners/performance-by-sub-id-and-shared-id-for-partners) | help pages current in 2026; contractual policy version `UNKNOWN` | 2026-07-12 |
| Rakuten Advertising | `CONFIRMED`: token-auth affiliate APIs | `CONFIRMED`: Product Search from advertiser feeds | `CONFIRMED`: Deep Links API, 100 calls/min, one link/request | `CONFIRMED`: Advanced Reports API, 500 calls/day | [Affiliate APIs](https://developers.rakutenadvertising.com/documentation/en-US/affiliate_apis), [Deep Links API](https://developers.rakutenadvertising.com/guides/deep_link), [Advanced Reports API](https://developers.rakutenadvertising.com/guides/advanced_reports), [Advertisers API reference](https://developers.rakutenadvertising.com/guides/advertisers/reference) | `UNKNOWN` | 2026-07-12 |
| ShareASale | current standalone API `UNKNOWN` | historical official datafeed material exists; current contract `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | [historical official tracking setup](https://shareasale.com/step3.pdf) | `UNKNOWN` | 2026-07-12 |
| FlexOffers | `CONFIRMED`: public REST API exists | `CONFIRMED`: Product Feeds API official feature notice | `CONFIRMED`: UI/bookmarklet/API deep-link validation | `CONFIRMED`: Sales API/report feed official feature notice | [public REST API](https://api.flexoffers.com/), [sales/deep-link/feed update](https://dr.flexoffers.com/new-features/sales-reports-deep-links-and-product-feeds-api-updates/), [product-feed API update](https://www.flexoffers.com/new-features/enhanced-message-center-product-widget-and-new-api-for-product-feeds/) | feature notices dated `2022-10-27` and later; current terms `UNKNOWN` | 2026-07-12 |

## 4. Priority deep review and POC decisions

### 4.1 POC GO 1 — 링크프라이스

`CONFIRMED`: official pages describe product/hot-deal data, deep-link conversion, reward data, and mobile CPA/CPI/CPE APIs. This is the broadest confirmed domestic capability surface in the first-pass list.

`PROPOSED` Phase-1 scope:

- accept a manually exported or synthetic schema fixture based only on confirmed field meanings;
- normalize advertiser/program identity, destination URL, generated affiliate URL, compensation model, region/currency, and evidence timestamps;
- do not call the API or publish a link;
- require a human to supply the applicable affiliate terms, channel approval, and disclosure text before any later live test.

GO rationale: domestic relevance plus confirmed product/deep-link API surface.  
Stop condition: no current official terms/API field specification can be obtained without account access, or the program prohibits the intended media/channel.

### 4.2 POC GO 2 — 애드픽

`CONFIRMED`: the official API guide exposes a JSON GET API with API-key authentication and describes mall lookup, product search, commission-link creation, and performance lookup. The official Biz policy defines revenue-producing ad activity and Biz membership.

`PROPOSED` Phase-1 scope:

- model the API response contract with local fixtures only;
- separate `shopping` opportunities from CPA/CPI/CPC campaigns;
- never store an API key in a request, fixture, log, or repository;
- block product claims when the product record lacks a source timestamp or merchant URL.

GO rationale: clear official API guide and well-bounded domestic first fixture.  
Stop condition: API access requires terms or permissions not captured in a current official policy snapshot, or product freshness cannot be determined.

### 4.3 Human-assisted — 네이버 브랜드커넥트/쇼핑커넥트

Naver exposes two related but operationally distinct paths. They must not be collapsed into one generic affiliate API integration.

#### Path A — creator-side campaigns and Shopping Connect

`CONFIRMED` from the [creator overview](https://brandconnect.naver.com/about/creator), [Shopping Connect creator terms](https://brandconnect.naver.com/service/term/affiliate/creator), and [creator operating policy](https://brandconnect.naver.com/service/policy/affiliate/creator):

- Brand Connect supports creator campaigns whose compensation can include manuscript fees/cash rewards, product provision, or both. The creator overview shows official campaign examples with `원고료`, `상품제공`, and `원고료+상품제공` conditions.
- A creator must authenticate an active channel; channel-specific eligibility remains governed by Naver's customer-center criteria. The official creator page also states that Shopping Connect may be available only to some creators during a beta period. This is an availability warning, not a permanent eligibility guarantee.
- Shopping Connect is a separate sales-commission path: the creator selects a product exposed in Shopping Connect, obtains the product-specific promotion link on the Naver Shopping Connect screen, publishes it to the approved media/channel, and may receive sales-based income.
- The link is Naver-issued. AI-Content-OS must not synthesize, rewrite, refresh, shorten, or reverse-engineer it. Public link-issuance automation API remains `UNKNOWN`.
- The creator must disclose the economic relationship in the manner required by the endorsement/advertising guideline. The duty applies to the post or transmitted information used for Shopping Connect activity.
- A product's Shopping Connect payout rate and `진행` status are set on a monthly basis. A program can also be stopped during the month for campaign-company circumstances, temporary promotions, restrictions, SmartStore policy sanctions, or another recognized urgent need. A captured rate is therefore volatile and not proof of continued eligibility.

#### Path B — SmartStore seller-side setup and creator recruitment

`CONFIRMED` from the [seller/partner overview](https://brandconnect.naver.com/about/partner):

- Shopping Connect is tied to SmartStore; the official page states that only SmartStore can be connected for this service.
- The seller chooses products already on sale in SmartStore and directly sets which products participate and the Shopping Connect usage fee/rate.
- The seller can search for and recruit creators using channel/topic/audience and collaboration information, and can manage campaign proposals, schedules, submitted content, communication, and settlement through Brand Connect.
- When a creator promotes a SmartStore product through an SNS channel, usage-fee settlement is based on sales that reach purchase confirmation. The seller-side page describes this as automatic settlement for confirmed purchases, not merely clicks, orders, or drafted content.
- Cash-reward campaigns and product-only campaigns are distinct from Shopping Connect sales commission. The official page says cash-reward campaigns require prepayment and may incur a settlement fee, while product-only campaigns can have different fee treatment. These terms must be captured per campaign rather than generalized.

#### Shared operating restrictions and settlement rules

`CONFIRMED` from the [Shopping Connect operating policy](https://brandconnect.naver.com/service/policy/affiliate/creator) and [creator terms](https://brandconnect.naver.com/service/term/affiliate/creator):

- manipulation of the Shopping Connect link, its form, refresh cycle, or embedded information is prohibited;
- invalid clicks, incentivized or abnormal traffic, and any act that interferes with accurate traffic/performance measurement are prohibited;
- Shopping Connect statistics supplied by Naver may not be disclosed externally;
- Shopping Connect rights may not be shared, provided, assigned, brokered, or resold to another person or media without Naver's written consent;
- cancellation and return amounts are excluded after measuring purchases confirmed during each calendar month;
- the monthly settlement-confirmed amount is finalized on the first day of the second following month (`익익월 1일`) and paid on the twenty-first day of that month (`익익월 21일`), subject to listed account, banking, customer-verification, and tax-document delays;
- Shopping Connect public automation API, public product feed, public report export API, and machine-readable policy-change feed remain `UNKNOWN`.

#### Proposed AI-Content-OS responsibility split

`PROPOSED` human-assisted flow:

```text
Human/Naver UI
  -> authenticate creator channel or seller/SmartStore eligibility
  -> select Path A campaign/product or configure Path B product/rate
  -> issue the official product-specific link in Naver

AI-Content-OS
  -> validate human-provided product/campaign evidence and freshness
  -> prepare product selection rationale and evidence-safe content
  -> insert the approved economic-interest disclosure
  -> generate a manual-upload package and preflight checklist

Human/Naver UI
  -> recheck beta/access status, product 진행 status, payout rate, price/stock, and link
  -> perform final review and publish manually to the authenticated channel

Official report / human export
  -> import only finalized, source-labeled settlement rows into Revenue Ledger
  -> reconcile cancellations/returns and payment status without exposing Naver-confidential statistics
```

AI-Content-OS may own product/campaign selection support, Research, content generation, compliance checks, manual-upload packaging, and a future source-labeled Revenue Ledger import. Naver must remain the source of link issuance and settlement facts; a human remains responsible for the final Naver-side link issuance and final channel publication.

Minimum human-assisted input additions (`PROPOSED`):

```json
{
  "naver_route": "creator_campaign|creator_shopping_connect|smartstore_seller_shopping_connect",
  "creator_channel_verified": false,
  "shopping_connect_access": "available|beta_limited|unavailable|unknown",
  "smartstore_eligibility_confirmed": false,
  "official_link_issued_in_naver_ui": false,
  "official_link_captured_at": null,
  "program_status": "active|stopped|unknown",
  "payout_rate_or_usage_fee": "source value or unavailable",
  "rate_verified_at": null,
  "economic_interest_disclosure_approved": false,
  "final_manual_publish_approved": false,
  "revenue_ledger_import": {
    "source": "official_naver_report_or_human_verified_export",
    "period": null,
    "purchase_confirmed_amount": null,
    "cancellation_return_adjustment": null,
    "settlement_finalized_at": null,
    "paid_at": null,
    "confidential_statistics_exported": false
  }
}
```

Reason for not choosing API POC: no public official API/feed/export contract was confirmed, and the operating policy expressly prohibits link/information manipulation and external disclosure of provided statistics.

### 4.4 Impact — deep review, deferred

`CONFIRMED`: partner tracking links, conditional deep linking, catalog APIs/downloads, report downloads/scheduling, and API export exist. Deep linking is advertiser/program controlled. Link parameters may carry Sub IDs, Shared IDs, product SKU, and even a partner customer ID.

`PROPOSED` controls before any future POC:

- never place raw email, phone, name, device ID, or another direct identifier in Sub ID/Shared ID/PartnerCustId;
- use a random campaign/content key, not a person key;
- make advertiser contract, allowed domain, approved promotional property, region, currency, and catalog freshness mandatory;
- treat every brand program as a distinct policy scope even though it shares the Impact platform.

Defer rationale: integration quality is high, but global program-by-program policy, PII-like link parameters, region/currency normalization, and account approval create more Phase-1 risk than the two domestic fixture POCs.

## 5. Phase-1 POC input contract

This contract is `PROPOSED`. Phase 1 is offline validation only and accepts no credential.

```json
{
  "registry_entry_id": "linkprice|adpick|naver_shopping_connect|...",
  "network_name": "display name",
  "network_group": "domestic_product_affiliate|domestic_cpa_lead|global_retail|global_network",
  "program_id": "network-issued stable ID or unavailable",
  "advertiser_id": "network-issued stable ID or unavailable",
  "program_name": "verified program name",
  "compensation_model": "CPS|CPA|CPL|CPI|CPC|UNKNOWN",
  "region": "ISO-3166-1 alpha-2 or explicit multi-region list",
  "currency": "ISO-4217 code",
  "promotion_channel": "blog|website|instagram|youtube|community|app|other",
  "channel_approval_status": "confirmed|unknown|rejected",
  "destination_url": "verified merchant/product URL",
  "affiliate_url": "human/API-issued URL or unavailable",
  "link_issue_method": "official_ui|official_api|official_feed|human_provided|unavailable",
  "product": {
    "product_id": "stable ID or unavailable",
    "title": "source value",
    "brand": "source value or unavailable",
    "price": {"value": null, "currency": "KRW", "verified_at": null, "expires_at": null},
    "stock": {"value": "in_stock|out_of_stock|preorder|unknown", "verified_at": null, "expires_at": null},
    "image_url": "official/licensed URL or unavailable",
    "image_rights": "confirmed|unknown|prohibited"
  },
  "campaign": {
    "valid_from": null,
    "valid_until": null,
    "commission_or_payout": "source value or unavailable",
    "commission_verified_at": null
  },
  "reporting": {
    "method": "official_ui|official_api|official_export|unavailable",
    "dimensions": [],
    "metrics": [],
    "is_measured": false
  },
  "disclosure": {
    "required": true,
    "text": "human/legal-approved text or unavailable",
    "placement": "before_or_near_first_affiliate_link",
    "policy_source_id": "official evidence ID"
  },
  "policy": {
    "terms_url": "official URL or unavailable",
    "operating_policy_url": "official URL or unavailable",
    "privacy_url": "official URL or unavailable",
    "policy_version": "explicit version/date or UNKNOWN",
    "evidence_checked_at": "ISO-8601 with timezone",
    "revalidate_by": "ISO-8601 date"
  },
  "sources": [],
  "manual_review_required": true,
  "credentials_present": false,
  "external_call_performed": false
}
```

Fail-closed rules:

1. Missing official identity, destination URL, region, currency, policy evidence, or channel approval blocks publish readiness.
2. `UNKNOWN` never becomes a guessed default.
3. `affiliate_url` is not proof of current price, stock, commission, eligibility, or attribution success.
4. Report metrics remain `is_measured=false` until imported from an official report with account ownership and time range recorded.
5. No credential, token, cookie, login session, raw PII, or secret may enter the contract.

## 6. Price, stock, campaign, and policy freshness

The following are `PROPOSED` conservative defaults for the POC, not claims about network guarantees.

| Field | Maximum age for draft generation | Publish-time rule |
|---|---:|---|
| price, discount, coupon | 6 hours | mandatory human/API recheck immediately before publication |
| stock/availability | 1 hour | mandatory recheck immediately before publication |
| shipping promise | 6 hours | recheck before publication |
| commission/payout/rate | 24 hours, unless program supplies a shorter validity | recheck program/rate state before publication |
| campaign eligibility/end time | source expiration governs | block after expiration or when timezone is unknown |
| product title/stable specification | 30 days unless source marks volatile | recheck on conflict or product-page change |
| policy/terms | 30 days | immediate recheck after notice, rejection, or platform change |

Every volatile value requires `verified_at`, `expires_at`, `region`, `currency`, source URL/ID, and retrieval method. A timezone-free campaign deadline is unusable. Cross-border price conversion must store the original currency and rate source/time; Phase-1 POC should display original currency and avoid inferred conversion.

## 7. Advertising disclosure and policy controls

`CONFIRMED`: Korea's Fair Trade Commission states that a material economic relationship affecting a recommendation's credibility must be disclosed, and its revised endorsement guideline took effect on 2024-12-01. Naver Shopping Connect independently requires economic-interest disclosure.

Official sources:

- [KFTC revised endorsement-guideline notice](https://www.ftc.go.kr/www/selectBbsNttView.do?bordCd=6&key=20&nttSn=9048&pageIndex=3&pageUnit=10&searchCnd=all)
- [KFTC 2025 consultation example](https://www.ftc.go.kr/www/selectExmplView.do?dscsnExmplSn=886&key=330&pageIndex=1&pageUnit=10&searchCnd=all)
- [Naver Shopping Connect creator terms](https://brandconnect.naver.com/service/term/affiliate/creator)

`PROPOSED`: every artifact must render a human/legal-approved disclosure before or adjacent to the first affiliate link and preserve `disclosure_text`, `placement`, `policy_source_id`, `policy_version`, and `evidence_checked_at`. A generic hashtag hidden at the end is not treated as automatically sufficient.

## 8. Separate CPA/CPL PII contract proposal

CPA/CPL campaigns are excluded from the two product-affiliate fixture POCs. Any future lead POC requires a separately approved `LeadConsentContract` before a form, webhook, API, or export is built.

Required fields (`PROPOSED`):

```json
{
  "lead_contract_id": "stable ID",
  "campaign_id": "verified network campaign ID",
  "controller": {"legal_name": "", "contact": ""},
  "processors": [{"legal_name": "", "purpose": "", "country": "", "contract_confirmed": false}],
  "fields_requested": [{"name": "phone", "required": true, "purpose": "", "sensitivity": "personal"}],
  "consent": {
    "notice_version": "",
    "purpose": "",
    "recipients": [],
    "retention_period": "",
    "cross_border_transfer": "none|declared|unknown",
    "withdrawal_method": "",
    "captured_at": null,
    "evidence_id": ""
  },
  "retention": {"delete_at": null, "legal_hold_basis": null},
  "deletion": {"method": "", "processor_confirmation_required": true, "completed_at": null},
  "delegation_contract": {"confirmed": false, "version": "", "signed_at": null},
  "data_minimization_passed": false,
  "manual_legal_review_required": true
}
```

Hard gates:

- explicit, purpose-specific consent before collection;
- named controller, recipient, and every processor/subprocessor;
- retention period and deterministic deletion date;
- withdrawal/deletion path and downstream processor deletion confirmation;
- processing/delegation agreement and cross-border-transfer review where applicable;
- field minimization: no resident-registration number, financial credential, health data, or unrelated profiling field in Phase 1;
- no PII in affiliate link parameters, logs, analytics labels, filenames, or model prompts;
- a campaign page's consent text is evidence only for that exact campaign/version, never a reusable network-wide template.

## 9. Hold and exclusion rationale

### Hold

- 텐핑: official CPS/CPA activity is confirmed, but public integration schema is not; split product and lead contracts first.
- DBDBDeep and 애드릭스: service identity/CPA description exists, but official API, reporting, and current policy evidence is incomplete.
- 모비온: API is confirmed but appears advertiser-oriented; affiliate/lead intake ownership and PII roles are unresolved.
- 오늘의집 파트너스: exact affiliate-program identity and current official policy were not confirmed.
- AliExpress and TEMU: official program/API evidence exists, but Korea eligibility, local terms, currency, disclosure, and current reporting/API contract remain incomplete.

### Exclude pending evidence

- 리더스CPA: no official identity/policy source retrieved in this pass.
- TOS: identity intentionally remains `UNKNOWN`; no vendor/domain may be guessed.
- ShareASale: historical official material is insufficient to confirm the current standalone program/API/policy state.

### Defer despite strong APIs

- Amazon Associates, CJ, Awin, Impact, Rakuten Advertising, FlexOffers: technically capable, but account/program approval, global policy, region/currency, product-data freshness, and reporting normalization create more first-POC scope than the two domestic candidates.

## 10. Revalidation and approval gates

Revalidate this matrix on `2026-08-11`, or earlier when any official notice, API rejection, program suspension, link failure, policy change, or unexplained reporting discrepancy occurs.

Before moving either POC beyond local fixtures, the CTO must separately approve:

1. named account owner and intended promotion channels;
2. current official terms/policy snapshot and legal/compliance review;
3. credential issuance and secret-storage design;
4. exact read-only API scopes and rate limits;
5. product/offer freshness SLA and stale-data behavior;
6. disclosure text and placement;
7. region/currency/tax handling;
8. sandbox or one-record human-approved test plan;
9. reporting import with no fabricated metrics;
10. kill switch, audit log, revocation, and deletion plan.

This document approves none of those external actions.

## 11. Confirmed source list and unresolved list

### Confirmed official-source families

- 링크프라이스, 애드픽, 텐핑, DBDBDeep identity, 모비온 API, 애드릭스 CPA description
- 네이버 브랜드커넥트/쇼핑커넥트
- AliExpress developer API pages, TEMU Affiliate/Partner pages, Amazon Associates
- CJ, Awin, Impact, Rakuten Advertising, FlexOffers
- Korea Fair Trade Commission disclosure guidance

### Unconfirmed items requiring the next research pass

- exact identity/domain for TOS;
- official current identity/policies for 리더스CPA and 오늘의집 파트너스;
- current standalone ShareASale lifecycle, API, and policy;
- current terms/policy versions for 링크프라이스, Impact, Rakuten, FlexOffers, CJ, and several domestic CPA networks;
- public reporting/export schemas for 링크프라이스, 네이버 쇼핑커넥트, 텐핑, TEMU, Amazon Associates;
- Korea account eligibility, supported region/currency, and local affiliate terms for AliExpress/TEMU/Amazon/global networks;
- advertiser/program-specific deep-link permission and product-feed freshness for every global network;
- formal controller/processor/deletion contracts for all CPA/CPL candidates.

## 12. Implementation status

- Evidence registry: documented.
- Phase-1 input contract: proposed.
- POC GO: 링크프라이스 and 애드픽, local fixtures only.
- Human-assisted: 네이버 쇼핑커넥트.
- Runtime integration/API calls: not implemented and not approved.
- Other repository files changed: none.
