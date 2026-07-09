# AI-Content-OS Project Snapshot

Updated at: 2026-07-09T12:40:15

## Execution Command

```powershell
py -m src.main
```

Do not use `python -m src.main` for this project.

## Workflow Result

- Final status: `workflow_completed`
- Result file: `storage/workflow_results/99_final_result.json`

## Recent Completed Features

- Trend collection: success
- Topic selection: success
- Pattern selection: pattern_selected
- Research: success
- Content generation: content_created with `content_intelligence`
- Image prompt generation: image_prompts_created
- Image generation: image_generation_completed
- Card news rendering: card_news_completed
- Publishing preparation: publishing_ready

## Current WorkflowEngine

- TrendCollectorModule -> TopicEngineModule -> PatternEngineModule -> ResearchModule -> ContentModule -> ImagePromptModule -> ImageGenerationModule -> CardNewsModule -> PublishingModule

## Current Project Tree

```text
AI-Content-OS/
|-- .agents/
|-- .codex/
|   `-- skills/
|       `-- ai-content-os-dev/
|-- benchmark/
|   |-- AI_CONTENT_STRATEGY.md
|   |-- CONTENT_PATTERNS.md
|   |-- CTA_LIBRARY.md
|   |-- HOOK_LIBRARY.md
|   |-- INSTAGRAM_BENCHMARK.md
|   `-- TOOLS_AND_FUNNEL_REFERENCES.md
|-- config/
|   |-- brand_profile.json
|   |-- publishing.json
|   |-- README.md
|   |-- settings.json
|   |-- topic_engine.json
|   `-- trend_sources.json
|-- docs/
|   |-- AI_RULES.md
|   |-- COST.md
|   |-- DEPLOYMENT.md
|   |-- DIRECTORY_STRUCTURE.md
|   |-- MASTER_JSON.md
|   |-- MONETIZATION.md
|   |-- PROJECT_VISION.md
|   |-- RELEASE_RULE.md
|   |-- SPRINT_01.md
|   |-- SYSTEM_ARCHITECTURE.md
|   |-- TECH_STACK.md
|   |-- TOPIC_ENGINE_SPEC.md
|   `-- WORKFLOW.md
|-- logs/
|   `-- README.md
|-- modules/
|   |-- card_news/
|   |   |-- __init__.py
|   |   `-- card_news_module.py
|   |-- common/
|   |   `-- __init__.py
|   |-- content/
|   |   |-- brand_rule_evaluator.py
|   |   |-- content_duplicate_detector.py
|   |   |-- content_module.py
|   |   |-- content_prompt_builder.py
|   |   |-- content_quality_scorer.py
|   |   |-- cta_strategy.py
|   |   |-- hook_strategy.py
|   |   |-- pattern_prompt_router.py
|   |   |-- publishing_hint_generator.py
|   |   `-- slide_strategy.py
|   |-- image_generation/
|   |   |-- __init__.py
|   |   `-- image_generation_module.py
|   |-- image_prompt/
|   |   |-- __init__.py
|   |   `-- image_prompt_module.py
|   |-- pattern_engine/
|   |   |-- __init__.py
|   |   |-- cta_selector.py
|   |   |-- hook_selector.py
|   |   |-- layout_selector.py
|   |   |-- pattern_engine_module.py
|   |   |-- pattern_result_writer.py
|   |   `-- pattern_selector.py
|   |-- publishing/
|   |   |-- __init__.py
|   |   `-- publishing_module.py
|   |-- research/
|   |   `-- research_module.py
|   |-- topic/
|   |   `-- topic_engine.py
|   |-- topic_engine/
|   |   |-- __init__.py
|   |   |-- confidence_score.py
|   |   |-- keyword_weight.py
|   |   |-- topic_classifier.py
|   |   |-- topic_cluster.py
|   |   `-- topic_engine_module.py
|   |-- trend/
|   |-- trend_collector/
|   |   |-- __init__.py
|   |   |-- nate_pann_collector.py
|   |   |-- naver_news_collector.py
|   |   |-- retry_policy.py
|   |   |-- source_health_tracker.py
|   |   |-- top_topic_picker.py
|   |   |-- trend_collector_module.py
|   |   |-- trend_engine_guard.py
|   |   |-- trend_quality_scorer.py
|   |   |-- trend_run_recorder.py
|   |   `-- trend_source_manager.py
|   |-- base_module.py
|   `-- README.md
|-- prompts/
|   |-- patterns/
|   |   |-- comparison_prompt.md
|   |   |-- number_list_prompt.md
|   |   |-- resource_prompt.md
|   |   |-- story_prompt.md
|   |   |-- tutorial_prompt.md
|   |   `-- warning_prompt.md
|   |-- content_prompt.md
|   |-- image_prompt.md
|   |-- README.md
|   `-- research_prompt.md
|-- scripts/
|   `-- update_project_snapshot.py
|-- src/
|   |-- llm_client.py
|   |-- main.py
|   |-- README.md
|   `-- workflow_engine.py
|-- storage/
|   |-- cache/
|   |   |-- .gitkeep
|   |   |-- nate_pann_cache.json
|   |   `-- naver_news_cache.json
|   |-- card_news/
|   |   |-- card_news_1.png
|   |   |-- card_news_2.png
|   |   |-- card_news_3.png
|   |   `-- card_news_4.png
|   |-- content/
|   |   `-- content_history.json
|   |-- generated_images/
|   |   |-- ai_image_1.png
|   |   |-- ai_image_2.png
|   |   |-- ai_image_3.png
|   |   `-- ai_image_4.png
|   |-- history/
|   |   `-- .gitkeep
|   |-- images/
|   |   |-- card_slide_1.png
|   |   |-- card_slide_2.png
|   |   |-- card_slide_3.png
|   |   `-- card_slide_4.png
|   |-- llm_logs/
|   |   |-- llm_log_20260708_121621.json
|   |   |-- llm_log_20260708_121624.json
|   |   |-- llm_log_20260708_121631.json
|   |   |-- llm_log_20260708_122845.json
|   |   |-- llm_log_20260708_122849.json
|   |   |-- llm_log_20260708_122855.json
|   |   |-- llm_log_20260708_135801.json
|   |   |-- llm_log_20260708_135807.json
|   |   |-- llm_log_20260708_141726.json
|   |   |-- llm_log_20260708_141734.json
|   |   |-- llm_log_20260708_142643.json
|   |   |-- llm_log_20260708_142649.json
|   |   |-- llm_log_20260708_144805.json
|   |   |-- llm_log_20260708_144813.json
|   |   |-- llm_log_20260708_150438.json
|   |   |-- llm_log_20260708_150446.json
|   |   |-- llm_log_20260708_155354.json
|   |   |-- llm_log_20260708_155404.json
|   |   |-- llm_log_20260708_155413.json
|   |   |-- llm_log_20260708_155420.json
|   |   |-- llm_log_20260708_155430.json
|   |   |-- llm_log_20260708_155440.json
|   |   |-- llm_log_20260708_160529.json
|   |   |-- llm_log_20260708_160538.json
|   |   |-- llm_log_20260708_160547.json
|   |   |-- llm_log_20260708_160554.json
|   |   |-- llm_log_20260708_160604.json
|   |   |-- llm_log_20260708_160613.json
|   |   |-- llm_log_20260708_161127.json
|   |   |-- llm_log_20260708_161137.json
|   |   |-- llm_log_20260708_161146.json
|   |   |-- llm_log_20260708_161153.json
|   |   |-- llm_log_20260708_161203.json
|   |   |-- llm_log_20260708_161212.json
|   |   |-- llm_log_20260708_162524.json
|   |   |-- llm_log_20260708_162533.json
|   |   |-- llm_log_20260708_162543.json
|   |   |-- llm_log_20260708_162550.json
|   |   |-- llm_log_20260708_162600.json
|   |   |-- llm_log_20260708_162609.json
|   |   |-- llm_log_20260708_163509.json
|   |   |-- llm_log_20260708_163519.json
|   |   |-- llm_log_20260708_163528.json
|   |   |-- llm_log_20260708_163536.json
|   |   |-- llm_log_20260708_163545.json
|   |   |-- llm_log_20260708_163554.json
|   |   |-- llm_log_20260708_163939.json
|   |   |-- llm_log_20260708_163948.json
|   |   |-- llm_log_20260708_163958.json
|   |   |-- llm_log_20260708_164005.json
|   |   |-- llm_log_20260708_164015.json
|   |   |-- llm_log_20260708_164024.json
|   |   |-- llm_log_20260708_165802.json
|   |   |-- llm_log_20260708_165811.json
|   |   |-- llm_log_20260708_165821.json
|   |   |-- llm_log_20260708_165828.json
|   |   |-- llm_log_20260708_165837.json
|   |   |-- llm_log_20260708_165847.json
|   |   |-- llm_log_20260708_170352.json
|   |   |-- llm_log_20260708_170401.json
|   |   |-- llm_log_20260708_170410.json
|   |   |-- llm_log_20260708_170418.json
|   |   |-- llm_log_20260708_170427.json
|   |   |-- llm_log_20260708_170437.json
|   |   |-- llm_log_20260708_172520.json
|   |   |-- llm_log_20260708_172529.json
|   |   |-- llm_log_20260708_172539.json
|   |   |-- llm_log_20260708_172546.json
|   |   |-- llm_log_20260708_172556.json
|   |   |-- llm_log_20260708_172605.json
|   |   |-- llm_log_20260708_173828.json
|   |   |-- llm_log_20260708_173838.json
|   |   |-- llm_log_20260708_173847.json
|   |   |-- llm_log_20260708_173855.json
|   |   |-- llm_log_20260708_173904.json
|   |   |-- llm_log_20260708_173913.json
|   |   |-- llm_log_20260708_175542.json
|   |   |-- llm_log_20260708_175552.json
|   |   |-- llm_log_20260708_175601.json
|   |   |-- llm_log_20260708_175608.json
|   |   |-- llm_log_20260708_175618.json
|   |   |-- llm_log_20260708_175627.json
|   |   |-- llm_log_20260708_180731.json
|   |   |-- llm_log_20260708_180741.json
|   |   |-- llm_log_20260708_180750.json
|   |   |-- llm_log_20260708_180758.json
|   |   |-- llm_log_20260708_180807.json
|   |   |-- llm_log_20260708_180816.json
|   |   |-- llm_log_20260708_181538.json
|   |   |-- llm_log_20260708_181547.json
|   |   |-- llm_log_20260708_181556.json
|   |   |-- llm_log_20260708_181604.json
|   |   |-- llm_log_20260708_181613.json
|   |   |-- llm_log_20260708_181622.json
|   |   |-- llm_log_20260708_182223.json
|   |   |-- llm_log_20260708_182233.json
|   |   |-- llm_log_20260708_182242.json
|   |   |-- llm_log_20260708_182249.json
|   |   |-- llm_log_20260708_182259.json
|   |   |-- llm_log_20260708_182308.json
|   |   |-- llm_log_20260709_115549.json
|   |   |-- llm_log_20260709_115559.json
|   |   |-- llm_log_20260709_115608.json
|   |   |-- llm_log_20260709_115616.json
|   |   |-- llm_log_20260709_115625.json
|   |   |-- llm_log_20260709_115634.json
|   |   |-- llm_log_20260709_120044.json
|   |   |-- llm_log_20260709_120054.json
|   |   |-- llm_log_20260709_120103.json
|   |   |-- llm_log_20260709_120110.json
|   |   |-- llm_log_20260709_120120.json
|   |   |-- llm_log_20260709_120129.json
|   |   |-- llm_log_20260709_120440.json
|   |   |-- llm_log_20260709_120449.json
|   |   |-- llm_log_20260709_120459.json
|   |   |-- llm_log_20260709_120506.json
|   |   |-- llm_log_20260709_120516.json
|   |   |-- llm_log_20260709_120525.json
|   |   |-- llm_log_20260709_122440.json
|   |   |-- llm_log_20260709_122450.json
|   |   |-- llm_log_20260709_122459.json
|   |   |-- llm_log_20260709_122507.json
|   |   |-- llm_log_20260709_122516.json
|   |   |-- llm_log_20260709_122526.json
|   |   |-- llm_log_20260709_123901.json
|   |   |-- llm_log_20260709_123910.json
|   |   |-- llm_log_20260709_123919.json
|   |   |-- llm_log_20260709_123927.json
|   |   |-- llm_log_20260709_123936.json
|   |   `-- llm_log_20260709_123945.json
|   |-- logs/
|   |   `-- .gitkeep
|   |-- memory/
|   |   `-- .gitkeep
|   |-- outputs/
|   |   |-- card_news_result.json
|   |   |-- content_result.json
|   |   |-- image_generation_result.json
|   |   |-- image_prompt_result.json
|   |   |-- publishing_result.json
|   |   `-- research_result.json
|   |-- pattern/
|   |   |-- .gitkeep
|   |   |-- pattern_history.json
|   |   |-- pattern_result.json
|   |   `-- pattern_statistics.json
|   |-- publishing/
|   |   |-- caption.txt
|   |   |-- hashtags.txt
|   |   |-- publish_queue.json
|   |   `-- publishing_result.json
|   |-- research/
|   |   `-- research_result.json
|   |-- topics/
|   |   |-- .gitkeep
|   |   `-- topic_result.json
|   |-- trends/
|   |   |-- snapshots/
|   |   |-- .gitkeep
|   |   |-- collector_statistics.json
|   |   |-- last_safe_trend_result.json
|   |   |-- selected_topic.json
|   |   |-- source_health.json
|   |   |-- trend_engine_status.json
|   |   |-- trend_result.json
|   |   `-- trend_run_log.jsonl
|   |-- workflow_results/
|   |   |-- 01_research_result.json
|   |   |-- 01_trend_result.json
|   |   |-- 02_content_result.json
|   |   |-- 02_topic_result.json
|   |   |-- 03_image_prompt_result.json
|   |   |-- 03_pattern_result.json
|   |   |-- 03_research_result.json
|   |   |-- 04_content_result.json
|   |   |-- 04_image_generation_result.json
|   |   |-- 04_research_result.json
|   |   |-- 05_card_news_result.json
|   |   |-- 05_content_result.json
|   |   |-- 05_image_prompt_result.json
|   |   |-- 06_image_generation_result.json
|   |   |-- 06_image_prompt_result.json
|   |   |-- 06_publishing_result.json
|   |   |-- 07_card_news_result.json
|   |   |-- 07_image_generation_result.json
|   |   |-- 08_card_news_result.json
|   |   |-- 08_publishing_result.json
|   |   |-- 09_publishing_result.json
|   |   |-- 99_final_result.json
|   |   `-- final_result.json
|   `-- README.md
|-- templates/
|   |-- card_news_template.json
|   `-- publishing_template.json
|-- tests/
|-- utils/
|   `-- __init__.py
|-- workflows/
|   `-- README.md
|-- .env
|-- .gitignore
|-- AGENTS.md
|-- AI_CONTEXT.md
|-- CHANGELOG.md
|-- CLAUDE.md
|-- CODEX_RULES.md
|-- CURRENT_TASK.md
|-- DECISIONS.md
|-- DIRECTORY_STRUCTURE.md
|-- MODULE_SPEC.md
|-- MODULE_STATUS.md
|-- PROJECT_BIBLE.md
|-- PROJECT_SNAPSHOT.md
|-- PROJECT_STATE.md
|-- README.md
|-- requirements.txt
|-- ROADMAP.md
|-- SYSTEM_ARCHITECTURE.md
`-- WORKFLOW_SPEC.md
```

## Current Work

- Project status document auto-update script added.
- Sprint 4 Content Intelligence v1 completed.
- ContentModule result includes `content_intelligence` with quality, duplicate, brand, publishing, recommendation, and detail fields.
- `storage/content/content_history.json` is generated for duplicate-risk checks and remains excluded from commit targets.
- Keep fallback-first workflow behavior intact.

## Protected Rules

- Keep existing WorkflowEngine structure.
- Use `py -m src.main` as the execution command.
- Keep `workflow_completed` from regressing.
- Keep fallback behavior for internet, LLM, and image failures.
- Content Intelligence calculation failures must fall back to safe default fields, not workflow failure.
