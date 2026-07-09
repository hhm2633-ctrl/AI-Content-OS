# Claude Codex Workflow Research

## Summary

AI-Content-OS should split AI work by responsibility.

- ChatGPT: CTO, architecture, strategy, planning, documentation decisions
- Claude: bulk implementation, complex refactoring, large draft changes
- Codex: repository integration, compile, test, git diff review, documentation update

## Task Routing Rules

- 1 to 3 files: Codex
- 4 to 7 files: ChatGPT decomposes the task, then routes to Codex or Claude
- 8 or more files: Claude draft first, Codex review and repository integration

## Additional Engines

- AI Planner
- AI Task Router
- AI Cost Optimizer
- Sprint Planner
- AI Capability Manager

## AI-Content-OS Direction

Keep GitHub as the source of truth. Use ChatGPT analysis as the project-level decision layer, then route implementation and verification to Claude/Codex according to file count, risk, and cost.
