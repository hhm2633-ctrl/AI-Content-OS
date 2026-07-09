---
name: content-engine
description: Content Engine 전용 Domain Skill. Prompt 구성, Brand Profile, Duplicate Check, Publishing Hint, Quality Score를 다룬다.
---

# Content Engine Skill

## 대상 모듈

`modules/content/`:

- `content_module.py` (`ContentModule`) — WorkflowEngine 진입점. `research_result`를 받아 카드뉴스 문안(4 slides + caption + hashtags)을 만든다.
- `content_prompt_builder.py` (`ContentPromptBuilder`) — pattern-aware 프롬프트 조립.
- `pattern_prompt_router.py` (`PatternPromptRouter`) — pattern_type별 `prompts/patterns/*.md` 가이드 선택.
- `hook_strategy.py` (`HookStrategy`) / `cta_strategy.py` (`CTAStrategy`) / `slide_strategy.py` (`SlideStrategy`) — Pattern Engine 결과를 Content 레벨에서 한 번 더 세분화.
- `content_quality_scorer.py` (`ContentQualityScorer`)
- `content_duplicate_detector.py` (`ContentDuplicateDetector`)
- `publishing_hint_generator.py` (`PublishingHintGenerator`)
- `brand_rule_evaluator.py` (`BrandRuleEvaluator`)

## Prompt

- `ContentModule.run()`은 항상 `ContentPromptBuilder.build(research_result)`를 먼저 시도한다.
- `research_result.pattern_plan`이 없거나 `pattern_type`이 비어 있으면 `build()`가 `None`을 반환하고, `ContentModule`은 **즉시 legacy 프롬프트**(`_legacy_system_prompt`/`_legacy_user_prompt`, Sprint 1부터 있던 고정 프롬프트)로 자동 복귀한다.
- pattern-aware 경로에서는 `PatternPromptRouter`(패턴 가이드) + `HookStrategy`/`CTAStrategy`(세분화된 hook/cta) + `SlideStrategy`(패턴별 슬라이드 blueprint) + Brand Profile을 모두 조합해 system/user prompt를 만들지만, **LLM에 요구하는 최종 JSON 스키마(title/slides[4]/caption/hashtags/status)는 절대 바꾸지 않는다** — 이 스키마가 바뀌면 `_safe_json_parse`/`_normalize_slides`가 깨진다.
- 결과에 `prompt_source`(`"pattern_aware"`/`"legacy"`)와 `pattern_prompt_meta`가 참고용으로 남는다.

## Brand Profile

- `config/brand_profile.json`: `brand_name`, `voice`, `tone_keywords`, `banned_words`, `target_audience`, `cta_style`.
- `ContentPromptBuilder`와 `BrandRuleEvaluator`가 각각 독립적으로 이 파일을 읽는다 (파일 없거나 손상돼도 동일한 하드코딩 fallback 값 사용).
- `BrandRuleEvaluator.evaluate()`가 `banned_words` + 내장 과장 수익 표현 정규식(`100% 보장`, `무조건 수익/성공`, `확정 수익` 등)을 검사해 `brand_rule_passed`를 결정한다.

## Duplicate Check

- `ContentDuplicateDetector`가 `storage/content/content_history.json`의 최근 30건과 제목/Hook/CTA 텍스트를 `difflib.SequenceMatcher`로 비교한다.
- `duplicate_risk`: 유사도 ≥0.9 `high`, ≥0.6 `medium`, 그 외 `low`.
- 매 실행마다 `record()`로 이력에 추가된다 (최대 500건 유지). fallback 콘텐츠도 이력에 남으므로, LLM이 반복 실패하면 매번 동일한 fallback 문구 때문에 `duplicate_risk: high`가 뜨는 것이 정상 동작이다.

## Publishing Hint

- `PublishingHintGenerator`가 `pattern_plan.cta_type`(또는 CTA 슬라이드 텍스트에서 추론)을 `save`/`comment`/`follow`/`profile`/`dm` 중 하나로 매핑해 `recommended_action`을 만든다.
- `caption_direction`, `hashtag_direction`(pattern_type별), `checklist`(업로드 전 체크포인트)를 함께 제공한다.

## Quality Score

`ContentQualityScorer`가 100점 만점 가점/감점제로 `quality_score`(0.0~1.0)를 계산한다:

- 가점: hook 슬라이드 존재(+15), CTA 슬라이드 존재(+15), 4-슬라이드 구조 완성(+20), selected_topic/keyword 반영(+15), `prompt_source=="pattern_aware"`(+15), caption 충실도(+10), hashtag 개수(+10)
- 감점: 빈약한 슬라이드(개당 -5), 슬라이드 문구 중복(최대 -15), `fallback_used`(-30)

## 최종 통합 필드

`content_result.content_intelligence`: `quality_score`, `duplicate_risk`, `brand_rule_passed`, `publishing_hint`, `recommendations`, `details`(하위 계산 전체 보존).

## 절대 원칙

- 4개 Intelligence 헬퍼는 전부 자체 try/except로 예외를 삼키고 안전 기본값을 반환한다 — 실패해도 `content_intelligence`는 항상 존재해야 한다.
- `content_result`의 최상위 스키마(title/slides/caption/hashtags/status)는 CardNewsModule/PublishingModule이 그대로 소비하므로, Intelligence 필드는 항상 **추가 필드**로만 붙인다.
