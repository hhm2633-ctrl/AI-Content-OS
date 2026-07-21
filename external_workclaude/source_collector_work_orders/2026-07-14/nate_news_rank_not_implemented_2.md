# Collector Work Order

## objective
- implement the `nate_news_rank` collector path and wire source intake metadata for status `NOT_IMPLEMENTED`

## owned files
- modules/trend_collector/nate_news_rank_collector.py when this source needs a new collector
- modules/source_intake/source_capability_map.py only if capability metadata must be extended
- tests/test_nate_news_rank_collector.py or focused source-intake collector tests

## prohibited files
- modules/workflow_engine.py
- modules/card_news
- modules/publishing
- modules/compliance
- unrelated existing collectors

## required reading
- modules/source_intake/collection_gap_runner.py
- collection gap queue item: source_id, status, lane_impact
- affected lanes: entertainment_news, news_society_economy

## completion checks
- collector module can import and load without runtime crash
- queue-related integration contract tests pass with this source id
- new collector output shape matches existing source intake contract

## handoff format
- status: done
- owner: Spark -> Claude
- files_touched: comma-separated list
- blockers: short bullet list
- test result summary
