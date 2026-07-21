# New Engine / Module Proposals (Design Only — Not Wired to WorkflowEngine)

Status: **DESIGN PROPOSAL ONLY. No code implemented, no `WorkflowEngine` change, no CTO approval
implied.** Every module below would be a standalone, on-demand system — same pattern as
`modules/commerce/`, `modules/compliance/`, `modules/affiliate/`, `modules/brandconnect/`,
`modules/competitor_learning/` — never connected to `src/workflow_engine.py`'s protected pipeline
without a separate, explicit future approval.

## 0. Status check — avoid proposing what already exists

Before proposing anything new, current state (verified by directory listing, not assumed):

| Candidate named in the task prompt | Actual current state |
|---|---|
| Affiliate Engine | **Already implemented** — `modules/affiliate/` (Phase 1: `AffiliateRevenueRouter`, contract/policy-gate/result/safety-utils split, dry-run only, no real link/API). Independent QA NO-GO round already completed. Not proposed again here. |
| Commerce (SmartStore/Coupang content package) | **Already implemented** — `modules/commerce/` (Phase 1: truth-gated copy-package generator) + a Phase 2A dry-run adapter skeleton (`modules/commerce/commerce_engine.py`, `smartstore_adapter.py`, `coupang_adapter.py`) already exists, currently frozen pending Independent QA per `MODULE_STATUS.md`. **Not proposed again** — see Section 3 below for what's genuinely still missing (a distinct "sync" concept, not a copy generator). |
| BrandConnect | **Already implemented** — `modules/brandconnect/` (`brandconnect_contract.py`, `brandconnect_package_builder.py`, `brandconnect_policy_gate.py`), currently frozen alongside Compliance per recent instructions. Not proposed again. |
| Analytics Engine | **Already implemented (v2, local-only)** — `modules/analytics_engine/` computes an honest local `quality_trend`; the real post-publish version is an existing, already-approved `ROADMAP.md` "Requires External API" item, not a new proposal. See Section 2 for what a *design* for that gated future version would look like, without implementing it.

Given the above, this document proposes only genuinely new designs: **Product/Competitive
Intelligence Engine** (Section 1), **Analytics v3 design sketch for the existing gated item**
(Section 2, design-only, does not un-gate it), **SmartStore Sync** and **Coupang Sync** as distinct
concepts from Commerce's copy-package generation (Sections 3-4).

---

## 1. Product / Competitive Intelligence Engine (new)

### Why this, and not another copy of Commerce/Affiliate
`docs/EXTERNAL_ENGINE_PORTFOLIO_STRATEGY.md` (existing CTO-authored strategy doc, already in the
repo) already names this exact gap: a `ProductCandidate`/`ProductSnapshot`/`OfferSnapshot` "Product
Intelligence Plane" that finds/normalizes/verifies/compares product opportunities *before* Commerce's
truth-gated copy generation or Affiliate's routing ever runs. Today, both Commerce and Affiliate
*consume* already-verified facts (a `commerce_request`/`AffiliateProgram`+`MerchantOffer`) but neither
one *discovers or tracks* those facts over time. This engine would sit upstream of both, offline,
read-only from whatever local sources already exist (no new scraping/API).

### Proposed contracts (design only)
```text
ProductCandidate   -- a product/SKU/link the operator is considering (manual entry or import)
ProductSnapshot    -- stable facts (name, brand, category) + evidence/source metadata + captured_at
OfferSnapshot      -- volatile facts (price, stock, discount, rating, review_count, rank) + captured_at + expires_at
SourceHealth        -- per-source freshness/reliability tracking (mirrors modules/trend_collector's
                       existing SourceHealthTracker pattern -- same idiom, new domain)
```

### Module shape (standalone, mirrors `modules/commerce/` file-split convention)
```text
modules/product_intelligence/
  __init__.py
  product_intelligence_contract.py   -- ProductCandidate/ProductSnapshot/OfferSnapshot normalization
  product_intelligence_freshness.py  -- expiry/staleness gates (reuse Commerce's existing freshness
                                         policy shape, don't reinvent it)
  product_intelligence_conflict.py   -- flags contradictory facts across sources for a candidate,
                                         never auto-resolves (mirrors Compliance's "conflicting_sources"
                                         handling philosophy)
  product_intelligence_storage.py    -- storage/product_intelligence/<candidate_id>/
  product_intelligence_module.py     -- orchestrator, no network calls, accepts already-collected
                                         facts only (same "no scraping" boundary as every other
                                         Phase-1 module in this repo)
```

### Explicit non-goals (CTO gates before ever relaxing these)
- No HTML scraping, no product-page fetching, no official API call in Phase 1 — accepts only
  manually-supplied or already-collected snapshots, exactly like Commerce Phase 1 accepts only
  already-verified `commerce_request` facts.
- Does not decide what to publish or route — its only output is a scored/ranked, freshness-gated
  candidate list for a human (or a later-gated Commerce/Affiliate run) to act on.
- Official-API adapters (a real Coupang/Naver/Amazon product-data source) remain a separate, later
  CTO gate — same posture as Commerce §9's Phase 2 gate and Affiliate's Phase 1 contract.

---

## 2. Analytics Engine v3 — real post-publish performance (design sketch for an already-approved future gate)

This item is **already** an approved `ROADMAP.md` "Requires External API" entry — this section is a
design sketch for what that future work would look like, so a future Sprint has a starting shape; it
does **not** request or imply approval to start building it now, and does not touch
`modules/analytics_engine/`'s current v2 code.

### Proposed shape (design only)
```text
modules/analytics_engine/  (existing directory -- a future Sprint would ADD, not replace)
  performance_import_adapter.py  -- NEW: imports real Instagram Graph API metrics (likes/comments/
                                    saves/shares/reach) for an ALREADY-PUBLISHED post, tagged
                                    performance_source="external_verified" (never blended silently
                                    with the existing "internal_quality_proxy" numbers -- the two
                                    must remain distinguishable in the output schema forever, per
                                    the existing DECISIONS.md entry on this exact topic)
```
Hard requirement carried over from the existing Roadmap entry (not new): Meta/Instagram Graph API +
OAuth + a publish-result import step are all CTO gates that remain unopened. This design sketch adds
nothing to that gate list — it only records where the eventual adapter would live and what field it
must never silently merge into.

---

## 3. SmartStore Sync (new — distinct from Commerce's copy-package generator)

### Why this is not a duplicate of `modules/commerce/`
Commerce Phase 1 generates a **manual-upload copy package** (title/description/notice text) from
already-verified facts — it explicitly does not read live listing state. "Sync" is a different
problem: given a listing that may **already exist** on SmartStore (created manually by a human using
Commerce's package), periodically re-check whether the *live* listing's price/stock/status still
matches what was last known, and surface drift — never push a change automatically.

### Proposed contract (design only)
```json
{
  "sync_check_id": "...",
  "platform": "smartstore",
  "listing_reference": "human-recorded listing ID (never auto-discovered)",
  "last_known_state": {"price": null, "stock": null, "status": null, "recorded_at": null},
  "current_observed_state": {"price": null, "stock": null, "status": null, "observed_at": null},
  "drift_detected": false,
  "drift_fields": [],
  "observation_method": "manual_human_recheck | official_api_read_only",
  "requires_human_action": true
}
```

### Module shape
```text
modules/smartstore_sync/
  __init__.py
  smartstore_sync_contract.py   -- the drift-check schema above
  smartstore_sync_comparator.py -- pure diff logic between last_known_state and current_observed_state
  smartstore_sync_storage.py    -- storage/smartstore_sync/<sync_check_id>/
  smartstore_sync_module.py     -- orchestrator; Phase 1 accepts `current_observed_state` as an
                                    already-supplied input only (human-entered or a future read-only
                                    official-API adapter) -- never fetches it itself
```

### Explicit non-goals
- Never writes to SmartStore. Never logs in. Never uses Commerce's or Affiliate's credential
  posture as precedent to skip its own separate CTO gate.
- Phase 1 has no live-read capability at all — it is purely a comparator over two human/adapter-
  supplied snapshots. A read-only official API adapter (to auto-populate
  `current_observed_state`) is an explicit future CTO gate, mirroring
  `docs/AFFILIATE_REVENUE_ROUTER_PHASE_1_CONTRACT.md`'s own Section 9 gate list shape.

---

## 4. Coupang Sync (new — same shape as Section 3, platform-specific differences noted)

Same design as SmartStore Sync (Section 3), with the platform-specific facts already confirmed by
`docs/RESEARCH/AFFILIATE/AFFILIATE_NETWORK_EVIDENCE_MATRIX.md` baked into the comparator's
documentation (not its logic — the comparator itself is platform-agnostic diffing):

- Coupang's confirmed item-level price/stock endpoints are **separate** from the general
  product-modify endpoint once a listing is approved (already documented in
  `modules/commerce/coupang_adapter.py`'s existing comments) — `CoupangSyncComparator` should record
  *which* field changed (price/stock vs. everything else) so a future read-only adapter, if ever
  approved, knows which confirmed endpoint category it would need, without this design committing to
  building that adapter.
- Coupang's confirmed rate-limit policy (aggressive blocking on repeated product-API calls, per the
  evidence matrix) means any future read-only sync-check adapter must be conservative/scheduled, not
  on-demand-per-request — flagged here as a design constraint for whoever eventually proposes the
  live adapter, not something this offline-only Phase 1 design needs to enforce itself.

### Module shape
```text
modules/coupang_sync/
  __init__.py
  coupang_sync_contract.py
  coupang_sync_comparator.py
  coupang_sync_storage.py
  coupang_sync_module.py
```

---

## 5. Common CTO approval gate checklist (applies to every module above before any Phase 2)

Mirrors the gate shape already established and proven in this repo (Commerce §9, Compliance §6,
Affiliate §9) — reusing the *pattern*, not inventing a new approval process:

1. Named workflow owner and measurable ROI for the specific module.
2. Official platform API/policy review (for SmartStore Sync / Coupang Sync's eventual live-read
   adapters only — Product Intelligence Engine has no platform API surface by design).
3. Explicit scope of what's read-only vs. ever-write-capable (default: read-only forever until a
   separate gate opens write capability, and even then never without human approval per submission —
   same posture as Affiliate's `human_approval`/`disclosure_policy_verified` gates).
4. Data freshness SLA and stale-data/conflict handling (reuse Commerce's existing freshness-policy
   shape rather than inventing a new one per module).
5. Storage/credential design review before any credential is ever introduced.
6. Explicit sign-off that `WorkflowEngine` remains untouched unless a future Sprint is separately
   scoped and approved to wire the module in.
