# Sprint Workflow

개별 Sprint(작업 단위) 하나가 시작부터 끝까지 어떻게 진행되는지 정의한다.
`development_workflow.md`가 "누가"를 다룬다면, 이 문서는 "한 Sprint 안에서 어떤 순서로"를 다룬다.

```text
Sprint 시작
  ↓
ROI 평가            카드뉴스 MVP에 직접 기여하는가? (.ai/decision/decision_engine.md)
  ↓
작업 분해            8개 이상 파일/신규 모듈/복잡한 리팩토링인가, 소규모 국소 수정인가?
  ↓
Claude              담당 판단되면 지시서(.ai/templates/task_template.md 형식)를 받아 구현
  ↓
Codex               Repository 검토, 실제 실행/커밋 준비
  ↓
Compile             py -m compileall src modules scripts
  ↓
workflow_completed   허용된 경우 py -m src.main 실행 후 storage/workflow_results/99_final_result.json 확인
  ↓
문서 업데이트         PROJECT_SNAPSHOT.md / CHANGELOG.md / MODULE_STATUS.md
```

## 단계별 세부 기준

### ROI 평가
- 카드뉴스 MVP(Trend→Topic→Pattern→Research→Content→Image→CardNews→Publishing) 파이프라인의 안정성/품질을 직접 개선하는가 → 진행.
- Shorts/Blog/SmartStore/대시보드 등 `ROADMAP.md`의 M5~M6, Later Roadmap 항목에 해당 → Sprint화하지 않고 Roadmap에 남긴다.
- 판단 기준 상세는 `.ai/decision/decision_engine.md`.

### 작업 분해
- Sprint 지시서(ChatGPT CTO)는 항상 아래를 명시해야 한다: 목표, 절대 규칙(수정 금지 항목 포함), 수정 가능/수정 금지 파일·폴더, 구현 내용, 테스트 범위, 문서 수정 허용 여부, 완료 보고 형식.
- 이 구조를 갖추지 않은 지시는 Claude가 먼저 범위를 명확히 확인한 뒤 진행한다.

### Claude
- 지시서의 절대 규칙(예: "WorkflowEngine 변경 금지", "storage/** 수정 금지", "py -m src.main 실행 금지")을 문자 그대로 지킨다.
- 8개 이상 파일 수정, 신규 모듈 생성 등은 전체 파일 단위로 작성한다 (`.claude/skills/large_implementation.md`).

### Codex
- Claude의 변경분을 git status/diff로 검토한다.
- Compile과 (허용 시) workflow 실행을 담당한다.
- 최종 커밋 및 `PROJECT_SNAPSHOT.md`/`CHANGELOG.md`/`MODULE_STATUS.md` 반영을 담당한다.

### Compile
```powershell
py -m compileall src modules scripts
```
대부분의 Sprint에서 최소한 이 명령까지는 허용된다. 오류가 나오면 Sprint는 완료로 보고하지 않는다.

### workflow_completed
```powershell
py -m src.main
```
지시서가 명시적으로 금지하지 않은 경우에만 실행한다. 성공 기준은 `storage/workflow_results/99_final_result.json`의
`status`가 `workflow_completed`인지 여부뿐이다 — 개별 단계의 `fallback_used: true`는 정상이다
(`.ai/rules/workflow_protection.md` 참고).

### 문서 업데이트
- `PROJECT_SNAPSHOT.md`: 대부분 `scripts/update_project_snapshot.py`가 자동 생성. 수기 편집은 최소화.
- `CHANGELOG.md`: append-only. 날짜 헤더로 새 항목만 추가, 기존 항목은 삭제/수정하지 않는다.
- `MODULE_STATUS.md`: Sprint별 완료 기능을 "## Sprint N Completed" 형태로 누적한다.
- 각 Sprint 지시서가 이 문서들의 수정을 명시적으로 금지하는 경우, 문서는 건드리지 않고 다음 Sprint(주로 Codex 또는 별도 문서화 Sprint)로 넘긴다.

## Sprint 완료 정의

아래를 모두 만족해야 Sprint가 끝난 것으로 본다:

- Compile 성공 (또는 지시서가 요구하는 최소 테스트 통과)
- workflow 실행이 허용된 경우, `workflow_completed` 확인
- 지시서가 요구한 문서 갱신 완료 (또는 명시적으로 금지되어 건너뜀)
- 완료 보고에 변경/신규 파일, 테스트 결과, 남은 TODO, 주의사항 포함
