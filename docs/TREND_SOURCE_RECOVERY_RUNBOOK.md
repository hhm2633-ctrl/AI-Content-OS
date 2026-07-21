# Trend Source Recovery Runbook

## 목적과 적용 범위

이 문서는 Trend Collector에서 `connection_refused`가 발생하고 cache fallback으로 전환됐을 때 운영자가 원인을 분리하고 안전하게 복구하는 절차다. 대상 소스는 Naver News, Nate Pann, FM Korea, Bobaedream이다.

네트워크 실패는 workflow 실패가 아니다. 정상 복구 전에도 `live collection -> bounded retry -> storage/cache -> settings fallback -> placeholder` 순서로 결과를 만들고, `TrendEngineGuard`가 `selected_topic`을 유지해야 한다. cache나 fallback 결과를 실시간 인기·반응 데이터로 표현해서는 안 된다.

## 최초 확인

아래 파일을 같은 실행 시각 기준으로 확인한다.

1. `storage/workflow_results/01_trend_result.json`
2. `storage/trends/source_health.json`
3. `storage/trends/collector_statistics.json`
4. `storage/trends/trend_engine_status.json`
5. `storage/trends/selected_topic.json`
6. `storage/cache/<source>_cache.json`

각 소스에서 다음 필드를 기록한다.

- `attempted`, `success`, `count`
- `failed_reason`, `fallback_reason`, `final_error_type`
- `collection_method`, `used_cache`
- `retry_enabled`, `retry_count`
- `cache_age_seconds`, `cache_expired`
- `service_diagnostic.status`, `service_diagnostic.error_type`, `safe_message`

`success=false`이면서 `count>0`이면 실시간 수집 성공이 아니라 fallback 결과가 존재한다는 의미일 수 있다. 반드시 `collection_method`와 `used_cache`를 함께 본다.

## 공통 `connection_refused` 진단 순서

1. 네 소스가 같은 실행에서 모두 `connection_refused`인지 확인한다.
   - 모두 동일하면 개별 사이트 장애보다 실행 환경의 인터넷 차단, 방화벽, 프록시, DNS 또는 샌드박스 제한 가능성이 높다.
   - 한 소스만 실패하면 해당 사이트의 접근 정책, endpoint 변경 또는 일시 장애를 우선 의심한다.
2. `error_message`에서 어느 endpoint가 실패했는지 확인한다.
3. `retry_count`가 현재 설정 범위인지 확인한다. 기본 구성은 최초 1회 + 재시도 2회다. 운영 근거 없이 재시도 횟수를 늘리지 않는다.
4. 마지막 성공 시각과 반복 실패 횟수를 `collector_statistics.json`에서 확인한다.
5. cache 유무와 나이를 확인한 뒤 아래 cache 판단표를 적용한다.
6. 접근 권한이나 외부 네트워크 변경이 필요하면 직접 우회하지 말고 승인 게이트로 넘긴다.

## 소스별 진단

### Naver News

1. `error_message`에 각 검색어별 실패가 기록됐는지 확인한다.
2. `collection_method`를 판정한다.
   - `naver_news_api`: 실시간 성공
   - `naver_news_cache`: cache fallback
   - `settings_keyword_fallback`: 실제 뉴스 근거가 아닌 설정 키워드 fallback
   - `placeholder_fallback`: 최후 안전 fallback
3. API 키 유무가 필요한 구성이라면 `service_diagnostic.api_key_present`만 확인한다. 키 원문은 로그나 보고서에 출력하지 않는다.
4. `settings_keyword_fallback` 결과에는 기사 URL·발행 시각·실시간 인기도가 없으므로 뉴스 근거로 사용하지 않는다.
5. API 키 발급·교체, 방화벽 예외, 외부 네트워크 허용은 CTO 승인 후 진행한다.

### Nate Pann

1. `ranking`, `talker`, `issue` endpoint별 실패를 `error_message`에서 확인한다.
2. `nate_pann_cache`이면 cache의 `updated_at`, `count`, 각 항목의 `link`를 확인한다.
3. 실제 게시글이 아닌 내비게이션 제목을 탐지한다.
   - 차단 대상 예: `톡커들의 선택 명예의 전당`, `톡톡`, `판포토`, `이슈`, `랭킹`, `전체`, `댓글`, `이전`, `다음`
   - 제목 링크가 게시글이 아니라 `/talk/ranking` 같은 목록 페이지면 후보에서 제외한다.
   - 실제 게시글처럼 보이는 제목이라도 원문 URL과 제목이 일치하는지 게시 전 확인한다.
4. 잘못된 제목이 `selected_topic`이면 그 실행 결과는 발행 근거로 사용하지 않는다. 수정된 필터가 적용된 다음 실행에서 새 주제를 확인한다.
5. 로그인, 쿠키, 실제 SNS/커뮤니티 크롤링 우회가 필요하면 외부 승인 없이 구현하거나 실행하지 않는다.

### FM Korea

1. `best`, `best2` endpoint별 실패를 확인한다.
2. `fmkorea_cache`이면 cache 생성 시각과 각 항목의 게시글 URL을 확인한다.
3. 목록·메뉴·공지 제목이 후보에 섞이지 않았는지 확인한다.
4. cache가 stale이면 최신 트렌드로 간주하지 않고, 과거 후보라는 사실을 표시한다.
5. 접근 차단을 우회하기 위한 로그인, 세션, 프록시 또는 scraping 변경은 승인 전 금지한다.

### Bobaedream

1. `best`, `info` endpoint별 실패를 확인한다.
2. `bobaedream_cache`이면 cache 생성 시각과 `/view?...` 등 실제 게시글 링크 여부를 확인한다.
3. `베스트`, `인기글`, `공지`, `이벤트`, `전체`, `이전`, `다음`, `로그인` 같은 내비게이션·메뉴 제목이 후보에 없는지 확인한다.
4. stale cache는 최신 사회 반응의 증거로 사용하지 않는다.
5. 사이트 접근 정책을 우회하는 변경은 승인 전 금지한다.

## Retry와 cache 판단

| 상태 | 판단 | 운영 조치 |
|---|---|---|
| 실시간 성공, `success=true` | 정상 | 결과 수와 URL 표본 확인 |
| 실시간 실패, fresh cache 사용 | 제한적 운영 가능 | fallback 표시 유지, 최신성 한계 기록 |
| 실시간 실패, stale cache 사용 | 발행 근거로 부적합 | 후보 탐색용으로만 취급하고 원문 재검증 |
| cache 없음, settings fallback | 실제 출처 근거 없음 | 아이디어 후보로만 사용 |
| placeholder fallback | workflow 안전 유지 전용 | 발행·성과 판단 금지 |
| 반복 `connection_refused` | 환경 또는 접근 정책 문제 가능 | 통합 환경의 네트워크 상태와 승인 게이트 확인 |

기본 stale 기준은 `cache_ttl_seconds=86400`, 즉 24시간이다. `cache_age_seconds > 86400` 또는 `cache_expired=true`이면 stale이다. TTL을 늘려 장애를 숨기지 않는다. 사업상 다른 TTL이 필요하면 소스 특성, 허용 가능한 최신성, 실패 빈도에 대한 근거와 함께 CTO 승인을 받는다.

cache 파일은 `storage/cache` 아래에만 둔다. Git에 포함하거나 수동으로 최신 데이터처럼 조작하지 않는다. cache 삭제·재생성은 통합 담당자가 영향 범위를 확인한 후 수행한다.

## 재실행과 복구 확인

통합 담당자가 저장소 규칙에 따라 다음 순서로 검증한다.

1. `py -m compileall src modules scripts`
2. Trend focused tests
3. `py -m src.main`

재실행 후 아래를 모두 확인한다.

- 최종 결과가 `workflow_completed`다.
- `01_trend_result.json`의 `collection_summary`가 최신 실행 시각으로 갱신됐다.
- 각 소스의 `retry_count`가 설정 범위를 넘지 않는다.
- 실시간 복구된 소스는 `success=true`이며 fallback collection method가 아니다.
- 실패가 지속되는 소스는 정확한 `failed_reason`, `fallback_reason`, `collection_method`를 보존한다.
- `source_health.json`과 `collector_statistics.json`이 같은 상태를 반영한다.
- `selected_topic`이 실제 후보 제목과 URL에 연결된다.
- 네이트판 내비게이션 제목이 후보와 `selected_topic`에서 제외됐다.
- Research 결과가 cache/settings fallback을 실시간 다중 출처 근거로 과장하지 않는다.

일부 소스만 복구돼도 나머지 실패를 숨기지 않는다. 전체 workflow 성공과 모든 외부 소스의 실시간 성공은 서로 다른 상태다.

## 외부 승인 게이트

다음 작업은 CTO의 명시적 승인 전 수행하지 않는다.

- 방화벽, 프록시, DNS, 샌드박스 또는 조직 네트워크 정책 변경
- 외부 API 키 발급·교체·과금 활성화
- 로그인, 쿠키, 세션 또는 계정 기반 접근
- 사이트 차단 우회, scraping 방식 확대, 새 crawler 도입
- endpoint 추가·교체 또는 요청 빈도 증가
- retry 횟수나 timeout 증가
- cache TTL 변경, cache 강제 삭제 또는 운영 데이터 재생성
- 새 외부 소스를 실시간 근거로 편입

승인 요청에는 영향을 받는 소스, 최근 실패 횟수, 마지막 성공 시각, 현재 fallback 방식, cache 나이, 예상 비용·운영 위험, 되돌리기 방법을 포함한다.

## CTO 보고 형식

- 실행 시각:
- 소스별 실시간 상태:
- `failed_reason` / `final_error_type`:
- retry 횟수:
- fallback 방식:
- cache 나이 / stale 여부:
- 선택 주제와 실제 URL 일치 여부:
- 잘못된 내비게이션 제목 발견 여부:
- `workflow_completed` 여부:
- 승인 필요 작업:
