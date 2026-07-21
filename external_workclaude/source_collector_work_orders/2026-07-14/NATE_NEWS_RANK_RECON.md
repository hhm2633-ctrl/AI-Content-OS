# Nate News Rank — Public Page Recon (Read-Only)

Date: 2026-07-15 (recon session)
Scope: Public, unauthenticated, read-only inspection of `news.nate.com` ranking pages via raw HTTP GET (desktop UA). No login, likes, comments, or social actions performed. No code implemented per work order.

## 1. Compliance blocker — READ FIRST

`https://news.nate.com/robots.txt` (200 OK) declares for generic crawlers:

```
User-agent: *
Disallow: /
Allow: /ads.txt
Disallow: /view/summary*
```

Only specific named bots (Googlebot, Yeti, Daum, Bingbot, MSNbot, ZumBot, facebookexternalhit, Mediapartners-Google, Twitterbot) get broader allowances; `GPTBot` is fully disallowed. **A generic automated collector against `news.nate.com` is disallowed by robots.txt.** This recon was a one-off manual read-only inspection; before any collector is implemented, the project owner must make an explicit ToS/robots policy decision (options: skip this source, keep it manual-fixture-only, or accept the policy risk knowingly). This recon does not constitute that review. Sitemap declared: `https://news.nate.com/sitemap?data=index`.

## 2. URLs tested (all 200 OK, no redirects, no login, no captcha)

| URL | Result | Notes |
|---|---|---|
| `https://news.nate.com/rank/` | 200, ~82 KB | Defaults to interest ranking, `sc=all`, `p=day`, today's date. Server-rendered. |
| `https://news.nate.com/rank/interest?sc=all&p=day&date=20260715` | 200 | Canonical explicit form of the default page. |
| `https://news.nate.com/rank/interest?sc=all&p=day&date=20260715&page=2` | 200 | Pagination works; page 2 starts at rank 51. |
| `https://news.nate.com/rank/interest?sc=ent&p=day&date=20260715` | 200 | Category variant, identical markup, 50 items. |
| `https://news.nate.com/rank/cmt?sc=all&p=day` | 200, ~73 KB | Comment-count ranking; per-item comment count present. |
| `https://news.nate.com/robots.txt` | 200 | See §1. |

### URL scheme (confirmed from page's own nav links)

```
https://news.nate.com/rank/<type>?sc=<category>&p=<period>&date=YYYYMMDD[&page=N]
```

- `type`: `interest` (많이 본 뉴스, default), `pop`, `cmt` (comment count), `updown`, `emoticon` — only `interest` and `cmt` were fetched and verified in this recon; treat the others as observed-in-nav only.
- `sc` (category): `all`, `sisa`, `pol`, `eco`, `soc`, `int`, `its`, `pho`, `spo`, `ent` (탭: 전체/시사/정치/경제/사회/국제/IT과학/사진/스포츠/연예).
- `p` (period): `day` | `week`.
- `date`: `YYYYMMDD`; historical dates work (nav offers ~previous 20 days). Omitting it defaults to today.
- `page`: 50 items per page (`page=1` → ranks 1–50, `page=2` → 51–…).
- Mobile equivalent exists at `https://m.news.nate.com/rank/list?mid=m2001` (not inspected).

## 3. Server-rendered vs dynamic

Fully **server-rendered static HTML**. All ranked items (rank number, headline, snippet, publisher, date, link, thumbnail, rank-change / comment-count badge) are present in the initial HTML response fetched with a plain `Invoke-WebRequest` and desktop UA — no JS execution needed, no embedded JSON state (`__NEXT_DATA__` etc.) required. Classic table-era markup with template comments (`<!-- mduRank rank1-5 -->`).

## 4. Item markup and selectors (verified against live HTML)

Two layout tiers per page:

### Ranks 1–5 (rich items, with thumbnail + snippet)

Container per item: `div.mduSubjectList` containing:

- Rank block: `dl.mduRank.rankN > dt > em` → rank number text (e.g. `1`).
- Rank change (interest/pop): `dl.mduRank dd span` — classes `up` / `down` (sibling `span > em` holds delta) or `noupdown` (text `-` + hidden `<i>순위변동없음</i>`).
- **On `/rank/cmt` this same `dd` instead holds `span.comment > em` = comment count** (e.g. `913`). Comment counts are NOT shown on `/rank/interest`.
- Article link: `div.mlt01 > a.lt1[href]` — href is protocol-relative: `//news.nate.com/view/YYYYMMDDnNNNNN?mid=nXXXX`.
- Headline: `h2.tit` inside the link (may be truncated with `...`; contains HTML entities like `&quot;`).
- Snippet: text node inside `span.tb` after the `h2` (loose text, not wrapped in its own tag).
- Thumbnail: `em.mediatype img[src]` → `//thumbnews.nateimg.co.kr/news90//...`.
- Publisher + date: `span.medium` → publisher name text, with `<em>` child = date `YYYY-MM-DD` (date only, no time on ranking pages).

### Ranks 6–50 (compact items, headline-only list)

Inside `div.postRankSubject > ul.mduSubject.mduRankSubject > li`:

- Rank + change: same `dl.mduRank.rankN` structure as above.
- Link: direct `a[href^="//news.nate.com/view/"]` (no `.lt1` class), headline in child `h2` (no `.tit` class).
- Publisher: `span.medium` (plain text, **no date `<em>` on compact items**).
- No snippet, no thumbnail.

A parser must handle both tiers; safest anchor is `dl.mduRank` + the nearest following `a[href*="/view/"]`.

## 5. Field availability summary

| Field | interest ranks 1–5 | interest ranks 6–50 | cmt ranking |
|---|---|---|---|
| rank | yes (`dl.mduRank dt em`) | yes | yes |
| headline | yes (`h2.tit`) | yes (`h2`) | yes |
| article URL | yes (`/view/YYYYMMDDnNNNNN?mid=nXXXX`) | yes | yes |
| publisher | yes (`span.medium`) | yes | yes |
| date | yes (`span.medium em`, date-only) | **no** | ranks 1–5 only |
| category | via request `sc` param only (not per-item); `mid=` code on link hints at article section (`n1006`/`n1007`/`n1008` observed) but the code→name map is unverified | same | same |
| comment count | **no** | **no** | yes (`span.comment em`) |
| rank change | yes (`span.up/.down/.noupdown`) | yes | no (replaced by comment count) |
| snippet | yes | no | ranks 1–5 only |
| thumbnail | yes | no | ranks 1–5 only |

## 6. Article permalink pattern

```
//news.nate.com/view/<YYYYMMDD>n<5-digit seq>?mid=<section code>
```

Example: `//news.nate.com/view/20260715n00317?mid=n1006`. Article ID = `YYYYMMDDnNNNNN`. `mid` is tracking/section context and can likely be dropped for a canonical article URL (not re-verified without it — verify before relying on it). Note `robots.txt` disallows `/view/summary*` and `/comment/*` explicitly for all bots.

## 7. Access blockers observed

- No login wall, no CAPTCHA, no cookie interstitial, no UA-based block against a plain desktop-UA HTTP client (single-session evidence only; rate-limit behavior under repeated automated hits NOT tested and out of scope).
- The only blocker is policy-level: robots.txt `Disallow: /` for `User-agent: *` (§1).

## 8. Static-HTML feasibility & implementation contract for Spark

**Technically feasible** with plain HTTP GET + HTML parsing (no browser, no JS). Recommended target: `https://news.nate.com/rank/interest?sc=<cat>&p=day&date=<YYYYMMDD>` (page 1 only, ranks 1–50; ranks 1–30 more than suffice for trend use). For lanes: `sc=ent` → `entertainment_news`; `sc=soc` + `sc=eco` (or `sc=all`) → `news_society_economy`.

Implementation constraints (binding on Spark):

1. **Do not implement live collection until the §1 robots.txt policy decision is recorded** (e.g. in `DECISIONS.md` by the owner). Until then the collector may only run against local fixtures / cache, consistent with the project's fallback-first contract.
2. Parse both markup tiers (§4); missing date/snippet/thumbnail on compact items must not be treated as errors.
3. Decode HTML entities in headlines; strip trailing `...` truncation marker only if normalization requires it.
4. Normalize protocol-relative hrefs to `https:`.
5. Follow the existing `nate_pann_collector.py` output/fallback conventions (RetryPolicy → cache → settings keywords → placeholder) so `workflow_completed` never regresses.
6. Encoding: page serves Korean text; verify charset header and decode explicitly (observed content parsed correctly as UTF-8 in this session).

Fixture contract: see `NATE_NEWS_RANK_FIXTURE_CONTRACT.json` (same folder). Fixture values are sanitized/representative of real observed structure.
