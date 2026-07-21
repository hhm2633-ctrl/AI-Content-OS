# HANKYUNG (한국경제) ECONOMY — PUBLIC-SITE RECONNAISSANCE

- Work order date: 2026-07-14 (recon executed 2026-07-15, KST-morning content observed)
- Scope: read-only inspection of public www.hankyung.com list pages. No article-body scraping of paid content, no account actions, no code changes.
- Recon status: **COMPLETE — with one access-control finding (Cloudflare interactive challenge on rapid repeated requests, see §7)**

## 1. Canonical URLs (all verified 200, server-rendered, no redirect)

| Purpose | URL | Notes |
|---|---|---|
| Latest news (전체 최신) | `https://www.hankyung.com/all-news` | Newest-first flat list |
| Ranking (many-read) | `https://www.hankyung.com/ranking` | 1~10위 block(s), rank number rendered |
| Economy section | `https://www.hankyung.com/economy` | Headline block + latest list |
| Economy sub-category | `https://www.hankyung.com/economy/<slug>` | Observed slugs: `economic-policy` (경제정책), `job-welfare` (고용복지) — sub-category links appear inside list items (`span.depth3 a`) |
| Article page | `https://www.hankyung.com/article/<article_id>` | `article_id` = `YYYYMMDD` + 5-char suffix, digits with optional trailing letter, e.g. `2026071556827`, `202607155966v`, `202607156285g` |
| Image CDN | `https://img.hankyung.com/photo/YYYYMM/XX.NNNNNNNN.3.jpg` | Thumbnails in list items |

HTTP is upgraded to HTTPS; no cross-host redirects observed on any list page.

## 2. robots.txt (fetched 2026-07-15)

- Disallowed for all agents: `/ad/`, `/cp/`, `/html/`, `/test/`, `/include/`, `/pdsdata/`, `/print/`, `/email/`, `/article/download/`, **`/api/`**, `/app-data/`, `/ext-api/`, `/action/`, `/pageviews/`, `/tag/`
- Fully banned bots: dotbot, AhrefsBot, SemrushBot(-SA/-BA)
- **Category pages, `/all-news`, `/ranking`, and `/article/<id>` are NOT disallowed.** Do not use `/api/` or `/ext-api/` endpoints — robots-prohibited.
- Sitemaps (robots-declared, usable as an alternative intake path):
  - `https://www.hankyung.com/sitemap/latest-article.xml`
  - `https://www.hankyung.com/sitemap/daily-article.xml`

## 3. Rendering model

List pages are **fully server-rendered classic HTML** (titles, links, dates, category labels, rank numbers all present in the raw response; no client-side hydration needed to read them). No `__NEXT_DATA__`/`__NUXT__`-style embedded JSON is required — plain CSS selectors suffice. JS on the page only handles paging-select navigation and scroll restoration.

## 4. Exact visible fields and selectors

### 4a. Economy section (`/economy`) — latest list
Container: `div.news-list-wrap > ul.news-list > li > div.news-item`

| Field | Selector (within `div.news-item`) | Example |
|---|---|---|
| title | `h2.news-tit > a` (text) | `[속보] 6월 취업자 6만3000명 증가…` |
| url | `h2.news-tit > a[href]` | `https://www.hankyung.com/article/2026071556827` |
| published time | `p.txt-date` (text) | `2026.07.15 08:01` (format `YYYY.MM.DD HH:mm`, KST) |
| sub-category label | `span.depth3 > a` (text) | `경제정책` |
| sub-category url | `span.depth3 > a[href]` | `/economy/economic-policy` |
| thumbnail | `figure.thumb img[src]` | img.hankyung.com CDN |

The page also has a headline block (`div.main-news-wrap`, `div.news-item.type-headline`) above the list; treat the `ul.news-list` items as the canonical intake list.

### 4b. Latest news (`/all-news`)
Container: `div.allnews-wrap ul.allnews-list > li[data-aid] > div.news-item`

| Field | Selector | Example |
|---|---|---|
| article id | `li[data-aid]` attribute | `202607156285g` |
| title / url | `h2.news-tit > a` | as above |
| published time | `p.txt-date` | `2026.07.15 10:24` |
| thumbnail | `div.thumb img[src]` | CDN |

Note: `txt-cont` (not `text-cont`) on this page; **no category label and no reporter byline** on all-news items. `data-aid` is the cleanest dedupe key.

### 4c. Ranking (`/ranking`)
Container: `div.ranking-wrap > div.ranking-panel > ul.ranking-news-list > li`

| Field | Selector | Example |
|---|---|---|
| rank | `em.rank.txt-num` (text, integer) | `1` |
| title / url | `div.news-item h2.news-tit > a` | as above |
| published time | `p.txt-date` | `2026.07.14 14:48` |
| range label | sibling `div.ranking-range strong.txt-num` | `1~10` |

### 4d. Publisher / reporter
List pages carry **no reporter byline**; publisher is implicitly `한국경제` (hankyung.com). Record `publisher: "hankyung"` as a constant in the fixture; reporter extraction would require article-page parsing (out of scope for this recon).

## 5. Pagination

- Query param `?page=N` on list pages; page JS builds `page=' + $(this).val()` from a `.paging .page-select select` control (server-side pagination, full page reload).
- `?page=2` on `/economy` returned HTTP 200, but the follow-up probe of `/all-news?page=2` hit a Cloudflare challenge before content comparison could be completed — pagination beyond page 1 is **unverified** and should be treated as best-effort. For the card-news use case, page 1 of each list (10–20 items) is sufficient.

## 6. Login / paywall

- List pages: no login wall, no paywall, no cookie-consent blocker. Header has `before-login` / `after-login` UI states but anonymous access is fully functional.
- Hankyung has a paid tier ("한경 PRO" / 한경 프리미엄 sections seen in the all-menu). **Collector must stay on the free list pages above and must not follow links into PRO/premium sections.** Paid articles were not accessed during this recon.

## 7. Access blockers — Cloudflare (IMPORTANT)

- The site sits behind Cloudflare. Single, browser-UA GET requests to each list page succeeded.
- A 4th rapid consecutive request (`/all-news?page=2`) returned a **Cloudflare interactive JS challenge** ("Just a moment…", `cType: 'interactive'`, HTTP challenge page instead of content). Probing was stopped at that point per the work order.
- Collector implications (fallback-first contract):
  1. Send a realistic browser `User-Agent`; keep ≤1 request per list page per run.
  2. Insert a delay (≥2–3 s) between requests; never parallel-fetch hankyung URLs.
  3. Detect challenge responses by marker `window._cf_chl_opt` or title `Just a moment` → immediately take the cache fallback path (`storage/cache/`), record `fallback_used`, never retry-hammer.
  4. Consider the robots-declared sitemap XML (`/sitemap/latest-article.xml`) as a lighter-weight alternate source if HTML fetch gets challenged repeatedly.

## 8. Sanitized fixture contract

See `HANKYUNG_ECONOMY_FIXTURE_CONTRACT.json` (same directory). Fixtures must be sanitized: keep structure and field shapes, replace real headlines/URLs with synthetic same-shape values when committing sample data.

## 9. Recon evidence

Raw HTML snapshots were saved only under the job tmp directory (not in the repo): `economy.html` (99,651 B), `latest.html` (107,663 B), `ranking.html` (68,368 B), all fetched 2026-07-15 with status 200.
