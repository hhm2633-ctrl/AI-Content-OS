# QA Report — Instagram Feed-Native Design Scan V1

## Completion checks (per WORK_ORDER.md)

| Check | Result |
|---|---|
| JSON parses | **PASS** — validated with `ConvertFrom-Json`, no errors |
| No candidate uses a non-existing layout ID | **PASS** — all 18 `mapped_existing_layout_candidate` values fall within the 10 approved layouts (`notebook`, `dark_editorial`, `bold_ai`, `character_diary`, `comparison`, `tutorial`, `checklist`, `timeline`, `warning`, `number_list`) |
| No status other than `CANDIDATE` | **PASS** — no `VERIFIED`/`PROVEN`/`PROMOTED` language used anywhere in the JSON or Markdown deliverables |
| No detailed candidate lacks `source_surface`, `post_type`, `mapped_existing_layout_candidate` | **PASS** — all 18 candidates have non-null values for all three fields |
| Duplicate control: max 2 detailed candidates per account | **PASS** — every account appears at most once among the 18 detailed candidates |
| Actual counts reported | **PASS** — see `README.md` and `RAW_FEED_TRIAGE.md` |

## Blockers encountered

### 1. Screenshot-capture tool instability (primary blocker)

Partway through the scan, the Claude-in-Chrome `computer` tool's `screenshot` action began
intermittently returning fully blank (all-white) JPEG captures, even though the underlying page
had rendered content (confirmed via `get_page_text` and accessibility-tree reads, which continued
to return correct data during the same blank-screenshot windows). This behavior:

- Was not correlated with any specific post type (occurred on cardnews carousels, reels, and ad
  units alike).
- Was not accompanied by any Instagram-side interstitial, login prompt, captcha, or security
  challenge — `get_page_text` and `find` continued to return normal Instagram content throughout.
- Was only reliably resolved by navigating to `https://www.instagram.com/` again (a full reload),
  which restored screenshot rendering but reset the feed to the top, re-surfacing previously-seen
  posts and capping forward progress.

Because of this, raw screenshot files could not be reliably saved to
`F:/AI-Content-OS-Data/design_learning/instagram_feed_native_v1/` as the work order specifies.
Every `screenshot_path_if_captured` field in the JSON is `null` for this reason. Design fields were
instead captured through direct visual inspection during the windows when screenshots did render,
supplemented by DOM/accessibility-tree text extraction (`get_page_text`, `find`, `read_page`) for
account handles, post URLs, engagement counts, and caption text.

**Impact:** Collected 18 of the targeted 30 detailed candidates. This is a tool-reliability
shortfall, not a natural-exposure shortfall — cardnews carousels were common throughout the
sampled feed window (an estimated 18 of ~34 distinct posts triaged, roughly 1 in 2), so a longer
or more stable session would very likely have reached 30.

### 2. One candidate with unconfirmed design fields

`ai.is.well` (candidate #16) was identified as a `carousel_cardnews` post (8 slides confirmed via
accessibility-tree slide-selector buttons, account handle and post URL confirmed via `find`), but
its cover text, color palette, and visual style could not be confirmed before the screenshot tool
failed for that post specifically and the scan window closed. It is included in the dataset for
count-integrity purposes only, with all unconfirmed fields set to `null` and a `risk_flags` entry
explaining the gap. It should not be used as a basis for any design-pattern conclusion.

### 3. Ad/duplicate content re-surfacing across reloads

Because recovering from the screenshot-tool failure required reloading the feed (see blocker #1),
some ad units and posts (e.g. `publly.co`, `onnydesign`) were seen more than once across reload
boundaries. These are noted in `RAW_FEED_TRIAGE.md` but not double-counted in the aggregate totals
or in the 18 detailed candidates.

## What was NOT done (per safety constraints, as instructed)

- No keyword or hashtag search was used at any point — all candidates were surfaced via natural
  home-feed scrolling only.
- No likes, comments, saves, follows, or DMs were sent.
- No posting or publishing action was taken.
- No login, age-gate, captcha, or account-security challenge was encountered, so no such-condition
  stop was required.
- No Git operations were performed as part of this scan task itself (file writes only).

## Recommendation for a follow-up run

If a full 30-candidate scan is required, a follow-up session should either (a) use a
browser-automation environment with more stable screenshot capture, or (b) accept periodic reloads
as an expected cost and explicitly re-triage from the top each time to avoid gaps, budgeting
roughly 2x the session length used here.
