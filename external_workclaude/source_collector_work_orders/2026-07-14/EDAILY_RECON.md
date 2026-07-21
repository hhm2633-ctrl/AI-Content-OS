# EDAILY Public-Site Reconnaissance (Read-Only)

- Recon date: 2026-07-15 (KST morning), executed by Claude (Fable 5)
- Scope: public latest/ranking/category pages of edaily.co.kr only. No login, no account/social actions, no form submissions. GET requests with a desktop Chrome User-Agent only.
- Outcome: **No blockers encountered.** No captcha, no login wall, no bot challenge (no Cloudflare/Incapsula interstitial). All target pages returned HTTP 200 with fully server-rendered HTML or plain JSON.

## 1. Canonical URLs and redirects

| Purpose | Canonical URL | Notes |
|---|---|---|
| Homepage | `https://www.edaily.co.kr/` | `http://` and apex `edaily.co.kr` both 301 → `https://www.edaily.co.kr/` |
| Latest news (실시간 뉴스) | `https://www.edaily.co.kr/News/RealTimeNews` | Case-insensitive (`/News/realtimenews` also works). Tabs: `?tab=0` 전체, `1` 연예·스포츠, `3` 시황·특징주, `4` 종목뉴스, `5` 포토. Pagination: `?tab=0&page=N` |
| Category list | `https://www.edaily.co.kr/article/{slug}` | Slugs seen in nav: `economy`, `stock`, `estate`, `global`, `politics`, `society`; subcategory form `/articles/{group}/{sub}` (e.g. `/articles/business/industry`, `/articles/economy/finance`) |
| Category pagination (JSON) | `https://www.edaily.co.kr/article/MoreList?categoryCode={code}&page={n}&pagesize={n}&date=` | Plain GET returning a JSON array. `categoryCode` is embedded in each category page's inline `fetch()` script (e.g. `16100` for 증권/stock) |
| Article detail | `https://www.edaily.co.kr/News/Read?newsId={17-digit id}&mediaCodeNo=257` | `newsId` is a 17-digit numeric string; `mediaCodeNo=257` is constant across all observed links |
| Latest sitemap | `https://www.edaily.co.kr/sitemap/latest-article.xml` | Google News sitemap: `loc`, `news:publication_date` (ISO-8601 +09:00), `news:title` (CDATA), `image:loc`. Cleanest machine-readable "latest" feed |
| Issue focus | `https://www.edaily.co.kr/issue/list?gcode=1&hcode={n}` | Curated issue tag pages |

## 2. robots.txt / access policy

`https://www.edaily.co.kr/robots.txt`:
- Named crawler bots (AhrefsBot, Scrapy, Bytespider, Diffbot, img2dataset, etc.) are `Disallow: /`.
- `User-agent: *` disallows only `/_template/popup/t_popup_click.asp` — the rest of the site is permitted for generic agents.
- Sitemaps declared: `latest-article.xml`, `daily-article.xml`, `daily-image.xml`.
- Analytics: Matomo + GA + Evergage beacons (client-side only; no effect on scraping).
- **Policy for our collector**: honor the bot blocks in spirit — low request rate, cache-first, identify politely; fallback-first contract applies (cache → keyword fallback → placeholder).

## 3. Rendering model

- **Homepage, RealTimeNews, and category pages are server-rendered** — all titles/links/times are present in the initial HTML. jQuery 1.12 progressive enhancement only.
- Category page "더보기" (more) button loads additional pages via the `MoreList` JSON endpoint (see §5); an inline `${(item.IMG_B ?...}` JS template string in the HTML renders those extra items client-side. First ~21 items are static HTML.
- RealTimeNews article body panel loads via `POST /news/_realtimenewsread` (JSON body `{newsid, newsgb, tab}`) — not needed for list collection.
- Page auto-refreshes itself every 1/3/5 min via a cookie-driven `location.reload()`; irrelevant to HTTP collection.

## 4. Field extraction — selectors

### 4a. RealTimeNews (`/News/RealTimeNews`) — latest feed
Container `div.news_list`; date header `div.date` ("7월 15일 (수)" — day-level date; year implied); one item per `dl`:

| Field | Selector / source | Example |
|---|---|---|
| time (HH:MM) | `dl > dt` text | `10:17` |
| title | `dl > dd > a > span` text (HTML-entity encoded: `&#39;`, `&#183;`, `&quot;`) | `SK하이닉스 원주·ADR 상호전환 …` |
| newsId | `dd > a[href]` = `javascript:View('{newsId}', '{newsGb}')` — regex `View\('(\d+)',\s*'(\w)'\)` | `03440726645514848`, gb `E` |
| article URL | reconstruct: `/News/Read?newsId={id}&mediaCodeNo=257` | — |
| pagination | `div.paging a` with `Page('N')`; URL form `?tab=0&page=N` | pages 1–6 observed |

No category, publisher, or rank fields on this page. Publisher is implicitly 이데일리 (edaily).

### 4b. Ranking / trending
Edaily exposes **no numbered "most viewed" ranking page** on the public desktop site (no `많이 본` section found on homepage, realtime, or category pages; `READ_CNT` in MoreList JSON is always `0`). The available ranking proxy is the **급상승 뉴스 (trending)** widget:
- On `/News/RealTimeNews`: `section#taparea_a > a` — each `a[href]` is the article URL, `dd p span` the title, `dt img[src]` the thumbnail. 9 items; **rank = DOM order** (no explicit rank number).
- Same list appears on the homepage inside the `<!-- //급상승뉴스·이슈 포커스 -->` section as `div > a[href^="/News/Read"] > span`.
- Fixture contract treats rank as 1-based position in this list.

### 4c. Category page (`/article/stock` etc.)
Container `div#newsList`; one item per `div.newsbox_04`:

| Field | Selector | Example |
|---|---|---|
| article URL / newsId | `.newsbox_04 > a[href]` (`/News/Read?newsId=…&mediaCodeNo=257`); `title` attr duplicates headline | — |
| title | `ul.newsbox_texts li:nth-of-type(1)` text | — |
| summary | `ul.newsbox_texts li:nth-of-type(2)` text (truncated with `...`) | — |
| thumbnail | `span.newsbox_visual img[src]` (has `onerror` default-image fallback) | — |
| subcategory | `div.author_category span.categories` text | `주식` |
| datetime | text node of `div.author_category` (between `.categories` and `<em>I</em>`), format `YY.MM.DD HH:MM` KST | `26.07.15 10:17` |
| reporter | `div.author_category a[href^="/jroom/main"] span.author` text; jid in href `?jid={id}` | `박순엽 기자` |

### 4d. MoreList JSON (`/article/MoreList`) — preferred structured source for categories
GET, returns a JSON array (~50 keys per item). **Warning: keys are case-sensitive duplicates** (`headline` AND `HEADLINE`) — parse case-sensitively (PowerShell `ConvertFrom-Json` needs `-AsHashtable`; Python `json` is fine). Key fields:

- `NEWS_ID` (17-digit string), `NEWS_GB`, `MediaCodeNo` (257)
- `HEADLINE` / `HEADLINE_HTML_DEL` (clean title), `HEADLINE_SHORT`
- `BODY_SHORT` (plain-text teaser), `BODY_HTML_DEL` (plain-text full body), `BODY_HTML` (raw HTML — heavy, drop in fixtures)
- Categories: `Category1CodeNo/Name` (e.g. 16000/증권) → `Category2CodeNo/Name` (16100/증권뉴스) → `Category3CodeNo/Name` (16103/종목), `CategoryName`
- `Journalist` (name), `JID` (reporter id), `JNAME`
- Timestamps (KST): `ConfirmDateFormat01` `2026-07-15 오전 09:31:00`, `ConfirmDateFormat02` `26.07.15 09:31`, `ConfirmDateTime` `09:31`, `ConfirmDateAgoMinute` `48분 전`, `CONFIRM_DT`; **beware `ConfirmDate` is US-format `07/15/2026 00:31:00` with a shifted time — do not use**
- Images: `IMG`, `IMG_S/H/T/B/KB`, `VISION_B/H/V`, `JImage`
- Paging: `TotalCnt` (e.g. 300) on every row; request params `page` (1-based), `pagesize`, `date` (empty = latest)
- `READ_CNT` always 0 (unused)

### 4e. Sitemap (`/sitemap/latest-article.xml`)
Per `<url>`: `loc` (canonical article URL), `news:publication_date` (full ISO-8601 with +09:00 offset — the **only source with precise machine-readable timestamps**), `news:title` (CDATA), `news:publication/news:name` = 이데일리, `image:loc`.

## 5. Recommended collection strategy (for later implementation — NOT implemented here)

1. **Primary latest feed**: sitemap `latest-article.xml` (stable schema, exact ISO timestamps, entity-free titles).
2. **Category collection**: `article/MoreList?categoryCode=…&page=1&pagesize=20&date=` JSON (titles, teasers, 3-level categories, reporter, KST timestamps in one call). Category codes must be harvested once per category page from the inline fetch script.
3. **Trending/rank proxy**: parse `section#taparea_a` on `/News/RealTimeNews` (server-rendered, small page ~23KB).
4. HTML scraping of `/article/{slug}` (`div.newsbox_04`) as fallback if JSON endpoint changes.
5. All titles from HTML need HTML-entity unescaping (`&#39;` `&quot;` `&#183;` observed).

## 6. Blockers / risks

- None observed: no captcha, no login, no rate-limit responses during ~10 low-rate requests.
- Risks: `MoreList` is an internal endpoint (no versioning; may change without notice) → keep the HTML selector fallback. Named-bot robots blocks signal anti-scraping awareness → keep request rate low and cache aggressively per the fallback-first contract.
- `ConfirmDate` field timezone trap (see §4d).

## 7. Sanitized fixture contract

See `EDAILY_FIXTURE_CONTRACT.json` (same directory). Sanitization rules: fixtures use the reduced field set only (no `BODY_HTML`), real article text may be replaced by placeholder Korean strings of similar length, `newsId` values in fixtures must be syntactically valid (17 digits) but fake (prefix `99`), and no reporter personal data beyond public byline name/jid.
