---
name: planning
description: Sprint 계획 규칙. Sprint 시작 전 ROI를 평가하고 카드뉴스 MVP를 우선한다. Claude는 설계/대량 구현을, Codex는 Repository/Compile/Test를 담당한다.
---

# Planning Skill

## Purpose

새 Sprint를 시작하기 전에 이 작업이 지금 해야 할 일인지, 어떤 AI가 담당해야 하는지를
판단하기 위한 스킬이다.

## Sprint 시작 전 ROI 평가

Sprint를 시작하기 전 항상 아래를 먼저 판단한다.

1. **카드뉴스 MVP 우선** — Instagram 카드뉴스 자동화 파이프라인(Trend → Topic → Pattern → Research → Content → Image → CardNews → Publishing)을 안정화/개선하는 작업이 항상 최우선이다.
2. **불필요 기능은 Roadmap으로 이동** — Shorts, Blog, SmartStore, 대시보드/분석, 영상 렌더러 등 `ROADMAP.md`의 후순위 마일스톤(M5, M6, Later Roadmap)에 해당하는 기능은 지금 구현하지 않고 `ROADMAP.md`에만 기록해 둔다. 명시적 승인 없이 범위를 확장하지 않는다.
3. 위 두 기준으로 판단이 애매하면 사용자에게 우선순위를 확인한다.

## 역할 분담

- **Claude**
  - 설계 (Architecture 판단, Sprint 범위 설계)
  - 대량 구현 (`large_implementation.md` 기준에 해당하는 작업)
- **Codex**
  - Repository 관리 (git 상태 정리, 실제 커밋)
  - Compile 검증 (`py -m compileall src modules scripts`)
  - Test / 전체 워크플로 실행 (`py -m src.main`) 및 `workflow_completed` 확인
  - Git Diff 검토 (Claude가 만든 변경분을 실제 커밋 전에 diff로 확인)
  - 문서 업데이트 (`PROJECT_SNAPSHOT.md`/`CHANGELOG.md`/`MODULE_STATUS.md`의 최종 반영, 대부분 `scripts/update_project_snapshot.py` 실행 결과로 갱신)

Claude는 지시받지 않는 한 `py -m src.main`을 직접 실행하지 않는다 (실행 여부는 항상 각 Sprint 지시를 따른다).

## Sprint 계획 체크리스트

- [ ] 이 작업이 카드뉴스 MVP에 직접 기여하는가?
- [ ] 8개 이상 파일 수정 / 새 모듈 생성이 필요한가 → Claude 담당 (`large_implementation.md`)
- [ ] 소규모 국소 수정인가 → Codex 담당이 더 적합할 수 있음
- [ ] `WorkflowEngine`, `workflow_completed`, 기존 모듈/폴더/클래스 이름을 건드리지 않는가?
- [ ] 이번 Sprint에서 수정 가능/금지 범위가 명확히 지정되었는가?
- [ ] 문서 수정 범위(PROJECT_SNAPSHOT.md/CHANGELOG.md/MODULE_STATUS.md 등)가 이번 Sprint 지시에 포함되어 있는가, 아니면 금지되어 있는가?

## 참고 문서

Sprint 계획 시 `architecture.md`에서 안내하는 순서(`PROJECT_MASTER.md` → `PROJECT_SNAPSHOT.md` → `MODULE_STATUS.md` → `ROADMAP.md`)로 현재 상태를 먼저 확인한 뒤 계획한다.
