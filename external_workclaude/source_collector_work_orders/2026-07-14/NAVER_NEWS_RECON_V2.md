# NAVER NEWS RECON V2 (read-only reconnaissance)

- Date: 2026-07-15 (KST)
- Scope: `modules/trend_collector/naver_news_collector.py` vs. current public Naver News surfaces.
- Mode: read-only GET probes only (no login, no account/social actions, no code changes).
- Companion contract: `NAVER_NEWS_FIXTURE_CONTRACT_V2.json`

## 1. Root cause of parse_failed / settings fallback

The collector fails today for two stacked reasons, in this exact order:

1. **RSS path is dead.** `_collect_from_rss()` requests
   `https://search.naver.com/search.naver?where=rss&query=<q>` and feeds the body to
   `xml.etree.ElementTree.fromstring()`. Live probe (2026-07-15) shows this URL returns
   **HTTP 200, `Content-Type: text/html; charset=UTF-8`, ~1.24 MB, starting with `<!doctype html>`**
   and containing no `<rss` element at all. Naver now silently ignores `where=rss` and serves the
   normal integrated-search HTML page. `ET.fromstring()` on HTML raises `ParseError`, which
   `_classify_error()` maps to `parse_failed`. There is no HTTP error and no redirect - the
   failure is purely content-type drift.
2. **HTML fallback selector is extinct.** `_collect_from_search_result()` regex-scans for
   `class="...news_tit..."`. Live probe of
   `https://search.naver.com/search.naver?where=news&query=<q>&sort=1` (HTTP 200, ~300 KB,
   server-rendered): **`news_tit` occurs 0 times**. Naver replaced the old news-search markup with
   the new SDS/fender component system (`sds-comps-*` classes, 916 occurrences on one page). The
   regex finds nothing, so the fallback returns an empty list.

Net effect: both query paths yield zero items -> `_collect_by_query` returns empty -> deduped list
is empty -> `last_status.success = false` with `failed_reason = parse_failed` (ParseError wins on
the RSS attempt) -> `TrendSourceManager` degrades to cache -> settings-keyword fallback. This
matches `storage/runtime/service_diagnostic.json`, which shows `naver_news` alternating between
`connection_refused` (2026-07-13 sessions where the local network/firewall blocked outbound -
environmental, not site-side) and `unknown_error`/parse failures once the network was reachable.

## 2. Live surface inventory (all probed 2026-07-15, desktop Chrome UA, plain GET, no cookies)

| Surface | URL | Status | Rendering | Notes |
|---|---|---|---|---|
| News keyword search | `https://search.naver.com/search.naver?where=news&query=<q>&sort=1` | 200, no redirect | Server-rendered HTML (headlines in initial payload) | New `sds-comps` markup; 10 articles per page |
| "RSS" search | `...?where=rss&query=<q>` | 200, no redirect | HTML (integrated search page) | **No longer RSS.** Do not use. |
| Daily ranking | `https://news.naver.com/main/ranking/popularDay.naver` | 200 | Server-rendered, **EUC-KR** charset | Per-press ranking boxes, ranks 1-5 each |
| Politics section (pattern for 100-105) | `https://news.naver.com/section/100` | 200 | Server-rendered, UTF-8 | Headline lists with press + relative time |

`sort=1` on news search = newest-first (recency), `sort=0` = relevance. Query must be URL-encoded UTF-8.

## 3. Observable fields and selectors

### 3a. News search page (`where=news`)
- **Article block**: repeated `sds-comps-vertical-layout` groups; 10 per page. Hashed utility
  classes (`fender-ui_xxxx`, random 16-char classes) are build-generated and **unstable - never key on them**.
- **Headline**: `<span class="sds-comps-text ... sds-comps-text-type-headline1">TITLE</span>`
  (exactly 10 `headline1` occurrences = 10 results). Titles may be ellipsized and contain
  `<mark>` around the query term - strip tags.
- **Link**: the enclosing `<a nocr="1" href="ORIGINAL_PUBLISHER_URL" ... data-heatmap-target=".tit">`.
  href is the original publisher article URL (e.g. `https://news.ifm.kr/news/articleView.html?idxno=...`).
- **Summary**: sibling `<a ... data-heatmap-target=".body">` -> `<span class="... sds-comps-text-type-body1">`.
- **Publisher**: `sds-comps-profile-info-title` block -> inner `<span class="...body2...">PRESS_NAME</span>`
  (42 `profile-info` occurrences: article + subarticle profiles).
- **Time**: relative time strings ("N시간 전" etc.) inside the profile-info block; no absolute
  timestamp in list markup.
- **Extraction pair to prefer**: `data-heatmap-target=".tit"` anchor + `sds-comps-text-type-headline1`
  span; `data-template-id` (11 occurrences) marks result-collection containers.

### 3b. Ranking page (`popularDay.naver`)
- Container: `div.rankingnews_box_wrap._popularRanking` -> per-press `rankingnews_box` (165 occurrences).
- Press name: `<strong class="rankingnews_name">SBS</strong>` (82).
- Rank: `<em class="list_ranking_num">1<span class="blind">위</span></em>` (407).
- Title+link: `<a href="https://n.news.naver.com/article/<press>/<articleId>?ntype=RANKING" class="list_title ...">TITLE</a>` (407).
- Charset is **EUC-KR** - the collector's hardcoded `utf-8` decode would mojibake this page.

### 3c. Section pages (`/section/100`..`105`)
- Item: `sa_item` (138); title text: `<strong class="sa_text_strong">TITLE</strong>` (46);
  link: `<a href="https://n.news.naver.com/mnews/article/<press>/<articleId>" class="sa_text_title ...">`;
  press: `<span class="sa_text_press">SBS</span>` (46);
  time: `<span class="sa_text_datetime is_recent"><b>19분전</b></span>` (relative only).
- The link also carries `data-nlog-params` JSON with `section1_id` and `rank` - machine-readable
  category + rank without extra parsing.

## 4. Access / blocking assessment

- **No hard technical blocker observed**: all four surfaces returned 200 to a plain desktop-UA GET
  with no cookies, no login, no captcha, no JS challenge, no redirect.
- **robots.txt is a full disallow** on both hosts: `search.naver.com/robots.txt` and
  `news.naver.com/robots.txt` both declare `User-agent: * / Disallow: /`, plus explicit AI-crawler
  bans (GPTBot, ClaudeBot, CCBot, ...) and an "AI training / RAG strictly prohibited" banner.
  This is a **policy/compliance blocker, not a technical one**. Whether automated collection from
  these hosts is acceptable is an owner decision; the compliant alternative is the official
  **Naver Search Open API** (news search endpoint, requires client id/secret - check
  `ROADMAP.md` "Requires External API" before any implementation).
- Historical `connection_refused` entries in `service_diagnostic.json` (2026-07-13) were local
  network/firewall conditions; today's probes prove the endpoints themselves are reachable.

## 5. Fixture contract summary

Sanitized minimal fixtures are specified in `NAVER_NEWS_FIXTURE_CONTRACT_V2.json`: one fixture per
surface (search HTML, ranking HTML, section HTML, plus an "rss-returns-html" regression body),
each trimmed to 2-3 sanitized items preserving only the structural classes listed above, with
expected parsed-output records matching the collector's `_build_trend_item` schema
(keyword/link/summary/publisher/published_at/rank).

## 6. Recon verdict (no implementation performed)

- `parse_failed` = HTML-instead-of-XML on the dead `where=rss` endpoint.
- Silent empty fallback = extinct `news_tit` selector.
- Repair surfaces exist and are server-rendered (search `headline1`/profile-info, ranking
  `list_title`/`list_ranking_num`, section `sa_text_*`), but the robots.txt full-disallow must be
  adjudicated (or the official Open API adopted) before any collector change ships.
