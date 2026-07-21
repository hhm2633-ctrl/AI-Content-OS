# CTO Work Order — Bobaedream Visible Summary

## Objective

Capture an honest summary only when a visible list-row snippet or summary attribute exists. Keep
empty summary when no snippet is present; do not add detail-page crawling. Implement first and run
tests only in the final joint batch.

## Exclusive owned files

- `modules/trend_collector/bobaedream_collector.py`
- `tests/test_community_metrics_parser.py`

## Prohibited files/actions

- Do not edit Naver/FMKorea files, config, storage, WorkflowEngine, or Git.
- No browser/live network, early tests/compile, or full workflow.

## Completion checks

- Visible snippet/attribute extraction, HTML cleanup, absent-snippet honesty, existing metric regression.
