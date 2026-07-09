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
- Trend Quality Scoring v1
- Selection Reason v1
- Top Topic Picker
- Duplicate Removal v1
- `selected_topic.json`
- `trend_result.json` includes `selected_topic`
- Research Module selected_topic linkage
- Research Module pattern_result linkage
- Content Module pattern-aware prompt linkage
- Content Intelligence v1
- CardNews Layout Intelligence v1
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

## Verification

- Compile command: `py -m compileall src modules scripts`
- Compile result: success
- Workflow command: `py -m src.main`
- Workflow result: `workflow_completed`
- Required pattern files generated:
  - `storage/pattern/pattern_result.json`
  - `storage/pattern/pattern_history.json`
  - `storage/pattern/pattern_statistics.json`
- Latest Research result includes `pattern_result_available: true`
- Latest Content result includes `prompt_source: pattern_aware`
- Latest Content result records LLM fallback with `fallback_used: true` when API calls fail
- Latest Content result includes all required `content_intelligence` fields
- Latest run generated `storage/content/content_history.json`
- Latest generated `PROJECT_SNAPSHOT.md` includes `PatternEngineModule` and runtime tree omission markers
- Latest CardNews result includes all required `layout_result` fields
- Latest run generated 4 card news PNG files

## Next

- M2 Content Engine enhancement
- Add focused unit checks for ContentPromptBuilder, Content Intelligence helpers, CardNews Layout Intelligence helpers, and fallback fields
- Keep snapshot generator in sync with WorkflowEngine if future modules are added
- Source Health dashboard
- Collector Statistics dashboard
- Improve final safe-result recovery behavior

## Notes

- Always run the project with `py -m src.main`.
- Do not use `python -m src.main`.
- Internet, LLM, image, Pattern Engine, Content prompt, Content Intelligence, and CardNews Layout Intelligence failures must be recorded as fallback events, not workflow failures.
- Keep Naver News and Nate Pann fallback/cache behavior intact.
