# CURRENT_TASK.md

# AI-Content-OS
Current Version: CardNews Operational Complete (M7 + M8 + M7-next, 2026-07-11)
Current Phase: Post-CardNews expansion planning
Status: CardNews production path closed; Shorts Phase 0 architecture may proceed in an isolated Claude lane

---

# Current Objective

카드뉴스 MVP 파이프라인(Protected Core)과 그 위의 Intelligence Layer(Knowledge/Trend Memory/
Performance Score/Audit/Learning/Analytics/Brand DNA/Competitor Engine, Sprint 11-13에서 구축)가
모두 `workflow_completed` 상태로 동작 중이다. 2026-07-11 Instagram Intelligence Phase에서
Competitor Learning Engine(Sprint 18)과 Instagram Research -> Competitor Learning -> Knowledge
Database -> Brand DNA -> Pattern -> Content **Internal Quality Feedback Loop**(pre-publish,
내부 `quality_score` 기반 - 실제 Instagram 성과 아님, `DECISIONS.md` 2026-07-11 참고)가
완성됐고, 이어서 같은 날 **CardNews Intelligence(Phase M7) + CardNews Production Quality
(Phase M8)**가 완료됐다: Evidence Selection(주제 관련성 + 저작권 render guard),
Social Proof 안전 선정(마스킹/PII/의견 라벨링), Story Flow, Debate/CTA 충돌 방지,
Typography 계층, Human Visual Rhythm, Mobile Readability + Contrast guard, Source
Attribution, Production Quality QA 10개 항목 — 기존 `CardNewsModule` Pillow Renderer 위에
전부 확장 방식으로 연결됐다(새 Engine/Renderer 없음, `src/workflow_engine.py` diff 없음).
자세한 내용은 `MODULE_STATUS.md`의 "Phase M7 + Phase M8" 항목 참고.

CardNews 실제 결과물 운영 검증까지 완료됐다. 전용 위험 기반 테스트 38개, compile,
`workflow_completed`, `card_news_completed`, `publishing_ready`, QA 0.85/pass, 렌더링 fallback
없음, PNG 4장 직접 시각 검수를 확인했다. 안전한 기존 레이아웃 대체는 렌더링 실패와 분리해
진단하고, 글자 수 보호로 의도적으로 생략한 Debate는 결함으로 감점하지 않는다.

다음 단계는 기존 카드뉴스 경로를 건드리지 않는 독립 작업으로 진행한다. Claude는 Shorts
Phase 0 아키텍처/계약 초안만 작성하고, Work/Codex는 저장소 통합·검증과 다음 실행 우선순위를
관리한다. 자세한 이력은 `MODULE_STATUS.md`, 향후 계획은 `ROADMAP.md`를 따른다.

---

# Current Sprint

Sprint 15 - AI Planner Architecture

- Sprint 15-0 완료: `modules/ai_planner/` Contract 초안 확정 — 입력(`PlanningContext`)/
  출력(`planning_result_schema`)/Schema/`WorkflowEngine` 연결 위치 정의.
- Sprint 15-0A 완료: Sprint 15-0 Contract의 구조적 결함(Planner 위치보다 나중에 생성되는
  `pattern_result`/`knowledge_result`/`trend_memory_result`/`competitor_result`/
  `image_strategy_result`를 입력으로 요구) 수정. Planner Input을 Runtime Input
  (`trend_result`/`topic_result`/`brand_profile`, 현재 실행에서 Planner 이전에 실제 존재)과
  Historical Input(`knowledge_history`/`trend_memory_history`/`competitor_history`/
  `brand_dna_history`/`performance_history`, 기존 Engine Interface로 읽는 과거 축적 데이터)로
  분리. 실제 Decision Engine과 `WorkflowEngine` 실행 연결은 여전히 없음. Codex MCP 독립 검수 포함.
- Sprint 15-1 완료: `modules/ai_planner/planner_decision_engine.py::PlannerDecisionEngine` 구현.
  `PatternEngineModule`이 실제로 쓰는 것과 동일한 규칙 기반 클래스(KeywordWeightEngine/
  TopicClassifier/TopicCluster/ConfidenceScorer/PatternSelector/HookSelector/CTASelector)를
  Runtime Input에 재사용해 `selected_pattern`/`selected_hook_strategy`/`selected_cta_strategy`를
  계산하고, Historical Input을 정렬/필터링해 `knowledge_priority`/`competitor_reference`를
  만든다. Brand DNA 이력이 충분(5회 이상)하면 hook/cta를 실제 브랜드 선호도로 override.
  LLM/외부 API/무작위 값 없음. `WorkflowEngine` 실행 연결은 여전히 없음(이번 Sprint 범위 밖).
  Codex MCP 독립 검수 포함.
- Sprint 15-2 완료: `modules/ai_planner/consumer_contract.py::PlannerConsumerContract` +
  `planner_consumer_adapter.py::PlannerConsumerAdapter` 구현. Planner 결과는 강제 명령이
  아니라 검증된 힌트라는 CTO 결정을 4단계 게이트(결과 유효성/confidence 기준/Consumer
  Engine 지원값/기존 안전 규칙 충돌 여부)로 구현. 기존 Engine의 선택 로직/fallback은
  절대 대체하지 않으며, 어떤 실제 Engine도 아직 이 계층을 호출하지 않는다(이번 Sprint는
  소비 "규칙"만 구현). `WorkflowEngine` 실행 연결은 여전히 없음. Codex MCP 독립 검수 포함.
- Sprint 15-3 완료 (AI Planner 마지막 Sprint): `WorkflowEngine`에 `AIPlannerModule`을
  실제로 연결 — `TopicEngineModule` 다음, `PatternEngineModule` 이전에 실행되며, 실패하면
  예외 없이 `None`을 반환해 하위 Engine 전부가 기존과 동일하게 동작한다.
  `PatternEngineModule`/`ContentModule`(`ContentPromptBuilder`)/`ImageStrategyModule`/
  `KnowledgeModule`이 각각 `PlannerConsumerAdapter`를 실제로 호출해 pattern/hook·cta·
  content_strategy/image content_type/knowledge_priority Hint를 검증 후 조건부 적용하고,
  `planner_consumption.*` 메타데이터를 기록한다. CardNews/Publishing은 그 메타데이터를
  요약해 기록만 할 뿐 렌더링/게시 로직은 바꾸지 않는다. 기존 Engine의 선택 로직/fallback은
  하나도 제거되지 않았으며, 실제 `py -m src.main` 실행으로 Planner 실행/Hint 적용/
  workflow_completed/CardNews 4장/Publishing ready를 모두 확인했다. 신규
  `tests/test_workflow_planner_integration.py`(14개) + 기존 `test_ai_planner_*`(92개)/
  `test_content_output_*`(33개) 전부 통과. Codex MCP 독립 검수 포함.

Sprint 16 - Intelligence Feedback Safety

- Sprint 16-0 완료: 새 Engine 생성 없음. Feedback Audit으로 실제 Self Reference/Circular
  Feedback 2건을 발견해 수정 — (1) Brand DNA→Planner: `pattern_plan.hook_type`/`cta_type`가
  Planner Hint의 영향을 받을 수 있는데도 `BrandDNAStorage`의 `total_observations`를 그대로
  override 근거로 썼던 문제 → `planner_influenced_observations` 카운터를 신설해
  `PlannerDecisionEngine`이 "독립 관찰 수"만 근거로 삼도록 수정. (2) Knowledge→Planner:
  Sprint 15-3의 "Priority Boost"가 실제 `overall_score`를 영구히 부풀려 저장해 다음 실행의
  Planner가 자신의 과거 힌트를 실제 성과처럼 재사용하던 문제 → score 변형을 완전히
  제거하고 순수 진단용 `planner_priority_preview` 필드로 대체(`top_knowledge`는 전혀
  영향받지 않음). Analytics에 `measurement_metadata`(runtime/historical/estimated/
  local_quality 출처 구분), Learning에 `evidence_metadata`+`planner_evidence_used`(항상
  False - Planner를 아예 참조하지 않음을 검증), Performance Score에 `planner_used`/
  `planner_helpful`/`planner_rejected`/`planner_reason`, Content에 `engine_influence`
  (planner/knowledge/brand/pattern) 추가. 공통 `modules/common/metadata_standard.py`로
  중복 구조 제거. 신규 테스트 42개(`test_intelligence_feedback_safety.py`), 전체 테스트
  186개(`py -m unittest discover -s tests -v`) 전부 통과, 기존 테스트 삭제 없음. Codex MCP
  독립 검수 포함.

Sprint 18 + Instagram Intelligence Phase (2026-07-11, 완료)

- Sprint 18 완료: 신규 `modules/competitor_learning/` Engine — `modules/instagram_research/`의
  이미 수집된 게시물을 읽기 전용으로 읽어(그 모듈은 diff 없음) Knowledge Database
  (`storage/knowledge/knowledge_database.json` + 5개 통계 파일)와
  `storage/dashboard/daily_learning_report.json`을 생성. `WorkflowEngine.run()`에는 연결하지
  않음(독립 실행형 배치 단계). 131개 테스트, Codex MCP 독립 검수 포함(1차 BLOCK -> 수정 ->
  APPROVED).
- Instagram Intelligence Phase 1/2 완료: Instagram Research -> Competitor Learning -> Knowledge
  Database -> Brand DNA -> Pattern -> Content Closed Loop 연결. Pattern Engine이 Knowledge
  (+0.05)/Competitor Learning(+0.03)/Brand DNA(+0.02)/Learning Engine(+0.025) 4개 소스를 참고해
  confidence만 보정(선택값 자체는 불변). `storage/history/content_performance_history.json`
  신설, Knowledge Feedback(`score.confidence` ±0.05 조정, 다른 필드/다른 entry는 불변),
  `daily_learning_report.json`에 `top_performing_pattern`/`weakest_pattern`/`learning_delta`/
  `knowledge_delta`/`brand_dna_change`/`brand_dna_delta` 추가.
- Instagram Intelligence Phase 3(최종 검증) 완료: 실제 결함 2건 발견 및 수정 — (1)
  `content_id`가 기록 시각을 섞어 만들어져 dedup이 전혀 작동하지 않던 버그(→ title/caption
  기반으로 수정, `record_once()`/`_apply_knowledge_feedback()`의 중복 방지 실제로 작동 확인),
  (2) `quality_score`/`learning_delta` 등이 실제 Instagram 성과로 오인될 수 있는 라벨링 누락(→
  `INTERNAL_QUALITY_PROXY_METADATA` 전 결과 구조에 명시). 22개 위험 회귀 테스트 추가, 전체
  444개 테스트 통과, `py -m src.main` → `workflow_completed`(CardNews/Publishing 상태 불변
  확인), Codex MCP 독립 검수(1차 BLOCK — `_fallback_result()` 메타데이터 누락 — 수정 →
  APPROVED).

Phase M7 (CardNews Intelligence) + Phase M8 (CardNews Production Quality) (2026-07-11, 완료)

- Evidence Selection + 오사용 방지 보정: `evidence_selector.py`가 `candidate_found`/
  `topic_relevant`(최소 2개 용어 일치 + 점수 0.34 이상)/`render_allowed`(허용된
  `copyright_status`만)/`asset_role == "topic_evidence"` 4개 게이트를 모두 통과해야
  `available: true`. Instagram Research 스크린샷은 항상 `competitor_reference`로 분류되어
  카드 배경에 자동 적용되지 않음. `card_news_module.py::_apply_evidence_asset`이 이중 방어.
- Social Proof 안전 선정: `caption_text`/`visible_*_text`(개수)는 댓글로 오인하지 않고,
  실제 `comment_text`/`reply_text`/`reaction_text`/`quote_text` 필드만 후보로 인정.
  계정명 마스킹, PII 스크럽, `is_opinion`/라벨 부여. 실제 댓글 데이터가 없어
  `available: false`가 정직한 현재 상태.
- Story Flow + Debate/CTA 충돌 방지: 서사 role은 실제 슬라이드 수를 넘지 않고, CTA가
  이미 댓글 유도 목적이거나 글자 수 예산을 초과하면 Debate 질문을 추가하지 않으며
  원본 CTA 문구는 항상 보존.
- Typography + Human Visual Rhythm 실제 렌더링 반영: `typography_rules.py`의 role별
  규칙(폰트 크기/줄 수/줄 간격)이 `_plan_text_layout()`을 거쳐 실제 PNG 폰트 크기·줄
  수에 반영됨. `visual_rhythm_selector.py`가 서사 role 기준으로 7개 시각 스타일을
  결정론적으로 배정하고, `quote_card`/`comparison`은 실제 데이터가 없으면 안전한
  기본 스타일로 fallback.
- Contrast + Mobile Readability guard: 라이트 모드 subtitle 대비가 실측 4.42(WCAG AA
  4.5 미달)로 확인되어 (120,120,120) → (112,112,112)로 최소 수정, 실측 4.95로 통과.
  `render_constants.py`가 Renderer/Checker 공용 단일 진실 소스.
  Source Attribution은 실제 적용+허용된 evidence에만 표시(URL 미노출).
- Production Quality QA 10개 항목 추가, 총점 100 유지, 조건부 채점(데이터 부재는
  무감점) 원칙 유지.
- 최종 검증 중 실제 PNG를 직접 열어본 결과 실결함 발견 및 수정: 번호 매긴 목록("1." "2.")을
  문장 경계로 오인해 항목 번호만 남고 내용이 사라지는 정규식 버그(`SENTENCE_SPLIT_PATTERN`)
  수정. Codex MCP 리뷰가 추가로 지적한 "최후 수단 글자 단위 절단에 말줄임표(…) 없음"도 수정.
- 검증: `tests/test_card_news_production_quality.py`(35개, 위험 기반) 포함 전체 480개
  테스트 통과, `py -m compileall -f src modules scripts tests` 클린, `py -m src.main` →
  `workflow_completed`(CardNews 4장/Publishing ready 확인), 생성된 PNG 4장 직접 열어 확인,
  Codex MCP 독립 검수(1차 BLOCK — 말줄임표 누락 — 수정 → APPROVED).

이전 완료: Sprint 14 - Documentation Alignment (14-0: 핵심 문서 정합성, 14-1: snapshot generator
순서 버그 수정, 14-2: Content Output Contract + Codex MCP 독립 검수)

기간

2026-07-10 ~ 2026-07-11 (Instagram Intelligence Phase 종료, CardNews Intelligence M7+M8 완료)

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
- [x] Content Output Contract (Sprint 14-2): ContentModule의 Validation -> Normalization ->
      Quality Recheck 파이프라인, Codex MCP 독립 검수 통과
- [x] AI Planner Contract 정의 (Sprint 15-0): `modules/ai_planner/`의 입력/출력/Schema/
      WorkflowEngine 연결 위치 확정. 실제 Decision Engine과 WorkflowEngine 실행 연결은 아직
      없음 (의도적으로 이번 Sprint 범위 밖)
- [x] AI Planner Contract 의존성 결함 수정 (Sprint 15-0A): Planner 위치보다 나중에 생성되는
      결과를 입력으로 요구하던 구조적 결함을 Runtime Input/Historical Input 분리로 해결.
      `PlannerContract`/`PlanningContext`/`planning_result_schema`/`PlannerInterface` 갱신,
      30개 테스트 추가, Codex MCP 독립 검수 포함
- [x] AI Planner Decision Engine v1 구현 (Sprint 15-1): `planner_decision_engine.py`가
      Runtime Input(실제 Pattern/Topic Engine 규칙 재사용)과 Historical Input(실제 storage
      집계)만으로 투명한 규칙 기반 판단을 수행. LLM/외부 API/무작위 값 없음. `WorkflowEngine`
      실행 연결은 여전히 없음. 47개 테스트(전체 `test_ai_planner_*` 스위트), Codex MCP 독립
      검수 포함
- [x] AI Planner Consumer Layer 구현 (Sprint 15-2): `consumer_contract.py`/
      `planner_consumer_adapter.py`가 "Planner 결과=검증된 힌트, 강제 명령 아님"을 4단계
      게이트(유효성/confidence/지원값/안전 규칙 충돌)로 구현. 기존 Engine 선택 로직/fallback
      대체하지 않음. 아직 어떤 실제 Engine도 이 계층을 호출하지 않음(소비 규칙만 구현).
      89개 테스트(전체 `test_ai_planner_*` 스위트), Codex MCP 독립 검수 포함
- [x] AI Planner Workflow Integration 완료 (Sprint 15-3, AI Planner 마지막 Sprint):
      `WorkflowEngine`에 `AIPlannerModule` 실제 연결(Topic 다음, Pattern 이전) +
      `PatternEngineModule`/`ContentModule`/`ImageStrategyModule`/`KnowledgeModule`이
      `PlannerConsumerAdapter`를 실제로 호출. Planner 실패/None/낮은 confidence/미지원
      값 모두 기존 Engine 로직 그대로 유지 확인. `planner_consumption.*` 메타데이터 기록.
      92+33+14개 테스트 전부 통과, 실제 `py -m src.main` 실행으로 Planner 실행 및
      workflow_completed 확인, Codex MCP 독립 검수 포함
- [x] Intelligence Feedback Safety 완료 (Sprint 16-0): Feedback Audit으로 Brand DNA→Planner/
      Knowledge→Planner 순환 참조 2건 발견 및 수정(Self Reference Guard). Analytics/
      Learning/Performance Score/Content에 출처가 명확한 Metadata 추가, 공통 표준
      (`modules/common/metadata_standard.py`)으로 중복 제거. 새 Engine 없음. 186개 테스트
      전부 통과(신규 42개), Codex MCP 독립 검수 포함
- [x] Competitor Learning Engine 구현 (Sprint 18): `modules/competitor_learning/`이
      `modules/instagram_research/`(diff 없음)를 읽기 전용으로 소비해 Knowledge Database +
      Dashboard 생성. `WorkflowEngine`에는 연결하지 않음. 131개 테스트, Codex MCP 독립 검수
      포함
- [x] Instagram Intelligence Phase 완료 (Phase 1/2/3, 2026-07-11): Instagram Research ->
      Competitor Learning -> Knowledge Database -> Brand DNA -> Pattern -> Content **Internal
      Quality Feedback Loop**(pre-publish, 내부 quality_score 기반 - 실제 Instagram 성과
      아님) 완성. 기존 Selector/WorkflowEngine 구조 불변, 4개 confidence 소스는 각각
      독립적으로 `topic_intelligence.confidence_score`만 보정. content_id 기반 dedup, ±0.05
      confidence 범위 clamp, 독립 관찰 5회 미만 시 Brand DNA Feedback 미적용(Self Reference
      Guard 재사용) 확인. 444개 테스트 전부 통과, Codex MCP 독립 검수 포함(`DECISIONS.md`
      2026-07-11 참고)
- [x] CardNews Intelligence(Phase M7) + CardNews Production Quality(Phase M8) 완료
      (2026-07-11): Evidence 주제 관련성 + 저작권 render guard, Social Proof 안전 선정(마스킹/
      PII/의견 라벨링), Story Flow, Debate/CTA 충돌 방지, Typography 계층 + Human Visual
      Rhythm 실제 렌더링 반영, Mobile Readability + Contrast guard, Source Attribution,
      Production Quality QA 10개 항목. 기존 `CardNewsModule` Pillow Renderer 확장만(새
      Engine/Renderer 없음, `src/workflow_engine.py` diff 없음). 실제 PNG 검증 중 번호 목록
      절단 결함 발견/수정. 전체 480개 테스트 통과, `py -m src.main` → `workflow_completed`,
      Codex MCP 독립 검수 포함(1차 BLOCK → 수정 → APPROVED)

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
- Instagram Intelligence (Sprint 18 + 2026-07-11 Phase, standalone/on-demand, not in
  `WorkflowEngine.run()`): `modules/competitor_learning/` (reads `modules/instagram_research/`
  read-only) + `modules/learning_engine/content_performance_history.py` +
  `modules/learning_engine/learning_performance_analyzer.py`. Internal pre-publish
  `quality_score` proxy loop only — see `DECISIONS.md` (2026-07-11).
- Renderer: `modules/card_news/`
- Publishing Engine: `modules/publishing/`
- AI Planner (Contract: Sprint 15-0/15-0A; Decision Engine v1: Sprint 15-1; Consumer Layer:
  Sprint 15-2; Workflow Integration: Sprint 15-3, complete): `modules/ai_planner/` — now
  actually connected to `WorkflowEngine` (runs between `TopicEngineModule` and
  `PatternEngineModule`) and actually called by `PatternEngineModule`/`ContentModule`/
  `ImageStrategyModule`/`KnowledgeModule` via `PlannerConsumerAdapter`; see `PlannerContract` in
  `modules/ai_planner/planner_contract.py`, `PlannerDecisionEngine` in
  `modules/ai_planner/planner_decision_engine.py`, `PlannerConsumerContract`/
  `PlannerConsumerAdapter` in `modules/ai_planner/consumer_contract.py`/
  `planner_consumer_adapter.py`, and `WorkflowEngine._run_ai_planner()` in
  `src/workflow_engine.py`

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

CardNews M7/M8/M7-next와 Content Intelligence focused coverage는 완료됐다. Claude의 Shorts
Phase 0 아키텍처 초안은 Work/Codex CTO 검토를 거쳐 제한 승인됐다. 다음 작업은 기존
Content 결과를 규칙 기반으로 변환하는 완전 오프라인 standalone Shorts Phase 1이다.

---

# Next Tasks

`MODULE_STATUS.md`의 "Next" 섹션과 `ROADMAP.md`를 그대로 따른다. 요약:

1. Shorts Phase 1: 기존 Content 결과를 9개 계획 계약으로 변환하는 offline standalone 모듈과 focused tests
2. Shorts Phase 1은 외부 API, 렌더러, AI Planner 확장, WorkflowEngine 연결 없이 구현
3. 실제 게시 후 Instagram 성과 기반 Closed Loop (현재는 내부 quality_score proxy만 존재) —
   Meta/Instagram Graph API + OAuth + 게시 결과 Import 필요, `ROADMAP.md` "Requires External
   API"에 명시적 승인 전까지 대기
4. Audit Engine의 Competitor Comparison + Blind Spot Detection (Competitor Engine 이력 축적 후)
5. ~~AI Planner 실제 통합~~ — Sprint 15-3에서 완료. AI Planner는 이제 별도 Next 항목이
   없다. (향후 고려사항, 미예정: 실제 실행 이력이 쌓이면
   `MIN_CONFIDENCE_FOR_HINT_APPLICATION`/Brand DNA override 관측 임계치를 재검토)
6. Source Health / Collector Statistics 대시보드
7. `ROADMAP.md` "Requires External API" 섹션 항목들은 명시적 승인 전까지 구현하지 않음
8. (Sprint 16-0에서 새로 남은 향후 고려사항, 미예정) 이번 Sprint에서 새로 추가한
   Metadata 표준(`modules/common/metadata_standard.py`)을 Audit/Trend Memory/Competitor 등
   나머지 Engine의 기존 ad-hoc metadata에도 점진적으로 적용하는 전면 리팩터링
9. (Phase M8에서 새로 남은 항목, 미예정) `comparison` 시각 스타일에 쓸 실제 A/B 비교
   슬라이드 구조 데이터가 아직 없음 — 필요해지면 slide schema 확장 검토

---

# Reminder

항상

문서 → 설계 → 코드 → 테스트 → CHANGELOG

순서로 진행한다.

작업 시작 전에는 `PROJECT_OPERATING_SYSTEM.md`의 Mandatory Reading Order를 따른다.
