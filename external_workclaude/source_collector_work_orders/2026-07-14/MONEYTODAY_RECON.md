# MoneyToday (머니투데이) Public-Site Reconnaissance

- Date (KST observation): 2026-07-15
- Scope: read-only inspection of public latest/ranking/category pages. No login, no paid content, no account actions.
- Method: raw HTTP GET (curl) of public pages + robots.txt + JSON-LD + sitemaps. No CAPTCHA or security challenge was triggered; recon stopped at public HTML only.

## 1. Hosts and canonical URLs

| Purpose | URL | Status |
|---|---|---|
| Canonical site | `https://www.mt.co.kr/` | 200, server-rendered |
| Legacy news host | `https://news.mt.co.kr/newsList.html` | **410 Gone** (legacy list pages retired) |
| Legacy article URL | `https://news.mt.co.kr/mtview.php?no=<articleId>` | **301** → canonical article URL (category resolved server-side) |
| Category (economy) | `https://www.mt.co.kr/economy` | 200 |
| Latest ("속보/최신 기사") | `https://www.mt.co.kr/breakingnews` | 200, paginated `?page=N` (observed max ~6525) |
| Dedicated ranking page | `https://www.mt.co.kr/ranking`, `/latest`, `/news` | **404** — no standalone ranking page |
| Ranking data | Homepage widgets (`div.rank`, e.g. "증권 랭킹뉴스", "부동산 랭킹뉴스") | embedded in `https://www.mt.co.kr/` |

Canonical article URL pattern:

```
https://www.mt.co.kr/{category}/{yyyy}/{mm}/{dd}/{articleId}
articleId = 19-digit numeric (e.g. 2026071510050389439; prefix encodes creation timestamp)
```

Observed category slugs (nav): `economy, stock, industry, finance, estate, politics, society, world, culture, entertainment, living, future, tech, law, policy, sports, thebio, thegreen, opinion, photo, video, breakingnews, hotissue, mtreport, series` (stock/politics/law/thebio have sub-slugs like `/stock/marketnews`).

## 2. Rendering / tech stack

- Laravel backend (session cookie `mt_www_session`, Laravel-style encrypted value) behind **Cloudflare** (`Server: cloudflare`, `cf-cache-status: DYNAMIC`, `_cfuvid` cookie). Cloudflare Image Resizing serves thumbnails (`thumb.mt.co.kr/cdn-cgi/image/...`).
- Pages are **fully server-rendered HTML** (Blade-style templates, `data-page-name` attribute e.g. `general-section`). All titles/links/times/descriptions are present in the initial HTML — no JS execution needed to extract list data. No `__NEXT_DATA__`, no Inertia payload.
- Article pages embed **JSON-LD `NewsArticle`** (`<script type="application/ld+json">`) with `headline`, `datePublished`, `dateModified` (ISO-8601 +09:00), `articleSection`, `keywords`, `publisher.name = "머니투데이"`, `image[]`, `isAccessibleForFree: true`.

## 3. Field extraction (CSS selectors, observed markup)

### Category page (e.g. `/economy`) — `div#generalSection`
- Top article: `.general_top_comp .top_one_area.article_item`
  - title: `h3.top_on_title a` (text; href = canonical URL)
  - summary: `p.top_one_desc`
  - thumbnail: `a.thumb_wrap img[src]` (alt = title)
  - article id: `button.bookmark[data-aid]`
- Secondary: `.top_two_area .top_two_article.article_item` (same sub-structure, `figure.thumb a`)

### Latest page (`/breakingnews`) — list
- container: `ul.list_wrap > li.article_item`
- link: `li.article_item > a[href]` (category derivable from URL path segment 1)
- title: `h3.headline`
- summary: `p.description`
- time: `div.article_date` → format `yyyy.MM.dd HH:mm` (KST)
- reporter: `div.writer` (e.g. "양윤우 기자")
- article id: `button.bookmark[data-aid]`
- thumbnail: `figure.thumb img[src]`
- pagination: `?page=N` links + `.pagination` block (page 2 returns 200)

### Homepage ranking widgets (`https://www.mt.co.kr/`)
- container: `div.rank` per section; section name: `h2.section_title` (e.g. "증권 랭킹뉴스")
- items: `ul.list_area > li.list_item`
  - rank number: `figure.rank_img label` (text "1", "2", …)
  - title/link: `h3.hd_line a[href]` (also `data-sectionid`, `data-testid="article"`)
  - thumbnail: `figure.rank_img img`
- No timestamps or reporters in ranking widgets — only rank, title, URL, thumbnail.

Publisher is constant (`머니투데이`); per-article time/reporter appear on list items (`/breakingnews`) and in article JSON-LD, not in ranking widgets.

## 4. Sitemaps (preferred bulk/latest source)

`robots.txt` advertises:
- `https://www.mt.co.kr/sitemap/latest.xml` — **last 1000 articles**, Google News sitemap format: `<loc>` (canonical URL), `<lastmod>`, `<news:publication_date>`, `<news:title>`, `<image:image>`. Verified live (~725 KB). Category derivable from `<loc>` path.
- `https://www.mt.co.kr/sitemap/news/daily.xml` — last 7 days.
- `https://www.mt.co.kr/sitemap/article/{year}/daily.xml` — yearly archives (2025–).

This is the cleanest machine-readable "latest" feed and avoids HTML parsing entirely (no rank data, though).

## 5. Access control / robots / blockers

- **No login wall, no paywall** on inspected pages (`isAccessibleForFree: true`). No CAPTCHA encountered; Cloudflare present but plain curl with default UA succeeded on all pages.
- `www.mt.co.kr/robots.txt` (**authoritative for the canonical host**):
  - `User-agent: *` → `Allow: /` but **`Disallow: /*?page=*`**, `/*?keyword=*`, `/*?utm_*`, `/api/`, `/oauth/`, `/newsflash/`, `/ads/`.
  - AI bots **explicitly allowed**: `anthropic-ai`, `ClaudeBot`, `Claude-Web`, `GPTBot`, `CCBot`, `PerplexityBot`, `Google-Extended` (all `Allow: /`). SEO crawlers (Ahrefs/Semrush/Scrapy etc.) disallowed.
- `news.mt.co.kr/robots.txt` (legacy host) conversely **disallows AI bots** (`anthropic-ai`, `ClaudeBot`, `GPTBot` → `Disallow: /`) — but that host now 410s/301s to www, so it's irrelevant for collection.
- **Compliance implications for the collector**:
  1. Use `www.mt.co.kr` only; treat `news.mt.co.kr` URLs as redirect inputs.
  2. Do **not** crawl `?page=N` pagination (robots-disallowed for generic agents). Use `sitemap/latest.xml` + page-1 HTML of `/breakingnews` and category roots instead.
  3. Never touch `/api/`, `/newsflash/`, search (`?keyword=`).
  4. Keep request rate low; Cloudflare can escalate to challenges (fallback-first: cache → settings keywords → placeholders, per project invariant).

## 6. Recommended collection strategy

1. Primary: fetch `https://www.mt.co.kr/sitemap/latest.xml` (XML, stable schema) for latest N articles with title/URL/publish time/category.
2. Secondary (for ranking): fetch homepage once, parse `div.rank` widgets for per-section ranked titles/URLs.
3. Fallback: `/breakingnews` page 1 HTML (`ul.list_wrap li.article_item`).
4. Legacy `mtview.php?no=` URLs (e.g. from old caches): resolve via 301 redirect, don't fetch content there.

## 7. Sanitized fixture contract

See `MONEYTODAY_FIXTURE_CONTRACT.json` (same directory). Fixtures must use fake article ids/titles, keep the real field names/formats, and never embed full article body text (headline + ≤2-sentence summary only).
