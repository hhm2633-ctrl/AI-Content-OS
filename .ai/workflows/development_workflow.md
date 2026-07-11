# Development Workflow

AI-Content-OS의 기본 변경 경로는 같은 프로젝트 컨텍스트 안에서 CTO 판단과 Codex 실행을 연결한다.

```text
사용자
  ↓  비즈니스 우선순위와 승인
ChatGPT Work CTO
  ↓  아키텍처, ROI, Research, Sprint 범위, 승인 게이트
Codex execution in the same workspace
  ↓  구현, 테스트, workflow_completed, 문서, Git
GitHub
     Single Source of Truth
```

## 사용자

- 우선순위와 외부 계정/API/비용/파괴적 작업의 최종 승인을 결정한다.
- 결과를 비개발자도 바로 확인할 수 있는 완결된 형태로 받는다.

## ChatGPT Work CTO

- 실제 저장소와 연결된 자료를 바탕으로 아키텍처, ROI, Sprint 범위와 보호 계약을 결정한다.
- 외부 자료를 분석해 Research 문서로 저장한다.
- 관련 프로젝트 스킬을 선택하고 구현·검증 상태를 끝까지 추적한다.
- ROI가 낮거나 선행조건이 없는 요청은 `ROADMAP.md`로 보낸다.

## Codex Execution

- Work CTO의 범위와 보호 계약 안에서 구현·리팩토링을 수행한다.
- 위험 기반 테스트, compile, 전체 workflow, 문서 동기화와 Git을 담당한다.
- 큰 작업도 작은 검증 단계로 나누며 사용자 루프를 유지한다.
- `storage/**`, `.env`, 로그와 생성 산출물을 커밋하지 않는다.

## Claude (Optional)

- 사용자가 명시적으로 맡기거나 독립 검토가 필요한 경우에만 참여한다.
- Codex MCP를 기본 호출하지 않는다.
- 구현 또는 읽기 전용 검토 역할을 지시받은 범위 안에서 수행한다.
- 결과는 Work/Codex가 저장소 관점에서 다시 검증한다.

## GitHub

- 커밋된 코드와 문서의 Single Source of Truth다.
- 기능 커밋과 운영체계/도구 재편 커밋을 분리한다.

## 특수 흐름

- 외부 자료 처리는 `.ai/knowledge/knowledge_system.md`를 따른다.
- Sprint는 `.codex/skills/ai-content-os-sprint-manager/`를 따른다.
- 최종 QA와 커밋 검수는 `ai-content-os-qa`, `ai-content-os-commit-check`를 사용한다.
