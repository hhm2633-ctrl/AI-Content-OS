# AI-Content-OS System Architecture

이 문서는 모든 AI(ChatGPT/Claude/Codex)가 공유하는 **정확한 현재 구조** 기준 문서다.
루트의 `SYSTEM_ARCHITECTURE.md`/`MODULE_SPEC.md`/`WORKFLOW_SPEC.md` 등은 초기 설계 단계에서 작성된
목표(aspirational) 문서라 실제 구현보다 앞서 있거나 다른 부분이 있다 — 실제 구조는 이 문서와
`PROJECT_SNAPSHOT.md`(최근 실행 결과)를 기준으로 판단한다.

## AI-Content-OS 전체 구조

```text
src/main.py                     진입점: load_dotenv() -> WorkflowEngine 생성/실행 -> 문서 스냅샷 갱신
  └─ src/workflow_engine.py     WorkflowEngine: 9개 모듈을 순서대로 호출
       └─ modules/<engine>/     각 엔진의 실제 로직
              └─ storage/       런타임 산출물 (JSON 결과, PNG, 로그)
config/                          모듈별 설정 JSON (settings, trend_sources, publishing, topic_engine, brand_profile)
templates/                       데이터 템플릿 (card_news_layout_rules.json 등)
prompts/                         LLM 프롬프트 가이드 (patterns/ 하위 6종 포함)
```

## WorkflowEngine

`src/workflow_engine.py::WorkflowEngine`이 유일한 오케스트레이터다. `__init__`에서 9개 모듈을 생성하고,
`run()`이 아래 순서로 호출하며 각 단계 결과를 `storage/workflow_results/NN_<name>_result.json`에 저장한다:

```text
TrendCollectorModule -> TopicEngineModule -> PatternEngineModule -> ResearchModule
  -> ContentModule -> ImagePromptModule -> ImageGenerationModule -> CardNewsModule -> PublishingModule
```

전체가 끝나면 `storage/workflow_results/99_final_result.json`에 `status: "workflow_completed"`가 기록된다.
`WorkflowEngine.run()`은 자신의 최상위 try/except에서만 `workflow_failed`를 발생시키며, 개별 모듈은
내부적으로 실패를 흡수하고 fallback 값을 반환하도록 설계되어 있다 — 이 이중 안전망이 프로젝트의 핵심 계약이다.

## Module 관계

각 모듈은 이전 단계의 결과 dict를 인자로 받아 자신의 결과 dict를 반환하는 것이 기본 계약이지만,
일부 모듈은 **파일 직접 읽기**로 추가 컨텍스트를 얻는 컨벤션을 쓴다 (WorkflowEngine 시그니처를 바꾸지 않기 위함):

| 모듈 | dict 입력 | 파일 직접 읽기 |
|---|---|---|
| `ResearchModule` | `topic_result` | `storage/trends/selected_topic.json`(우선), `storage/pattern/pattern_result.json` |
| `PatternEngineModule` | `selected_topic`, `trend_result` (WorkflowEngine이 넘김) | `storage/trends/selected_topic.json`, `storage/trends/trend_result.json` (인자 없을 때 fallback) |
| `CardNewsModule` | `content_result`, `image_generation_result` | `storage/research/research_result.json`(topic_intelligence), `config/brand_profile.json` |

이 "파일 직접 읽기" 패턴 때문에, 어떤 모듈을 단독으로 테스트하면 이전 단계가 실제로 실행되어 그 파일들을
만들어 놓지 않는 한 빈 값(`{}`)을 fallback으로 받는다 — 버그가 아니라 설계다.

## Engine 관계 (데이터 흐름)

```text
Trend Engine
  -> selected_topic, trend_result
Topic Engine
  -> title/angle/target (카드뉴스용 주제 형태)
Pattern Engine  (storage/trends/*.json을 직접 읽어 topic_intelligence 계산)
  -> topic_intelligence { keywords, category, cluster, confidence_score }
  -> pattern_plan { pattern_type, hook_type, cta_type, layout_type }
Research Engine  (selected_topic.json 우선, pattern_result.json 추가)
  -> research_result { ..., topic_intelligence, pattern_plan, pattern_result_available }
Content Engine  (research_result.pattern_plan 있으면 pattern-aware, 없으면 legacy)
  -> content_result { slides, caption, hashtags, content_intelligence, pattern_prompt_meta }
Image Prompt / Image Generation Engine
  -> image_generation_result { images[], fallback_used, service_diagnostic }
CardNews Engine  (content_result + image_generation_result + research_result.json 재-읽기 + brand_profile.json)
  -> card_news_result { cards, layout_result, rendering_result, design_quality_result, card_news_quality }
Publishing Engine
  -> publishing_result, publish_queue.json, caption.txt, hashtags.txt
```

핵심: **Pattern Engine이 만든 `topic_intelligence`/`pattern_plan`은 Research Engine을 거쳐 Content Engine까지
dict로 전달되지만, CardNews Engine에는 dict로 전달되지 않고 `storage/research/research_result.json`을
다시 파일로 읽어서 얻는다.** 이는 `WorkflowEngine.run()`의 `CardNewsModule(content_result, image_generation_result)`
호출 시그니처를 바꾸지 않기 위한 의도적 설계다.

## 문서 관계

```text
PROJECT_MASTER.md       프로젝트 목적/현재 핵심 기능/확장 계획 (정적, 자주 안 바뀜)
PROJECT_SNAPSHOT.md     최근 py -m src.main 실행 결과 + 프로젝트 트리 (거의 매번 자동 갱신)
MODULE_STATUS.md        Sprint별 완료 기능 목록 + Next + Notes (Sprint마다 갱신)
ROADMAP.md              M1~M6 마일스톤. M1(카드뉴스 MVP)이 항상 최우선
AGENTS.md               Codex 실행/구조/안정성/문서화 규칙 (CODEX_RULES.md와 사실상 같은 내용의 두 벌)
CURRENT_TASK.md         진행 중 작업 컨텍스트 (Sprint 1 이후 최신화 빈도 낮음, 참고용)
DECISIONS.md            append-only 의사결정 로그. 절대 삭제되지 않음
CHANGELOG.md            append-only 변경 이력. 날짜 헤더로 구분
.claude/skills/         Claude 전용 절차 스킬 (교차 규칙 6개 + domain/ 엔진별 10개)
.codex/skills/          Codex 전용 절차 스킬 (5개)
.ai/                    이 문서를 포함한, AI에 상관없이 공유되는 인프라
```

이 중 `PROJECT_SNAPSHOT.md`는 `scripts/update_project_snapshot.py`가 `py -m src.main` 실행 후 자동으로
전체 재작성하므로, 사람이나 AI가 수기로 일부만 고치면 다음 실행 때 덮어써진다 — 수기 편집은 최소화한다.
