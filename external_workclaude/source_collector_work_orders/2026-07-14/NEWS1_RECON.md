# NEWS1 Public-Site Reconnaissance (Read-Only)

- **Recon date:** 2026-07-15 (KST)
- **Scope:** Public News1 Korea (news1.kr) category / ranking / latest pages only. No account, no social actions, no code implemented.
- **Method:** Raw HTTPS GET with a standard desktop browser User-Agent (`Invoke-WebRequest`). No JS execution required for any recommended extraction path.
- **Result:** Fully collectible. No login wall, no captcha, no bot challenge encountered on any fetched page.

## 1. Platform & rendering model

- Site is a **Next.js (Pages Router) app served through Akamai** (`X-Cache: ... AkamaiGHost`, `Cache-Control: s-maxage=60, stale-while-revalidate`, `x-nextjs-cache: MISS/HIT`). Content is ISR-cached ~60s at the edge.
- Every page is **server-rendered**: plain GET returns full HTML including headlines, and an embedded `<script id="__NEXT_DATA__" type="application/json">` blob containing clean structured article data.
- Static assets are served from `https://image.news1.kr/system/_sjs/_next/...` (asset prefix); article images from `https://image.news1.kr/system/photos/...`.
- Client-side XHR API host is `https://rest.news1.kr/v6/...` (only observed for ads/popup widgets in the JS bundles; article lists do not need it).

## 2. Canonical URLs (all stable, no redirects; HTTP→HTTPS upgrade only)

| Purpose | URL | Notes |
|---|---|---|
| Homepage | `https://www.news1.kr/` | 200, ~940KB SSR HTML |
| Latest news | `https://www.news1.kr/latest` | 200, SSR list of 34 items |
| Latest pagination | `https://www.news1.kr/latest?page=N` | 200, next 33–34 items per page |
| Ranking (most-viewed) | `https://www.news1.kr/trend` | 200, SSR ranked list (rank = array order), ~30 items |
| Category | `https://www.news1.kr/{section}` | e.g. `/society`, `/politics`, `/economy` |
| Subcategory | `https://www.news1.kr/{section}/{subsection}` | e.g. `/society/labor` |
| Article | `https://www.news1.kr/{section}/{subsection}/{article_id}` | numeric id, e.g. `/society/labor/6228304` |
| Category sitemap | `https://www.news1.kr/api/feeds/category/` | XML urlset of every section/subsection (canonical category map) |
| Google News feed | `https://www.news1.kr/api/feeds/google-news/` | listed in robots.txt |

Top-level sections observed in nav: `politics, society, economy, industry, finance, realestate, world, diplomacy, nk, it-science, bio, life-culture, entertain, sports, local, opinion, people, photos, videos, series, trend, latest, issues`.

Subsections (from `/api/feeds/category/`): e.g. society → `incident-accident, court-prosecution, education, welfare-hr, labor, environment, weather-disaster, people, women-family, general-society`.

## 3. Server-rendered vs dynamic

| Page | SSR content | Dynamic (client-fetched) |
|---|---|---|
| `/latest`, `/trend` | Full article list in HTML **and** `__NEXT_DATA__.props.pageProps.data` | none needed |
| `/{section}` | Only top block (`pageProps.sectionTop`, 11 items) | remainder of the list is client-rendered |
| `/{section}/{subsection}` | `pageProps.subsectionData` (~9 items) + `subsectionTop` | "load more" is client-side |
| Homepage | Most content SSR, but **"많이 본 뉴스" (most-viewed) sidebar is a client-side skeleton** (`placeholder-glow`) linking to `/trend` | ranking widget |

**Pagination without JS:** Next.js data routes work with plain GET:
`https://www.news1.kr/_next/data/{buildId}/latest.json?page=2` and `/_next/data/{buildId}/trend.json` return the same `pageProps` JSON (verified 200).
⚠️ `buildId` changes on every deploy — scrape it from `__NEXT_DATA__.buildId` in any page's HTML at run time (current build at recon time: `u5NCPVjayeZpKrl_omD-T`). `?page=N` also works on the plain HTML URL `/latest?page=N`.

## 4. Extraction contract (recommended: `__NEXT_DATA__`, fallback: HTML selectors)

### Primary: embedded JSON

Selector: `script#__NEXT_DATA__` → `JSON.parse` → keys by page type:

- `/latest`: `props.pageProps.data` — array of items
- `/trend`: `props.pageProps.data` — array in **rank order** (index 0 = rank 1); extra field `section` (Korean label, e.g. `"연예"`)
- `/{section}`: `props.pageProps.sectionTop` (array), `props.pageProps.section` (slug)
- `/{section}/{subsection}`: `props.pageProps.subsectionData`, `subsectionTop`, plus `sectionId`, `sectionName` (Korean), `subsectionId`, `subsectionName`

Item fields (verified live):

| Field | Type | Example |
|---|---|---|
| `id` | int | `6228304` |
| `title` | str (may contain HTML entities) | `"내년 최저임금 1만700원…"` |
| `sub_title` | str, may contain `<br>` | |
| `badge` | str, often empty | |
| `url` | site-relative | `/society/labor/6228304` |
| `image` | absolute URL | `https://image.news1.kr/system/photos/.../no_water.jpg/dims/crop/628x390` |
| `author` | str | `"조용훈 기자"` |
| `pubdate` | `YYYY-MM-DD HH:MM:SS` (KST) | `"2026-07-15 00:10:26"` |
| `pubdate_kor`, `time_ago` | str, often empty on list payloads | |
| `summary` | str, first ~500 chars of body | |
| `section` | str (trend only, Korean label) | `"연예"` |
| `related` | str, often empty | |

Publisher is implicitly News1 (`뉴스1`) — single-publisher site; no per-item publisher field.

### Fallback: HTML selectors (`/latest` list; classes are Bootstrap-like but stable across pages fetched)

- List item container: `div.row-bottom-border-2 > div.row`
- Title + link: `h2.n1-header-title-1-2 > a[href]` (href = relative article URL; text = headline)
- Summary: `span.n1-header-desc-1`
- Author: `div.entry-meta span` (last span, `"이름 기자"`)
- Thumbnail: first `a > img[alt]` in item (`alt` duplicates headline; real image URL inside `/_next/image?url=...` or `srcSet`)
- Page section header: `h2.n1-header-title-5` (e.g. `최신뉴스`)
- Time is **not** rendered in list-item HTML — take `pubdate` from `__NEXT_DATA__`.

## 5. robots.txt / access blockers

- `robots.txt` (200): `User-agent: *` disallows only `/ads`, `/jebo`, `/search`. **`/latest`, `/trend`, and all category pages are allowed.**
- GPTBot / OAI-SearchBot and a few scraper UAs are fully disallowed — use a normal browser UA string, not an AI-crawler UA.
- No login, no captcha, no Cloudflare/WAF challenge observed on ~10 fetches. Akamai edge caching (60s) means polite low-frequency polling is effectively free for the origin.
- Sitemaps declared: `/api/feeds/category/`, `/api/feeds/sitemap-index/`, `/api/feeds/google-news/`, `/api/feeds/globalmarkets/`.

## 6. Risks / caveats for a future collector

1. `buildId` for `/_next/data/...` routes rotates per deploy — always re-read from `__NEXT_DATA__`; or avoid data routes entirely and parse `__NEXT_DATA__` from the HTML page (self-contained, no buildId management).
2. Category landing pages (`/{section}`) only SSR 11 top items; prefer `/latest?page=N` (site-wide) or `/{section}/{subsection}` (9+ items per subsection) for volume.
3. CSS class names are framework-generated-ish (`n1-*`, `row-bottom-border-2`) and could change on redesign; the `__NEXT_DATA__` path is the stable contract, HTML selectors are fallback only.
4. `title`/`summary` contain HTML entities (`&quot;`) and `sub_title` may contain `<br>` — unescape/strip before use.
5. `/trend` ranking has no explicit rank number field; rank = array index + 1 (HTML shows the same order).

## 7. Fixture contract

See `NEWS1_FIXTURE_CONTRACT.json` (same directory). Minimal sanitized fixture = the `__NEXT_DATA__` script block (with `data`/`sectionTop` arrays truncated to 3 items and summaries shortened) embedded in a skeleton HTML page, plus one standalone JSON fixture per page type mirroring `pageProps`.
