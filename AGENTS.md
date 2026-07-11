# AI-Content-OS Codex Rules

This document defines the rules Codex must follow in the AI-Content-OS repository.

## Execution Rules

- Always run the project with `py -m src.main`.
- Do not use `python -m src.main`.
- Use `py -m compileall src modules scripts` as the default compile check.
- After meaningful changes, run `py -m src.main` when feasible and confirm `workflow_completed`.

## Structure Rules

- Do not create a new project.
- Keep the existing `WorkflowEngine` structure.
- Keep existing module names, folder names, and class names.
- Add new behavior as small modules connected to the current flow.
- Avoid unrelated refactors.

## Stability Rules

- Do not break `workflow_completed`.
- Internet, LLM, and image API failures must be fallback events, not workflow failures.
- Keep Naver News and Nate Pann fallback/cache behavior intact.
- Keep cache files under `storage/cache`.
- Record source failure reasons and fallback use in result JSON files.

## Documentation Rules

- Update `PROJECT_SNAPSHOT.md` after meaningful changes.
- Update `CHANGELOG.md` after meaningful changes.
- Prefer `scripts/update_project_snapshot.py` for snapshot/changelog updates.

## Sprint Rules

- Before Sprint work, check `ROADMAP.md`, `MODULE_STATUS.md`, and `docs/SPRINT_01.md`.
- Keep Sprint work small and aligned with the current Sprint goal.
- Completion reports should include changed files, test results, final state, and error details.

## Mandatory Delegation Rules

- For any task spanning more than one independent concern, the CTO must split work before implementation.
- The CTO owns scope, contracts, file ownership, approval gates, integration review, and final Git operations. The CTO must not default to implementing every workstream personally.
- Run independent workstreams in parallel when their file ownership does not overlap.
- Every delegated work order must state: objective, owned files, prohibited files, required reading, completion checks, and handoff format.
- Assign one writer per file. Shared status documents and Git are owned only by the CTO/integration lane.
- Claude and worker agents must not edit `CURRENT_TASK.md`, `ROADMAP.md`, `MODULE_STATUS.md`, `DECISIONS.md`, `CHANGELOG.md`, `PROJECT_SNAPSHOT.md`, or perform Git operations unless the CTO explicitly assigns that ownership.
- The CTO may implement directly only for integration glue, urgent blockers, or a small task that cannot be split usefully. Record the reason in the progress update.
- Do not wait idly for a delegated lane. Continue a non-overlapping lane or integration preparation.
- Use `docs/ACTIVE_PARALLEL_WORK_ORDERS.md` as the active assignment board and handoff contract.

## Codex Skills

Use project Codex skills when the task matches:

- `ai-content-os-sprint-manager`: end-to-end Sprint scope, execution, QA, docs, and handoff
- `ai-content-os-cto-review`: architecture, ROI, risk, tool/plugin, and approval review
- `ai-content-os-trend-collector`: trend sources, retry, cache, fallback, and selection
- `ai-content-os-research-intelligence`: evidence-backed research context and insight
- `ai-content-os-card-news`: card-news structure, rendering, readability, and production QA
- `ai-content-os-shorts`: approved Shorts/Reels planning and dependency gates
- `ai-content-os-publishing`: captions, hashtags, queue, schedule, and publish readiness
- `ai-content-os-instagram`: Instagram research, learning, metrics, and API boundaries
- `ai-content-os-coupang`: approved commerce planning and product-data integrity
- `ai-content-os-qa`: risk-based tests, compile, workflow, and output verification
- `ai-content-os-sprint`: legacy Sprint compatibility workflow
- `ai-content-os-commit-check`: pre-commit classification and safety check
- `ai-content-os-research`: saving CTO-analyzed external materials into project docs
- `ai-content-os-retry-audit`: diagnosing slow workflow, retry, fallback, service diagnostics
- `ai-content-os-doc-update`: updating `PROJECT_SNAPSHOT.md`, `CHANGELOG.md`, `MODULE_STATUS.md`, `ROADMAP.md`, `DECISIONS.md`

Do not re-read the entire repository when a skill gives a narrower context path.
Prefer the smallest relevant context.
Always preserve WorkflowEngine and `workflow_completed`.
