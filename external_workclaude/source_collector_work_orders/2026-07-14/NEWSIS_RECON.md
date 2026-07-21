# Newsis Public-Site Reconnaissance (Read-Only)

- **Recon date:** 2026-07-15 (KST morning), executed by Fable 5 per work order 2026-07-14
- **Scope:** public list/ranking/category pages only. No account, no social actions, no article-body scraping beyond what list pages embed.
- **Method:** plain HTTPS GET with a generic desktop browser User-Agent (`Mozilla/5.0 (Windows NT 10.0; Win64; x64)`), no cookies, no JS execution. All findings below verified against live raw HTML.

## 1. Access & blockers

| Check | Result |
|---|---|
| `https://www.newsis.com/` | HTTP 200, no redirect, ~177 KB HTML |
| Bot blocking / WAF challenge | **None observed** for generic UA, plain GET |
| CAPTCHA / login wall | **None** on any list, category, or ranking surface |
| Cloudflare/Akamai interstitial | Not encountered |
| robots.txt | Allows all list pages. `User-agent: *` disallows only `/common/`, `/search/`, `/ar_detail/`. Sitemaps: `/sitemap.xml`, `/newsis_news_google.xml` (Google News sitemap — useful secondary feed) |
| Encoding | UTF-8 |

**Blocker policy for collector:** none currently needed beyond polite rate limiting; stop and fall back to cache if a non-200 or `/error/` redirect appears.

## 2. Canonical URLs

Canonical host is `https://www.newsis.com` (HTTP upgrades to HTTPS; `newsis.com` serves same site — always store `www.` form).

| Surface | Canonical URL | Server-rendered? |
|---|---|---|
| Latest (실시간) | `https://www.newsis.com/realnews/` | Yes — full list in HTML |
| Category section main | `https://www.newsis.com/{section}/?cid={cid}` e.g. `/society/?cid=10200` | Partially (top boxes + ranking); `div.cornList > ul` is **empty in raw HTML** (JS-filled) — do not depend on it |
| Category flat list (**recommended collect target**) | `https://www.newsis.com/{section}/list/?cid={cid}&scid={scid}` e.g. `/society/list/?cid=10200&scid=10201` (사회최신) | **Yes — fully server-rendered, 20 items/page** |
| Ranking (많이 본 / "이 시간 Top") | Embedded in every section/list page as `div.rankBox` (`#topnews1`–`#topnews13`). Standalone `/rank/` **does not exist** → redirects to `https://www.newsis.com/error/` | Yes — server-rendered |
| Article detail | `https://www.newsis.com/view/{article_id}` (`article_id` = `NISX{YYYYMMDD}_{10-digit-seq}` for text news, `NISI…` for photo items) | (out of scope; pattern noted for ID extraction) |

### Category (cid) map — from GNB nav, stable ids `li#top_{cid}`

| Section path | cid | Label |
|---|---|---|
| /politic/ | 10300 | 정치 |
| /world/ | 10100 | 국제 |
| /economy/ | 10400 | 경제 |
| /money/ | 15000 | 금융 |
| /business/ | 13000 | 산업 |
| /health/ | 13100 | IT·바이오 |
| /society/ | 10200 | 사회 |
| /metro/ | 14000 | 수도권 |
| /region/ | 10800 | 지방 |
| /culture/ | 10700 | 문화 |
| /sports/ | 10500 | 스포츠 |
| /entertainment/ | 10600 | 연예 |

Sub-lists use `scid` (e.g. society: 10201 사회최신, 10202 사건/사고, 10203 법원/검찰 — visible in each section's sub-nav `<li><a href="/{section}/list?cid=…&scid=…">`).

## 3. Server-rendered vs dynamic

- **Server-rendered (safe to parse without JS):** `ul.articleList2` list items on `/realnews/` and `/{section}/list/`; breaking-news ticker `div.quickNews ul.newsList`; ranking `div.rankBox`; pagination block `#paging_t1`.
- **JS-dynamic (avoid):** `div.cornList > ul` on section main pages (empty at fetch time); image crop sizing scripts; sokbo push spans.
- No embedded JSON data island (no `__NEXT_DATA__`/`window.__INITIAL_STATE__`); parse HTML directly.

## 4. Exact fields & selectors (verified against live HTML)

### 4a. Latest / category list — `ul.articleList2 > li > div.boxStyle05`

| Field | Selector (within item) | Example value |
|---|---|---|
| headline | `div.txtCont p.tit a` text | `'반도체 학과'는 모두 삼전닉스 채용 보장? 아닙니다` |
| link (relative) | `div.txtCont p.tit a[href]` | `/view/NISX20260715_0003709833` |
| article_id | last path segment of link, regex `NIS[XI]\d{8}_\d{10}` | `NISX20260715_0003709833` |
| summary/lede | `div.txtCont p.txt a` text | first ~200 chars of body |
| reporter (byline) | `div.txtCont p.time span` text | `이현주기자` |
| published_at | `div.txtCont p.time` text after span, format `YYYY.MM.DD HH:MM:SS` (KST) | `2026.07.15 09:33:20` |
| thumbnail | `div.thumCont img[src]` (protocol-relative `//image.newsis.com/...`) | `_thm.jpg` variant |
| publisher | constant: `뉴시스` (Newsis) — not per-item in markup |
| category | not in item markup — derive from the requested `cid`/`scid` |

20 items per page.

### 4b. Ranking — `div.rankBox` (on every section/list page)

- Tabs: `div.sectName div.tit a[href="#topnewsN"]` give tab labels (N=1 종합, 2 정치, 3 국제, 4 경제, 5 금융, 6 산업, 7 IT·바이오, 8 사회, 9 수도권, 10 지방, 11 문화, 12 스포츠, 13 연예).
- Items: `div#topnewsN ul.left li a` (ranks 1–6) then `div#topnewsN ul.right li a` (ranks 7–12). **Rank = DOM order** (left list first, then right). Fields: headline = `a` text, link = `a[href]`. No time/reporter in ranking items.
- Note: markup has an unclosed `</ul>` before `</div>` on `ul.right` — use a lenient HTML parser (BeautifulSoup/lxml), not strict XML.

### 4c. Breaking ticker — `div.quickNews ul.newsList li`

- `li[pushdate]` attribute = `YYYYMMDDHHMMSS` (KST); `a[href]` = link; `a` text = headline.

### 4d. Pagination

- Block `div#paging_t1`; numbered links `span.num a[href="?cid=…&scid=…&page=N"]`, plus `button.next` / `button.end` anchors.
- Confirmed working: `&page=2` returns a distinct older set (page1 first item `NISX20260715_0003709833` vs page2 `NISX20260715_0003709700`). `/realnews/` uses the same `#paging_t1` / `?page=N` scheme.

## 5. Sanitized minimal fixture contract

Machine-readable contract in sibling file `NEWSIS_FIXTURE_CONTRACT.json`. Fixture rules:

- Fixtures are **sanitized static HTML snippets** (one list page, one rankBox fragment), max 3 items per surface, with real headlines replaced by placeholder Korean text and article IDs rewritten to the reserved pattern `NISX19700101_0000000001..3`.
- Never store live article bodies, images, or full pages in the repo; thumbnails replaced by `//image.newsis.com/FIXTURE_thm.jpg`.
- Parser must be validated against: (a) item extraction from `ul.articleList2`, (b) rank ordering from `rankBox` left→right, (c) `pushdate` attribute parsing, (d) `?page=N` URL construction.

## 6. Collector recommendations (design-time notes only — NO implementation in this work order)

1. Primary feed: `/{section}/list/?cid=…&scid=…` pages (fully static, paginated, 20/page).
2. Ranking feed: parse `div.rankBox` from any single fetched page (e.g. `/society/list/…`) — no extra request needed.
3. Secondary/fallback feed: Google News sitemap `https://www.newsis.com/newsis_news_google.xml` (robots-allowed).
4. Respect robots: never request `/search/`, `/ar_detail/`, `/common/`.
5. Stop conditions: HTTP ≠ 200, redirect to `/error/`, or any challenge page → cache fallback per fallback-first contract.
