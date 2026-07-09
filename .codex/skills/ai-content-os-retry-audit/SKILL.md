---
name: ai-content-os-retry-audit
description: AI-Content-OS의 네트워크/API retry, fallback, service_diagnostic, 실행시간 증가 문제를 검수하고 최적화 방향을 제안하는 절차.
---

# AI-Content-OS Retry Audit Skill

## Purpose

Use this skill when workflow execution becomes slow, appears hung, or network/API retries may be causing long silent waits.

## Protected Behavior

Network, browser, LLM, and image failures must not cause `workflow_failed`.

They must be recorded as:

- retry
- fallback
- cache
- status
- diagnostic event

Final workflow should still reach:

```text
workflow_completed
```

## First Check

Before changing code, determine whether a process is truly running or already completed.

Read-only checks are allowed:

- process list
- workflow result timestamp
- `storage/workflow_results/99_final_result.json`
- `storage/runtime/service_diagnostic.json` if present
- recent changelog entries

Do not use destructive commands.

## Known Issue

Retry backoff can make the workflow appear hung.

Example:

- LLM retry: 2s / 5s / 10s
- Image retry per image
- Trend collector retry
- Multiple fallback sources

This can cause several minutes of silence even when the workflow is still progressing.

## Audit Targets

Inspect these files when relevant:

- `src/llm_client.py`
- `modules/image_generation/image_generation_module.py`
- `modules/trend_collector/naver_news_collector.py`
- `modules/trend_collector/nate_pann_collector.py`
- `modules/trend_collector/retry_policy.py`
- `modules/common/service_diagnostic.py`

## Optimization Direction

Prefer:

- fast fallback
- bounded retry
- maximum total timeout
- clear diagnostic logging
- no infinite waiting
- no workflow failure for external service problems

Avoid:

- long silent sleep
- unbounded retries
- blocking all images because one API fails
- changing WorkflowEngine structure

## Final Report Format

```text
[Retry Audit Report]

Is process still running:
- yes/no

Last workflow result:
- timestamp
- status

Retry sources:
- LLM
- Image
- Naver
- Nate Pann

Observed fallback:
- yes/no

Execution time:
- seconds

Risk:
- ...

Recommendation:
- keep / reduce retry / add timeout cap / fast fallback
```
