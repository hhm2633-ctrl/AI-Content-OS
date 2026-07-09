# AI-Content-OS Project Master

## Purpose

AI-Content-OS is a content operating system for automated trend research, card news generation, publishing preparation, and future multi-format content workflows.

## Current Core

- Trend collection
- Topic selection
- Pattern selection
- Research
- Content generation
- Image prompt generation
- Image generation
- Card news rendering and QA
- Publishing preparation

## Planning Additions

- Knowledge Engine
- Competitor Engine
- Audit Engine
- AI Planner

## Research Knowledge Base

Research conclusions are stored under `docs/` and `docs/RESEARCH/`.

External material is analyzed by ChatGPT CTO first. Claude and Codex use the analyzed documentation as project context and do not re-analyze raw material by default.

## Codex Skill System

Codex Skill System added.

Skills are used to reduce repeated instructions and speed up Sprint execution.

Reusable workflows:

- Sprint
- Commit Check
- Research Knowledge
- Retry Audit
- Documentation Update

## Claude Developer Kit

Claude Developer Kit v1 added. This is the project-specific framework (documentation only, no code) that
defines how Claude approaches recurring AI-Content-OS work: project understanding, large implementation,
refactoring, Sprint planning, and external-research handling.

Its core mechanism is the **Claude Skill System** under `.claude/skills/`.

Claude roles:

- Architecture
- Large Implementation
- Refactoring
- Research
- Planning
- Review

## Claude Domain Skill

Claude Domain Skill (v2 of the Claude Developer Kit) added under `.claude/skills/domain/`. These are
per-engine implementation Skills so Claude does not have to re-derive real module names, fallback chains,
or known gaps for each engine every Sprint:

- `cardnews.md`, `trend_engine.md`, `topic_engine.md`, `pattern_engine.md`, `content_engine.md`, `image_engine.md`, `publishing_engine.md`
- Cross-cutting: `debug.md`, `performance.md`, `testing.md`

## AI Developer Kit

AI Developer Kit Foundation v1 added under `.ai/`. This is shared, AI-agnostic project infrastructure that
every collaborating AI (ChatGPT CTO, Claude, Codex, and any future AI) references, sitting above the
AI-specific skill systems (Codex Skill System, Claude Developer Kit):

- `.ai/architecture/system_architecture.md` — full structure, WorkflowEngine, Module/Engine/document relationships
- `.ai/workflows/development_workflow.md`, `sprint_workflow.md` — user -> ChatGPT CTO -> Claude -> Codex -> GitHub, and the Sprint lifecycle
- `.ai/rules/project_rules.md`, `ai_roles.md`, `workflow_protection.md` — absolute rules, AI role division, workflow/fallback/retry/cache protection
- `.ai/prompts/README.md` — prompt management principles and Prompt Library structure
- `.ai/templates/task_template.md`, `sprint_template.md` — reusable templates for writing task instructions and Sprint plans
- `.ai/knowledge/knowledge_system.md` — external material -> CTO analysis -> Research docs -> project assets
- `.ai/decision/decision_engine.md` — ROI/file-count/risk-based decision rules for Claude vs. Codex and Roadmap triage

## Protected Rules

- Keep existing WorkflowEngine structure.
- Use `py -m src.main`.
- Do not use `python -m src.main`.
- Keep `workflow_completed` from regressing.
- Treat external API, network, and rendering failures as fallback/status events where possible.
