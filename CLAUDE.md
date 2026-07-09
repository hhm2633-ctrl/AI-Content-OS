# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Content-OS is a modular, fallback-first content automation pipeline (Python). It collects Korean-language trends, picks a topic, generates card-news copy and images via OpenAI, renders card-news images with Pillow, and prepares an Instagram publish queue. The current business priority (per `AI_CONTEXT.md`, `CURRENT_TASK.md`, `ROADMAP.md`) is Instagram card-news automation, with the same engine intended to later expand to Shorts, Blog, SmartStore, and Coupang.

The project is developed jointly by ChatGPT (architecture/docs/decisions) and Claude/Codex (implementation). Documentation-first: architecture and specs are written before code, and `PROJECT_SNAPSHOT.md`/`CHANGELOG.md` are regenerated after meaningful changes.

## Commands

**Always use `py`, never `python`**. The `python` command is not recognized on the target Windows machine. This is a hard rule repeated across `AGENTS.md`, `CODEX_RULES.md`, `PROJECT_STATE.md`, and `MODULE_STATUS.md`.

```powershell
# Run the full workflow (trend -> topic -> research -> content -> image prompt -> image gen -> card news -> publishing)
py -m src.main

# Compile-check everything (the project's de facto build/lint check; no separate linter is configured)
py -m compileall src modules scripts

# Install dependencies
pip install -r requirements.txt
```

There is no test suite (`tests/` referenced in docs does not exist yet) and no linter/formatter config. Verification is done by running the workflow and checking for `workflow_completed`, or by module-level manual checks. Per `CODEX_RULES.md`, don't run the full workflow after every small change; run it at Sprint completion or after architecture changes.

After a change that affects workflow behavior, regenerate project docs instead of hand-editing them:

```powershell
py -m scripts.update_project_snapshot --message "Describe the change"
```

This rewrites `PROJECT_SNAPSHOT.md` (project tree + workflow module status) and appends an entry to `CHANGELOG.md`. `src/main.py` also calls this automatically after every `workflow_completed` run.

## Architecture

### Pipeline (`src/workflow_engine.py`)

`WorkflowEngine` instantiates and runs eight modules strictly in sequence, saving each stage's JSON output to `storage/workflow_results/NN_name_result.json`:

```text
TrendCollectorModule -> TopicEngineModule -> ResearchModule -> ContentModule
  -> ImagePromptModule -> ImageGenerationModule -> CardNewsModule -> PublishingModule
```

`WorkflowEngine` owns the module-to-module orchestration and persists each stage result. `TrendCollectorModule` starts the workflow with no prior result input. Most later modules receive the previous stage's result dict, while `CardNewsModule` receives both `content_result` and `image_generation_result`. Modules return result dicts that are saved by the engine; avoid direct module-to-module calls outside `WorkflowEngine`. `src/main.py` loads `config/settings.json`, runs the engine, and prints the final `status`.

### Fallback-first is the core invariant

The single most important architectural rule (stated in `AGENTS.md`, `CODEX_RULES.md`, `PROJECT_BIBLE.md`): **`workflow_completed` must never regress.** Internet, LLM, and image-API failures must degrade to a fallback/cache path, never to `workflow_failed`. Every module that talks to an external system implements a fallback chain, e.g. in `TrendSourceManager`:

```text
live collect -> retry (RetryPolicy) -> cache file (storage/cache/*.json)
  -> settings.json keyword fallback -> hardcoded placeholder fallback
```

`TrendEngineGuard` (`modules/trend_collector/trend_engine_guard.py`) is a final safety net that runs after ranking/selection and guarantees the result dict always has a non-empty `selected_topic`, reusing `last_safe_trend_result.json` if the current run produced nothing usable. When extending any collector or LLM-calling module, preserve this "always return something usable" contract rather than raising.

### Trend Collector subsystem (most developed module; Sprint 1 complete)

`modules/trend_collector/` is a small pipeline of its own, composed in `TrendCollectorModule`:

- `TrendSourceManager` reads `config/trend_sources.json`, collects from enabled sources (currently real collectors for `naver_news` and `nate_pann`; other sources like `bobaedream`, `dcinside`, `google_trends` are placeholder-only), applies `RetryPolicy`, and falls back through cache -> settings keywords -> hardcoded placeholders.
- `TrendQualityScorer` / `TopTopicPicker` rank and deduplicate candidates into a single `selected_topic`.
- `SourceHealthTracker` accumulates per-source success/failure/fallback stats into `storage/trends/source_health.json` and `collector_statistics.json`.
- `TrendEngineGuard` normalizes/repairs the final result (see above).
- `TrendRunRecorder` writes an append-only run log (`trend_run_log.jsonl`), timestamped snapshots (`storage/trends/snapshots/`), and `last_safe_trend_result.json`, plus a `recovery_mode` diagnosis (`normal` / `fallback_safe` / `last_safe_available` / `manual_review_required`).

`modules/topic/topic_engine.py` is an older/duplicate `TopicEngine` not wired into `WorkflowEngine`. The active one is `modules/topic_engine/topic_engine_module.py` (`TopicEngineModule`). Don't confuse the two.

### LLM access

All LLM calls go through `src/llm_client.py::LLMClient` (OpenAI `gpt-4o-mini` by default), which centralizes retry logic and logs every request/response to `storage/llm_logs/llm_log_<timestamp>.json`. Modules (`ContentModule`, `ImagePromptModule`) call `generate_text()` and parse JSON out of the response themselves via a `_safe_json_parse` + `_fallback_*` pattern. If the LLM response isn't valid JSON or is missing expected keys, the module normalizes/pads it with hardcoded fallback content rather than failing. Follow this same parse-then-fallback pattern when adding LLM-backed modules.

Image generation (`modules/image_generation/image_generation_module.py`) calls OpenAI's `gpt-image-1` directly and writes PNGs to `storage/generated_images/`; per-image failures are caught and recorded with `status: "failed"` in the result rather than raising.

### Card News rendering

`CardNewsModule` (`modules/card_news/card_news_module.py`) receives both `content_result` and `image_generation_result`. It uses Pillow to composite text over generated (or solid-color fallback) backgrounds into 1080x1080 PNGs in `storage/card_news/`. It expects Windows fonts (`C:/Windows/Fonts/malgun.ttf` etc.) with a fallback chain down to Pillow's default font; this module is Windows-oriented.

### Module conventions

- `modules/base_module.py::BaseModule` is the common parent: stores `config`, exposes `run()` (must be overridden), and small logging helpers (`log_start`, `log_finish`, `log`). Not all modules inherit it consistently (some older ones, like `TrendCollectorModule` and `ResearchModule`, are plain classes). Check the specific module before assuming `BaseModule` methods are available.
- Module `run()` signatures follow the actual `WorkflowEngine` call sequence: `TrendCollectorModule.run()` starts without prior result input, most middle stages consume the previous stage result, and `CardNewsModule.run()` consumes both content and image-generation results. Each module returns a dict; modules may also independently persist their own result JSON under `storage/` in addition to `WorkflowEngine`'s `storage/workflow_results/` copies.
- Config loading pattern: read `config/settings.json` (or a module-specific file like `config/trend_sources.json`, `config/publishing.json`), with an in-code fallback dict if the file is missing/invalid. Never let a missing config file raise.

### Storage layout

`storage/` is the runtime data directory (JSON results, PNGs, LLM logs, caches, per-run snapshots) and is mostly gitignored except a few tracked sample outputs. Key subpaths: `storage/workflow_results/` (pipeline stage outputs), `storage/trends/` (trend engine state + snapshots), `storage/cache/` (source-level fallback cache), `storage/llm_logs/`, `storage/generated_images/`, `storage/card_news/`.

### Documentation set

The repo root and `docs/` hold many planning documents (`SYSTEM_ARCHITECTURE.md`, `MODULE_SPEC.md`, `WORKFLOW_SPEC.md`, `DIRECTORY_STRUCTURE.md` describe the *target* architecture, which is broader/more aspirational than what's implemented today; e.g. they describe a `Master AI`/`Task Manager` layer that doesn't exist in code). `PROJECT_BIBLE.md`, `ROADMAP.md`, `MODULE_STATUS.md`, `CURRENT_TASK.md`, and `docs/SPRINT_01.md` describe actual current status and near-term priorities and are more reliable for "what's real right now." If `PROJECT_MASTER.md` exists, treat it as an additional reference; it is not required in the current repository state. `DECISIONS.md` is an append-only decision log; never delete entries from it. `benchmark/*.md` are content-strategy reference notes (hooks, CTAs, patterns) used to inform prompt copywriting, not code.

## Working in this repo

- Do not restructure `WorkflowEngine`, rename existing modules/classes/folders, or introduce a new project layout. Extend the existing flow with small additions instead (per `AGENTS.md`/`CODEX_RULES.md`).
- Keep the fallback-first contract intact for any code touching network/LLM/image calls: fallback events must be recorded in the result JSON (see `collection_summary`, `fallback_used`, `trend_engine_status` fields), not thrown as exceptions that kill the workflow.
- Prefer one larger, related batch of changes ("Sprint") over many tiny commits, per the documented workflow philosophy (`docs/` -> design -> architecture review -> code -> test -> commit -> changelog).
- `.env` holds `OPENAI_API_KEY` and is gitignored. Never commit it or print its contents.
