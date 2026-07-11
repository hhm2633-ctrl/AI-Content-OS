# Claude Task: Shorts Phase 0 Architecture and Contract Draft

## Role

You are an isolated architecture researcher for AI-Content-OS. CardNews M7, M8, and M7-next are
operationally complete. Your task is to design the next Shorts phase without changing any working
pipeline.

## Single Deliverable

Create or replace only:

`docs/SHORTS_ARCHITECTURE_DRAFT.md`

Do not edit any other file. Do not implement code, run Git operations, change WorkflowEngine, update
shared status documents, or claim Shorts is implemented. Do not invoke Codex MCP. Stop after the
draft is complete and report the single changed file.

## Read First

- `PROJECT_OPERATING_SYSTEM.md`
- `CURRENT_TASK.md`
- `ROADMAP.md`
- `MODULE_STATUS.md`
- `SYSTEM_ARCHITECTURE.md`
- `docs/RESEARCH/AlphaCut.md`
- `docs/KNOWLEDGE_ENGINE.md`
- `.codex/skills/ai-content-os-shorts/SKILL.md`
- Existing contracts under `modules/topic`, `modules/research`, `modules/content`,
  `modules/brand_dna_engine`, `modules/card_news`, and `modules/publishing`

Read the smallest relevant set of source files needed to identify existing JSON contracts. Treat the
repository as the source of truth when documentation and code differ.

## Draft Requirements

The draft must be implementation-ready but must not contain implemented code. Include:

1. Purpose, user outcome, scope, and explicit non-goals for Shorts Phase 0.
2. Inputs reused from Topic, Research, Content, Brand DNA, CardNews, and Publishing. Name exact
   existing fields where confirmed and label every assumption.
3. Proposed output contracts for shorts brief, script, scene plan, asset plan, captions, audio plan,
   render plan, QA result, and publish-preparation result. Provide compact JSON examples.
4. Module boundaries and a minimal future file map that preserves the existing `WorkflowEngine`.
5. Deterministic offline/fallback behavior for every external dependency failure.
6. Manual operator checklist for assets, voice, music, captions, render review, rights, and upload.
7. External dependency gates for transcription, TTS, video generation/editing, music, stock assets,
   and platform publishing APIs. No API key may be required for Phase 0.
8. Copyright, likeness, disclosure, privacy, platform-policy, and credential-handling constraints.
9. Risk-based test plan covering unit contracts, fallback paths, duration/caption limits, asset
   provenance, and future end-to-end verification.
10. A phased roadmap from contract-only Phase 0 to an optional production renderer. Each phase must
    have entry criteria, exit criteria, dependencies, and rollback boundaries.
11. Open questions and CTO approval gates. Separate facts found in the repository from proposals.

## Protected Boundaries

- Do not modify or duplicate `CardNewsModule`, its Pillow renderer, or CardNews QA.
- Do not add a new top-level engine during this task.
- Do not alter existing module names, folders, classes, schemas, or workflow order.
- Do not fabricate external metrics, comments, evidence, licenses, or API availability.
- External failures must remain fallback events, never workflow failures.
- Do not recommend installing a service or library without stating its license, operating cost,
  maintenance risk, data handling, and replaceability.

## Quality Bar

The output must let Work/Codex review the architecture and approve a small implementation Sprint
without repeating the research. Prefer tables and explicit contracts over broad prose. Mark uncertain
items as `ASSUMPTION`, unresolved decisions as `CTO GATE`, and repository-backed statements as
`CONFIRMED`.

## Completion Response

Return only:

- changed file: `docs/SHORTS_ARCHITECTURE_DRAFT.md`
- sections completed
- unresolved CTO gates
- confirmation that no other file, code, Git state, or WorkflowEngine behavior was changed
