# AI-Content-OS — Project Operating System

This document is the top-level operating reference for AI-Content-OS. It governs how ChatGPT
(CTO), Claude, Codex, and the human project owner all work in this repository, and how the
other project documents fit together. Nothing below removes or overrides prior entries in
`DECISIONS.md`.

## Mandatory Reading Order

Always read these documents before any implementation. Never start implementation before
reading them.

1. PROJECT_OPERATING_SYSTEM.md
2. CTO_BRAIN.md
3. PROJECT_MASTER.md
4. PROJECT_SNAPSHOT.md
5. MODULE_STATUS.md
6. ROADMAP.md
7. CURRENT_TASK.md
8. .claude/skills/*

Repository state has higher priority than memory.

If documentation conflicts with the repository, analyze the repository first.

Always check available MCPs before starting.

Always verify Codex MCP availability.

Never implement features requiring unavailable APIs.

Always maximize Repository growth and ROI.

## System Identity

- **Product**: Instagram card-news automation first (the ★★★★★ priority per
  `CURRENT_TASK.md`), engineered so the same pipeline later extends to Shorts, Blog,
  SmartStore, and Coupang.
- **Architecture style**: a single linear pipeline (`src/workflow_engine.py::WorkflowEngine`)
  calling `modules/<engine>/` stages in a fixed order, each stage returning a result dict that
  `WorkflowEngine` persists to `storage/workflow_results/`. The exact current stage list
  changes as Sprints add stages — confirm it in `PROJECT_SNAPSHOT.md`/`.claude/skills/architecture.md`
  rather than assuming.
- **Reliability contract (fallback-first)**: `workflow_completed` must never regress. Every
  stage that touches something unreliable (network, LLM, image API, file I/O) degrades to a
  safe default and records the degradation as data (`fallback_used`, `reason`, quality/QA
  fields) — it never raises an exception that reaches `WorkflowEngine.run()`'s outer handler.

## AI Roles

| AI | Role |
|---|---|
| ChatGPT | CTO — architecture, documentation, research analysis, Sprint decomposition |
| Claude | Large implementation, broad refactors, new Engine construction |
| Codex | Repository operations, compile/test, git diff review, focused fixes, documentation sync |

Full detail: `DECISIONS.md` ("AI 사용 정책"), `.ai/rules/ai_roles.md`, `docs/AI_PLANNER.md`.

## Protected Core vs. Intelligence Layer

The `WorkflowEngine` pipeline has two tiers, governed by different rules:

- **Protected core** (never reorder, rename, or remove without explicit instruction):
  `TrendCollectorModule -> TopicEngineModule -> PatternEngineModule -> ResearchModule ->
  ContentModule -> ImageStrategyModule -> ImagePromptModule -> ImageGenerationModule ->
  CardNewsModule -> PublishingModule`.
- **Intelligence Layer** (additive bonus stages after `PublishingModule`, introduced from
  Sprint 11 onward): Knowledge, Trend Memory, Performance Score, Audit, Learning, Analytics,
  Brand DNA, and Competitor Engines. These may be reordered among themselves when a real data
  dependency requires it, but the protected core above may not be touched.

Every Intelligence Layer Engine follows the same internal shape: **Core, Storage, History,
Score, Fallback, Interface**, plus Retry/Cache where the Engine actually talks to something
unreliable. "One module" is not "Engine Completed" — see `.claude/skills/large_implementation.md`.

## Offline-First Principle

No Instagram API, Meta Graph API, access-token-based auth, or real SNS login/crawling may be
implemented without explicit future approval — check `ROADMAP.md`'s "Requires External API"
section before building anything that looks like it needs one. When real data isn't available,
an Engine must either (1) compute something real from data that already exists locally, or
(2) record the gap honestly (`fallback_used`, a clear `reason`, a manual checklist) and move the
blocked work to `ROADMAP.md`. Fabricating data that impersonates a real external signal is never
acceptable, even labeled as a placeholder.

## Documentation Map

| Document | Answers |
|---|---|
| `PROJECT_MASTER.md` | What is this project, at a glance? |
| `PROJECT_SNAPSHOT.md` | What did the last real run actually produce? |
| `MODULE_STATUS.md` | What has been built, Sprint by Sprint, and what's next? |
| `ROADMAP.md` | What's planned, and what's explicitly out of scope right now? |
| `DECISIONS.md` | Why was this decided, and when? (append-only, never delete) |
| `AGENTS.md` | What are Codex's/the project's execution rules? |
| `CURRENT_TASK.md` | What is being worked on right now? |
| `CTO_BRAIN.md` | What is ChatGPT's own operating context? |
| `.claude/skills/*.md` | How should Claude approach this *kind* of work? |
| `.codex/skills/*` | The equivalent operating rules for Codex |
| `docs/`, `docs/RESEARCH/` | Analyzed external-material conclusions (Claude reads, never re-analyzes raw sources) |

## Absolute Rules (never break, regardless of Sprint instructions)

- Keep `src/workflow_engine.py`'s protected core pipeline order and structure intact.
- `workflow_completed` must never regress to `workflow_failed`.
- Execute with `py -m src.main`; never `python -m src.main`.
- Do not delete working modules/folders/classes/functions without explicit instruction.
- Do not fabricate data that impersonates a real external signal (see Offline-First above).
- Claude drafts and implements; Claude does not `git add`/`commit`/`push` — that is Codex's
  role (`.claude/skills/review.md`).
- `DECISIONS.md` entries are never deleted, only appended to.
