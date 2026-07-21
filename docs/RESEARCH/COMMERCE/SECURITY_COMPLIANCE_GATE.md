# Commerce Phase 2 — Security & Compliance Gate

Author: Claude Security and Compliance Architect
Status: **RESEARCH + DESIGN DRAFT. No code, credentials, accounts, or shared status document
touched. No secret value read (including no `.env` open). No login, API key request, product/order
operation, or browser automation performed.**

Scope: this document defines the security and compliance checklist and CTO approval-gate structure
that must be satisfied before Commerce Phase 2 (real SmartStore/Coupang marketplace integration)
moves from research/design into any implementation phase. It extends, and does not weaken or
duplicate-govern, the existing `CONFIRMED` contracts already in force:

- `docs/COMMERCE_PHASE_1_CONTRACT.md` — the implemented, offline-only Phase 1 truth/source/
  freshness/rights gate model and its own §9 Phase 2 CTO approval gate (this document does not
  replace §9; it operationalizes it into a staged, checkable gate structure).
- `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` — the Phase 2 adapter/dry-run/audit-log research
  and design draft (§3.4 credential storage, §3.8 automatic-registration CTO gate, §3.11 image
  rights, §3.17 PII are extended below, not redesigned).
- `docs/RESEARCH/MANUS/SELLER_AUTOMATION_AUDIT.md` §5 (Security And Compliance Risks) and §9
  (Execution Decision) — a real, concrete negative-example audit of a comparable local
  seller-automation prototype, used throughout this document as grounding for what to explicitly
  design against.

## Tagging Legend

- `CONFIRMED` — directly read from an official/primary source, or from this repository's own code
  or docs.
- `INFERRED` — derived from observed structure/precedent, not independently verified.
- `UNKNOWN` — not verified in this pass; typically requires direct official-domain access, legal
  review, or platform-side confirmation this document could not obtain.
- `BLOCKED` — cannot proceed under current conditions.
- `PROPOSAL` — this document's own security-design recommendation. Not built, not binding by
  itself.
- `CTO GATE` — requires a real business, legal, or financial decision by the CTO/human project
  owner. Never asserted as already decided in this document.

---

## 0. Negative-Example Baseline (what this design must not repeat)

`CONFIRMED`, from `docs/RESEARCH/MANUS/SELLER_AUTOMATION_AUDIT.md` §5: a comparable real-world
local seller-automation app exhibited six concrete failure patterns. Each is mapped below to the
section of this document that exists specifically to prevent it in AI-Content-OS.

| Manus finding (§5) | AI-Content-OS Phase 2 counter-design |
|---|---|
| Default admin password coexisting with `0.0.0.0` LAN binding | §8 (environment separation defaults to most restrictive/localhost-only; no default credentials ever shipped) |
| Runtime database co-located with its own decryption key | §1, §9 (secret storage location rules; never co-locate secret material with the data it protects) |
| Real marketplace product-creation reachable when a dry-run flag is merely off | §10 (staged rollout has hard entry/exit criteria per stage, not a single boolean) |
| Arbitrary remote image URL fetching during upload (SSRF-ish risk) | §4 (image provenance gate — only rights-confirmed, already-known-good image sources may ever be fetched/uploaded; no fetching an arbitrary URL found in scraped/collected product data) |
| No CSRF protection on state-changing routes; cookies not marked secure | §2 (this section also concludes Commerce Phase 2 should have no user-facing browser session surface of this kind at all in its initial scope — see rationale below) |
| Reused/unvalidated third-party HTML flowing into marketplace listings | §4, §5 (extends Phase 1's existing rights/provenance and review-quote gates to the upload step; no raw scraped HTML may reach a real listing unreviewed) |

---

## 1. API Key / Secret Key / OAuth Token Handling (SmartStore + Coupang)

### 1.1 What is `CONFIRMED` about each platform's credential model

- Naver Commerce API: `UNKNOWN` in `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1.3 whether
  auth is a standard OAuth2 `client_credentials` grant, or that plus a non-standard
  bcrypt-based `client_secret_sign` signature — sourced only from third-party blogs, not an
  official domain. `CTO GATE` (already recorded in §1.3/§3.2 of that document): the exact
  algorithm must be confirmed against `apicenter.commerce.naver.com` directly before any signing
  code is written; an incorrect signature algorithm is a hard integration blocker.
- Coupang Open API: `CONFIRMED` (§2.3 of the architecture doc) — HMAC signing using an Access Key
  (`CLIENT_KEY`) and a Secret Key, signature valid for up to ~5 minutes, one key per seller ID, max
  two "Integrators" per seller.

### 1.2 Storage location

`PROPOSAL`, building on the project's own existing baseline rather than replacing it: the project
today (`CONFIRMED`, `CLAUDE.md`/`AGENTS.md`) stores its one existing secret,
`OPENAI_API_KEY`, in a gitignored `.env` file with an explicit rule — never commit or print its
contents. This is an acceptable baseline for a single low-blast-radius LLM key.

Marketplace credentials are materially higher blast radius than the LLM key, for reasons specific
to this project's own stated future scope, not a generic claim:

- They gate real, irreversible marketplace side effects (`docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`
  §3.8 explicitly treats automatic registration as `CTO GATE`, not default-safe).
- Once §3.15 order sync exists, the same credentials also gate access to real customer PII
  (§3.17 of that document, and §3 of this document below).
- A leaked LLM key costs money; a leaked marketplace credential can create real, policy-violating,
  customer-facing listings or expose real customer shipping data — this is a different risk class,
  not a bigger version of the same risk.

`PROPOSAL`:

- Phase 2A (dry-run only, no credentials required) needs no change to the existing `.env`
  convention at all — there is nothing to store yet.
- Phase 2B (first real credential issuance) is the point at which `.env`-only storage should be
  treated as **the floor, not the target**. `.env` may continue to hold the actual key material
  (matching existing project convention, least operational disruption), but must additionally
  satisfy the co-location rule below regardless of storage backend.
- **Never co-locate secret material with the data it protects or with runtime application state.**
  This is the direct, named counter-design to Manus finding §5 Critical #2 (`data/seller.db` and
  `data/secret.key` sitting in the same folder — copying one folder is enough to decrypt
  everything). Concretely: `.env` (or any future secret store) must not live under `storage/`,
  must not be readable by the same process/user boundary that has no legitimate need for it, and
  must never be included in any `storage/commerce/` audit-log export, backup, or snapshot.
- `CTO GATE`: whether a dedicated secret manager (OS credential store, a vault product, or
  encrypted-at-rest file with separate key custody) replaces `.env` for marketplace credentials
  specifically is a real decision to make once Phase 2B is actually approved — this document
  recommends treating it as a real open question, not a settled "yes" or "no", precisely because
  the blast-radius reasoning above is new to this project (the LLM-key precedent alone does not
  answer it).

### 1.3 Rotation

`PROPOSAL`:

- Coupang: `CONFIRMED` one key per seller ID, so "rotation" in practice means re-issuing the key
  in Wing and updating stored credentials — no live dual-key rotation window is `CONFIRMED`
  available. `PROPOSAL`: treat rotation as a planned, logged, human-executed event (old key
  revoked, new key issued, credential store updated, one audit-log entry recording the rotation
  event by outcome only — see §9) rather than an automated background process, since automating
  credential rotation without a `CONFIRMED` dual-key grace window risks a self-inflicted outage.
- Naver: `UNKNOWN` rotation mechanics entirely (auth method itself is `UNKNOWN`, §1.1). `CTO GATE`:
  confirm rotation/re-authentication requirements directly before assuming any specific cadence;
  §1.2 of the architecture doc already flags a third-party claim of "periodic re-authentication"
  that is explicitly not relied upon.
- `PROPOSAL` baseline cadence pending platform-specific confirmation: treat any marketplace
  credential as due for human review at minimum every 90 days, and immediately upon any suspected
  exposure (e.g. an accidental log line, a committed `.env`, a shared debugging session) —
  consistent with the "never appears in logs" rule in §9 existing as a hard backstop, not a
  substitute for rotation discipline.

### 1.4 Least-privilege scoping

`PROPOSAL`, extending `docs/COMMERCE_PHASE_1_CONTRACT.md` §9's existing requirement ("explicit
decision on whether listing creation, update, inventory, price, and order scopes are individually
allowed") rather than introducing a new concept:

- If a platform's credential/app-registration flow supports scoped permissions (`UNKNOWN` for both
  platforms in this research pass — neither `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1.2/§2.2
  nor this document found a `CONFIRMED` scoping mechanism), request the minimum scope needed for
  the current rollout stage only (§10), not the full eventual capability set up front.
  `CTO GATE`: confirm actual scoping mechanics per platform before app/key registration.
  Coupang: `CONFIRMED` at most two "Integrators" (distinct API-consuming credentials) may be
  registered per seller — `PROPOSAL`: reserve one Integrator for the dry-run/sandbox-equivalent
  path and the second, if ever used, only for the human-approved real-upload path in §10 Stage 3,
  never both purposes on one credential.
- Regardless of platform scoping granularity, this project's own code must enforce the
  per-capability allow-list itself (creation/update/inventory/price/order, each individually
  toggled) at the `PlatformUploadAdapter` layer — `PROPOSAL`, matching
  `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.8 item (1) — so an over-broad platform
  credential never becomes an over-broad application capability.

---

## 2. Cookie / Browser-Session Handling

`PROPOSAL` (with a clear recommendation, not a hedge): **Commerce Phase 2 should not use
browser-session/cookie-based marketplace authentication at all, for any stage, including dry-run
and sandbox.**

Basis for this recommendation:

- `CONFIRMED`, `PROJECT_OPERATING_SYSTEM.md` "Offline-First Principle": *"No Instagram API, Meta
  Graph API, access-token-based auth, or real SNS login/crawling may be implemented without
  explicit future approval."* While this line is written about Instagram/Meta, it establishes this
  project's general posture toward session/login-based automation of third-party platforms: it is
  treated as a higher-approval-bar category than an official, documented API integration, not a
  default-acceptable shortcut.
- `CONFIRMED`, `.codex/skills/ai-content-os-cto-review/SKILL.md`: the CTO review process explicitly
  prefers "existing repository modules and installed first-party capabilities" and requires
  checking "official ... plugin examples and primary vendor documentation before adding
  dependencies" — the same reasoning that favors official SDKs over ad hoc integrations favors
  official marketplace APIs over cookie/session automation, which is not an officially supported
  integration surface for either platform and is inherently more fragile (breaks on any UI change)
  and higher-risk (a stolen/replayed session cookie grants the same access as a stolen API key,
  with none of a key's revocation/scoping/audit tooling).
- `CONFIRMED`, `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1.1/§2.1: both platforms have
  `CONFIRMED` official, documented APIs (Naver Commerce API, Coupang Open API) covering the
  product/order/fulfillment surface this project needs. There is no `CONFIRMED` capability gap
  that would force a fallback to session-based automation.
- Negative-example grounding, `docs/RESEARCH/MANUS/SELLER_AUTOMATION_AUDIT.md` §5 High #2/#3: the
  Manus app's own browser-facing session cookies (its *local admin dashboard*, not marketplace
  auth — Manus itself also uses official Naver API keys, not scraped SmartStore sessions) lacked
  CSRF protection and a `secure` flag. That is a distinct, cheaper mistake than marketplace
  session-cookie auth would be, and it still produced real risk. Marketplace-side session-cookie
  auth would import that entire risk class (CSRF, session replay, no first-party revocation) at a
  much higher blast radius (a real seller account, not a local dashboard).

`PROPOSAL`: if a future `CTO GATE` decision explicitly wants an operator-facing local admin UI for
Commerce Phase 2 (e.g. a human-approval review screen for §10 Stage 3/4), that UI's own session
cookies (unrelated to marketplace auth) must still be `HttpOnly`, `Secure`, `SameSite=Strict` (or
equivalent), CSRF-token-protected on every state-changing route, and bound to `127.0.0.1` by
default (§8) — i.e. the specific concrete failures found in Manus §5 High #2/#3 are named
requirements here, not assumptions.

`CTO GATE`: if a genuine, `CONFIRMED` future capability gap is ever found where the official API
truly cannot do something session automation could, that must be brought back as an explicit,
named exception request — not implemented by default under this document's approval.

---

## 3. PII (Orderer / Recipient Personal Data)

`PROPOSAL` (this document's own recommendation; existing Phase 2 design left this open):
`docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.17 already identifies this as unresolved —
*"This must never be written into any location this project already treats as
broadly-readable/loggable ... `CTO GATE`: decide whether order/PII data may live in the same
`storage/commerce/` tree at all, or requires a separately-access-controlled location, encryption
at rest, and a retention/deletion policy."* This document does not treat that as settled; it
restates it as a still-open `CTO GATE` and adds the following operational detail so the gate is
concrete and checkable when raised:

- **Scope of PII in play** (once §3.15 order sync exists, per the architecture doc): orderer
  name, recipient name, shipping address, phone number, and any order-note free text a buyer
  supplies. `CONFIRMED` this data does not exist anywhere in the current Phase 1 pipeline
  (`docs/COMMERCE_PHASE_1_CONTRACT.md` has no order/PII fields at all — Phase 1 is pre-order,
  content-generation only).
- `PROPOSAL` minimum bar, to be ratified or replaced by the `CTO GATE` above, not assumed live:
  - PII must not be stored in the same plain-JSON `storage/<engine>/` pattern the rest of this
    project uses today (`CONFIRMED`, architecture doc §3.17: every other Engine's storage is
    unencrypted JSON on disk with no access-control layer — acceptable for content/pattern/
    performance data, not acceptable for customer PII).
  - If any PII must transiently pass through this process (e.g. to generate a shipping label or
    invoice via §3.15's state machine), it should be handled in memory and persisted, if at all,
    only in a separately access-controlled store with encryption at rest — never inside
    `storage/commerce/<request_id>/` alongside the fully-readable content package artifacts.
  - PII must never appear in `upload_audit_log.jsonl` (§9) beyond an opaque reference (e.g. an
    order ID), consistent with the general "hash/outcome/status only" logging rule.
  - A retention/deletion policy (how long order PII is kept, and a deletion mechanism) is a real
    legal requirement in Korea for e-commerce operators handling customer data — `CTO GATE`:
    this is a compliance/legal decision, not an engineering default; this document flags it and
    does not set a retention period.
- This section applies only once order-sync (§3.15 of the architecture doc) is in scope, which is
  Phase 2D — after Phase 2A–2C (dry-run, sandbox, single human-approved product) in the staged
  rollout below (§10). No PII exists in this pipeline before that point.

---

## 4. Product Image Rights / Provenance

`CONFIRMED` alignment baseline: `docs/COMMERCE_PHASE_1_CONTRACT.md` §3 gate 6 already requires
"Rights/compliance: review quotes, images, certifications, and claims have documented use
permission and required attribution/disclosure" as an existing, in-force Phase 1 rule — every
`sources` entry carries `rights_or_permission`, and unrights-cleared images are blocked from
customer-facing copy today. This document does not redesign that gate; it extends it one step
further, to the upload boundary itself.

`PROPOSAL` (already previewed in `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.11, restated
here as an explicit, testable security rule): a `PlatformUploadAdapter` must refuse to include any
image in an outbound upload request whose Phase 1 record lacks a passing `rights_or_permission`
value — the same allow-list pattern already implemented and reviewed in
`modules/card_news/evidence_selector.py`'s `copyright_status` gate (reuse the *pattern*, not the
code, per this project's established cross-engine convention).

**Direct counter-design to the negative example**: `docs/RESEARCH/MANUS/SELLER_AUTOMATION_AUDIT.md`
§5 High #1 found the Manus app fetches arbitrary remote image URLs (`thumbnail_url` from scraped
product data) and uploads them during real listing — an SSRF-adjacent risk and an unreviewed-content
risk in one. AI-Content-OS Phase 2 must not replicate this shape at all:

- `PROPOSAL`: an adapter must never fetch an image URL that did not already pass through Phase 1's
  `rights_or_permission` gate and get recorded as a `sources` entry with a known `source_locator`.
  No adapter code path may accept or dereference an arbitrary URL supplied by upstream scraped/
  collected product data at upload time — the set of fetchable image locations is exactly the set
  Phase 1 already verified, not an open-ended fetch of "whatever URL the product record happens to
  contain."
- `UNKNOWN` (architecture doc §1.6/§2.6): neither platform's exact image upload mechanism
  (URL-reference vs. binary multipart vs. dedicated image-hosting API) is `CONFIRMED`. `CTO GATE`:
  until confirmed, no adapter payload may assume a specific mechanism (already flagged in the
  architecture doc; restated here because the mechanism choice also has security implications — a
  URL-reference upload mechanism, if that is what either platform actually uses, must still only
  ever reference a rights-cleared, already-known URL, never re-open the arbitrary-fetch risk above
  under a different name).

---

## 5. Review-Quote Usage Rights

`CONFIRMED` alignment baseline, same pattern as §4: `docs/COMMERCE_PHASE_1_CONTRACT.md` already
requires review-quote rights confirmation today — §3 gate 6 (rights/compliance) applies to review
quotes explicitly, and §7's manual upload checklist already states: *"Confirm review quotation
authenticity, permission, attribution, and absence of personal data; if not confirmed, do not
upload the quote."*

`PROPOSAL`: extend this unchanged rule to the automated-adapter path exactly as §4 extends the
image rule — a `PlatformUploadAdapter` must refuse to include a review quote in an outbound
payload unless it carries the same passing rights/permission/attribution/no-PII status Phase 1
already requires for a human doing manual upload. No new rights standard is introduced; the
existing Phase 1 bar simply must not be silently bypassed just because upload becomes automated
rather than manual. This also intersects with §3 (PII): a review quote containing an identifiable
reviewer's personal data is blocked by the existing Phase 1 rule regardless of rights status.

---

## 6. Affiliate-Link Disclosure

`CONFIRMED` alignment baseline: `.codex/skills/ai-content-os-coupang/SKILL.md` "Gates" section
already states, as an existing project rule: *"Never publish an affiliate link without disclosure
and user-approved account ownership."*

`PROPOSAL`: this rule is unchanged and extends directly to Commerce Phase 2 — no
`PlatformUploadAdapter`, publish-queue integration, or future affiliate-content workflow may emit
a live affiliate link without (1) an explicit, rendered disclosure adjacent to the link/content,
and (2) confirmed user/seller ownership of the affiliate account being linked (not a third party's
account, not an inferred/guessed account ID). This is a pre-existing gate, not a new one — this
document's only addition is naming it explicitly inside the security/compliance checklist so it is
not accidentally scoped out of a future Phase 2 review as "someone else's document's problem."
`CTO GATE`: any affiliate program terms-of-service review remains a legal/compliance decision, not
addressed further here.

---

## 7. Price / Stock Freshness Risk (At the Moment of Real Upload)

`CONFIRMED` alignment baseline: `docs/COMMERCE_PHASE_1_CONTRACT.md` §2/§3 already requires
`expires_at` on every volatile fact (price, discount, benefit, shipping promise, stock, sales
count, rating, review count, ranking are all `CONFIRMED` always-volatile) and already blocks a
value once `expires_at` has passed, at generation time.

**What "freshness risk" specifically means at upload time** (this document's own definition,
`PROPOSAL`, since this is the concrete elaboration the task asked for): freshness risk is the gap
between two distinct timestamps that Phase 1 alone cannot see:

```text
t0 = commerce_result.generated_at         (Phase 1 generation time — CONFIRMED field)
t1 = actual moment of platform submission  (Phase 2 adapter call time — does not exist in Phase 1)

freshness_risk = t1 - t0, compared against each volatile fact's own expires_at window
```

A package can be `ready_for_manual_upload` (all facts fresh as of `t0`) and still be dangerously
stale by `t1` if a human sits on the package for hours/days before actually uploading, or if an
automated pipeline queues it and only submits later. `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`
§3.5 step 3 and §3.10 already name this exact gap as a `PROPOSAL` pre-registration validation
step ("freshness at generation time" != "freshness at upload time") — this document does not
redesign that mechanism; it restates it as a named security/compliance checklist item because
uploading stale price/stock is both a customer-trust failure and, per §2.7/§2.13 of the
architecture doc, a `CONFIRMED` policy-violation risk on Coupang specifically (mandatory
required-purchase-option and other category policy can also change between `t0` and `t1`).

`PROPOSAL` checklist:

- Every adapter call re-runs Phase 1's exact freshness check against `NOW` (i.e. `t1`), never
  trusting `t0`'s already-passed check as still valid.
- Any fact that was fresh at `t0` but has since crossed its `expires_at` by `t1` is re-blocked
  (new `blocked_reasons` code `freshness_expired_since_generation`, already named in the
  architecture doc §3.5) — never silently uploaded.
- Category/notice metadata (§1.7/§2.7 of the architecture doc) is re-fetched live at `t1`, not
  reused from `t0`, for the same reason — platform policy can move between generation and upload
  (`CONFIRMED` example: Coupang's dated 2026-02-02 required-purchase-option policy change, §2.7).
- A maximum allowable `t1 - t0` gap is itself a `CTO GATE`-worthy operational parameter (how long
  a package may sit in a human-review or automated queue before it must be regenerated from Phase
  1 rather than re-submitted as-is) — this document does not set that number, since it depends on
  business review cadence, which is not a technical fact.

---

## 8. Dev / Test / Production Environment Separation

`PROPOSAL` (concrete scheme), with an explicit `UNKNOWN` flagged up front: `UNKNOWN`
(`docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1.13/§2.13/§4 Phase 2B row) — **sandbox/test-account
availability for either platform is not `CONFIRMED`**. Naver's is explicitly `UNKNOWN`; Coupang's
was not found in that research pass either. This is a material unresolved gap, not a minor detail
— the entire meaning of a "test environment" in §10 Stage 2 depends on it.

### 8.1 Proposed separation scheme (degrades safely when sandbox availability is unconfirmed)

| Environment | Credentials | Config flag | Network scope | Audit-log `environment` tag | Applies when |
|---|---|---|---|---|---|
| `dev` | None (no marketplace credentials loaded at all) | `COMMERCE_ENV=dev` | No outbound marketplace network calls possible — adapter `dry_run()` only | `"dev"` | Always available; default for all local development |
| `sandbox` | A platform-provided sandbox/test credential, distinct from any production key | `COMMERCE_ENV=sandbox` | Outbound calls only to the platform's confirmed sandbox endpoint (if `CONFIRMED` to exist) | `"sandbox"` | **Only if a real platform sandbox is confirmed to exist** (§8.2 below governs what happens if not) |
| `production_limited` | Real production credential, scoped to the minimum stage-appropriate capability (§1.4) | `COMMERCE_ENV=production_limited` | Real platform production endpoint, single-item human-approved calls only (§10 Stage 3) | `"production_limited"` | Only after explicit `CTO GATE` per §10 Stage 3 entry criteria |
| `production_auto` | Real production credential, full approved scope | `COMMERCE_ENV=production_auto` | Real platform production endpoint, unattended calls | `"production_auto"` | Only after the CTO GATE structure in §11 is fully satisfied — not proposed as enabled by this document |

`PROPOSAL`: every `upload_audit_log.jsonl` entry (§9) carries an explicit `environment` field from
this table — never inferred from which credential happened to be loaded, so a misconfigured
credential swap cannot silently mislabel a real production call as a test one in the audit trail.

### 8.2 Safe degradation when sandbox availability is unconfirmed

Per the task's explicit instruction, this scheme must default to the most restrictive/manual mode
whenever sandbox availability cannot be confirmed — `PROPOSAL`:

- If, after a `CTO GATE`-directed direct check of `apicenter.commerce.naver.com` and
  `developers.coupangcorp.com` (the access this research pass could not obtain, per
  `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §0), no real sandbox/test environment is
  confirmed for a given platform, the `sandbox` row above is **skipped entirely for that
  platform** — there is no substitute "pretend sandbox" using real production credentials in
  disguise.
- In that case, the rollout for that platform proceeds directly from `dev` (dry-run payload
  generation, §10 Stage 1) to `production_limited` (§10 Stage 3: a small number of real, low-risk
  products with mandatory human approval on every single item) — i.e. the missing sandbox stage is
  not silently skipped in a way that increases risk; instead the human-approval requirement of
  Stage 3 is what absorbs the lost safety margin a sandbox would have provided. This is the
  concrete meaning of "degrade to the most restrictive/manual mode": skipping the automated-test
  stage does not permit skipping or loosening the human-review stage that follows it.
- This platform-by-platform difference must itself be recorded and visible (e.g. a
  `sandbox_confirmed: true/false` field alongside each platform's rollout-stage tracking), not
  quietly assumed by omission.

### 8.3 Separation enforcement details

`PROPOSAL`:

- Distinct credential sets per environment row (§8.1) — a `sandbox` credential, if one exists,
  must never be reused as a `production_limited` credential and vice versa; this is the direct
  counter-design to Manus §5 Critical #2's co-location risk pattern generalized to environments,
  not just secret files.
- `COMMERCE_ENV` (or equivalent) must be an explicit, required config value with no default that
  resolves to a production-capable environment — an unset/misconfigured value must fail closed to
  `dev` (dry-run only, no network calls), never fail open to `production_auto`.
- Local development must bind to `127.0.0.1` only if any local operator UI exists at all (§2),
  directly countering Manus §5 Critical #1's `0.0.0.0` LAN-binding-plus-default-password pattern —
  no Commerce Phase 2 component should ever default to listening beyond localhost.

---

## 9. Secret Storage Location and Log Masking

This section states the explicit, testable rule the task requires — not a general aspiration.

### 9.1 The rule

**No secret value, HMAC/OAuth signature, or bearer/access token may ever appear in any log line,
`upload_audit_log.jsonl` entry, error message, exception trace, or any file under `storage/`, in
full or in part, at any verbosity level, in any environment (§8).** The only things a log or audit
entry may ever record about a credential-bearing operation are:

- A payload hash (e.g. `sha256` of the outbound request body) — `CONFIRMED` already proposed in
  `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.12's audit-log schema
  (`request_payload_hash`), restated here as a hard rule rather than a schema suggestion.
- An outcome/status (success/failure, HTTP status code, platform error code such as the
  `CONFIRMED` `GW.RATE_LIMIT` or HTTP 429).
- A human-readable, secret-free response summary.
- A reviewer identity and timestamp, for human-approved actions.
- An idempotency key (derived from `request_id` + `product_id`, per architecture doc §3.9 — not
  secret material itself).
- An `environment` tag (§8.1).

### 9.2 How this is testable, not just aspirational

`PROPOSAL`:

- A credential value (access key, secret key, signature, token) must never be passed as a
  positional/keyword argument to any logging call, string-formatted into any log/exception
  message, or included in any object that gets serialized to `storage/commerce/**` or
  `upload_audit_log.jsonl`.
- Before any Phase 2B+ implementation is considered complete, a concrete verification step must
  exist and pass: grep every generated log file and every `storage/commerce/**` artifact from a
  real (or sandbox, or dry-run) run for the loaded credential's known value/prefix and confirm zero
  matches. This is a deliberately mechanical, repeatable check — "the credential's literal
  characters do not appear anywhere on disk outside its own storage location" — not a
  code-review-only assurance.
- Exception handling around any adapter network call must catch and re-raise/log a sanitized
  error, never the raw request object or raw response headers verbatim if either could contain
  signing material (e.g. an `Authorization` header, a `GNCP-GW-*` internal token-bearing header if
  any such header ever carries more than rate-limit metadata — `CONFIRMED` architecture doc §1.11
  headers are rate-limit-only and safe, but this rule applies generally to any future header, not
  just the ones currently known).
- This rule applies uniformly across all environments in §8.1, including `dev`/`dry_run`, where no
  real credential may exist yet but the discipline must already be in place before real credentials
  are ever introduced.

---

## 10. Staged Rollout: Dry-Run → Sandbox → Limited Real → Limited Automatic

This restates and operationalizes `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §4's phased plan
(Phases 2A–2E) as an explicit security/compliance gate structure, with the sandbox-unavailability
degradation from §8.2 folded in. It does not change the phase content already defined there; it
adds explicit rollback triggers alongside each stage's existing entry/exit criteria, per this
task's requirement.

### Stage 1 — Dry-Run (Phase 2A)

- **Entry criteria**: Phase 1 contract stable (`CONFIRMED`, already true); a real
  `ready_for_manual_upload` Phase 1 package exists to generate a payload from; zero credentials
  required or loaded.
- **Exit criteria**: a platform-shaped request payload is reproducibly generated from a real Phase
  1 output, every field traceable to a `CONFIRMED` platform field mapping (any `UNKNOWN`-gap field
  explicitly marked `pending_confirmation`, never guessed), reviewed by a human against what the
  real seller UI would actually require, with zero network calls made.
- **Rollback trigger**: any adapter code path found to make (or attempt) a real network call during
  this stage is a stop-the-line finding — delete/disable the adapter immediately; this stage must
  have zero network-call capability by construction, not by discipline alone.

### Stage 2 — Sandbox (Phase 2B) — conditional on §8.2

- **Entry criteria**: Stage 1 complete; `CTO GATE` credential/account approval obtained (§11); a
  real platform sandbox/test environment has been `CONFIRMED` to exist for that specific platform
  (direct official-domain check, not third-party sourcing) — if not confirmed for a platform, that
  platform skips directly to Stage 3 per §8.2, and this stage is marked `not_applicable` for it,
  not silently passed.
- **Exit criteria**: a Stage 1 dry-run payload successfully validates against the real platform's
  sandbox/validation endpoint without creating any live listing.
- **Rollback trigger**: any sandbox call that appears to affect real production data or a real
  listing (a sandbox/production boundary failure) halts the platform's rollout immediately, reverts
  to Stage 1 only, and requires a fresh `CTO GATE` re-approval before re-attempting Stage 2 — this
  is treated as a possible platform-side or integration-side environment-isolation failure, not a
  minor bug.

### Stage 3 — Limited Real Registration, Human Approval on Every Item (Phase 2C)

- **Entry criteria**: Stage 2 complete (or explicitly `not_applicable` per §8.2 for platforms with
  no confirmed sandbox); `CTO GATE` first-test-product selection (§11) satisfied — low commercial
  risk, no safety-critical/regulated category beyond Phase 1's already-modeled notice fields,
  single option/no complex variant matrix, only already-rights-cleared images (§4).
- **Exit criteria**: one real listing created, a human reviewer verifies it directly in the seller
  UI (not just trusting the API response), price/stock/detail content confirmed correct, no policy
  violation observed. Every single item in this stage requires its own individual human approval —
  no batch approval, no "approve once, submit many" shortcut, for the entire duration of this
  stage.
- **Rollback trigger**: any policy rejection, any observed price/stock/content mismatch between
  what was submitted and what appears live, or any platform error not already accounted for in
  §3.13's partial-failure handling triggers immediate use of the platform's confirmed
  deactivation/stop-sales capability (`CONFIRMED` Coupang 판매중지 endpoint, architecture doc
  §2.5/§3.14; Naver's equivalent is `UNKNOWN` and must be confirmed before this stage begins for
  Naver specifically) and a mandatory incident write-up regardless of outcome, per
  `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §4's existing Phase 2C rollback row.

### Stage 4 — Limited Automatic Registration (Phase 2E)

- **Entry criteria**: Stage 3 (and, if in scope, Stage 2D order/shipping sync) stable over an
  extended, `CTO GATE`-defined observation period with zero incidents; the full CTO approval gate
  structure in §11 satisfied, including an explicit per-capability scope approval.
- **Exit criteria**: not scoped by this document, matching `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`
  §4's Phase 2E row — this document does not propose enabling this stage, only what would be
  required if a future `CTO GATE` explicitly approves it.
- **Rollback trigger**: any automatic-mode incident (policy violation, pricing/stock error,
  unexpected platform block) triggers an immediate, automatic kill-switch back to Stage 3
  (human-approval-per-item), not a lesser automatic mode — `CONFIRMED` requirement already named
  in architecture doc §3.8 item (3), "real-time platform error-rate monitoring wired to an
  automatic kill-switch," restated here as this stage's rollback trigger specifically.

---

## 11. CTO Approval Gates Required Before Any Automatic Upload

This section consolidates every gate named above plus `docs/COMMERCE_PHASE_1_CONTRACT.md` §9's
existing requirements into one exhaustive, concrete checklist. **None of the following are
approved by this document.** Every row is `CTO GATE`.

1. **Accounts**: a real Naver SmartStore seller account and a real Coupang Wing seller account,
   both under confirmed business ownership. (`CONFIRMED` not created or accessed by this document
   or the architecture research doc.)
2. **Credentials issued**: Naver Commerce API application ID/secret and Coupang Access
   Key/Secret Key, each issued through the platform's own official process — never fabricated,
   guessed, or reused from an unrelated account. Storage location per §1.2, environment separation
   per §8.
3. **Named workflow owner**: a specific person accountable for this capability's ongoing operation,
   credential custody, and incident response — not an implicit/shared ownership assumption.
   (`CONFIRMED` required already, `docs/COMMERCE_PHASE_1_CONTRACT.md` §9.)
4. **Legal/compliance sign-off**: covering product claims, required category notices, review-quote
   usage (§5), image rights (§4), affiliate disclosure (§6), and — once in scope — order/PII
   handling and retention (§3). (`CONFIRMED` required already, §9; PII specifics are this
   document's own added detail, §3.)
5. **Named first test product**: satisfying the low-risk criteria in §10 Stage 3 entry criteria —
   named and reviewed before Stage 3 begins, not selected ad hoc at submission time.
6. **Explicit per-capability scope approval**: creation, update, inventory, price, and order
   actions individually and separately approved — `CONFIRMED` already required,
   `docs/COMMERCE_PHASE_1_CONTRACT.md` §9 ("explicit decision on whether listing creation, update,
   inventory, price, and order scopes are individually allowed"), and this document adds no weaker
   alternative to it anywhere above.
7. **Sandbox/staging confirmation or explicit acceptance of its absence**: per §8.2, either a real
   confirmed sandbox exists for a platform, or the CTO explicitly accepts that platform's rollout
   proceeds directly from dry-run to human-approved-single-item (Stage 3) with no automated test
   stage in between.
8. **Product-data readiness**: a real product with fully sourced, verified facts already passing
   Phase 1's existing truth/source/freshness gates (`ready_for_manual_upload`, zero
   `blocked_reasons`) — Phase 2 must never be the first place a product's facts are verified.
   (`CONFIRMED` required already, architecture doc §5.)
9. **Cost and terms/policy risk review**: platform fee schedules (`UNKNOWN`, not researched, per
   architecture doc §3.19/§5) and each platform's terms of service, confirmed directly rather than
   assumed — including Coupang's `CONFIRMED` live, dated (2026-02-02) policy-change pattern, which
   means this is not a one-time review.
10. **Audit log and kill-switch operational readiness**: `upload_audit_log.jsonl` (§9) verified to
    contain zero secret material via the mechanical check in §9.2, and — specific to Stage 4 only —
    a working automatic kill-switch verified before any unattended call is permitted.
11. **Rollback capability confirmed per platform**: Coupang's stop-sales/deactivation endpoint is
    `CONFIRMED` to exist (architecture doc §2.5); Naver's equivalent is `UNKNOWN` and must be
    confirmed before that platform enters Stage 3, since Stage 3's rollback trigger (§10) depends
    on having a real deactivation mechanism to invoke.

**The single most load-bearing gate above is #6 (explicit per-capability scope approval,
individually for creation/update/inventory/price/order)** — every other gate in this document
(credential scoping in §1.4, the staged rollout in §10, the automatic-mode kill-switch in Stage 4)
is only as strong as this gate being genuinely per-capability rather than a single blanket "yes,
enable Commerce Phase 2" approval. `docs/COMMERCE_PHASE_1_CONTRACT.md` §9 already establishes this
requirement; this document's role is to ensure nothing proposed above ever provides a path that
bypasses it — none does.

---

## Summary for Reviewers

This document adds no new implementation and touches no other file. It operationalizes the
security/compliance dimension of `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`'s existing
`PROPOSAL`/`CTO GATE` design into: (1) an explicit credential storage-and-blast-radius argument
that builds on, rather than replaces, the project's existing `.env` convention; (2) a firm
recommendation against any marketplace session/cookie auth; (3) a restated-open PII `CTO GATE`
with concrete operational detail; (4)/(5) direct extensions of Phase 1's already-`CONFIRMED`
image-rights and review-quote-rights gates to the upload boundary; (6) a restatement of the
existing affiliate-disclosure gate; (7) a precise technical definition of upload-time freshness
risk; (8) a concrete dev/sandbox/production separation scheme that explicitly degrades to the more
restrictive human-approval-only path when sandbox availability is unconfirmed, exactly as
instructed; (9) an explicit, mechanically testable no-secrets-in-logs rule; (10) a staged rollout
with named rollback triggers per stage; and (11) a consolidated, exhaustive CTO approval-gate
checklist that weakens none of Phase 1 §9's existing requirements. Every negative example from the
Manus Seller Automation audit (§5) is explicitly named and mapped to the section of this document
designed to prevent its recurrence in AI-Content-OS.
