---
name: large_implementation
description: Claude가 담당하는 작업 범위(대량 구현, 8개 이상 파일 수정, 복잡한 리팩토링, 새 모듈 생성)를 정의한다. 항상 전체 파일 기준으로 작성하고 부분 수정 안내를 하지 않는다.
---

# Large Implementation Skill

## Purpose

AI-Content-OS에서 "이 작업은 Claude가 맡아야 하는가"를 판단하고,
Claude가 맡는 경우 어떤 방식으로 작업해야 하는지를 정의한다.

## Claude 담당 작업

아래 조건 중 하나라도 해당하면 Claude가 담당한다.

- 8개 이상 파일을 수정해야 하는 작업
- 대량 구현 (새로운 엔진/모듈 세트를 한 번에 추가하는 Sprint)
- 복잡한 리팩토링 (여러 모듈에 걸친 구조 변경)
- 새 모듈 생성 (예: `modules/<engine>/*.py` 신규 디렉터리)
- 파일 전체 수정본 작성이 필요한 경우

이 기준에 못 미치는 작고 국소적인 수정(설정값 조정, 오탈자 수정, 로그 문구 변경 등)은
Codex가 처리하는 것이 더 적합하다 (`ai-content-os-sprint` 스킬의 Sprint Decision Rule 참고).

## 작업 방식 원칙

프로젝트 오너는 개발자가 아닌 초보자이므로, 항상 아래 방식을 따른다.

- **부분 수정 금지**: "이 줄만 바꾸세요", "이 함수의 이 부분만 고치세요" 같은 부분 패치 안내를 하지 않는다.
- **항상 전체 파일 기준**: 새 파일은 전체 내용을 작성하고, 기존 파일 수정은 실제 코드 편집 도구(Edit/Write)로 파일 전체를 일관된 상태로 만든다. 사용자가 직접 코드를 짜깁기하도록 요구하지 않는다.
- 여러 파일에 걸친 작업이라도, 각 파일은 그 자체로 완결된 상태여야 한다 (절반만 구현된 함수, TODO만 남긴 placeholder 금지).
- **Repository 반영은 하지 않음**: Claude는 구현/작성까지만 담당한다. `git add`/`commit`/`push`는 수행하지 않는다 (Codex 담당, `planning.md`/`review.md` 참고).

## 함께 적용되는 규칙

- `architecture.md`의 WorkflowEngine 보호 규칙을 항상 유지한다.
- `refactoring.md`의 구조 유지 규칙을 항상 유지한다.
- 작업 완료 후에는 `review.md`의 체크리스트를 따른다.

## Not This Skill

- 리서치 자료 반영은 `research.md`를 따른다.
- Sprint 범위/ROI 판단은 `planning.md`를 따른다.

---

# AI-Content-OS Engine Rule

모듈 하나를 구현했다고 완료가 아니다.

Engine은 반드시 아래를 포함해야 한다.

- Core
- Storage
- History
- Index
- Score
- Cache
- Retry
- Fallback
- Interface
- Documentation
- Workflow Integration

위 항목이 없으면 Engine Completed가 아니다.

항상 다른 Engine에서 재사용 가능한 구조로 만든다.

현재 기능만 구현하지 않는다.

6개월 뒤 재사용될 구조를 먼저 설계한다.
