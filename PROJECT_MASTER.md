# AI-Content-OS Project Master

## Purpose

AI-Content-OS is a content operating system for automated trend research, card news generation, publishing preparation, and future multi-format content workflows.

## Current Core

Protected pipeline (`src/workflow_engine.py::WorkflowEngine`, never reordered without explicit
instruction):

- Trend collection
- Topic selection
- AI Planner (Hint Layer, wired Sprint 15-3 — see "AI Planner Contract" below; never a forced
  decision, every downstream Engine keeps its own selection logic and fallback)
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

No remaining Planning items from the original list — AI Planner (the last one) completed its
`WorkflowEngine` wiring and Consumer Layer integration in Sprint 15-3 (see "AI Planner Contract"
below and `MODULE_STATUS.md`'s Sprint 15-3 entry).

## AI Planner Contract (Sprint 15-0, Architecture Only; dependency-repaired Sprint 15-0A; Decision Engine v1 added Sprint 15-1; Consumer Layer added Sprint 15-2; wired into WorkflowEngine Sprint 15-3)

AI Planner is designed to eventually become the central coordinating Engine across Pattern
Engine, Knowledge Engine, Competitor Engine, Image Strategy, Content Engine, Brand DNA Engine,
and Trend Memory. Sprint 15-0 defined the **contract only** — no decision logic. Sprint 15-0A
fixed a structural defect in that Contract: it originally required `pattern_result`,
`knowledge_result`, `trend_memory_result`, `competitor_result`, and `image_strategy_result` as
Planner inputs, but the Planner's intended `WorkflowEngine` position (after `TopicEngineModule`,
before `PatternEngineModule`) runs **before** all five of those stages produce their results —
making the original Contract unimplementable without placeholders or reordering the Workflow
(both forbidden). Sprint 15-0A re-scoped AI Planner v1 as a **Pre-Planning Engine** with inputs
split into genuinely-available **Runtime Inputs** (from the current run, pre-Planner) and
**Historical Inputs** (accumulated past-run data read from existing Engine Interfaces):

- `modules/ai_planner/planner_contract.py` (`PlannerContract`) — single source of truth for
  the coordinated-Engine list, `RUNTIME_INPUT_FIELDS`/`HISTORICAL_INPUT_FIELDS`/`INPUT_FIELDS`,
  `FORBIDDEN_FUTURE_STAGE_INPUT_FIELDS`, Output field list, and the intended `WorkflowEngine`
  connection point (documented via `PlannerContract.describe()`).
- `modules/ai_planner/planning_context.py` (`PlanningContext`) — the corrected Input Contract:
  3 Runtime fields (`trend_result`, `topic_result`, `brand_profile`) + 5 Historical fields
  (`knowledge_history`, `trend_memory_history`, `competitor_history`, `brand_dna_history`,
  `performance_history`). `pattern_result`/`knowledge_result`/`trend_memory_result`/
  `competitor_result`/`image_strategy_result` are no longer accepted.
- `modules/ai_planner/planning_result_schema.py` — the Output Contract (`REQUIRED_FIELDS`,
  unchanged from Sprint 15-0): `selected_pattern`, `selected_hook_strategy`,
  `selected_cta_strategy`, `selected_image_strategy`, `knowledge_priority`,
  `competitor_reference`, `content_strategy`, `planner_confidence`, `planner_reason`,
  `planner_version`; plus `build_undecided_result()`, `validate_schema()`, and (added
  Sprint 15-0A) `TARGET_ENGINE_BY_FIELD` mapping each selectable field to the downstream Engine
  it is meant for.
- `modules/ai_planner/planner_interface.py` (`PlannerInterface`) — read-only API for future
  Engines/Sprints; now also exposes `load_historical_inputs()` (added Sprint 15-0A), which reuses
  the existing `KnowledgeInterface`/`TrendMemoryInterface`/`CompetitorInterface`/
  `BrandDNAInterface`/`PerformanceScoreInterface` to read real accumulated `storage/` data —
  no new storage structure was invented.
- `modules/ai_planner/planner_module.py` (`AIPlannerModule`) — a thin entry point that
  normalizes any input into a `PlanningContext` and delegates to
  `planner_decision_engine.py::PlannerDecisionEngine` for the real decision, then validates the
  result with `validate_schema()`. **Wired into `WorkflowEngine` since Sprint 15-3** —
  `WorkflowEngine.__init__` instantiates it, and `WorkflowEngine._run_ai_planner()` calls
  `run()` between `TopicEngineModule` and `PatternEngineModule`, returning `None` (not raising)
  on any failure.
- `modules/ai_planner/planner_decision_engine.py` (`PlannerDecisionEngine`, added Sprint 15-1) —
  the actual Decision Engine. Computes `selected_pattern`/`selected_hook_strategy`/
  `selected_cta_strategy` by reusing the exact same rule-based classes `PatternEngineModule`
  uses (`KeywordWeightEngine`/`TopicClassifier`/`TopicCluster`/`ConfidenceScorer`/
  `PatternSelector`/`HookSelector`/`CTASelector`) on the Runtime Input's `selected_topic`/
  `trends`, with an optional Brand DNA history override for hook/cta once
  `brand_dna_history.total_observations >= 5`. `knowledge_priority`/`competitor_reference` come
  from sorting/filtering real Historical Input statistics. No LLM call, no external API, no
  random values — any unexpected failure falls back to `build_undecided_result()` (kept as the
  exception-safety net, not the normal path). Still never fabricates a decision that isn't
  traceable to a real input.
- `modules/ai_planner/consumer_contract.py` (`PlannerConsumerContract`, added Sprint 15-2) — the
  CTO decision that Planner output is a **verified hint, never a forced command**, encoded as
  four AND-gates: `is_result_valid()` (schema-valid + actually decided), `meets_confidence_threshold()`
  (`planner_confidence >= MIN_CONFIDENCE_FOR_HINT_APPLICATION = 0.5`), `is_value_supported()`
  (the hinted value must be a member of the Consumer Engine's own real enum), and a caller-supplied
  `safety_conflict` flag (the Consumer Engine's own existing safety rule, e.g. Pattern Engine's
  low-confidence-forces-"resource" fallback or a blocked category) — any gate failing means "keep
  the existing Engine value/logic," never an exception.
- `modules/ai_planner/planner_consumer_adapter.py` (`PlannerConsumerAdapter`, added Sprint 15-2) —
  per-field `resolve_pattern`/`resolve_hook`/`resolve_cta`/`resolve_image_strategy`/
  `resolve_knowledge_priority`/`resolve_competitor_reference` methods that choose between the
  Planner's hint and an already-computed Engine default (it never re-runs Pattern/Hook/CTA/Image
  Strategy selection itself). Supported-value sets are the real Engine enums
  (`PatternSelector.PATTERN_TYPES`, `HookSelector.HOOK_TYPES`, `CTASelector.CTA_TYPES`,
  `ImageSourceSelector.SOURCE_PRIORITY` keys, `KnowledgeExtractor.KNOWLEDGE_TYPES`) — nothing
  invented. **Actually called since Sprint 15-3** by `PatternEngineModule.run()`
  (`resolve_pattern`), `ContentPromptBuilder.build()` (`resolve_hook`/`resolve_cta`),
  `ImageStrategyModule.run()` (`resolve_image_strategy`), and `KnowledgeModule.run()`
  (`resolve_knowledge_priority`, applied as a small `overall_score` boost to this run's newly
  extracted items only — `KnowledgeRanker` still does all the actual sorting). Every one of
  these Engines keeps its own existing selection logic/fallback fully intact; the Adapter only
  chooses between the Engine's own already-computed value and the Planner's hint, and every
  consumption point records a `planner_consumption.*` entry built by the shared
  `build_consumption_metadata()` helper (`planner_available`/`planner_applied`/`planner_mode`/
  `planner_confidence`/`requested_value`/`original_value`/`final_value`/`reason`/`fallback_used`).

See `MODULE_STATUS.md`'s Sprint 15-0, Sprint 15-0A, Sprint 15-1, Sprint 15-2, and Sprint 15-3
entries for full detail and Codex's independent review results.

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
