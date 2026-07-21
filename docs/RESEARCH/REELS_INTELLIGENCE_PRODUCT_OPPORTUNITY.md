# Reels Intelligence Product Opportunity

Date: 2026-07-12

Source: <https://reelscode.co.kr/>

Scope: product opportunity analysis for AI-Content-OS. This document does not authorize scraping,
Instagram login automation, video redistribution, code changes, site work, storage writes, or Git
operations.

Legend:

- `CONFIRMED`: observed from the public site or provided by CTO/user.
- `INFERRED`: product or architecture conclusion derived from confirmed facts.
- `UNKNOWN`: not verified; requires official source, owner clarification, or controlled QA.
- `CTO GATE`: requires CTO approval before implementation or data ingestion.

## 1. CTO Executive Decision

Decision:

```text
Build a clean-room Reels Intelligence product layer using AI-Content-OS engines.
Do not copy Reelscode data, code, category heuristics, or analysis text.
Do not use the visible board as training data.
Treat Reelscode as product-pattern evidence only.
```

Why:

- `CONFIRMED`: The public page presents a Reels reference board with categories, visible metrics,
  public creator handles, pattern briefs, and original Instagram references.
- `CONFIRMED`: The site frames usage as reference discovery and says not to copy the content
  directly.
- `CONFIRMED`: The visible categories include beauty, food, fashion, brand, travel, exercise,
  daily life, and humor.
- `CONFIRMED`: The visible board includes pattern types such as result-first food content,
  relatable skits, fandom/issue content, and save-oriented travel references.
- `UNKNOWN`: Whether the data is live, seeded, demo, heuristic-generated, or manually curated.
- `CTO GATE`: No production ingestion until provenance, metric freshness, category accuracy,
  dedupe, deletion/DMCA, and Instagram policy boundaries are solved.

## 2. Public Product Pattern

`CONFIRMED`: Reelscode positions itself as a reference board for creators. The public page exposes
today's viral pattern brief, category filters, visible metric-like values, public Instagram handles,
hashtags, and links to detail pages/original Instagram references.

`CONFIRMED`: CTO-provided facts for the observed service:

- public Instagram reel link and metadata reference board;
- score formula: `likes + comments * 3`;
- categories: beauty, food, fashion, brand, travel, exercise, daily life, humor;
- format summaries: tutorial/demo, fandom/issue, save inducement, visual hook;
- browser saved collection, similar style, original Instagram link;
- the site states it is link/public metadata exploration, not video redistribution.

`INFERRED`: The product value is not "download popular reels." It is a workflow that turns public
references into structured creative direction.

## 3. Data Quality Warning

The visible data must not be used as model training data or as factual benchmark evidence without
verification.

`CONFIRMED / CTO-PROVIDED` warning signals:

- multiple different reels repeat identical views, likes, comments, or score values;
- Ariana Grande and Guess Korea examples appear under generic domestic-travel hashtags;
- UFC-like content can be classified as fashion/OOTD;
- detail pages can show "travel / temporary" style labels;
- detail analysis may stay generic instead of extracting real hook, cut, CTA, or scene structure.

Risk classification:

- `UNKNOWN`: actual data source and refresh method;
- `UNKNOWN`: whether metrics are captured from Instagram, seeded, cached, estimated, or demoed;
- `UNKNOWN`: whether categories are manual, heuristic, AI-generated, or placeholders;
- `HIGH`: using these records directly would pollute AI-Content-OS learning with possibly synthetic
  or mislabeled data;
- `HIGH`: copying examples too closely risks creative plagiarism, rights issues, and brand safety
  problems.

Policy:

```text
Use Reelscode only as market/product-pattern input.
Do not ingest its item data into Knowledge, Brand DNA, Performance, Trend Collector, or training sets.
```

## 4. Existing Engine Reuse Map

| AI-Content-OS engine | Reuse for Reels Intelligence | Required guardrail |
|---|---|---|
| Trend Collector | discover seasonal/social topics that should be monitored as reel cohorts | source health, dedupe, no scraped metrics without policy gate |
| Instagram Research | store authorized/public reference observations and distinguish real metrics from visible proxies | Graph API/OAuth boundary, captured_at, provenance |
| Competitor Learning | compare competitor formats, hooks, creative angles, and posting themes | no copying captions/video; competitor data labeled reference-only |
| Research Intelligence | convert references into evidence-backed briefs and claim-safe insights | source confidence, fact/claim separation |
| Shorts planner/exporter | create original scene plans, captions, shot lists, and edit packages | adaptation, not replication |
| Publishing | prepare manual/draft publish packages and platform metadata | human approval, platform policy |
| Performance | connect published AI-Content-OS outputs to actual account performance | authorized import only; no fake view/save/share claims |

`INFERRED`: The strongest reuse path is `reference -> pattern signature -> adaptation brief ->
Shorts edit package -> publishing checklist -> measured performance feedback`.

## 5. Differentiated Products

### 5.1 Trust-Labeled Reels Reference Board

Value: A board that shows reference items with confidence labels instead of pretending every metric
is equally reliable.

Differentiators:

- provenance badge;
- metric captured time;
- stale metric warning;
- category confidence;
- duplicate cluster;
- rights boundary;
- "do not copy" adaptation reminder.

### 5.2 Industry Pattern Brief

Value: Weekly or daily briefs for beauty, food, fashion, brand, travel, exercise, daily life, humor,
commerce, and local businesses.

Output:

- common hook patterns;
- first three seconds;
- scene/cut rhythm;
- CTA type;
- save/share/comment triggers;
- content risk;
- original concept prompts.

### 5.3 Competitor Account Monitoring

Value: Monitor a user's chosen competitor/reference accounts and detect changes in format strategy.

Required source mode:

- official Graph API for owned accounts where possible;
- manual import for reference competitors;
- public-data collection only after terms and legal review.

### 5.4 Hook / Scene / CTA Structure Extraction

Value: Turn a reel reference into an abstract creative structure.

Examples:

- hook: problem/result/identity/fandom/controversy;
- scene structure: reveal -> proof -> detail -> CTA;
- CTA: save, comment, share, follow, product click, profile visit.

`CTO GATE`: This must extract structure, not copy captions, visuals, music, creator likeness, or
editing sequence too closely.

### 5.5 Reference To Original Concept

Value: Generate original concepts inspired by a pattern while staying brand-safe.

Output:

- original concept title;
- brand angle;
- scene plan;
- asset list;
- caption;
- disclosure, if commercial;
- rejection notes for too-similar concepts.

### 5.6 Shorts Edit Package Export

Value: Export a practical package for editors or AI video tools.

Output:

- `ScenePlan`;
- `TimedCaption`;
- `AssetManifest`;
- `RenderProfile`;
- thumbnail/caption variants;
- manual publishing checklist.

### 5.7 Post-Publish Feedback

Value: Learn from the user's real performance after publishing.

Inputs:

- authorized account metrics;
- manual CSV import;
- per-post URL/receipt;
- cost and production time.

Outputs:

- view/save/share/comment lift;
- cohort comparison;
- creative pattern score;
- next brief recommendations.

## 6. Revenue Models

| Product | Customer | Pricing model | Why it sells | Main risk |
|---|---|---|---|---|
| Creator subscription | solo creators, small brands | monthly subscription with saved boards and briefs | lowers idea discovery time | public-data policy, low willingness to pay |
| Agency/team dashboard | agencies, social teams | per-seat SaaS plus workspace limits | repeatable client research and production handoff | permissions, account separation, support load |
| Brand competitor monitoring | brands, franchise marketers | monthly monitoring package or report retainer | strategic value beyond content ideas | evidence quality, legal review |
| Per-report brief | SMBs, consultants | one-off industry brief | easy low-friction sale | manual ops cost |
| Managed production | brands, local businesses | per-video/package service | highest revenue per customer | production capacity, rights, approvals |
| Commerce affiliate/product reels | affiliate creators, commerce teams | revenue share, content credits, package fee | connects trend demand to monetization | disclosure, product claims, stale offers |

`INFERRED`: Start with briefs and edit packages before building a live monitoring SaaS. They reuse
more of AI-Content-OS and require less risky data automation.

## 7. Minimum New Contracts

### ReelReference

Purpose: a public or authorized reel reference record.

Minimum fields:

- `reference_id`
- `source_platform`
- `original_url`
- `creator_handle`
- `caption_excerpt_hash`
- `category`
- `category_confidence`
- `captured_at`
- `provenance`
- `rights_boundary`
- `metric_snapshot_id`
- `dedupe_cluster_id`

### MetricSnapshot

Purpose: metrics captured at a specific time, never treated as timeless truth.

Minimum fields:

- `metric_snapshot_id`
- `views`
- `likes`
- `comments`
- `shares`
- `saves`
- `score`
- `score_formula`
- `captured_at`
- `source_method`
- `freshness_status`
- `confidence`

### PatternSignature

Purpose: abstract creative structure extracted from one or more references.

Minimum fields:

- `pattern_id`
- `pattern_name`
- `hook_type`
- `scene_structure`
- `cta_type`
- `format_family`
- `category`
- `evidence_reference_ids`
- `confidence`
- `do_not_copy_notes`

### RightsBoundary

Purpose: define what can and cannot be reused.

Minimum fields:

- `can_link`
- `can_quote_excerpt`
- `can_use_thumbnail`
- `can_download_video`
- `can_republish`
- `allowed_use`
- `restricted_use`
- `dmca_status`
- `reviewed_at`

Default:

```json
{
  "can_link": true,
  "can_quote_excerpt": false,
  "can_use_thumbnail": false,
  "can_download_video": false,
  "can_republish": false,
  "allowed_use": "reference_only"
}
```

### AdaptationBrief

Purpose: turn a reference pattern into an original concept.

Minimum fields:

- `brief_id`
- `source_pattern_id`
- `brand_context`
- `target_audience`
- `original_angle`
- `scene_plan`
- `caption_direction`
- `cta`
- `similarity_risk`
- `approval_status`

### BenchmarkCohort

Purpose: compare references or published outputs by industry, format, or goal.

Minimum fields:

- `cohort_id`
- `industry`
- `format_family`
- `time_window`
- `reference_ids`
- `inclusion_rules`
- `exclusion_rules`
- `known_biases`

### PerformanceLink

Purpose: connect a produced AI-Content-OS asset to real post performance.

Minimum fields:

- `content_id`
- `publish_receipt_id`
- `platform_post_url`
- `metric_snapshot_ids`
- `cost_ledger_id`
- `revenue_ledger_id`
- `captured_at`
- `source_authorized`

## 8. Data Collection Policy

Default allowed:

- user-supplied URLs;
- manual CSV import;
- public links as reference pointers;
- metadata stored with provenance and captured time;
- authorized account performance import after OAuth/API approval.

Default blocked:

- Instagram login automation;
- scraping beyond a reviewed public-data boundary;
- downloading or redistributing reel videos;
- treating public visible metrics as verified performance without captured_at/provenance;
- storing copied captions, comments, faces, music, or thumbnails without rights review;
- using Reelscode records as training data;
- auto-posting without human approval.

Required controls:

- official Graph API boundary review;
- scraping and terms gate for any public collection;
- `captured_at` for every metric;
- provenance and source method;
- dedupe cluster;
- bot/outlier flags;
- sample bias notes;
- deletion/DMCA process;
- PII and comment-scrubbing rule;
- account-owner consent for private or owned-account metrics.

## 9. Build Vs Buy

Decision:

```text
Buy/copy: NO.
Clean-room build: YES.
Use product pattern: YES.
Use Reelscode data as learning data: NO.
```

Rationale:

- `CONFIRMED`: The public site proves demand for a Reels reference board and pattern brief.
- `UNKNOWN`: No data license, API access, backend method, or data provenance is verified.
- `HIGH`: Observed/CTO-provided quality warnings mean direct ingestion would damage model quality.
- `INFERRED`: AI-Content-OS can exceed the reference product by connecting pattern discovery to
  original production packages and real post-publish feedback.

## 10. 30 / 60 / 90 Day MVP

### 30 Days: Networkless Brief Product

Build:

- manual `ReelReference` import template;
- `PatternSignature` and `AdaptationBrief` schemas;
- industry brief generator using user-provided references;
- Shorts edit package export as files/checklist, not platform upload;
- confidence labels and rights boundaries.

Validation KPI:

- reference save rate;
- brief acceptance rate;
- brief-to-production conversion;
- user-reported time saved;
- rejection rate for too-generic briefs.

Stop criteria:

- briefs remain generic;
- adaptation is too close to originals;
- users will not provide references manually;
- rights boundary cannot be explained simply.

### 60 Days: Controlled Monitoring And Production Handoff

Build:

- competitor/reference account watchlist as manual or approved source;
- dedupe and category-confidence QA;
- scene/CTA extraction QA workflow;
- editor-facing Shorts package export;
- publishing checklist integration.

Validation KPI:

- publish rate from generated briefs;
- editor revision reduction;
- category accuracy after human review;
- customer repeat use.

Stop criteria:

- data collection policy blocks monitoring;
- no measurable improvement in production throughput;
- category errors remain high.

### 90 Days: Performance Feedback Loop

Build:

- authorized PerformanceLink import;
- view/save/share/comment lift analysis;
- cohort benchmarking;
- pattern recommendation based on real owned outputs;
- commerce affiliate/product reels package after disclosure gate.

Validation KPI:

- view lift;
- save/share lift;
- paid conversion;
- content package gross margin;
- repeat subscription retention.

Stop criteria:

- Graph API or manual import cannot provide reliable metrics;
- performance claims become unverifiable;
- policy overhead exceeds revenue.

## 11. Site Work Separation

This document is not a site-building task.

Do not modify:

- active M7/M8 code;
- Instagram Research implementation;
- Shorts implementation;
- Publishing implementation;
- Commerce implementation;
- CardNews implementation;
- `site/`;
- `storage/`;
- Git state.

Recommended next lanes, all non-overlapping and approval-gated:

1. `docs/REELS_REFERENCE_CONTRACTS.md`: contract-only lane for `ReelReference`,
   `MetricSnapshot`, `PatternSignature`, `RightsBoundary`, `AdaptationBrief`, `BenchmarkCohort`,
   and `PerformanceLink`.
2. `docs/INSTAGRAM_DATA_POLICY_GATE.md`: policy-only lane for Graph API, public-data limits,
   DMCA/deletion, provenance, and metric freshness.
3. `docs/SHORTS_ADAPTATION_BRIEF_SPEC.md`: Shorts package handoff lane, no `modules/shorts/**`
   edits.
4. `docs/PERFORMANCE_FEEDBACK_LOOP_SPEC.md`: measured feedback design, no Performance code edits.

## 12. CTO Gate

CTO approval required before:

- any Reelscode data ingestion;
- any Instagram scraping;
- any login/OAuth/API connection;
- any automated metric import;
- any stored captions/comments/media;
- any Shorts implementation work;
- any Publishing or live posting integration;
- any claim that visible metrics represent verified performance.

Recommended CTO decision:

```text
Approve clean-room Reels Intelligence planning.
Reject data ingestion from Reelscode.
Start with networkless industry briefs and adaptation packages.
Move to official/authorized metrics only after policy and source gates.
```

