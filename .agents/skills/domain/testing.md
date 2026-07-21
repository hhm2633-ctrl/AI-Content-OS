---
name: testing
description: Compile/Workflow 실행 방법과 workflow_completed 확인 절차. review.md의 체크리스트가 참조하는 실제 실행 방법을 정의한다.
---

# Testing Skill

## Purpose

AI-Content-OS에는 별도 테스트 스위트(`tests/`)가 없다. 검증은 오직 두 명령으로 이루어진다.
이 스킬은 그 두 명령을 "언제/어떻게" 쓰는지를 정의한다 — 완료 체크리스트 자체는 `review.md`를 따른다.

## Compile

```powershell
py -m compileall src modules scripts
```

- 문법 오류만 잡는다 (import 시점 오류나 런타임 로직 오류는 잡지 못한다).
- 대부분의 Sprint 지시에서 최소한 이 명령까지는 허용된다 — 지시에 다른 언급이 없다면 항상 이 명령으로 마무리한다.
- 출력에 `Compiling '<path>'...`가 새로 수정/추가한 모든 파일에 대해 나오는지 확인한다. 오류가 나오면 해당 파일의 트레이스백을 그대로 보고에 포함한다.

## Workflow

```powershell
py -m src.main
```

- **절대 `python -m src.main`을 사용하지 않는다** (이 환경에서 `python` 명령이 인식되지 않는다).
- Sprint 지시에 "py -m src.main 실행 금지"가 있으면 이 단계 전체를 건너뛰고, 보고서에 "실행하지 않음"을 명시한다 — 임의로 실행하지 않는다.
- 실행이 허용된 경우, 실행 후 아래를 확인한다:
  - `storage/workflow_results/99_final_result.json`의 `status`
  - 각 단계 결과(`01_trend_result.json` ~ `09_publishing_result.json`)가 모두 생성되었는지
  - 콘솔에 `workflow_completed`가 출력되었는지

## workflow_completed 확인

- 유일한 성공 기준은 `storage/workflow_results/99_final_result.json`의 최상위 `"status": "workflow_completed"`다.
- 개별 단계의 `fallback_used: true`(Naver/Nate/LLM/Image 등)는 **정상적인 성공 사례**다 — fallback-first 계약에 따라 실패가 아니라 성공으로 취급된다. `workflow_failed`가 나온 경우에만 실제 실패로 간주한다.
- `workflow_failed`가 나오면 `storage/workflow_results/00_workflow_error.json`에 예외 메시지가 기록된다 — 이를 `debug.md`의 원인 분석 절차로 조사한다.

## 이 스킬이 다루지 않는 것

- Compile/Workflow 결과를 언제 문서(`PROJECT_SNAPSHOT.md`/`CHANGELOG.md`/`MODULE_STATUS.md`)에 반영할지는 `review.md`를 따른다.
- 실행 시간이 비정상적으로 길다면 `performance.md`를 참고한다.
