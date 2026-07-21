# Naver News Public Comment Availability & Aggregate Metadata — Reconnaissance Report

- **Date:** 2026-07-15 (KST)
- **Mode:** Read-only public-web reconnaissance. No login, no cookies/tokens/credentials, no social actions, no code changes. **No comment bodies, usernames, or any user-identifying values were collected or reproduced** — only structural key names and article-level aggregate numbers.
- **Method:** Plain HTTPS GET with a desktop Chrome User-Agent against one live article (officeId `015`, articleId `0005310249`, picked from the public ranking page), plus robots.txt probes. Follows the completed `NAVER_RANKING_CATEGORY_RECON.md` contract.
- **Companion contract:** `NAVER_COMMENTS_METADATA_FIXTURE_CONTRACT.json` (same folder).

---

## 1. Accessibility summary

| Surface | Stable URL | HTTP | Rendering | Verdict |
|---|---|---|---|---|
| Article page | `https://n.news.naver.com/article/{officeId}/{articleId}` | 200 | Server-rendered shell (UTF-8) | Accessible |
| Article page (mnews variant) | `https://n.news.naver.com/mnews/article/{officeId}/{articleId}` | 200 | Same content | Accessible |
| Legacy URL | `news.naver.com/main/read.naver?oid=&aid=` | 200 | Redirects to the mnews URL above | Redirect only |
| Dedicated comment page | `https://n.news.naver.com/(mnews/)article/comment/{officeId}/{articleId}` | 200 | **JS skeleton only** — zero comment content in static HTML (`u_cbox_contents` count = 0) | Accessible but empty statically |
| Comment list/count API | `apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json` (JSONP) | 200 | JSON — works **without login** but **requires a `Referer` from the article page**; without Referer → `success:false, code:3999 "잘못된 접근입니다"` | Accessible (private, undocumented) |
| Reaction API | `news.like.naver.com/v1/search/contents?q=NEWS[ne_{officeId}_{articleId}]` | 200 | JSON — works without login and without Referer | Accessible (private, undocumented) |

No captcha, login wall, or security challenge was encountered anywhere (the `nidlogin` string in page HTML is just the standard header login link). No stop condition triggered.

## 2. Comment availability signal

- The article HTML contains the comment UI anchor (`#comment_count`, `_COMMENT_COUNT`, `u_cbox`/`cbox5` markers), but the **count number is NOT server-rendered** — the element's static text is the label `"댓글"` only; JS fills the number from the API.
- The authoritative availability flag is in the API response: **`result.exposureConfig = {"status": "COMMENT_ON", "reason": null}`** (verified). A publisher/article with comments disabled is expected to return a non-`COMMENT_ON` status and/or a `reason`; not verified on a closed article in this probe (no deterministic way to pick one) — treat any other status as "comments unavailable".

## 3. Aggregate (non-PII) metadata verified available

### 3a. Article page (server-rendered, static HTML)

- **Absolute timestamps** — the only place they exist in the whole ranking/section/article route family: `span._ARTICLE_DATE_TIME[data-date-time]` (publish, e.g. `2026-07-15 13:07:09`) and `span._ARTICLE_MODIFY_DATE_TIME[data-modify-date-time]` (last modified), inside the `media_end_head_info_datestamp` block.
- officeId/articleId (from URL), publisher branding, category `sid` hints.

### 3b. Comment API (`web_naver_list_jsonp.json`, `pageSize=1` count-probe)

`result.count` (verified values in parentheses): `comment` (51), `reply` (11), `total` (62), `exposeCount` (46), `delCommentByUser` (5), `delCommentByMon` (0), `blindCommentByUser` (0), `blindReplyByUser` (0), `fallback` (false). Plus `result.pageModel.totalRows/totalPages/pageSize` and `morePage` cursors.

**Sort options** (param `sort=`, echoed back in `result.sort`; all verified accepted): `FAVORITE` (순공감순), `NEW` (최신순), `REPLY` (답글순), `OLD` (과거순). Labels are the standard Naver UI names; the API itself only echoes the enum.

Request contract (verified): `ticket=news`, `templateId=default_society` (worked even for an economy article), `pool=cbox5`, `objectId=news{officeId},{articleId}`, `lang=ko`, `country=KR`, plus `Referer: https://n.news.naver.com/article/{officeId}/{articleId}`. These values are **not embedded in the page HTML** in extractable form (they live inside JS bundles) — they must be treated as hardcoded, unversioned internals.

### 3c. Reaction API (`news.like.naver.com`)

Returns `contents[].reactions[] = {reactionType, count}`. Observed on the probed article: `useful` 24, `recommend` 3, `wow` 1, `touched` 1 (news articles use the 쏠쏠정보/흥미진진/공감백배/후속강추 reaction family; the older like/warm/sad/angry family exists on other content types). Response also carries `isLogin:false` and a `guestToken` — **the token must never be stored**.

## 4. Unavailable / blocked fields

- **Comment count as static HTML** — not available; API-only.
- **Sort labels as strings** — not in the API; UI-side only.
- **Per-comment absolute permalinks/times without touching comment records** — per-comment fields exist only inside comment items, which are excluded wholesale (see §5).
- **Comments-disabled `reason` values** — unverified (no closed article probed).
- **Any official/sanctioned path** — the Naver Open API (News Search) exposes **no comment or reaction data at all**; this signal has no documented public API.

## 5. Privacy exclusions (hard prohibitions)

Comment items in the API response are dense with personal data. The comment item schema includes (key names observed; values never extracted): `userName`, `maskedUserId`, `maskedUserName`, `userIdNo`, `profileUserId`, `userProfileImage`, `userHomepageUrl`, **`exposedUserIp`**, `contents`, `mentions`, `replyList`, `badges`, `grades`, plus moderation flags. Under Korean PIPA even masked IDs and IP fragments are personal data. Therefore:

- **Never store, log, or fixture any element of `commentList` or `bestList`** — not even "just the sympathy counts", because `commentNo`/`sortValue` re-identify the comment. Only the article-level `count`, `exposureConfig`, `pageModel`, and `sort` objects are safe.
- Never store `guestToken`, cookies, or any request/response headers containing session material.
- Aggregate reaction counts and comment totals are article-level facts, not UGC, and are the only fields cleared for fixtures.

## 6. Robots / terms blockers

- `n.news.naver.com/robots.txt`: `User-agent: * Disallow: /`; only Facebook/Twitter preview bots allowed; AI-training/RAG bot access explicitly prohibited in-file.
- `apis.naver.com/robots.txt` and `news.like.naver.com/robots.txt`: `User-agent: * Disallow: /` (total disallow).
- The comment API's Referer gate (code 3999) shows Naver actively restricts non-browser access; both APIs are undocumented internals that can change or be locked down without notice.
- Comment/reaction data is Naver-platform data adjacent to UGC; publisher attribution rules from the prior recon still apply to any article metadata carried alongside.

## 7. Handoff verdict

- **Accessible aggregate metadata (technically):** comment on/off status, total/visible/deleted/blind comment counts, reply count, sort enum, page totals, article-level reaction counts, absolute publish/modify timestamps. All confirmed without login.
- **Unavailable/blocked:** static comment counts, sort labels, official API path, closed-comment behavior (unverified).
- **Privacy exclusions:** entire `commentList`/`bestList`, all user fields, IPs, tokens — see §5.
- **Implementation recommendation: DO NOT implement a live collector.** All three hosts fully disallow robots; both endpoints are private, Referer-gated, undocumented internals; and the payload is one field away from PIPA-scoped personal data. If a "comment heat" signal is ever wanted for topic ranking, it requires an explicit legal/compliance decision first, and even then only the sanitized article-level aggregates in the companion fixture contract may be stored. For now: use the fixture contract for offline schema/consumer tests only, and keep the project on the sanctioned Naver Open API path (which simply lacks this signal).
