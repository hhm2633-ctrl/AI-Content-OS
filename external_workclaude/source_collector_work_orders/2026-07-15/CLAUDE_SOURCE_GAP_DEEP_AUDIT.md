# Source Gap Deep Audit — CTO Recovery Completion

Date: 2026-07-15  
Scope: repository truth + historical artifacts only; no browser, live network, login, credentials, UGC capture, or production implementation.

## Decision

**Next implementation source: `yonhap`. Implementation GO; live activation NO_GO until a manual robots/terms review pins an approved public list endpoint.**

This split permits deterministic fixture-driven code and executor wiring now while preventing an unverified live crawler from being treated as policy-approved.

## Actual runtime truth versus stale artifact truth

The 2026-07-14 Source Intake artifacts report 14 `NOT_IMPLEMENTED` sources and only 3 operational sources. That is historical evidence, not current truth. Current repository inspection shows:

- Configured sources: **23**
- Daily-plan sources: **19**
- Actually callable now: **13**
- Not callable now: **10**
- Callable through `TrendSourceManager`: `naver_news`, `nate_pann`, `fmkorea`, `bobaedream`, `moneytoday`
- Callable through the executor direct-factory seam: `daum_news`, `news1`, `mk_economy`, `nate_news_rank`, `newsis`, `theqoo`, `edaily`, `hankyung_economy`

The stale claim for Daum and News1 is specifically superseded by the completed SC-S direct-factory connection. Several other 2026-07-14 `NOT_IMPLEMENTED` claims are also superseded by current collector files and factories. `COLLECTOR_METHODS` membership alone is not counted as support.

## Inventory and decisions

Scores are CardNews ROI / technical feasibility / safety, each out of 100.

| Source | Collector state | Executor truth | Lane coverage | Decision | Scores |
|---|---|---|---|---|---|
| naver_news | implemented | callable | news_society_economy, entertainment_news, lifestyle_knowledge | GO | 92/90/75 |
| daum_news | implemented | callable | news_society_economy, entertainment_news, lifestyle_knowledge | GO | 94/88/78 |
| nate_news_rank | implemented | callable | news_society_economy, entertainment_news | GO | 88/90/76 |
| google_news_kr | not_implemented | not_callable | - | DEFER | 65/72/68 |
| yonhap | not_implemented | not_callable | news_society_economy | GO | 96/82/74 |
| newsis | implemented | callable | news_society_economy, lifestyle_knowledge | GO | 92/86/76 |
| news1 | implemented | callable | news_society_economy, lifestyle_knowledge | GO | 92/84/75 |
| hankyung_economy | implemented | callable | news_society_economy | GO | 82/82/72 |
| mk_economy | implemented | callable | news_society_economy | GO | 78/84/72 |
| moneytoday | implemented | callable | news_society_economy | GO | 80/85/73 |
| edaily | implemented | callable | news_society_economy | GO | 80/84/72 |
| ap_world | not_implemented | not_callable | - | DEFER | 52/66/64 |
| bbc_world | not_implemented | not_callable | - | DEFER | 54/66/64 |
| nate_pann | implemented | callable | dopamine_community, beauty_fashion, lifestyle_knowledge | GO | 78/86/58 |
| fmkorea | implemented | callable | dopamine_community, beauty_fashion | GO | 76/84/55 |
| bobaedream | implemented | callable | dopamine_community | GO | 74/84/54 |
| dcinside | parser_only | not_callable | entertainment_news, dopamine_community | FIXTURE_ONLY | 70/62/38 |
| theqoo | implemented | callable | entertainment_news, dopamine_community, beauty_fashion | GO | 76/78/50 |
| ppomppu | not_implemented | not_callable | entertainment_news | FIXTURE_ONLY | 62/60/40 |
| ruliweb | not_implemented | not_callable | dopamine_community | FIXTURE_ONLY | 58/60/40 |
| dogdrip | not_implemented | not_callable | dopamine_community | FIXTURE_ONLY | 58/60/38 |
| reuters_world | not_implemented | not_callable | - | BLOCKED | 50/20/20 |
| instiz | diagnostic_only | not_callable | dopamine_community, lifestyle_knowledge | BLOCKED | 55/15/15 |

Decision totals: **GO 14, FIXTURE_ONLY 4, DEFER 3, BLOCKED 2.**

## Important boundaries

- `dcinside_parser.py` is parser-only and is not a production collector.
- `instiz_diagnostic_contract.py` records the block; it is not a collector.
- `mk_economy` support is limited to the approved **MK Pick** surface.
- Naver comments/reactions remain **FIXTURE_ONLY** unless separately approved.
- Repository `access_status: ok` or an HTTP 200 does not prove external permission.
- Community sources are list-metadata only. Usernames, profiles, comment bodies, and other PII/UGC are outside scope.
- All selected topics from community sources still require evidence and second-source checks.

## Selected next source: Yonhap

### Why it wins

Yonhap is already configured and included in `news_society_economy`, the lane most in need of independent news evidence. A title/link/rank-only collector adds a wire-service second source without authentication, comments, profiles, image reuse, or article-body storage. The change is small and reversible: one collector, one fixture test, and one direct executor factory.

### Implementation contract

- Surface: public non-auth Yonhap headline/list metadata under the configured origin only.
- Fields: title, canonical link, publisher, visible published time, category, one-based list rank, existing source metadata, collection method, timestamps, and service diagnostic.
- Forbidden: body text, images, comments, users, profiles, cookies, credentials, private APIs, proxying, and bypass.
- Rank: verified list order only; never infer popularity or engagement.
- Dedup: canonical URL, then normalized title; first occurrence wins.
- Retry/fallback: existing bounded RetryPolicy; valid cache under `storage/cache/yonhap_cache.json`; then empty diagnostic result. Never fabricate a headline.
- Attribution: `publisher=연합뉴스` plus original canonical link.
- Executor: add `yonhap` mapping and `YonhapCollector` direct factory in `daily_collection_executor.py`.
- Live gate: fixture/code may be implemented now; network activation remains disabled until an operator records robots/terms evidence and the exact approved list endpoint.

The full machine-readable contract is in `SOURCE_IMPLEMENTATION_DECISION_MATRIX.json`.

## Risks and blockers

1. No external permission was proven in this offline audit. Therefore live activation is blocked even though code implementation is approved.
2. Historical storage artifacts must be regenerated after the current callable set is integrated; otherwise dashboards will continue to show false `NOT_IMPLEMENTED` claims.
3. Unsupported community sources remain fixture-only because UGC/privacy/attribution and terms risks exceed current ROI.
4. Reuters and Instiz remain blocked by recorded HTTP 401/403. No bypass is permitted.
5. AP/BBC/Google News are outside the current daily plan and deferred to avoid translation, duplication, and copyright cost.

## Validation

- JSON schema version: `source_implementation_decision_matrix_v1`
- Configured source entries expected: 23
- Duplicate source IDs expected: 0
- Config omissions expected: 0
- Exactly one selected next source: `yonhap`
- Implementation gate: **GO**
- Live activation gate: **NO_GO_PENDING_MANUAL_POLICY_CHECK**

