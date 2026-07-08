# Sprint 1: Trend Engine 운영형 완성

## 목표

수집된 국내 트렌드 후보를 안정적으로 수집, 평가, 중복 제거, 최종 선택하여 Research/Content 단계로 넘길 수 있게 만든다.

## 완료된 작업

1. 네이버 뉴스 수집기 운영형 fallback/cache
2. 네이트판 수집기 운영형 fallback/cache
3. Trend Quality Scoring v1
4. Selection Reason v1
5. Top Topic Picker
6. Duplicate Removal v1
7. `selected_topic.json` 저장
8. `trend_result.json` selected_topic 포함
9. Research Module selected_topic 우선 사용
10. Source Health v1 기록
11. Collector Statistics v1 기록
12. Retry Policy v1
13. Cache TTL v1
14. Source Health retry/cache TTL 필드 기록
15. Collector Statistics fallback 사용 횟수 누적
16. `trend_result.json` trend_engine_status 포함
17. `trend_run_log.jsonl` 실행 로그 기록
18. Trend Result snapshot 자동 저장
19. `trend_engine_status.json` 복구 요약 기록
20. `last_safe_trend_result.json` 보존
21. Trend Engine Guard v1

## 완료 조건

- `py -m compileall src modules scripts` 성공
- `py -m src.main` 성공
- `workflow_completed` 확인
- `selected_topic.json` 생성 및 유지
- `trend_result.json`에 selected_topic 포함
- `trend_result.json`에 source_health_summary 포함
- `trend_result.json`에 trend_engine_status 포함
- `source_health.json` 생성 및 retry/cache TTL 필드 기록
- `collector_statistics.json` 생성 및 total_fallback_used 기록
- `trend_run_log.jsonl` 생성
- `storage/trends/snapshots`에 trend_result snapshot 생성
- `trend_engine_status.json`에 recovery 필드 기록
- `last_safe_trend_result.json` 생성
- Research가 selected_topic 기반으로 실행
- `PROJECT_SNAPSHOT.md` / `CHANGELOG.md` 업데이트

## Sprint 1 완료 보고서

### 최종 판정

- Sprint 1 Trend Engine 운영형 완료
- 네트워크/사이트/LLM/이미지 실패에도 workflow가 죽지 않는 fallback-first 구조 유지
- 수집 후보 평가, 중복 제거, 최종 주제 선택, Research 연동까지 완료
- source health, collector statistics, retry, cache TTL, run log, snapshot, recovery summary, last safe result 보존 완료

### 운영 산출물

- `storage/trends/trend_result.json`
- `storage/trends/selected_topic.json`
- `storage/trends/source_health.json`
- `storage/trends/collector_statistics.json`
- `storage/trends/trend_engine_status.json`
- `storage/trends/trend_run_log.jsonl`
- `storage/trends/last_safe_trend_result.json`
- `storage/trends/snapshots/*_trend_result.json`

### 남은 개선 후보

- Source Health dashboard
- Collector Statistics dashboard
- 마지막 안전 결과 기반 자동 복구 연동 고도화
- Content Engine에서 selected_topic 품질 활용 강화

## 운영 규칙

- 기존 `WorkflowEngine` 구조를 유지한다.
- 실행 명령은 `py -m src.main`만 사용한다.
- `python -m src.main`은 사용하지 않는다.
- 기존 네이버 뉴스/네이트판 fallback/cache 구조를 유지한다.
- 수집 실패는 `workflow_failed`가 아니라 fallback 이벤트로 처리한다.
- 실행 로그, 스냅샷, 마지막 안전 결과를 보존한다.
