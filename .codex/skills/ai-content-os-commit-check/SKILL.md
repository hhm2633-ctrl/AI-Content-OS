---
name: ai-content-os-commit-check
description: AI-Content-OS 변경사항을 커밋 전 안전하게 분류하고 검수하는 절차. .env와 storage 산출물 제외, 변경 파일 검토, 테스트 결과 확인을 포함한다.
---

# AI-Content-OS Commit Check Skill

## Purpose

Use this skill before committing or preparing a final report.

## Absolute Exclusions

Never commit:

- `.env`
- `storage/**`
- `__pycache__/**`
- `*.pyc`
- temporary logs
- runtime-generated images
- runtime workflow outputs
- API keys or secrets

Do not print `.env`.

## Commit Candidate Areas

Commit candidates usually include:

- `src/**`
- `modules/**`
- `config/**`
- `templates/**`
- `prompts/**`
- `docs/**`
- `.codex/**`
- `.agents/**`
- root markdown files:
  - `PROJECT_MASTER.md`
  - `PROJECT_SNAPSHOT.md`
  - `ROADMAP.md`
  - `CHANGELOG.md`
  - `MODULE_STATUS.md`
  - `DECISIONS.md`
  - `CURRENT_TASK.md`
  - `AGENTS.md`
  - `CLAUDE.md`
  - `README.md`

## Check Order

1. Run git status.
2. Classify files:
   - commit target
   - exclude
   - needs user decision
3. Inspect diffs for important modified files.
4. Confirm no `.env` or `storage/**` is staged.
5. Confirm docs updated after meaningful changes.
6. Run:

```powershell
py -m compileall src modules scripts
```

7. If Sprint-end verification is required, run:

```powershell
py -m src.main
```

8. Confirm `workflow_completed`.

## Final Report Format

Return:

```text
[Commit Check Report]

Commit candidates:
- ...

Excluded:
- ...

Needs user decision:
- ...

Compile:
- success/fail

Workflow:
- success/fail
- workflow_completed: yes/no
- execution time:

Docs updated:
- PROJECT_SNAPSHOT.md
- CHANGELOG.md
- MODULE_STATUS.md

Risk:
- ...
```

## Do Not

- Do not auto-commit unless user explicitly instructs.
- Do not run destructive git commands.
- Do not run `git rm --cached` unless user explicitly approves.
- Do not modify `storage/**` during commit cleanup.
