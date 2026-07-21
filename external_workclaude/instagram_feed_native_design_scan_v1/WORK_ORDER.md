# Instagram Feed-Native CardNews Design Scan V1

## Objective

Observe what Instagram is naturally showing now, not what search results return. Build a design-learning pack for AI-Content-OS CardNews from feed-native card/news carousel exposure.

This is a design trend scan, not a topic recommendation, not a performance proof, and not a publishing action.

## Method

Use Claude in Chrome if connected. Do not use keyword search, hashtag search, likes, comments, follows, DMs, saves, or posting.

Start from the currently logged-in Instagram session. Prefer Home feed first; if card/news carousel volume is too low after a reasonable scroll window, use Explore feed. Keep the source label explicit:

- `home_feed_natural`
- `explore_feed_natural`
- `blocked_or_unavailable`

## Collection Target

Collect up to 30 feed-native cardnews/carousel design candidates.

If fewer than 30 are naturally exposed, stop honestly and report the shortfall. Do not fabricate, do not search to fill the quota unless explicitly marked as a separate fallback section.

## Fast Triage Rules

For every visible post while scrolling, classify quickly:

- `reel`
- `carousel_cardnews`
- `carousel_photo`
- `single_image`
- `ad`
- `personal`
- `unknown`

Only `carousel_cardnews` candidates receive detailed design analysis.

Reels, personal photos, and generic ads should be counted only unless they reveal a reusable visual style signal. Do not spend deep time on them.

## Recency

Prefer currently surfaced posts. If a visible post age is unavailable, record `visible_post_age=null` rather than guessing.

Do not include obviously old posts when a date/age is visible and stale. This scan is about current feed design feel.

## Duplicate Control

Same account: max 2 detailed candidates.

Same design template from same account: keep the strongest one and record the duplicate count.

## Fields Per Detailed Candidate

Record:

- `observed_order`
- `source_surface`
- `account_handle`
- `post_url`
- `visible_post_age`
- `post_type`
- `topic_category_guess`
- `cover_hook_text`
- `cover_visual_type`
- `color_palette`
- `typography_style`
- `image_usage`
- `slide_count_if_visible`
- `cta_type`
- `visible_likes`
- `visible_comments`
- `why_it_stopped_scroll`
- `mapped_existing_layout_candidate`
- `risk_flags`
- `screenshot_path_if_captured`
- `notes`

## Design Taxonomy

Use these starter labels, but add new labels if truly observed:

- `news_headline_card`
- `quote_overlay`
- `screenshot_commentary`
- `community_capture`
- `magazine_editorial`
- `minimal_checklist`
- `bold_number_list`
- `dark_neon_attention`
- `soft_pastel_lifestyle`
- `beauty_product_grid`
- `before_after_comparison`
- `ui_mockup_explainer`

## Mapping Rule

Map every detailed candidate to one of the existing 10 AI-Content-OS card layouts only:

- `notebook`
- `dark_editorial`
- `bold_ai`
- `character_diary`
- `comparison`
- `tutorial`
- `checklist`
- `timeline`
- `warning`
- `number_list`

Do not invent an 11th layout.

## Storage

Large/raw files:

- `F:/AI-Content-OS-Data/design_learning/instagram_feed_native_v1/`

Project summary files:

- `storage/design_learning/instagram_feed_native_design_scan_v1.json`
- `external_workclaude/instagram_feed_native_design_scan_v1/README.md`
- `external_workclaude/instagram_feed_native_design_scan_v1/RAW_FEED_TRIAGE.md`
- `external_workclaude/instagram_feed_native_design_scan_v1/DESIGN_TREND_REPORT.md`
- `external_workclaude/instagram_feed_native_design_scan_v1/QA_REPORT.md`

## Safety

- No publishing.
- No API posting.
- No likes/saves/comments/follows/DMs.
- Do not reuse competitor images as production assets.
- Screenshots are for internal design learning only.
- Do not store private DMs or personal profile data beyond public post observation.
- If login, age gate, suspicious activity, captcha, or account security challenge appears, stop and report.

## Output Judgment

Every pattern is `CANDIDATE` only.

Never use `VERIFIED`, `PROVEN`, `PROMOTED`, or causal performance claims.

## Completion Checks

Run lightweight validation:

- JSON parses.
- No candidate uses a non-existing layout ID.
- No status other than `CANDIDATE`.
- No detailed candidate lacks `source_surface`, `post_type`, `mapped_existing_layout_candidate`.
- Report actual counts: total observed posts, detailed cardnews candidates, skipped reels, skipped ads, skipped personal/single images.

## Handoff Format

Report:

1. browser connection status
2. observed counts
3. detailed candidate count
4. strongest 5 design patterns
5. account/topic bias observed
6. files written
7. blockers or reasons for shortfall

