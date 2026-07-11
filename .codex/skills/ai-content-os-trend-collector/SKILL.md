---
name: ai-content-os-trend-collector
description: AI-Content-OS의 트렌드 수집기, 소스 상태, retry/cache/fallback, 후보 품질과 주제 선택을 점검하거나 수정할 때 사용한다. Naver News, Nate Pann, FM Korea, Bobaedream 수집 장애, 실행 지연, source_diagnostic, trend_result 문제를 다룬다.
---

# Trend Collector

## Context

Read only the relevant files under `modules/trend_collector/`, `config/trend_sources.json`, and the latest trend result or diagnostic. Use `ai-content-os-retry-audit` when the main symptom is slow retries.

## Workflow

1. Identify whether the issue is collection, parsing, ranking, deduplication, or fallback.
2. Preserve the chain: live collection -> bounded retry -> `storage/cache` -> settings fallback -> placeholder.
3. Record source failure reasons, final error type, collection method, and fallback use.
4. Keep `TrendEngineGuard` able to produce `selected_topic` even when every network source fails.
5. Add or update focused collector tests before running the full workflow.

## Protected Contracts

- Do not remove Naver News or Nate Pann cache/fallback behavior.
- Do not increase retry counts without measured benefit.
- Keep cache files under `storage/cache`; never commit them.
- Treat network failure as diagnostic data, not workflow failure.
- Do not fabricate popularity or engagement values.

## Verification

Run `py -m compileall src modules scripts`, focused trend tests, then `py -m src.main` at Sprint end. Confirm `01_trend_result.json`, `source_health`, and final `workflow_completed`.
