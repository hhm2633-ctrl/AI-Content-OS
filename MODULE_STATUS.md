# Engine Status (Implemented vs. Planning)

Corrected 2026-07-10 (Sprint 14-0 doc audit): this section was previously titled "Planning
Additions" even though almost everything in it was already implemented. AI Planner was the
last Engine still in Planning; **Sprint 15-3 completed its `WorkflowEngine` wiring and Consumer
Layer integration**, so it has moved to Implemented below. Everything in this section is
implemented and verified against `src/workflow_engine.py`.

## Implemented

- Knowledge Engine: v1 implemented (Sprint 11); real active consumption (not just passive reference) in Pattern/Content/CardNews/Audit/Learning (Sprint 13)
- Competitor Engine: v2 implemented (Sprint 13, offline-first) — Instagram placeholder removed, replaced with real `INSTAGRAM_BENCHMARK.md`/`TOOLS_AND_FUNNEL_REFERENCES.md` parsing
- Audit Engine: v2 implemented (Sprint 13) — 9 real checks incl. Pattern/Image Strategy match, save/comment inducement (Competitor Comparison/Blind Spot Detection extensions listed under Planning below)
- Learning Engine: v2 implemented (Sprint 13) — `internal_learning_score` (audit+performance+knowledge, all real local data, no fabricated performance)
- Analytics Engine: v2 implemented (Sprint 13) — fabricated SNS metrics removed, replaced with honest local `quality_trend` (real Instagram Graph API connection listed under Planning below)
- Brand DNA Engine: v1 implemented (Sprint 12)
- Trend Memory: v1 implemented (Sprint 12), consumed by Audit Engine (Sprint 13)
- Performance Score: v1 implemented (Sprint 12, shared by Audit/Learning/Analytics)
- **AI Planner**: Contract (Sprint 15-0/15-0A), Decision Engine v1 (Sprint 15-1), Consumer Layer
  (Sprint 15-2), and actual `WorkflowEngine` wiring + Consumer Layer integration into
  Pattern/Content/Image Strategy/Knowledge (Sprint 15-3) are all complete — see the Sprint 15-3
  entry below for the full integration. AI Planner runs as a **Hint Layer** between
  `TopicEngineModule` and `PatternEngineModule`; every downstream Engine independently decides
  (via `PlannerConsumerAdapter`) whether to use its hints, and none of their own selection logic
  or fallback behavior was removed.
- **Competitor Learning Engine**: implemented (Sprint 18) — `modules/competitor_learning/`
  converts `modules/instagram_research/`'s already-collected posts (read-only, no crawler) into
  a ranked Knowledge Database (`storage/knowledge/knowledge_database.json` + 5 statistics files).
  Standalone/on-demand, not wired into `WorkflowEngine.run()`.
- **Instagram Intelligence Phase (Internal Quality Feedback Loop)**: implemented (2026-07-11) —
  see the "Instagram Intelligence Phase" entry below for the full Content -> Performance History
  -> Learning -> Knowledge -> Brand DNA -> Pattern -> Content loop. Explicitly a **pre-publish
  internal `quality_score` proxy**, not real Instagram performance — see `DECISIONS.md`
  (2026-07-11) and `ROADMAP.md` "Requires External API" for the real post-publish version.
- **CardNews Intelligence (Phase M7) + Production Quality (Phase M8)**: implemented (2026-07-11)
  — Evidence Selection with topic-relevance + copyright render guards, Social Proof safe
  selection (masking/PII scrub/opinion labeling), Story Flow planning, Debate/CTA conflict guard,
  Typography hierarchy, Human Visual Rhythm, Mobile Readability + Contrast guard, Source
  Attribution, and 10 new Production Quality QA checks — all layered onto the existing
  `CardNewsModule` Pillow renderer. See the "Phase M7 + Phase M8" entry below for full detail.
  Social Proof stays honestly `available: false` (no real comment collector exists yet); Instagram
  competitor screenshots remain `render_allowed: false` by design (analysis-only).

## Planning

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

## Sprint 15-0 Completed (AI Planner Architecture — Contract Only)

Design-first Sprint per explicit instruction: define the AI Planner **Contract** (input/output/
schema/`WorkflowEngine` connection point) before any decision logic. No new Decision Engine, no
placeholders that fabricate plausible-looking decisions, no actual `WorkflowEngine` wiring.

- New `modules/ai_planner/` package (contract-only, deliberately narrower than the full Engine
  Standard — no `*_storage.py`/`*_history.py`/`*_score.py`, per this Sprint's explicit file list):
  - `planner_contract.py` (`PlannerContract`) — single source of truth: `COORDINATED_ENGINES`
    (pattern_engine, knowledge_engine, competitor_engine, image_strategy, content_engine,
    brand_dna_engine, trend_memory), `INPUT_FIELDS`, `OUTPUT_FIELDS`,
    `WORKFLOW_INTEGRATION_NOTE`, and `NOT_IN_SCOPE_THIS_SPRINT`, all exposed via a `describe()`
    classmethod for Codex/future Sprints to introspect.
  - `planning_context.py` (`PlanningContext`) — the 8-field Input Contract: `trend_result`,
    `topic_result`, `pattern_result`, `knowledge_result`, `trend_memory_result`,
    `competitor_result`, `brand_profile`, `image_strategy_result`. Plain class with
    `to_dict()`/`from_dict()`, matching every input to an already-real WorkflowEngine stage
    output — no new collection/generation logic.
  - `planning_result_schema.py` — the Output Contract: `REQUIRED_FIELDS` (10 fields:
    `selected_pattern`, `selected_hook_strategy`, `selected_cta_strategy`,
    `selected_image_strategy`, `knowledge_priority`, `competitor_reference`,
    `content_strategy`, `planner_confidence`, `planner_reason`, `planner_version`),
    `build_undecided_result(reason)` (all decision fields explicitly `None`/`[]`/`0.0` — an
    honest "not decided" state, not a fabricated-looking value, per the Sprint 13 Offline-First
    honesty standard), and `validate_schema(result)` (presence-only check, no exceptions).
  - `planner_interface.py` (`PlannerInterface`) — read-only `get_latest_result()` (reads
    `storage/planner/planner_result.json` if present; returns `{}` for now since nothing writes
    there yet — no `*_storage.py` exists this Sprint) and `get_contract()`.
  - `planner_module.py` (`AIPlannerModule`, Skeleton) — accepts an optional `PlanningContext`,
    returns `build_undecided_result()` plus a `schema_valid` flag from `validate_schema()`. Never
    reads the context's actual field values for decision-making (verified: passing a fully
    populated `PlanningContext` still returns `selected_pattern: None` etc. — confirmed by a
    standalone verification script, not committed, since this Sprint adds no test requirement).
    Writes nothing to disk.
  - `storage/planner/.gitkeep` — directory reserved for a future Storage class; `.gitignore`
    updated to allow-list `storage/planner/`/`storage/planner/.gitkeep` (the existing
    `storage/**` blanket-ignore rule required an explicit exception, matching the pattern
    already used for `storage/cache/`, `storage/history/`, etc.).
- `src/workflow_engine.py`: **comment-only** connection points added, no import/instantiation/
  execution — one in `__init__` (where `self.ai_planner_module` would be created) and one in
  `run()` (between `TopicEngineModule` and `PatternEngineModule`, matching
  `PlannerContract.WORKFLOW_INTEGRATION_NOTE`'s stated rationale: Planner decisions need to
  exist before Pattern/Content/Image Strategy run in order to influence them).
- Verified with `py -m compileall -f src modules scripts tests` (success, `modules/ai_planner/`
  files appear in the output) and `py -m src.main` (`workflow_completed` — unaffected, since
  nothing was actually wired in).
- **Independent Codex MCP review** (Architecture Review, Interface Review, Schema Review,
  Repository Consistency) — see verdict and any findings recorded by Codex at commit time
  (this entry is written before that round completes; if Codex requested changes, they are
  folded into this same Sprint 15-0 entry rather than a separate correction section).

## Sprint 15-0A Completed (AI Planner Contract Dependency Repair)

Structural bug-fix to the Sprint 15-0 Contract, not a Sprint 15-1 implementation. Sprint 15-0
placed `AIPlannerModule` between `TopicEngineModule` and `PatternEngineModule`, but its
`PlanningContext` required `pattern_result`, `knowledge_result`, `trend_memory_result`,
`competitor_result`, and `image_strategy_result` — all produced by stages that run **after**
that position. This was unimplementable without passing empty dicts, filling future-stage
results with placeholders, or reordering the Workflow — all three explicitly forbidden.

- **Fix**: AI Planner v1 re-scoped as a **Pre-Planning Engine**. Position unchanged
  (`TrendCollectorModule -> TopicEngineModule -> AIPlannerModule -> PatternEngineModule`); only
  the Input Contract changed.
  - **Runtime Inputs** (directly receivable at this position in the current run):
    `trend_result`, `topic_result`, `brand_profile`.
  - **Historical Inputs** (read from local storage, accumulated past-run data, not current-run
    results): `knowledge_history`, `trend_memory_history`, `competitor_history`,
    `brand_dna_history`, `performance_history`. Verified before naming that the backing storage
    genuinely exists: `storage/knowledge/knowledge_history.json`,
    `storage/trend_memory/trend_memory_history.json`,
    `storage/performance_score/performance_score_history.json`,
    `storage/brand_dna/brand_dna_history.json`, `storage/competitor/competitor_history.json`.
  - Removed from Planner Input entirely: `pattern_result`, `knowledge_result`,
    `trend_memory_result`, `competitor_result`, `image_strategy_result` (now listed in
    `PlannerContract.FORBIDDEN_FUTURE_STAGE_INPUT_FIELDS` as an explicit regression guard).
- `planner_contract.py`: added `RUNTIME_INPUT_FIELDS`, `HISTORICAL_INPUT_FIELDS`,
  `FORBIDDEN_FUTURE_STAGE_INPUT_FIELDS`; `INPUT_FIELDS` is now their concatenation;
  `VERSION` bumped to `"0.2.0-contract-only"`.
  `planning_context.py`: `PlanningContext` constructor rewritten to the 3 Runtime + 5 Historical
  fields; `to_dict()`/`from_dict()` updated to match; `from_dict()` still never raises on
  invalid input (coerces to `{}`).
  `planning_result_schema.py`: `REQUIRED_FIELDS` (10 fields) unchanged; added
  `TARGET_ENGINE_BY_FIELD` mapping each selectable output field to its downstream Engine
  (`selected_pattern` -> Pattern Engine, `selected_hook_strategy`/`selected_cta_strategy`/
  `content_strategy` -> Content Engine, `selected_image_strategy` -> Image Strategy Engine,
  `knowledge_priority` -> Knowledge Engine, `competitor_reference` -> Competitor Engine);
  `PLANNER_VERSION` bumped to match. `build_undecided_result()`/`validate_schema()` logic
  unchanged (still honest/undecided, no exceptions).
  `planner_module.py`: docstring updated only; `_build_undecided_result()` logic unchanged
  (still never fabricates a decision, verified even when Historical Input is fully populated
  with real past data).
  `planner_interface.py`: rewritten to add `load_historical_inputs()`, which instantiates and
  reuses the existing `KnowledgeInterface`, `TrendMemoryInterface`, `CompetitorInterface`,
  `BrandDNAInterface`, `PerformanceScoreInterface` — no new storage structure invented, no
  circular import (verified: these Engine Interfaces do not import `modules.ai_planner`).
- `src/workflow_engine.py`: **not modified**. The Sprint 15-0 comment-only connection points
  already described the correct position (`TopicEngineModule -> AIPlannerModule ->
  PatternEngineModule`) — only the input contract was wrong, not the workflow position.
- **Tests** (new, `tests/test_ai_planner_*.py`, 30 tests total, all local/no network/no LLM):
  `test_ai_planner_contract.py` (9 — Runtime/Historical field correctness, `INPUT_FIELDS` vs.
  `PlanningContext` field match, all 5 forbidden future-stage fields absent, Output vs. schema
  match, `WorkflowEngine` has no real `AIPlannerModule` import/instantiation/`run()` call while
  its explanatory comment remains, `describe()` completeness), `test_ai_planner_context.py`
  (6 — default-empty construction, Runtime/Historical field acceptance, to_dict/from_dict
  round-trip, `from_dict` never raises on 6 garbage inputs, forbidden/unknown keys ignored),
  `test_ai_planner_schema.py` (7 — `build_undecided_result` honesty/completeness/never-raises,
  `validate_schema` pass/each-missing-field-detected/never-raises, `TARGET_ENGINE_BY_FIELD`
  coverage), `test_ai_planner_module.py` (8 — Skeleton never fabricates a decision regardless
  of empty/Runtime-only/Historical-only/fully-populated context, `run()` never raises, interface
  exposed). Run via `py -m unittest discover -s tests -p "test_ai_planner_*.py" -v` ->
  **Ran 30 tests in 0.010s, OK**.
- Verified with `py -m compileall -f src modules scripts tests` (success) and `py -m src.main`
  (`workflow_completed`, unchanged 17-stage order confirming AI Planner still does not execute,
  4 CardNews PNGs, `publishing_ready`).
- **Independent Codex MCP review** (thread `019f4a7a-6c78-7d73-a017-d5c37d3e4e93`): first pass
  returned **CONDITIONAL PASS** — everything checked out except one ambiguity: `brand_profile`
  was classified as a Runtime Input but is not actually a `WorkflowEngine.run()` stage output
  (unlike `trend_result`/`topic_result`); it is static config (`config/brand_profile.json`) with
  no explicit loader wired into the Planner layer. Fixed by adding
  `PlannerInterface.load_brand_profile()` (reuses the existing
  `modules/brand_dna_engine/brand_profile_loader.py::BrandProfileLoader` — no new storage/loader
  invented), clarifying `planner_contract.py`/`planning_context.py` docstrings that
  `brand_profile` is grouped with Runtime Inputs because it is unconditionally available at the
  Planner's position, not because a prior stage produced it, and adding a regression test
  (`test_interface_load_brand_profile_never_raises_and_returns_dict`, bringing the suite to 31
  tests). Re-verified `py -m compileall -f modules\ai_planner tests\test_ai_planner_module.py`
  and `py -m unittest discover -s tests -p "test_ai_planner_*.py" -v` (31 tests, OK) after the
  fix.

## Sprint 15-1 Completed (AI Planner Decision Engine v1)

Implements the actual Decision Engine that Sprint 15-0/15-0A deliberately deferred. Still not
wired into `WorkflowEngine` (explicit Sprint scope limit).

- New `modules/ai_planner/planner_decision_engine.py` (`PlannerDecisionEngine`) — computes real
  Output Contract values from `PlanningContext` via transparent, deterministic rules only (no
  LLM call, no external API, no random values):
  - `selected_pattern`/`selected_hook_strategy`/`selected_cta_strategy`: reuses the exact same
    classes `PatternEngineModule` uses on the Runtime Input's `selected_topic`/`trends`
    (`KeywordWeightEngine` → `TopicClassifier` → `TopicCluster` → `ConfidenceScorer` →
    `PatternSelector` → `HookSelector`/`CTASelector`) — not a re-invented heuristic, so the
    Planner's hint matches what Pattern Engine will independently compute moments later.
  - hook/cta then get an optional **Brand DNA history override**: if
    `brand_dna_history.total_observations >= 5` and `dominant_hook_type`/`dominant_cta_type` is
    a recognized value (`HookSelector.HOOK_TYPES`/`CTASelector.CTA_TYPES`), the Planner
    recommends the brand's actual proven preference instead of the pattern-consistent default —
    otherwise it keeps the pattern-consistent default. Corrupted/unrecognized dominant values
    are ignored regardless of observation count (defensive).
  - `selected_image_strategy`: a lightweight keyword/source-based `content_type` pre-estimate
    (education/tutorial/ai_tools/news/community/shopping/review/promotion — the same vocabulary
    `ImageStrategyModule.content_type` uses) computed from Runtime Input only, since
    `content_result` doesn't exist yet at the Planner's position; documented as a pre-estimate,
    not a replacement for `ImageStrategyModule`'s own later authoritative classification.
  - `knowledge_priority`: `knowledge_history.average_overall_score_by_type` sorted descending
    (real accumulated Knowledge Engine statistics, non-numeric/malformed entries ignored).
  - `competitor_reference`: `competitor_history.account_profiles` filtered to
    `priority in {"Very High", "High"}`, sorted Very High first, capped to 5 account names.
  - `content_strategy`/`planner_reason`: human-readable strings summarizing the decision and
    which real inputs drove it. `planner_confidence`: the real `ConfidenceScorer` topic
    confidence plus small transparent bonuses when Brand DNA override / knowledge_priority /
    competitor_reference were actually usable — never an arbitrary/fabricated number.
  - Any unexpected exception is caught and safely replaced with
    `planning_result_schema.build_undecided_result()` — the Sprint 15-0 "undecided" schema is
    kept as the exception-safety net, not the normal path anymore.
  - **Codex review correction**: the first Decision Engine draft still returned a concrete
    decision (`number_list`/`saveable_tip`/`save`/etc.) even when `topic_result.selected_topic`
    had no real signal at all (missing, non-dict, or blank title/keyword) — Codex flagged this
    as a plausible-looking value not actually traceable to real input. Fixed by adding
    `_has_real_topic_signal()`: when there is no real title/keyword, `decide()` now returns
    `build_undecided_result(reason="selected_topic_missing_or_invalid")` instead of running the
    Pattern/Hook/CTA selectors on an empty topic.
- `planner_module.py` (`AIPlannerModule`): now delegates to `PlannerDecisionEngine` instead of
  always returning `build_undecided_result()`; `run()` defensively coerces any input
  (`PlanningContext`, `dict`, `None`, or anything else) via a new `_coerce_context()` before
  calling the Decision Engine, then validates the result with `validate_schema()` exactly as
  before.
- `planning_result_schema.py`: `PLANNER_VERSION` bumped `"0.2.0-contract-only"` →
  `"0.3.0-decision-v1"` (also reflected in `PlannerContract.VERSION`); `REQUIRED_FIELDS`/
  `TARGET_ENGINE_BY_FIELD`/`build_undecided_result()`/`validate_schema()` unchanged.
  `planner_contract.py`: `NOT_IN_SCOPE_THIS_SPRINT` no longer lists "Decision Engine 구현" (now
  done) and instead calls out that the Decision Engine must stay LLM/external-API-free;
  `WORKFLOW_INTEGRATION_NOTE` updated to note the Decision Engine exists but `WorkflowEngine`
  wiring is still absent.
- `src/workflow_engine.py`: **not modified** — still only the Sprint 15-0 comment markers, no
  import/instantiation/`run()` call (verified by the existing
  `test_workflow_engine_has_no_real_ai_planner_wiring` regression test, still passing unchanged).
- **Tests** (new, `tests/test_ai_planner_decision_engine.py`, 16 tests; `test_ai_planner_module.py`
  rewritten for the new delegate-and-validate behavior, 8 tests; full `test_ai_planner_*.py` suite
  now 47 tests total, all local/no network/no LLM): realistic-topic decision validity (values
  within the real `PatternSelector`/`HookSelector`/`CTASelector` enums), determinism, honest
  "undecided" behavior for None/empty/blank/non-dict `selected_topic` (no real topic signal),
  malformed-Historical-Input safety (with a real topic still present), Brand DNA override
  applied/not-applied/ignored-when-corrupted, `knowledge_priority` ordering and non-numeric-score
  filtering, `competitor_reference` priority filtering/ordering/capping, no dependency on the
  Sprint 15-0A forbidden future-stage attributes.
  Run via `py -m unittest discover -s tests -p "test_ai_planner_*.py" -v` → **Ran 47 tests, OK**.
- Verified with `py -m compileall -f src modules scripts tests` (success) and `py -m src.main`
  (`workflow_completed`, unchanged 17-stage order confirming AI Planner still does not execute,
  4 CardNews PNGs, `publishing_ready`).
- **Independent Codex MCP review** (thread `019f4aa3-ad93-7ec1-879e-73f5c26b1922`): first pass
  returned **CONDITIONAL PASS** — one real issue found: an empty/missing/blank `selected_topic`
  still produced a concrete-looking decision (`number_list`/`saveable_tip`/`save`/etc.) via the
  reused selectors' own hardcoded defaults, which Codex judged indistinguishable from a
  fabricated value since it wasn't traceable to any real input signal. Fixed by adding
  `_has_real_topic_signal()`: when `selected_topic` has no non-blank `title`/`keyword`, `decide()`
  now returns `build_undecided_result(reason="selected_topic_missing_or_invalid")` before calling
  any selector, and 3 tests were rewritten/added to assert the honest-undecided shape for that
  case (bringing the suite to 47 tests). Re-submitted → **APPROVED**, with only a non-blocking
  documentation note (test-count wording, corrected above) and an optional/non-blocking
  observation that `src/workflow_engine.py`'s existing comments still describe AI Planner as
  having no Decision Engine (left as-is this Sprint — comment-only cosmetic drift, not a
  functional issue, and `src/workflow_engine.py` edits were kept out of scope to minimize risk to
  the Protected Core file).

## Sprint 15-2 Completed (AI Planner Consumer Layer)

Implements how existing Engines may safely *consume* `planner_result` — still without wiring
`AIPlannerModule` into `WorkflowEngine` and without any real Engine calling this layer yet.

**CTO decision encoded**: Planner results are **verified hints, not forced commands**. Existing
Engine selection logic and fallback are never removed. Consumption requires ALL four gates:
(1) `planner_result` valid (`schema_valid=True`, `status="planner_decided"`), (2)
`planner_confidence` at/above threshold, (3) Consumer Engine actually supports the hinted value,
(4) no conflict with the Engine's own existing safety rules. Failing any gate → keep the
Engine's existing value/logic unchanged.

- New `modules/ai_planner/consumer_contract.py` (`PlannerConsumerContract`) — the shared,
  Engine-agnostic gate logic: `is_result_valid()`, `meets_confidence_threshold()` (constant
  `MIN_CONFIDENCE_FOR_HINT_APPLICATION = 0.5`, chosen from Sprint 15-1's observed confidence
  values — ~0.35 for a topic that fell back to the default "트렌드" category vs. ~0.6-0.9 for a
  genuinely classified one), `is_value_supported()`, `should_apply_hint()` (scalar fields:
  `selected_pattern`/`selected_hook_strategy`/`selected_cta_strategy`/`selected_image_strategy`),
  and `should_apply_list_hint()` (list fields: `knowledge_priority`/`competitor_reference` — these
  are priority/reference hints, not exclusive choices, so they have no "safety conflict" concept,
  only validity/confidence/per-item support checks). Never raises; any gate failure or malformed
  input safely resolves to "do not apply".
- New `modules/ai_planner/planner_consumer_adapter.py` (`PlannerConsumerAdapter`) — per-field
  `resolve_*` methods that pick between the Planner's hint and an already-computed Engine default
  (the Adapter never re-runs Pattern/Hook/CTA/Image Strategy selection itself, only chooses
  between two pre-computed candidates):
  - `resolve_pattern(planner_result, engine_pattern_type, topic_confidence_score, blocked)` —
    supported values = `PatternSelector.PATTERN_TYPES`; safety conflict = `blocked` OR
    `topic_confidence_score < PatternSelector.LOW_CONFIDENCE_THRESHOLD` (the real, existing
    Pattern Engine safety rule that forces a safe "resource" pattern under uncertain
    classification — reused here, not reinvented).
  - `resolve_hook(...)`/`resolve_cta(...)` — supported values = `HookSelector.HOOK_TYPES`/
    `CTASelector.CTA_TYPES`; safety conflict = the same `blocked` flag (a blocked category must
    never accept any Planner hint, hook/cta included).
  - `resolve_image_strategy(planner_result, engine_content_type)` — supported values =
    `ImageSourceSelector.SOURCE_PRIORITY` keys (education/tutorial/ai_tools/news/community/
    shopping/review/promotion); no established safety-conflict concept exists for content_type
    classification, so `safety_conflict=False` always (documented as an explicit, reasoned
    choice, not an oversight).
  - `resolve_knowledge_priority(...)`/`resolve_competitor_reference(...)` — list hints filtered
    to real, checkable membership (`KnowledgeExtractor.KNOWLEDGE_TYPES` for the 10 real knowledge
    types; non-blank strings for competitor account identifiers, since accounts aren't a fixed
    enum).
  - Every method wrapped in try/except; any failure returns the Engine's own default value
    unchanged (`hint_applied: False`, `source: "engine_default"`).
- `modules/ai_planner/planner_interface.py`: added `get_consumer_adapter()` — a convenience
  accessor returning a `PlannerConsumerAdapter` instance for a future Sprint's actual Engine
  integration; does not itself decide anything.
- `src/workflow_engine.py` and the real `PatternEngineModule`/`ContentModule`/
  `ImageStrategyModule`/`KnowledgeInterface` consumption code paths: **not modified**. No Engine
  calls this Consumer Layer yet — this Sprint only implements the consumption *rules*, per
  explicit Sprint scope ("이번 Sprint에서는 소비 규칙만 구현한다").
- **Tests** (new, `tests/test_ai_planner_consumer_contract.py`, 24 tests;
  `tests/test_ai_planner_consumer_adapter.py`, 21 tests; full `test_ai_planner_*.py` suite now
  92 tests total, all local/no network/no LLM): all four gates individually and in combination,
  the core invariant that a rejected hint always returns the Engine's original value/logic
  unchanged (never blanked, never altered), per-field supported-value filtering against each
  Engine's real enum, the shared `blocked`-safety-conflict propagating to Pattern/Hook/CTA
  consistently, list-hint item filtering, and never-raises behavior across garbage/malformed
  `planner_result` values (`None`, non-dict, missing fields, non-numeric confidence).
  Run via `py -m unittest discover -s tests -p "test_ai_planner_*.py" -v` → **Ran 92 tests, OK**.
- Verified with `py -m compileall -f src modules scripts tests` (success) and `py -m src.main`
  (`workflow_completed`, unchanged 17-stage order confirming AI Planner still does not execute,
  4 CardNews PNGs, `publishing_ready`).
- **Independent Codex MCP review** (thread `019f4af3-0ec6-7580-b66f-9c7df1b027b1`): first pass
  returned **CONDITIONAL PASS** — the scalar resolvers (`resolve_pattern`/`resolve_hook`/
  `resolve_cta`/`resolve_image_strategy`) correctly preserved the Engine's own default on
  rejection, but `resolve_knowledge_priority`/`resolve_competitor_reference` had no
  Engine-supplied default parameter at all and always collapsed to `[]` on rejection — Codex
  judged this inconsistent with the "existing Engine value never removed" invariant (harmless
  today since nothing calls them yet, but a latent trap for whoever wires them in later). Fixed
  by adding an `engine_default` parameter to both methods; on rejection they now return that
  default (or `[]` if none was supplied) instead of an unconditional `[]`, with 2 new regression
  tests plus a never-raises test (bringing `test_ai_planner_consumer_adapter.py` to 21 tests,
  `test_ai_planner_consumer_contract.py` to 24 tests, suite total 92). Re-submitted — Codex
  confirmed the code fix directly but flagged a leftover stale test-count sentence in this same
  `MODULE_STATUS.md` entry (now corrected above) as the only remaining issue → final verdict
  **APPROVED**.

## Sprint 15-3 Completed (AI Planner Workflow Integration — final AI Planner Sprint)

Wires `AIPlannerModule` into `WorkflowEngine` for real and connects the Consumer Layer
(Sprint 15-2) into the actual Pattern/Content/Image Strategy/Knowledge Engines. **CTO decision
encoded throughout**: Planner output is a **verified hint, never a forced command** — no
existing Engine's selection logic or fallback was removed, and if the Planner is unavailable,
raises, or its hint fails any gate, every downstream Engine behaves exactly as it did before
this Sprint.

- `src/workflow_engine.py`: real `from modules.ai_planner.planner_module import AIPlannerModule`
  import, `self.ai_planner_module = AIPlannerModule(self.config)` in `__init__`, and a new
  `_run_ai_planner(trend_result, topic_result)` method called between
  `self.topic_engine.run()` and `self._run_pattern_engine()` — builds a `PlanningContext` from
  real Runtime Input (`trend_result`/`topic_result`) plus real Historical Input
  (`self.ai_planner_module.interface.load_historical_inputs()`/`load_brand_profile()`, reused
  unchanged from Sprint 15-0A) and calls `self.ai_planner_module.run(context)`. **Returns `None`
  on any exception** — never propagates, matching "Planner Exception → 기존 Workflow 그대로."
  `planner_result` is threaded through to `_run_pattern_engine()`, `ContentModule.run()`,
  `ImageStrategyModule.run()`, and `_run_knowledge_engine()` (all as an added optional trailing
  argument, default `None`), and included in `final_result["planner"]`.
- `modules/pattern_engine/pattern_engine_module.py`: `run()` gained an optional `planner_result`
  parameter. After `PatternSelector.select()` computes its own `pattern_type` as before,
  `PlannerConsumerAdapter.resolve_pattern()` decides whether to swap it for the Planner's hint
  (gated on validity/confidence/support/the *same* `blocked`/`LOW_CONFIDENCE_THRESHOLD` safety
  rule Pattern Engine already enforced) — the merged value then feeds
  `HookSelector`/`CTASelector`/`LayoutSelector` exactly as before, so hook/cta/layout stay
  internally consistent with whichever pattern_type won. Result gains
  `planner_consumption.pattern`. Also added `topic_intelligence.blocked` (previously a local
  variable never exposed to downstream consumers — a purely additive field so Content Engine
  could apply the same safety rule without duplicating `TopicClassifier`'s blocked-category
  logic).
- `modules/content/hook_strategy.py`/`cta_strategy.py`: each `select()` gained an optional
  `hook_type_override`/`cta_type_override` parameter (default `None` = 100% unchanged existing
  behavior). When supplied and a member of the class's own `HOOK_TYPES`/`CTA_TYPES`, it's used
  in place of the pattern-based selection, but `hook_line`/`cta_line` generation and scoring
  still run through the exact same code — an override away from the pattern-ideal type
  naturally scores lower via the *existing* scoring rule, not a new one. `CTAStrategy`'s
  platform-override step was guarded to never re-clobber an applied Planner override.
  `modules/content/content_prompt_builder.py`: `build()` gained an optional `planner_result`
  parameter; computes each Engine's own baseline hook/cta first, then asks
  `PlannerConsumerAdapter.resolve_hook()`/`resolve_cta()` (safety conflict = the new
  `topic_intelligence.blocked`) whether to re-run `select()` with the override. A separate
  `content_strategy` hint (freeform text, no enum) is gated only by
  `PlannerConsumerContract.is_result_valid()`/`meets_confidence_threshold()` (reused directly,
  no new judgment logic) and appended as a labeled reference line in the system prompt — the
  LLM's required JSON schema is untouched. `meta.planner_consumption` records `hook`/`cta`/
  `content_strategy`. `modules/content/content_module.py`: `run()` gained an optional
  `planner_result` parameter, passed through; `content_result["planner_consumption"]["content"]`
  is copied up from the prompt builder's `meta`, or — for the legacy prompt path (no
  `pattern_plan`), where the Consumer Adapter is never even invoked — an honest
  `planner_mode: "unavailable"` record is written instead of fabricating one.
- `modules/image_strategy/image_strategy_module.py`: `run()` gained an optional
  `planner_result` parameter. `ContentTypeClassifier.classify()` still computes its own
  `content_type` as before; `PlannerConsumerAdapter.resolve_image_strategy()` (supported values =
  `ImageSourceSelector.SOURCE_PRIORITY` keys, no safety-conflict concept — documented as a
  reasoned choice, not a gap) decides whether to swap it. Because the merge only changes *which*
  `content_type` bucket is used, and `ImageSourceSelector`/`AIImageDecision`'s real-image-first,
  AI-image-last-resort logic runs unchanged afterward, the Planner has no way to force
  `need_ai_image=True` — it can only nudge which existing priority chain is consulted. Result
  gains `planner_consumption.image_strategy`.
- `modules/knowledge_engine/knowledge_module.py`: `run()` gained an optional `planner_result`
  parameter. New `_apply_planner_priority_boost()` calls
  `PlannerConsumerAdapter.resolve_knowledge_priority()` and, only for **this run's newly
  extracted `scored_items`**, adds a small `+0.05` bonus to `overall_score` for items whose
  `type` is in the accepted priority list — `KnowledgeRanker.rank()` is still the only thing
  that sorts (called completely unmodified, immediately after). The full-DB re-rank step
  (`globally_ranked_records`) is **not** touched, so historical records' real accumulated scores
  are never retroactively altered by an ephemeral per-run hint. Result gains
  `planner_consumption.knowledge`.
- `modules/card_news/card_news_module.py`: `run()` (signature unchanged — `content_result`/
  `image_strategy_result` were already passed in) now also builds
  `result["planner_influence"]` by summarizing the `planner_consumption` sub-dicts already
  recorded by Content/Image Strategy — no new selection, no rendering change.
  `modules/publishing/publishing_module.py`: `run()` (signature unchanged) copies that summary
  into `result["planner_strategy"]` — no change to caption/hashtag/queue generation.
- **Metadata Contract**: every consumption point uses the shared
  `modules/ai_planner/planner_consumer_adapter.py::build_consumption_metadata()` helper (pure
  formatting, no judgment logic) so `planner_consumption.*` has an identical shape everywhere:
  `planner_available`, `planner_applied`, `planner_mode` (`"unavailable"`/`"fallback"`/
  `"preferred"`), `planner_confidence`, `requested_value`, `original_value`, `final_value`,
  `reason`, `fallback_used` (`= not planner_applied` — distinct from other Engines'
  "computation itself failed" `fallback_used` meaning, documented in the helper's docstring to
  avoid confusion).
- **Workflow Protection verified live** (`storage/workflow_results/` from an actual
  `py -m src.main` run): `02b_planner_result.json` shows a real decided result
  (`selected_pattern: "number_list"`, `planner_confidence: 0.87`); `03_pattern_result.json`,
  `05_content_result.json`, `05b_image_strategy_result.json`, `10_knowledge_result.json` all
  show `planner_consumption` with `planner_applied: true` and correct `requested_value`/
  `original_value`/`final_value` (e.g. Content Engine's own CTA baseline `"share"` was
  legitimately overridden to the Planner's `"save"`, proving the mechanism isn't a no-op);
  `08_card_news_result.json.planner_influence.any_hint_applied` and
  `09_publishing_result.json.planner_strategy.any_hint_applied` are both `true`;
  `99_final_result.json.planner.status == "planner_decided"`.
- **Tests**: existing `test_ai_planner_*.py` (92 tests) and `test_content_output_*.py`
  (33 tests) suites re-run unchanged and pass — one *intentional* update:
  `tests/test_ai_planner_contract.py::test_workflow_engine_has_no_real_ai_planner_wiring` (a
  Sprint 15-0A regression guard asserting no wiring existed) was renamed to
  `test_workflow_engine_wires_ai_planner_between_topic_and_pattern` and rewritten to assert the
  opposite — that real import/instantiation/execution now exist, in the correct order — since
  Sprint 15-3's explicit purpose is to add exactly that wiring. New
  `tests/test_workflow_planner_integration.py` (14 tests, all local/offline — a lightweight
  stub is used instead of a full `WorkflowEngine()` instance for `_run_ai_planner`/
  `_run_pattern_engine` tests, since constructing the full engine pulls in `ContentModule`'s
  `LLMClient`, which raises without an API key even before any network call): Planner execution
  position (static source order check), Planner exception/`None` recovery, each of the four
  Consumer Engines applying a hint and recording metadata, `blocked`-category rejection,
  identical `pattern_type` output with vs. without a (low-confidence, rejected) Planner result,
  and never-raises behavior across `None`/malformed `planner_result` for every integration
  point. Full combined run: `py -m unittest discover -s tests -p "test_ai_planner_*.py" -v`
  (92 OK), `-p "test_content_output_*.py" -v` (33 OK), `-p "test_workflow_planner_integration.py"
  -v` (14 OK).
- Verified with `py -m compileall -f src modules scripts tests` (success) and `py -m src.main`
  (`workflow_completed`; **AI Planner actually executes now** — `"AI Planner Module Started
  (Decision Engine v1)"`/`"...Finished..."` appear in the run log, unlike every prior Sprint;
  unchanged 17-Engine order otherwise; 4 CardNews PNGs; `publishing_ready`).
- **Independent Codex MCP review** (thread `019f4b1c-2905-7030-811f-feeebe9fa19b`): first pass
  returned **CONDITIONAL PASS** — one real bug found: `CardNewsModule._build_planner_influence()`
  checked `content_consumption.get("planner_applied")` directly, but unlike
  `image_strategy_result`'s flat `planner_consumption.image_strategy`,
  `content_result["planner_consumption"]["content"]` is nested
  (`{"hook": {...}, "cta": {...}, "content_strategy": {...}}`) — so `any_hint_applied` silently
  evaluated to `False` for Content's contribution regardless of whether a hook/cta/
  content_strategy hint was actually applied (the live verification run's `any_hint_applied:
  true` only happened to be correct because Image Strategy's flat check passed independently,
  masking the bug). Fixed by checking each nested `content_consumption` sub-entry's
  `planner_applied` instead of the (nonexistent) top-level key; `PublishingModule` inherited the
  fix automatically since it only copies CardNews's already-correct summary. Also addressed two
  non-blocking Codex notes: a stale `planner_module.py` docstring still claiming no
  `WorkflowEngine` connection (updated), and added the suggested CardNews/Publishing
  planner-summary tests plus a `PatternEngineModule` blocked-category rejection integration test
  (bringing `test_workflow_planner_integration.py` to 19 tests). Re-verified
  `py -m compileall`, all three required test-discovery commands, and `py -m src.main`
  (`workflow_completed`) after the fix. Re-submitted — Codex confirmed the fix directly resolves
  the bug (not a symptom patch) and found no new issues → final verdict **APPROVED**.

## Sprint 16-0 Completed (Intelligence Feedback Safety)

No new Engine created — this Sprint strengthens the feedback quality, self-reference safety,
and metadata honesty of the existing Intelligence Layer Engines that Sprint 15-3 wired together.

### Feedback Audit (actual code, not the intended design)

Traced the real feedback path `Planner → Pattern/Content/Image Strategy/Knowledge → Brand DNA/
Performance Score/Learning/Analytics → (storage) → Planner`:

- **Real Runtime Sources** (current-run data): `trend_result`/`topic_result` (Planner's own
  Runtime Input), `content_result`/`card_news_result`/`image_strategy_result` (Performance
  Score, Content engine_influence).
- **Real Historical Sources** (accumulated past-run storage): `knowledge_history`,
  `trend_memory_history`, `competitor_history`, `brand_dna_history`, `performance_history` (all
  five already correctly scoped as Historical Input since Sprint 15-0A).
- **Self Reference found (real, not hypothetical) — Brand DNA → Planner**:
  `BrandDNATracker.observe()` reads `pattern_plan.hook_type`/`cta_type` from
  `PatternEngineModule`'s output. Since Sprint 15-3, that `pattern_plan` may itself already
  reflect an AI Planner hint (`PlannerConsumerAdapter.resolve_pattern()`). `BrandDNAStorage`
  accumulates this into `dominant_hook_type`/`dominant_cta_type`, which
  `PlannerDecisionEngine._select_hook_with_history()`/`_select_cta_with_history()` then reads
  back as "real accumulated brand preference" to justify overriding the *next* run's hook/cta —
  meaning the Planner could reinforce its own past recommendation as if it were independent
  evidence, with no natural ceiling.
- **Circular Feedback found (real, introduced by Sprint 15-3, fixed this Sprint) — Knowledge →
  Planner**: `KnowledgeModule`'s original "Priority Boost" mutated the *actual*
  `score.overall_score` of this run's newly-extracted items matching
  `planner_result.knowledge_priority` by `+0.05`, and that mutated value was then permanently
  persisted via `self.storage.upsert(ranked_items)`. `KnowledgeStorage.update_score_statistics()`
  recomputes `average_overall_score_by_type` from `self.storage.load_all()` — which now includes
  the inflated record — so the boosted average would compound across every future run, and the
  next run's `PlannerDecisionEngine._rank_knowledge_priority()` would read that inflated
  historical average as if it were genuine accumulated quality, not partly Planner-caused.
- No other circular path found: `AnalyticsEngineModule`/`LearningEngineModule`/
  `LearningSelector`/`AuditEngineModule` never receive `planner_result` as an input at all (`git
  grep`/signature inspection confirmed) — there was no pre-existing Planner→Analytics→Planner or
  Planner→Learning→Planner loop; the two loops above were the only real ones.

### Self Reference Guard (fixes)

- `modules/knowledge_engine/knowledge_module.py`: removed the score-mutating "Priority Boost"
  entirely. Ranking/persistence now always uses the real, unmodified `KnowledgeRanker.rank()`
  output — `overall_score` is never altered by a Planner hint. Replaced with
  `_build_planner_priority_preview()`, a purely diagnostic, non-mutating method that reads the
  already-real-ranked `ranked_items` and returns (without changing) the subset matching the
  Planner's accepted `knowledge_priority` types, exposed as a new, separate
  `planner_priority_preview` result field. `top_knowledge` (what `LearningSelector`/Audit Engine
  actually consume for `knowledge_score`) is completely unaffected by any Planner hint, closing
  the Knowledge→Planner loop entirely.
- `modules/brand_dna_engine/brand_dna_tracker.py`/`brand_dna_storage.py`/
  `brand_dna_engine_module.py`: `BrandDNATracker.observe()` gained a `planner_influenced: bool`
  parameter; `BrandDNAEngineModule` computes it from
  `pattern_result.planner_consumption.pattern.planner_applied` (already recorded since
  Sprint 15-3) and passes it through. `BrandDNAStorage` now tracks a parallel
  `planner_influenced_observations` counter alongside `total_observations`.
  `modules/ai_planner/planner_decision_engine.py`: the Brand DNA override gate
  (`_select_hook_with_history`/`_select_cta_with_history`) now requires
  `total_observations - planner_influenced_observations >=
  MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE` (a new `_independent_brand_dna_observations()`
  helper) instead of raw `total_observations` — so the Planner can only trust Brand DNA's
  dominant hook/cta once enough *independent* (non-Planner-caused) observations exist. Verified
  live: after Sprint 15-3's hint was applied once, `brand_dna_statistics.json` shows
  `total_observations: 30, planner_influenced_observations: 1` — the counter correctly
  distinguishes the one Planner-influenced run from the 29 pre-Sprint-15-3 independent ones.

### Analytics Verification

`AnalyticsEngineModule`/`analytics_predictor.py` were already Offline-First-compliant (no
fabricated SNS metrics, Sprint 13) but had no explicit per-field source labeling. Added
`measurement_metadata` with one entry per output field, each built via the new shared
`build_standard_metadata()` helper: `current_performance_score`/`current_audit_score` →
`source: "local_quality"` (explicitly labeled as internal quality proxies, not real
measurements — directly addresses "가짜 실측처럼 보이면 안 된다"), `historical_average_
performance_score` → `source: "historical"`, `quality_trend` → `source: "estimated"` (it's an
inference from comparing the other two, not a direct measurement). Present on both the success
path and the exception-fallback path.

### Learning Verification

Confirmed (via `inspect.signature` in a new regression test, not just reading the code) that
`LearningEngineModule.run()`/`LearningSelector.select()` take no `planner_result` parameter and
never did — `internal_learning_score` is always `audit_score*0.4 + performance_score*0.35 +
knowledge_score*0.25`, all three computed fresh from this run's real local values. Added
`evidence_metadata` (per-component `source` labels: `audit_score`/`performance_score` →
`"local_quality"`, `knowledge_score` → `"runtime"`) and an explicit `planner_evidence_used:
False` field (always `False`, on both the success and fallback paths) so the "Learning never
reinforces Planner Decisions unconditionally" guarantee is visible in every result, not just
implied by the absence of a parameter.

### Performance Score

Added `planner_used`/`planner_helpful`/`planner_rejected`/`planner_reason`, computed from the
`planner_consumption` metadata already recorded by Content/Image Strategy (Sprint 15-3) — no new
`WorkflowEngine` wiring needed since `PerformanceScoreModule.run()` already receives
`content_result`/`card_news_result`/`image_strategy_result`. `planner_used`/`planner_rejected`
are independent booleans (both can be `True` in the same run — e.g. hook hint applied, cta hint
rejected — this is real, expected behavior, not a bug). `planner_helpful` is deliberately
conservative: `planner_used AND overall_performance_score >= 0.7` — the `reason` string
explicitly labels this a same-run correlation observation, not a proven causal claim, so it can
never be read as "Planner caused this quality."

### Content Metadata

`ContentModule` gained `engine_influence` (`planner`/`knowledge`/`brand`/`pattern` sub-keys) built
from fields that already existed (`planner_consumption`, `knowledge_used`/`knowledge_items`,
`content_intelligence.brand_rule_passed`, `prompt_source`/`pattern_fallback_used`) — no new
judgment logic. `planner` intentionally references the existing `planner_consumption` structure
directly rather than wrapping it in the new standard again (avoids the "중복 구조" the CTO asked
to eliminate); `knowledge`/`brand`/`pattern` use the new shared `build_standard_metadata()`.

### Metadata Standardization

New `modules/common/metadata_standard.py` (`build_standard_metadata()`, `SOURCE_RUNTIME`/
`SOURCE_HISTORICAL`/`SOURCE_ESTIMATED`/`SOURCE_LOCAL_QUALITY`/`VALID_SOURCES`) — a pure
formatting helper (no new Engine, consistent with the existing `modules/common/
service_diagnostic.py` pattern) reused by every new metadata field added this Sprint
(Analytics/Learning/Content), so future Sprints have one shared shape
(`metadata_version`/`source`/`confidence`/`generated_at`) to extend instead of inventing another
one. Full retrofit of every pre-existing Engine's ad-hoc metadata is not attempted this Sprint
(out of scope/too risky for a safety-hardening Sprint) — noted as a future consideration.

### Tests

New `tests/test_intelligence_feedback_safety.py`, 42 tests, all local/no network/no LLM:
`TestBrandDNASelfReferenceGuard` (7 — tracker flag recording, engine module detection from
`planner_consumption`, the override-gate regression proving `total_observations` alone is no
longer sufficient, independent-observation override still works, missing-field backward
compatibility, negative-clamping), `TestKnowledgeFeedbackLoop` (7 — priority preview never
mutates input scores, only includes matching types, uses real not-boosted scores, empty when no
priority types, never raises on malformed items, resolver never raises, `top_knowledge` stays
separate from `planner_priority_preview`), `TestAnalyticsSourceMetadata` (4),
`TestLearningSourceVerification` (5, including the signature-inspection regression),
`TestPlannerMetadataOnPerformanceScore` (7, including the "both used and rejected can be true"
case), `TestContentEngineInfluenceMetadata` (7), `TestMetadataStandardization` (5, including a
cross-Engine `metadata_version` consistency check). Full suite:
`py -m unittest discover -s tests -v` → **186 tests, OK** (144 pre-existing + 42 new — no
existing test deleted or weakened).
- Verified with `py -m compileall -f src modules scripts tests` (success) and `py -m src.main`
  (`workflow_completed`; Planner executes normally; unchanged 17-stage order; 4 CardNews PNGs;
  `publishing_ready`; spot-checked `storage/brand_dna/brand_dna_statistics.json` showing the new
  `planner_influenced_observations` counter and `storage/workflow_results/10_knowledge_result.json`
  showing `planner_priority_preview` with real, unboosted scores separate from `top_knowledge`).
- **Independent Codex MCP review** (thread `019f4b4c-226e-7a30-a5db-9ced208dbd15`): first pass
  returned **CONDITIONAL PASS** — both Self Reference Guard fixes verified genuine (Brand DNA's
  `planner_influenced` flag traces to a real `planner_consumption.pattern.planner_applied`
  signal and degrades safely on pre-Sprint-16-0 storage; the Knowledge score-mutation path is
  fully removed and `top_knowledge`/the global re-rank/`update_score_statistics()` all operate
  on real, never-boosted data), but found one real gap: `src/workflow_engine.py`'s
  `_empty_performance_score_result()`/`_empty_learning_result()`/`_empty_analytics_result()` —
  the outer `_run_safe()` emergency fallbacks used when a module's own internal
  `run()`/`_fallback_result()` doesn't catch an exception — still returned the pre-Sprint-16-0
  shape, missing `planner_used`/`planner_helpful`/`planner_rejected`/`planner_reason`,
  `evidence_metadata`/`planner_evidence_used`, and `measurement_metadata` respectively. Fixed by
  mirroring the same metadata shapes (via the same `build_standard_metadata()` helper) into all
  three `_empty_*` methods. Also renamed a stale test
  (`test_knowledge_module_applies_priority_boost_without_removing_ranker` →
  `test_knowledge_module_records_planner_priority_consumption_without_removing_ranker`) whose
  name/comment still referenced the removed "Priority Boost" mechanism (non-blocking per Codex,
  fixed anyway for clarity). Re-verified `py -m compileall`, full `py -m unittest discover -s
  tests -v` (186 tests, OK), and `py -m src.main` (`workflow_completed`) after the fix.
  Re-submitted — Codex independently re-probed the `_empty_*` fallback shapes directly and
  confirmed they now match the module-level fallbacks → final verdict **APPROVED**.

## Sprint 18 + Instagram Intelligence Phase (Internal Quality Feedback Loop, 2026-07-11)

Goal: make the already-collected `modules/instagram_research/` data actually improve future
content quality, without a new crawler, without touching `src/workflow_engine.py`, and without
duplicating any existing Engine.

- **Sprint 18 (Competitor Learning Engine)**: new `modules/competitor_learning/` (8 files:
  extractor/statistics/score/storage/interface/dashboard/module/`__init__`). Reads
  `modules/instagram_research/`'s posts read-only via its existing public
  `InstagramResearchInterface`/`classify_post()`/`parse_visible_count_text()` — that module has
  zero diff. Computes hook/cta/pattern/layout/caption/hashtag statistics, scores them into a
  ranked Knowledge Database, and persists `storage/knowledge/knowledge_database.json` +
  `hook_statistics.json`/`cta_statistics.json`/`pattern_statistics.json`/`layout_statistics.json`/
  `competitor_statistics.json`/`competitor_learning_history.json` (additive alongside the
  pre-existing `modules/knowledge_engine/` files in the same directory — different filenames, no
  collision) and `storage/dashboard/daily_learning_report.json`. **Not** wired into
  `WorkflowEngine.run()` — a standalone, on-demand batch step, mirroring
  `scripts/update_project_snapshot.py`'s shape. `layout` deliberately uses Instagram's own post
  format vocabulary (`carousel`/`reel`/`single_image`), never mapped onto
  `LayoutSelector.LAYOUT_TYPES` (`bold_ai`/`notebook`/...) — those are different systems and
  mapping them would fabricate a correspondence that was never observed. 131 new tests. Codex MCP
  independent review: APPROVED (one BLOCK round on a screenshot-path sanitizer bypass / storage
  constructor raising on `OSError` / a comma+unit parsing gap — all fixed, re-reviewed APPROVED).
- **Instagram Intelligence Phase 1**: additive wiring only, no existing selection logic touched.
  `PatternEngineModule` gained `_apply_competitor_learning_consumption()` (Competitor Learning DB
  top pattern/hook/cta match -> `topic_intelligence.confidence_score` +0.03) and
  `_apply_brand_dna_consumption()` (Brand DNA dominant hook/cta match -> +0.02, gated on
  `independent_observations >= 5`, the same Self Reference Guard threshold from Sprint 16-0).
  `ContentPromptBuilder` gained a Competitor Learning hook/cta hint gate
  (`overall_score >= 0.4`, `sample_size >= 3`, never when `blocked`) evaluated **before** the
  pre-existing AI Planner hint, reusing `HookStrategy`/`CTAStrategy`'s existing
  `hook_type_override`/`cta_type_override` parameters. `BrandDNAEngineModule` gained
  `competitor_learning_reference` (read-only) and `brand_dna_change` (before/after dominant_*
  diff, merged into `daily_learning_report.json` by loading, adding one key, and saving — no new
  Dashboard Engine). `ContentQualityScorer`'s 100-point budget was rebalanced
  (`pattern_reflected` 15 -> 10 + a new `pattern_confidence_bonus` up to 5, linear above a 0.6
  confidence threshold) so Pattern Engine's (now-boosted) confidence actually reaches
  `content_result.content_intelligence.quality_score`, not just prompt text.
- **Instagram Intelligence Phase 2 (Closed Loop)**: new `modules/learning_engine/
  content_performance_history.py` (`storage/history/content_performance_history.json`: one
  record per content with `content_id`/`hook`/`cta`/`pattern`/`layout`/`brand_dna_snapshot`/
  `quality_score`/`competitor_reference`/`knowledge_reference` — all values already computed
  elsewhere, none invented) and `learning_performance_analyzer.py` (top/worst/average
  `quality_score` over recent history — pure aggregation, no new selection algorithm).
  `LearningEngineModule` reads `storage/pattern/pattern_result.json` and
  `storage/workflow_results/05_content_result.json` directly (both already fresh by the time
  Learning Engine runs in the pipeline) rather than requiring new `WorkflowEngine.run()`
  parameters. New `CompetitorLearningStorage.adjust_entry_confidence(knowledge_id, delta)`
  nudges one Knowledge Database entry's `score.confidence` (clamped [0.0, 1.0]) and recomputes
  `score.overall_score` with the exact existing `CompetitorLearningScorer` formula — no other
  field on that entry, and no other entry, is touched. Learning Engine applies this ±0.05
  (`LearningScorer.REINFORCEMENT_STEP`, reused not reinvented) based on the existing
  `internal_learning_score >= 0.65` "good run" threshold. `BrandDNAEngineModule` gained
  `learning_feedback_reference` (Learning Engine's `total_runs`/`total_good_runs` ratio, same
  `independent_observations >= 5` guard) and `brand_dna_delta`. `PatternEngineModule` gained a
  4th confidence source, `_apply_learning_consumption()` (+0.025, Learning Memory hook/cta/pattern
  match by exact `knowledge_id`, layout excluded for the same vocabulary-mismatch reason as
  Competitor Learning). `daily_learning_report.json` gained `top_performing_pattern`/
  `weakest_pattern`/`learning_delta`/`knowledge_delta` (merged in by Learning Engine, same
  load-add-key-save pattern, existing keys untouched).
- **Instagram Intelligence Phase 3 (Final Verification)**: two real defects found and fixed
  before this round shipped, neither caught by the "compile only" verification the first two
  Phases were scoped to:
  1. `ContentPerformanceHistory.build_content_id()` originally hashed `title` + the *recording*
     timestamp (`datetime.now()`), which made every call produce a different id even for the
     exact same content — silently defeating deduplication entirely. Fixed to hash `title` +
     `caption` (both real, stable content fields) instead. `ContentPerformanceHistory.
     record_once()` now dedupes by `content_id` (returns `False`, does not re-append, when the id
     already exists; rejects empty ids rather than mis-deduping on them), and
     `LearningEngineModule._apply_knowledge_feedback()` skips the ±0.05 confidence adjustment
     entirely when `performance_history_entry["deduplicated"]` is `True` — reprocessing the same
     content can no longer apply Knowledge Feedback twice.
  2. Semantic-accuracy gap: `quality_score`/`learning_delta`/`top_performing_pattern` are an
     **internal, pre-publish content-quality proxy**, not real Instagram engagement data, but
     nothing in the result structure said so explicitly. Added
     `LearningEngineModule.INTERNAL_QUALITY_PROXY_METADATA`
     (`performance_source: "internal_quality_proxy"` / `external_metrics_used: false` /
     `external_metrics_available: false` / `learning_scope: "pre_publish_internal_feedback"`) to
     the top-level `learning_completed` result, `performance_history_entry` (including the
     `_fallback_result()` path — the one gap Codex's final review round caught), `performance_
     analysis`, and a new `internal_quality_feedback_metadata` block merged into
     `daily_learning_report.json`. See `DECISIONS.md` (2026-07-11).
  - Added 22 targeted regression tests (`tests/test_instagram_intelligence_risk_checks.py`)
    covering exactly these two fixes plus confidence-bounds/independent-observation-gate/
    selector-immutability, rather than a full re-coverage pass (no test-count target was set for
    this round). Full verification run once: 444 tests pass (`py -m unittest discover -s tests
    -v`), `py -m compileall -f src modules scripts tests` clean, `py -m src.main` ->
    `workflow_completed` (CardNews `card_news_completed`, Publishing `publishing_ready`, Learning
    `learning_completed` all confirmed from the real run's `storage/workflow_results/
    99_final_result.json`). Codex MCP independent review: **APPROVED** (one BLOCK — the
    `_fallback_result()` metadata gap above — fixed, re-reviewed).

## Phase M7 (CardNews Intelligence) + Phase M8 (CardNews Production Quality) Completed (2026-07-11)

Goal: elevate `CardNewsModule`'s existing Pillow renderer from "functionally generated images"
to production-quality output, and close the Evidence/Social Proof misuse gaps found during M7
review — all layered onto the existing renderer. No new top-level Engine, no new Renderer,
`src/workflow_engine.py` has zero diff (confirmed via `git diff --stat`).

- **Evidence Selection + guards** (`modules/card_news/evidence_selector.py`): a screenshot asset
  is only ever `available: true` when ALL FOUR independently-computed gates pass —
  `candidate_found` (file actually exists), `topic_relevant` (>= 2 matched terms AND score >=
  0.34 against `research_result`, never a single coincidental word), `render_allowed`
  (`copyright_status` in an explicit allow-list: `owned`/`licensed`/`public_domain`/
  `official_reuse_allowed`/`user_supplied_with_permission`), and `asset_role == "topic_evidence"`.
  Instagram-Research-sourced screenshots are hardcoded `asset_role: "competitor_reference"` and
  `copyright_status: "third_party_unlicensed_reference"` — never auto-promoted to topic evidence
  (no signal strong enough exists yet), so they can never reach the rendered card background.
  `CardNewsModule._apply_evidence_asset` re-checks `asset_role`/`render_allowed`/`candidate_found`
  as defense-in-depth before ever substituting an image path (does not trust `available` alone).
- **Social Proof safe selection** (`modules/card_news/social_proof_selector.py`): only real
  `comment_text`/`reply_text`/`reaction_text`/`quote_text` fields count as candidates —
  `caption_text` (the post owner's own text) and `visible_*_text` (like/comment *counts*, not
  content) are explicitly excluded. `_mask_account_handle()` (keep first 2 + last 1 char) and
  `_scrub_sensitive_info()` (email/phone regex masking, no meaning changes) are applied before any
  text reaches rendering. Every selected item carries `is_opinion: true` + `label: "커뮤니티 반응"` +
  a disclaimer. `available: false` remains correct today since no real third-party comment text
  source exists yet (only like/comment counts) — this is an honest gap, not a bug.
- **Story Flow + Debate/CTA guard** (`story_flow_planner.py`, `debate_question_selector.py`):
  narrative roles (`cover`/`problem`/`evidence`/`explanation`/`social_proof`/`conclusion`/
  `debate_cta`) are assigned only to slides that actually exist (`applied_roles` length never
  exceeds the real slide count). Debate questions are skipped entirely when `cta_type == "comment"`
  (already comment-inducing, would be redundant) and, at apply time, when the combined CTA+question
  text would exceed the existing `CTA_MAX_SENTENCES` character budget — the original CTA body is
  always preserved unchanged in both skip cases.
- **Typography + Human Visual Rhythm, actually wired into the renderer** (`typography_rules.py`,
  `visual_rhythm_selector.py`, `render_constants.py`): 7 typography roles (`cover_title`/
  `slide_title`/`body`/`quote`/`source`/`cta`/`page_number`) define real `font_size_range`/
  `max_lines`/`line_spacing`/`paragraph_spacing`. `CardNewsModule._plan_text_layout()` computes
  actual line-wrapped text and font size **before** the card box is drawn, and
  `_draw_layout_card`/`_draw_layout_text_content` use those real values (not just metadata) —
  `VISUAL_STYLE_PROFILES` (`title_focus`/`short_line_focus`/`image_focus`/`quote_card`/
  `comparison`/`whitespace_focus`/`cta_focus`) vary `box_top`/line-count budgets per slide's
  narrative role. `quote_card` and `comparison` fall back to a safe default style
  (`_resolve_visual_rhythm_application()`) when the real data they'd need (an actually-applied
  Social Proof quote / an actual A/B comparison structure, which the slide schema doesn't have
  yet) isn't present — never fabricated. `render_constants.py` is a single shared source of truth
  for font sizes/margins/palette between the renderer and `MobileReadabilityChecker` (no
  duplicated/drifting copies).
- **Contrast + Mobile Readability guard** (`mobile_readability_checker.py`): real WCAG relative-
  luminance contrast computed from the renderer's actual palette. Found and fixed a real
  pre-existing defect: light-mode subtitle text (120,120,120) on white box_fill had a measured
  contrast ratio of 4.42, below the WCAG AA 4.5 threshold — darkened to (112,112,112) (measured
  ~4.95) rather than lowering the threshold to hide the finding. Checker result now includes
  `evaluated_render_values`/`min_font_size_used`/`contrast_ratio_min`/`safe_margin_used`/
  `overflow_detected`, all computed from the same shared constants the renderer uses.
- **Source Attribution**: shown only when an Evidence asset was both `render_allowed: true` AND
  actually `applied: true` for that slide — `source_type` + `source_name` in the bottom safe area,
  never a raw `source_url`. No attribution block is drawn at all when either condition is false.
- **Production Quality QA** (`card_news_quality_checker.py`): 10 new checks
  (`typography_hierarchy_ok`/`cover_readability_ok`/`mobile_readability_ok`/`visual_rhythm_ok`/
  `text_overflow_free`/`contrast_ok`/`source_legible`/`cta_focus_ok`/
  `prohibited_fake_screenshot_absent`/`unlicensed_asset_not_rendered`) added to `CHECK_POINTS`;
  the pre-existing 14 checks were proportionally rescaled (100 -> 70) so the total remains exactly
  100 (verified: `sum(CardNewsQualityChecker.CHECK_POINTS.values()) == 100`). Data genuinely
  unavailable (not yet collected) is never penalized (`CONDITIONAL_CHECKS`/`_conditional_ok`);
  only "data was available but not applied" is penalized.
- **Real defect found and fixed during final PNG inspection** (not caught by compile/unit tests):
  `CardNewsTextOptimizer.SENTENCE_SPLIT_PATTERN` (and the identical pattern duplicated in
  `CardNewsModule._fit_lines`) treated a period right after a digit (e.g. `"1."` `"2."` in a
  numbered list) as a sentence boundary, so `BODY_MAX_SENTENCES` truncation could cut a rendered
  card's body to `"1. <content> 2."` — item 2's number surviving but its actual content silently
  disappearing. Fixed the regex to require a non-digit character before the sentence-ending
  punctuation (`(?<=[^\d][.!?。!?])`), confirmed via a real generated PNG before/after. Also
  hardened both modules' true last-resort character-level truncation fallback (only reached when
  even the minimum font size / a single remaining sentence still doesn't fit) to append an
  ellipsis ("…") rather than cutting with no visual indicator at all (found by Codex MCP review,
  fixed, re-reviewed APPROVED).
- **Honest current limitations** (not bugs — no data source exists yet):
  - No real third-party comment-body collector exists; Social Proof stays `available: false`
    until one is built.
  - Instagram competitor screenshots remain `competitor_reference`/`render_allowed: false` by
    design — analysis-only, never auto-rendered.
  - `comparison` visual style always falls back to the default style — the slide schema has no
    real A/B comparison structure yet.
  - Real post-publish Instagram performance Closed Loop still requires Meta/Instagram Graph API +
    OAuth (see `ROADMAP.md` "Requires External API") — unrelated to and unblocked by this Phase.
- New `tests/test_card_news_production_quality.py` (35 risk-based tests covering the guards
  above — no test-count target, each test maps to one specific risk item). Verified once each:
  `py -m unittest discover -s tests -v` -> 480 tests pass; `py -m compileall -f src modules
  scripts tests` clean; `py -m src.main` -> `workflow_completed` (`card_news_completed`,
  `publishing_ready`, 4 PNGs, `evidence_result`/`social_proof_result`/`story_flow_result`/
  `debate_result`/`typography_result`/`visual_rhythm_result`/`mobile_readability_result`/
  `card_news_quality` all present). All 4 generated PNGs opened and visually inspected (cover not
  overcrowded, clear hierarchy/whitespace rhythm per slide, clear CTA, no unsourced attribution,
  no fake comment card, no competitor screenshot misuse). Codex MCP independent review: one BLOCK
  (silent-truncation-fallback finding above), fixed, re-reviewed **APPROVED**.

## Next

### Content Intelligence Focused Contract Coverage (2026-07-11)

- Added 16 focused tests for ContentPromptBuilder, BrandRuleEvaluator, ContentDuplicateDetector, ContentQualityScorer, and PublishingHintGenerator.
- Covered legacy fallback, research-context injection, four-slide JSON contract, provenance metadata, Planner confidence gating, brand/exaggeration rules, duplicate thresholds, quality-score penalties/bonuses, CTA inference, and malformed input safety.
- Confirmed malformed or missing research input returns `None` for the existing ContentModule legacy path and never escapes an exception.
- All 49 `test_content_*.py` tests pass and the repository compile check is clean.
- No production Content Engine behavior or WorkflowEngine order changed.

### CardNews Operational Complete (M7-next, 2026-07-11)

- Generated and visually inspected all four 1024x1024 PNGs: no overlap, clipping, missing CTA, fake social proof, or prohibited competitor screenshot use.
- Fixed QA diagnostics so safe layout-selection fallback is not mislabeled as renderer fallback.
- Added `debate_required` so a documented character-budget/CTA-conflict skip is not penalized as an unexplained failure.
- CardNews QA: 0.85, passed; `rendering_fallback_used: false`; only the safe layout-selection fallback remains informational.
- Verification: 38 focused production-quality tests, compile clean, full `py -m src.main` -> `workflow_completed`, `card_news_completed`, `publishing_ready`.
- CardNews M7, M8, and M7-next are now operationally complete. Missing real evidence/comments/images remain separate external-data capabilities.

### Work/Codex Operating System and Domain Skills (2026-07-11)

- Default delivery path updated to ChatGPT Work CTO -> Codex execution in one project context.
- Claude remains available only for explicitly assigned specialist implementation or independent review; Codex MCP is no longer a prerequisite.
- Added ten validated project skills: Trend Collector, Research Intelligence, Card News, Shorts, Publishing, Instagram, Coupang, QA, CTO Review, and Sprint Manager.
- Shorts and Coupang skills are planning/approval gates only; they do not mark those Roadmap engines as implemented.
- Existing Claude domain files remain as compatibility references and are not the primary operating layer.

- Shorts Phase 0 architecture may now proceed as an isolated planning task; it must not modify the protected CardNews pipeline or mark Shorts implemented.
- Real post-publish Instagram Performance Closed Loop (actual likes/comments/saves/shares/reach
  replacing the current internal `quality_score` proxy in Learning/Knowledge Feedback) — requires
  Meta/Instagram Graph API + OAuth + a publish-result Import step; see `ROADMAP.md` "Requires
  External API".
- Real image sourcing automation (news thumbnail fetch, community post/comment capture, product lookup) — requires crawling external SNS/news pages, moved to ROADMAP.md "Requires External API"
- ContentPromptBuilder, Content Intelligence helpers, and CardNews production-quality focused coverage are complete
- Keep snapshot generator in sync with WorkflowEngine if future modules are added
- Wire Audit Engine's Competitor Comparison + Blind Spot Detection stages once Competitor Engine's `competitor_profiles.json` history accumulates across multiple runs
- Real Instagram Graph API connection for Analytics Engine — see ROADMAP.md "Requires External API"; until then `quality_trend` remains based on real local Performance Score history only
- AI Planner: fully implemented and wired (Sprint 15-0 → 15-3) — no remaining Planner work.
  Future consideration (not scheduled): tuning `MIN_CONFIDENCE_FOR_HINT_APPLICATION`/the Brand
  DNA override observation threshold once more real runs accumulate and hint-acceptance rates
  can be observed in practice.
- Source Health dashboard
- Collector Statistics dashboard
- Improve final safe-result recovery behavior

## Notes

- Always run the project with `py -m src.main`.
- Do not use `python -m src.main`.
- Internet, LLM, image, Pattern Engine, Content prompt, Content Intelligence, CardNews Layout Intelligence/rendering/QA/design quality, Knowledge Engine, Performance Score, Audit Engine, Learning Engine, Analytics Engine, Brand DNA Engine, Trend Memory, and Competitor Engine failures must be recorded as fallback events, not workflow failures.
- Competitor Learning Engine is not part of `WorkflowEngine.run()` (standalone/on-demand), but its consumption points inside Pattern Engine/Content Engine/Brand DNA/Learning Engine must still degrade to their existing pre-Sprint-18 behavior, never raise, if `storage/knowledge/knowledge_database.json` is missing or empty.
- `content_performance_history.json`/Learning Feedback/Knowledge Feedback are an internal pre-publish `quality_score` proxy, not real Instagram performance — never remove the `INTERNAL_QUALITY_PROXY_METADATA` labeling when touching this loop (see `DECISIONS.md`, 2026-07-11).
- OpenAI, Naver News, and Nate Pann transient connection failures should retry with backoff before fallback.
- Keep Naver News and Nate Pann fallback/cache behavior intact.
- Knowledge Engine failure must still guarantee an existing (even empty) `storage/knowledge/knowledge.json` — never leave the DB file missing. The same guarantee now applies to `storage/performance_score/`, `storage/audit/`, `storage/learning/`, `storage/analytics/`, `storage/brand_dna/`, `storage/trend_memory/`, and `storage/competitor/`.
- None of the Sprint 12/13 bonus Engines call external network/LLM APIs, so none implement literal retry logic — their Fallback strategy (safe default result, never raise) is the reliability contract instead, consistent with `image_strategy`/`pattern_engine`.
- Per Sprint 13's explicit "Offline-First" constraint: do not implement Instagram API, Meta Graph API, access-token-based auth, or real SNS login/crawling without explicit future approval — check ROADMAP.md's "Requires External API" section first.
