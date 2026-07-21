# Manus / FarmersGo → AI-Content-OS Commerce Integration Plan

Plan date: 2026-07-11

This is a forward-looking INTEGRATION PLAN, not a new audit. It builds entirely on top of the
existing read-only audit at `docs/RESEARCH/MANUS/SELLER_AUTOMATION_AUDIT.md` (facts, risks,
evidence index) and the existing AI-Content-OS Commerce documents (`docs/COMMERCE_PHASE_1_CONTRACT.md`,
`docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`, `modules/commerce/commerce_module.py`). No Manus
code was copied, imported, executed, or modified while writing this plan. `external_workmanus/**`
was read-only throughout, and `data/`, `venv/`, `logs/`, and bytecode/cache files were not opened,
consistent with the prior audit's boundary.

Legend: `CONFIRMED` = directly read in a source file opened during this task. `INFERRED` =
reasonable derivation from code structure, not runtime-verified. `UNKNOWN` = not determinable
without running the app or reading data this task was told not to read. `BLOCKED` = explicitly
forbidden by task rules or by the existing Commerce Phase 1 contract.

---

## 0. FarmersGo — explicit non-finding

`UNKNOWN`/absent: no FarmersGo desktop application or browser-extension implementation exists
anywhere in this repository. A repo-root glob for `**/*armersGo*` and `**/*farmers*` during this
task returned zero matches, consistent with the prior audit's §7 finding (`UNKNOWN`: "No direct
FarmersGo desktop or browser-extension implementation was found in
`external_workmanus/seller_automation`"). This plan therefore treats FarmersGo as
**referenced-but-absent**: nothing below assumes FarmersGo code, data shapes, or behavior exist in
this codebase. If FarmersGo is a real external tool the user has used outside this repository, its
facts are simply not available here and must be supplied fresh by a human, not inferred by this
plan.

---

## 1. Data Contracts — Manus fields mapped to Phase 1 `facts`, with mandatory re-verification

Source: `external_workmanus/seller_automation/app/models.py` (`Product`, `ProcessingProfile`,
`Listing`), `app/processing.py` (`PricingConfig`, `NamingConfig`), `app/markets/naver_payload.py`
(`NaverProductInput`) — all `CONFIRMED` (read directly in this task).

**Governing rule, restated from the task and from `COMMERCE_PHASE_1_CONTRACT.md` §3**: nothing
below is a trusted pass-through. Every mapped value is `unverified_manus_hint` until it passes
Phase 1's presence/source/verification/freshness/consistency/rights gates independently. Manus has
no concept of `source_ids`, `verified_at`, `verification_method`, `volatile`, or `expires_at` — a
Manus `Product.price` is a scraped wholesale cost, not a source-backed, timestamped commercial
fact, and must never be written directly into a Phase 1 `commerce_request` field.

### 1.1 `Product` (app/models.py, SQLAlchemy model) → Phase 1 `product.facts` / `commercial_facts`

| Manus field (`CONFIRMED`) | Phase 1 target concept | Mapping note (mandatory re-verification) |
|---|---|---|
| `source_site` (`luckyfresh`/`econfarm`/`choigozip`) | `sources[].source_name` / `source_type: "marketplace_export"` (arguable) | `INFERRED`: could seed a `source_id`/`source_name` entry, but Phase 1 requires `rights_or_permission` and `retrieved_at` that Manus does not track at all — must be filled by a human, not inferred from `source_site` alone. |
| `source_product_id` | `product.product_id` (as a *hint*, not the merchant SKU of record) | `INFERRED`: usable only as a cross-reference key for a human importer, never as the authoritative `product_id`. |
| `title` | `product.product_name` candidate | `INFERRED`: raw wholesale-site title, unverified. Requires `field_id`, `source_ids`, `verified_at`, `verification_method` before it can enter `facts`. Manus's own `process_name()` (prefix/suffix/banned-word stripping) is marketing formatting, not truth-verification — running it does not satisfy Phase 1's gates. |
| `price` / `min_price` / `max_price` | `commercial_facts.price` (wholesale cost, **not** sale price) | `CONFIRMED` Phase 1 rule: price is `ALWAYS_VOLATILE` and requires `expires_at`. A Manus DB row has no timestamp granularity finer than `updated_at` and no `verification_method` — every price value must be re-collected/re-verified at generation time, never imported from a stale Manus DB row. |
| `origin` | `product.country_of_origin` | `INFERRED`: free-text field (e.g. "국내산"), needs mapping to Phase 1's structured origin plus a source and verification event. |
| `thumbnail_url` / `images_json` | `claims`/`images` rights-sensitive fields | `BLOCKED` as a direct pass-through: Phase 1 §3 gate 6 requires `rights_or_permission` for every image; Manus has no rights/licensing field for scraped images at all (`CONFIRMED`, no such column in `Product`/`SiteCredential`). An image URL scraped from a wholesale site must never be treated as rights-cleared. |
| `options_json` | `product.options[]` | `INFERRED`: raw option name/price pairs; usable as a *structural* hint (option grouping shape) only — each option's price/availability is itself a volatile fact requiring its own source/verification/freshness entry. |
| `detail_html` | `detail_page` section source material | `BLOCKED` as direct pass-through: Manus reuses this HTML almost verbatim into the Naver payload (`CONFIRMED`, see §2 below) with no truth-gating; Phase 1's canonical `detail_page` sections (`headline`/`problem`/`benefits`/`features`/`specifications`/`usage`/`cautions`/`faq`/`cta`) require per-fact `source_ids`, which raw scraped HTML cannot supply without manual extraction and re-verification. |
| `status` (`collected`/`processed`/`listed`) | no Phase 1 equivalent | `INFERRED`: this is Manus's own workflow-state field, not a product fact; not mappable to Phase 1's fact/source model. Could inform a future local import pipeline's own state tracking (see §5), never a `commerce_request` field. |

### 1.2 `ProcessingProfile` (app/models.py + app/processing.py `PricingConfig`/`NamingConfig`) → Phase 1 `commercial_facts` / copy-generation config

| Manus field (`CONFIRMED`) | Phase 1 target concept | Mapping note |
|---|---|---|
| `margin_rate`, `payment_fee_rate`, `round_unit`, `min_price` | Not a Phase 1 fact at all — this is a **pricing formula**, `calc_sale_price()` in `app/processing.py`, computing `sale_price` from wholesale `cost`. | `INFERRED`: Phase 1 has no concept of computing a sale price from a cost/margin formula — Phase 1 only ever renders a `price` that was already supplied as a verified fact. If AI-Content-OS ever wants margin-based pricing, that is a **new capability**, not something Phase 1 has room for today; see §4 classification (`NEW BUILD REQUIRED`). |
| `prefix` / `suffix` / `banned_words` | Loosely analogous to Brand DNA's banned-words concept (`config/brand_profile.json`, per `CLAUDE.md`) | `INFERRED`: conceptually similar shape (a banned-word list influencing copy), but Phase 1 §4 states Brand DNA may only influence wording/tone — it must never supply or override product facts. Manus's `prefix`/`suffix` are literal product-name mutations, which is a different (marketing-string) concern than Phase 1's fact-gated `product_name`. |
| `default_stock` | `commercial_facts.stock` | `BLOCKED` as a direct pass-through: a fixed default like `default_stock=200` is exactly the kind of fabricated/assumed stock value Phase 1 §3 explicitly forbids ("the generator must not invent ... stock"). A default profile value is never a verified fact. |

### 1.3 `NaverProductInput` (app/markets/naver_payload.py) → Phase 1 `platform_packages.smartstore` field hints

| Manus field (`CONFIRMED`) | Phase 1 target concept | Mapping note |
|---|---|---|
| `name` | `platform_packages.smartstore.product_name` | `INFERRED`: shows Naver's real product-name field name (useful for Phase 2 adapter field-naming), but the *value* must come from Phase 1's own verified `product_name`/`brand`/`model_name`/`category` composition, not from Manus's `process_name()` output. |
| `leaf_category_id` | Not present in Phase 1 contract at all today | `INFERRED`: Phase 1's contract has no `category_id` field, only a free-text `category`. This is a real gap — see §4 (`NEW BUILD REQUIRED` for a category-ID resolution step) and §2 below (adapter-level category lookup, per `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.2). |
| `notice_type` / `notice_fields` (`productName`, `foodType`, `producerAndLocation`, `manufactureDate`, `shelfLifeOrUseByDate`, `capacityAndQuantityAndWeight`, `ingredientsAndContent`, `nutritionFacts`, `geneticallyModified`, `precautionWhenEatingOrCooking`, `importDeclaration`, `customerServicePhoneNumber`) | `platform_packages.smartstore.notice_information` | `INFERRED`, high value as a **field-name hint only**: this is the most concrete, reusable piece of data-contract information Manus offers — it names 11 concrete Korean food-category notice fields Naver's real payload expects, none of which are enumerated in Phase 1's current schema (`notice_information: {}` is an open dict today). Still `UNKNOWN`/unconfirmed against Naver's *official* documentation (per `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1.7, which independently found this exact gap `UNKNOWN`) — treat these 11 field names as a **research lead to verify against `apicenter.commerce.naver.com` directly**, not as confirmed Naver schema. Every value populating these fields still needs its own `source_ids`/`verified_at`/`verification_method` before Phase 1 could ever consider it `ready`. |
| `origin` → `_origin_area_info()` (`originAreaCode`, `content`) | `product.country_of_origin` formatting hint | `INFERRED`: shows a real Naver-side origin-code convention (`"00"` domestic vs `"04"` other); useful as an adapter-level formatting hint, not a fact source. |
| `option_combinations` (`optionName1`, `stockQuantity`, `price`, `usable`) | `platform_packages.smartstore.options[]` | `INFERRED`: shows Naver's real option-combination field shape; each `price`/`stockQuantity`/`usable` value is volatile and must independently pass Phase 1's freshness gate at upload time (this exact requirement is already `PROPOSAL`-designed in `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.10). |
| `delivery_fee`, `after_service_phone`, `after_service_guide`, `minor_purchasable`, `seller_product_code` | `commercial_facts.shipping` / notice-adjacent fields | `INFERRED`: field-name hints only; every value needs independent verification. |
| `representative_image_url` / `optional_image_urls` | `detail_page` image references | `BLOCKED` as direct pass-through — same rights-gate reasoning as §1.1's `thumbnail_url` row. |

### 1.4 Summary of the data-contract lesson

`INFERRED`: Manus's single most useful contribution to Phase 1/2 is not any specific *value* — it
is the **concrete Naver field-name vocabulary** (`leafCategoryId`, `productInfoProvidedNotice`,
`originAreaInfo`, `optionCombinations`, `deliveryFeeType`, etc.), which narrows the `UNKNOWN` gaps
already flagged in `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1.6/§1.7 from "we don't know
the shape at all" to "here is a plausible shape to verify against official docs before trusting
it." Every one of these field names remains `UNKNOWN` in the Phase 2 document's own evidentiary
sense until independently confirmed against `apicenter.commerce.naver.com` — Manus is a
third-party, unofficial source exactly like the blog sources the Phase 2 document already
downgrades to `UNKNOWN`.

---

## 2. Adapter Concepts — Manus's auth/payload/client split as a structural pattern (not code)

Source: `app/markets/naver_auth.py`, `app/markets/naver_payload.py`, `app/markets/naver_client.py`
(all `CONFIRMED`, read in this task; `naver_client.py` and `naver_payload.py` shown in full above).

`CONFIRMED` structural observation: Manus already separates Naver integration into three files
with distinct responsibilities:

1. **`naver_auth.py`** (not opened in full this pass, but referenced by `naver_client.py`'s
   `from .naver_auth import NaverAuth, API_BASE` — `CONFIRMED` import) — owns token acquisition
   (`auth.get_token()`), i.e. the *signing/authentication* concern, isolated from payload shape and
   HTTP transport.
2. **`naver_payload.py`** — owns pure data transformation: `NaverProductInput` (a plain dataclass)
   in, a nested `dict` (`build_product_payload()`) out. `CONFIRMED`: this file makes zero network
   calls and imports nothing from `naver_client.py` or `naver_auth.py` — it is a pure function
   module.
3. **`naver_client.py`** — owns HTTP transport and the **dry-run branch**: every method
   (`search_category`, `upload_image`, `create_product`) checks `self.dry_run` first and returns an
   inspectable payload/URL/headers dict instead of calling `requests.*` when true (`CONFIRMED`,
   lines 34-40, 46-48, 67-75 of `naver_client.py`).

**Conceptual pattern worth mirroring** (describe-only, no code copied) for AI-Content-OS's own
proposed `SmartStoreAdapter`/`CoupangAdapter` (`docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`
§3.2/§3.3):

- **Separate signing from shaping from sending.** Manus's three-file split is a clean instance of
  exactly the three responsibilities `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.1 already
  proposes bundling into one `PlatformUploadAdapter` base class
  (`validate() -> dry_run() -> submit() -> poll_status() -> record_audit_log()`). AI-Content-OS's
  adapters could structurally mirror Manus's split by keeping payload-building as a pure,
  side-effect-free function (like `build_product_payload()`) completely separate from the class
  that holds credentials and makes HTTP calls — this makes the payload-building half trivially
  unit-testable without network access or secrets, and keeps a reviewer's job (inspecting a
  dry-run payload, per Phase 2 §3.6) simple because the payload function has no hidden state.
- **Dry-run as a first-class branch inside every transport method, not a separate code path.**
  `CONFIRMED`: Manus's `dry_run` check lives inside each method (`search_category`, `upload_image`,
  `create_product`), not as a wrapper around a whole client instance. `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`
  §3.7 already proposes an equivalent `dry_run()` adapter method; the structural idea worth
  reusing is that *every* platform call the adapter can make (not just product creation) should
  have its own explicit dry-run branch, since Manus shows a real precedent where image upload also
  needed one (`upload_image()` returns the raw URL unchanged in dry-run instead of performing the
  real multipart upload — `CONFIRMED`, lines 46-48).
- **Never let payload-building read credentials.** `CONFIRMED`: `naver_payload.py`'s functions
  (`build_origin_product`, `build_product_payload`) take only a `NaverProductInput` dataclass and
  return a `dict` — no `client_id`/`client_secret`/token ever passes through them. This is a
  pattern worth deliberately preserving in `SmartStoreAdapter`/`CoupangAdapter`: keep the function
  that decides *what* to send structurally incapable of touching *how it authenticates*, which
  makes it easier to guarantee the `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.12 rule ("never log
  the raw HMAC secret, signature, or OAuth token itself") — a payload-builder that never receives a
  secret cannot leak it.

**Explicitly not reused**: `NaverAuth`'s actual signing implementation, `NaverClient`'s actual HTTP
call code, and any credential-handling code are `SECURITY-FORBIDDEN TO PORT` (see §4) — only the
three-way separation-of-concerns *shape* is being described here, not the code.

---

## 3. UI Flow Ideas — Manus's collect → review → dry-run → confirm flow as a UX pattern

Source: `app/templates/dashboard.html`, `app/templates/products.html` (both `CONFIRMED`, read in
full in this task), and the README's step-by-step (`external_workmanus/seller_automation/README.md`
§4, `CONFIRMED`).

`CONFIRMED` observed flow, as implemented in the templates and described in the README:

1. **Collect** (`dashboard.html`): operator checks source-site checkboxes (`luckyfresh`,
   `econfarm`, `choigozip`), sets a max-items-per-site number input, clicks "수집 시작" (Start
   Collection) — triggers `POST /api/collect`, then polls `GET /api/jobs/{id}` every second via
   `setInterval`, rendering a progress bar (`width: X%`), a one-line status message, and a
   scrolling last-15-lines log panel (`<pre class="job-log">`) until `status` becomes `done` or
   `error`, then auto-reloads the page after 1.5s.
2. **Review/select in a product table** (`products.html`): a filterable table (site dropdown +
   text search) with one row per product — thumbnail, title, source site, wholesale price, status
   badge (`등록`/other) — each row has a checkbox, plus a "select all" header checkbox and a live
   "N개 선택" (N selected) counter updated on every checkbox change.
3. **Dry-run toggle default-on** (`products.html`, lines 40-52): a `leafCategoryId` text input, a
   `dry-run(모의 전송)` checkbox that is **checked by default** (`CONFIRMED`, `<input type="checkbox"
   id="dryRun" checked>`), and a single "선택 상품 등록" (Register Selected Products) button.
4. **Confirm gate on the risky path only**: `CONFIRMED`, the button's click handler
   (`products.html` JS) calls `confirm('실제로 네이버에 등록합니다. 계속할까요?')` **only when
   `dryRun` is false** — i.e. the UI adds an extra native-browser confirmation dialog specifically
   for the real-upload path, while the dry-run path proceeds without any extra confirmation. Job
   progress is then polled the same way as collection.

**UX pattern worth considering for a future AI-Content-OS Commerce operator UI** (idea only, not
implementation):

- A three-stage screen flow — *Collect/Import* (background job with live progress + scrolling log)
  → *Review table* (checkbox-select, per-row status badge, live selection counter, filter/search)
  → *Action panel* (mode toggle defaulting to the safe option, extra confirmation only on the
  risky option) — is a reasonable shape for a future Commerce Phase 2 "prepare packages for manual
  upload" or "review dry-run adapter output" screen, since it matches the same collect → review →
  gate → act rhythm AI-Content-OS would need regardless of Manus.
- The **default-on safe toggle + confirm-only-on-danger** pattern is directly reusable as a UX
  idea for Phase 2's Human Approval Mode (`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.6): a
  future adapter-review screen could default to "dry-run" exactly as Manus does, and gate only the
  transition to a real submit behind an explicit extra confirmation step.
- The **job polling + bounded scrolling log** pattern (progress %, last-N log lines, auto-refresh
  on completion) is a reasonable idea for surfacing Phase 1's own `blocked_reasons`/
  `missing_fields` generation progress or a future Phase 2A dry-run-payload-generation job, without
  needing a heavier real-time transport (it is plain `setInterval` + `fetch`, `CONFIRMED`, no
  websockets).

**Explicitly excluded from reuse** (per task instruction and the prior audit's documented risks):
Manus's actual authentication/session/device-approval implementation must not be reused, because
the prior audit (`SELLER_AUTOMATION_AUDIT.md` §5 "Critical"/"High") already found, `CONFIRMED`:
default admin password co-existing with `0.0.0.0` LAN binding; runtime database and decryption key
co-located (`data/seller.db` + `data/secret.key`); no CSRF token mechanism on state-changing POST
routes; and cookies signed/HTTP-only but not marked secure. A future AI-Content-OS operator UI may
borrow the *screen flow shape* above, but must design its own auth/session/CSRF/device-approval
implementation from scratch, informed by ordinary modern web-security practice, not by reading
Manus's `app/security.py`.

---

## 4. Classification Table

| Manus capability | Classification | Reasoning |
|---|---|---|
| Wholesale-site collection/scraping (`app/collector.py`, `app/crawlers/luckyfresh.py`, `app/crawlers/adminplus.py`, `app/crawlers/choigozip.py`) | **NEW BUILD REQUIRED** (if ever approved) — and explicitly **not inherited from Manus** | `CONFIRMED`, real supplier-site scraping is out of Phase 1/2 scope entirely per `COMMERCE_PHASE_1_CONTRACT.md` (Phase 1 "does not... crawl a marketplace") and the coupang skill (`.codex/skills/ai-content-os-coupang/SKILL.md`: "Require a real product source... Separate stable product facts from volatile... fields"). If AI-Content-OS ever needs supplier-site collection, it must be designed fresh against current site terms/robots/ToS, not copied from Manus's crawler code, which the prior audit already flagged (`SELLER_AUTOMATION_AUDIT.md` §5 High #4: "Hardcoded external source URLs and scraping/API assumptions"). |
| Local encrypted credential storage (`app/crypto.py`, `data/secret.key` co-located with `data/seller.db`) | **SECURITY-FORBIDDEN TO PORT** | Prior audit `CONFIRMED` Critical #2: "Runtime database and decryption key are co-located... copying the `data/` folder may be enough to decrypt stored source credentials and market API keys." AI-Content-OS's own convention (`CLAUDE.md`: `.env` for `OPENAI_API_KEY`, gitignored) and Phase 2's own `CTO GATE` on credential storage (`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.4) must not adopt Manus's co-located key+DB pattern. |
| Naver auth + payload + upload code (`app/markets/naver_auth.py`, `naver_client.py`, real `create_product()` non-dry-run path) | **SECURITY-FORBIDDEN TO PORT** (code); **REUSE AS PATTERN ONLY** (the three-way separation shape, §2 above) | Prior audit `CONFIRMED` Critical #3: "Real Naver product creation can be triggered by the app when dry-run is disabled" — directly incompatible with Phase 1's `upload_mode: "manual_only"` contract and Phase 2's explicit `CTO GATE` on any real submission (`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.8). The auth mechanism itself is also unverified against official docs (`UNKNOWN` in Phase 2 §1.3) — porting an unverified signing implementation would be doubly wrong. Only the conceptual file-split (§2) is safe to reuse. |
| Dry-run toggle (concept + default-on UX) | **REUSE AS PATTERN ONLY** | Matches Phase 2's own already-proposed `dry_run()` adapter mode (§3.7) and Human Approval Mode default (§3.6); Manus's implementation (`products.html`'s checked-by-default checkbox + confirm-only-on-real-submit) is a validated UX shape worth mirroring, not code to import. |
| Device approval (`app/security.py`, cookie-based device tokens, dashboard approve/block/label/delete) | **SECURITY-FORBIDDEN TO PORT** (implementation); **DISCARD** as a concept for now | Prior audit `CONFIRMED` High #2/#3: no CSRF protection on state-changing routes, cookies not marked secure. Also, AI-Content-OS currently has no multi-device LAN-exposed operator surface at all — there is no existing engine this would extend, so it is not a data-contract or adapter-shape item; it is a whole auth subsystem that would need to be designed fresh, under ordinary web-security review, if AI-Content-OS ever ships a networked operator UI. Classifying as `DISCARD` rather than `NEW BUILD REQUIRED` because no current Commerce Phase 1/2 scope calls for a LAN-exposed multi-device UI at all yet — this is speculative beyond current approved scope. |
| Job queue (`app/jobs.py`, in-memory thread + polling dict) | **REUSE AS PATTERN ONLY** | The `queued/running/done/failed` + progress + bounded log-line shape (§3 above) is a reasonable, already-validated-by-the-prior-audit ("Job lifecycle shape... can inform a safe Commerce operation queue", `SELLER_AUTOMATION_AUDIT.md` §7) idea for a future Phase 2A dry-run-generation job or Phase 1 batch-generation job. The in-memory, non-durable implementation itself (`CONFIRMED` risk: "server restart loses job state", audit §5 High #6) should not be copied — any real AI-Content-OS job queue should be durable, consistent with this project's existing pattern of writing every stage result to `storage/`. |
| Detail-page assembly (`app/processing.py` name/price transforms + raw `detail_html` passthrough into `naver_payload.py`) | **DISCARD** | `CONFIRMED`/`INFERRED` per the prior audit §3.5: "A separate AI/content detail-page generator was not found... packages existing source detail content and basic processing, but does not implement AI-Content-OS style truth-gated detail-page sections, rights checks, or freshness gates." AI-Content-OS's Commerce Phase 1 `_detail()` method (`modules/commerce/commerce_module.py` lines 164-184) already does something categorically more rigorous — per-section `status`/`source_ids`, blocked-when-required-and-missing — and Content Engine's own established fallback-first, LLM-parse-then-normalize pattern (per `CLAUDE.md`) is more mature than Manus's raw-HTML passthrough + regex name cleanup. Nothing here is worth reusing even as a pattern. |
| Processing/margin rules (`ProcessingProfile`, `calc_sale_price()`) | **NEW BUILD REQUIRED** (if ever approved) | Phase 1 has no concept of computing a sale price from wholesale cost + margin/fee/rounding — it only renders an already-supplied, source-verified price (§1.2 above). If AI-Content-OS ever wants margin-based dynamic pricing, that is new product scope requiring its own truth/freshness design (what verifies the wholesale cost input itself?), not a Manus-derived feature — Manus's specific formula (`app/processing.py`'s `calc_sale_price()`) is a reasonable *reference formula shape* to look at when that scope is eventually approved, but is not something to build from today. |
| Coupang/Gmarket/Toss support | **DISCARD** (from Manus specifically) | `CONFIRMED`, prior audit §3.4: "No Coupang/Gmarket/Toss client implementation... was found" — `stub/placeholder` only, disabled UI. Nothing to reuse. AI-Content-OS's own Coupang work is already gated separately via `.codex/skills/ai-content-os-coupang/SKILL.md` and Phase 2's own `CoupangAdapter` `PROPOSAL` (which is materially better-researched against official Coupang docs than anything in Manus, per `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §2). |
| Naver field-name vocabulary embedded in `naver_payload.py` (`leafCategoryId`, `productInfoProvidedNotice`/11 food-notice sub-fields, `originAreaInfo`, `optionCombinations`, `deliveryFeeType`) | **REUSE AS PATTERN ONLY** (data-contract hint, unverified) | See §1.3/§1.4 above — genuinely useful as a research lead narrowing Phase 2's own `UNKNOWN` gaps (§1.6/§1.7 of `COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`), but explicitly not `CONFIRMED` against official Naver docs and must be independently verified, exactly as that document's own evidentiary standard already requires for every other third-party source. |
| FarmersGo desktop/extension (any capability) | **N/A — not found** | See §0. No classification is possible for something that does not exist in this repository. |

---

## 5. Proposed Flow for AI-Content-OS's Own Future Commerce Evolution

Built only from already-approved/existing AI-Content-OS pieces (Phase 1's truth-gated generation,
Phase 2's `PROPOSAL`-stage dry-run adapters) plus the Manus UX/pattern ideas from §2/§3 above.
Every step below that does not already exist in the repository is marked `PROPOSAL` and remains
subject to the same `CTO GATE`s already documented in `COMMERCE_PHASE_1_CONTRACT.md` §9 and
`COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §5. Nothing below assumes Manus's scraping or
direct-upload code gets reused, per the task's explicit instruction.

```text
1. Product-collection            (PROPOSAL, NEW BUILD REQUIRED — no Manus scraper reuse)
   A human/import step supplies a commerce_request-shaped product with real sources —
   never an automated scrape. If a future collection mechanism is ever approved, it must
   independently satisfy Phase 1's source/rights model from day one; Manus's crawlers are
   explicitly excluded as an implementation source (see classification table, row 1).

2. Price-calculation             (PROPOSAL, NEW BUILD REQUIRED, out of current scope)
   Only if/when a margin-based pricing capability is separately approved (see classification
   table row 8) — and even then, the *input* wholesale cost must itself be a Phase 1-gated
   verified fact, not a live-scraped Manus-style DB row. Until then, price must be
   merchant-supplied and independently source/freshness-gated exactly as Phase 1 already
   requires; nothing here changes.

3. Copy-generation                (EXISTING — CommerceModule.run(), Phase 1, CONFIRMED, unmodified)
   modules/commerce/commerce_module.py already implements the truth/source/freshness gates,
   detail_page assembly, and platform_packages(smartstore/coupang) generation described in
   docs/COMMERCE_PHASE_1_CONTRACT.md. This step needs no new work to support this flow —
   it already refuses to fabricate anything.

4. Review                         (PROPOSAL — UX pattern only, from Manus §3 above)
   A future operator screen presents CommerceModule's own missing_fields/blocked_reasons/
   platform_packages output using the collect -> review-table -> action-panel screen shape
   observed in Manus's dashboard.html/products.html: a status-badged item list, a live
   selection count, and a safe-default toggle. This is a UX-pattern borrow only — the
   review screen's own authentication/session/CSRF handling must be designed fresh (see §3's
   explicit exclusion), and the data it reviews is exclusively Phase 1's already-gated
   commerce_result, never a raw Manus-style scraped record.

5. Manual-upload package           (EXISTING — Phase 1's manual_upload_checklist + *_package.txt,
                                     CONFIRMED, unmodified)
   Terminal state for all current, approved scope: storage/commerce/<request_id>/
   {smartstore,coupang}_package.txt plus the manual_upload_checklist, exactly as Phase 1
   already produces. Real upload remains entirely out of scope until Phase 2's CTO GATE
   (COMMERCE_PHASE_1_CONTRACT.md §9 / COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md §5) is
   explicitly approved — at which point Phase 2A's dry-run adapter (already PROPOSAL-designed,
   informed structurally but not by-code by Manus's auth/payload/client split, §2 above) would
   sit between this step and any future real submission, with its own review screen reusing the
   same collect -> review -> safe-default-toggle -> confirm-on-danger shape from step 4.
```

This flow adds no new `WorkflowEngine` wiring, no new external API calls, and no code copied from
`external_workmanus/`. It only names an ordering for capabilities that are either already built
(Phase 1) or already `PROPOSAL`-stage designed (Phase 2), and slots in the two Manus-derived
non-code ideas (§2's adapter-shape pattern, §3's review-screen UX shape) at the points where they
are structurally relevant.

---

## 6. Confirmation of Task Boundaries

- No file under `external_workmanus/**` was modified.
- `data/`, `venv/`, `logs/`, and bytecode/cache files under `external_workmanus/seller_automation/`
  were not opened or read at any point in this task.
- `docs/RESEARCH/MANUS/SELLER_AUTOMATION_AUDIT.md` was read in full and not modified.
- No file was written by this task other than this one:
  `docs/RESEARCH/COMMERCE/MANUS_FARMERSGO_INTEGRATION_PLAN.md`.
- No git write operation, application execution, login, API key request, or browser automation was
  performed.
