# AI-Content-OS Module Status

## Completed

- WorkflowEngine 정상
- `workflow_completed` 정상
- Project snapshot/changelog 자동 업데이트
- TrendCollector
- TopicEngine
- Research
- Content
- ImagePrompt
- ImageGeneration
- CardNews
- Publishing
- Publishing v2
- Trend Source Manager v1
- 네이버 뉴스 수집기 운영형 fallback/cache
- 네이트판 수집기 운영형 fallback/cache
- Trend Quality Scoring v1
- Selection Reason v1
- Top Topic Picker
- Duplicate Removal v1
- `selected_topic.json`
- `trend_result.json` selected_topic 포함
- Research Module selected_topic 연동
- Source Health v1
- Collector Statistics v1
- Retry Policy v1
- Cache TTL v1
- Source Health retry/cache TTL 필드 기록
- Collector Statistics fallback 사용 횟수 누적
- `trend_result.json` trend_engine_status 포함
- Trend Run Log v1
- Trend Result Snapshot v1
- Trend Recovery Summary v1
- Last Safe Trend Result v1
- Trend Engine Guard v1

## Operational Complete

- Sprint 1 Trend Engine 운영형 완료
- 수집 실패는 fallback/cache/retry/status/log/snapshot 흐름으로 처리
- `workflow_completed` 유지
- `selected_topic.json` 및 Research selected_topic 연동 유지
- `trend_run_log.jsonl`, `trend_engine_status.json`, `last_safe_trend_result.json` 보존

## Next

- M2 Content Engine 고도화
- Source Health dashboard
- Collector Statistics dashboard
- 마지막 안전 결과 기반 자동 복구 연동 고도화

## Notes

- 실행 명령은 `py -m src.main`만 사용한다.
- `python -m src.main`은 사용하지 않는다.
- 인터넷/LLM/이미지 실패는 workflow 실패가 아니라 fallback 이벤트로 기록한다.
- 네이버 뉴스와 네이트판 상태는 독립적으로 기록한다.
