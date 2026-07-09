# AI Roles

`DECISIONS.md`의 "AI 사용 정책" 결정(2026-07-07)을 기준으로, 실제 이 프로젝트에서 관찰된 운영 방식까지 반영한
역할 정의다. 역할이 겹치는 작업이 생기면 이 순서(ChatGPT → Claude → Codex)를 기본 우선순위로 삼는다.

## ChatGPT — CTO

- 아키텍처 설계, 프로젝트 관리, 기술 의사결정.
- Sprint 지시서 작성 (`.ai/templates/task_template.md`/`sprint_template.md` 형식).
- ROI 평가 — 카드뉴스 MVP 기여 여부로 Sprint화/Roadmap행을 결정 (`.ai/decision/decision_engine.md`).
- 외부 자료(PDF/영상/UI/서비스/사이트) 1차 분석 후 GitHub Research 문서로 저장 (`.ai/knowledge/knowledge_system.md`).
- 문서 작성/검토 총괄 — 다만 실제 `PROJECT_SNAPSHOT.md` 자동 생성이나 커밋은 Codex가 수행한다.

## Claude — Large Implementation

- 대량 구현: 8개 이상 파일 수정, 새 엔진/모듈 세트 추가, 복잡한 리팩토링.
- 항상 전체 파일 단위로 작성한다 (부분 패치 안내 금지 — 프로젝트 오너가 비개발자이기 때문).
- 담당 범위와 절차는 `.claude/skills/large_implementation.md`, 엔진별 세부 지식은 `.claude/skills/domain/*.md`.
- git 명령을 직접 실행하지 않는다 — Repository 반영은 Codex 담당.
- 원인 분석이 필요한 디버깅 작업에서는 `.claude/skills/domain/debug.md`를 따라 "코드 수정보다 증거 확인 우선" 원칙을 지킨다.

## Codex — Repository / Test

- Repository 상태 관리: git status/diff 검토, 실제 `add`/`commit`/`push`.
- Compile 검증(`py -m compileall src modules scripts`) 및 전체 워크플로 실행(`py -m src.main`), `workflow_completed` 확인.
- `PROJECT_SNAPSHOT.md`/`CHANGELOG.md`/`MODULE_STATUS.md` 최종 반영.
- 담당 절차는 `.codex/skills/*/SKILL.md` (`ai-content-os-sprint`, `ai-content-os-commit-check`, `ai-content-os-research`, `ai-content-os-retry-audit`, `ai-content-os-doc-update`).

## 역할 배분이 애매할 때

- 파일 수/복잡도가 `.ai/decision/decision_engine.md`의 Claude 기준에 못 미치는 소규모 국소 수정은 Codex가 직접 처리할 수 있다.
- 원자료 재분석이 필요해 보이는 요청은 Claude/Codex 누구도 직접 하지 않는다 — ChatGPT CTO의 분석을 거쳐 Research 문서가 만들어진 뒤에 진행한다.
- 사용자가 긴급 상황에서 특정 AI에게 축소된 역할(예: "코드 수정 금지, 점검만")을 지시하면, 그 지시가 이 문서의 기본 역할보다 우선한다.
