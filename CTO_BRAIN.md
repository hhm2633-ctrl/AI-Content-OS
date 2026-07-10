# CTO_BRAIN.md

이 문서는 ChatGPT(CTO 역할)가 세션이 바뀌어도 프로젝트의 현재 아키텍처/상태에 대한 이해를
유지하기 위한 운영 요약이다. `PROJECT_OPERATING_SYSTEM.md`, `CLAUDE.md`, 최근 여러 Sprint의
"반드시 먼저 읽기" 목록에 이미 참조되어 왔으나 실제 파일이 없었다 — Sprint 14-0에서 Repository
문서 정합성 감사 중 이 사실을 확인하고 생성했다.

이 문서는 append-only가 아니다 (`DECISIONS.md`와 다름). Repository 상태가 바뀌면 이 문서도
갱신한다 — 여기 적힌 내용이 실제 코드와 어긋나면 항상 Repository(코드)가 기준이다.

---

## 현재 아키텍처 한 줄 요약

`WorkflowEngine`(`src/workflow_engine.py`)이 Protected Core 10단계 파이프라인을 실행한 뒤,
그 결과를 8개의 Intelligence Layer Engine이 소비해 재사용 가능한 지식/품질 신호를 만든다.
전체가 Fallback-first다 — 어떤 단계도 예외로 죽지 않고, 실패는 항상 데이터(`fallback_used`,
`reason`)로 기록된다.

## Protected Core (변경 금지, 순서 고정)

```text
TrendCollectorModule -> TopicEngineModule -> PatternEngineModule -> ResearchModule ->
ContentModule -> ImageStrategyModule -> ImagePromptModule -> ImageGenerationModule ->
CardNewsModule -> PublishingModule
```

## Intelligence Layer (Sprint 11-13, Publishing 이후 추가 단계, 서로 간 재정렬은 가능)

실제 `src/workflow_engine.py`의 실행 순서 (2026-07-10 기준, Sprint 13 재정렬 반영):

```text
KnowledgeModule -> TrendMemoryModule -> PerformanceScoreModule -> AuditEngineModule ->
LearningEngineModule -> AnalyticsEngineModule -> BrandDNAEngineModule -> CompetitorEngineModule
```

주의: `scripts/update_project_snapshot.py`가 자동 생성하는 `PROJECT_SNAPSHOT.md`의 "Current
WorkflowEngine" 줄은 이 순서와 다르게 나올 수 있다 (알려진 코드 버그, `MODULE_STATUS.md`
Sprint 14-0 항목 참고) — 이 문서와 실제 `src/workflow_engine.py`를 신뢰한다.

## Engine 인벤토리 (한 줄 요약)

- **Knowledge Engine** — Hook/CTA/Pattern/Layout/Brand/Workflow/Prompt Pattern/Tool/Image
  Strategy/Funnel 지식을 추출·점수화·랭킹·저장. Pattern/Content/CardNews/Audit/Learning이
  실제로 읽어 소비함(Sprint 13).
- **Trend Memory** — 최근 topic/hook/cta/layout/image_source 조합 기록, 반복 위험만 경고
  (생성 차단 없음). Audit Engine의 duplicate_check가 소비.
- **Performance Score** — hook/cta/layout/brand/image 5개 도메인 점수를 기존 신호로부터 합성.
  Audit/Learning/Analytics가 공유.
- **Audit Engine** — 9개 검사(hook/cta/pattern/layout/brand/image_strategy/duplicate/
  save_inducement/comment_inducement) 종합 `audit_score`. Competitor Comparison/Blind Spot
  Detection은 아직 Planning.
- **Learning Engine** — `internal_learning_score`(audit+performance+knowledge, 전부 실제
  로컬 값)가 임계치를 넘는 "좋은 실행"에서 고성과 Knowledge를 Learning Memory로 승격.
- **Analytics Engine** — 실제 SNS 지표 없음. Performance Score 이력과 비교한 정직한
  `quality_trend`(improving/declining/stable)만 제공. 가짜 성과 절대 생성 안 함.
- **Brand DNA Engine** — `config/brand_profile.json` + 실제 사용된 hook/cta/layout/color
  빈도 추적.
- **Competitor Engine** — Instagram 실시간 API 없음. `benchmark/*.md`(이미 CTO가 분석한 문서)
  파싱만으로 `storage/competitor/competitor_profiles.json` 생성.

## 절대 지켜야 할 것 (`PROJECT_OPERATING_SYSTEM.md`와 동일, 여기서도 반복)

- Protected Core 순서/구조 변경 금지.
- `workflow_completed`는 절대 `workflow_failed`로 후퇴하면 안 됨.
- `py -m src.main`만 사용, `python -m src.main` 금지.
- 명시적 지시 없이 동작하는 모듈/폴더/클래스/함수 삭제 금지.
- 실제 외부 신호를 흉내내는 가짜 데이터 생성 금지 (Sprint 13 Offline-First 원칙).
- Instagram API / Meta Graph API / access token / 실제 SNS 로그인·크롤링은 명시적 승인 없이
  구현하지 않는다 — `ROADMAP.md`의 "Requires External API" 섹션 확인 후 판단.

## AI 역할 분담 (요약, 상세는 `DECISIONS.md`/`.ai/rules/ai_roles.md`)

- **ChatGPT (CTO, 이 문서를 쓰는 주체)** — 아키텍처, 문서화, 외부 리서치 자료 분석, Sprint 설계.
- **Claude** — 대규모 구현, 광범위 리팩토링, 신규 Engine 구축.
- **Codex** — Repository 운영(git), compile/test, git diff 검토, 문서 자동 갱신 스크립트 실행.

## 알려진 리스크 / 감시 항목 (2026-07-10 기준, Sprint 15-3 갱신)

- ~~`scripts/update_project_snapshot.py`의 `module_lines` 하드코딩 문자열이 Sprint 13
  재정렬을 반영하지 못함~~ — Sprint 14-1에서 수정 완료 (`MODULE_STATUS.md` Sprint 14-1 항목
  참고). `PROJECT_SNAPSHOT.md`의 "Current WorkflowEngine" 줄은 이제 실제 코드 순서와 일치한다.
- Audit Engine의 Competitor Comparison/Blind Spot Detection은 Competitor Engine 실행 이력이
  더 쌓여야 의미 있게 동작함 — 아직 단일 실행 스냅샷만 있음.
- AI Planner: Contract(입력/출력/Schema/WorkflowEngine 연결 위치)는 Sprint 15-0에서
  `modules/ai_planner/`로 확정되고, Sprint 15-0A에서 구조적 결함(Planner 실행 위치보다
  나중에 생성되는 `pattern_result`/`knowledge_result`/`trend_memory_result`/
  `competitor_result`/`image_strategy_result`를 입력으로 요구하던 문제)을 Runtime
  Input(`trend_result`/`topic_result`/`brand_profile`)/Historical Input(`knowledge_history`/
  `trend_memory_history`/`competitor_history`/`brand_dna_history`/`performance_history`) 분리로
  수정했다. Sprint 15-1에서 실제 Decision Engine(`planner_decision_engine.py::
  PlannerDecisionEngine`)을 구현했다 - `PatternEngineModule`이 실제로 쓰는 규칙 기반 클래스를
  재사용해 `selected_pattern`/`selected_hook_strategy`/`selected_cta_strategy`를 계산하고,
  Historical Input을 실제로 정렬/필터링해 `knowledge_priority`/`competitor_reference`를
  만든다. LLM/외부 API/무작위 값 없음. Sprint 15-2에서 그 소비 방식에 대한 CTO 결정이
  내려졌다 - Planner 결과는 **강제 명령이 아니라 검증된 힌트**이며, 기존 Engine의 선택
  로직/fallback은 절대 대체하지 않는다. `consumer_contract.py::PlannerConsumerContract` +
  `planner_consumer_adapter.py::PlannerConsumerAdapter`가 이를 4단계 게이트(결과 유효성/
  planner_confidence 기준(0.5)/Consumer Engine 지원값/기존 안전 규칙 충돌 여부)로 구현했다.
  **Sprint 15-3(AI Planner 마지막 Sprint)에서 실제 통합을 완료했다** - `WorkflowEngine`이
  `AIPlannerModule`을 실제로 인스턴스화하고 `TopicEngineModule` 다음/`PatternEngineModule`
  이전에 `run()`을 호출하며(실패 시 예외 없이 `None` 반환, 하위 Engine 전부 기존과 동일하게
  동작), `PatternEngineModule`/`ContentModule`(`ContentPromptBuilder`)/`ImageStrategyModule`/
  `KnowledgeModule`이 각각 `PlannerConsumerAdapter`를 실제로 호출해 `planner_consumption.*`
  메타데이터를 기록한다. 실제 `py -m src.main` 실행으로 Planner 실행/Hint 적용/
  workflow_completed를 확인했다. AI Planner 관련 작업은 이제 완료됐다 - 더 이상 별도 감시
  항목이 아니다 (`.claude/skills/planning.md`, `docs/AI_PLANNER.md`은 별개 개념인
  "AI 작업 분담 라우팅"을 설명하며 `modules/ai_planner/`와 이름만 같음에 유의).
- Offline-First 원칙 위반 여부는 매 Sprint 시작 전 `ROADMAP.md`의 "Requires External API"
  섹션과 대조해 확인할 것.

## 이 문서 갱신 규칙

- Repository 상태가 바뀌면(Engine 추가/제거, WorkflowEngine 순서 변경, Planning→Implemented
  전환) 이 문서를 함께 갱신한다.
- 여기 적힌 내용과 실제 코드가 다르면 코드를 기준으로 이 문서를 고친다 (반대 아님).
- `DECISIONS.md`의 과거 결정을 이 문서가 뒤집을 수 없다 — 결정 변경은 항상 `DECISIONS.md`에
  새 항목을 추가하는 방식으로 한다.
