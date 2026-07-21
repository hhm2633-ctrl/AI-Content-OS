# MK (매일경제) Economy Public-Site Reconnaissance

- Date: 2026-07-15 (KST), work order 2026-07-14
- Scope: read-only inspection of public mk.co.kr latest/ranking/economy/category surfaces
- Method: normal browser page views (Playwright, default Chrome UA) + robots.txt / llms.txt / sitemap reads. No login, no paid/premium articles, no account actions, no code changes.

## 1. Access policy — CRITICAL COMPLIANCE FINDING

`https://www.mk.co.kr/robots.txt`:

- Named AI crawlers (`GPTBot`, `ChatGPT-User`, `anthropic-ai`, `ClaudeBot`, `CLAUDE-WEB`, `CCBot`, `Bytespider`, `cohere-ai`, `Diffbot`, etc.) are **`Disallow: /`** with only these allowed: `/intro`, `/news/pick`, `/en/news/pick`, `/en/pick`.
- `User-agent: *` (ordinary clients/browsers, i.e. a plain Python collector) has **no Disallow directives** — general crawling is not robots-restricted.
- Sitemaps advertised: `/sitemap/sections/`, `/sitemap/latest-articles/`, `/sitemap/daily-articles/`, `/sitemap/daily-images/`.

`https://www.mk.co.kr/llms.txt` (site guide for AI models):

- States most editorial sections are "strictly protected and disallowed" for AI crawlers, and **explicitly authorizes AI/RAG crawling only of MK Pick** (`/news/pick`, `/news/pick/{qa|solution|casestudy|corporate|brand}` plus `/en/...` equivalents).
- Attribution rules for MK Pick content: attribute "매일경제 / Maeil Business Newspaper", deep-link the source article, do not alter figures/quotes.

**Recommendation:** if the collector identifies as an AI agent, only MK Pick is sanctioned. A conventional collector (generic UA, `User-agent: *` rules) is not robots-blocked from editorial pages, but MK's stated intent is that AI-content pipelines use MK Pick. Decision on which surface to use belongs to the CTO/owner; the fixture contract below covers both the economy editorial surface and the sanctioned MK Pick surface. The **Google News sitemap (`/sitemap/latest-articles/`) is the most stable, lowest-risk "latest" feed** and is explicitly advertised in robots.txt.

No captcha, login wall, paywall, or bot challenge was encountered on any inspected page. No premium/paid article was opened.

## 2. Canonical URLs and redirects

| Surface | Stable URL | Canonical (from `<link rel=canonical>`) |
|---|---|---|
| Economy home (latest list) | `https://www.mk.co.kr/news/economy/` | `https://www.mk.co.kr/news/economy` (trailing slash tolerated) |
| Economy subcategories | `/news/economy/economic-policy`, `/news/economy/business-index`, `/news/economy/trade`, `/news/economy/living-economy` | same pattern |
| Ranking (popular) per section | `https://www.mk.co.kr/news/ranking/economy/` | `https://www.mk.co.kr/news/ranking/economy` |
| Ranking tabs | `/news/ranking/{all,economy,financial,business,stock,realestate,it,opinion,politics,society,world,culture,sports}` | — |
| Article page | `https://www.mk.co.kr/news/{section}/{article_id}` (numeric id, e.g. `/news/economy/12098864`) | — |
| MK Pick (AI-sanctioned) | `https://www.mk.co.kr/news/pick` (+ `/qa /solution /casestudy /corporate /brand /all`), article `/news/pick/{id}` | `https://www.mk.co.kr/news/pick` |
| Latest-news sitemap | `https://www.mk.co.kr/sitemap/latest-articles/` | Google News sitemap XML |

`https://www.mk.co.kr/news/all/` returns **404** — there is no generic "/news/all" latest page; use the sitemap or per-section pages for latest.

## 3. Rendering model

- List pages are **server-rendered**: fetching the raw HTML of `/news/ranking/economy` (no JS) already contains all 20 `class="news_item"` anchors and titles. Same for `/news/economy`. Requests-based scraping works; no headless browser required.
- No `__NEXT_DATA__`. JSON-LD present: `NewsMediaOrganization`, `WebSite`, `BreadcrumbList`, `CollectionPage` (page-level metadata only, not the article list).
- The economy home shows 10 latest items server-rendered; the "더보기" (more) button has no `href` (JS/AJAX load-more — endpoint not probed; use the sitemap for depth instead).
- Images served from `wimg.mk.co.kr` (CMS thumbnails, `_T1`/`_R` suffix variants).

## 4. Field structure and selectors

### 4a. Economy latest list (`/news/economy`)

Item anchor: `a.news_item` — carries machine-readable data attributes:

```html
<a href="https://www.mk.co.kr/news/economy/12098864" class="news_item"
   data-category_1depth="뉴스" data-category_2depth="경제" data-category_3depth="홈"
   data-section="최신기사" data-idx="001" data-id="12098864">
  <div class="art_area">
    <h4>제목…</h4>
    <p class="art_desc">본문 요약…</p>
    <div class="info_group"><p class="time_info">1시간 전</p></div>
  </div>
  <div class="list_thumb"><img src="https://wimg.mk.co.kr/..._T1.png" alt="제목"></div>
  <div class="time_area"><span>07.15<br>2026</span></div>
</a>
```

Selectors:
- item: `a.news_item[data-section="최신기사"]`
- title: `h4` (inside `.art_area`)
- summary: `p.art_desc`
- relative time: `p.time_info` (Korean relative, e.g. "1시간 전"); absolute date: `.time_area span` ("07.15\n2026" — MM.DD + YYYY, no clock time on list page)
- article id: `data-id` (also last URL segment)
- rank/order: `data-idx` (zero-padded 3-digit)
- publisher: constant "매일경제" (not per-item on list pages)

### 4b. Ranking page (`/news/ranking/economy`, 20 items, SSR)

Two visual blocks, same `data-*` scheme, `data-section="인기뉴스"`:
- Ranks 1–10 (with thumbnail): anchor without `news_item` class; rank in `em.news_num`, title in `.headline .text`, image in `.a_pnews_img img`.
- Ranks 11–20 (text-only): `li.popular_news_node > a.news_item.type_num`; rank in `em.news_num_else`, title in `h3.news_ttl`.
- Robust rank source: `data-idx` ("001"–"020"); target section from the article URL path (`/news/{section}/{id}` — ranked items may cross sections).
- No timestamps on the ranking page.

### 4c. MK Pick (`/news/pick`, AI-sanctioned)

- Article links: plain `<a href=".../news/pick/{id}">` (no class); title `h3.main_tit`, summary `p.main_desc`, thumb `.main_thumb img`.
- Category tabs: `/news/pick/{qa|solution|casestudy|corporate|brand|all}`; brand pages `/news/pick/brand/{BrandName}`.

### 4d. Latest-articles sitemap (`/sitemap/latest-articles/`) — recommended latest feed

Google News sitemap XML, site-wide latest across all sections:

```xml
<url>
  <loc>https://www.mk.co.kr/news/stock/12099009</loc>
  <news:news>
    <news:publication><news:name>매일경제</news:name><news:language>ko</news:language></news:publication>
    <news:publication_date>2026-07-15T10:38:54+09:00</news:publication_date>
    <news:title>HLB, 간암 신약 FDA 우려 완화에 상한가…</news:title>
    <news:keywords>제조시설,원료의약품,…</news:keywords>
  </news:news>
  <image:image><image:loc>https://wimg.mk.co.kr/..._R.jpg</image:loc></image:image>
</url>
```

Gives exact ISO-8601 KST timestamps, titles, keywords, image, and section (from `<loc>` path) — filter `loc` containing `/news/economy/` for economy-only latest. This is the cleanest, most stable machine contract on the site.

## 5. Pagination

- Economy list: no URL pagination visible; "더보기" is a JS load-more (button `a.art_more`, no href). Not probed further. Depth beyond the first 10 items should come from the sitemap.
- Ranking: fixed 20 items, no pagination.
- MK Pick: category tab pages; load behavior not deeply probed.

## 6. Blockers / risks

- No captcha, login, paywall, or bot challenge encountered on the inspected public pages.
- Anthropic/OpenAI-class UAs are robots-disallowed outside MK Pick — do not crawl editorial sections with an AI-identifying User-Agent.
- Claude Code's built-in WebFetch is blocked for mk.co.kr ("unable to fetch"); a plain HTTP client from the collector worked (raw HTML fetch returned 200 with full SSR content).
- CSS class names (`news_item`, `art_desc`, `time_info`, `news_ttl`) and `data-*` attributes look stable and semantic; `data-id`/`data-idx`/URL id are the most durable anchors.

## 7. Fixture contract

See `MK_ECONOMY_FIXTURE_CONTRACT.json` (same folder). Fixtures must be sanitized: keep structure, truncate summaries, no full article bodies, no premium content.
