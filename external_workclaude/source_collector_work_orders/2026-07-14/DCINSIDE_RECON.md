# DCInside Public List-Surface Reconnaissance

- Date: 2026-07-15 (work order 2026-07-14)
- Scope: read-only inspection of public DCInside list surfaces (gallery lists, 실시간베스트, 힛갤, per-gallery 개념글/recommend mode). No adult/restricted boards entered, no account/social actions, no code implemented.
- Method: plain HTTPS GET with a desktop Chrome User-Agent (curl), raw HTML inspection. No login, no cookies, no JS execution needed.

## 1. Canonical URLs and redirects

| Surface | Canonical URL | Notes |
|---|---|---|
| Regular gallery list | `https://gall.dcinside.com/board/lists/?id=<gallery_id>` | HTTP 200, fully server-rendered |
| Minor gallery list | `https://gall.dcinside.com/mgallery/board/lists/?id=<gallery_id>` | Same markup family (path prefix `mgallery/`) |
| 실시간 베스트 (site-wide best) | `https://gall.dcinside.com/board/lists/?id=dcbest` | Behaves as a normal gallery; internal links carry extra `&_dcbest=1` |
| 힛갤 (hit gallery, curated best) | `https://gall.dcinside.com/board/lists/?id=hit` | Normal gallery markup |
| Per-gallery 개념글 (recommend) | `https://gall.dcinside.com/board/lists/?id=<gallery_id>&exception_mode=recommend` | HTTP 200, same row markup, 50 rows/page |
| Post view | `https://gall.dcinside.com/board/view/?id=<gallery_id>&no=<post_no>` | Relative hrefs in list rows resolve to this |

Redirect behavior:
- `http://` upgrades to `https://` (standard).
- `/board/lists?id=dcbest` (no trailing slash) returns 200 directly — no redirect issued; both forms serve the same page. Use the trailing-slash form as canonical since all internal links use it.
- No geo/consent/interstitial redirect observed from a plain GET.

## 2. Server-rendered vs dynamic

The list table is **fully server-rendered HTML** — all fields below are present in the initial response body with a plain GET and no JavaScript. No embedded JSON state (no `__NEXT_DATA__`-style blob) is needed; parse the DOM directly. Thumbnails and nickname icons load lazily but their URLs are inline in the HTML.

## 3. Row structure and selectors (verified 2026-07-15)

Container: `table.gall_list > tbody > tr.ub-content`

- Real posts additionally carry class `us-post` → **use `tr.ub-content.us-post`** to skip pinned rows (설문/survey, 공지/notice, AD).
- Row attributes: `data-no` (post number), `data-type` (post kind: `icon_txt`, `icon_pic`, `icon_recomtxt`, `icon_recomimg`, `icon_btimebest`, `icon_hit`, `icon_notice`, …). Rows with a thumbnail also have class `thum`.

Per-row cells (all `td` children of the row):

| Field | Selector | Format / notes |
|---|---|---|
| Post number | `td.gall_num` | Digits for real posts; `공지`/`설문`/`AD` for pinned rows |
| Title + link | `td.gall_tit.ub-word > a:first-child` | Text = title; `href` is relative (`/board/view/?id=...&no=...&page=1`, plus `&_dcbest=1` on dcbest, `&exception_mode=recommend` in recommend mode) |
| Origin board tag (dcbest only) | `td.gall_tit strong` | e.g. `[해갤]` — source gallery abbreviation prefixed inside the title anchor; absent on normal galleries |
| Comment count | `td.gall_tit a.reply_numbox span.reply_num` | Bracketed, e.g. `[21]` or `[6108/2]` (total/voice); strip brackets, take first number |
| Author | `td.gall_writer.ub-writer` | Attributes `data-nick`, `data-uid` (empty for guests), `data-ip` (set for guests) |
| Date | `td.gall_date` | Visible text is short (`07.11` same-year, `23.10.05` older, `26/07/13` on survey rows); **`title` attribute holds full `YYYY-MM-DD HH:MM:SS`** — always prefer `title` |
| Views | `td.gall_count` | Integer; `-` on survey rows |
| Recommends | `td.gall_recommend` | Integer; `-` on survey rows |
| Thumbnail (optional) | `td.gall_tit div.thumimg img[src]` | Only on `tr.thum` rows |
| Rank | not provided | No explicit rank field; rank = 1-based row order among `us-post` rows on the page |

Header row confirms column semantics: 번호 / 제목 / 글쓴이 / 작성일 / 조회 / 추천.

## 4. Pagination

- Query param `page=N` (1-based): `/board/lists/?id=dcbest&page=2&_dcbest=1`.
- Numeric pager rendered server-side (current page in `<em>`, others as `<a>`); page size options 30/50/100 via `listDisp(n)`; recommend mode returned 50 rows/page.
- For collection, page 1 alone is sufficient for a top-N trend snapshot.

## 5. Access blockers and compliance

- **robots.txt (gall.dcinside.com, v2.1.2): AI crawlers are disallowed site-wide** — `GPTBot`, `ClaudeBot`, `anthropic-ai`, `Claude-Web`, `Google-Extended`, `CCBot`, `Bytespider`, `PerplexityBot`, etc. all get `Disallow: /`. Generic `User-agent: *` is `Allow: /` except: `/kcaptcha/image_v3/`, a specific board blocklist (`47`, `cat`, `dog`, `stock_new`, `stock_new2`, `baseball_new8`, `m_entertainer1`, `ib_new`, `d_fighter_new1`, `produce48`, `sportsseoul`, `metakr`, `salgoonews`, `singo`, mgallery `rezero`), and individual post URLs. **Decision needed from CTO/owner: DCInside explicitly opts out of AI-agent access; the collector design should treat DCInside as robots-restricted and either skip live collection or get an explicit policy decision before Sprint implementation.** Blocking is advisory (a ClaudeBot UA string still received HTTP 200), but the stated policy is unambiguous.
- No captcha, login wall, or Cloudflare challenge encountered on any list page fetched with a browser UA. Captcha exists on the site (`/kcaptcha/`) but was not triggered by read-only list GETs.
- Adult/restricted boards: not entered (out of scope). Regular list surfaces required no age gate.
- Encoding: UTF-8. Response sizes ~100–220 KB per list page.

## 6. Recommended collection surface

For the trend-collector use case, **`?id=dcbest` page 1** is the best single surface: site-wide, pre-ranked by DCInside itself, includes origin-gallery tag, and one GET yields a full page of items with title/board/time/views/comments/recommends — subject to the robots policy decision above. `?id=hit` is curated/slow-moving (dates span years) and is not suitable for real-time trends. Per-gallery `exception_mode=recommend` works identically if targeted galleries are ever needed.

## 7. Fixture contract

See `DCINSIDE_FIXTURE_CONTRACT.json` in this directory: minimal sanitized record shape a future `dcinside_collector` must emit and that offline fixtures must mirror. Sanitization: drop `data-uid`/`data-ip`/nickname (author identity not needed for trend ranking), keep only public aggregate fields.
