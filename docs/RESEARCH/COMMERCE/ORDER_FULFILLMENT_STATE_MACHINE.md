# Order Collection → 발주확인 → 송장입력 → 배송추적 → 취소/교환/반품 State Machine

Author: Claude (Commerce Architecture Specialist, assigned deliverable)
Status: **DRY-RUN / DESIGN-ONLY OPERATING CONTRACT.**

> **THIS ENTIRE DOCUMENT IS A DRY-RUN, DESIGN-ONLY OPERATING CONTRACT.**
> No real SmartStore or Coupang API was called, no seller account was logged into, no API key
> was requested or issued, no real order, invoice, shipment, cancellation, exchange, or return
> was queried, created, modified, or simulated against a live system in the production of this
> document. Every payload shape, endpoint reference, and platform behavior claim below is either
> a direct citation of prior CONFIRMED research (`docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`),
> a newly obtained CONFIRMED legal-source citation (§7), or an explicitly labeled PROPOSAL /
> INFERRED / UNKNOWN / BLOCKED / CTO GATE item. This document authorizes **nothing**. It is a
> contract to be reviewed, not a system to be run.

Legend (same convention as `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`):

- `CONFIRMED` — verified directly against an official-domain source (this document or its
  predecessor fetched/read the primary source).
- `CONFIRMED (official channel)` — verified via an official technical-support channel (e.g. the
  `commerce-api-naver/commerce-api` GitHub org) rather than formal documentation prose.
- `CONFIRMED (existence only)` — an official source confirms a capability/endpoint exists;
  field-level/schema detail remains unconfirmed.
- `INFERRED` — derived from confirmed facts or established project code patterns, not itself
  independently verified.
- `UNKNOWN` — no reliable source found this pass; must not be treated as fact.
- `BLOCKED` — cannot be resolved without an approval, credential, or account this document is not
  authorized to obtain.
- `PROPOSAL` — this document's own design choice. Not built, not approved, not binding until a
  CTO reviews it.
- `CTO GATE` — requires explicit human/CTO approval (and, where noted, legal review) before any
  implementation may proceed.

---

## 1. Purpose and Scope

This document extends `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.15 ("Order /
Purchase-Order / Invoice Status State Machine"), §3.17 ("Personal Data and Shipping-Address
Protection"), and §3.18 ("CS / Return Status Synchronization") from a two-paragraph sketch into a
complete, formal operating contract: every state, every valid transition, idempotency, retry,
audit logging, human-approval checkpoints, and a PII policy — for **both** SmartStore and Coupang,
covering order collection → 발주확인 (purchase-order confirmation) → 송장입력 (invoice/tracking
entry) → 배송추적 (shipment tracking) → 취소/교환/반품 (cancel/exchange/return).

It is a **contract and state-machine design**, not an implementation. No code is written here, no
`modules/**` file is touched, and — per `docs/COMMERCE_PHASE_1_CONTRACT.md` §9 and
`docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §5 — no part of this design is authorized to run
against a real account until a human CTO explicitly approves each numbered gate.

This document is additive to, and does not replace, override, or contradict:

- `docs/COMMERCE_PHASE_1_CONTRACT.md` (CONFIRMED, implemented, the only real code today —
  offline copy generation with truth/source/freshness gates).
- `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` (PROPOSAL/research, prior art this document
  builds on; its §3.15/§3.17/§3.18 sketch is the seed this document formalizes).
- `.codex/skills/ai-content-os-coupang/SKILL.md` (CONFIRMED project rule: "Treat Coupang as a
  Roadmap capability until the user approves a dedicated Sprint").
- `ROADMAP.md` "Requires External API" section and `PROJECT_OPERATING_SYSTEM.md`'s Offline-First
  Principle (CONFIRMED: no real marketplace login/API call may be implemented without explicit
  future approval).

---

## 2. Design Principle: Build the Shape from Confirmed Operational Logic, Not from Unresolved API Detail

Per the assignment, the state machine's shape is derived from **platform-agnostic operational
logic** that is true of order fulfillment regardless of API specifics — receive an order, confirm
intent to fulfill it, ship it with a tracking number, track delivery, and allow cancel/exchange/
return to branch off at realistic points. Where `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`
already established a CONFIRMED platform-specific fact (invoice-upload preconditions, duplicate
windows, rate-limit asymmetry, etc.), this document uses it directly. Where a platform detail
remains `UNKNOWN`, the corresponding transition is still fully defined in the canonical state
machine, and the platform-specific integration point is marked `pending_confirmation` rather than
blocking the whole design — consistent with the assignment's explicit instruction not to let
unresolved API trivia block the contract's shape.

---

## 3. Canonical State Machine

### 3.1 State Definitions

All states below are **PROPOSAL** (this document's design) unless the "Platform basis" column
cites a specific CONFIRMED fact from `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`.

| # | State | Meaning | Platform basis |
|---|---|---|---|
| S0 | `DISCOVERED` | An order appears in a platform order-collection/query response; not yet imported into the local ledger. Read-only, pre-ingestion. | Naver order collection: `CONFIRMED (existence only)`, §1.8. Coupang order collection: `CONFIRMED (existence only)`, §2.8. |
| S1 | `ORDER_RECEIVED` | Order imported into the local commerce ledger; assigned a local `order_local_id` and an idempotency key (§4). Terminal ingestion point — nothing platform-side has been written yet. | PROPOSAL (local state); backed by S0's confirmed read APIs. |
| S2 | `PO_CONFIRMED` (발주확인) | Local ops has reviewed the order and confirmed intent to fulfill it — the seller-side "accept this order for picking" decision. For Coupang, this state's platform-facing counterpart is the confirmed 발주서(purchase/dispatch-order document) upload step that precedes invoice upload (§2.9, `CONFIRMED (existence only)`: "a separate 발주서 upload step precedes invoice upload, followed by an 출고전표-based fulfillment-processing step"). For Naver, no distinct confirm-order API was found this pass — `UNKNOWN`, `pending_confirmation`. | Coupang: `CONFIRMED (existence only)` (§2.9). Naver: `UNKNOWN`. |
| S2a | `OUTBOUND_PROCESSING` (출고전표 처리, optional sub-phase) | Optional internal picking/packing/outbound-slip sub-state between PO confirmation and invoice entry. Not a formally separate top-level state in the transition table (§3.3) — recorded as ops metadata within `PO_CONFIRMED`, since exact platform API boundaries for this step are `UNKNOWN` (§2.9: "exact endpoint names for the purchase-order/outbound-slip steps are UNKNOWN"). | Coupang: `CONFIRMED (existence only)` step exists; schema `UNKNOWN`. |
| S3 | `INVOICE_ENTERED` (송장입력) | A carrier + tracking/invoice number has been submitted to the platform for this order. | Coupang: `CONFIRMED` — invoice-upload API exists, valid only when the order is in "상품준비중" status, and duplicate invoice numbers within a 6-month window are rejected (§2.9). Naver: `CONFIRMED (official channel)` — a "Modified Product Order History Search"-type API with a `DISPATCHED`-type `lastChangedType` value confirms dispatch/invoice completion is queryable (§1.9); the invoice-submission endpoint itself (as opposed to the query-after-the-fact) is `UNKNOWN`. |
| S4 | `SHIPPED` (배송지시 / dispatch-instructed) | The platform has accepted the invoice and transitioned the order to a dispatch/shipped state. | Coupang: `CONFIRMED` — invoice upload "transitions an order to a '배송지시' (dispatch-instructed) state" (§2.9). Naver: `CONFIRMED (official channel)` state is queryable via `lastChangedType=DISPATCHED` (§1.9); the state's own name/semantics beyond "dispatched" are `UNKNOWN`. |
| S5 | `IN_TRANSIT` (optional granularity) | Carrier-side tracking shows movement short of final delivery. Optional — most marketplace order APIs do not expose granular carrier scan events; this state exists in the model for platforms/carriers where it can be populated, and is otherwise skipped directly to S6. | `UNKNOWN` for both platforms this pass — carrier-level tracking granularity was not part of the confirmed research scope. |
| S6 | `DELIVERED` (배송완료) | Platform (or carrier integration) reports the order as delivered. | `UNKNOWN` (existence highly likely — both platforms track this operationally — but no specific confirmed endpoint/field was found this pass; `pending_confirmation`). |
| S7 | `FINALIZED` | Internal-only terminal state: the CS/dispute window (§7 retention policy driver) has closed with no open cancel/exchange/return action. No further state-machine transitions are valid from here except the PII purge action defined in §7. | PROPOSAL, no platform basis needed (purely local). |

**Cancel branch** (can originate from S1, S2, or — platform-dependent, `UNKNOWN` specifics — a
restricted post-S3/S4 window; see §3.4 irreversibility notes):

| # | State | Meaning | Platform basis |
|---|---|---|---|
| C1 | `CANCEL_REQUESTED` | Buyer- or seller-initiated cancellation request recorded. | Coupang: `CONFIRMED` cancel-order API exists (§2.10, `.../Cancel-an-order`). Naver: `CONFIRMED (official channel)` cancel/return/exchange claim information surfaced via order-detail inquiry (§1.10). |
| C2 | `CANCEL_APPROVED` | Seller (or platform, if buyer-initiated within an auto-approval window) approves the cancellation. Refund is triggered by this transition. | Coupang cancel-order response is `CONFIRMED` to report success/failure **per item** (`failedVendorItemIds` alongside succeeded ones, §2.10) — approval and execution are effectively the same confirmed API call; a separate "approved-but-not-yet-executed" sub-state is not confirmed to exist and is therefore folded into this one state rather than invented. |
| C3 | `CANCEL_REJECTED` | Seller declines a buyer-initiated cancel request (e.g., already shipped). Returns the order to its state immediately prior to `CANCEL_REQUESTED`. | `UNKNOWN` platform mechanics; state included because rejection is operationally certain to be possible once an order has shipped. |
| C4 | `CANCELLED` | Terminal. Refund completed. | Reached from `CANCEL_APPROVED`. |

**Return branch** (typically originates from `DELIVERED`, but a refused-delivery/undeliverable
case can originate from `SHIPPED`/`IN_TRANSIT` — platform-specific mechanics `UNKNOWN`):

| # | State | Meaning | Platform basis |
|---|---|---|---|
| R1 | `RETURN_REQUESTED` | Buyer files a return claim. | Coupang: `CONFIRMED` — Return-Cancellation Request List Query API returns receipt info, requester detail, reason, return items (§2.10). Naver: `CONFIRMED (official channel)` return approval/hold/reject surface exists (§1.10). |
| R2 | `RETURN_HOLD` | Claim placed on hold pending more information (documented capability on Naver; Coupang hold-equivalent `UNKNOWN`). | Naver: `CONFIRMED (official channel)` "return hold, return-hold release" listed explicitly (§1.10). Coupang: `UNKNOWN`. |
| R3 | `RETURN_APPROVED` | Seller approves the return claim. | Naver: `CONFIRMED (official channel)` "return approval" (§1.10). Coupang: `UNKNOWN` as a distinct step vs. folded into claim processing. |
| R4 | `RETURN_PICKUP_COMPLETE` | Returned item collected from the buyer. | `UNKNOWN` exact API for either platform this pass; state included because it is operationally required before a refund can be safely released. |
| R5 | `RETURN_REJECTED` | Seller rejects/withdraws the claim. Returns order to `DELIVERED` with a `dispute_flag` set. | Naver: `CONFIRMED (official channel)` "return rejection (withdrawal)" (§1.10). Coupang: return-withdrawal history query is `CONFIRMED` to exist (§2.10, `.../Query-return-withdrawal-history-by-receiptID`), confirming a withdrawal concept exists even though the originating rejection endpoint itself is `UNKNOWN`. |
| R6 | `RETURN_WITHDRAWN` | Buyer withdraws their own return request before completion. Returns order to `DELIVERED`. | Coupang: `CONFIRMED (existence only)` via the withdrawal-history query APIs (§2.10); date-range variant confirmed queryable over a max 7-day window. |
| R7 | `RETURN_COMPLETED` | Terminal. Refund issued. | Reached after `RETURN_PICKUP_COMPLETE` + seller inspection (inspection step itself is local/PROPOSAL, `UNKNOWN` whether either platform models it as a distinct API state). |

**Exchange branch** (originates from `DELIVERED`; `UNKNOWN` whether either platform allows
pre-delivery exchange — treated as not permitted in this design pending confirmation):

| # | State | Meaning | Platform basis |
|---|---|---|---|
| X1 | `EXCHANGE_REQUESTED` | Buyer files an exchange claim. | Naver: `CONFIRMED (official channel)` exchange pickup-completion/re-shipment/hold/rejection all listed as existing operations (§1.10), implying a request state precedes them. Coupang: `UNKNOWN` — exchange-specific endpoints not found via official source this pass (§2.10: "treat exchange-API specifics as UNKNOWN pending direct official confirmation"). |
| X2 | `EXCHANGE_HOLD` | Claim on hold. | Naver: `CONFIRMED (official channel)` "exchange hold, exchange-hold release" (§1.10). Coupang: `UNKNOWN`. |
| X3 | `EXCHANGE_APPROVED` | Seller approves the exchange. | `UNKNOWN` as a distinct step for either platform this pass; included for operational completeness, `pending_confirmation`. |
| X4 | `EXCHANGE_PICKUP_COMPLETE` | Original item retrieved from the buyer. | Naver: `CONFIRMED (official channel)` "exchange pickup-completion" (§1.10). Coupang: `UNKNOWN`. |
| X5 | `EXCHANGE_RESHIPPED` | Replacement item invoice entered and shipped. Modeled as a **linked sub-order**: this transition spawns a nested cycle through `INVOICE_ENTERED` → `SHIPPED` → `DELIVERED` for the replacement item, cross-referenced to the original `order_local_id` via an `exchange_of` field, never overwriting the original order's own state history. | Naver: `CONFIRMED (official channel)` "exchange re-shipment processing" (§1.10). Coupang: `UNKNOWN`. |
| X6 | `EXCHANGE_REJECTED` | Seller rejects the exchange claim. Returns order to `DELIVERED` with `dispute_flag` set. | Naver: `CONFIRMED (official channel)` "exchange rejection (withdrawal)" (§1.10). Coupang: `UNKNOWN`. |
| X7 | `EXCHANGE_COMPLETED` | Terminal. Replacement item delivered (i.e., the linked sub-order's own `DELIVERED` transition closes the parent exchange claim). | PROPOSAL; derived from the linked sub-order model above. |

Cross-cutting flag (not a state, an annotation applicable to any state): `DISPUTE_ESCALATED` — set
whenever the platform-reported state and the local expected state conflict, or whenever a
rejection (`C3`/`R5`/`X6`) is itself contested by the buyer. See §6 — this flag always forces a
manual-approval checkpoint and is never auto-resolved.

### 3.2 State Diagram

```text
                                   ┌───────────────┐
                                   │   DISCOVERED  │  (S0, read-only, pre-ingestion)
                                   └───────┬───────┘
                                           │ import + idempotency key assigned
                                           ▼
                                   ┌───────────────┐
                       ┌──────────►│ ORDER_RECEIVED│◄─────────────┐ (rejected cancel returns here)
                       │           └───────┬───────┘              │
                       │                   │ ops confirms intent  │
                       │                   ▼                      │
                       │           ┌───────────────┐              │
                       │  ┌───────►│  PO_CONFIRMED │◄─────────────┤ (rejected cancel returns here)
                       │  │        │ (+ optional    │              │
                       │  │        │ 출고전표 sub-  │              │
                       │  │        │ phase, S2a)    │              │
                       │  │        └───────┬───────┘              │
                       │  │                │ invoice/tracking     │
                       │  │                │ number submitted     │
                       │  │                ▼                      │
                       │  │        ┌───────────────┐              │
                       │  │        │INVOICE_ENTERED│  (irreversible forward, §3.4)
                       │  │        └───────┬───────┘
                       │  │                │ platform accepts,
                       │  │                │ dispatch-instructed
                       │  │                ▼
                       │  │        ┌───────────────┐
                       │  │        │    SHIPPED    │
                       │  │        └───────┬───────┘
                       │  │                │ (optional carrier
                       │  │                │  tracking events)
                       │  │                ▼
                       │  │        ┌───────────────┐
                       │  │        │  IN_TRANSIT   │ (optional, may be skipped)
                       │  │        └───────┬───────┘
                       │  │                │
                       │  │                ▼
                       │  │        ┌───────────────┐        return/exchange claims
                       │  │        │   DELIVERED   │◄───────────┐  branch from here
                       │  │        └───────┬───────┘            │
                       │  │                │ CS/dispute window  │
                       │  │                │ elapses, no open   │
                       │  │                │ claim               │
                       │  │                ▼                    │
                       │  │        ┌───────────────┐            │
                       │  │        │   FINALIZED   │ (terminal) │
                       │  │        └───────────────┘            │
                       │  │                                     │
   CANCEL branch (from S1/S2 only; post-S3 cancel is UNKNOWN/CTO GATE — see §3.4)
                       │  │
                       │  ▼
              ┌────────┴────────┐
              │ CANCEL_REQUESTED│
              └────┬───────┬────┘
                   │       │ reject
        approve    │       └──────────► (back to originating S1/S2 state)
                   ▼
           ┌───────────────┐
           │ CANCEL_APPROVED│ (irreversible, refund triggered)
           └───────┬───────┘
                   ▼
           ┌───────────────┐
           │   CANCELLED   │ (terminal)
           └───────────────┘

   RETURN branch (from DELIVERED)                 EXCHANGE branch (from DELIVERED)
   ┌─────────────────┐                             ┌───────────────────┐
   │ RETURN_REQUESTED│                             │ EXCHANGE_REQUESTED│
   └──┬───────┬───────┘                             └──┬───────┬────────┘
      │       │hold                                    │       │hold
      │       ▼                                        │       ▼
      │  ┌──────────┐                                  │  ┌──────────────┐
      │  │RETURN_HOLD│─────► (back to REQUESTED)        │  │EXCHANGE_HOLD │──► (back to REQUESTED)
      │  └──────────┘                                  │  └──────────────┘
      ▼                                                 ▼
  approve/reject/withdraw split:                    approve/reject split:
  ┌────────────────┐  ┌─────────────────┐          ┌─────────────────┐  ┌───────────────────┐
  │ RETURN_APPROVED│  │ RETURN_REJECTED │          │ EXCHANGE_APPROVED│  │ EXCHANGE_REJECTED │
  └───────┬────────┘  └────────┬────────┘          └────────┬─────────┘  └─────────┬──────────┘
          │           (back to DELIVERED,                    │           (back to DELIVERED,
          │            dispute_flag set)                     │            dispute_flag set)
          ▼                                                  ▼
  ┌───────────────────────┐                        ┌──────────────────────────┐
  │ RETURN_PICKUP_COMPLETE│                         │ EXCHANGE_PICKUP_COMPLETE │
  └───────────┬────────────┘                        └────────────┬─────────────┘
              ▼                                                  ▼
  ┌───────────────────┐                             ┌───────────────────┐
  │  RETURN_COMPLETED │ (terminal, refund issued)    │ EXCHANGE_RESHIPPED│ (spawns linked
  └───────────────────┘                              └──────────┬─────────┘  sub-order: new
                                                                 │            INVOICE_ENTERED
   RETURN_WITHDRAWN: buyer withdraws before completion,          ▼            → SHIPPED →
   returns order to DELIVERED (not diagrammed as a         ┌───────────────────┐  DELIVERED cycle)
   separate box — same shape as RETURN_REJECTED's          │ EXCHANGE_COMPLETED│ (terminal, closes
   return-to-DELIVERED edge, different trigger)             └───────────────────┘  when linked
                                                                                    sub-order delivers)
```

### 3.3 Full Transition Table

`Auto?` = eligible for fully-automatic execution once Phase 2 is CTO-approved and a track record
is established (§6 defines the exact eligibility bar). `Manual` = always requires human approval,
regardless of Phase 2 approval status, per this document's design (§6).

| From | To | Trigger | Platform confirmation | Irreversible? | Auto? |
|---|---|---|---|---|---|
| `DISCOVERED` | `ORDER_RECEIVED` | Order import job dedupes against idempotency key (§4) and creates local record | `CONFIRMED (existence only)` order query APIs exist (§1.8/§2.8) | No (read/import is idempotent) | Auto (read-only) |
| `ORDER_RECEIVED` | `PO_CONFIRMED` | Ops (or, post-approval, an automated rule) confirms intent to fulfill | Coupang 발주서 step `CONFIRMED (existence only)` (§2.9); Naver `UNKNOWN` | No | Manual until track record (§6); PROPOSAL default |
| `ORDER_RECEIVED` | `CANCEL_REQUESTED` | Buyer or seller requests cancellation before fulfillment starts | Coupang `CONFIRMED` (§2.10); Naver `CONFIRMED (official channel)` (§1.10) | No | Manual (money-adjacent, §6) |
| `PO_CONFIRMED` | `INVOICE_ENTERED` | Carrier + tracking number submitted to platform | Coupang `CONFIRMED` (§2.9); Naver `CONFIRMED (official channel)` existence, submission endpoint `UNKNOWN` | **Yes** — see §3.4 | Manual until track record (§6) |
| `PO_CONFIRMED` | `CANCEL_REQUESTED` | Cancellation requested after PO confirmation but before invoice | `UNKNOWN` exact mechanics; assumed possible by analogy to §2.10/§1.10's general cancel surface | No | Manual |
| `CANCEL_REQUESTED` | `CANCEL_APPROVED` | Seller (or platform auto-rule) approves cancel | Coupang `CONFIRMED` per-item response shape (§2.10) | No (until refund executes) | Manual (§6, money movement) |
| `CANCEL_REQUESTED` | `CANCEL_REJECTED` | Seller declines cancel request | `UNKNOWN` | No | Manual |
| `CANCEL_REJECTED` | *(originating state: `ORDER_RECEIVED` or `PO_CONFIRMED`)* | Automatic on rejection | PROPOSAL | No | Auto (pure bookkeeping) |
| `CANCEL_APPROVED` | `CANCELLED` | Refund executes | Coupang `CONFIRMED` (§2.10) | **Yes** | Manual (§6) |
| `INVOICE_ENTERED` | `SHIPPED` | Platform accepts invoice, transitions to dispatch-instructed | Coupang `CONFIRMED` (§2.9); Naver `CONFIRMED (official channel)` state queryable (§1.9) | **Yes** — see §3.4 | Auto once §6 bar is met (this is a platform-confirmed state readback, not a mutating call) |
| `INVOICE_ENTERED` | `INVOICE_REJECTED_DUPLICATE` (error branch, not a numbered state — logged and surfaced, does not advance) | Duplicate invoice number submitted within platform's dedup window | Coupang `CONFIRMED`: 6-month duplicate-invoice-number rejection window (§2.9) | N/A (no state change occurred) | N/A — always requires human investigation before any resubmission |
| `SHIPPED` | `IN_TRANSIT` | Carrier scan event (optional) | `UNKNOWN` for either platform | No | Auto (read-only tracking poll) |
| `IN_TRANSIT` | `DELIVERED` | Carrier/platform reports delivery | `UNKNOWN` exact source this pass | **Yes** | Auto (read-only tracking poll) |
| `SHIPPED` | `DELIVERED` | Direct transition when `IN_TRANSIT` granularity is unavailable | Same as above | **Yes** | Auto |
| `SHIPPED` / `IN_TRANSIT` | `CANCEL_REQUESTED` | Post-dispatch cancellation (e.g., delivery refusal) | `UNKNOWN` platform mechanics for a true post-dispatch "cancel" vs. it actually being modeled as a return | No | **CTO GATE**: do not implement until confirmed whether either platform treats this as cancel or as forced return |
| `DELIVERED` | `FINALIZED` | CS/dispute window elapses with no open claim (§7 retention driver) | PROPOSAL, local only | No (but see §7 — `FINALIZED` is functionally terminal for the state machine) | Auto (pure time-based bookkeeping, never affects money) |
| `DELIVERED` | `RETURN_REQUESTED` | Buyer files return claim | Coupang `CONFIRMED` (§2.10); Naver `CONFIRMED (official channel)` (§1.10) | No | Manual (§6, first-time and always for approval steps) |
| `DELIVERED` | `EXCHANGE_REQUESTED` | Buyer files exchange claim | Naver `CONFIRMED (official channel)` (§1.10); Coupang `UNKNOWN` | No | Manual |
| `RETURN_REQUESTED` | `RETURN_HOLD` | Claim placed on hold pending info | Naver `CONFIRMED (official channel)` (§1.10); Coupang `UNKNOWN` | No | Manual |
| `RETURN_HOLD` | `RETURN_REQUESTED` | Hold released | Naver `CONFIRMED (official channel)` (§1.10) | No | Manual |
| `RETURN_REQUESTED` | `RETURN_APPROVED` | Seller approves claim | Naver `CONFIRMED (official channel)` (§1.10); Coupang `UNKNOWN` distinct step | No | Manual always (§6) |
| `RETURN_REQUESTED` | `RETURN_REJECTED` | Seller rejects claim | Naver `CONFIRMED (official channel)` (§1.10); Coupang `CONFIRMED (existence only)` via withdrawal-history query (§2.10) | No (returns to `DELIVERED` + `dispute_flag`) | Manual always |
| `RETURN_REQUESTED` | `RETURN_WITHDRAWN` | Buyer withdraws before completion | Coupang `CONFIRMED (existence only)`, max 7-day query window (§2.10) | No (returns to `DELIVERED`) | Auto (buyer-initiated, no seller money decision) |
| `RETURN_APPROVED` | `RETURN_PICKUP_COMPLETE` | Item collected from buyer | `UNKNOWN` exact API | No | Auto once §6 bar met (read-only confirmation) |
| `RETURN_PICKUP_COMPLETE` | `RETURN_COMPLETED` | Refund issued after inspection | `UNKNOWN` inspection-step modeling | **Yes** | Manual always (§6, money movement) |
| `EXCHANGE_REQUESTED` | `EXCHANGE_HOLD` | Claim on hold | Naver `CONFIRMED (official channel)` (§1.10); Coupang `UNKNOWN` | No | Manual |
| `EXCHANGE_HOLD` | `EXCHANGE_REQUESTED` | Hold released | Naver `CONFIRMED (official channel)` (§1.10) | No | Manual |
| `EXCHANGE_REQUESTED` | `EXCHANGE_APPROVED` | Seller approves | `UNKNOWN` distinct step for either platform | No | Manual always |
| `EXCHANGE_REQUESTED` | `EXCHANGE_REJECTED` | Seller rejects | Naver `CONFIRMED (official channel)` (§1.10) | No (returns to `DELIVERED` + `dispute_flag`) | Manual always |
| `EXCHANGE_APPROVED` | `EXCHANGE_PICKUP_COMPLETE` | Original item retrieved | Naver `CONFIRMED (official channel)` (§1.10) | No | Auto once §6 bar met |
| `EXCHANGE_PICKUP_COMPLETE` | `EXCHANGE_RESHIPPED` | Replacement item invoice entered + shipped (spawns linked sub-order, §3.1 X5) | Naver `CONFIRMED (official channel)` "exchange re-shipment processing" (§1.10) | **Yes** (a new `INVOICE_ENTERED` event under the same irreversibility rule) | Manual until track record (§6) |
| `EXCHANGE_RESHIPPED` | `EXCHANGE_COMPLETED` | Linked sub-order reaches its own `DELIVERED` | PROPOSAL | **Yes** | Auto (derived from sub-order's own auto-eligible transition) |
| *(any state)* | *(same state, `DISPUTE_ESCALATED` flag set)* | Local expected state conflicts with a fresh platform query, or a rejection is itself contested | PROPOSAL | N/A | **Never auto** — always Manual, always highest-priority review (§6) |

### 3.4 Irreversible Transitions (explicit)

The assignment requires explicitly stating which transitions are irreversible. This design treats
irreversibility as **"no valid backward edge exists in this state machine — a mistake past this
point can only be corrected by moving forward through a cancel/return/exchange branch, never by
silently resetting the order to an earlier forward state."**

1. **`PO_CONFIRMED → INVOICE_ENTERED`**: once an invoice/tracking number is successfully
   submitted and accepted by the platform, this design forbids ever re-deriving or resubmitting a
   "corrected" invoice through the automated adapter for the same order. Coupang's `CONFIRMED`
   6-month duplicate-invoice-number rejection window (§2.9) is platform-side evidence that
   invoice resubmission is not treated as routine by the platform itself. A genuine invoice
   correction (wrong carrier, wrong tracking number typo) must be routed to a **manual, seller-UI
   correction path** — whether such a correction mechanism exists at all is `UNKNOWN`/`CTO GATE`;
   this design does not assume one exists.
2. **`INVOICE_ENTERED → SHIPPED`**: platform-confirmed dispatch-instructed state (Coupang
   `CONFIRMED`, §2.9). No transition returns an order from `SHIPPED` back to `PO_CONFIRMED` or
   `INVOICE_ENTERED`.
3. **`SHIPPED`/`IN_TRANSIT` → `DELIVERED`**: once delivery is platform/carrier-confirmed, the
   only paths forward are `FINALIZED`, `RETURN_*`, or `EXCHANGE_*` — never back to a
   pre-delivery state.
4. **`CANCEL_APPROVED → CANCELLED`**: refund execution. No transition reverses a completed
   refund; a mistaken cancel-refund would require an entirely separate, manually-initiated
   re-order — out of scope for this state machine.
5. **`RETURN_PICKUP_COMPLETE → RETURN_COMPLETED`** and **`EXCHANGE_RESHIPPED →
   EXCHANGE_COMPLETED`**: refund/replacement-fulfillment execution, same irreversibility
   rationale as #4.
6. **`DELIVERED → FINALIZED`**: not reversible by design once the CS/dispute window (§7) has
   genuinely elapsed with no open claim — however, this document proposes that `FINALIZED` must
   never be entered while any `RETURN_*`/`EXCHANGE_*`/`CANCEL_*` branch is open, and any late
   claim discovered after `FINALIZED` triggers `DISPUTE_ESCALATED` (manual) rather than a silent
   reopen, since a late claim past the retention/dispute window is itself a decision requiring
   human/legal judgment, not an automatic state reversal.

All other transitions in §3.3 (holds, rejections, withdrawals) are explicitly **reversible** in
the sense that they return the order to a well-defined prior state (`DELIVERED`, or the
originating pre-cancel state) — they are not irreversible, and the state machine must not treat a
rejection or withdrawal as if it were.

### 3.5 Platform Mapping Summary

| Canonical state | Naver SmartStore mapping | Coupang mapping |
|---|---|---|
| `ORDER_RECEIVED` | Order query result, likely "신규 결제완료" per `CONFIRMED (existence only)` (§1.8) | Order query result, category `CONFIRMED (existence only)` to exist (§2.8) |
| `PO_CONFIRMED` | `UNKNOWN` — `pending_confirmation` | 발주서 upload, `CONFIRMED (existence only)` (§2.9) |
| `INVOICE_ENTERED` | Submission endpoint `UNKNOWN`; confirmation queryable via `lastChangedType` `CONFIRMED (official channel)` (§1.9) | Invoice-upload API, `CONFIRMED` (§2.9) |
| `SHIPPED` | `DISPATCHED`-queryable state, `CONFIRMED (official channel)` (§1.9) | "배송지시" state, `CONFIRMED` (§2.9) |
| `DELIVERED` | `UNKNOWN` — `pending_confirmation` | `UNKNOWN` — `pending_confirmation` |
| `CANCEL_*` | Cancel/return/exchange claim info via order-detail inquiry, `CONFIRMED (official channel)` (§1.10) | Cancel-order API + Return-Cancellation Request List Query, `CONFIRMED` (§2.10) |
| `RETURN_*` | Return approval/hold/hold-release/rejection, `CONFIRMED (official channel)` (§1.10) | Return API section, withdrawal-history queries, `CONFIRMED` (§2.10) |
| `EXCHANGE_*` | Exchange pickup-completion/re-shipment/hold/hold-release/rejection, `CONFIRMED (official channel)` (§1.10) | `UNKNOWN` — no official exchange-specific endpoint found this pass (§2.10) |

---

## 4. Duplicate-Request Prevention: Idempotency Key Scheme

`PROPOSAL`, following the project's own established precedent of deriving stable IDs from content
fields rather than timestamps — the same principle already applied elsewhere in this project (per
the assignment: "you may reference `ContentPerformanceHistory.build_content_id()`'s pattern
conceptually... describe the principle: hash stable identifying fields, never a generation
timestamp"). This document does not read that file; it applies the stated principle fresh to the
order/fulfillment domain.

**Principle**: an idempotency key must be a deterministic hash of fields that describe *what the
action is*, not *when it happened*. Two retries of the same logical action — whether 3 seconds or
3 days apart — must produce the identical key, so a naive retry-after-timeout can never be
mistaken for a new action.

**Scheme** (SHA-256 over a canonical, sorted field list; PROPOSAL field sets per action type):

| Action type | Idempotency key = SHA-256 of (in this order) |
|---|---|
| Order import (`DISCOVERED → ORDER_RECEIVED`) | `platform` + `platform_order_id` (the platform's own stable order identifier — never a local timestamp) |
| PO confirmation (`ORDER_RECEIVED → PO_CONFIRMED`) | `platform` + `platform_order_id` + `"po_confirm"` |
| Invoice entry (`PO_CONFIRMED → INVOICE_ENTERED`) | `platform` + `platform_order_id` + `carrier_code` + `tracking_number` — deliberately includes the tracking number itself (not just the order ID), because Coupang's own confirmed duplicate-detection is keyed on invoice number (§2.9); the local idempotency key must be at least that strict, and this also naturally prevents two different tracking numbers from being silently treated as "the same" retry |
| Cancel action | `platform` + `platform_order_id` + `"cancel"` + `claim_id` (if the platform issues one) |
| Return/exchange action | `platform` + `platform_order_id` + `claim_id` (receipt ID / return ID as returned by the platform's own claim-query API, per Coupang's `CONFIRMED` receipt-ID-keyed query surface, §2.10) + `action_type` (`request`/`approve`/`reject`/`pickup_complete`/`complete`) |

**Enforcement (PROPOSAL)**: before executing any state-mutating call, the adapter must:

1. Compute the idempotency key for the intended action.
2. Check the local `order_audit_log.jsonl` (§5) for a prior entry with the same key and a
   successful outcome. If found, **do not resubmit** — treat the action as already done, and
   surface the prior result.
3. Only if no successful prior entry exists (or the prior entry's outcome was itself ambiguous —
   see §5's timeout handling) does the adapter proceed with the network call, and it must record
   the idempotency key in the same audit-log entry that records the call's outcome.

This is a **local** dedup ledger, deliberately independent of whatever dedup the platform itself
may or may not perform — Coupang's confirmed 6-month duplicate-invoice window (§2.9) is a useful
platform-side backstop, not something this design relies on as the primary defense, since its
window and scope (invoice number specifically) do not cover every action type in this document.

---

## 5. Retry Policy (Asymmetric by Endpoint Class)

`PROPOSAL`, directly informed by `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`'s `CONFIRMED`
finding that Coupang applies **stricter, block-triggering** rate limiting specifically to
product/price/stock-related endpoints since 2023-10-12 (§2.11), distinct from its general
~5-calls/sec/vendorId default. Order/fulfillment endpoints were not found to carry that same
elevated-blocking designation in the confirmed research — this design treats that as a real
asymmetry, not an assumption that one retry policy fits everything, per the assignment's explicit
instruction.

Reused structural template only (not its tuning): `modules/trend_collector/retry_policy.py`'s
existing `RetryPolicy` shape (`CONFIRMED` precedent already cited in
`docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.13).

| Endpoint class | Retry? | Backoff shape | Max attempts | Rationale |
|---|---|---|---|---|
| **Read/query** (order collection §1.8/§2.8, status polling, category/notice metadata lookup §1.7/§2.7, claim/return queries §1.10/§2.10) | Yes, freely | Exponential, base 2s × 2, cap 60s, + jitter | Up to 5 | Idempotent GETs; no state mutation risk; Coupang's confirmed general rate limit (~5 calls/sec/vendorId, §2.11) is the only real constraint, not a blocking-risk endpoint class. |
| **Order/fulfillment state-mutating** (PO confirm, invoice entry, dispatch confirmation) | Yes, but cautiously, and **only after a query-before-retry check** | Exponential, base 5s × 2, cap 120s | 2–3 | These endpoints were not found to carry Coupang's confirmed strict product-API blocking designation (§2.11 scopes that specifically to product create/edit/query and price/stock-change) — so a materially different, still-conservative, profile applies. Before any retry, the adapter must first re-query the order's current platform-reported state; if the state already reflects the intended mutation (e.g., invoice already recorded), treat as success and do not resubmit — this is the primary defense against a duplicate mutation from a timeout of unknown outcome. |
| **Cancel/return/exchange approval actions** (money-adjacent) | Yes, but only after query-before-retry, and **never fully automatically past 1 retry** — a second failure escalates to manual (§6) rather than retrying again | Exponential, base 5s × 2, cap 120s | 1 automatic retry, then manual escalation | These transitions move refund money or commit a replacement shipment; an ambiguous outcome must never be resolved by blind resubmission. |
| **Product/price/stock-related** (out of this document's direct scope — see `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.13 for the primary treatment) | Yes, very conservatively | Exponential, base 10s × 2, cap 300s | 2–3, hard ceiling | Reproduced here only as a cross-reference: Coupang's `CONFIRMED` finding (§2.11) is that repeated excessive calls to these specific endpoints "can result in immediate blocking" — a materially worse consequence than a 429. Never apply the order/fulfillment retry profile above to this class. |
| **Invoice resubmission specifically** | **No automatic retry ever**, per §3.4's irreversibility rule and §2.9's `CONFIRMED` 6-month duplicate window | N/A | 0 automatic; always manual | A duplicate invoice submission is both a platform-rejected action and, per §3.4, an irreversible-forward transition this design refuses to auto-correct. |

**Timeout-with-unknown-outcome handling (PROPOSAL, applies to every mutating call)**: a network
timeout on a state-mutating call must never be treated as "definitely failed, safe to retry." The
adapter must first attempt a read-only status query for the same order/claim; only if that query
confirms the mutation did **not** take effect does a retry (within the limits above) proceed. If
the read-only query itself is inconclusive or also fails, the action is escalated to manual review
(§6) rather than retried blindly.

---

## 6. Manual Approval Checkpoints vs. Automatic-Eligible Transitions

`PROPOSAL`. Two tiers, both gated by the overriding fact that **none of this is authorized to run
against a real account at all** until the Phase 2 CTO approval gates in
`docs/COMMERCE_PHASE_1_CONTRACT.md` §9 and `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §5 are
explicitly satisfied. The tiers below describe the *target* operating model once that top-level
approval exists — they do not themselves constitute that approval.

### 6.1 Always manual, forever (never eligible for automation regardless of track record)

- Any `CANCEL_APPROVED`, `RETURN_COMPLETED`, or `EXCHANGE_RESHIPPED`/`EXCHANGE_COMPLETED`
  transition — these move refund money or commit a replacement shipment.
- Any transition into `DISPUTE_ESCALATED` (state conflict, contested rejection) — always the
  highest-priority manual queue item, never auto-resolved, per §3.3's transition table.
- The first occurrence of **any** claim type (`RETURN_REQUESTED`, `EXCHANGE_REQUESTED`) for a
  given product category or platform, mirroring `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`
  §4's Phase 2C precedent of a human-reviewed single-item track record before any automation.
- Any transition where a fresh platform query (§3.5) disagrees with the locally expected state.
- Any invoice resubmission decision (§3.4, §5) — always manual, always investigated before any
  action.
- Any post-dispatch cancellation request (`SHIPPED`/`IN_TRANSIT → CANCEL_REQUESTED`) — this
  document explicitly marks this a `CTO GATE` pending platform-mechanics confirmation (§3.3), not
  merely "manual for now."
- Any order whose PII record (§7) cannot be fully populated (e.g., recipient address missing) —
  do not auto-advance a fulfillment action against incomplete shipping data.

### 6.2 Manual until a track record is established, then automation-eligible (CTO GATE to enable)

Per `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §4's phased model (2C → 2D → 2E), the following
become automation-**eligible** only after: (a) the overarching Phase 2 CTO approval gate is
satisfied, (b) a minimum observation period of human-approved single-order handling with zero
policy-rejection or duplicate-mutation incidents (duration itself `CTO GATE`, not fixed by this
document), and (c) per-scope explicit sign-off (mirroring Phase 1 §9's "individually allowed"
requirement):

- `ORDER_RECEIVED → PO_CONFIRMED` for standard, non-flagged orders.
- `PO_CONFIRMED → INVOICE_ENTERED` using a pre-approved carrier/template, once the query-before-
  retry idempotency machinery (§4, §5) has itself been exercised without incident.
- Read-only status/tracking polling and `RETURN_WITHDRAWN` bookkeeping (buyer-initiated, no seller
  money decision).
- `DELIVERED → FINALIZED` (pure time-based bookkeeping once the retention window in §7 elapses
  with no open claim — never itself a money-moving action).

### 6.3 Always automatic (no CTO gate needed beyond the base Phase 2 approval, since these are read-only)

- `DISCOVERED → ORDER_RECEIVED` order import.
- Status/tracking read-only polling (`SHIPPED → IN_TRANSIT → DELIVERED` observation).
- CS/return-status synchronization reads (§3.18 of the prior architecture doc) — reconciling
  local state against a fresh platform query is itself read-only and safe to automate; only the
  *action taken* in response to a discovered mismatch (`DISPUTE_ESCALATED`) is manual.

---

## 7. Personal Data (PII) Policy

This system will eventually handle real customer **name, phone number, and shipping address**.
This section is written on that assumption from the start, not as an afterthought, per the
assignment's explicit instruction.

### 7.1 Minimum necessary fields

`PROPOSAL`, minimum-necessity principle:

| Field | Store? | Reasoning |
|---|---|---|
| Recipient name | Yes | Required for delivery and CS. |
| Recipient phone number | Yes | Required for carrier delivery contact and CS. |
| Shipping address (full) | Yes | Required for delivery. |
| Buyer's platform account identifier (order-scoped, not a persistent login credential) | Yes, order-scoped only | Needed to correlate with platform order/claim queries; never store a login credential. |
| Order item summary, price, quantity | Yes | Operational necessity, not itself PII in the strict sense but stored alongside PII. |
| Payment card / bank details | **No, never** | Payment is handled entirely by the platform; this system has no legitimate reason to see or store card/bank data, and must refuse to accept it even if a platform response ever included it. |
| Buyer's platform login credentials, session tokens | **No, never** | Out of scope entirely; this system never logs in as the buyer. |
| Any field not needed for fulfillment, delivery, or CS (demographic data, marketing profile data, etc.) | **No** | Minimum-necessity principle; no field is collected "in case it's useful later." |

### 7.2 Storage location and separation from general `storage/`

`PROPOSAL`, resolving `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.17's open `CTO GATE`
("decide whether order/PII data may live in the same `storage/commerce/` tree at all"): **no** —
PII must **not** live in the same plain-JSON, unencrypted `storage/` tree this project uses for
every other Engine's output today (`CONFIRMED` observation already made in the prior document:
"every other Engine's `storage/<engine>/` output is plain JSON on disk with no encryption layer
in this codebase today").

Proposed conceptual path (not created by this document — no `storage/` write was performed):

```text
storage/commerce/orders/<platform>/<local_order_id>/
  order_state.json              (state machine position, NO PII — order_local_id, platform_order_id,
                                  state, timestamps, item summary, price/qty; safe to treat like
                                  every other Engine's plain JSON)
  order_audit_log.jsonl         (§5/§8 audit trail — references order_local_id and idempotency
                                  keys, NEVER embeds raw PII values, only a pointer to the PII
                                  record below)

storage/commerce/pii/<platform>/<local_order_id>.enc     (PROPOSAL, separately access-controlled)
  — encrypted-at-rest blob containing recipient name/phone/address only
  — NOT covered by this project's existing storage/** blanket-ignore-and-plain-JSON convention
  — access restricted to the fulfillment/CS code path specifically, not general-purpose read
```

This mirrors the separation PIPA (개인정보보호법) itself requires when data must be retained
under another law's mandate rather than destroyed on the general schedule (§7.3): "개인정보처리자가
다른 법령에 따라 개인정보를 파기하지 아니하고 보존하여야 하는 경우에는 해당 개인정보 또는
개인정보파일을 다른 개인정보와 분리하여서 저장·관리하여야 한다" — Personal Information Protection
Act Art. 21(3), `CONFIRMED (official channel, search-synthesis)`: sourced from law.go.kr-linked
aggregation (casenote.kr summary of 개인정보 보호법 제21조), not independently verbatim-fetched
from `law.go.kr` directly in this pass (the direct `law.go.kr` fetch returned only navigation
chrome, not article text — see §7.4 sourcing note). Treat the exact statutory wording as `CTO
GATE`-verify-before-relying-on, but the *existence* of a segregation requirement when retention is
legally mandated is well-established and consistent across sources.

### 7.3 Encryption at rest

`CTO GATE` for the specific mechanism/library — this document proposes a **requirement**, not an
implementation: any file under `storage/commerce/pii/` must be encrypted at rest using an
established authenticated-encryption scheme (e.g., Fernet/AES-GCM), with the encryption key held
**outside** the repository and outside the plain `.env` pattern this project currently uses for a
single LLM API key — `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.4 already flagged that two
marketplace credential pairs plus real order/PII data "materially raises the blast radius of a
credential leak" beyond what `.env` was originally sized for; this document extends that same
concern specifically to the PII encryption key, not just marketplace API credentials. Key
management mechanism (OS keystore, dedicated secret manager, HSM, etc.) is explicitly **not**
decided by this document.

### 7.4 Retention period proposal

`CONFIRMED` (directly fetched, official Korean government legal-information domain
`easylaw.go.kr` — 법제처/Ministry of Government Legislation's plain-language legal guide,
retrieved in this session): under 전자상거래 등에서의 소비자보호에 관한 법률 시행령 제6조
(Enforcement Decree of the Act on Consumer Protection in Electronic Commerce, Art. 6, "사업자가
보존하는 거래기록의 대상 등"), Korean e-commerce transaction-record retention periods are:

| Record type | Retention period | Source |
|---|---|---|
| 표시·광고에 관한 기록 (advertising/display records) | 6 months | `easylaw.go.kr` (CONFIRMED, fetched this session) |
| 계약 또는 청약철회 등에 관한 기록 (contract / cooling-off withdrawal records) | 5 years | same |
| 대금결제 및 재화등의 공급에 관한 기록 (payment and product-supply records — this includes delivery/shipping data) | 5 years | same |
| 소비자의 불만 또는 분쟁처리에 관한 기록 (consumer complaint / dispute-resolution records — covers cancel/exchange/return CS records) | 3 years | same |

This is a directly-fetched official-domain source (not merely search-engine synthesis, unlike
most of `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`'s `CONFIRMED` tags), but it is a government
**plain-language summary** page, not a verbatim fetch of the enforcement decree's own article
text (the direct `law.go.kr` fetch attempted in this session returned only page-navigation chrome,
not the article body — recorded honestly rather than silently upgraded to a stronger claim).

`PROPOSAL` retention default, reasoning from the table above: since this system's PII (recipient
name/address/phone) is generated and consumed **as part of** both the "payment and product-supply"
record category (delivery requires the address) and, when a claim occurs, the "consumer
complaint/dispute-resolution" category, this document proposes the **longer of the two applicable
windows** as the default retention period for order-linked PII:

> **Default: 5 years from order completion (delivery or cancellation, whichever finalizes the
> order), for the full PII record (name/address/phone). At 5 years, purge PII fields specifically
> (name/address/phone) while retaining the non-PII order/transaction metadata (product, price,
> date, state history) indefinitely for analytics, matching the pattern already established by
> this project's other Engines, which never touch PII in the first place.**

This 5-year default is a **safe-side design proposal, not a settled legal conclusion.** It is
explicitly `CTO GATE` for the following unresolved questions, none of which this document is
positioned to answer:

- Whether **this specific software system** (an internal automation tool operated on behalf of a
  seller) is itself the regulated "사업자" (business operator) under 전자상거래법, or whether that
  obligation attaches only to the seller entity using the software — a real legal distinction this
  document cannot resolve.
- Whether a shorter retention period is legally sufficient for records that don't squarely fall
  into the "payment/supply" category (e.g., pure browsing/order-attempt data that never
  completed) — this document's 5-year default is deliberately the *longer* of the two most
  plausibly applicable categories as a conservative default, not a precise per-field legal
  determination.
- Whether PIPA's general "destroy without delay once purpose is achieved" principle (Art. 21(1),
  `CONFIRMED (existence only, search-synthesis)`: "개인정보처리자는 보유기간의 경과, 개인정보의
  처리 목적 달성... 그 개인정보가 불필요하게 되었을 때에는 지체 없이 그 개인정보를 파기해야
  한다") should in fact govern a *shorter* window for some field subset even while the
  전자상거래법 retention mandate governs others — this requires per-field legal classification
  this document does not attempt.

**Deletion/purge policy (PROPOSAL)**: at the 5-year mark (or upon an earlier explicit legal
determination that a shorter window applies), a scheduled purge job (not built by this document)
must: (1) overwrite/delete the PII-bearing fields specifically (name/phone/address) such that they
are not recoverable, per PIPA's confirmed destruction-method requirement ("개인정보를 파기할 때에는
복구 또는 재생되지 아니하도록 조치하여야 한다" — Art. 21(2), `CONFIRMED (existence only,
search-synthesis)`); (2) retain the non-PII order/state-history metadata; (3) log the purge event
itself (order_local_id, purge timestamp, retention basis) in the audit trail (§8) — the purge
event is logged, but never the purged content.

### 7.5 What this section does not decide

This document does not decide, and marks `CTO GATE`: the exact encryption library/key-management
mechanism (§7.3), whether this software is itself a regulated 사업자 (§7.4), the precise legal
retention period per field category (§7.4), and whether any additional consent/notice obligations
under PIPA (개인정보 수집·이용 동의, 제3자 제공 동의 if the platform relationship counts as such)
apply to how this system receives buyer PII from the marketplace platforms in the first place —
that last question was entirely out of this research pass' scope and is flagged here as a gap,
not silently assumed resolved.

---

## 8. Audit Log

`PROPOSAL`, extending the shape already proposed in
`docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.12 for upload adapters to cover every order
state transition and every outbound/inbound API interaction in this document's scope.

### 8.1 Conceptual location

`storage/commerce/orders/<platform>/<local_order_id>/order_audit_log.jsonl` (PROPOSAL path only —
no file was created by this document). Append-only, one JSON object per line, matching the
existing project convention already used for `trend_run_log.jsonl` and `knowledge_history.json`-
style append logs. Never mixed into `storage/commerce/pii/` (§7.2) — the audit log references PII
by `local_order_id` pointer only, never embeds a raw name/phone/address value, so the audit log
itself can remain in the same access tier as every other Engine's plain-JSON output.

### 8.2 State-transition entries

```json
{
  "type": "state_transition",
  "timestamp": "ISO-8601 with timezone",
  "actor": "system | human:<reviewer_id>",
  "platform": "smartstore | coupang",
  "order_local_id": "...",
  "platform_order_id": "...",
  "from_state": "...",
  "to_state": "...",
  "trigger": "e.g. invoice_upload_accepted, buyer_return_request, manual_approval",
  "idempotency_key": "sha256:...",
  "manual_approval": true,
  "reviewer": "human:<reviewer_id> | null",
  "reason": "free text, no PII",
  "dispute_flag": false
}
```

### 8.3 API interaction entries (outbound + inbound)

```json
{
  "type": "api_call",
  "timestamp": "ISO-8601 with timezone",
  "direction": "outbound | inbound",
  "platform": "smartstore | coupang",
  "endpoint_category": "order_query | po_confirm | invoice_upload | dispatch_query | cancel | return_query | return_action | exchange_query | exchange_action | category_metadata",
  "mode": "dry_run",
  "http_status": 200,
  "request_payload_hash": "sha256:...",
  "response_status": "success | error | timeout | ambiguous",
  "response_summary": "safe, non-PII summary only",
  "retry_attempt_number": 0,
  "idempotency_key": "sha256:...",
  "order_local_id": "..."
}
```

**Never logged, under any circumstance**: raw HMAC secret, OAuth token, `client_secret_sign`
value, raw request/response body containing PII, or any credential value — mirroring the
`CONFIRMED` project-wide rule already stated in `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`
§3.12 and `CLAUDE.md`'s `.env` handling rule. `mode` is hardcoded `"dry_run"` for every entry this
document's design would produce today, since no live mode is authorized (§9).

---

## 9. Explicit Non-Authorization Statement

Restating the top-of-document banner, per the assignment's requirement to state this prominently:

**This document is a DRY-RUN / design-only operating contract.** No real SmartStore or Coupang
API call, login, order query, invoice submission, cancellation, exchange, return, or any other
live action was authorized, requested, performed, or simulated against a real system in producing
this document. Every state, transition, retry rule, audit-log shape, approval checkpoint, and PII
policy above is a **PROPOSAL** pending explicit CTO review and pending the approval gates already
defined in `docs/COMMERCE_PHASE_1_CONTRACT.md` §9 and `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`
§5. Implementation of any part of this contract requires a separate, explicitly-scoped Sprint with
its own CTO approval — this document does not grant that approval, and none of its file paths
(`storage/commerce/orders/`, `storage/commerce/pii/`) were created on disk.

---

## 10. Open Gaps Rolled Up (for the next research/implementation pass)

Consolidated from the tags used throughout this document — nothing new, just gathered in one place
for planning:

- `PO_CONFIRMED` exact Naver API mapping — `UNKNOWN`.
- `DELIVERED` exact platform signal for either platform — `UNKNOWN`.
- Post-dispatch cancellation mechanics (cancel vs. forced-return) for either platform — `UNKNOWN`,
  `CTO GATE` before implementing that specific transition.
- Coupang exchange-specific endpoints — `UNKNOWN` (§2.10's own gap, inherited here).
- Return/exchange inspection-step modeling (does either platform expose a distinct
  "inspecting" state before completion?) — `UNKNOWN`.
- Whether this software itself is a regulated 전자상거래법 사업자 — `CTO GATE`, legal review.
- Exact PII encryption mechanism/key management — `CTO GATE`.
- Exact per-field PII retention window (vs. this document's conservative 5-year default) —
  `CTO GATE`, legal review.
- Naver invoice-submission endpoint itself (vs. the confirmed post-hoc query) — `UNKNOWN`.
- Everything already listed as `UNKNOWN`/`CTO GATE` in
  `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §1–§2 remains equally unresolved here; this
  document did not attempt to re-verify those platform-API facts beyond the two new legal-source
  fetches in §7.4.
