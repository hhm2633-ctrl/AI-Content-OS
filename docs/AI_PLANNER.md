# AI Planner

## Naming Note (Sprint 15-0A)

This document describes the **AI-collaborator task-routing** concept (how work is split across
ChatGPT/Claude/Codex) — see "Purpose" below. There is a second, unrelated use of the name "AI
Planner" in the codebase: `modules/ai_planner/` implements a **content-strategy Pre-Planning
Engine Contract** (deciding pattern/hook/CTA/image-strategy hints for a single card-news run,
coordinating Pattern/Knowledge/Competitor/Image Strategy/Content/Brand DNA/Trend Memory
Engines). The two concepts share a name but are different systems:

- This document / the routing concept: **Planning-only, no code** (part of the Claude/Codex/
  ChatGPT role division, `.ai/rules/ai_roles.md`, `docs/AI_PLANNER.md` itself).
- `modules/ai_planner/` (`PlannerContract`, `PlanningContext`, `AIPlannerModule`): **Contract
  defined in Sprint 15-0, dependency-repaired in Sprint 15-0A** — see `MODULE_STATUS.md`'s
  Sprint 15-0/15-0A entries. Its Decision Engine is not implemented and it is not connected to
  `WorkflowEngine`.

Do not conflate the two when reading Sprint history — "AI Planner: Contract defined" in
`ROADMAP.md`/`MODULE_STATUS.md` refers to `modules/ai_planner/`, not this document's routing
rules below.

## Purpose

The AI Planner decides how AI work should be distributed across ChatGPT, Claude, and Codex while controlling cost and repository risk.

## Roles

- ChatGPT: CTO, architecture, research analysis, sprint decomposition
- Claude: large implementation drafts, broad refactors, repeated edits
- Codex: repository operation, compile, test, git diff review, focused fixes, documentation updates

## Routing Rules

- 1 to 3 files: Codex
- 4 to 7 files: ChatGPT decomposes and routes
- 8 or more files: Claude draft, Codex review and integration

## Cost Principles

- Evaluate ROI before starting each sprint.
- Avoid unnecessary Claude/Codex calls.
- Keep implementation tasks small.
- Prefer documentation planning before large code changes.

## Sprint Rule

Before each sprint, confirm:

- MVP relevance
- Expected file count
- Test path
- Fallback impact
- Commit target
- Excluded runtime outputs
