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

## Codex Skills

Use project Codex skills when the task matches:

- `ai-content-os-sprint`: Sprint implementation or Sprint verification
- `ai-content-os-commit-check`: pre-commit classification and safety check
- `ai-content-os-research`: saving CTO-analyzed external materials into project docs
- `ai-content-os-retry-audit`: diagnosing slow workflow, retry, fallback, service diagnostics
- `ai-content-os-doc-update`: updating `PROJECT_SNAPSHOT.md`, `CHANGELOG.md`, `MODULE_STATUS.md`, `ROADMAP.md`, `DECISIONS.md`

Do not re-read the entire repository when a skill gives a narrower context path.
Prefer the smallest relevant context.
Always preserve WorkflowEngine and `workflow_completed`.
