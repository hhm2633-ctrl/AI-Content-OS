---
name: ai-content-os-sprint-manager
description: AI-Content-OS Sprint의 목표, 범위, 작업 순서, 상태 추적, Work/Codex 실행, 선택적 Claude 검토, 문서 갱신, QA, 커밋과 인계를 처음부터 완료까지 관리할 때 사용한다.
---

# Sprint Manager

## Operating Model

Use ChatGPT Work for CTO decisions, research, project context, and orchestration. Use Codex capabilities in the same workspace for implementation, tests, docs, and Git. Use Claude only as an optional independent reviewer or explicitly assigned specialist; do not require Claude or Codex MCP in the default path.

## Sprint Workflow

1. Read `AGENTS.md`, `CURRENT_TASK.md`, `PROJECT_SNAPSHOT.md`, `ROADMAP.md`, `MODULE_STATUS.md`, and relevant decisions.
2. Run `ai-content-os-cto-review` for scope, ROI, dependencies, and approval gates.
3. Define one outcome, protected files, target files, tests, and done criteria.
4. Track work with one active step at a time.
5. Implement small additive changes using the relevant domain skill.
6. Run `ai-content-os-qa` and confirm `workflow_completed` at Sprint end.
7. Run `ai-content-os-doc-update` and `ai-content-os-commit-check`.
8. Commit only the intended source, docs, and tests; report any push or approval blocker.

## Boundaries

- Do not route by file count alone. Route by risk, context, domain specialization, and need for independent review.
- Do not mix a completed feature commit with operating-system or tooling refactors.
- Do not require Claude to call Codex MCP.
- Do not mark a Sprint complete without required verification and documentation.

## Completion Report

Report changed files, tests, full workflow state, fallbacks, excluded runtime files, commit/push state, residual risks, and the next approved priority.
