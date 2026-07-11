---
name: ai-content-os-sprint
description: AI-Content-OS Sprint 작업을 안전하게 진행하기 위한 표준 절차. WorkflowEngine 보존, 모듈 테스트 우선, Sprint 마지막 전체 실행, workflow_completed 확인까지 포함한다.
---

# AI-Content-OS Sprint Skill

## Purpose

Use this skill when working on any AI-Content-OS Sprint.

This project is a Windows-first AI content automation repository.
The main command is always:

```powershell
py -m src.main
```

Never use:

```powershell
python -m src.main
```

## Protected Rules

- Do not create a new project.
- Do not replace or redesign WorkflowEngine.
- Do not rename existing folders, modules, or classes unless explicitly instructed.
- Do not break `workflow_completed`.
- Internet, LLM, browser, and image API failures must be handled as fallback/cache/retry/status events, not workflow failures.
- Keep changes Sprint-sized.
- Do not expand scope without explicit approval.
- Do not hardcode API keys.
- Do not read or print `.env`.

## Required Context Files

Before Sprint work, inspect only the necessary project context:

- `PROJECT_MASTER.md`
- `PROJECT_SNAPSHOT.md`
- `MODULE_STATUS.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `AGENTS.md`
- `CURRENT_TASK.md` if relevant
- `DECISIONS.md` if relevant

Avoid reading every document unless the task requires it.

## Sprint Decision Rule

Before making changes, classify the task:

- Directly helps CardNews MVP or workflow reliability: proceed.
- Helps later Shorts, Video, Dashboard, Analytics: move to Roadmap unless explicitly approved.
- Work/Codex is the default implementation path regardless of file count.
- Use Claude only when the user requests it or an independent second opinion has clear value.
- For new work prefer `ai-content-os-sprint-manager`; keep this skill for compatibility.

## Work Order

1. Identify target module.
2. Inspect current files.
3. Make minimal changes.
4. Run module-level checks first when possible.
5. Run compile check:

```powershell
py -m compileall src modules scripts
```

6. Run full workflow only at Sprint end:

```powershell
py -m src.main
```

7. Confirm:

```text
storage/workflow_results/99_final_result.json
status is workflow_completed
```

8. Update:
   - `PROJECT_SNAPSHOT.md`
   - `CHANGELOG.md`
   - `MODULE_STATUS.md`
9. Report:
   - changed files
   - new files
   - excluded files
   - compile result
   - workflow result
   - workflow_completed status
   - execution time
   - known risks

## Done Means

A Sprint is not complete until:

- compile check passes
- full workflow passes, unless user explicitly says not to run it
- `workflow_completed` is confirmed
- project docs are updated
- no `.env` or runtime storage files are included
