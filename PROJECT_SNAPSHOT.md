# AI-Content-OS Project Snapshot

Updated at: 2026-07-08T16:06:58

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
- Research: success
- Content generation: content_created
- Image prompt generation: image_prompts_created
- Image generation: image_generation_completed
- Card news rendering: card_news_completed
- Publishing preparation: publishing_ready

## Current WorkflowEngine

- TrendCollectorModule -> TopicEngineModule -> ResearchModule -> ContentModule -> ImagePromptModule -> ImageGenerationModule -> CardNewsModule -> PublishingModule

## Current Project Tree

```text
AI-Content-OS/
|-- .agents/
|-- config/
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
|   |   `-- content_module.py
|   |-- image_generation/
|   |   |-- __init__.py
|   |   `-- image_generation_module.py
|   |-- image_prompt/
|   |   |-- __init__.py
|   |   `-- image_prompt_module.py
|   |-- publishing/
|   |   |-- __init__.py
|   |   `-- publishing_module.py
|   |-- research/
|   |   `-- research_module.py
|   |-- topic/
|   |   `-- topic_engine.py
|   |-- topic_engine/
|   |   |-- __init__.py
|   |   `-- topic_engine_module.py
|   |-- trend/
|   |-- trend_collector/
|   |   |-- __init__.py
|   |   |-- naver_news_collector.py
|   |   |-- trend_collector_module.py
|   |   `-- trend_source_manager.py
|   |-- base_module.py
|   `-- README.md
|-- prompts/
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
|   |   `-- .gitkeep
|   |-- card_news/
|   |   |-- card_news_1.png
|   |   |-- card_news_2.png
|   |   |-- card_news_3.png
|   |   `-- card_news_4.png
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
|   |   `-- llm_log_20260708_160613.json
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
|   |   |-- .gitkeep
|   |   `-- trend_result.json
|   |-- workflow_results/
|   |   |-- 01_research_result.json
|   |   |-- 01_trend_result.json
|   |   |-- 02_content_result.json
|   |   |-- 02_topic_result.json
|   |   |-- 03_image_prompt_result.json
|   |   |-- 03_research_result.json
|   |   |-- 04_content_result.json
|   |   |-- 04_image_generation_result.json
|   |   |-- 05_card_news_result.json
|   |   |-- 05_image_prompt_result.json
|   |   |-- 06_image_generation_result.json
|   |   |-- 06_publishing_result.json
|   |   |-- 07_card_news_result.json
|   |   |-- 08_publishing_result.json
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
|-- AI_CONTEXT.md
|-- CHANGELOG.md
|-- CURRENT_TASK.md
|-- DECISIONS.md
|-- DIRECTORY_STRUCTURE.md
|-- MODULE_SPEC.md
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
- Keep fallback-first workflow behavior intact.

## Protected Rules

- Keep existing WorkflowEngine structure.
- Use `py -m src.main` as the execution command.
- Keep `workflow_completed` from regressing.
- Keep fallback behavior for internet, LLM, and image failures.
