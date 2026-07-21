# HANDOFF — Category Media + Publish Package V1

Date: 2026-07-17
Worker: Claude (Fable 5), assigned implementation specialist
Work order: `external_workclaude/category_publish_package_v1/WORK_ORDER.md`

## Changed files (owned list only)

- `config/cardnews_category_packages.json` — new. Canonical category bucket map,
  beauty_fashion split metadata rules, allowed media types/origins/extensions,
  AP reference-only agency list, internal-review caption markers, download limits
  (timeout 10s, 25 MiB, https/http, png/jpeg/webp/mp4 content types), output root.
- `modules/card_news/category_media_pack.py` — new. `CategoryMediaPackBuilder`,
  `resolve_category`, `build_topic_slug`, `load_package_config`. Validates and
  inventories supplied media candidates, copies local files into `media_pack/`,
  keeps remote URLs as manifest references, opt-in download of only the supplied
  URLs, per-item diagnostics, never raises out of `build`.
- `modules/publishing/category_publish_package.py` — new.
  `CategoryPublishPackageBuilder`. Emits ordered slide files, `caption.txt`,
  `sources.txt`, relative-path `preview.html`, and package-level `manifest.json`.
  Manual upload only; never marks anything published; never raises out of `build`.
- `scripts/build_category_publish_packages.py` — new CLI. Reads the reviewed JSON
  file, separates topics by canonical category, runs media pack then publish
  package per topic, prints honest per-topic and summary lines.
- `tests/test_category_media_pack.py` — new, 15 tests.
- `tests/test_category_publish_package.py` — new, 14 tests (builders + CLI layout).
- `external_workclaude/category_publish_package_v1/HANDOFF.md` — this file.

No other file was edited.

## Input contract

One reviewed JSON file: a single topic object, a list, or `{"topics": [...]}`.
Per topic:

```json
{
  "topic_id": "...", "topic_slug": "optional", "title": "...",
  "category": "community_buzz",
  "vertical": "fashion | beauty (required only for beauty_fashion)",
  "caption": "public feed copy (verbatim)",
  "caption_source_line": "optional explicit attribution line",
  "sources": [{"publisher": "...", "url": "...", "title": "", "note": ""}],
  "slides": [{
    "order": 1, "slide_role": "cover",
    "media_type": "image|video|screenshot|editorial|motion_graphic",
    "origin": "official|news|community|generated|local_created",
    "asset_class": "source_evidence|auxiliary",
    "source_url": "...", "publisher": "...", "brand": "...",
    "local_path": "relative-to-input-file or absolute",
    "remote_url": "https://... (used instead of local_path)"
  }]
}
```

No arbitrary search is performed; only supplied paths/URLs are used. Relative
`local_path` values resolve against the input file's directory (the CLI passes
`local_media_root`; the builder defaults to CWD when called directly).

## Output contract

`artifacts/publish_packages/<YYYY-MM-DD>/<category>/<topic_slug>/` containing:

- `media_pack/` — validated/copied media (`item_NN_<role>.<ext>`) plus
  `media_pack.json` (full inventory, statuses, diagnostics).
- `publish_package/` — ordered `slide_01.png`, `slide_02.mp4`, … (mixed
  PNG/JPG/WebP/MP4 order preserved), `caption.txt`, `sources.txt` (internal
  record, not public copy), `preview.html` (relative paths only).
- `manifest.json` at the topic root — status, category result, slide metadata
  (source_url/publisher/brand/media_type/slide_role/origin/asset_class),
  `upload_mode: "manual"`, `published: false`,
  `publish_status: manual_upload_pending | blocked`, blocking reasons, warnings.

Category-unresolvable topics emit their blocked manifest under
`<date>/_blocked/<topic_slug>/`. Blocked packages get `manifest.json` (and the
media pack inventory) but no `publish_package/` upload files.

## Category mapping

- `major_news_policy` → `news_policy_society`
- `incident_conflict` → `news_incident`
- `economy_market` → `news_economy_market`
- `entertainment_relationship` → `relationship_entertainment`
- `community_buzz` → `community_story`
- `beauty_fashion` → `fashion` or `beauty` only from explicit metadata
  (`vertical`, `canonical_category`, `category_detail`, `editorial_scope`;
  accepts fashion/beauty/패션/뷰티). Missing metadata blocks with
  `beauty_fashion_vertical_missing` — no guessing.
- Already-canonical values pass through; anything else blocks with
  `category_unknown`. Never one universal account folder.

## Caption/source behavior

- Caption is written verbatim. News categories append `참고: <publisher>` built
  only from supplied publisher fields (or the supplied `caption_source_line`),
  and only when the caption does not already contain that attribution. No
  investigative language or internal review warnings are added to public copy.
- `community_story` never gets an invented/forced source line; supplied URLs go
  to the internal `sources.txt` only.
- A caption containing internal operations markers (내부 검토, 게시 불가, 권리
  재확인, 팩트 재검증, 제작 메모) blocks the package instead of leaking the
  marker into a publishable file (OD-CARD-013).
- News packages without any supplied source record block with
  `news_source_missing`.

## Media rules enforced

- AP/Associated Press items (publisher/brand/agency match or `ap_source: true`)
  stay `reference_only` in the manifest and are never copied or downloaded into
  a publishable asset, even in download mode (OD-CARD-011).
- Generated or motion_graphic media declared as `source_evidence` is blocked
  per item with an explicit diagnostic; it is never presented as evidence.
- Remote URLs stay manifest references by default. `--download-remote` is the
  explicit opt-in; it fetches only the supplied URLs with timeout, byte-size,
  scheme, and content-type limits and records honest per-item failure
  diagnostics (`download_failed` keeps the URL as a reference).
- Validation is file-level (existence/size/extension/content-type); media
  content is not decoded, and the manifest states this scope.

## Fallback behavior

Nothing escapes the builders as an exception. Missing/invalid input, missing
category or vertical, missing media/caption/source, unreadable files, copy or
download failures, and even internal builder errors all degrade to a written
`manifest.json` with `status: *_blocked`, explicit `blocking_reasons`,
per-item `diagnostics`, and `fallback_used: true`. Missing/unreadable config
falls back to an embedded default config with a recorded warning.

## Checks actually run (each exactly once, after implementation)

1. `py -m compileall modules/card_news/category_media_pack.py modules/publishing/category_publish_package.py scripts/build_category_publish_packages.py`
   → all three compiled, no errors.
2. `py -m unittest tests.test_category_media_pack tests.test_category_publish_package`
   → `Ran 29 tests ... OK` (0 failures, 0 errors).

The full workflow was not run, as directed (this isolated manual path does not
touch WorkflowEngine).

## Final state

Implementation complete within the owned scope. The path is reversible: it adds
one config, two standalone modules, one CLI, and two test modules; no existing
module, renderer, storage output, or WorkflowEngine stage was modified. No
package artifacts were generated under `artifacts/publish_packages/` (tests use
temporary directories only).

## Unresolved gaps

- `sources.txt`/`manifest.json` live inside the manual package; the operator
  must not paste `sources.txt` into public copy (the file header states this).
- Downloaded remote assets are trusted at the content-type/size level only;
  rights confirmation stays an upstream review responsibility recorded via the
  supplied `origin`/`asset_class` metadata.
- Real account binding (account id → category folder) is intentionally out of
  scope; packages are keyed by canonical category only.
- The default fetcher exists for the opt-in mode but was exercised only through
  injected test fetchers; no live network call was made in this lane.

## Prohibited actions — confirmation

Not performed: edits outside the owned list; changes to `src/workflow_engine.py`,
existing CardNews/Publishing modules, storage outputs, shared status documents,
owner inbox, site, Commerce, or Shorts; Git operations; web search or any
network call; paid API or generation-provider calls; Instagram/Meta API calls,
posting, login, or automation; marking any item published; Claude subagents,
new projects, or worktrees; broad refactors; fabricated facts, sources,
metrics, comments, or media rights.
