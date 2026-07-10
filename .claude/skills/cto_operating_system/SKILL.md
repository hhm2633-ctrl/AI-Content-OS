---
name: cto_operating_system
description: 이 프로젝트의 최상위 진입점 스킬. 어떤 작업이든 시작하기 전에 PROJECT_OPERATING_SYSTEM.md와 Mandatory Reading Order를 먼저 따르게 한다.
---

# CTO Operating System Skill

## Purpose

이 스킬은 AI-Content-OS에서 Claude가 어떤 작업(Sprint, 디버깅, 리서치 반영, 단발성 요청)을
시작하든 가장 먼저 확인하는 진입점이다. 다른 모든 `.claude/skills/*` 파일보다 먼저 읽는다.

이 스킬 자체는 새로운 규칙을 만들지 않는다 — 프로젝트 루트의 **`PROJECT_OPERATING_SYSTEM.md`**가
진짜 규칙(운영 원칙, AI 역할 분담, Protected Core/Intelligence Layer 구분, Offline-First 원칙,
Absolute Rules)을 담고 있는 단일 진실 소스(single source of truth)이며, 이 스킬은 그 문서로
가는 다리 역할만 한다.

## 반드시 먼저 할 일

1. **`PROJECT_OPERATING_SYSTEM.md`를 읽는다.** 이 문서의 "Mandatory Reading Order"를 그대로
   따른다:
   1. `PROJECT_OPERATING_SYSTEM.md`
   2. `CTO_BRAIN.md` (있는 경우)
   3. `PROJECT_MASTER.md`
   4. `PROJECT_SNAPSHOT.md`
   5. `MODULE_STATUS.md`
   6. `ROADMAP.md`
   7. `CURRENT_TASK.md`
   8. `.claude/skills/*` (작업 범위에 맞는 나머지 스킬)
2. Repository 상태가 메모리보다 항상 우선한다. 문서와 실제 코드/storage 결과가 다르면
   Repository를 먼저 분석한다.
3. 사용 가능한 MCP(특히 Codex MCP)를 먼저 확인한다.
4. 외부 API(Instagram API, Meta Graph API, access token, 실제 SNS 로그인/크롤링)가 있어야만
   가능한 기능은 억지로 구현하지 않는다 — `ROADMAP.md`의 "Requires External API" 섹션에
   있는지 먼저 확인하고, 없으면 그 섹션으로 옮긴다 (`PROJECT_OPERATING_SYSTEM.md`의
   "Offline-First Principle" 참고).
5. 항상 Repository 성장과 ROI를 최대화하는 방향으로 작업 범위를 판단한다
   (`.claude/skills/planning.md`의 Sprint ROI 평가와 함께 사용).

## 이 스킬이 다른 스킬과 관계

- `.claude/skills/architecture.md`가 프로젝트 상태를 읽는 구체적인 절차(WorkflowEngine 구조,
  Windows 실행 규칙 등)를 다룬다면, 이 스킬은 그보다 한 단계 위에서 "가장 먼저
  `PROJECT_OPERATING_SYSTEM.md`부터 본다"는 진입 절차를 강제한다.
- Protected Core(`WorkflowEngine`의 10개 핵심 모듈)와 Intelligence Layer(Knowledge/Trend
  Memory/Performance Score/Audit/Learning/Analytics/Brand DNA/Competitor Engine)의 구분,
  그리고 각 Engine이 갖춰야 할 표준 구조(Core/Storage/History/Score/Fallback/Interface)는
  `PROJECT_OPERATING_SYSTEM.md`의 "Protected Core vs. Intelligence Layer"를 따른다 —
  `.claude/skills/large_implementation.md`의 Engine Rule과 동일한 내용이다.
- 새로운 Research 자료 반영은 `.claude/skills/research.md`를, Sprint 범위 판단은
  `.claude/skills/planning.md`를, 완료 후 점검은 `.claude/skills/review.md`를 따른다 —
  이 스킬은 그 전 단계(무엇을 먼저 읽어야 하는가)만 담당한다.

## Not This Skill

- 프로젝트 규칙 자체(무엇이 허용/금지되는지)는 여기 아니라 `PROJECT_OPERATING_SYSTEM.md`에
  있다. 규칙이 궁금하면 이 스킬이 아니라 그 문서를 인용한다.
- WorkflowEngine의 실제 모듈 순서/구조 세부사항은 `.claude/skills/architecture.md`를 따른다.
