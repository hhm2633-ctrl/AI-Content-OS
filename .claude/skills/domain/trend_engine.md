---
name: trend-engine
description: Trend Engine 전용 Domain Skill. RSS/Naver/Nate 수집, Fallback/Retry/Cache 체계, Trend Quality/선택 기준을 다룬다.
---

# Trend Engine Skill

## 대상 모듈

`modules/trend_collector/`:

- `trend_collector_module.py` (`TrendCollectorModule`) — WorkflowEngine 진입점. 후보 랭킹 + `selected_topic` 확정까지 담당.
- `trend_source_manager.py` (`TrendSourceManager`) — 소스별 수집 오케스트레이션과 fallback 체인.
- `naver_news_collector.py` (`NaverNewsCollector`) — RSS 우선, 실패 시 검색 결과 HTML 파싱으로 폴백.
- `nate_pann_collector.py` (`NatePannCollector`) — ranking/talker/issue 3개 엔드포인트.
- `retry_policy.py` (`RetryPolicy`) — 수집 재시도 정책.
- `trend_quality_scorer.py` (`TrendQualityScorer`) — 후보 품질 점수화.
- `top_topic_picker.py` (`TopTopicPicker`) — 중복 제거 + 최종 주제 선택.
- `source_health_tracker.py` (`SourceHealthTracker`) — 소스별 성공/실패 통계 누적.
- `trend_engine_guard.py` (`TrendEngineGuard`) — 최종 결과 안전망 (selected_topic 항상 보장).
- `trend_run_recorder.py` (`TrendRunRecorder`) — 실행 로그/스냅샷/최종 안전 결과 기록.

## RSS / Naver / Nate

- **Naver News**: 1순위 `naver_news_rss` (`search.naver.com/search.naver?where=rss`), 실패 시 `naver_news_html`(검색 결과 페이지 직접 파싱)으로 폴백. 둘 다 `config/trend_sources.json`의 `naver_news` 소스 설정을 따른다.
- **Nate Pann**: `pann.nate.com/talk/ranking`, `/talk/talker`, `/talk/c20002`(issue) 3개 엔드포인트를 순회하며 각각의 실패를 개별 기록한다.
- 둘 다 `urllib.request` 기반이며 API Key가 없다 — 인증 실패가 아니라 항상 네트워크/파싱 실패만 발생할 수 있다.

## Fallback 체인

```text
실시간 수집 (RSS/HTML)
   ↓ 실패
RetryPolicy 재시도 (최대 3회, 짧은 backoff)
   ↓ 실패
storage/cache/{naver_news,nate_pann}_cache.json (마지막 성공 결과)
   ↓ 캐시도 없음
config/trend_sources.json / naver_news_keywords 기반 설정 키워드 fallback
   ↓ 그래도 없음
하드코딩된 placeholder fallback
```

각 단계는 `collection_method` 값으로 구분된다: `naver_news_rss`/`naver_news_html`, `naver_news_cache`, `settings_keyword_fallback`, `placeholder_fallback`.

## Retry

- `RetryPolicy`가 재시도 횟수/딜레이를 관리한다 (Network Stability Patch 이후 최대 3회, 각 시도 사이 backoff).
- **주의**: 재시도는 근본적인 네트워크 문제(예: 테더링 환경의 간헐적 연결 거부)를 해결하지 못하고, 실패할 때마다 실행 시간만 늘린다 (`performance.md` 참고). 재시도 횟수를 늘리기 전에 실제로 도움이 되는지 먼저 확인한다.
- 각 수집기의 `last_status.service_diagnostic`(`modules/common/service_diagnostic.py` 기반)에 `error_type`(`connection_refused`/`timeout`/`auth_failed`/`rate_limited`/`unknown_error`)이 기록된다.

## Cache

- `storage/cache/naver_news_cache.json`, `storage/cache/nate_pann_cache.json` — 마지막으로 성공한 수집 결과를 저장, TTL은 `trend_collector.cache_ttl_seconds`(기본 24시간)로 관리.
- 캐시는 `storage/**`이므로 Claude가 직접 수정하지 않는다 — 오직 각 Collector가 런타임에 쓴다.

## Trend Quality / 선택 기준

`TrendQualityScorer`가 45점 기준으로 가감산:

- 제목 길이(12~55자 최적) 가점
- 카드뉴스 친화 키워드(AI/automation/content/creator/Instagram/side/income/workflow/card/news/trend/monetization) 가점
- 소스 신뢰도(naver_news=18, nate_pann=14, google_trends=16 등) 가점
- 중복/유사 제목 감점
- fallback 방식별 감점(`_cache`=-8, `settings_keyword_fallback`=-18, `placeholder_fallback`=-28)
- 민감 표현(death/crime/suicide/violence 등) 감점

`TopTopicPicker`가 제목 정규화 기반으로 중복을 제거한 뒤, `quality_score` → `score` 순으로 정렬해 최고점 후보를 `selected_topic`으로 확정하고 `storage/trends/selected_topic.json`에 저장한다. 후보가 전혀 없으면 `TrendEngineGuard`가 `last_safe_trend_result.json` 또는 placeholder로 안전하게 대체한다.

## 절대 원칙

- 이 Fallback/Retry/Cache 체인은 Sprint 1의 핵심 자산이다. 구조를 바꾸지 않고, 새 소스를 추가할 때도 동일한 패턴(수집 → 재시도 → 캐시 → 설정 fallback → placeholder)을 따른다.
