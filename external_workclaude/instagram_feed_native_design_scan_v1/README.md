# Instagram Feed-Native CardNews Design Scan V1 — Summary

## Status

Executed per `WORK_ORDER.md`. Scan is **complete but partial**: 18 of the targeted 30 detailed
`carousel_cardnews` candidates were collected before the browser automation tool's screenshot
capture became unreliable for the remainder of the session (see `QA_REPORT.md`). No search,
hashtag, like, comment, follow, DM, or save actions were used. No login/security-challenge/captcha
was encountered.

## Browser connection status

Connected via Claude in Chrome to an already-logged-in Instagram session (`ho_hong_hongs`).
Source surface used throughout: `home_feed_natural`. `explore_feed_natural` was not needed —
cardnews carousels appeared at a healthy rate in the home feed.

## Observed counts

- Detailed `carousel_cardnews` candidates recorded: **18**
- Reels observed (counted, not detailed): **4**
- Ads observed (counted, not detailed): **7** (some ad units resurfaced across feed reloads —
  counted per distinct sighting, not deduplicated across reloads)
- Personal / single-image posts observed (counted, not detailed): **6**
- Carousel photo (no cardnews text design) observed: **1**
- Local news/community flyer-style post (counted separately from cardnews): **1**
- Approximate total posts scrolled past: **~40**

## Strongest 5 design patterns (see `DESIGN_TREND_REPORT.md` for full list)

1. **Dark gradient/neon typographic covers with no photography** (`click.wave.company`, `qjc.ai`,
   `mktg.with.ai`) — cheap to produce, high-contrast, urgency-driven copy.
2. **Real photo + minimal text label, near-zero graphic design** (`brandyclassic` — highest
   engagement in the sample at 648 likes) — story/curiosity beat production value.
3. **Bold numeral/list headline over a dramatic but topically-unrelated image**
   (`onnydesign` — 943 likes) — pattern-interrupt visual contrast outperformed literal relevance.
4. **Handwritten/notebook aesthetic paired with a comment-to-DM CTA** (`marketer_c_`) — reads as
   authentic, low-produced, and pairs a proven lead-capture mechanic.
5. **Cute mascot/pastel illustration softening a dry productivity topic** (`ai.injae`) — the only
   soft-pastel illustrated account in the sample, distinct from the dominant dark-editorial cluster.

## Account / topic bias observed

The sampled home feed skewed heavily toward **Korean-language AI-tool and AI-marketing accounts**
(Claude/MCP tooling, AI image/video generation, AI subscription bundling) — roughly 9 of the 18
detailed candidates. The remainder spanned local news/community accounts, a design-tool listicle
account, a classic-car story account, a beauty roundup account, and one illustrated tabloid-style
account. This likely reflects the seed account's own follow graph and Instagram's recommendation
weighting toward AI/tech content (many posts were explicitly labeled `회원님을 위한 추천` —
"recommended for you" — rather than from followed accounts), not necessarily the platform-wide
cardnews landscape.

## Files written

- `storage/design_learning/instagram_feed_native_design_scan_v1.json` — structured candidate data
- `external_workclaude/instagram_feed_native_design_scan_v1/README.md` — this file
- `external_workclaude/instagram_feed_native_design_scan_v1/RAW_FEED_TRIAGE.md` — fast-triage log
- `external_workclaude/instagram_feed_native_design_scan_v1/DESIGN_TREND_REPORT.md` — pattern analysis
- `external_workclaude/instagram_feed_native_design_scan_v1/QA_REPORT.md` — validation + blocker report

## Blockers / reasons for shortfall

The Claude-in-Chrome screenshot-capture tool began intermittently returning blank (all-white)
images partway through the session. This was not caused by Instagram (no login/captcha/security
interstitial appeared at any point) — it was a browser-automation tool reliability issue local to
this session. The only reliable recovery was reloading the feed URL, which reset scroll position to
the top of the home feed, capping how far forward the scan could progress before candidates started
repeating. Design-field data for one candidate (`ai.is.well`, #16) could not be fully confirmed as a
result and is flagged accordingly in the JSON. Full detail in `QA_REPORT.md`.

Raw screenshot files could not be reliably saved to
`F:/AI-Content-OS-Data/design_learning/instagram_feed_native_v1/` for this reason — the
`screenshot_path_if_captured` field is `null` for all candidates. All design observations were
instead captured via on-screen visual inspection (screenshots that did render) plus DOM/accessibility-tree
text extraction, and recorded as structured text fields rather than saved image assets.

All patterns in this scan are labeled `CANDIDATE` only — no `VERIFIED`, `PROVEN`, `PROMOTED`, or
performance-causal claims are made anywhere in these deliverables.
