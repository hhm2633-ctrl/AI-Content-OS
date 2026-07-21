---
name: topic-engine
description: Topic Engine 전용 Domain Skill. Category, Cluster, Keyword Weight, Confidence 계산을 다룬다.
---

# Topic Engine Skill

## 대상 모듈

- `modules/topic_engine/topic_engine_module.py` (`TopicEngineModule`) — WorkflowEngine 진입점. `TrendCollectorModule`의 `selected_topic`을 받아 카드뉴스용 주제 형태(`title`/`angle`/`target`/`reason` 등)로 변환한다.
- `modules/topic_engine/keyword_weight.py` (`KeywordWeightEngine`) — 키워드 가중치 계산.
- `modules/topic_engine/topic_classifier.py` (`TopicClassifier`) — 카테고리 분류.
- `modules/topic_engine/topic_cluster.py` (`TopicCluster`) — 카테고리 → 세부 클러스터 매핑.
- `modules/topic_engine/confidence_score.py` (`ConfidenceScorer`) — 신뢰도 점수 계산.

이 4개 헬퍼는 `TopicEngineModule`이 아니라 **`PatternEngineModule`(`modules/pattern_engine/`)이 호출**해 `topic_intelligence`를 만든다 — `TopicEngineModule` 자체는 이 헬퍼들을 사용하지 않는 별개의 단순 변환 로직이다. 둘을 혼동하지 않는다.

## Keyword Weight

`KeywordWeightEngine.compute_weights(selected_topic, trends)`:

- `selected_topic.title`의 토큰에 기본 가중치(5.0)를 부여한다.
- `trends` 리스트의 각 후보 키워드 토큰에 `1.0 + quality_score/100` 가중치를 누적한다.
- 최댓값으로 정규화(0~1) 후 상위 10개 키워드만 반환한다.
- 정규식 `[^0-9a-z가-힣 ]`로 토큰을 정리하며, 2자 미만 토큰은 제외한다.

## Category

`TopicClassifier`가 `config/topic_engine.json`의 `allowed_categories`/`blocked_categories`를 기준으로 분류한다:

- 허용 카테고리(기본값): `AI`, `부업`, `경제`, `생활`, `쇼핑`, `트렌드`
- 차단 카테고리(기본값): `도박`, `성인`, `불법`, `혐오`, `정치선동` — 차단 키워드가 감지되면 `blocked: true`를 반환하고, 이후 Pattern Engine의 `ConfidenceScorer`가 confidence를 강제로 낮춘다.
- 일치하는 키워드가 없으면 기본 카테고리 `트렌드`로 분류한다 (예외 없이 항상 값이 나온다).

## Cluster

`TopicCluster`가 카테고리를 세부 클러스터로 매핑한다 (`CATEGORY_CLUSTER_MAP`):

```text
AI     -> ai_automation_cluster
부업   -> side_income_cluster
경제   -> living_cost_cluster
생활   -> daily_life_cluster
쇼핑   -> shopping_saving_cluster
트렌드 -> general_trend_cluster (기본값)
```

## Confidence

`ConfidenceScorer.score()`가 0.0~1.0 사이 값을 계산한다:

- base = `quality_score / 100` (없으면 0.5)
- `is_fallback=true`면 -0.15
- `collection_method == "placeholder_fallback"`면 -0.2, `_cache`로 끝나면 -0.05
- `keyword_weights`가 비어 있으면 -0.1
- `category == "트렌드"`(기본값)면 -0.05
- `blocked=true`면 상한을 0.1로 강제 제한

이 confidence_score는 `PatternEngineModule`의 `PatternSelector`가 `LOW_QUALITY_THRESHOLD`(0.3) 미만일 때 안전한 기본 패턴으로 강제 전환하는 데 사용된다 — Topic Engine의 계산 실수가 곧바로 Pattern 선택 품질에 영향을 준다는 뜻이다.

## 절대 원칙

- 이 4개 헬퍼는 모두 자체 try/except로 예외를 삼키고 안전한 기본값을 반환한다 — 새 로직을 추가할 때도 이 패턴(계산 실패 → 안전 기본값, 절대 raise하지 않음)을 유지한다.
- `config/topic_engine.json`이 없거나 손상돼도 하드코딩된 fallback 값으로 동작해야 한다.
