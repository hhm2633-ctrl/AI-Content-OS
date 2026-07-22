# DECISIONS.md

# AI-Content-OS

프로젝트에서 내려진 모든 중요한 의사결정을 기록한다.

---

# Decision History

## 2026-07-07

### 프로젝트 방향

결정

AI 자동화 프로젝트가 아니라

AI Content Operating System을 구축한다.

이유

장기적으로 다양한 플랫폼과 사업으로 확장하기 위함.

---

### 개발 방식

결정

Documentation First

문서를 먼저 작성한다.

이유

프로젝트 규모가 커질수록 유지보수가 쉬워진다.

---

### 프로젝트 관리

결정

GitHub를 Single Source of Truth로 사용한다.

이유

모든 AI와 개발 환경에서 동일한 기준을 유지하기 위함.

---

### Legacy 정책

결정

기존 자료는 바로 사용하지 않는다.

반드시

분석

↓

분류

↓

리팩토링

↓

편입

절차를 따른다.

---

### Architecture

결정

모놀리식 구조가 아니라

모듈형 구조를 채택한다.

이유

필요한 기능만 교체 가능하도록 하기 위함.

---

### AI 사용 정책

결정

AI마다 역할을 분리한다.

ChatGPT

- CTO
- Architecture
- Documentation
- Project Management

Claude

- Code
- Refactoring

Gemini

- Vision
- OCR
- Google Ecosystem

필요시 다른 AI 추가 가능

---

### 현재 사업 전략

결정

첫 번째 목표는

Instagram 카드뉴스 자동화

이유

가장 빠르게 수익 검증이 가능하기 때문.

---

### 장기 전략

Instagram

↓

YouTube Shorts

↓

Affiliate

↓

Smart Store

↓

Coupang

↓

AI Content Company

---

### 개발 원칙

결정

기능 추가보다

프로젝트 구조를 우선한다.

---

### 문서 정책

결정

모든 중요한 변경은

먼저 문서를 수정한다.

그 이후 코드를 수정한다.

---

### 답변 정책

결정

AI는

부분 최적화가 아니라

프로젝트 전체를 고려하여 답변한다.

---

# Future Decisions

앞으로 중요한 기술적 결정은

날짜와 함께 계속 추가한다.

절대로 삭제하지 않는다.
# 2026-07-09 External Research Handling

Decision

External materials are analyzed by ChatGPT CTO first.

Claude and Codex do not re-analyze raw external materials by default. They use the analyzed GitHub documents as project context.

Reason

This keeps project knowledge stable, reduces duplicate AI cost, and prevents raw-source interpretation drift during implementation.

Applied Documents

- `docs/KNOWLEDGE_ENGINE.md`
- `docs/RESEARCH/AlphaCut.md`
- `docs/RESEARCH/Claude_Instagram_Audit.md`
- `docs/RESEARCH/Claude_Codex_Workflow.md`

---

# 2026-07-11 Instagram Intelligence Phase: Internal Quality Proxy, Not Real External Performance

결정

Instagram Intelligence Phase(Instagram Research -> Competitor Learning -> Knowledge Database ->
Brand DNA -> Pattern -> Content)에서 만들어지는 Learning Feedback/Knowledge Feedback/
`content_performance_history`는 실제 Instagram 좋아요/댓글/저장/공유/도달 성과가 아니라,
발행 전(pre-publish) 내부 content quality_score를 대리 신호(proxy)로 사용한다. 이 사실을
`performance_source: "internal_quality_proxy"` / `external_metrics_used: false` /
`external_metrics_available: false` / `learning_scope: "pre_publish_internal_feedback"`
메타데이터로 관련된 모든 결과 구조(Learning Engine 결과, `content_performance_history.json`,
`daily_learning_report.json`)에 명시적으로 기록한다.

이유

실제 외부 성과 데이터 없이 내부 품질 점수를 "성과"라고 부르면, 나중에 실제 Instagram 성과
데이터가 연결됐을 때 두 개념이 섞여 잘못된 결론(예: "품질 점수가 높으니 실제로도 잘 나갔다")을
내릴 위험이 있다. Offline-First 원칙(가짜 외부 신호를 만들지 않는다)의 연장선으로, "값을
가짜로 만들지 않는 것"뿐 아니라 "실제 값이 아닌 것을 실제 값처럼 라벨링하지 않는 것"까지
포함한다.

완성된 것 / 완성되지 않은 것 구분

- 완성됨: "내부 품질 Proxy 기반 Pre-Publish Feedback Loop" (Instagram Research -> Competitor
  Learning -> Knowledge -> Brand DNA -> Pattern -> Content, 전부 로컬 데이터/내부 quality_score
  기반, LLM/외부 API 없음).
- 완성되지 않음: "실제 게시 후 Instagram 성과 기반 Closed Loop" (실제 좋아요/댓글/저장/공유/
  도달 데이터를 Meta API/OAuth/게시 결과 Import로 가져와 Learning/Knowledge Feedback에
  반영하는 것). 이 항목은 `ROADMAP.md`의 "Requires External API" 섹션에 명시적 승인 전까지
  남는다.

다음 최우선 작업

CardNews Intelligence -> Evidence Selection -> Comment/Social Proof Selection -> Story Flow ->
Debate/CTA -> Production Quality. Reels/Shorts와 Commerce는 지금 시작하지 않는다.

Applied Modules

- `modules/competitor_learning/`
- `modules/learning_engine/content_performance_history.py`
- `modules/learning_engine/learning_performance_analyzer.py`
- `modules/learning_engine/learning_engine_module.py`
- `modules/brand_dna_engine/brand_dna_engine_module.py`
- `modules/pattern_engine/pattern_engine_module.py`
- `modules/content/content_quality_scorer.py`

---

# 2026-07-11 CardNews Intelligence (M7) + Production Quality (M8): Extend the Existing Renderer, Never Fabricate Evidence/Comments

결정

CardNews Intelligence(Evidence Selection/Social Proof Selection/Story Flow/Debate Engine)와
CardNews Production Quality(Typography/Human Visual Rhythm/Mobile Readability/Contrast/Source
Attribution/QA)는 새 Engine이나 새 Renderer를 만들지 않고, 기존 `CardNewsModule`(Pillow
Renderer)을 확장하는 방식으로만 구현한다. `src/workflow_engine.py`는 건드리지 않는다.

Evidence/Social Proof는 "파일이 존재한다"와 "실제로 써도 된다"를 절대 같은 값으로 취급하지
않는다: Evidence는 `candidate_found`(파일 존재)/`topic_relevant`(주제 관련성, 단어 1개 우연
일치로 통과시키지 않음)/`render_allowed`(허용된 `copyright_status`만)/`asset_role ==
"topic_evidence"` 4개 게이트를 모두 통과해야 실제 카드 배경에 쓸 수 있다. Instagram Research
스크린샷은 항상 `competitor_reference`(경쟁 계정 참고 자료)로 분류하고, 이 사건/주제의 실제
증거라는 확인 신호가 없는 한 `topic_evidence`로 승격하지 않는다 — 출처 표시는 사용 허가를
대신하지 않는다. Social Proof는 실제 댓글/반응 텍스트 필드(`comment_text`/`reply_text`/
`reaction_text`/`quote_text`)만 후보로 인정하고, 게시물 소유자 자신의 글(`caption_text`)이나
좋아요/댓글 "개수"(`visible_*_text`)는 절대 댓글 "내용"으로 오인하지 않는다. 실제 데이터가
없으면 `available: false`를 정직하게 반환하고, 가짜 댓글이나 가짜 SNS 캡처를 만들지 않는다.

이유

카드뉴스가 실제 배포되는 콘텐츠이기 때문에, "그럴듯해 보이는 증거/반응"을 자동 생성하면
독자를 속이는 결과로 이어진다. 이는 Sprint 13 Offline-First 원칙("가짜 외부 신호를 만들지
않는다")과 2026-07-11 Instagram Intelligence Phase 결정("실제 값이 아닌 것을 실제 값처럼
라벨링하지 않는다")의 CardNews 버전이다.

완성된 것 / 완성되지 않은 것 구분

- 완성됨: Evidence 주제 관련성/저작권 render guard, Social Proof 안전 선정(마스킹/PII
  스크럽/의견 라벨링), Story Flow/Debate·CTA 충돌 방지, Typography 계층 + Human Visual
  Rhythm의 실제 PNG 반영, Mobile Readability + WCAG Contrast guard(라이트 모드 subtitle
  대비를 4.42 -> 4.95로 실측 수정), Source Attribution(실제 적용+허용된 evidence만),
  Production Quality QA 10개 항목(총점 100 유지, 조건부 채점).
- 완성되지 않음(버그 아니라 데이터 소스가 아직 없음): 실제 제3자 댓글 본문 수집기 — Social
  Proof는 계속 `available: false`가 정상 상태다. Instagram 경쟁계정 screenshot의 실제 증거
  승격(현재는 항상 `competitor_reference`로 남는다). `comparison` 시각 스타일에 쓸 실제 A/B
  비교 슬라이드 구조(현재 slide 스키마에 없어 항상 기본 스타일로 fallback한다).

검증 중 발견한 실결함과 최소 수정 원칙 확인

최종 검증 단계에서 실제 생성된 PNG를 직접 열어본 결과, 번호 매긴 목록("1." "2.")을 문장
경계로 오인하는 정규식 결함이 발견됐다(항목 번호만 남고 내용이 사라짐). 전체 구조를 다시
만들지 않고 정규식 하나만 최소 수정했고, Codex MCP 리뷰가 추가로 지적한 "최후 수단 글자 단위
절단에 잘렸다는 표시(말줄임표)가 없는" 문제도 동일하게 최소 수정했다. "실제 결과물을 직접
확인해야만 발견되는 결함이 있다"는 원칙을 재확인한 사례로 기록한다.

다음 최우선 작업

CardNews 실제 결과물 운영 테스트 — 다양한 실제 주제로 카드뉴스 생성 -> 실제 업로드 가능한
품질 확인 -> 필요한 소규모 디자인 보정. Reels/Shorts와 Commerce는 지금 시작하지 않는다.

Applied Modules

- `modules/card_news/evidence_selector.py`
- `modules/card_news/social_proof_selector.py`
- `modules/card_news/story_flow_planner.py`
- `modules/card_news/debate_question_selector.py`
- `modules/card_news/typography_rules.py`
- `modules/card_news/visual_rhythm_selector.py`
- `modules/card_news/mobile_readability_checker.py`
- `modules/card_news/render_constants.py`
- `modules/card_news/card_news_module.py`
- `modules/card_news/card_news_quality_checker.py`
- `modules/card_news/card_news_text_optimizer.py`

---

# 2026-07-11 Work/Codex Primary Operating Model and Project Skill System

결정

AI-Content-OS의 기본 개발 경로를 `ChatGPT CTO -> Claude -> Codex MCP -> GitHub` 강제 체인에서 `ChatGPT Work CTO -> 같은 프로젝트 컨텍스트의 Codex 실행 -> GitHub`로 단순화한다. Claude는 제거하지 않지만, 사용자가 명시적으로 맡기거나 독립적인 2차 검토 가치가 큰 경우에만 선택적으로 사용한다. Claude의 Codex MCP 확인·호출은 기본 요구사항에서 제거한다.

Work와 Codex가 저장소 파일, 사이드 작업, 브라우저, 연결 앱, 구현, 테스트, 문서와 Git을 한 프로젝트 안에서 다룰 수 있으므로, 동일 맥락을 여러 AI 사이에 반복 전달하는 비용과 손실을 줄이는 것이 목적이다. 파일 수만으로 Claude를 강제하지 않고 위험도, 전문성, 독립 검토 가치와 사용자 지시로 선택한다.

공용 실행 지식을 `.codex/skills/`의 프로젝트 스킬로 관리한다. 추가된 스킬은 Trend Collector, Research Intelligence, Card News, Shorts, Publishing, Instagram, Coupang, QA, CTO Review, Sprint Manager다. Shorts와 Coupang은 현재 구현 완료를 의미하지 않으며, Roadmap·외부 데이터·승인 게이트를 강제하는 계획 스킬이다.

외부 스킬·플러그인 원칙

- 기존 모듈과 설치된 공식 기능을 우선한다.
- 공개 스킬은 코드, 권한, 유지보수, 라이선스를 검토한 뒤 채택한다.
- 폐기된 `openai/skills` 카탈로그보다 현재 `openai/plugins`와 공식 Skill Creator 형식을 기준으로 한다.
- GitHub와 Google Drive는 현재 유효한 핵심 연결이며, 추가 메신저·메일·디자인 플러그인은 실제 운영 주체가 생길 때만 설치한다.

---

# 2026-07-11 Shorts Phase 1 Offline-Only Boundary

Shorts Phase 1은 기존 Content 결과를 9개 제작계획 계약으로 변환하는 standalone 모듈로만
구현한다. 실제 영상, 음성, 음악, 외부 자산, 전사, 렌더링, 게시 API를 호출하지 않으며
`WorkflowEngine`, CardNews, AI Planner를 수정하거나 연결하지 않는다.

30초 예산 초과는 문장 중간 절단이 아니라 마지막 대사 전체 제거로 처리하고 원래 길이와 제거
수를 기록한다. 출처와 사용 권한이 확인되지 않은 자산은 절대 render-allowed로 만들지 않는다.
Phase 1 완료는 "제작계획 생성 가능"을 뜻하며 "영상 제작/게시 가능"을 뜻하지 않는다.

---

# 2026-07-11 CardNews Renderer Completion Is Not Publish Approval

CardNews의 PNG 생성, 레이아웃/가독성 QA 통과와 실제 게시 승인을 분리한다. 현재 4개 PNG는
앱에서 열 수 있고 렌더링 실패도 없지만, 문안 의미 품질과 실제 이미지 준비가 남아 있으므로
게시 승인 상태가 아니다. `manual_image_required=true`이면 `publishing_ready` 문자열과 무관하게
사용자 UI와 manifest의 ready 값은 반드시 false여야 한다.

자동 QA 점수는 렌더러/디자인 증거이며 최종 콘텐츠 의미 품질을 대체하지 않는다. 독립 시각
검수에서 주제-본문 불일치, 문장 절단, 미완성 headline, CTA 불일치가 발견되면 publish-level
acceptance를 다시 연다.

---

# 2026-07-11 CardNews Operational Completion

결정

CardNews M7, M8, M7-next를 운영 완료로 판정한다. 실제 1024x1024 PNG 4장을 직접 검수했고,
Production QA 0.85/pass, `rendering_fallback_used: false`, 전용 테스트 38개 통과, compile 성공,
`py -m src.main`의 `workflow_completed`, `card_news_completed`, `publishing_ready`를 확인했다.

QA 진단에서 레이아웃 선택 단계의 안전한 대체(`layout_fallback_used`)와 실제 렌더링 실패
대체(`rendering_fallback_used`)를 분리한다. 또한 Debate가 글자 수 예산이나 CTA 충돌 방지로
명시적으로 생략된 경우 `debate_required: false`로 처리하며, 설명 없이 누락된 경우에만 결함으로
경고한다.

실제 댓글·증거 이미지·Instagram 성과 데이터가 없거나 외부 LLM이 fallback한 상태는 CardNews
Renderer의 미완료 사유가 아니다. 해당 능력은 Research, Instagram, 외부 API Roadmap에서 별도
추적한다. 이후 Shorts 작업은 CardNews 경로를 수정하지 않는 독립 Phase 0 설계부터 시작한다.
# 2026-07-22 - CardNews production is controller-authorized and fail-closed

- The standard Workflow is a planning/learning path, not an implicit production authorization path.
- Image API calls, CardNews rendering, and publishing preparation require explicit owner-bound authorization through the controlled production path.
- Approval receipts must be explicit and scoped; scripts may not synthesize approvers, receipt IDs, or ready states.
- CardNews slide count is fully variable from 1 through 20 and comes from the approved content/media plan. There is no fixed minimum or default production count; fixed-four truncation is prohibited.
- OCR/OpenCLIP post-render checks are machine evidence only. They cannot create owner approval or publish readiness.
- `workflow_completed` means orchestration completed; it does not mean production, visual acceptance, or publishing completed.
- Intel XPU, SeaweedFS, Mixpost, and TryPost remain non-critical/reference-only until separately approved and operationally proven.
