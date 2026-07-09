---
name: cardnews-engine
description: CardNews Engine 전용 Domain Skill. 레이아웃, 슬라이드, 강조, CTA, 가독성, 이미지 배치, 품질, QA를 다룬다. 기존 Layout Engine을 우선 사용하고 새 Layout을 만들지 않는다.
---

# CardNews Engine Skill

## 대상 모듈

`modules/card_news/`:

- `card_news_module.py` (`CardNewsModule`) — WorkflowEngine이 호출하는 진입점. `content_result`, `image_generation_result`를 받아 4장의 PNG(`storage/card_news/card_news_*.png`)와 `card_news_result` dict를 반환한다.
- `layout_selector.py` (`LayoutSelector`) — Pattern/Topic/Brand Profile/Content Intelligence를 조합해 `layout_type`을 고른다.
- `layout_rule_engine.py` (`LayoutRuleEngine`) — `templates/card_news_layout_rules.json`에서 레이아웃별 시각 규칙을 읽는다.
- `slide_designer.py` (`SlideDesigner`) — 슬라이드별 title/body 위치, 강조 박스 여부, CTA 영역 여부를 결정한다.
- `highlight_engine.py` (`HighlightEngine`) — 강조할 키워드/숫자/경고/비교/CTA 단어를 추출한다.
- `card_news_text_optimizer.py` (`CardNewsTextOptimizer`) — 렌더링 직전 텍스트를 규칙 기반으로 다듬는다.
- `card_news_quality_checker.py` (`CardNewsQualityChecker`) — 생성된 결과물을 자동 QA한다.

## 레이아웃

지원 Layout은 정확히 10종이며 `templates/card_news_layout_rules.json`의 `layouts` 키가 유일한 소스다:

```text
notebook, dark_editorial, bold_ai, character_diary,
comparison, tutorial, checklist, timeline, warning, number_list
```

각 레이아웃은 `title_style`, `body_style`, `image_ratio`, `cta_position`, `highlight_color`, `background_tone`을 가진다.

**⚠️ 기존 Layout Engine 우선 사용 — 새로운 Layout 생성 금지.**
새로운 시각 스타일 요청이 오면:

1. 먼저 기존 10종 중 가장 가까운 것을 고를 수 있는지 검토한다.
2. `LayoutSelector`의 `PATTERN_TYPE_LAYOUT_MAP`/`CATEGORY_LAYOUT_MAP` 매핑을 조정하는 것으로 해결되는지 검토한다.
3. `templates/card_news_layout_rules.json`의 기존 항목 값(색상/스타일 문자열)을 조정하는 것으로 해결되는지 검토한다.
4. 정말 11번째 레이아웃이 필요하다고 판단되면, 반드시 사용자에게 먼저 확인을 받는다 — Claude 임의로 새 레이아웃 타입을 추가하지 않는다.

## 슬라이드

- 슬라이드는 항상 4장 고정이며 role은 `hook`/`problem`/`solution`/`cta`다. `CardNewsModule`과 `ImagePromptModule`이 이 4장 구조를 전제로 동작하므로, 지시 없이 슬라이드 수를 바꾸지 않는다.
- `SlideDesigner`는 role별 `title_position`(top/center/bottom)과 `body_position`(below_title/middle/bottom)을 결정하고, `problem`/`solution` role에는 `highlight_box: true`, `cta` role에는 `cta_area: true`를 부여한다.
- 패턴별로 5단계 개념(blueprint)이 있어도(예: warning의 hook/problem/reason/solution/cta), 최종 렌더링은 항상 4개 canonical role로 압축된다. 5장으로 실제 확장하려면 `CardNewsModule`/`ImagePromptModule`을 함께 바꿔야 하므로 별도 Sprint로 승인받는다.

## 강조

- `HighlightEngine`이 숫자(`\d+[%가-힣]*`), 경고 단어(주의/위험/실수/손해/절대/금지), 비교 단어(보다/대신/vs/비교/차이), CTA 단어(저장/팔로우/댓글/공유/DM/프로필), topic keyword를 추출한다.
- **안전 우선 원칙**: 강조는 텍스트 파편을 잘라 색칠하는 방식이 아니라 **강조 박스(좌측 accent bar)**, **강조 배지(뱃지-카드박스 사이 여백의 키워드 태그)**, **키워드 태그** 방식으로만 표현한다. 단어 단위 인라인 색상 변경처럼 줄바꿈을 깨뜨릴 수 있는 방식은 쓰지 않는다.

## CTA

- `cta_position`은 `bottom_center`/`bottom_left`/`bottom_right` 중 하나이며 레이아웃별로 다르다.
- CTA 슬라이드(role="cta") 또는 `slide_design.cta_area=true`인 슬라이드에만 CTA 영역(강조색 바)을 그린다.

## 가독성 (CardNewsTextOptimizer 규칙)

- headline 권장 길이: **18자 이하** (단어 경계에서 자연스럽게 자름, "..." 사용 금지)
- body 한 줄 권장 길이: **24자 이하**
- body는 **3문장 이하** 우선 (CTA 슬라이드는 **2문장 이하**)
- 빈 문장 제거, 슬라이드 내 중복 문장 제거
- 이 최적화는 **렌더링용 사본에만** 적용된다 — `content_result` 원본은 훼손하지 않는다.

## 이미지 배치

- 배경은 `ImageGenerationModule`이 만든 1024x1024 PNG를 1080x1080으로 리사이즈해 사용하거나, 이미지가 없으면 페이지별 solid color로 대체한다.
- `image_ratio`(예: dark_editorial의 `4:5`)는 현재 **메타데이터로만 보존**되고 실제 크롭에는 반영되지 않는다 (알려진 한계, Sprint 7 TODO).

## 카드뉴스 품질 / QA

- `design_quality_result`: `text_optimized`, `headline_trimmed_count`, `body_trimmed_count`, `duplicate_removed_count`, `cta_optimized`, `readability_warnings`, `fallback_used`
- `card_news_quality` (`CardNewsQualityChecker`): `qa_score`(0.0~1.0), `passed`, `checks`(10개 항목: PNG 존재/카드 수/파일 크기/해상도/layout_result·rendering_result 존재/layout_applied/fallback_used/highlight 존재/CTA 존재/design_quality_exists), `warnings`, `recommendations`. 결과는 `storage/card_news/card_news_quality.json`에 저장된다 (Claude가 직접 쓰지 않음, `CardNewsQualityChecker`가 런타임에 씀).

## Fallback 원칙

레이아웃 선택, 텍스트 최적화, QA 계산 중 어느 하나가 실패해도 실제 PNG 렌더링(`_create_background`/`_draw_card`)에는 영향이 없어야 한다. 항상 "메타데이터 계산 실패 → 안전한 기본값 + `fallback_used: true`"로 처리하고, 카드 자체는 기존 방식으로 계속 생성되어야 한다.
