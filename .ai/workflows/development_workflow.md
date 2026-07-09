# Development Workflow

AI-Content-OS의 모든 변경은 아래 흐름을 따른다. 각 단계는 앞 단계의 산출물을 신뢰하고,
자기 역할 밖의 일을 대신하지 않는다 (역할 상세는 `.ai/rules/ai_roles.md` 참고).

```text
사용자
  ↓  (비즈니스 우선순위, 승인/거절)
ChatGPT CTO
  ↓  (아키텍처 설계, ROI 판단, Sprint 지시서 작성, 외부 자료 분석 -> Research 문서화)
Claude
  ↓  (Sprint 지시서를 받아 대량 구현/리팩토링 수행, 전체 파일 단위로 작성)
Codex
  ↓  (Repository 상태 정리, compile, workflow 실행, workflow_completed 확인, 문서 최종 반영, 커밋)
GitHub
     (Single Source of Truth — 모든 AI와 개발 환경이 여기 기준으로 상태를 판단)
```

## 단계별 책임

### 사용자
- 우선순위와 방향을 정한다 (예: "카드뉴스 자동화가 먼저다").
- ChatGPT CTO/Claude/Codex의 제안 중 최종 승인을 결정한다.
- 컴퓨터 초보 기준으로 운영하므로, 모든 산출물은 사용자가 그대로 받아 쓸 수 있는 완결된 형태여야 한다 (`.claude/skills/large_implementation.md`의 "항상 전체 파일" 원칙).

### ChatGPT CTO
- 아키텍처/구조 설계, Sprint 범위와 절대 규칙을 정의해 지시서를 작성한다 (`.ai/templates/task_template.md`, `sprint_template.md` 사용).
- 외부 자료(PDF/영상/UI/서비스/사이트)를 분석해 GitHub Research 문서로 저장한다 (`.ai/knowledge/knowledge_system.md`).
- ROI가 낮은 요청은 Sprint로 만들지 않고 `ROADMAP.md`로 보낸다.

### Claude
- ChatGPT CTO의 지시서를 받아 실제 구현/리팩토링을 수행한다.
- 지시서의 "수정 가능"/"수정 금지" 범위를 문자 그대로 지킨다.
- git 명령을 직접 실행하지 않는다 (`add`/`commit`/`push` 없음) — Codex에게 넘긴다.
- 완료 후 변경 파일 목록, compile 결과, workflow 실행 여부(허용된 경우만), 주의사항을 보고한다.

### Codex
- Claude가 만든 변경분을 Repository 관점에서 검토한다 (git status/diff).
- `py -m compileall src modules scripts`, 필요 시 `py -m src.main`을 실행해 `workflow_completed`를 확인한다.
- `PROJECT_SNAPSHOT.md`/`CHANGELOG.md`/`MODULE_STATUS.md`를 최종 반영하고 커밋한다.

### GitHub
- 모든 AI와 개발 환경이 동일한 기준으로 삼는 Single Source of Truth (`DECISIONS.md`의 "프로젝트 관리" 결정 참고).
- 커밋되지 않은 변경은 "아직 존재하지 않는 것"으로 취급한다.

## 예외 처리

- 긴급 상황(예: Codex가 멈춘 상태)에서는 사용자가 Claude에게 "코드 수정 금지, 읽기 전용 점검만" 같은 축소된 역할을 임시로 지시할 수 있다. 이 경우 Claude는 평소 역할(구현)이 아니라 지시받은 축소 역할만 수행한다.
- Research 자료 처리처럼 흐름이 다른 특수 케이스는 `.ai/knowledge/knowledge_system.md`를 따른다.
