# Sprint 템플릿 (Sprint Template)

`task_template.md`가 개별 작업지시서 형식이라면, 이 템플릿은 **Sprint 단위 계획**을 세울 때 쓴다
(여러 작업지시서로 나뉘기 전, "이번 Sprint가 왜 필요한가"를 정리하는 단계).

```markdown
# Sprint: [이름]

## 배경 / 문제
지금 무엇이 부족하거나 문제인가? (`MODULE_STATUS.md`의 Next, 사용자 요청, 관측된 실패 등 근거를 명시)

## ROI 평가
- 카드뉴스 MVP에 직접 기여하는가? (`.ai/decision/decision_engine.md` 기준)
- 그렇지 않다면 왜 지금 해야 하는가, 또는 ROADMAP.md로 보내야 하는가?

## 범위
- 이번 Sprint에서 다루는 것
- 이번 Sprint에서 **다루지 않는 것** (다음 Sprint/Roadmap으로 명시적으로 분리)

## 작업 분해
1. [작업 1] — 담당: Claude/Codex, 예상 파일 수/복잡도
2. [작업 2] — ...

담당 AI 배정 기준은 `.ai/decision/decision_engine.md`(파일 수/복잡도/위험도)를 따른다.

## 절대 규칙 (Sprint 공통)
- WorkflowEngine 변경 여부
- workflow_completed 보호 여부
- storage/**, .env 접근 여부
- 문서 수정 허용 범위

## 완료 조건
- [ ] Compile 통과
- [ ] (허용 시) workflow_completed 확인
- [ ] 문서 갱신 (허용된 범위만)
- [ ] 완료 보고 작성

## 검증 방법
- `py -m compileall src modules scripts`
- (허용 시) `py -m src.main` → `storage/workflow_results/99_final_result.json`의 `status` 확인
- 그 외 이번 Sprint 특화 검증(예: 특정 필드가 결과 JSON에 존재하는지)
```

## 사용 시 주의사항

- "범위"에서 "다루지 않는 것"을 명시하지 않으면, 다음 Sprint에서 "이미 했다고 생각했는데 안 되어 있다"는
  혼란이 생긴다 — 항상 명시적으로 경계를 긋는다.
- Sprint 하나가 8개 이상 파일을 건드릴 것 같으면 처음부터 Claude 담당으로 계획한다 (`.ai/decision/decision_engine.md`).
- 여러 Sprint에 걸쳐 같은 이름의 결과물(예: "Claude Skill System")을 계속 만들게 되는 경우, 새로 만들지 말고
  기존 것을 버전업(v2, v3...)하는 방식을 우선 검토한다 — 중복 제거 원칙.
