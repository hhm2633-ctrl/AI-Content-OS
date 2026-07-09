# AI Planner

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
