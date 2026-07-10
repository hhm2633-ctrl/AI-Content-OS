# AI-Content-OS Project Master

## Purpose

AI-Content-OS is a content operating system for automated trend research, card news generation, publishing preparation, and future multi-format content workflows.

## Current Core

Protected pipeline (`src/workflow_engine.py::WorkflowEngine`, never reordered without explicit
instruction):

- Trend collection
- Topic selection
- Pattern selection
- Research
- Content generation
- Image strategy selection (real-image-first decision, added Sprint 10)
- Image prompt generation
- Image generation
- Card news rendering and QA
- Publishing preparation

Intelligence Layer (additive bonus stages after Publishing, added Sprint 11–13; may be
reordered among themselves when a real data dependency requires it):

- Knowledge Engine — extraction/classification/scoring/ranking of reusable Hook/CTA/Pattern/
  Layout/Brand/Workflow/Prompt Pattern/Tool/Image Strategy/Funnel knowledge; consumed by
  Pattern Engine, Content Module, CardNews Module, Audit Engine, and Learning Engine
- Trend Memory — records recent topic/hook/cta/layout/image combinations, flags repeat risk
- Performance Score — composite hook/cta/layout/brand/image score, shared by Audit/Learning/
  Analytics
- Audit Engine — 9-check content audit (hook/cta/pattern/layout/brand/image strategy/
  duplicate/save inducement/comment inducement)
- Learning Engine — `internal_learning_score` (audit + performance + knowledge, real local
  data only) promotes high-performing patterns into a reinforced Learning Memory
- Analytics Engine — honest local `quality_trend`, no fabricated SNS metrics
- Brand DNA Engine — tracks actually-used hook/cta/layout/color per run
- Competitor Engine — offline-first competitor profiles parsed from `benchmark/*.md` docs

See `MODULE_STATUS.md` for the full Sprint-by-Sprint history and `ROADMAP.md` for what's
implemented vs. still Planning.

## Planning Additions

- AI Planner (AI task routing / cost control / Sprint ROI review) — the only Engine from the
  original Planning Additions list not yet implemented as a Decision Engine; see
  `docs/AI_PLANNER.md`. Its **Contract** (input/output/schema/workflow connection point) was
  defined in Sprint 15-0 under `modules/ai_planner/` — see "AI Planner Contract" below. No
  actual decision logic exists yet, and it is not connected into `WorkflowEngine`.

## AI Planner Contract (Sprint 15-0, Architecture Only)

AI Planner is designed to eventually become the central coordinating Engine across Pattern
Engine, Knowledge Engine, Competitor Engine, Image Strategy, Content Engine, Brand DNA Engine,
and Trend Memory. Sprint 15-0 defined the **contract only** — no decision logic:

- `modules/ai_planner/planner_contract.py` (`PlannerContract`) — single source of truth for
  the coordinated-Engine list, Input/Output field lists, and the intended `WorkflowEngine`
  connection point (documented via `PlannerContract.describe()`).
- `modules/ai_planner/planning_context.py` (`PlanningContext`) — the 8-field Input Contract:
  `trend_result`, `topic_result`, `pattern_result`, `knowledge_result`, `trend_memory_result`,
  `competitor_result`, `brand_profile`, `image_strategy_result`.
- `modules/ai_planner/planning_result_schema.py` — the Output Contract (`REQUIRED_FIELDS`):
  `selected_pattern`, `selected_hook_strategy`, `selected_cta_strategy`,
  `selected_image_strategy`, `knowledge_priority`, `competitor_reference`, `content_strategy`,
  `planner_confidence`, `planner_reason`, `planner_version`; plus `build_undecided_result()`
  and `validate_schema()`.
- `modules/ai_planner/planner_interface.py` (`PlannerInterface`) — read-only API for future
  Engines/Sprints, consistent with every other Engine's `*_interface.py` pattern.
- `modules/ai_planner/planner_module.py` (`AIPlannerModule`) — a Skeleton that accepts a
  `PlanningContext` and returns a schema-valid but fully **undecided** result (`selected_*` and
  `content_strategy` are `None`, `planner_confidence: 0.0`) — never a fabricated-looking
  decision. Not wired into `WorkflowEngine`; only a comment marks the intended connection point
  (after `TopicEngineModule`, before `PatternEngineModule`).

See `MODULE_STATUS.md`'s Sprint 15-0 entry for full detail and Codex's independent review result.

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

Its core mechanism is the **Claude Skill System** under `.claude/skills/`. The entry-point
skill is `.claude/skills/cto_operating_system/SKILL.md`, which points to the project-root
`PROJECT_OPERATING_SYSTEM.md` (the top-level operating reference and Mandatory Reading Order)
and is read before any other skill file.

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
