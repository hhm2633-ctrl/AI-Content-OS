# TheQoo Public-Site Reconnaissance (Read-Only)

- Date: 2026-07-15 (work order 2026-07-14)
- Scope: public HOT list surfaces + one public post detail page. No login, no social actions, no restricted boards entered.
- Method: plain HTTPS GET with a desktop browser User-Agent (`Invoke-WebRequest`), plus WebFetch cross-checks. No captcha or block was triggered at any point.

## 1. Platform & Rendering

- Engine: **Rhymix** (XpressEngine fork) — `<meta name="generator" content="Rhymix">`; board skin `sketchbook5_ajax`; jQuery 2.2.4.
- **Fully server-rendered.** The HOT list page (`/hot`, ~23.6 KB) contains the complete post table in initial HTML; no client-side hydration is needed to read list data. Post detail pages (~30 KB) are also server-rendered.
- `enforce_ssl = true`; HTTP upgrades to HTTPS. Canonical form of the list URL is `https://theqoo.net/?mid=hot` internally, but the rewritten path `https://theqoo.net/hot` is stable (rewrite_level=1).
- A per-page CSRF token exists (`<meta name="csrf-token">`) but is only needed for POST actions — irrelevant for read-only collection.

## 2. Stable URLs

| Surface | URL | Notes |
|---|---|---|
| HOT list | `https://theqoo.net/hot` | 200, server-rendered table, 20 normal rows/page |
| HOT pagination | `https://theqoo.net/hot?page=N` | N observed up to ~7898 |
| HOT category filter | `https://theqoo.net/hot/category/{category_srl}` | e.g. `24788` = 이슈; combinable with `?page=N` |
| Post detail (via hot) | `https://theqoo.net/hot/{document_srl}` | e.g. `/hot/4279889037` |
| Post canonical (origin board) | `https://theqoo.net/{board}/{document_srl}` | detail page shows origin link, e.g. `https://theqoo.net/square/4279889037` |

Category sidebar (visible on `/hot`): 전체, 이슈, 유머, 정보, 기사/뉴스, 팁/유용/추천, 정치, 뷰티, 영화/드라마/방송, 도서, 먹거리, 그외/광고. A politics-exclusion toggle is cookie-based (`THEQOO_SQUARE_NO_POLITICS=1`), not URL-based.

No cross-host redirects observed; `/hot` serves directly with 200.

## 3. List Page Structure (exact selectors)

Container: `table.bd_lst.bd_tb_lst.bd_tb.theqoo_board_table` inside `div.bd_lst_wrp`; rows in `tbody.hide_notice`.

- **Notice/event rows**: `tr.notice` (some carry `data-document_srl`, `data-regdate`, `data-permanent-notice="Y"`). Skip these — filter `tr:not(.notice)` inside the tbody. 20 normal rows per page.
- Per normal `<tr>`:
  - `td.no` — board-local post number (e.g. `157952`). Descending; usable as tiebreaker, not a global id.
  - `td.cate > span` — category label (e.g. `이슈`).
  - `td.title > a[href^="/hot/"]` — title text + link. `href` is relative: `/hot/{document_srl}` (on paged views `/hot/{srl}?page=N` — strip the query for a stable id).
  - `td.title > a.replyNum` — comment count (e.g. `66`), href anchors to `#{srl}_comment`.
  - `td.title i.fas.fa-images` — presence marker for image posts (optional).
  - `td.time` — same-day posts show `HH:MM`; older posts show `MM.DD` (no year). Ambiguity must be resolved at ingest time against fetch date.
  - `td.m_no` — view count with thousands commas (e.g. `4,745`).
- **Rank**: there is no explicit rank field. Rank = 1-based position of the normal row on the page (+ 20×(page−1)).
- **Recommend count is NOT exposed in the list.** Detail pages expose views + comments in the header and a 추천(vote) button, but no reliable public recommend counter in list rows. The fixture contract marks it nullable.
- Pagination markup: `form.theqoo_pagination ul li > a[href="/hot?page=N"]`, active page `li.active`. (Note: raw HTML contains leftover Rhymix template junk in pagination anchors — `||cond="$__Context->..."` attributes — parse `href` only.)

## 4. Post Detail Page Structure

Container `div.rd[data-docSrl]` → header `div.rd_hd > div.theqoo_document_header`:

- `strong.cate[title="Category"]` — category (e.g. `이슈`)
- `span.title` — title
- `div.count_container` — `<i class="far fa-eye"></i> 5,892` (views) and `<i class="far fa-comment-dots"></i> 70` (comments); numbers are text nodes after the icons
- `.btm_area .side.fr > span` — absolute timestamp `YYYY.MM.DD HH:MM` (e.g. `2026.07.15 09:52`) — the only place the full date appears
- `.btm_area .side a.link` — canonical origin-board URL
- Author is anonymized as `무명의 더쿠` on square/hot posts
- Body: `div.rd_body article[itemprop="articleBody"] .rhymix_content.xe_content`; images served from `img-cdn.theqoo.net`
- No `og:title` meta on detail pages; parse the DOM, not OpenGraph.

## 5. Access / Blockers

- **robots.txt: HTTP 404** — no robots.txt is served. No crawl directives exist; apply self-imposed politeness (low frequency, single-threaded, cache-first per the project's fallback-first contract).
- No captcha, no Cloudflare challenge, no age-gate, and no login wall on `/hot`, `/hot?page=2`, `/hot/category/24788`, or the sampled detail page, using a normal desktop UA.
- Login exists (`/index.php?mid=hot&act=dispMemberLoginForm`) but is not required for any surface above. Restricted/member-only boards were not entered (out of scope).
- Risk notes for a future collector: default/blank UA behavior untested (always send a browser UA); rate limiting thresholds unknown — keep to the existing `RetryPolicy` + cache fallback chain used by other collectors.

## 6. Fixture Contract

See `THEQOO_FIXTURE_CONTRACT.json` (same directory). Shape mirrors the row fields above, sanitized: real titles replaced with placeholders in fixtures, numeric fields kept realistic, `document_srl` values synthetic. `recommend_count` is nullable (not publicly exposed on list surfaces). `collected_at` + raw `time_text` are both retained so the `HH:MM` / `MM.DD` ambiguity can be unit-tested.

## 7. Verbatim Samples (evidence)

List row (2026-07-15, `/hot` page 1, row 1):

```html
<tr>
  <td class="no">157952</td>
  <td class="cate"><span>이슈</span></td>
  <td class="title">
    <a href="/hot/4279889037">(펌) 유자녀 돌싱은 재혼하면 안 되겠어요</a>
    <i class="fas fa-images"></i>
    <a href="/hot/4279889037#4279889037_comment" class="replyNum">66</a>
  </td>
  <td class="time">09:52</td>
  <td class="m_no">4,745</td>
</tr>
```

Detail header count block:

```html
<div class="count_container">
  <i class="far fa-eye"></i> 5,892
  <i class="far fa-comment-dots"></i> 70
</div>
```
