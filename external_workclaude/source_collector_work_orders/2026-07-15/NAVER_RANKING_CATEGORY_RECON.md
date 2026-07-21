# Naver News Ranking / Category Pages — Reconnaissance Report

- **Date:** 2026-07-15 (KST)
- **Mode:** Read-only public-web reconnaissance. No credentials, no Naver API HUB secrets, no social actions, no downloads beyond page HTML, no code changes.
- **Method:** Plain HTTPS GET with a desktop Chrome User-Agent (and control probes with `python-requests` / `curl` UAs), structural analysis of returned HTML/JSON. No login or session cookies used.
- **Companion contract:** `NAVER_RANKING_CATEGORY_FIXTURE_CONTRACT.json` (same folder).

---

## 1. Accessibility summary

| Page | Stable URL | HTTP | Rendering | Encoding | Verdict |
|---|---|---|---|---|---|
| Daily ranking (per-publisher) | `https://news.naver.com/main/ranking/popularDay.naver` | 200 | Fully server-rendered | **EUC-KR** | Accessible |
| Ranking for a past date | `.../popularDay.naver?date=YYYYMMDD` (verified `20260714`) | 200 | Server-rendered | EUC-KR | Accessible |
| Society section | `https://news.naver.com/section/102` | 200 | Server-rendered | UTF-8 | Accessible |
| Economy section | `https://news.naver.com/section/101` | 200 | Server-rendered | UTF-8 | Accessible |
| World section | `https://news.naver.com/section/104` | 200 | Server-rendered | UTF-8 | Accessible |
| Section "more" endpoint | `https://news.naver.com/section/template/SECTION_ARTICLE_LIST?sid=<sid>&pageNo=<n>[&next=<cursor>]` | 200 | JSON wrapping rendered HTML | UTF-8 | Accessible |
| Entertainment ranking | `https://entertain.naver.com/ranking` → redirects to `https://m.entertain.naver.com/ranking` | 200 | **SPA shell (~2 KB), JS-rendered only** | UTF-8 | **Blocked for static fetch** |

Additional observations:

- No captcha, no login wall, and no security challenge was encountered on any probed page. The `nidlogin` strings in the HTML are just the standard header login link.
- `news.naver.com` served HTTP 200 with full content even to `python-requests/2.31` and `curl/8.0` User-Agents (no UA-based blocking observed at probe time). This does **not** imply permission — see §5.
- `https://entertain.naver.com/robots.txt` does not return a robots file; the request is redirected to the `m.entertain.naver.com/home` SPA shell. Entertainment content lives on a separate subdomain with a separate (client-rendered) architecture.
- Known but **unverified** variant: `popularMemo.naver` (most-commented ranking). Not probed; treat as out of contract.

### Category → URL mapping (news.naver.com sections)

| Category | sid | URL |
|---|---|---|
| Politics | 100 | `/section/100` (not probed, same template family) |
| Economy | 101 | `/section/101` ✅ probed |
| Society | 102 | `/section/102` ✅ probed |
| Life/Culture | 103 | `/section/103` (not probed) |
| World | 104 | `/section/104` ✅ probed |
| IT/Science | 105 | `/section/105` (not probed) |
| **Entertainment** | — | Not a news.naver.com section. Separate SPA at `m.entertain.naver.com/ranking`; **not extractable via static HTTP.** |

Important structural fact: the public "ranking" page is **grouped per publisher** (each press's top-5 most-viewed articles), not a single global top-N list, and it has **no category filter**. Category coverage must come from the section pages, whose headline block carries an internal per-block `rank` in `data-nlog-params`.

---

## 2. Ranking page structure (`popularDay.naver`)

Server-rendered, EUC-KR (a collector must decode `euc-kr`, not utf-8 — probing with utf-8 produced mojibake). Observed on probe: ~81 publisher boxes × 5 articles ≈ 405 items, 810 article links total (each item has title link + thumbnail link).

DOM skeleton per publisher box:

```
div.rankingnews_box_wrap._popularRanking
└─ div._officeCard._officeCard{n}
   └─ div.rankingnews_box
      ├─ a.rankingnews_box_head          (publisher home link)
      │  ├─ span.rankingnews_thumb > img (publisher logo)
      │  └─ strong.rankingnews_name      (publisher display name, e.g. "중앙일보")
      └─ ul.rankingnews_list
         └─ li  (×5)
            ├─ em.list_ranking_num       (rank 1–5, text content)
            ├─ div.list_content
            │  ├─ a.list_title           (title text; href = article URL)
            │  └─ span.list_time         (relative time text; present on every item)
            └─ a.list_img > img          (thumbnail; may carry strong.r_ico.r_vod_small for video)
```

- Article URL pattern: `https://n.news.naver.com/article/{officeId}/{articleId}` (officeId = 3-digit publisher code, articleId = 10-digit).
- Date control: `?date=YYYYMMDD` query param returns that day's ranking (verified for the previous day).
- No pagination — one page contains all publisher boxes.
- Fields visibly available per item: **rank (1–5), title, article URL, officeId+articleId (from URL), relative time, thumbnail URL, video badge**; per box: **publisher name, publisher logo, publisher office link**.
- Not available on this page: category/section of each article, absolute timestamps, view counts.

## 3. Section (category) page structure (`/section/{sid}`)

Server-rendered UTF-8. The page mixes a "headline" cluster block and a "latest" list; both use the same `sa_item` card markup (~46 full-text cards per initial page).

DOM skeleton per article card:

```
li.sa_item._SECTION_HEADLINE   (or latest-list variant)
└─ div.sa_item_inner > div.sa_item_flex
   ├─ div.sa_thumb > … > a.sa_thumb_link  [data-imp-url = article URL, data-nlog-params contains {"section1_id":"102","rank":N}]
   │  └─ img._LAZY_LOADING [data-src = thumbnail URL]
   └─ div.sa_text
      ├─ a.sa_text_title [href = article URL] > strong.sa_text_strong  (title)
      ├─ div.sa_text_lede                                              (summary/lede text)
      └─ div.sa_text_info
         ├─ div.sa_text_press                                          (publisher name)
         ├─ a.sa_text_cmt._COMMENT_COUNT_LIST [data-object-id="news{officeId},{articleId}"]
         ├─ div.sa_text_datetime > b                                   (relative time, e.g. "12분전")
         └─ a.sa_text_cluster > span.sa_text_cluster_num               (related-article cluster count)
```

- Article URL pattern here: `https://n.news.naver.com/mnews/article/{officeId}/{articleId}`.
- `data-nlog-params` carries `section1_id` (category sid) and `rank` (position within the headline block) — the only rank-like signal on category pages.
- Timestamps are **relative Korean strings** ("12분전", "1시간전"); absolute time requires opening the article page (out of scope here).

### Pagination ("더보기") — verified working

`GET https://news.naver.com/section/template/SECTION_ARTICLE_LIST?sid={sid}&pageNo={n}&next={cursor}`

- Returns JSON: `{"component": {...}, "renderedComponent": {"SECTION_ARTICLE_LIST": "<html fragment>"}, "uhv": ...}` — the fragment is the same `sa_item` markup.
- Cursor protocol (embedded as data attributes on the fragment root): `data-has-next="true|false"`, `data-cursor-name="next"`, `data-cursor="<YYYYMMDDHHMMSS>"` (a KST timestamp cursor, e.g. `20260715150418`).
- Verified: page 2 → cursor `20260715150418` → page 3 with `&next=<cursor>` returned 200 with 36 distinct new items and a new, older cursor. No date-range control on section pages; the cursor walks backward in time.

## 4. Entertainment — blocked for static collection

`entertain.naver.com/*` (including `/ranking`) redirects to `m.entertain.naver.com` and serves an ~2 KB SPA shell with no article content, no `__NEXT_DATA__`/preloaded-state payload, and no robots.txt. Content is materialized client-side by JS calling internal, undocumented APIs. **Static HTTP collection is not viable**; extraction would require headless-browser rendering or reverse-engineering private APIs — both out of scope and not recommended. Recommendation: defer entertainment, or source it later via the sanctioned Naver Open API / a licensed feed.

## 5. Robots, terms, and attribution — the decisive constraint

`https://news.naver.com/robots.txt` (fetched 2026-07-15):

```
User-agent: *
Disallow: /

User-agent: FacebookExternalHit
User-agent: Twitterbot
Allow: /

# BOT ACCESS FOR THE PURPOSES OF AI TRAINING AND RETRIEVAL-AUGMENTED GENERATION (RAG) IS STRICTLY PROHIBITED.
User-agent: GPTBot / OAI-SearchBot / PerplexityBot / Google-Extended / ClaudeBot / Claude-SearchBot / meta-externalagent / Applebot-Extended / CCBot
Disallow: /
```

- **All automated access is disallowed for every agent except Facebook/Twitter link-preview bots**, and AI-training/RAG use is explicitly and separately prohibited in the file itself.
- News article copyright belongs to the individual publishers, not Naver; Naver's terms prohibit unauthorized crawling/reproduction of news content. Any lawful reuse requires publisher attribution (publisher name + original link) at minimum, and republication of article text/images generally requires a license from the publisher.
- The sanctioned programmatic path is the **Naver Open API (developers.naver.com News Search API)**, which the project already targets elsewhere; it returns titles/links/descriptions with its own quota and terms.

## 6. Fixture contract (sanitized)

Defined in `NAVER_RANKING_CATEGORY_FIXTURE_CONTRACT.json`. Two fixture types — `ranking_page` (per-publisher top-5 groups) and `section_page` (category card list + cursor pagination). Sanitization rules: strip all tracking attributes (`nclicks`, `data-nlog-*`, `data-imp-gdid`), keep at most 3 publisher groups / 10 articles per fixture, record `fetched_at` and source URL, always retain publisher attribution, never include article body text, comment counts tied to real users, or any personal data. Fixtures are for **offline parser tests only**, not for content republication.

## 7. Handoff verdict

- **Accessible (technically):** `popularDay.naver` (incl. `?date=`), `/section/101|102|104`, `SECTION_ARTICLE_LIST` JSON endpoint. All server-rendered, stable selectors documented above. No captcha/login encountered.
- **Blocked:** `entertain.naver.com` / `m.entertain.naver.com/ranking` (JS-only SPA — no static content). Entertainment category cannot be covered by this route.
- **Fields available:** rank, title, article URL (officeId/articleId), publisher, relative time, thumbnail, lede (sections only), cluster count (sections only), category sid (sections only).
- **Is implementation safe?** **Technically yes, compliance-wise no — not as an unrestricted crawler.** `robots.txt` disallows all generic bot access and expressly prohibits AI/RAG use. A production collector that scrapes these pages would violate robots.txt and likely Naver/publisher terms. Recommended gates before any implementation: (1) prefer the official Naver Open API path already planned for this project; (2) if page-level collection is ever pursued, obtain an explicit legal/compliance decision first, keep volumes minimal, cache aggressively (fallback-first), and always carry publisher attribution; (3) use the sanitized fixtures in this contract for parser development and tests so no live crawling is needed during development.
