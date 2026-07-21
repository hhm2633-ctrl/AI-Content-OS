---
name: pattern-engine
description: Pattern Engine 전용 Domain Skill. Pattern/Hook/CTA/Layout 선택과 Pattern Score(confidence 연동)를 다룬다.
---

# Pattern Engine Skill

## 대상 모듈

`modules/pattern_engine/`:

- `pattern_engine_module.py` (`PatternEngineModule`) — WorkflowEngine에서 `TopicEngineModule` 다음, `ResearchModule` 이전에 실행. `topic_intelligence` + `pattern_plan`을 계산해 `storage/pattern/`에 저장한다.
- `pattern_selector.py` (`PatternSelector`) — `pattern_type` 선택.
- `hook_selector.py` (`HookSelector`) — `hook_type` 선택 (5종).
- `cta_selector.py` (`CTASelector`) — `cta_type` 선택 (5종).
- `layout_selector.py` (`LayoutSelector`) — `layout_type` 선택 (5종).
- `pattern_result_writer.py` (`PatternResultWriter`) — `pattern_result.json`/`pattern_history.json`/`pattern_statistics.json` 기록.

**⚠️ 이름 충돌 주의**: `modules/pattern_engine/layout_selector.py::LayoutSelector`와 `modules/card_news/layout_selector.py::LayoutSelector`는 **완전히 다른 클래스**다. 전자는 5종 레이아웃(콘텐츠 생성 전, category 기반 큰 분류), 후자는 10종 레이아웃(카드뉴스 렌더링 직전, pattern_type+content_intelligence 기반 세부 분류)을 다룬다. `cardnews.md` 참고.

## Pattern

`PatternSelector`가 6종 `pattern_type` 중 선택한다: `warning`, `tutorial`, `comparison`, `number_list`, `story`, `resource` (+ `funnel`은 enum에 있지만 실제 매핑에서 선택되지 않음).

- 1차: `pattern_type = CATEGORY_PATTERN_MAP[category]` (예: AI→tutorial, 부업→warning, 경제→number_list, 생활→resource, 쇼핑→comparison, 트렌드→number_list)
- `confidence_score < 0.3`이면 무조건 `resource`로 안전 전환 (Topic Engine의 confidence 계산과 직접 연동, `topic_engine.md` 참고)

## Hook

`HookSelector`가 `pattern_type` 기준으로 5종 중 선택: `attention`, `saveable_tip`, `authority`, `contrarian`, `pain_point`.

```text
warning -> attention, tutorial -> pain_point, comparison -> contrarian,
story -> authority, resource -> saveable_tip, number_list -> saveable_tip
```

Content Engine 단계(`content_engine.md`)에서 이 값을 그대로 쓰거나, 7종 팔레트(beginner/result_proof 추가)로 한 번 더 세분화한다.

## CTA

`CTASelector`가 `pattern_type` 기준 5종 중 선택: `save`, `comment`, `dm`, `profile`, `follow`.

```text
number_list -> save, warning -> save, comparison -> comment,
tutorial -> follow, story -> comment, resource -> save, funnel -> dm
```

## Layout (Pattern Engine 레벨, 5종)

`LayoutSelector`(pattern_engine)가 category 기준 5종 중 선택: `notebook`, `dark_editorial`, `bold_ai`, `character_diary`, `talking_head`. 이 값은 `pattern_prompt_meta.layout_type`으로 Content Engine에 전달되지만, 실제 카드뉴스 렌더링은 `cardnews.md`에서 설명하는 CardNews 레벨의 10종 Layout이 별도로 다시 계산한다.

## Pattern Selection 흐름

```text
storage/trends/selected_topic.json + trend_result.json
        ↓
KeywordWeightEngine / TopicClassifier / TopicCluster / ConfidenceScorer (topic_engine.md)
        ↓
topic_intelligence { keywords, keyword_weights, category, cluster, confidence_score, reason }
        ↓
PatternSelector -> HookSelector -> CTASelector -> LayoutSelector
        ↓
pattern_plan { pattern_type, hook_type, cta_type, layout_type, reason }
        ↓
PatternResultWriter -> storage/pattern/{pattern_result,pattern_history,pattern_statistics}.json
```

## Pattern Score

Pattern Engine 자체는 별도의 "pattern score" 필드를 노출하지 않는다 — 대신 `topic_intelligence.confidence_score`가 사실상의 신뢰도 점수 역할을 하며, 낮으면 `PatternSelector`가 안전한 `resource` 패턴으로 강제 전환한다 (`fallback_used: true`로 표시). 새로운 스코어링을 추가하려면 이 confidence 기반 안전장치를 대체하지 말고 그 위에 얹는다.

## 절대 원칙

- `PatternEngineModule`은 `storage/trends/*.json`을 직접 파일로 읽는다 (WorkflowEngine이 dict를 넘겨주는 것이 아님) — 이 방식은 `ResearchModule`/`CardNewsModule`도 동일하게 따르는 프로젝트 컨벤션이다.
- 입력이 없거나 계산이 실패해도 `status: "pattern_selected"` + `fallback_used: true`인 안전한 기본값을 반환한다. 절대 `workflow_failed`로 이어지지 않는다.
