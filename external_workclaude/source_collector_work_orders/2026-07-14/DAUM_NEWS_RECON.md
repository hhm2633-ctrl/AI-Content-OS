# Daum News — Public Page Recon (Read-Only)

Date: 2026-07-15 (recon performed 2026-07-14/15 session)
Scope: Public, unauthenticated read-only inspection of Daum News category pages. No login/captcha encountered. No code implemented per work order.

## 1. URLs tested

| URL | Result | Notes |
|---|---|---|
| `https://news.daum.net/` | 200 OK | Homepage, server-rendered list of headline items. No visible "ranking/popular" link in nav or DOM (`a[href*=ranking]` / `[href*=popular]` query returned empty). |
| `https://news.daum.net/ranking/popular` | **404** | Confirmed via direct navigation (Playwright, real browser render) — page title "Daum \| 페이지를 찾을 수 없습니다". This path does not exist currently, despite being referenced by external search results/older docs. **Do not build a collector against this URL without re-verifying it first.** |
| `https://news.daum.net/ranking/popular?regDate=YYYYMMDD` | 404 | Same as above; query param does not resurrect the route. |
| `https://news.daum.net/breakingnews/society` | 200 but **redirects to homepage** (`/`) | Old-style category path no longer resolves to a category page; silently redirected, no error. |
| `https://news.daum.net/society` | 200 OK | Valid category page, real server-rendered content confirmed. |
| `https://news.daum.net/politics` | 200 OK | Valid category page, same structure as `/society`. |
| `https://news.daum.net/robots.txt` | **404** (true 404, verified via `fetch()` in-page, status code + HTML 404 body returned) | `news.daum.net` has **no robots.txt of its own**. robots.txt is scoped per-origin, so `www.daum.net`'s robots.txt does NOT apply to `news.daum.net`. |
| `https://www.daum.net/robots.txt` | 200 OK | Applies only to the `www.daum.net` origin. Content: `User-agent: * / Disallow: / / Allow: /$` (root only) plus `/ads.txt`, `/app-ads.txt`. **This is a different host and does not govern `news.daum.net`.** Included for completeness only — do not treat it as authoritative for the news subdomain. |

Valid category slugs observed working: `society`, `politics` (pattern: `https://news.daum.net/<category>`). Other category slugs (economy, world, culture, it, etc.) were shown as nav labels on the homepage but were not individually re-verified — verify each before use.

## 2. Access blockers

- No login wall.
- No CAPTCHA.
- No JavaScript-gated content wall: category-page article list (headline, description, source, relative time) is present in the initial server-rendered HTML (confirmed by direct DOM inspection immediately after navigation, and no client-side JSON payload populates it — see §4).
- `news.daum.net` has no robots.txt (404). This is not the same as an explicit "Allow: /" — absence of a robots.txt is conventionally read as no crawl restriction declared, but this is a legal/policy judgment call, not a technical fact this recon can resolve. Flag for the requester's own ToS/legal review before building a persistent collector; this recon does not constitute that review.

## 3. Stable selectors (from `/society`, `/politics` — live DOM, verified via `document.querySelector`)

- List container: `ul.list_newsheadline2` inside `div.box_comp.box_news_headline2`
- Item: `li` (no class)
- Article link: `a.item_newsheadline2[href^="https://v.daum.net/v/"]`
  - `data-tiara-ordnum="N"` — **1-indexed order/rank of the item within the list** (confirmed present: `data-tiara-ordnum="1"` on first item)
  - `data-title="<url-encoded headline>"` — redundant copy of headline, URL-encoded
  - `data-tiara-layer="news"`
- Headline text: `strong.tit_txt` (inside `a.item_newsheadline2 > div.cont_thumb`)
- Description/snippet: `p.desc_txt`
- Source + time: `span.info_txt > span.con_txt > span.txt_info` — **two sibling `span.txt_info` elements**: first = source name (e.g. "머니투데이"), second = relative time (e.g. "22분 전")
- Thumbnail: `div.wrap_thumb > picture > source[srcset]` (webp + fallback) and `img.img_g`
- Category: not present as a field within the list item itself — category is implied by the page URL slug (`/society`, `/politics`), not per-item markup, on these listing pages.

No `<script>` tag contains embedded JSON state (no `__NEXT_DATA__`, `__NUXT__`, or similar). Content is plain server-rendered HTML text nodes — confirmed by scanning all `<script>` tags on the page for JSON-shaped content (none found beyond an unrelated dark-theme toggle snippet).

## 4. Article permalink pattern

```
https://v.daum.net/v/<17-digit id>
```
Example: `https://v.daum.net/v/20260715040308416` — first 14 digits appear to be a `YYYYMMDDHHMMSS` timestamp, remaining 3 digits a sequence/hash suffix. Not independently verified against a second source; treat as an observed pattern, not a documented contract.

## 5. Canonical / redirect behavior

- No `<link rel="canonical">` tag found on `/politics` (checked via `document.querySelector('link[rel=canonical]')` → none).
- `/breakingnews/society` redirects (200, final URL `/`) rather than 404ing — silent failure mode a collector must guard against by checking final resolved URL / expected DOM markers, not just HTTP status.
- `/ranking/popular` is a **hard 404**, not a redirect — this old path is fully gone.

## 6. Recommendation on static-HTML feasibility

Feasible for category pages (`/<category>` pattern) using static HTML parsing (no JS execution required) — content is server-rendered and selectors above are stable CSS selectors, not generated/obfuscated class names. **Not feasible for `/ranking/popular`** as that route currently 404s; if a "most-read ranking" feed is required, the URL must be rediscovered (it may have moved under a different path, e.g. per-category ranking widgets, or may require checking the site's current nav/sitemap) before any implementation work begins.
