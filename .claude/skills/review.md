---
name: review
description: Claude 작업 완료 후 체크리스트. Compile, workflow_completed, 문서 갱신 여부를 확인한다. 최종 Repository 반영(커밋)은 Codex가 담당한다.
---

# Review Skill

## Purpose

Claude가 Sprint/작업을 마무리하기 전에 확인해야 할 최소 체크리스트다.
이 체크리스트는 각 Sprint 지시의 "테스트"/"수정 금지" 범위를 항상 우선한다 —
예를 들어 "py -m src.main 실행 금지"라고 지시받았다면 워크플로 실행은 건너뛰고,
그 사실을 보고서에 명시한다.

## 체크리스트

- [ ] **Compile**: `py -m compileall src modules scripts` 실행 결과가 오류 없이 성공했는가? (Sprint 지시에서 이 명령까지만 허용하는 경우가 많다)
- [ ] **workflow_completed**: 이번 Sprint에서 `py -m src.main` 실행이 허용되었다면, `storage/workflow_results/99_final_result.json`의 `status`가 `workflow_completed`인지 확인했는가? 실행이 금지되었다면 "실행하지 않음"을 명시했는가?
- [ ] **PROJECT_SNAPSHOT.md**: 이번 Sprint에서 이 파일 수정이 허용/요구되었는가? 금지되었다면 건드리지 않았는가?
- [ ] **CHANGELOG.md**: 위와 동일하게 이번 Sprint의 허용 범위를 따랐는가?
- [ ] **MODULE_STATUS.md**: 위와 동일.
- [ ] 변경 파일/추가 파일 목록이 실제 작업 범위(수정 가능/수정 금지)와 정확히 일치하는가?
- [ ] `.env`, API Key, `storage/**` 런타임 산출물을 출력하거나 커밋 대상으로 포함하지 않았는가?

## 문서 갱신 원칙

- `PROJECT_SNAPSHOT.md`는 대부분 `scripts/update_project_snapshot.py`가 `py -m src.main` 실행 후 자동 생성한다. Claude가 수기로 전체를 다시 쓰지 않는다 — Sprint 지시가 명시적으로 허용한 경우에만 최소한으로 보정한다.
- `CHANGELOG.md` / `MODULE_STATUS.md`는 Sprint 지시가 명시적으로 요청한 경우에만 수정한다. 대부분의 Sprint는 "문서 수정 금지" 목록에 이 파일들을 포함시키므로, 기본값은 "수정하지 않는다"이다.

## 최종 Repository 반영

- Claude는 `git add` / `git commit` / `git push`를 수행하지 않는다.
- 최종 Repository 반영(커밋, 커밋 메시지 작성, 실제 실행 검증)은 Codex가 담당한다.
- Claude의 역할은 변경 파일 목록과 검증 결과를 명확히 보고해, Codex가 이어서 커밋/실행할 수 있도록 준비하는 것까지다.

## 완료 보고 형식

작업 완료 보고에는 최소한 아래가 포함되어야 한다.

- 변경 파일 / 추가 파일 목록
- Compile 결과
- Workflow 실행 여부 (실행했다면 결과, 안 했다면 왜 안 했는지)
- 남은 TODO
- Codex(또는 사용자)가 주의해야 할 점
