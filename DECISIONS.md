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
