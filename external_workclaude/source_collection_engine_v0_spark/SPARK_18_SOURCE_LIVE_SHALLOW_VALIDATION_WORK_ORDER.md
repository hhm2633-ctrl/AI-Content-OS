# Spark Work Order — 18-Source Live Shallow Validation

## Objective

Run the existing daily shallow collection once for 2026-07-15 and report per-source results for
the 18 retained sources. This is an explicitly approved live collection validation, not deep-dive
crawling, browser automation, bypassing, publishing, or a recurring schedule.

## Required source scope

`naver_news`, `daum_news`, `nate_news_rank`, `yonhap`, `newsis`, `news1`,
`hankyung_economy`, `mk_economy`, `moneytoday`, `edaily`, `nate_pann`, `fmkorea`,
`bobaedream`, `dcinside`, `theqoo`, `ppomppu`, `ruliweb`, `dogdrip`.

## Forbidden source/actions

- Never call `google_news_kr`, `ap_world`, `bbc_world`, `reuters_world`, or `instiz`.
- No detail-page/body bulk collection, browser/Chrome, anti-bot bypass, login, credentials, proxy,
  actual publishing, code/config/test edits, full WorkflowEngine run, Git, or recurring automation.

## Owned outputs

- Generated files only under `storage/source_intake/2026-07-15/`.
- `external_workclaude/source_collection_engine_v0_spark/AUTO_SPARK_STATUS_18_SOURCE_LIVE_SHALLOW_VALIDATION.md`.

## Execution contract

- Preflight the daily plan and stop NO-GO if the attempted source set can include anything outside
  the required 18.
- Invoke `execute_daily_shallow_collection(today="2026-07-15")` once using current repository code.
- Network failures are data, never a reason to fabricate results or retry without the collector's
  existing bounded policy.
- Do not patch storage by hand; only persist through the existing executor.

## Handoff

- List attempted/success/fallback/skipped/failed counts and each source's final status.
- Confirm forbidden sources had zero attempts.
- State output path and any timeout/error details.
