# Claude Code Fable 5 Work Order — Category Media + Publish Package V1

## Objective

Implement the smallest reversible CardNews path that takes an owner-selected topic plus already
discovered/local media candidates, separates everything by editorial category, builds a truthful
media pack, and emits a manual-upload publish package. Do not search the web, publish, create
external accounts, call paid generation providers, or modify WorkflowEngine.

## Required reading

- `AGENTS.md`
- `PROJECT_OPERATING_SYSTEM.md`
- `docs/CARDNEWS_MULTI_ACCOUNT_DIRECTIVE.md`
- `.claude/skills/domain/cardnews.md`
- `.codex/skills/ai-content-os-card-news/SKILL.md`
- `.codex/skills/ai-content-os-publishing/SKILL.md`
- `knowledge/owner_directives/cardnews_owner_directives.json`
- `knowledge/owner_feedback/cardnews_owner_feedback.jsonl`
- `config/source_intake_account_routing.json`
- `modules/card_news/card_news_result_manifest.py`
- `modules/publishing/publishing_module.py`
- `scripts/extract_cardnews_video_clip.py`

## Owned files only

- `config/cardnews_category_packages.json`
- `modules/card_news/category_media_pack.py`
- `modules/publishing/category_publish_package.py`
- `scripts/build_category_publish_packages.py`
- `tests/test_category_media_pack.py`
- `tests/test_category_publish_package.py`
- `external_workclaude/category_publish_package_v1/HANDOFF.md`

One writer owns these files. Do not edit any other file.

## Required behavior

1. Category-first separation, never one universal account folder. Resolve these canonical buckets:
   - `major_news_policy` -> `news_policy_society`
   - `incident_conflict` -> `news_incident`
   - `economy_market` -> `news_economy_market`
   - `entertainment_relationship` -> `relationship_entertainment`
   - `community_buzz` -> `community_story`
   - `beauty_fashion` must split into `fashion` or `beauty` from explicit vertical/category metadata;
     if absent, block honestly instead of guessing.
2. Input is a reviewed JSON object/file containing selected topic metadata, category/vertical,
   caption, source records, slide/media records, and local paths and/or remote URLs already
   discovered upstream. Do not perform arbitrary search.
3. Media pack validates and inventories candidates. Local files may be copied into the artifact
   package. Remote URLs remain manifest references by default; an explicit opt-in download mode may
   fetch only the supplied URLs with timeout/size/type limits and honest per-item diagnostics.
4. Preserve source URL, publisher/brand, media type, slide role, origin (`official`, `news`,
   `community`, `generated`, `local_created`), and whether it is source evidence or auxiliary media.
   AP-origin items must remain reference-only and must not be promoted into a publishable asset.
5. Emit under `artifacts/publish_packages/<date>/<category>/<topic_slug>/` with distinct
   `media_pack/` and `publish_package/` directories, ordered slide filenames, `caption.txt`,
   `sources.txt`, `manifest.json`, and a lightweight local `preview.html` that uses relative paths.
6. News caption/source behavior: retain supplied news-source attribution in the caption/package;
   do not add investigative language or internal review warnings to public copy. Community story
   packages must not invent or force a source line when none is supplied.
7. Mixed PNG/JPG/WebP/MP4 carousel ordering must be preserved. Never present generated/animated
   media as source footage or evidence.
8. Manual upload only. Never call Instagram/Meta APIs and never mark an item published.
9. Missing input/media/caption/source produces a useful blocked/fallback manifest, not an exception
   that escapes the builder.
10. Reuse current repository contracts where possible; do not edit existing renderer, Publishing
    Module, CardNews Module, storage, or shared project docs.

## Prohibited files/actions

- No edits outside the owned list.
- No `src/workflow_engine.py`, existing CardNews/Publishing files, storage outputs, shared status
  documents, owner inbox, site, Commerce, Shorts, Git, posting, automation, login, paid API, Claude
  subagents, or new project/worktree.
- No broad refactor and no fabricated facts, comments, sources, metrics, or media rights.

## Completion checks

Implement completely first. Then run exactly once at the end:

- `py -m compileall modules/card_news/category_media_pack.py modules/publishing/category_publish_package.py scripts/build_category_publish_packages.py`
- `py -m unittest tests.test_category_media_pack tests.test_category_publish_package`

Do not run the full Workflow because this isolated manual-package path does not modify
WorkflowEngine. Write `HANDOFF.md` with changed files, input/output contract, category mapping,
test results, fallback behavior, unresolved gaps, and explicit confirmation of prohibited actions
not taken.
