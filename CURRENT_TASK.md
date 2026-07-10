# CURRENT_TASK.md

# AI-Content-OS
Current Version: Sprint 13 complete (Intelligence Layer operational)
Current Phase: Intelligence Layer Operational / Documentation Alignment
Status: In Progress

---

# Current Objective

카드뉴스 MVP 파이프라인(Protected Core)과 그 위의 Intelligence Layer(Knowledge/Trend Memory/
Performance Score/Audit/Learning/Analytics/Brand DNA/Competitor Engine, Sprint 11-13에서 구축)가
모두 `workflow_completed` 상태로 동작 중이다.

현재는 새 Engine을 계속 늘리는 것보다, 문서-저장소 정합성 유지와 M2(Content Engine 고도화) 등
기존 파이프라인 품질 개선이 우선이다. 자세한 이력은 `MODULE_STATUS.md`(Sprint별 완료 내역),
현재/향후 계획은 `ROADMAP.md`를 따른다.

---

# Current Sprint

Sprint 14 - Documentation Alignment (Sprint 14-0 완료: `PROJECT_MASTER.md`/`PROJECT_SNAPSHOT.md`/
`MODULE_STATUS.md`/`ROADMAP.md`/`CURRENT_TASK.md`/`CTO_BRAIN.md`를 Repository 코드 상태와
일치시킴)

기간

2026-07-10 ~

---

# Primary Goal

AI 기반 콘텐츠 운영 시스템의 핵심 구조(Protected Core)를 안정적으로 유지하면서, Intelligence
Layer가 실제 로컬 데이터를 기반으로 계속 더 정확하게 동작하도록 고도화한다.

---

# Status Summary

## 완료됨 (더 이상 진행 중인 작업 아님)

- [x] GitHub Repository 생성
- [x] AI_CONTEXT.md 작성
- [x] PROJECT_BIBLE.md 작성
- [x] SYSTEM_ARCHITECTURE.md 작성
- [x] WORKFLOW_SPEC.md / docs/WORKFLOW.md 작성
- [x] docs/MASTER_JSON.md 작성
- [x] Protected Core 10단계 파이프라인 구축 및 운영 (Trend -> Topic -> Pattern -> Research ->
      Content -> Image Strategy -> Image Prompt -> Image Generation -> CardNews -> Publishing)
- [x] Intelligence Layer 8개 Engine 구축 (Knowledge/Trend Memory/Performance Score/Audit/
      Learning/Analytics/Brand DNA/Competitor Engine) — Sprint 11-13
- [x] Offline-First 원칙 확립 (Sprint 13): Instagram/Meta API 없이 로컬 데이터만으로 동작,
      가짜 성과 데이터 생성 금지
- [x] Claude Developer Kit + CTO Operating System 진입점 스킬 (`PROJECT_OPERATING_SYSTEM.md`,
      `.claude/skills/cto_operating_system/SKILL.md`)

## Legacy Migration (superseded)

과거에 계획했던 "기존 자료(Claude/Gemini/Manus/Notion/PDF/Python 코드/HTML Template/Prompt 모음)를
수집 → 분석 → 분류 → 리팩토링 → 편입" 절차는 이후 `DECISIONS.md`(2026-07-09, "External Research
Handling")와 `.claude/skills/research.md`로 대체되었다: 외부 자료는 ChatGPT CTO가 먼저 분석해
`docs/`, `docs/RESEARCH/`에 저장하고, Claude/Codex는 그 분석 결과만 소비하며 원자료를 재분석하지
않는다. 별도의 마이그레이션 체크리스트로 다시 진행하지 않는다.

---

## Architecture

실제 구현된 구조 (계획이 아니라 현재 상태):

- Protected Core: `src/workflow_engine.py::WorkflowEngine`
- Intelligence Layer: `modules/knowledge_engine/`, `modules/trend_memory/`,
  `modules/performance_score/`, `modules/audit_engine/`, `modules/learning_engine/`,
  `modules/analytics_engine/`, `modules/brand_dna_engine/`, `modules/competitor_engine/`
- Renderer: `modules/card_news/`
- Publishing Engine: `modules/publishing/`

세부 모듈 구성과 Engine별 알려진 gap은 `.claude/skills/domain/*.md`와 `MODULE_STATUS.md`를 따른다.

---

## Current Priority

★★★★★

Instagram 카드뉴스 자동화 (Protected Core 안정성 유지)

이 시스템이 완성되면 동일한 엔진으로

- Shorts
- Blog
- Smart Store
- Coupang

까지 확장한다. (`ROADMAP.md` M6)

---

# Current Focus

현재는

문서-Repository 정합성

M2 Content Engine 고도화

Intelligence Layer의 실제 로컬 데이터 소비 정확도

를 우선한다. 구조를 깨뜨리는 새로운 대형 리팩토링은 지금 우선순위가 아니다.

---

# Next Tasks

`MODULE_STATUS.md`의 "Next" 섹션과 `ROADMAP.md`를 그대로 따른다. 요약:

1. `scripts/update_project_snapshot.py`의 `module_lines` 하드코딩 문자열을 Sprint 13 순서에
   맞게 수정 (코드 변경 필요, 이번 Sprint 14-0 범위 아님)
2. M2 Content Engine 고도화
3. ContentPromptBuilder / Content Intelligence / CardNews 헬퍼에 대한 focused unit test 추가
4. Audit Engine의 Competitor Comparison + Blind Spot Detection (Competitor Engine 이력 축적 후)
5. AI Planner 설계/구현 (유일하게 남은 Planning 상태 Engine)
6. Source Health / Collector Statistics 대시보드
7. `ROADMAP.md` "Requires External API" 섹션 항목들은 명시적 승인 전까지 구현하지 않음

---

# Reminder

항상

문서 → 설계 → 코드 → 테스트 → CHANGELOG

순서로 진행한다.

작업 시작 전에는 `PROJECT_OPERATING_SYSTEM.md`의 Mandatory Reading Order를 따른다.
