# Engine Status (Implemented vs. Planning)

Corrected 2026-07-10 (Sprint 14-0 doc audit): this section was previously titled "Planning
Additions" even though almost everything in it was already implemented. **AI Planner is the
only Engine still in Planning.** Everything else below is implemented and verified against
`src/workflow_engine.py`.

## Implemented

- Knowledge Engine: v1 implemented (Sprint 11); real active consumption (not just passive reference) in Pattern/Content/CardNews/Audit/Learning (Sprint 13)
- Competitor Engine: v2 implemented (Sprint 13, offline-first) — Instagram placeholder removed, replaced with real `INSTAGRAM_BENCHMARK.md`/`TOOLS_AND_FUNNEL_REFERENCES.md` parsing
- Audit Engine: v2 implemented (Sprint 13) — 9 real checks incl. Pattern/Image Strategy match, save/comment inducement (Competitor Comparison/Blind Spot Detection extensions listed under Planning below)
- Learning Engine: v2 implemented (Sprint 13) — `internal_learning_score` (audit+performance+knowledge, all real local data, no fabricated performance)
- Analytics Engine: v2 implemented (Sprint 13) — fabricated SNS metrics removed, replaced with honest local `quality_trend` (real Instagram Graph API connection listed under Planning below)
- Brand DNA Engine: v1 implemented (Sprint 12)
- Trend Memory: v1 implemented (Sprint 12), consumed by Audit Engine (Sprint 13)
- Performance Score: v1 implemented (Sprint 12, shared by Audit/Learning/Analytics)

## Planning

- **AI Planner** — AI task routing, cost control, Sprint ROI review (`docs/AI_PLANNER.md`). The
  only Engine from the original Planning Additions list not yet implemented.
- Audit Engine's Competitor Comparison + Blind Spot Detection stages (extension of the
  already-implemented Audit Engine, pending Competitor Engine history accumulation across
  multiple runs — not a separate Engine).
- Real Instagram Graph API connection for Analytics Engine (see `ROADMAP.md` "Requires External API").
- Real-time Instagram competitor account scanning for Competitor Engine (see `ROADMAP.md` "Requires External API").

# Operational Support

The following are documentation-only / no-code systems. They are real and in active use — not
"planning" in the sense of not-yet-built — but they contain no `modules/` code of their own.

- Codex Skill System: Operational Support
- `ai-content-os-sprint` skill
- `ai-content-os-commit-check` skill
- `ai-content-os-research` skill
- `ai-content-os-retry-audit` skill
- `ai-content-os-doc-update` skill
- Claude Developer Kit v1: Operational Support (`.claude/skills/`, documentation only, no code)
  - Claude Skill System skills: `architecture`, `large_implementation`, `refactoring`, `research`, `planning`, `review`
- CTO Operating System entry-point skill: Operational Support (`.claude/skills/cto_operating_system/SKILL.md`, read before any other Claude skill) — points to the project-root `PROJECT_OPERATING_SYSTEM.md` and its Mandatory Reading Order
- Claude Domain Skill (Developer Kit v2): Operational Support (`.claude/skills/domain/`, documentation only, no code)
  - Engine skills: `cardnews`, `trend_engine`, `topic_engine`, `pattern_engine`, `content_engine`, `image_engine`, `publishing_engine`
  - Cross-cutting skills: `debug`, `performance`, `testing`
- AI Developer Kit Foundation v1: Operational Support (`.ai/`, shared AI-agnostic infrastructure, documentation only, no code)
  - `architecture/system_architecture.md`, `workflows/development_workflow.md`, `workflows/sprint_workflow.md`
  - `rules/project_rules.md`, `rules/ai_roles.md`, `rules/workflow_protection.md`
  - `prompts/README.md`, `templates/task_template.md`, `templates/sprint_template.md`
  - `knowledge/knowledge_system.md`, `decision/decision_engine.md`

# AI-Content-OS Module Status

## Completed

- WorkflowEngine operational
- `workflow_completed` maintained
- Project snapshot/changelog auto-update
- TrendCollector
- TopicEngine
- PatternEngineModule connected to WorkflowEngine
- Research
- Content
- ImagePrompt
- ImageGeneration
- CardNews
- Publishing
- Publishing v2
- Trend Source Manager v1
- Naver News collector fallback/cache
- Nate Pann collector fallback/cache
- FMKorea collector fallback/cache
- Bobaedream collector fallback/cache
- Trend Quality Scoring v1
- Selection Reason v1
- Top Topic Picker
- Duplicate Removal v1
- `selected_topic.json`
- `trend_result.json` includes `selected_topic`
- Research Module selected_topic linkage
- Research Module pattern_result linkage
- Research Intelligence v1 context/insight generation
- Content Module pattern-aware prompt linkage
- Content Intelligence v1
- Hook Engine v1 metadata reflected in Content prompts and Content Score
- CTA Engine v1 metadata reflected in Content prompts and Content Score
- CardNews Layout Intelligence v1
- CardNews layout-aware PNG rendering v1
- CardNews Quality QA v1
- CardNews Design Quality v1
- CardNews Layout Quality Scoring v2
- Source Health v1
- Collector Statistics v1
- Retry Policy v1
- Cache TTL v1
- Source Health retry/cache TTL fields
- Collector Statistics fallback counts
- `trend_result.json` includes `trend_engine_status`
- Trend Run Log v1
- Trend Result Snapshot v1
- Trend Recovery Summary v1
- Last Safe Trend Result v1
- Trend Engine Guard v1

## Sprint 2 Completed

- Topic Intelligence helpers added in `modules/topic_engine/`:
  - `KeywordWeightEngine`
  - `TopicClassifier`
  - `TopicCluster`
  - `ConfidenceScorer`
- Pattern Engine added in `modules/pattern_engine/`:
  - `PatternEngineModule`
  - `PatternSelector`
  - `HookSelector`
  - `CTASelector`
  - `LayoutSelector`
  - `PatternResultWriter`
- `PatternEngineModule` is connected after `TopicEngineModule` and before `ResearchModule`.
- Pattern outputs are saved under `storage/pattern/`:
  - `pattern_result.json`
  - `pattern_history.json`
  - `pattern_statistics.json`
- `ResearchModule` reads `pattern_result.json` additively.
- Research results include:
  - `pattern_result_available`
  - `topic_intelligence`
  - `pattern_plan`
- Pattern Engine failure is handled as a fallback event, not a workflow failure.

## Operational Complete

- Sprint 1 Trend Engine operational complete
- Collection failures are handled through fallback/cache/retry/status/log/snapshot flow
- `workflow_completed` maintained
- `selected_topic.json` and Research selected_topic linkage maintained
- `trend_run_log.jsonl`, `trend_engine_status.json`, and `last_safe_trend_result.json` maintained
- Sprint 2 Pattern Engine workflow linkage verified with `py -m src.main`
- Sprint 3 Pattern -> Research -> Content linkage verified with `py -m src.main`
- Sprint 4 Content Intelligence v1 verified with `py -m src.main`
- Sprint 5 snapshot generator and runtime storage tracking cleanup verified with `py -m src.main`
- Sprint 6 CardNews Layout Intelligence v1 verified with `py -m src.main`
- Sprint 7 CardNews layout-aware PNG rendering verified with `py -m src.main`
- Sprint 8 CardNews Quality QA v1 verified with `py -m src.main`
- Sprint 9 CardNews Design Quality v1 verified with `py -m src.main`

## Sprint 3 Completed

- Content Engine reads Research output containing:
  - `pattern_result_available`
  - `topic_intelligence`
  - `pattern_plan`
- Content Engine builds pattern-aware prompts through:
  - `ContentPromptBuilder`
  - `PatternPromptRouter`
  - `HookStrategy`
  - `CTAStrategy`
  - `SlideStrategy`
- Pattern prompt guide files are available under `prompts/patterns/`.
- `config/brand_profile.json` is used by the Content prompt builder, with in-code fallback if loading fails.
- Content LLM failure is recorded as fallback copy generation, not workflow failure.
- ImagePrompt LLM failure is recorded as fallback prompt generation, not workflow failure.
- ImageGeneration API failure is recorded as failed image items and `fallback_used`, not workflow failure.

## Sprint 4 Completed

- ContentModule adds `content_intelligence` to content results.
- Content Intelligence fields:
  - `quality_score`
  - `duplicate_risk`
  - `brand_rule_passed`
  - `publishing_hint`
  - `recommendations`
  - `details`
- Content Intelligence helper modules:
  - `ContentQualityScorer`
  - `ContentDuplicateDetector`
  - `PublishingHintGenerator`
  - `BrandRuleEvaluator`
- `storage/content/content_history.json` is generated for duplicate-risk checks.
- Content Intelligence calculation failures return safe defaults and do not break `workflow_completed`.

## Sprint 5 Completed

- `scripts/update_project_snapshot.py` includes `PatternEngineModule` in the generated Current WorkflowEngine line.
- Generated `PROJECT_SNAPSHOT.md` collapses noisy runtime-output directories instead of enumerating every generated file.
- `.gitignore` excludes runtime storage outputs including workflow results, logs, generated images, card images, and snapshots.
- Runtime storage outputs were removed from Git tracking with `git rm --cached` while keeping local files on disk.
- Tracked storage placeholders are limited to required stable files such as `storage/README.md` and `.gitkeep` files.

## Sprint 6 Completed

- CardNewsModule now adds `layout_result` to card news results.
- Layout Intelligence helper modules:
  - `LayoutSelector`
  - `LayoutRuleEngine`
  - `SlideDesigner`
  - `HighlightEngine`
- Layout rule template:
  - `templates/card_news_layout_rules.json`
- `layout_result` includes layout type, slide count, highlight keywords, title/body style, image ratio, CTA position, selection reason, slide designs, slide highlights, and fallback status.
- Layout Intelligence failures return a safe default layout with `fallback_used: true` and do not break `workflow_completed`.
- Existing card PNG generation and PublishingModule handoff remain operational.

## Sprint 7 Completed

- CardNewsModule applies `layout_result` metadata to actual PNG rendering.
- CardNews results now include `rendering_result` fields:
  - `layout_applied`
  - `layout_type`
  - `highlight_applied`
  - `cta_area_applied`
  - `fallback_used`
  - `rendering_notes`
- `rendering_result.layout_type` is linked to `layout_result.layout_type`.
- Layout-aware rendering failures fall back to the original CardNews rendering path.
- Partial rendering fallback is recorded with `rendering_result.fallback_used: true`.
- Latest run generated 4 layout-aware card news PNG files and maintained PublishingModule handoff.

## Sprint 8 Completed

- CardNewsModule now adds `card_news_quality` to card news results.
- CardNews Quality QA helper:
  - `CardNewsQualityChecker`
- QA output fields:
  - `qa_score`
  - `passed`
  - `checks`
  - `warnings`
  - `recommendations`
- Runtime QA output is saved to `storage/card_news/card_news_quality.json`.
- QA scoring checks PNG existence/count/size/resolution plus `layout_result` and `rendering_result` status.
- `layout_result.fallback_used=True` or `rendering_result.fallback_used=True` applies a QA score penalty.
- QA failures return safe default QA fields and do not break `card_news_completed` or `workflow_completed`.

## Sprint 9 Completed

- CardNewsModule now optimizes slide text before PNG rendering.
- CardNews Design Quality helper:
  - `CardNewsTextOptimizer`
- CardNews results now include `design_quality_result` fields:
  - `text_optimized`
  - `headline_trimmed_count`
  - `body_trimmed_count`
  - `duplicate_removed_count`
  - `cta_optimized`
  - `readability_warnings`
  - `fallback_used`
- CardNews QA checks include `design_quality_exists`.
- Latest run produced `design_quality_result.text_optimized: true`, `headline_trimmed_count: 1`, `body_trimmed_count: 1`, and `fallback_used: false`.
- Tethering workflow run completed in 138.54 seconds without timeout exit 124.
- Naver News, Nate Pann, LLM Content, LLM ImagePrompt, and Image API fallback/status handling remained active and did not break `workflow_completed`.

## Verification

- Compile command: `py -m compileall src modules scripts`
- Compile result: success
- Workflow command: `py -m src.main`
- Workflow result: `workflow_completed`
- Latest Network Stability Patch run completed in 357.66 seconds.
- Latest LLM service diagnostics record `retry_count: 3` before fallback.
- Latest Image service diagnostic records `retry_count: 3` before fallback.
- Latest Naver News collection summary records `retry_count: 3` before settings fallback.
- Latest Nate Pann collection summary records `retry_count: 3` before settings fallback.
- Latest Trend collection summary includes `fmkorea` and `bobaedream` source health records.
- Required pattern files generated:
  - `storage/pattern/pattern_result.json`
  - `storage/pattern/pattern_history.json`
  - `storage/pattern/pattern_statistics.json`
- Latest Research result includes `pattern_result_available: true`
- Latest Research result includes `research_context` and `research_insight`
- Latest Research insight fallback remains a status field and does not break `workflow_completed`
- Latest Content result includes `prompt_source: pattern_aware`
- Latest Content result records LLM fallback with `fallback_used: true` when API calls fail
- Latest Content result includes all required `content_intelligence` fields
- Latest Content result includes `hook_score`, `cta_score`, and `pattern_fallback_used` quality checks
- Latest Content quality score is `0.66`
- Latest run generated `storage/content/content_history.json`
- Latest generated `PROJECT_SNAPSHOT.md` includes `PatternEngineModule` and runtime tree omission markers
- Latest CardNews result includes all required `layout_result` fields
- Latest CardNews result includes all required `rendering_result` fields
- Latest `layout_result.layout_type` matches `rendering_result.layout_type`
- Latest CardNews result includes all required `card_news_quality` fields
- Latest CardNews result includes all required `design_quality_result` fields
- Latest CardNews result includes additive `layout_score`, `highlight_score`, `readability_score`, and `layout_quality_score`
- Latest CardNews QA checks include `design_quality_exists: true`
- Latest QA score is `0.85` and passed the `0.6` threshold
- Latest run generated `storage/card_news/card_news_quality.json`
- Latest run generated 4 card news PNG files

## Sprint 10 Completed (Image Intelligence v1)

- New `modules/image_strategy/` engine added:
  - `ContentTypeClassifier` — classifies content into `news`/`community`/`shopping`/`review`/`promotion`/`tutorial`/`ai_tools`/`education` using research source/category/pattern signals and keyword rules.
  - `ImageSourceSelector` — maps each content type to a real-image-first priority chain (e.g. `news -> news_image`, `community -> post_capture -> comment_capture`, `shopping -> product_image`, `review -> real_photo`, `education/tutorial -> icon -> diagram -> ai_image`, `ai_tools -> official_screenshot -> ai_image`).
  - `AIImageDecision` — decides `need_ai_image` based on whether the priority chain ends in `ai_image`.
  - `ImageStrategyModule` — orchestrates the above, always returns a safe result (`need_ai_image: true`) on internal failure, and writes `storage/image_strategy/image_strategy_result.json`.
- `ImageStrategyModule` is connected in `WorkflowEngine` after `ContentModule` and before `ImagePromptModule`; its result is also passed into `ImagePromptModule.run()`.
- `ImagePromptModule.run()` now accepts an optional `image_strategy_result` argument; when `need_ai_image` is `False`, it skips the LLM prompt call entirely and returns `status: "image_prompts_skipped"` with an `ai_image_skipped: true` flag and an `image_strategy` summary (including `image_usage_plan`).
- `ImageGenerationModule.run()` checks `ai_image_skipped` and, when set, skips the OpenAI image API entirely and returns `status: "image_generation_skipped"` with `images: []` — no AI image credits/API calls are spent for content types that should use real images.
- `CardNewsModule`'s existing solid-color background fallback (unchanged) renders card news normally even when no images were generated, so `workflow_completed` is unaffected.
- Image Strategy failures (classification/selection/decision exceptions) are caught internally and always fall back to `need_ai_image: true` (existing AI generation path), never to `workflow_failed`.
- `scripts/update_project_snapshot.py` updated to include `image_strategy` in the workflow module list and `ImageStrategyModule` in the `PROJECT_SNAPSHOT.md` pipeline line.
- Verified with `py -m compileall src modules scripts` (success) and `py -m src.main` (`workflow_completed`); latest run classified the selected topic as `content_type: "community"` (source `nate_pann`) with `need_ai_image: false`, and both `ImagePromptModule`/`ImageGenerationModule` skipped AI generation while `CardNewsModule` still produced 4 PNGs via solid-color fallback backgrounds.

## Sprint 11 Completed (Knowledge Intelligence v1)

- New `modules/knowledge_engine/` engine added, built as a full Engine (Core/Storage/History/Index/Score/Cache/Retry-safe/Fallback/Interface), not a single module:
  - `KnowledgeExtractor` — pulls reusable Knowledge candidates out of each pipeline stage's result dict across 10 extraction targets: `hook`, `cta` (from `ContentModule` slides + `pattern_plan`), `pattern` (Pattern Engine `pattern_plan`/`topic_intelligence`), `layout` (CardNews `layout_result`), `brand` (Content `content_intelligence.details.brand_rule`), `workflow` (aggregate `fallback_used` signature across all pipeline stages for the run), `prompt_pattern` (Content `prompt_source`/`pattern_prompt_meta`), `tool` and `image_strategy` (Image Strategy `image_source`/`content_type`/`image_usage_plan`), and `funnel` (Research keyword/target + Publishing platform/status). Each extraction step is individually try/except-wrapped so one failing step never blocks the others.
  - `KnowledgeClassifier` — tags each item with `category`/`cluster`/`tags` from Pattern Engine `topic_intelligence`.
  - `KnowledgeDuplicateDetector` (`duplicate_detector.py`) — `SequenceMatcher`-based title similarity against same-type existing records in `knowledge.json`, same low/medium/high thresholds as `ContentDuplicateDetector`.
  - `KnowledgeScorer` (`knowledge_score.py`) — computes `reusability` (per-type weight), `importance` (fallback-aware), `confidence` (from `topic_intelligence.confidence_score` / Content `quality_score`), `duplicate_risk_score`, and a combined `roi`, plus an `overall_score` used for ranking.
  - `KnowledgeRanker` — sorts items by `overall_score` and assigns `rank`.
  - `KnowledgeStorage` — upserts by `knowledge_id` into `storage/knowledge/knowledge.json` and maintains `storage/knowledge/knowledge_statistics.json` (run counts, fallback-run counts, per-type totals).
  - `KnowledgeHistory` — append-only run log at `storage/knowledge/knowledge_history.json` (same pattern as `pattern_history.json`/`content_history.json`, capped at 500 records).
  - `KnowledgeIndex` — type/tag inverted index at `storage/knowledge/knowledge_index.json`, rebuilt from the full `knowledge.json` every run so a corrupted index never loses data.
  - `KnowledgeInterface` — read-only query API (`get_top_hooks`, `get_top_ctas`, `get_pattern_knowledge`, `get_layout_knowledge`, `get_brand_knowledge`, `get_image_strategy_knowledge`, `get_tool_knowledge`, `get_funnel_knowledge`, `get_workflow_knowledge`, `get_by_keyword`, `get_statistics`) intended for future use by Pattern Engine/Research/Content/Image Strategy/CardNews. **Not wired into those engines yet** — API only, per this Chapter's scope; every method fails safe to `[]`/`{}`.
  - `KnowledgeModule` — orchestrates extract -> classify -> duplicate-check -> score -> rank -> persist, and always returns a safe `knowledge_extracted` result (with `fallback_used: true` and an empty-but-existing Knowledge DB) even on internal exceptions.
- `KnowledgeModule` is connected in `WorkflowEngine` after `PublishingModule` and before final-result assembly; `WorkflowEngine._run_knowledge_engine()` adds an extra outer try/except as a second safety net so a Knowledge Engine exception can never turn into `workflow_failed`. `final_result` now additively includes a `"knowledge"` key.
- `scripts/update_project_snapshot.py` updated to include `knowledge`/`Knowledge extraction` in the workflow module list and labels, and `KnowledgeModule` appended to the `PROJECT_SNAPSHOT.md` pipeline line.
- Verified with `py -m compileall src modules scripts` (success) and `py -m src.main` (`workflow_completed`). Latest run extracted 10 Knowledge items (one of each type) from the `톡커들의 선택 명예의 전당` topic run, wrote all four `storage/knowledge/*.json` files, and top-ranked `hook`/`cta` items scored `overall_score: 0.9125`.

## Sprint 12 Completed (Multi-Engine Growth Sprint)

Seven new Engines added in one Sprint, each built to the full Engine standard (Core/Storage/History/Score/Fallback/Interface; Retry/Cache noted as "not applicable" where the Engine makes no network/LLM calls). `WorkflowEngine` now runs 17 stages total, all additive — no existing module, folder, class, or call signature was renamed or removed.

- **Knowledge Interface real connection**: `PatternEngineModule`, `ResearchModule`, `ContentModule`, `ImageStrategyModule`, and `CardNewsModule` now each import `KnowledgeInterface` and attach a `knowledge_reference` field to their own result dict (top pattern/layout, funnel/workflow, hook/cta/prompt_pattern, image_strategy/tool, and layout knowledge respectively). This is deliberately additive-only — none of the five engines' existing selection/scoring logic was changed, so behavior and fallback paths are unaffected. Confirmed in the latest run: `pattern_result.knowledge_reference.top_patterns`/`top_layouts` populated from the persisted Knowledge DB.
- **`modules/performance_score/`** — `PerformanceScoreModule` composes (does not recompute) `hook_score`/`cta_score` from Content's existing `pattern_prompt_meta`, `layout_score` from CardNews `layout_result.layout_quality_score`/`card_news_quality.qa_score`, `brand_score` from `content_intelligence.brand_rule_passed`, and a heuristic `image_score` from Image Strategy fallback/need_ai_image, into one `overall_performance_score`. Storage: `storage/performance_score/performance_score.json` + `_statistics.json` + `_history.json`. Consumed by Audit/Learning/Analytics Engines.
- **`modules/audit_engine/`** — `AuditEngineModule` runs the docs/AUDIT_ENGINE.md "My Account Analysis" + "Score Calculation" + "Recommended Actions" stages: `hook_check`/`cta_check`/`layout_check`/`brand_check`/`image_check`/`duplicate_check` (duplicate reusing Content's existing `duplicate_risk`), weighted into `audit_score`, with `strengths`/`weaknesses`/`recommendations`. Competitor Comparison/Blind Spot Detection remain for a future Sprint once Competitor Engine data accumulates. Storage: `storage/audit/`.
- **`modules/learning_engine/`** — `LearningEngineModule` treats `(Performance Score + Audit Score) >= 0.65` as a proxy "good run" signal (no real Analytics data exists yet) and promotes that run's high-scoring (`overall_score >= 0.7`) hook/cta/pattern/layout/brand Knowledge items into `storage/learning/learning_memory.json`. Repeated promotion of the same `knowledge_id` across good runs increases its `memory_score` (reinforcement). Storage: `storage/learning/`.
- **`modules/analytics_engine/`** (Skeleton) — `AnalyticsEngineModule` defines the full views/saves/comments/shares/CTR/follow_conversion/DM schema but has no real Instagram Graph API connection yet; `AnalyticsPredictor` fills it with a Performance/Audit-Score-derived estimate and every result carries `is_measured: false`. Structure is designed so a future real-data collector can replace the predictor without changing the schema. Storage: `storage/analytics/`.
- **`modules/brand_dna_engine/`** — `BrandDNAEngineModule` loads `config/brand_profile.json` (tone/banned words/target) and additionally observes each run's actual `hook_type`/`cta_type`/`layout_type` (plus `highlight_color` looked up from `templates/card_news_layout_rules.json`) to build up `dominant_hook_type`/`dominant_cta_type`/`dominant_layout_type`/`dominant_color` frequency stats — i.e. what the brand actually repeats, not just its written profile. Storage: `storage/brand_dna/` (`brand_dna.json` + `brand_dna_statistics.json` + `brand_dna_history.json`).
- **`modules/trend_memory/`** — `TrendMemoryModule` records each run's `(topic_title, hook_type, cta_type, layout_type, image_source)` combination and compares it against the last 10 runs for `topic_repeat_risk` (title similarity) and per-element repeat counts. It only records/flags — it does not block generation, per the "no WorkflowEngine structure change" rule. Storage: `storage/trend_memory/`.
- **`modules/competitor_engine/`** (docs/COMPETITOR_ENGINE.md) — `CompetitorEngineModule` builds a competitor profile from 4 sources: `BenchmarkSource` parses the already-CTO-analyzed `benchmark/*.md` docs (`HOOK_LIBRARY.md`, `CTA_LIBRARY.md`, `CONTENT_PATTERNS.md`, `INSTAGRAM_BENCHMARK.md`, `TOOLS_AND_FUNNEL_REFERENCES.md`, `AI_CONTENT_STRATEGY.md`) into structured `hook_and_cta_map`/`repeated_content_patterns` sections (no raw external re-analysis — reads existing project docs per `research.md`); `CommunitySource`/`NewsSource` reuse Trend Collector's already-collected `storage/trends/trend_result.json` (`nate_pann`/`fmkorea`/`bobaedream`/`naver_news`) rather than scraping anything new; `InstagramSource` is an explicit placeholder (`fallback_used: true`) since no live Instagram collection exists yet. Output includes a `gap_analysis_input` for the Audit Engine to consume in a future Sprint. Storage: `storage/competitor/`.
- **Knowledge DB upgraded** (`modules/knowledge_engine/`): `KnowledgeStorage` gained an in-run instance cache (`load_all()` no longer re-reads disk on repeated calls within a run) and a `replace_all()` used for **global re-ranking** — `KnowledgeModule` now re-ranks the *entire* cumulative `knowledge.json`, not just the current run's batch, so every record's `rank` always reflects its standing across the whole DB. Added `update_score_statistics()` (average `overall_score` per type in `knowledge_statistics.json`) and `KnowledgeInterface.search(query, limit)` (substring search across title/content, sorted by `overall_score`).
- `scripts/update_project_snapshot.py` updated: workflow module list/labels/pipeline line now include all 7 new stages (`performance_score`, `audit`, `learning`, `analytics`, `brand_dna`, `trend_memory`, `competitor`).
- `WorkflowEngine` gained a shared `_run_safe()` wrapper (used by all 7 new stages) as a second safety net on top of each Engine's own internal fallback, mirroring the existing `_run_pattern_engine`/`_run_knowledge_engine` pattern — any one Engine failing outright still cannot turn into `workflow_failed`.
- Verified with `py -m compileall src modules scripts` (success, twice — second pass after fixing an initially-unused `brand_dna_statistics.json` path) and `py -m src.main` (`workflow_completed`, twice). Latest run: `overall_performance_score: 0.8636`, `audit_score: 0.737` (passed, weaknesses: `layout_check`/`duplicate_check` — expected, since the run reused a previously-seen topic/layout), Learning Engine promoted 2 items (`is_good_run: true`), Competitor Engine read all 6 benchmark files and extracted 10 hook sections / 7 CTA sections, and `storage/knowledge/knowledge.json` global rank/statistics updated.

## Sprint 13 Completed (Offline-First 실전 고도화)

Goal: with no API/login/token, make every Sprint 12 structure actually do something real with local data. No new placeholders, no new skeletons.

- **Placeholder/Skeleton removal**:
  - Deleted `modules/competitor_engine/instagram_source.py` (the `instagram_not_implemented` placeholder) entirely rather than documenting around it.
  - Rewrote `AnalyticsEngineModule`/`AnalyticsPredictor`/`AnalyticsStorage`/`AnalyticsHistory` to remove the fabricated `predicted_metrics` (views/saves/comments/shares/ctr/follow_conversion/dm_count, all `is_measured: false`) — this was inventing SNS performance data that doesn't exist. Replaced with a real `quality_trend` (`improving`/`declining`/`stable`/`insufficient_history`) computed by comparing this run's actual Performance Score against the actual historical average already stored in `storage/performance_score/performance_score_statistics.json` (via the existing `PerformanceScoreInterface` — no new fabricated data, no external API).
  - Fixed a real bug found during the placeholder audit: `benchmark_source.py`'s generic `### N. Title` parser silently produced 0 sections for `INSTAGRAM_BENCHMARK.md` (`### account_handle`, no number) and `TOOLS_AND_FUNNEL_REFERENCES.md` (`## N. Title`, H2 not H3) — both files were listed as "read" but contributed nothing. Replaced with two dedicated parsers (`InstagramBenchmarkParser`, `ToolsFunnelParser`) matching each file's actual heading structure.
  - API-dependent items (real Instagram/Meta metrics, live competitor account scanning, real image auto-sourcing, Reels transcript/translation) moved to `ROADMAP.md`'s new "Requires External API" section instead of being stubbed in code.
- **Knowledge DB real consumption** (previously passive `knowledge_reference` attach-only fields, Sprint 12):
  - `PatternEngineModule`: reads `KnowledgeInterface.get_pattern_knowledge`/`get_layout_knowledge`; when the selected `pattern_type` matches a same-category top-ranked Knowledge item, boosts `topic_intelligence.confidence_score` by +0.05 (observed in practice: `0.72 -> 0.77`). Adds `knowledge_used`/`knowledge_items`/`knowledge_influence` to `pattern_result.json`.
  - `ContentModule`: reads top hooks/CTAs and injects them into the LLM `user_prompt` as explicitly-labeled "reference, do not copy verbatim" examples (real influence on generation, not just metadata). Adds the same 3 fields to `content_result.json`.
  - `CardNewsModule`: when the rendered `layout_type` matches a top-ranked Knowledge layout, boosts `layout_result.layout_quality_score` by +0.03 (observed: `0.6833 -> 0.7133`, which also raised the downstream `card_news_quality.qa_score`). Adds the same 3 fields.
  - `AuditEngineModule`: `duplicate_check` now blends `content_intelligence.duplicate_risk`, `trend_memory_result.topic_repeat_risk`, and the current run's `knowledge_result.top_knowledge` items' `duplicate_risk` into one worst-case verdict.
  - `LearningEngineModule`: `knowledge_score` = average `overall_score` of this run's `top_knowledge` items, one of three real inputs to `internal_learning_score`.
  - All five engines now log `knowledge_used`/`knowledge_items`/`knowledge_influence` in their result JSON as required.
- **Competitor Engine v2** (offline-first, no Instagram API):
  - New `InstagramBenchmarkParser` parses `benchmark/INSTAGRAM_BENCHMARK.md`'s 14 `### account_handle` sections (Category/Observed Pattern/Common Hooks/AI-Content-OS 적용/Priority) into per-account `hook`/`pattern`/`layout`/`cta`/`image_strategy`/`priority` profiles (layout/cta/image_strategy derived via keyword matching against the already-analyzed text — no fabrication, empty where the source doc has nothing).
  - New `ToolsFunnelParser` parses `benchmark/TOOLS_AND_FUNNEL_REFERENCES.md`'s 6 numbered sections.
  - New `CompetitorProfileBuilder` normalizes parser output into the requested schema.
  - New `storage/competitor/competitor_profiles.json` (14 account profiles in the latest run) alongside the existing `competitor_profile.json` (run-level source summary). `format_comparison` is now real (layout/cta/image_strategy distribution counts across parsed profiles), not a `not_available` placeholder.
- **Content Audit Engine real strengthening**: expanded from 6 to 9 checks — added `pattern_check` (Content's actual `pattern_type` vs Pattern Engine's plan), `image_strategy_check` (rewritten to check whether Image Strategy's plan was actually fulfilled, via the new `image_sourcing_status`, not just a fallback flag), `save_inducement_check` and `comment_inducement_check` (keyword/cta_type detection on the actual CTA slide text). All 9 checks now take a single `context` dict so `AuditChecks.run_all()` can read `pattern_result`/`knowledge_result`/`trend_memory_result` alongside the original inputs. `recommendations` remain mandatory in every result.
- **Learning Engine real strengthening**: `internal_learning_score` (renamed from `run_quality_score`) = `audit_score * 0.4 + performance_score * 0.35 + knowledge_score * 0.25` — three real local numbers, explicitly no fabricated engagement data.
- **Trend Memory real connection**: already recording/checking topic+hook+cta+layout+image_source combinations since Sprint 12; Sprint 13 moved its pipeline position earlier (stage 11, before Performance Score/Audit) specifically so Audit Engine's `duplicate_check` can consume `trend_memory_result.topic_repeat_risk`. Still warning-only — never blocks generation.
- **Image Strategy → CardNews/Publishing wiring**: `CardNewsModule.run()` gained an optional `image_strategy_result` param (`WorkflowEngine` now passes it); it compares the plan (`need_ai_image`/`image_source`) against what was actually rendered (`cards[].source_image`) and writes `image_sourcing_status` (`manual_image_required`, `recommended_source`, `checklist`) into `card_news_result.json`. `PublishingModule` reads that status from `card_news_result` (no new required param) and surfaces `manual_image_required`/`image_checklist` in `publish_queue.json` and `publishing_result.json` — the checklist goes into ops metadata, not the public-facing caption text.
- `WorkflowEngine` pipeline reordered among the Sprint-12 bonus stages only (core 10-stage protected pipeline untouched): `... -> PublishingModule -> KnowledgeModule -> TrendMemoryModule -> PerformanceScoreModule -> AuditEngineModule -> LearningEngineModule -> AnalyticsEngineModule -> BrandDNAEngineModule -> CompetitorEngineModule`. `storage/workflow_results/` numbering updated (`11_trend_memory_result.json` through `17_competitor_result.json`).
- Verified with `py -m compileall -f src modules scripts` (success, forced full recompile) and `py -m src.main` (`workflow_completed`). Latest run: Pattern Engine `confidence_score` boosted `0.72 -> 0.77` from Knowledge match; CardNews `layout_quality_score` boosted `0.6833 -> 0.7133`; `audit_score: 0.7552` (9 checks, `image_strategy_check` correctly failed with `manual_image_required: true`); `internal_learning_score: 0.7762` (`audit=0.7552*0.4 + performance=0.8587*0.35 + knowledge=0.6945*0.25`); Analytics `quality_trend: "stable"` (real 3-run historical average, no fabricated metrics); `competitor_profiles.json` has 14 real account profiles; `publish_queue.json` correctly carries `manual_image_required: true` with a 2-item checklist.

## Sprint 14-0 Completed (Documentation Alignment Audit)

Goal: make `PROJECT_MASTER.md`, `PROJECT_SNAPSHOT.md`, `MODULE_STATUS.md`, `ROADMAP.md`,
`CURRENT_TASK.md`, and `CTO_BRAIN.md` match the actual repository state, judged by the code
(no code changes made this Sprint; `py -m compileall`/`py -m src.main` intentionally not run).

- **Found and fixed a real doc/code conflict**: `PROJECT_SNAPSHOT.md`'s "Current WorkflowEngine"
  line had `TrendMemoryModule` positioned after `BrandDNAEngineModule` (the pre-Sprint-13 order).
  The actual `src/workflow_engine.py` runs `TrendMemoryModule` immediately after `KnowledgeModule`
  (moved there in Sprint 13 specifically so Audit Engine's `duplicate_check` could consume its
  output). Traced the root cause to `scripts/update_project_snapshot.py`'s hardcoded
  `module_lines` string (line ~184-191), which was never updated for the Sprint 13 reorder —
  this is a **code bug**, out of scope to fix this Sprint (docs-only), tracked below.
  `PROJECT_SNAPSHOT.md` was hand-corrected to the true order for now; it will revert to the
  wrong order on the next `py -m src.main` run until the script itself is fixed.
- **`PROJECT_MASTER.md` was the most stale of the six**: its "Current Core" list predated even
  Sprint 10 (no Image Strategy) and "Planning Additions" still listed Knowledge Engine,
  Competitor Engine, and Audit Engine as not-yet-built — all three (plus Learning/Analytics/
  Brand DNA/Trend Memory/Performance Score) have been implemented since Sprint 11-13. Rewrote
  "Current Core" to list the protected pipeline + Intelligence Layer, and reduced "Planning
  Additions" to AI Planner only.
- **`MODULE_STATUS.md`'s top section was self-contradictory**: titled "Planning Additions" but
  8 of 9 listed items were already implemented, and "Operational Support" entries were labeled
  "Planning/Operational Support" despite already existing. Split into "Engine Status
  (Implemented vs. Planning)" with explicit Implemented/Planning subsections, and dropped the
  misleading "Planning/" prefix from Operational Support entries (they are real, existing,
  documentation-only systems — not unbuilt).
- **`CURRENT_TASK.md` described a project that no longer exists**: "Sprint 01 - Foundation",
  unchecked boxes for `PROJECT_BIBLE.md`/`SYSTEM_ARCHITECTURE.md`/`WORKFLOW.md`/`MASTER_JSON.md`
  (all four exist in the repo today), and a "Legacy Migration" checklist superseded by the
  `research.md` skill workflow established in `DECISIONS.md` (2026-07-09). Rewritten to reflect
  Sprint 13 completion and the actual `MODULE_STATUS.md`/`ROADMAP.md` "Next" items.
- **`CTO_BRAIN.md` did not exist**, despite being referenced as a Mandatory Reading Order item
  in `PROJECT_OPERATING_SYSTEM.md`, `CLAUDE.md`, and every recent Sprint's "반드시 먼저 읽기"
  list. Created it as the CTO's own current-state operating summary (architecture snapshot,
  Engine inventory, standing risks/watch items) so that reading order item is no longer a
  dangling reference.
- `ROADMAP.md` was already accurate (Engine statuses and "Requires External API" section both
  correctly reflect Sprint 13's real state) — no content changes needed there beyond
  confirming consistency with the corrected documents above.
- **AI Planner status confirmed**: it is the only Engine marked Planning across all six
  documents after this audit (previously `PROJECT_MASTER.md` also listed Knowledge/Competitor/
  Audit Engine as Planning — now corrected).

## Sprint 14-1 Completed (Snapshot Generator Workflow Order Repair)

Fixes the code bug tracked in Sprint 14-0's Next list above.

- Verified `src/workflow_engine.py`'s actual `run()` call order directly (not assumed from
  memory): `... -> PublishingModule -> KnowledgeModule -> TrendMemoryModule ->
  PerformanceScoreModule -> AuditEngineModule -> LearningEngineModule ->
  AnalyticsEngineModule -> BrandDNAEngineModule -> CompetitorEngineModule`.
- Fixed `scripts/update_project_snapshot.py`'s two hardcoded lists that were both still in the
  pre-Sprint-13 order (`TrendMemoryModule` after `brand_dna`/`BrandDNAEngineModule` instead of
  right after `knowledge`/`KnowledgeModule`):
  - `get_workflow_summary()`'s `modules` list (drives the "Recent Completed Features" bullets).
  - `build_snapshot()`'s `module_lines` string (drives the "Current WorkflowEngine" line).
- No new Engine added, AI Planner not implemented, no unrelated refactoring — this Sprint only
  reordered existing list entries to match the verified real execution order.
- Verified with `py -m compileall src modules scripts` (success) and `py -m src.main`
  (`workflow_completed`). `PROJECT_SNAPSHOT.md` was regenerated by the real script run (not
  hand-edited) and its "Current WorkflowEngine" line now reads: `TrendCollectorModule ->
  TopicEngineModule -> PatternEngineModule -> ResearchModule -> ContentModule ->
  ImageStrategyModule -> ImagePromptModule -> ImageGenerationModule -> CardNewsModule ->
  PublishingModule -> KnowledgeModule -> TrendMemoryModule -> PerformanceScoreModule ->
  AuditEngineModule -> LearningEngineModule -> AnalyticsEngineModule -> BrandDNAEngineModule ->
  CompetitorEngineModule` — matching the actual code exactly. `CHANGELOG.md` auto-updated via
  the same run.

## Sprint 14-2 Completed (Content Output Contract & Quality Hardening)

M2 Content Engine enhancement: `ContentModule` now enforces an explicit Output Contract so any
LLM result (well-formed, partially broken, or completely invalid) always produces the same
stable `content_result.json` schema.

- New `modules/content/content_output_validator.py` (`ContentOutputValidator`) — diagnoses
  (never fixes) issues in a parsed content dict: `slides_not_list`, `slide_count_mismatch:N`,
  `page_missing_or_invalid`/`page_duplicate`, `role_unrecognized`/`hook_not_first`/
  `cta_not_last`/`role_order_mismatch`, `headline_missing`/`headline_too_long`/
  `headline_too_short`, `body_missing`/`body_too_long`/`body_too_short`,
  `title_invalid`/`caption_invalid`/`hashtags_invalid`.
- New `modules/content/content_output_normalizer.py` (`ContentOutputNormalizer`) — always
  rebuilds a clean 4-slide result regardless of input quality. Matches slides to the canonical
  `hook -> problem -> solution -> cta` order by **role first** (so a scrambled or partial LLM
  response like "cta first, hook last, only 3 slides" still lands each real slide in its
  correct position instead of losing content to positional indexing), falls back to unmatched
  slides by original order, and only uses hardcoded fallback content for slots with nothing
  usable. Enforces headline (2-40 chars) / body (4-160 chars) bounds with trimming, and
  caption/hashtags type + minimum-count guarantees.
  - New, more accurate `fallback_used` semantics: `true` only when **zero** slides had any
    real LLM content (`fallback_reason: "no_usable_llm_slide_content"`); partially-broken
    input that gets successfully repaired is `fallback_used: false`, since real generated
    content was preserved — this is a real behavior change from Sprint 1-13's `_normalize_slides`,
    which only checked for a `slides` key's presence/absence and could silently mis-tag
    hook/cta if the LLM's role labels were wrong or out of order.
- `ContentModule._run_output_contract()` replaces the old `_safe_json_parse`/`_normalize_slides`
  pair with the exact pipeline requested: `Content LLM Result -> Content Output Validation ->
  Content Output Normalization -> Content Quality Recheck -> Stable content_result.json`. The
  Quality Recheck step re-runs `ContentOutputValidator` on the *normalized* result as a
  defense-in-depth guarantee that the contract was actually satisfied (logs a warning if not,
  but never raises). `content_result` gains three additive fields: `output_validation`
  (pre-normalization diagnosis), `output_recheck` (post-normalization re-verification),
  `output_normalization` (`normalization_applied` + human-readable `notes` of what was fixed).
  Top-level schema (title/slides/caption/hashtags/status) is unchanged, so `CardNewsModule`/
  `PublishingModule`/downstream Intelligence Layer Engines require no changes.
- `.claude/skills/domain/content_engine.md` updated: removed references to the deleted
  `_safe_json_parse`/`_normalize_slides` methods, added a "Content Output Contract" section
  documenting the new pipeline so future Sprints don't have to re-derive it.
- Verified with `py -m compileall -f src modules scripts` (success) and `py -m src.main`
  (`workflow_completed`) — this run's real LLM output was already well-formed
  (`output_validation.valid: true`, `normalization_applied: false`), confirming the contract
  doesn't interfere with good output. Since a clean run doesn't exercise the repair path, also
  ran a standalone verification script (`content_output_validator`/`content_output_normalizer`
  imported directly, no workflow side effects) against 4 deliberately malformed inputs: totally
  invalid input, `slides` as a non-list, scrambled roles with `cta` first/`hook` last/only 3
  slides/one missing headline, and an oversized headline. All 4 cases produced a recheck-valid
  result; the scrambled-role case correctly preserved the real hook/cta text in the right slots
  and set `fallback_used: false` (3 of 4 slides had real content); the oversized-headline case
  trimmed to exactly 40 characters.

### Sprint 14-2 Correction (real `tests/` suite added)

The verification above was a throwaway script, not a committed, discoverable test suite — a
follow-up check found `tests/` didn't exist at all, so `py -m unittest discover -s tests -p
"test_content_output_*.py"` ran 0 tests. Fixed properly:

- New `tests/test_content_output_validator.py` (17 tests) and
  `tests/test_content_output_normalizer.py` (13 tests) — 30 tests total, pure `unittest`,
  `TestCase` subclasses, `test_`-prefixed methods, no external API/LLM/network calls (the
  normalizer tests use a local `fallback_slides()` stand-in matching `ContentModule._fallback_slides()`'s
  signature).
- Writing real tests surfaced two genuine gaps in the Sprint 14-2 implementation itself (fixed,
  not worked around):
  - `ContentOutputValidator` only checked for **duplicate** page numbers, not **out-of-order**
    ones (e.g. pages `[4,3,2,1]` with no duplicates went undetected). Added a `page_out_of_order`
    check (`page != index + 1`), and excluded `bool` from passing the `isinstance(page, int)`
    check (`True`/`False` are technically `int` subclasses in Python).
  - `ContentOutputNormalizer` treated `hashtags` given as a string as simply invalid and
    discarded it entirely (falling through to fallback hashtags) instead of actually
    normalizing it into a list. Added string-to-list splitting (`re.split(r"[,\s]+", ...)`) so
    e.g. `"#AI #콘텐츠 #자동화"` or `"#AI,#콘텐츠,#자동화"` become `["#AI", "#콘텐츠", "#자동화"]`.
- Re-verified end to end: `py -m unittest discover -s tests -p "test_content_output_*.py" -v`
  → 30 tests, all `ok`. `py -m compileall -f src modules scripts tests` → success, both test
  files now appear in the compile output. `py -m src.main` → `workflow_completed`, 4 CardNews
  PNGs generated, `publishing_result.status: "publishing_ready"`, Naver News/Nate Pann fallback
  events still occurred as normal (fallback-first contract intact).

### Sprint 14-2 Independent Review (Codex MCP) — one more real bug found and fixed

Per instruction, this round was reviewed independently via Codex MCP (`mcp__codex__codex`)
rather than Claude self-approving. Codex read the repo fresh, ran the verification commands
itself, and returned verdict **BLOCKED** with two findings — both real, both fixed:

1. **Tracked `.pyc` files**: `modules/content/__pycache__/content_module.cpython-313.pyc` (and,
   on inspection, 4 other stale tracked `.pyc` files elsewhere in the repo — `modules/base_module`,
   `modules/research/research_module`, `src/main`, `src/workflow_engine`) were committed even
   though `.gitignore` already excludes `__pycache__/`/`*.pyc` — they were tracked before that
   rule existed and never cleaned up. Fixed with `git rm --cached` on all 5 (files remain on
   disk; only removed from git tracking).
2. **Real `fallback_used` logic bug** in `ContentOutputNormalizer._normalize()`: a slide counted
   toward `real_content_used_count` as soon as *any* non-empty candidate text was found for its
   role, **before** `_clean_text()` checked whether that text actually met the minimum length. A
   slide with a too-short-but-non-empty headline/body (e.g. `"a"`/`"ok"`) could get counted as
   "real content used" even though both fields were then fully replaced by fallback text inside
   `_clean_text()` — meaning `fallback_used` could come back `false` when zero real LLM content
   actually survived, contradicting the documented contract. Fixed by having `_clean_text()`
   return `(text, is_real)` and only counting a slide as real when at least one of
   headline/body actually survived the length check (not merely "a candidate existed").
   Added 2 regression tests: `test_all_slides_too_short_counts_as_no_real_content` (all 4 slides
   too short -> `fallback_used: true`) and `test_partial_real_content_when_only_body_survives_length_check`
   (one slide's body survives -> `fallback_used: false`) — test suite is now 33 tests, all `ok`.
   Codex's other 9 review items (validator correctness, ContentModule wiring, test strength,
   full workflow, CardNews/Publishing compatibility, unrelated-changes check, runtime storage
   tracking) all passed on first review with no changes needed.

## Next

- Real image sourcing automation (news thumbnail fetch, community post/comment capture, product lookup) — requires crawling external SNS/news pages, moved to ROADMAP.md "Requires External API"
- Add focused unit checks for ContentPromptBuilder, Content Intelligence helpers, CardNews Layout Intelligence/rendering/QA/design quality helpers, and fallback fields
- Keep snapshot generator in sync with WorkflowEngine if future modules are added
- Wire Audit Engine's Competitor Comparison + Blind Spot Detection stages once Competitor Engine's `competitor_profiles.json` history accumulates across multiple runs
- Real Instagram Graph API connection for Analytics Engine — see ROADMAP.md "Requires External API"; until then `quality_trend` remains based on real local Performance Score history only
- AI Planner (routing/cost-control layer) remains the one planned Engine not yet implemented
- Source Health dashboard
- Collector Statistics dashboard
- Improve final safe-result recovery behavior

## Notes

- Always run the project with `py -m src.main`.
- Do not use `python -m src.main`.
- Internet, LLM, image, Pattern Engine, Content prompt, Content Intelligence, CardNews Layout Intelligence/rendering/QA/design quality, Knowledge Engine, Performance Score, Audit Engine, Learning Engine, Analytics Engine, Brand DNA Engine, Trend Memory, and Competitor Engine failures must be recorded as fallback events, not workflow failures.
- OpenAI, Naver News, and Nate Pann transient connection failures should retry with backoff before fallback.
- Keep Naver News and Nate Pann fallback/cache behavior intact.
- Knowledge Engine failure must still guarantee an existing (even empty) `storage/knowledge/knowledge.json` — never leave the DB file missing. The same guarantee now applies to `storage/performance_score/`, `storage/audit/`, `storage/learning/`, `storage/analytics/`, `storage/brand_dna/`, `storage/trend_memory/`, and `storage/competitor/`.
- None of the Sprint 12/13 bonus Engines call external network/LLM APIs, so none implement literal retry logic — their Fallback strategy (safe default result, never raise) is the reliability contract instead, consistent with `image_strategy`/`pattern_engine`.
- Per Sprint 13's explicit "Offline-First" constraint: do not implement Instagram API, Meta Graph API, access-token-based auth, or real SNS login/crawling without explicit future approval — check ROADMAP.md's "Requires External API" section first.
