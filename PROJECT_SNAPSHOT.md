# AI-Content-OS Project Snapshot

Updated at: 2026-07-09T13:02:36

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
- Content generation: content_created
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
|   |   `-- (4 runtime file(s) omitted; gitignored, see .gitignore)
|   |-- content/
|   |   `-- (1 runtime file(s) omitted; gitignored, see .gitignore)
|   |-- generated_images/
|   |   `-- (4 runtime file(s) omitted; gitignored, see .gitignore)
|   |-- history/
|   |   `-- .gitkeep
|   |-- images/
|   |   `-- (4 runtime file(s) omitted; gitignored, see .gitignore)
|   |-- llm_logs/
|   |   `-- (136 runtime file(s) omitted; gitignored, see .gitignore)
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
|   |   |   `-- (8 runtime file(s) omitted; gitignored, see .gitignore)
|   |   |-- .gitkeep
|   |   |-- collector_statistics.json
|   |   |-- last_safe_trend_result.json
|   |   |-- selected_topic.json
|   |   |-- source_health.json
|   |   |-- trend_engine_status.json
|   |   |-- trend_result.json
|   |   `-- trend_run_log.jsonl
|   |-- workflow_results/
|   |   `-- (23 runtime file(s) omitted; gitignored, see .gitignore)
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

- Project status document auto-update script maintained.
- Sprint 5 snapshot generator correction completed: PatternEngineModule is included in the current WorkflowEngine line.
- Runtime storage directories are collapsed in the project tree instead of listing every generated file.
- Runtime storage outputs are gitignored and excluded from commit targets.
- Keep fallback-first workflow behavior intact.

## Protected Rules

- Keep existing WorkflowEngine structure.
- Use `py -m src.main` as the execution command.
- Do not use `python -m src.main`.
- Keep `workflow_completed` from regressing.
- Keep fallback behavior for internet, LLM, and image failures.
