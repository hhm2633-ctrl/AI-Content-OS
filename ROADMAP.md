# AI-Content-OS Roadmap

## M1: Trend Engine 운영형 완성

- 국내 트렌드 소스 수집 안정화
- 네이버 뉴스 fallback/cache 운영화
- 네이트판 fallback/cache 운영화
- Trend Quality Scoring
- Selection Reason
- Top Topic Picker
- Duplicate Removal
- selected_topic 저장 및 Research 연동
- Source Health 및 Collector Statistics

## M2: Content Engine 고도화

- selected_topic 기반 Research 강화
- 카드뉴스 문안 품질 개선
- LLM 실패 시 자연스러운 fallback copy 생성
- caption/hashtag 품질 개선
- 프롬프트 템플릿 버전 관리

## M3: Image/CardNews Engine 고도화

- 이미지 프롬프트 품질 개선
- 이미지 API 실패 시 local/card background fallback 강화
- 카드뉴스 레이아웃 템플릿 다변화
- 한글 폰트/줄바꿈 안정화
- 카드뉴스 QA 지표 추가

## M4: Publishing/Scheduler 고도화

- Publishing v2 안정화
- 플랫폼별 caption/hashtag formatter
- 예약 발행 큐 개선
- 수동 업로드 체크리스트
- 발행 결과 기록

## M5: Dashboard/Analytics

- workflow 결과 대시보드
- source health 대시보드
- 콘텐츠별 성과 기록
- 반복 주제/고성과 주제 분석

## M6: Shorts/Blog/Store 확장

- Shorts script workflow
- Blog article workflow
- SmartStore/Coupang content workflow
- 채널별 재가공 파이프라인

## M7: CardNews Intelligence (다음 최우선 작업, 2026-07-11 지정)

Instagram Intelligence Phase(Internal Quality Feedback Loop) 완료 후 다음 최우선 순서.
Reels/Shorts, Commerce(SmartStore/Coupang)는 지금 시작하지 않는다.

1. CardNews Intelligence
2. Evidence Selection
3. Comment/Social Proof Selection
4. Story Flow
5. Debate/CTA
6. Production Quality
# Research Knowledge / Intelligence Engines

- Knowledge Engine: v1 implemented (Sprint 11), enhanced (Sprint 13: global rank across full DB, `search()`, in-run cache, per-type average score statistics) — real read+write consumption wired into Pattern Engine (confidence_score boost on match), Content Module (prompt guidance injection), CardNews Module (layout_quality_score boost on match), Audit Engine (duplicate_check blending), Learning Engine (knowledge_score component)
- Performance Score Engine: v1 implemented (Sprint 12) — hook/cta/layout/brand/image composite scoring, shared by Audit/Learning/Analytics
- Competitor Engine: v2 implemented (Sprint 13, offline-first) — Benchmark/Community/News sources + `InstagramBenchmarkParser` (parses `benchmark/INSTAGRAM_BENCHMARK.md`'s per-account sections into real `storage/competitor/competitor_profiles.json`) + `ToolsFunnelParser` (parses `benchmark/TOOLS_AND_FUNNEL_REFERENCES.md`). No live Instagram/Meta API — see "Requires External API" below.
- Audit Engine: v2 implemented (Sprint 13) — 9 checks (hook/cta/pattern/layout/brand/image_strategy/duplicate/save_inducement/comment_inducement) reading content_result + pattern_result + card_news_result + image_strategy_result + knowledge_result + trend_memory_result; Competitor Comparison and Blind Spot Detection remain for a future Sprint once Competitor Engine history accumulates across runs
- Learning Engine: v2 implemented (Sprint 13) — `internal_learning_score` = audit_score(0.4) + performance_score(0.35) + knowledge_score(0.25), all real local values (no fabricated SNS performance); promotes high-scoring Hook/CTA/Pattern/Layout/Brand Knowledge from "good runs" into a reinforced Learning Memory
- Analytics Engine: v2 implemented (Sprint 13) — Sprint 12's fabricated views/saves/comments/shares/CTR/follow/DM predictions (`is_measured: false`) were removed; replaced with an honest `quality_trend` (improving/declining/stable) computed by comparing this run's real Performance Score against the real historical average in `storage/performance_score/`. Real Instagram Graph API metrics are Planning — see "Requires External API" below.
- Brand DNA Engine: v1 implemented (Sprint 12) — tracks actually-used hook/cta/layout/color per run on top of `config/brand_profile.json`
- Trend Memory: v1 implemented (Sprint 12), consumed by Audit Engine's duplicate_check (Sprint 13) — records recent topic/hook/cta/layout/image combinations and flags repeat risk (does not block generation)
- AI Planner: **fully implemented (Sprint 15-0 → 15-3), no remaining Planning items.** Contract
  (Sprint 15-0/15-0A) split input into Runtime (`trend_result`, `topic_result`, `brand_profile` —
  available at the Planner's actual pre-Pattern-Engine position) and Historical
  (`knowledge_history`, `trend_memory_history`, `competitor_history`, `brand_dna_history`,
  `performance_history` — read from existing local storage, not the current run).
  `PlannerDecisionEngine` (Sprint 15-1) computes real `selected_pattern`/
  `selected_hook_strategy`/`selected_cta_strategy`/`selected_image_strategy`/
  `knowledge_priority`/`competitor_reference`/`content_strategy` values via transparent rules
  (reusing `PatternEngineModule`'s real classes + real Historical Input aggregation, no
  LLM/external API/random values). `PlannerConsumerContract`/`PlannerConsumerAdapter`
  (Sprint 15-2) define how a Consumer Engine safely treats that output as a verified hint (never
  a forced command) via four gates: validity, confidence threshold, supported-value membership,
  and no conflict with the Engine's own existing safety rules. **Sprint 15-3** wired
  `AIPlannerModule` into `WorkflowEngine` (runs between `TopicEngineModule` and
  `PatternEngineModule`, returns `None` — not an exception — on any failure) and connected the
  Consumer Adapter into `PatternEngineModule`/`ContentModule`/`ImageStrategyModule`/
  `KnowledgeModule`, each recording a `planner_consumption.*` metadata entry and none of them
  losing their own existing selection logic or fallback behavior.
- **Competitor Learning Engine**: implemented (Sprint 18, offline-first) — `modules/competitor_learning/`
  converts `modules/instagram_research/`'s already-collected posts (read-only, no crawler) into a
  ranked Knowledge Database (`storage/knowledge/knowledge_database.json` + 5 statistics files).
  Not wired into `WorkflowEngine.run()` — a standalone, on-demand batch step.
- **Instagram Intelligence Phase — Internal Quality Feedback Loop**: implemented
  (2026-07-11) — Instagram Research -> Competitor Learning -> Knowledge Database -> Brand DNA ->
  Pattern -> Content, closed via `content_performance_history.json`/Knowledge Feedback
  (`score.confidence` nudges)/4-source Pattern Engine confidence consultation
  (Knowledge/Competitor Learning/Brand DNA/Learning Engine)/`ContentQualityScorer`'s
  `pattern_confidence_bonus`. **This is a pre-publish, internal `quality_score`-based proxy loop,
  not a real Instagram performance loop** — every result surface carries explicit
  `performance_source: "internal_quality_proxy"` / `external_metrics_used: false` /
  `external_metrics_available: false` / `learning_scope: "pre_publish_internal_feedback"`
  metadata so it is never mistaken for real engagement data. See `DECISIONS.md` (2026-07-11).
  The **real** post-publish Instagram performance Closed Loop (actual likes/comments/saves/
  shares/reach feeding back into this same loop) remains in "Requires External API" below.
- **Intelligence Feedback Safety (Sprint 16-0, no new Engine)**: a Feedback Audit of the actual
  `Planner → Content/Pattern/Image Strategy/Knowledge → Brand DNA/Performance Score/Learning/
  Analytics → storage → Planner` path found two real self-reinforcing loops (Brand DNA→Planner
  via `total_observations`; Knowledge→Planner via a persisted score-boosting bug in Sprint
  15-3's "Priority Boost") and closed both — see `MODULE_STATUS.md`'s Sprint 16-0 entry.
  Analytics/Learning/Performance Score/Content also gained explicit source-labeled metadata
  (`measurement_metadata`/`evidence_metadata`/`planner_used`+family/`engine_influence`) built on
  a new shared `modules/common/metadata_standard.py` helper.

# Requires External API (do not implement without explicit approval)

These items are intentionally **not** implemented because they require Instagram API, Meta Graph API, access tokens, or real SNS login/crawling — all explicitly out of scope per the Sprint 13 "Offline-First" decision. They stay here until a Sprint explicitly authorizes the external dependency.

- **Real Instagram/Meta performance metrics** (views, saves, comments, shares, CTR, follow conversion, DM count) for Analytics Engine — requires Instagram Graph API + access token. Until then, Analytics Engine only reports a real, locally-computed `quality_trend`.
- **Real post-publish Instagram Performance Closed Loop** (2026-07-11): the Instagram Intelligence
  Phase's Learning Feedback/Knowledge Feedback/`content_performance_history` currently run on an
  internal, pre-publish `quality_score` proxy only (see the entry above and `DECISIONS.md`).
  Replacing that proxy with real post-publish performance (actual likes/comments/saves/shares/
  reach per published card news, via Meta/Instagram Graph API + OAuth + a publish-result Import
  step) is intentionally deferred here until explicit approval — it is a superset of the metrics
  bullet directly above, scoped specifically to closing this feedback loop with real data.
- **Real-time Instagram competitor account scanning** (beyond the static `benchmark/*.md` docs already parsed by Competitor Engine) — requires either Instagram API/login or a scraping tool (e.g. the "Bla View" reference in `benchmark/TOOLS_AND_FUNNEL_REFERENCES.md`, which itself requires an AssemblyAI API key).
- **Real image sourcing automation** (news thumbnail fetch, community post/comment capture, product image lookup) to fulfill `image_usage_plan` — requires crawling external pages/SNS posts for images, which falls under "실제 SNS 로그인/크롤링 전제 금지". Until implemented, CardNews/Publishing only surface a `manual_image_required` checklist (Sprint 13).
- **Reels/Shorts transcript extraction and translation** (Bla View / AssemblyAI workflow described in `benchmark/TOOLS_AND_FUNNEL_REFERENCES.md`) — requires a third-party transcription API key.
- **Edits app deep-linking / automated Reels publishing** — requires Instagram-side app integration, not just local rendering.

# Later Roadmap

- Timeline Engine
- Animation Engine
- Video Renderer
- PDF Report

These are roadmap items only and should not replace the current card news MVP priority.
