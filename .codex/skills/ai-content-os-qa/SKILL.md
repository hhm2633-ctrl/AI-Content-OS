---
name: ai-content-os-qa
description: AI-Content-OS 변경의 위험 기반 테스트 범위, compile, unit/regression test, 전체 WorkflowEngine 실행, 결과 JSON과 시각 산출물 검증, 커밋 전 품질 판정을 수행할 때 사용한다.
---

# QA

## Test Order

1. Classify changed contracts and highest-risk failure modes.
2. Run the smallest focused tests first.
3. Run `py -m compileall src modules scripts`.
4. Run broader regression tests when shared contracts changed.
5. At Sprint end run `py -m src.main` and wait for completion.
6. Inspect `storage/workflow_results/99_final_result.json` and relevant stage outputs.
7. Inspect PNG/PDF/video output visually when layout or media behavior changed.

## Pass Criteria

- Focused tests pass for each changed behavior.
- Network, LLM, and image failures are recorded fallbacks rather than workflow failure.
- Final status is `workflow_completed`.
- Output schemas preserve existing required fields.
- No `.env`, `storage/**`, logs, caches, or generated media is staged.

## Failure Reporting

Distinguish code failures from environment, network, permissions, credentials, and test-fixture failures. Report the failing command, exact contract affected, fallback state, and next safe action. Do not call a run successful merely because the process exited zero when final status is missing.
