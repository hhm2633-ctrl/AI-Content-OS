# Asset Provenance Audit V1.6

Target: `output_set_id = f2281e14df8d4ab68a46152e93e9029b`. Read-only, cross-referenced directly
against `storage/image_strategy/image_strategy_result.json`,
`storage/output_sets/card_news/sets/f2281e14df8d4ab68a46152e93e9029b/09_publishing_result.json`,
and the four committed card PNGs.

## What "Image Strategy selected a real image source" actually means

The console log from the V1.5 run printed:

```
Image Prompt Module Skipped: Image Strategy selected a real image source
Image Generation Module Skipped: Image Strategy selected a real image source
```

Read at face value, this could be misread as "a real image was obtained." It was not. The actual
`storage/image_strategy/image_strategy_result.json` for this run states:

```json
{
  "content_type": "community",
  "image_source": "post_capture",
  "need_ai_image": false,
  "image_usage_plan": {
    "mode": "real_image_required",
    "recommended_source": "post_capture",
    "notes": "content_type 'community'은 AI 이미지 대신 실제 이미지(post_capture)를 사용하는 것을 권장함. 실제 수집/캡처 자동화는 아직 구현되지 않았으므로 수동 소싱 또는 향후 Sprint 연동이 필요하며, 이번 실행은 AI 이미지 생성을 생략함."
  }
}
```

**`image_source: "post_capture"` is a strategy recommendation string -- which category of real
image the content type should ideally use -- not an image, a URL, or a file reference.** The
module's own note is explicit: real capture/collection automation does not exist yet
("실제 수집/캡처 자동화는 아직 구현되지 않았으므로"), so this run only skipped the *AI-generated*
image path; it did not, and could not, fetch or verify a real photo.

## Checklist answers

- **Is it a candidate URL?** No. No URL, no candidate reference of any kind -- just the string
  `"post_capture"` naming a source *type*.
- **Is it an actually-downloaded image?** No. `09_publishing_result.json.image_sourcing_status.real_image_used_count = 0`, and its own `checklist` states plainly: `"실제 이미지가 없어 이번 렌더링은 solid-color 배경으로 대체되었습니다."` (no real image exists, so this render substituted a solid-color background).
- **Is usage-rights verified?** Not applicable -- there is no real asset to verify rights for. Every card in `pre_publish_attestation.assets[]` shows `"rights_status": ""` and `"rights_evidence_status": "blocked"`.
- **Relationship to the fallback PNG**: the four committed PNGs
  (`storage/output_sets/card_news/sets/f2281e14df8d4ab68a46152e93e9029b/cards/card_news_{1..4}.png`,
  confirmed 1080x1080, decodable, immutable -- see `CARDNEWS_WORKFLOW_RC_V1_5.md`) **are** the
  solid-color-background fallback renders described in the checklist above. There is no separate
  "real image" file anywhere in this output set to compare them against -- the fallback *is* the
  entire visual content of every card.
- **Was the external/strategy image ever promoted to a real publish asset?** **No, confirmed on
  every available signal:**
  - `pre_publish_attestation.assets[*].classification == "technical_fixture_not_publish_approved"` for all 4 cards.
  - `pre_publish_attestation.assets[*].render_allowed == false` for all 4 cards.
  - `pre_publish_attestation.render_allowed_asset_ids == []`.
  - `pre_publish_attestation.publish_ready == false`, `actual_publish == false`.
  - `09_publishing_result.json.actual_publish == false`, `package_ready == false`, `publishing_ready == false`.
  - `manifest.json.release_ready == false`, `manifest.json.actual_publish == false`.

At no point in this pipeline is a fallback/solid-color card treated as, or promoted to, a real
publish-approved asset. The system is correctly, consistently fail-closed on this point across
every JSON artifact checked.

## Why this matters for the blocker audit

`PUBLISH_MANUAL_IMAGE_REQUIRED` exists specifically because of this gap (community content type
needs a real captured image, none exists). That blocker is a genuine, correctly-firing
`EXPECTED_USER_INPUT_BLOCKER` -- supplying a real, rights-clear `post_capture` screenshot of the
source community post and re-rendering is the concrete, non-technical action that would clear it.
It would not, by itself, clear `PUBLISH_RIGHTS_BLOCKED` / `PUBLISH_EVIDENCE_BLOCKED` (those also
need a code-side intake mechanism that does not exist yet, see `PUBLISH_BLOCKER_AUDIT_V1_6.md`
§1-2), nor `PUBLISH_MANIFEST_PATH_MISMATCH` (an independent defect unrelated to whether the image
is real, see §5 of that same document).
