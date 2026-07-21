# REBORN AI Automation Playbook Technical Reuse Audit

Audit date: 2026-07-14

Source: `C:/Users/가산 솔리드옴므/Downloads/AI-automation-playbook-v2.pdf`
Status: **RESEARCH ONLY - no prompt/code copying, install, account, API, automation, outreach, publishing, or purchase authorized**

## CTO Decision

**BENCHMARK the operating pattern; do not copy or integrate the PDF as code.**

The useful material is a compact sequence - prioritize one repetitive task, define an explicit input/output contract, keep a human gate, measure real results, then iterate. AI-Content-OS already implements most of the content-side safety architecture more rigorously. The PDF provides no source repository, package, workflow export, n8n/Make JSON, command, API schema, credential contract, test, or license grant. It therefore contains **zero directly reusable code/configuration**.

The fastest project benefit is to use its gaps as a checklist for future revenue experiments:

- distinguish content generation from real publishing and real performance;
- treat ad angles as hypotheses, never predicted winners;
- add actual affiliate/brand/ad receipts only through approved imports;
- calculate ROI from measured labor and recurring costs, not the PDF's illustrative assumptions;
- retain the project's existing fail-closed affiliate, brand, commerce, rights, and human-approval gates.

## PDF Forensics and Review Coverage

The file was inspected before interpreting its content:

| Check | Result |
|---|---|
| Page count | 12 |
| Page size | 1230 x 1740 points on every page |
| Embedded text | **None**; `0` extracted characters on all 12 pages |
| Page objects | One raster image per page |
| Attachments | None |
| Outline/bookmarks | None |
| Link/form annotations | None |
| Embedded JavaScript | None |
| PDF metadata | Creation and modification date `2026-06-28 14:51:07Z`; no author/title/license metadata |

All 12 pages were rendered and visually inspected. A temporary visual transcription was made because the PDF has no text layer. PDF page numbers below mean the PDF's 1-based page position, which matches the printed `01/12` through `12/12` footer.

## Technical Asset Inventory

### Directly reusable assets

**None found.**

- Source code: none.
- Shell/Python/JavaScript commands: none.
- n8n/Make workflow JSON or node configuration: none.
- Prompt schema file or machine-readable JSON Schema: none.
- API endpoint, request/response schema, webhook contract, OAuth scope, retry policy, or rate limit: none.
- Test fixture, evaluation dataset, benchmark receipt, or reproducible execution log: none.
- Public repository, package version, commit, checksum, or dependency lock: none.
- License or permission to copy the six prompt templates: none.

The document names products and presents text prompts, but product names and screenshots are not integration artifacts.

### Tools named by the PDF

PDF page 3 names Claude, ChatGPT, Perplexity, GPT image, Midjourney, Higgsfield, Runway, Veo, ElevenLabs, n8n, Make, Claude Code, and Cursor. PDF page 7 describes n8n/Make calling an LLM, image model, ElevenLabs, and a generic platform API in sequence.

What the PDF does **not** establish:

- which exact model or version is used;
- whether access is UI, API, CLI, SDK, or browser automation;
- commercial rights for prompts, outputs, voices, images, music, faces, or video;
- current pricing, quotas, latency, geography, or content policy;
- n8n/Make node names, credentials, expressions, error paths, or export format;
- official publishing APIs or channel eligibility;
- data retention, deletion, encryption, secret storage, or subprocess security;
- maintenance and license terms for any dependency.

The monthly prices on PDF page 3 are uncited, volatile marketing guidance. They must not enter a cost model until revalidated from each vendor's current official terms.

## Page-by-Page Technical Findings

| PDF page | Verifiable content | Reuse classification | CTO finding |
|---:|---|---|---|
| 1 | Claims a system covering prioritization, prompts, content factory, sales funnel, and ROI | Marketing overview | No implementation evidence |
| 2 | `frequency x time x regularity` prioritization heuristic; one-at-a-time automation | `CLEAN-ROOM-PATTERN` | Useful backlog rubric, but frequency encoding and regularity weights are arbitrary and unvalidated |
| 3 | Vendor stack and illustrative monthly prices | `BUY/BENCHMARK` | Tool list only; no API/config/license evidence and considerable duplication with current capabilities |
| 4 | Role/context/task/format/constraints, few-shot examples, self-review, JSON output, “reason first” | `CLEAN-ROOM-PATTERN` | Contract-first output is useful; generic self-scoring is not independent QA; do not request or persist hidden chain-of-thought |
| 5 | Content calendar, sales email, and data-analysis prompt text | Unlicensed prompt text | Do not copy. The data prompt's “do not invent numbers” rule agrees with project data honesty, but project contracts are stronger |
| 6 | FAQ bot, rewrite, and ad-angle prompt text | Unlicensed prompt text | Do not copy. “Most likely highest CTR” is unsupported without experiment data |
| 7 | Five-stage content flow and generic tool chain | `CLEAN-ROOM-PATTERN` | Structurally resembles the existing pipeline; its unattended publish/learning claims omit required API, rights, QA, and attribution contracts |
| 8 | Target discovery, personalized outreach, landing page, lead alerts, follow-up | High-risk clean-room pattern | No scraping source, consent/legal basis, sending provider, bounce handling, suppression list, or platform-policy evidence |
| 9 | Time-saving and break-even formulas with an illustrative content example | `CLEAN-ROOM-PATTERN` | Formula is usable only with measured inputs; example excludes review, rework, recurring API, failure, and maintenance costs |
| 10 | Nine failure modes: hallucination, cost, style, human boundary, PII, stale loop, over-scope, approval, tool sprawl | `BENCHMARK` | Mostly aligned with project policy; still lacks executable controls and tests |
| 11 | Four-week roadmap: select, prompt, connect, measure, iterate | `BENCHMARK` | Reasonable experiment cadence, not an implementation plan for this repository |
| 12 | REBORN AX service offer and claims of automated content/outreach/CS/dashboard | Marketing CTA | No customer evidence, execution receipt, SLA, terms, security, price, or rights proof |

## Direct Reuse vs. Clean-Room vs. Prohibited

### Direct reuse

**None.** The absence of a license is decisive even for the six “copy/paste” prompts on PDF pages 5-6. They may be analyzed as ideas but not copied into project prompts or skills.

### Clean-room patterns worth retaining

The following contracts can be independently designed from project requirements, without copying the PDF wording:

```text
AutomationCandidate
  id, owner, task_frequency, measured_minutes_per_run,
  determinism_evidence, failure_cost, external_dependencies,
  required_approvals, baseline_receipt, decision
```

```text
RevenueExperimentReceipt
  experiment_id, channel, content_id, offer_or_campaign_id,
  hypothesis, variant_id, exposure_start, exposure_end,
  cost_observed, clicks_observed, conversions_observed,
  commission_or_revenue_observed, refunds_or_reversals,
  measurement_source, imported_at, is_measured
```

```text
AutomationROIReceipt
  baseline_minutes_observed, automated_minutes_observed,
  review_minutes_observed, runs_observed, labor_rate_basis,
  build_cost_observed, recurring_cost_observed,
  failure_and_rework_cost_observed, revenue_delta_observed,
  payback_period_observed, assumptions, confidence
```

Unknown fields must remain null/unknown. Estimated commission, internal quality score, claimed CTR, and vendor testimonials must never be stored as measured revenue.

### Prohibited or rejected reuse

- Copying the page 5-6 prompt text without a license.
- Treating the PDF's tool prices or ROI example as current project evidence.
- Sending scraped bulk emails/DMs, buying lead lists, automating account sessions, or bypassing platform restrictions.
- Auto-publishing content without rights, evidence, disclosure, QA, and human approval receipts.
- Feeding customer PII, contracts, credentials, settlement data, or unpublished campaign terms to an external model without explicit data approval.
- Claiming an ad variant will have the highest CTR before a real controlled experiment.
- Treating an LLM's self-score as independent QA or storing chain-of-thought.
- Building a second orchestration system beside `WorkflowEngine` because the PDF mentions n8n/Make.

## Mapping to Current AI-Content-OS

### Content factory

PDF page 7's `source -> script -> production -> publish -> learn` sequence is not new code for this project.

| PDF concept | Existing project capability | Actual gap |
|---|---|---|
| Source collection | trend/research modules | External source health and approved live data |
| Script/content generation | `modules/ai_planner/`, `modules/content/` | No need for another prompt framework |
| Image/card production | image modules and `modules/card_news/` | Shorts rendering/TTS remain separately gated |
| Publishing | `modules/publishing/` manual package | Actual platform upload is intentionally not implemented |
| Learning | knowledge/learning/analytics modules | Current signals are internal quality proxies, not real reach/click/revenue |

The PDF understates evidence, asset rights, fallback, metadata provenance, and publish attestations. Its “person only approves” claim on page 7 cannot replace the project's numerous preconditions.

### Coupang Partners and other affiliate revenue

Potential use: generate content/angle hypotheses around a **previously verified** merchant offer.

Required project boundary:

```text
verified MerchantOffer + channel policy + disclosure evidence
  -> content variant candidate
  -> human review
  -> official tracking-link request/attachment
  -> observed click/conversion/settlement import
```

`modules/affiliate/` already requires exact program/offer joins, enrollment evidence, freshness, disclosure verification, and human approval. PDF pages 5-7 supply none of those facts. They cannot generate a real Coupang link, price, stock state, commission rate, or settlement record.

Decision: **BENCHMARK content experiment structure; reject direct automation.**

### Naver Shopping Connect / BrandConnect

PDF page 5's personalized proposal idea and page 8's lead funnel could inform a human-reviewed brand proposal package. `modules/brandconnect/` already separates creator campaigns, shopping-connect products, disclosure, compensation, affiliate commission, manual link attachment, rights, policy evidence, and approval receipts.

Missing from the PDF:

- Naver campaign/product eligibility and owner-scoped link proof;
- official campaign brief import;
- creator/seller/product identity joins;
- compensation vs affiliate commission separation;
- disclosure, prohibited claims, asset rights, deadline, and receipt evidence;
- allowed outreach channel and consent/suppression handling.

Decision: **CLEAN-ROOM proposal-assistance pattern only.** No automated discovery, DM, application, link generation, or publishing.

### Google/Meta advertising revenue and paid acquisition

PDF page 6 proposes five copy angles and then asks the model to name the likely CTR winner. The first part is useful ideation; the second is not measurement.

A safe future boundary is:

```text
CreativeHypothesis[]
  -> platform-approved human launch
  -> actual spend/impression/click/conversion import
  -> ExperimentReceipt with attribution window
  -> decision with guardrails
```

No ad account API, campaign schema, conversion tag, attribution rule, budget cap, consent signal, or brand-safety contract appears in the PDF. Google Ads acquisition and Google AdSense publisher revenue are also different systems; the playbook does not establish an AdSense workflow.

Decision: **BENCHMARK ad-variant generation; REJECT predicted performance and unattended spend/publishing.**

### Brand sales and outbound

PDF page 8 correctly notes personalization, bounce rate, opt-out, and the risk of purchased lists, but it still provides no lawful-basis, jurisdiction, suppression, sender-reputation, domain-authentication, consent, audit, or deletion design.

The project may later build a human-approved `BrandLeadCandidate` and `OutreachReceipt` only from an explicitly authorized source. No scraping, sending, or follow-up service is justified by this PDF.

### Commerce

`modules/commerce/` has explicit approval, dry-run, credential, audit, and rollback boundaries. The PDF contains no product schema, marketplace adapter, credential design, listing validation, rollback, price/stock evidence, or order handling. It offers no commerce code to reuse.

Decision: **NO FIT as an implementation source.**

## ROI Correction

PDF page 9 states:

```text
monthly saving = time per run x hourly rate x monthly runs
payback months = build cost / monthly saving
```

This is a valid first-order arithmetic identity, not an ROI proof. A project decision must use:

```text
net monthly benefit =
  measured baseline labor cost
  - measured automated-operation and review labor cost
  - recurring model/API/orchestrator/tool cost
  - measured failure, rework, and support cost
  + measured incremental contribution margin

payback = total observed implementation cost / net monthly benefit
```

The PDF's `1.5 hours x KRW 20,000 x 20 runs = KRW 600,000/month` and `KRW 1.2M / KRW 600,000 = two months` are explicitly labeled assumptions on PDF page 9. They are not project observations. The implied “earning KRW 600,000 every month” ignores retained human review and operating cost.

## Build / Buy / Benchmark Verdict

| Candidate | Verdict | Reason |
|---|---|---|
| Copy PDF prompts into project | **REJECT** | No license; project already has stronger prompt/output contracts |
| Add n8n/Make now | **REJECT/DEFER** | No exported workflow or demonstrated gap; risks a second orchestrator |
| One-task prioritization rubric | **BENCHMARK** | Low-cost planning aid, but weights must come from observed receipts |
| Generic content factory | **REJECT as new build** | Existing protected pipeline already covers it more safely |
| Revenue experiment/ROI receipts | **BUILD later, clean-room** | Needed for honest affiliate/brand/ad decisions once real data imports are approved |
| Personalized brand proposal assistant | **BUILD narrowly later** | Can reuse current BrandConnect contracts; sending remains human/manual |
| Bulk outbound/DM automation | **REJECT** | Legal, platform, consent, reputation, and account risk |
| Vendor tools in page 3 | **BUY selectively after gate** | Revalidate official API, price, rights, security, and fallback per concrete need |
| REBORN AX managed service | **BUY only after due diligence** | PDF is a sales document; no SLA, DPA, security, price, references, ownership, or portability evidence |

## Smallest Reversible Pilot

No new automation tool is needed. A useful pilot can be run with current project outputs:

1. Select one existing manual operation with at least five timestamped baseline runs.
2. Record actual input, operator time, review time, errors, retries, and outcome.
3. Apply one existing project contract or small clean-room helper, not a new orchestrator.
4. Keep all external publishing, affiliate link attachment, outreach, and ad spend manual.
5. Run five comparable executions.
6. Compare measured net time, defect/rework rate, operating cost, and any real revenue receipt.
7. Stop if quality, policy compliance, or net benefit does not improve.

For a revenue-specific pilot, choose only one path:

- one verified affiliate offer and one approved content variant;
- one owner-provided BrandConnect campaign brief and one proposal package; or
- one manually launched ad creative experiment with a fixed budget and imported actual metrics.

Do not combine all three in one pilot.

## Approval Gates

Before any implementation derived from this playbook:

1. CTO names one measured bottleneck, owner, revenue path, and stop condition.
2. Existing module/skill duplication is checked first.
3. Exact vendor/API/version/pricing/license/output rights and data-processing terms are verified from primary sources.
4. Credentials, secrets, PII, campaign terms, and settlement data remain excluded until explicit data approval.
5. External services sit behind project-owned adapters with timeout, retry, cost ceiling, cache where appropriate, fallback, and diagnostic receipts.
6. Affiliate/brand/commerce/ad facts require source timestamp, eligibility, rights, disclosure, and human approval.
7. Publishing, outreach, account actions, link generation, and spend remain manual until separately approved.
8. ROI uses measured baseline and full recurring/review/failure cost.
9. Native QA remains authoritative; LLM self-scoring is only a draft aid.
10. No derived work modifies the protected `WorkflowEngine` or threatens `workflow_completed`.

## Implementation Status

Research documentation only. No prompt, package, account, API, n8n/Make workflow, outreach list, automation, publishing action, or code was imported or executed. No runtime module was changed.
