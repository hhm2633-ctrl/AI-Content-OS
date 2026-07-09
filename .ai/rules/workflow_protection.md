# Workflow Protection Rules

`workflow_completed`는 AI-Content-OS의 유일한 성공 기준이다. 이 문서는 그것을 지키기 위해
실제로 구현되어 있는 메커니즘과, 그 메커니즘을 건드릴 때의 규칙을 정의한다.

## workflow_completed

- 판정 위치: `storage/workflow_results/99_final_result.json`의 최상위 `status` 필드.
- `WorkflowEngine.run()`의 최상위 try/except만이 `workflow_failed`를 만들 수 있다 — 개별 모듈 내부의 실패는
  절대 여기까지 전파되면 안 된다 (설계상 각 모듈이 자체적으로 흡수해야 함).
- 개별 단계의 `fallback_used: true`(Naver/Nate/LLM/Image/Layout/QA 등 어디서든)는 **정상적인 성공 사례**다.
  fallback이 있었다는 것과 워크플로가 실패했다는 것은 서로 다른 개념이다.

## WorkflowEngine

- 9단계 순서(`.ai/architecture/system_architecture.md` 참고)와 각 모듈의 호출 시그니처를 바꾸지 않는다.
- `WorkflowEngine.__init__`이 모듈을 생성하는 순서와, `run()`이 호출하는 순서는 항상 동일해야 한다.

## Fallback

실제 구현된 fallback 체인 (엔진별 상세는 `.claude/skills/domain/*.md`):

| 엔진 | Fallback 체인 |
|---|---|
| Trend | 실시간 수집 → Retry → 캐시(`storage/cache/*.json`) → 설정 키워드 → placeholder |
| Topic/Pattern | 계산 실패 시 안전한 기본 카테고리/패턴(`resource`)/신뢰도 0으로 대체 |
| Content (LLM) | `_safe_json_parse` 실패 시 하드코딩된 `_fallback_slides`로 대체 |
| Image | 개별 이미지 실패는 `status: "failed"`로 기록, 나머지는 계속 생성 |
| CardNews Layout/Rendering/QA/Design Quality | 각 계산이 실패해도 실제 PNG 렌더링에는 영향 없이 메타데이터만 안전 기본값으로 대체 |

## Retry

- `modules/trend_collector/retry_policy.py::RetryPolicy` — Trend 수집 재시도.
- `ImageGenerationModule._generate_image()` — 이미지 1장당 최대 3회, 2/5/10초 backoff.
- `LLMClient.generate_text()` — 설정값 기반 재시도.
- **재시도는 일시적 오류에만 유효하다.** `auth_failed`/`rate_limited`처럼 재시도해도 소용없는 오류 유형과
  `connection_refused`/`timeout`처럼 재시도가 의미 있는 유형을 구분한다 (`modules/common/service_diagnostic.py`의
  `error_type` 분류 참고). 재시도 횟수/backoff를 늘리기 전에 `.claude/skills/domain/performance.md`의
  비용(관측된 최대 357.66초 실행 시간)을 먼저 검토한다.

## Cache

- `storage/cache/naver_news_cache.json`, `storage/cache/nate_pann_cache.json` — Trend Engine 전용, TTL 관리.
- `storage/content/content_history.json` — Content 중복 검사용 이력 (최대 500건).
- `storage/card_news/card_news_quality.json` — CardNews QA 결과 (매 실행 덮어씀, 이력 아님).
- `storage/runtime/service_diagnostic.json` — 외부 서비스 진단 이력 (최대 200건).
- 이 파일들은 전부 `storage/**`이므로 **Claude/사람이 직접 수정하지 않는다** — 각 모듈이 런타임에만 쓴다.

## 이 규칙을 지키기 위한 작업 원칙

- 새 외부 연동을 추가할 때는 반드시 위 fallback/retry/cache 패턴 중 하나를 따른다 — 새로운 예외 처리 스타일을 발명하지 않는다.
- Sprint 지시서가 "storage/** 수정 금지"를 명시하면, 위 파일들의 스키마를 바꾸는 코드 변경도 storage 데이터 자체를 직접 편집하는 것도 하지 않는다.
