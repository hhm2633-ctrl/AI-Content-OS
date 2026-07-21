# Content Automation Harness Architecture

Status: PROPOSED architecture research. No code implemented.

Date: 2026-07-12

Owner intent: apply the content-factory harness concepts confirmed by the CTO from the temporary
`saju-casebook.pdf` review without copying the PDF into this repository.

Legend:

- `CONFIRMED`: observed in current AI-Content-OS repository files.
- `PROPOSED`: architecture proposal for future Sprints.
- `CONFIRMED / CTO-PROVIDED`: provided by CTO/user as verified external observation for this
  architecture update.
- `UNKNOWN`: not verified; requires official source, platform policy review, or controlled QA.

## 1. Decision

`PROPOSED`: Build a common Content Automation Harness as an additive orchestration layer around
CardNews, Shorts, and Commerce. Do not replace `WorkflowEngine` first. Do not wire external tools
such as Higgsfield, Genspark, platform upload APIs, browser automation, or vendor renderers in this
architecture Sprint.

`PROPOSED`: The smallest safe target is a deterministic, file-backed harness that produces and
resumes packages from explicit contracts:

```text
CONTRACT -> spec.json -> deterministic stage runner -> status.json -> ledger -> package output
```

`PROPOSED`: AI may propose content, mappings, prompts, or decisions, but deterministic code must
execute file writes, stage transitions, retries, approvals, scheduling, idempotency, and rollback.

## 2. Repository Reality

`CONFIRMED`: `SYSTEM_ARCHITECTURE.md` defines modular design, JSON module communication, retry,
fallback, human review, logging, and future platform expansion.

`CONFIRMED`: `WORKFLOW_SPEC.md` defines WorkflowEngine responsibilities: workflow selection, module
calling, execution order, state management, error handling, logs, result saving, retry, fallback,
human review, and abort.

`CONFIRMED`: `src/workflow_engine.py` currently runs a fixed sequential workflow:

```text
Trend -> Topic -> AI Planner hint -> Pattern -> Research -> Content -> Image Strategy
-> Image Prompt -> Image Generation -> CardNews -> Publishing -> Knowledge
-> Trend Memory -> Performance Score -> Audit -> Learning -> Analytics
-> Brand DNA -> Competitor -> workflow_completed
```

`CONFIRMED`: `WorkflowEngine` preserves `workflow_completed` when the main path succeeds and uses
safe wrappers for several later engines. Pattern, Knowledge, Performance Score, Audit, Learning,
Analytics, Brand DNA, Trend Memory, and Competitor have fallback-style safety paths at the
WorkflowEngine level.

`CONFIRMED`: `src/main.py` runs `WorkflowEngine(config)` and updates snapshot/changelog only after
`workflow_completed`.

`CONFIRMED`: CardNews is already wired into `WorkflowEngine`, produces card-news output, and has
fallback/quality metadata. Active governance marks CardNews manifest work as GO and closed.

`CONFIRMED`: Shorts Phase 1 is offline/manual-planning oriented and is not part of the main
WorkflowEngine path. Active governance marks Shorts Phase 1 as GO and implementation ownership
closed.

`CONFIRMED`: Commerce Phase 1 is standalone/manual-only, and Commerce Phase 2A code is explicitly
not wired into `src/workflow_engine.py`. `modules/commerce/commerce_engine.py` states that its
dry-run pipeline makes no real API calls and remains standalone. Current governance says Commerce
Phase 1 awaits Independent QA revalidation, while Claude Phase 2 architecture is NO-GO.

## 3. Harness Concepts From CTO-Confirmed Source

`PROPOSED`: Apply these source concepts as design principles:

- `CONTRACT` is the single truth for each product/output line.
- `spec.json` relays stage outputs forward; stages do not inspect hidden state.
- `status.json` allows safe resume after interruption.
- `fails[].route` declares stage-level backtracking instead of ad hoc exception handling.
- Retry ceilings are explicit per route and per stage.
- Human approval gates are first-class state transitions.
- A ledger plus `period + composition` idempotency prevents duplicate work.
- Scheduler catch-up is deterministic and bounded.
- AI judgment and deterministic execution are forcibly separated.

`CONFIRMED / CTO-PROVIDED`: Builderlog contributes a practical operations checklist for a public
content-factory style product: queue depletion, cross-output dedupe, failure alert, draft default,
frequency, fact guard, rollback, and language/channel parity.

`UNKNOWN`: Builderlog's Threads public-data collection method, metric accuracy, and platform-terms
position are not verified here. A 49-sample analyzer is not enough to support market conclusions or
performance claims.

## 4. Non-Goals

`PROPOSED`: The harness must not:

- replace or rewrite `src/workflow_engine.py` in its first Sprint;
- change the `py -m src.main` execution contract;
- break `workflow_completed`;
- add real platform upload, browser automation, or vendor-side rendering;
- introduce hidden LLM decisions inside deterministic stage runners;
- treat Commerce Phase 2 uploads as approved;
- write to `site/` or deployment artifacts;
- copy temporary PDF source material into the repository.

## 5. Core Objects

### 5.1 CONTRACT

`PROPOSED`: A `CONTRACT` is the durable, human-readable and machine-checkable truth source for one
automation line. It defines what may be generated, which facts are allowed, which approvals are
required, and which outputs are blocked.

Minimal schema:

```json
{
  "contract_id": "cardnews:2026-07-12:topic-slug",
  "contract_version": "content_harness_contract.v1",
  "line": "card_news | shorts | commerce",
  "owner": "operator-or-cto",
  "created_at": "2026-07-12T00:00:00+09:00",
  "source_refs": [
    {
      "source_id": "research_result_001",
      "source_type": "workflow_result | merchant_input | evidence_manifest",
      "locator": "storage/workflow_results/04_research_result.json",
      "rights_or_permission": "internal_runtime | merchant_confirmed | unknown",
      "verified_at": "2026-07-12T00:00:00+09:00"
    }
  ],
  "allowed_outputs": ["spec", "dry_run_payload", "manual_package"],
  "blocked_outputs": ["real_upload", "browser_automation"],
  "human_approval_required": true,
  "approval_policy": {
    "approval_scope": "render | publish | upload | commerce_dry_run",
    "expires_after_seconds": 86400,
    "required_roles": ["CTO"]
  },
  "operations_policy": {
    "queue_empty_action": "skip | reuse_last_safe | generate_placeholder | alert_only",
    "idempotency_scope": "period_line_contract_composition_channel",
    "draft_by_default": true,
    "cadence_policy": "daily_max_1 | weekly_max_3 | campaign_defined",
    "numeric_claim_gate": "require_source | require_freshness | block_unknown",
    "channel_parity_required": true
  },
  "facts_policy": {
    "allow_unverified_claims": false,
    "volatile_fields_require_expiry": true,
    "claim_risk_gate": {
      "numeric_claims": "require_source_and_freshness",
      "financial_claims": "require_policy_review",
      "experience_claims": "require_user_confirmation",
      "performance_claims": "require_authorized_metric_source"
    }
  },
  "revenue_policy": {
    "affiliate_route": "domestic | cpa | global | none",
    "revenue_ledger_required": false,
    "performance_ledger_required": false
  }
}
```

### 5.2 spec.json

`PROPOSED`: `spec.json` is the stage relay file. Each stage reads a bounded subset, writes only its
own section, and never mutates previous approved sections.

Minimal schema:

```json
{
  "spec_version": "content_harness_spec.v1",
  "contract_id": "cardnews:2026-07-12:topic-slug",
  "idempotency_key": "2026-W29:card_news:topic_hash:composition_hash",
  "line": "card_news",
  "stage_order": ["ingest", "plan", "generate", "validate", "package", "approve"],
  "stages": {
    "ingest": {
      "status": "completed",
      "input_refs": [],
      "output_refs": [],
      "ai_decision_ref": null,
      "deterministic_result_ref": "storage/harness/.../ingest_result.json"
    }
  },
  "current_stage": "plan",
  "outputs": {
    "package_dir": "storage/harness/card_news/2026-W29/topic_hash"
  }
}
```

### 5.3 status.json

`PROPOSED`: `status.json` is the resume and operation-state file. It is small, append-safe in
spirit, and reconstructable from the ledger if corrupted.

Minimal schema:

```json
{
  "status_version": "content_harness_status.v1",
  "contract_id": "cardnews:2026-07-12:topic-slug",
  "idempotency_key": "2026-W29:card_news:topic_hash:composition_hash",
  "overall_status": "pending | running | waiting_approval | completed | failed | rolled_back",
  "current_stage": "validate",
  "stage_status": {
    "ingest": "completed",
    "plan": "completed",
    "generate": "completed",
    "validate": "running"
  },
  "retry_counts": {
    "validate": 1
  },
  "fails": [
    {
      "failed_at": "2026-07-12T00:00:00+09:00",
      "stage": "validate",
      "code": "missing_source_ref",
      "message": "A claim has no source reference.",
      "route": "backtrack_to_plan",
      "retry_after_seconds": 0,
      "max_retries": 2
    }
  ],
  "approval": {
    "required": true,
    "status": "not_requested | pending | approved | rejected | expired",
    "approval_hash": null,
    "approved_by": null,
    "approved_at": null,
    "expires_at": null
  },
  "operations": {
    "queue_empty_action": "alert_only",
    "idempotency_scope": "period_line_contract_composition_channel",
    "alert_receipt": null,
    "draft_by_default": true,
    "cadence_policy": "campaign_defined",
    "numeric_claim_gate": "require_source",
    "claim_risk_gate": "not_checked | passed | manual_review | blocked",
    "rollback_receipt": null,
    "channel_parity_status": "not_checked | aligned | drift_detected | blocked"
  },
  "commercial": {
    "affiliate_route": "none",
    "revenue_ledger_status": "not_required | pending | recorded | blocked",
    "performance_ledger_status": "not_required | pending | recorded | blocked"
  },
  "resume_safe": true
}
```

### 5.4 ledger.jsonl

`PROPOSED`: The ledger is append-only operational evidence. It records transitions, hashes, writes,
approval checks, retry decisions, rollback steps, and scheduler catch-up decisions. It must not
store secrets or full PII.

Minimal JSON line:

```json
{
  "event_at": "2026-07-12T00:00:00+09:00",
  "event_type": "stage_completed",
  "contract_id": "cardnews:2026-07-12:topic-slug",
  "idempotency_key": "2026-W29:card_news:topic_hash:composition_hash",
  "stage": "generate",
  "input_hash": "sha256:...",
  "output_hash": "sha256:...",
  "result_ref": "storage/harness/.../generate_result.json",
  "actor": "deterministic_runner"
}
```

## 6. State Transition Model

`PROPOSED`: Standard stage states:

```text
pending -> running -> completed
                  -> failed_retryable -> running
                  -> failed_backtrack -> previous_stage.running
                  -> waiting_approval -> approved -> completed
                  -> waiting_approval -> rejected -> failed
                  -> rollback_required -> rolled_back
```

`PROPOSED`: Workflow result states:

- `completed`: all required stages completed and approvals satisfied.
- `partial`: package exists, but optional or manual work remains.
- `waiting_approval`: deterministic output is ready but blocked by human gate.
- `blocked`: required source, rights, or policy condition is missing.
- `rolled_back`: side effects were reversed or package was invalidated.
- `failed`: retry/backtrack limits were exhausted.

`PROPOSED`: `workflow_completed` in the current main WorkflowEngine must remain separate from
harness result status. Harness failures should produce blocked/manual-review packages, not crash
the main workflow.

## 7. Retry Route And Backtracking

`PROPOSED`: Each failure declares a route. The runner must not invent routes dynamically.

Route examples:

| route | Meaning | Max default |
|---|---|---|
| `retry_same_stage` | rerun same deterministic stage with same input | 2 |
| `backtrack_to_plan` | invalidate generated output and return to plan | 1 |
| `backtrack_to_ingest` | source/fact issue requires new input mapping | 1 |
| `manual_review` | stop automation, wait for operator | 0 |
| `block_contract` | no safe automated path | 0 |
| `rollback_outputs` | invalidate or remove package artifacts | 1 |

`PROPOSED`: Retry counters are keyed by `stage + route + input_hash`, so a new human-approved input
can receive a fresh retry budget while repeated deterministic failure cannot loop forever.

## 8. Idempotency

`PROPOSED`: Idempotency key format:

```text
{period}:{line}:{contract_hash}:{composition_hash}:{target_variant}
```

Example:

```text
2026-W29:card_news:8a17c4b2:4slide_resource_tip:v1
```

Definitions:

- `period`: schedule window, such as `2026-W29`, `2026-07-12`, or campaign cycle.
- `line`: `card_news`, `shorts`, or `commerce`.
- `contract_hash`: stable hash of the approved CONTRACT minus runtime-only fields.
- `composition_hash`: stable hash of stage order, template, channel, and output format.
- `target_variant`: optional A/B or platform variant.

`PROPOSED`: If the same key exists as `completed`, scheduler catch-up must not regenerate it. If it
exists as `waiting_approval`, catch-up may notify but not rebuild. If it exists as `failed` and the
failure route allows retry, catch-up can resume within retry limits.

## 9. Human Approval Gate

`CONFIRMED`: Commerce already contains an approval gate concept that fails closed and reads
approval state from config; Commerce dry-run code states that it does not make real API calls.

`PROPOSED`: Generalize approval for all content lines with hash-bound approvals:

```json
{
  "approval_version": "content_harness_approval.v1",
  "contract_id": "commerce:2026-07-12:sku-001",
  "idempotency_key": "2026-W29:commerce:contract_hash:smartstore_payload:v1",
  "approval_scope": "publish | render | commerce_dry_run | upload",
  "artifact_hash": "sha256:...",
  "approved_by": "CTO",
  "approved_at": "2026-07-12T00:00:00+09:00",
  "expires_at": "2026-07-13T00:00:00+09:00",
  "decision": "approved",
  "notes": "Approved for dry-run payload only; no real upload."
}
```

`PROPOSED`: Approval is valid only when all of these match:

- same `contract_id`;
- same `idempotency_key`;
- same `approval_scope`;
- same `artifact_hash`;
- current time is before `expires_at`;
- approval role satisfies the CONTRACT policy.

`PROPOSED`: Any artifact change invalidates approval automatically.

## 10. Rollback And Invalidation

`PROPOSED`: Early harness Sprints should avoid irreversible side effects. Rollback therefore means:

- mark output package as invalidated;
- write a ledger event;
- prevent scheduler from treating the package as usable;
- keep artifacts for audit unless the file contains secrets or policy-disallowed data.

`PROPOSED`: If future platform actions are ever approved, rollback must be platform-specific and
pre-approved before the action is enabled. No action may be introduced unless its rollback or
stop-sales/invalidation path is documented.

## 11. Scheduler Catch-Up

`PROPOSED`: Scheduler catch-up should be deterministic:

1. Enumerate missed `period` windows.
2. Build expected idempotency keys from approved CONTRACTS.
3. Skip completed keys.
4. Resume `running` or `waiting_approval` keys only when `resume_safe=true`.
5. Retry failed keys only if route and retry ceiling allow it.
6. Create at most `N` catch-up runs per line per invocation.
7. Record every skip/resume/retry in the ledger.

`PROPOSED`: Catch-up must prefer under-production over duplicate publication.

## 12. AI Judgment vs Deterministic Execution

`CONFIRMED`: Current WorkflowEngine includes an AI Planner hint layer that does not replace module
selection logic and falls back to `None` when unavailable.

`PROPOSED`: Harness should enforce this boundary:

| AI may do | Deterministic runner must do |
|---|---|
| propose hooks, scripts, slide copy, payload field suggestions | validate schema and required fields |
| propose failure diagnosis | choose route only from configured route table |
| suggest template or composition | compute idempotency key |
| summarize evidence | verify source refs are present |
| propose retry/backtrack plan | enforce max retry ceilings |
| draft approval note | verify artifact hash and expiry |

`PROPOSED`: AI output must always be stored as `ai_decision_ref`, then normalized by deterministic
code into `deterministic_result_ref`.

## 13. Builderlog Operations Checklist Mapping

`PROPOSED`: Convert Builderlog's 8-question operations checklist into explicit harness fields and
state transitions. These fields make operational safety visible instead of burying it in prompts or
operator memory.

| Builderlog checklist | Harness field | State transition / enforcement |
|---|---|---|
| Queue depletion | `queue_empty_action` | If queue is empty, transition to `skipped`, `waiting_input`, or `alerted`; never fabricate a topic/product. |
| Cross-output dedupe | `idempotency_scope` | Before generating, compute key across period, line, contract, composition, and channel; if existing, transition to `duplicate_skipped`. |
| Failure alert | `alert_receipt` | On blocked/retry-exhausted status, write an alert receipt and transition to `attention_required`. |
| Draft default | `draft_by_default` | Channel stages default to `draft_ready`; live states require separate approval and capability gate. |
| Frequency | `cadence_policy` | Scheduler checks cadence before run creation; excess runs transition to `cadence_skipped`. |
| Fact guard | `numeric_claim_gate` | Numeric/volatile claims without source/freshness transition to `blocked_fact_guard`. |
| Rollback | `rollback_receipt` | Any invalidation or reversal writes a receipt before `rolled_back` is accepted. |
| Language/channel parity | `channel_parity_status` | Multilingual or multi-channel packages must pass parity check or transition to `parity_blocked`. |

Minimal fields:

```json
{
  "queue_empty_action": "skip | reuse_last_safe | generate_placeholder | alert_only",
  "idempotency_scope": "period_line_contract_composition_channel",
  "alert_receipt": {
    "alerted_at": "2026-07-12T00:00:00+09:00",
    "reason": "queue_empty | retry_exhausted | fact_guard_blocked | parity_blocked",
    "recipient_role": "operator | CTO | QA",
    "receipt_hash": "sha256:..."
  },
  "draft_by_default": true,
  "cadence_policy": {
    "window": "day | week | campaign",
    "max_outputs": 1,
    "catch_up_allowed": false
  },
  "numeric_claim_gate": {
    "mode": "require_source_and_freshness",
    "volatile_fields": ["price", "discount", "stock", "views", "likes", "comments", "score"],
    "unknown_action": "block_claim"
  },
  "rollback_receipt": {
    "rolled_back_at": null,
    "scope": "package | draft | channel_task",
    "reason": null,
    "receipt_hash": null
  },
  "channel_parity_status": "not_checked | aligned | drift_detected | blocked"
}
```

Operational state extensions:

```text
pending -> queue_empty -> alerted | skipped | waiting_input
pending -> duplicate_detected -> duplicate_skipped
running -> fact_guard_failed -> blocked_fact_guard
running -> cadence_limit_hit -> cadence_skipped
draft_ready -> approval_required -> approved_for_live | rejected
running -> parity_drift_detected -> parity_blocked
rollback_required -> rollback_receipt_written -> rolled_back
failed_retryable -> retry_exhausted -> alert_receipt_written -> attention_required
```

Line-specific application:

- CardNews: dedupe by topic, source package, slide composition, and target channel.
- Shorts: dedupe by topic, scene plan, aspect ratio, language, and channel.
- Commerce/Affiliate: dedupe by product, offer snapshot, disclosure, channel, and period.
- Bilingual/RSS/Threads GTM outputs: require `channel_parity_status=aligned` before publishing or
  marking as ready.

Data warning:

`UNKNOWN`: Public Threads metrics, repost/share weights, and small sample analyzer outputs must not
drive deterministic scheduling or market conclusions until source method, terms, and accuracy are
verified. If imported later, they must enter as `MetricSnapshot`-style evidence with
`captured_at`, provenance, sample size, and confidence.

## 14. Commercial And Claim Gates

`PROPOSED`: Add commercial-risk gates before any affiliate, sponsored, seller, or performance
output can be marked ready. These gates are deterministic status transitions, not prompt wording.

### 14.1 Affiliate Revenue Router

`PROPOSED`: Revenue routing must be explicit because domestic affiliate, CPA, and global affiliate
programs have different disclosure, payout, currency, reporting, and reversal rules.

Minimal state:

```json
{
  "affiliate_revenue_router": {
    "route": "domestic | cpa | global | none",
    "program_name": "coupang_partners | shopping_connect | amazon | cpa_network | unknown",
    "disclosure_required": true,
    "disclosure_status": "missing | drafted | approved | not_required",
    "payout_model": "sale_commission | cpa | flat | unknown",
    "currency": "KRW | USD | mixed | unknown",
    "reporting_source": "manual | official_api | partner_dashboard | unknown",
    "policy_status": "unknown | reviewed | blocked"
  }
}
```

State transitions:

```text
affiliate_route_unknown -> manual_review
disclosure_missing -> blocked_disclosure
policy_status_unknown -> blocked_policy
reporting_source_unknown -> revenue_forecast_disabled
route_ready -> package_ready
```

### 14.2 ClaimRiskGate

`PROPOSED`: Numeric, financial, experience, and performance claims need a stricter gate than generic
fact checking.

| Claim type | Examples | Required proof | Failure state |
|---|---|---|---|
| Numeric | price, discount, stock, views, likes, score | source, captured_at, freshness window | `blocked_numeric_claim` |
| Financial | revenue, income, ROI, payout, savings | policy-reviewed evidence and caveat | `blocked_financial_claim` |
| Experience | "I used it", "real review", "hands-on" | user direct-use confirmation | `blocked_experience_claim` |
| Performance | views lift, conversion, sales, ranking | authorized metric or user-provided report | `blocked_performance_claim` |

Minimal state:

```json
{
  "claim_risk_gate": {
    "status": "not_checked | passed | manual_review | blocked",
    "blocked_claims": [],
    "manual_claims": [],
    "evidence_refs": [],
    "reviewed_at": "2026-07-12T00:00:00+09:00"
  }
}
```

### 14.3 Campaign Compliance Checklist

`PROPOSED`: DAF-style sponsored condition checking should enter the harness as a networkless
campaign checklist first.

Minimal state:

```json
{
  "campaign_checklist": {
    "campaign_id": "campaign-or-brief-hash",
    "required_keywords": [],
    "required_keyword_count": null,
    "required_images": null,
    "required_video": false,
    "required_map_or_place": false,
    "required_disclosure": true,
    "required_links": [],
    "status": "not_checked | pass | fail | manual_review",
    "missing_items": [],
    "manual_review_items": [],
    "publish_gate": "blocked | draft_allowed | publish_allowed_after_approval"
  }
}
```

State transitions:

```text
checklist_not_checked -> campaign_check_running
campaign_check_running -> campaign_pass -> draft_ready
campaign_check_running -> campaign_fail -> blocked_campaign_requirements
campaign_check_running -> campaign_manual_review -> waiting_approval
campaign_pass + human_approval -> publish_allowed_after_approval
```

### 14.4 Revenue And Performance Ledgers

`PROPOSED`: Revenue and performance evidence are separate but linked. A content package can be
approved without revenue data, but it must not claim revenue or performance until an appropriate
ledger event exists.

Minimal ledger refs:

```json
{
  "commercial_ledgers": {
    "revenue_ledger_ref": null,
    "performance_ledger_ref": null,
    "cost_ledger_ref": null,
    "attribution_window": "unknown | 7d | 14d | 30d | custom",
    "ledger_status": "not_required | pending | recorded | blocked"
  }
}
```

State transitions:

```text
package_ready -> published_or_manual_receipt
published_or_manual_receipt -> performance_pending
performance_pending -> performance_recorded
performance_recorded -> revenue_pending
revenue_pending -> revenue_recorded | revenue_reversed | revenue_unknown
```

## 15. Reels Staged Harness

`PROPOSED`: Reels intelligence should not jump from public reference to generated video. It should
move through explicit stages so rights, metrics, and originality are checked.

Stages:

```text
reference_intake -> provenance_check -> metric_snapshot_check -> pattern_signature
-> adaptation_brief -> scene_plan -> shorts_package -> approval -> performance_link
```

Required gates:

- `reference_intake`: source URL and rights boundary captured.
- `provenance_check`: source method and terms status known or blocked.
- `metric_snapshot_check`: metrics marked `authorized`, `manual`, `public_unknown`, or `unusable`.
- `pattern_signature`: extracts abstract hook/scene/CTA, not copied caption or edit sequence.
- `adaptation_brief`: similarity risk reviewed.
- `shorts_package`: assets and captions have rights status.
- `approval`: human approval required before publish-ready status.
- `performance_link`: authorized or user-provided metrics only.

`UNKNOWN`: Public Reels/Threads collection accuracy and terms remain unverified. Unknown metrics can
support ideation labels only, never performance claims or automated ranking.

## 16. CodeGraph Dev-Tool Isolation

`PROPOSED`: CodeGraph-style tooling may be useful only as a developer POC to map modules,
contracts, and dependencies. It must stay outside content runtime and customer workspaces.

Rules:

- read-only repository inspection;
- no secrets, storage payloads, customer data, or generated media;
- no WorkflowEngine dependency;
- no production package output;
- no automatic refactor;
- output is an `InspectionReport`, not a business artifact.

CTO gate:

```text
Approve only as isolated developer tooling after active QA lanes close.
```

## 17. Application By Content Line

### 17.1 CardNews

`CONFIRMED`: CardNews is in the main WorkflowEngine path and already has quality/fallback metadata.

`PROPOSED`: CardNews is the best first harness pilot because it has high ROI for the active
CardNews-first objective and can remain offline/file-based.

Initial stages:

```text
ingest_research -> plan_4_cards -> generate_copy -> validate_evidence
-> render_or_reference_assets -> package_manifest -> approval_gate
```

CTO gate:

- Do not regenerate production images automatically in the harness pilot.
- Approval required before any output is marked publish-ready.

### 17.2 Shorts

`CONFIRMED`: Shorts Phase 1 is GO and offline/manual. It includes manual asset/audio/render/upload
checklists and does not add rendering or upload side effects.

`PROPOSED`: Shorts harness should package plans, scripts, scene specs, captions, asset validation,
and manual editing checklist. It should not introduce TTS, music, video rendering, or upload until
separate CTO gates exist.

Initial stages:

```text
ingest_content -> plan_script -> plan_scenes -> validate_assets
-> package_editing_files -> manual_approval
```

Reels extension:

```text
reference_intake -> pattern_signature -> adaptation_brief -> scene_plan
-> shorts_package -> approval -> performance_link
```

### 17.3 Commerce

`CONFIRMED`: Commerce Phase 1 is manual-only and Commerce Phase 2A dry-run code is standalone, not
wired into WorkflowEngine. Commerce Phase 1 awaits Independent QA; Phase 2 architecture is NO-GO.

`PROPOSED`: Commerce should adopt the harness last among these three lines. It has the highest
policy, factuality, price/stock, credential, and platform-risk surface.

Initial safe stages after QA clears:

```text
ingest_product_facts -> validate_sources -> build_manual_package
-> build_dry_run_payload -> approval_gate -> package_only
```

Hard CTO gates:

- No real upload.
- No browser automation.
- No credential use.
- No product scraping.
- No price/stock/review/ranking claims without freshness and source proof.

### 17.4 Sponsored Campaign Compliance

`PROPOSED`: First implementation target should be networkless and file/report based.

Initial stages:

```text
ingest_campaign_brief -> normalize_requirements -> validate_draft
-> pass_fail_manual_report -> approval_gate -> manual_handoff
```

Hard CTO gates:

- No legal certainty claims.
- No live publish.
- No platform login.
- No sponsored/affiliate claim without disclosure status.
- No use of user photos without rights/privacy confirmation.

## 18. Storage Layout

`PROPOSED`: Use a new isolated harness storage tree:

```text
storage/harness/
  contracts/
    <contract_id>.json
  runs/
    <line>/
      <period>/
        <idempotency_key>/
          CONTRACT.json
          spec.json
          status.json
          ledger.jsonl
          approvals/
            approval_<timestamp>.json
          outputs/
          snapshots/
```

`PROPOSED`: No secrets are stored in harness files. External credential status can be referenced
only as secret-free metadata.

## 19. Minimal Interfaces

`PROPOSED`: A future `ContentHarnessRunner` should expose:

```python
class ContentHarnessRunner:
    def plan(contract: dict) -> dict: ...
    def resume(contract_id: str, idempotency_key: str) -> dict: ...
    def run_stage(contract_id: str, stage: str) -> dict: ...
    def request_approval(contract_id: str, scope: str) -> dict: ...
    def apply_approval(approval: dict) -> dict: ...
    def catch_up(period: str, line: str) -> dict: ...
```

`PROPOSED`: Each line adapter should implement:

```python
class HarnessLineAdapter:
    line = "card_news"
    def build_initial_spec(contract: dict) -> dict: ...
    def run_stage(spec: dict, stage: str) -> dict: ...
    def validate_stage_output(spec: dict, stage: str, output: dict) -> dict: ...
    def rollback(spec: dict, reason: str) -> dict: ...
```

## 20. Risks

| Risk | Severity | Mitigation |
|---|---:|---|
| Harness accidentally becomes a second WorkflowEngine | High | Keep standalone first; integrate by reading existing outputs only |
| AI decisions mutate state directly | High | Store AI output separately; deterministic runner owns writes |
| Duplicate generation or duplicate upload | High | `period + composition` idempotency and ledger checks |
| Approval applied to changed artifact | High | approval hash and expiry required |
| Retry loops increase cost or damage outputs | Medium | route table and retry ceilings |
| Commerce policy violations | Critical | Commerce last; no real upload/browser automation/credentials |
| Scheduler catch-up floods output | Medium | bounded catch-up limit and skip completed keys |
| Storage corruption blocks resume | Medium | status reconstructable from ledger; snapshots |
| Public social metrics are treated as truth | High | metric provenance, sample-size warning, official/authorized source gate |
| Prompt library becomes production policy | Medium | prompts remain suggestions; contracts and deterministic checks enforce gates |
| Affiliate routes are blended | High | explicit domestic/CPA/global route and disclosure gates |
| Financial claims imply guaranteed revenue | High | ClaimRiskGate blocks ROI/income/payout claims without reviewed evidence |
| Campaign checker sounds like legal advice | High | status is operational pass/fail/manual; legal certainty claims blocked |
| Developer tooling leaks runtime data | Medium | CodeGraph POC is read-only and excludes storage/secrets/customer data |

## 21. CTO Gates

`PROPOSED`: Required gates before implementation:

1. Approve this architecture as an additive harness, not a WorkflowEngine rewrite.
2. Approve storage path and schema naming.
3. Approve CardNews as the first pilot line.
4. Confirm no external vendor integration in Harness v1.
5. Confirm approval hash/expiry policy.
6. Confirm that Commerce harness work waits for Independent QA on Phase 1 and separate CTO approval
   on Phase 2.
7. Confirm Builderlog-style checklist fields before any public build-in-public cadence automation.
8. Confirm public Threads/social metric collection method and terms before using analyzer data.
9. Confirm Affiliate Revenue Router fields before affiliate monetization work.
10. Confirm ClaimRiskGate policy before financial/performance claims.
11. Confirm campaign compliance checklist language before any sponsored-content checker MVP.
12. Confirm CodeGraph POC remains isolated developer tooling.

`PROPOSED`: Required gates before any future external execution:

- official vendor/platform policy review;
- credential storage decision;
- dry-run evidence;
- rollback path;
- human approval UI or signed local approval file;
- audit log review;
- explicit per-capability enablement.

## 22. Sprint Plan

### Sprint H0 - Architecture Acceptance

`PROPOSED`: Keep this document as the source design. No code.

Exit:

- CTO accepts or revises scope.
- CardNews pilot remains the recommended first line.

### Sprint H1 - Harness Schemas And File Utilities

`PROPOSED`: Add schema validators and safe read/write utilities only. No WorkflowEngine wiring.
Include the operations checklist fields: `queue_empty_action`, `idempotency_scope`,
`alert_receipt`, `draft_by_default`, `cadence_policy`, `numeric_claim_gate`, `rollback_receipt`,
and `channel_parity_status`.

Exit:

- CONTRACT/spec/status/ledger fixtures validate.
- Corrupt status recovers from ledger or fails closed.

### Sprint H2 - CardNews Offline Harness Pilot

`PROPOSED`: Read existing WorkflowEngine outputs and create a CardNews harness package. Do not
regenerate images by default.

Exit:

- package created from existing `storage/workflow_results`;
- approval gate can block/approve by artifact hash;
- no change to `py -m src.main`.

### Sprint H3 - Scheduler Catch-Up Dry Run

`PROPOSED`: Simulate catch-up from fixture contracts. No real publishing.

Exit:

- completed keys skipped;
- failed keys obey route/retry budget;
- waiting approvals are not rebuilt.

### Sprint H4 - Shorts Package Adapter

`PROPOSED`: Add Shorts offline package adapter using existing Phase 1 outputs.

Exit:

- manual editing package has status/spec/ledger;
- no TTS/render/upload integration.

### Sprint H5 - Commerce Harness Preflight

`PROPOSED`: Only after Commerce QA clears, wrap manual package/dry-run payload generation with
CONTRACT/spec/status/approval. No real upload.

Exit:

- Commerce facts remain truth-gated;
- approval records are hash-bound;
- Phase 2 real actions remain blocked.

## 23. Conflict Check

`CONFIRMED`: This document does not require changing existing `WorkflowEngine` now.

`CONFIRMED`: The proposed first implementation can be standalone and can read existing outputs,
which preserves `py -m src.main` and `workflow_completed`.

`CONFIRMED`: Active governance says site is excluded, CardNews/Shorts implementation ownership is
closed, Research is still active, Commerce awaits QA, and Claude Phase 2 architecture is NO-GO.

`PROPOSED`: Therefore Harness v1 should start as a new, separate architecture/Sprint lane. It
should not edit Research active files, Commerce active files, shared status docs, `site/`, or
WorkflowEngine until a CTO gate explicitly opens that lane.

## 24. Summary

`PROPOSED`: The common harness is worth pursuing because it converts content automation from
fragile sequential scripts into resumable, auditable, idempotent production runs. The first safe
pilot is CardNews offline packaging. Shorts follows because it is already manual/offline. Commerce
comes last because it has the highest policy and platform-risk surface.

`PROPOSED`: The architectural line is simple: AI can recommend; deterministic harness code decides
state transitions, writes files, enforces retry/approval/idempotency, and records the ledger.
