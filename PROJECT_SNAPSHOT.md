# AI-Content-OS Project Snapshot

Updated at: 2026-07-11T19:03:25

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
- Image strategy selection: image_strategy_completed
- Image prompt generation: image_prompts_skipped
- Image generation: image_generation_skipped
- Card news rendering: card_news_completed
- Publishing preparation: publishing_ready
- Knowledge extraction: knowledge_extracted
- Trend memory record: trend_memory_recorded
- Performance score: performance_score_completed
- Content audit: audit_completed
- Learning engine: learning_completed
- Analytics prediction: analytics_completed
- Brand DNA update: brand_dna_updated
- Competitor profile: competitor_profile_built

## Current WorkflowEngine

- TrendCollectorModule -> TopicEngineModule -> PatternEngineModule -> ResearchModule -> ContentModule -> ImageStrategyModule -> ImagePromptModule -> ImageGenerationModule -> CardNewsModule -> PublishingModule -> KnowledgeModule -> TrendMemoryModule -> PerformanceScoreModule -> AuditEngineModule -> LearningEngineModule -> AnalyticsEngineModule -> BrandDNAEngineModule -> CompetitorEngineModule

## Current Project Tree

```text
AI-Content-OS/
|-- .agents/
|-- .ai/
|   |-- architecture/
|   |   `-- system_architecture.md
|   |-- decision/
|   |   `-- decision_engine.md
|   |-- knowledge/
|   |   `-- knowledge_system.md
|   |-- prompts/
|   |   `-- README.md
|   |-- rules/
|   |   |-- ai_roles.md
|   |   |-- project_rules.md
|   |   `-- workflow_protection.md
|   |-- templates/
|   |   |-- sprint_template.md
|   |   `-- task_template.md
|   |-- workflows/
|   |   |-- development_workflow.md
|   |   `-- sprint_workflow.md
|   `-- README.md
|-- .claude/
|   |-- skills/
|   |   |-- cto_operating_system/
|   |   |-- domain/
|   |   |-- architecture.md
|   |   |-- competitor_analysis.md
|   |   |-- content_roi.md
|   |   |-- image_strategy.md
|   |   |-- large_implementation.md
|   |   |-- planning.md
|   |   |-- refactoring.md
|   |   |-- research.md
|   |   `-- review.md
|   `-- settings.local.json
|-- .codex/
|   `-- skills/
|       |-- ai-content-os-card-news/
|       |-- ai-content-os-commit-check/
|       |-- ai-content-os-coupang/
|       |-- ai-content-os-cto-review/
|       |-- ai-content-os-dev/
|       |-- ai-content-os-doc-update/
|       |-- ai-content-os-instagram/
|       |-- ai-content-os-publishing/
|       |-- ai-content-os-qa/
|       |-- ai-content-os-research/
|       |-- ai-content-os-research-intelligence/
|       |-- ai-content-os-retry-audit/
|       |-- ai-content-os-shorts/
|       |-- ai-content-os-sprint/
|       |-- ai-content-os-sprint-manager/
|       `-- ai-content-os-trend-collector/
|-- .codex-test-tmp/
|   |-- card_news_render_test_rdfokizy/
|   |-- competitor_learning_interface_test_7f_pzxnv/
|   |-- competitor_learning_interface_test_bjdbpp0g/
|   |-- competitor_learning_interface_test_crz6aoo_/
|   |-- competitor_learning_interface_test_ctn3rmco/
|   |-- competitor_learning_interface_test_fie05bwb/
|   |-- competitor_learning_interface_test_gmqd49_5/
|   |-- competitor_learning_interface_test_h6qpadnq/
|   |-- competitor_learning_interface_test_idy3978j/
|   |-- competitor_learning_interface_test_ljc65mos/
|   |-- competitor_learning_interface_test_mvqqanqa/
|   |-- competitor_learning_interface_test_nxgu9b8j/
|   |-- competitor_learning_interface_test_o9906j9x/
|   |-- competitor_learning_interface_test_s7fdyx2j/
|   |-- competitor_learning_interface_test_sk2lqiyx/
|   |-- competitor_learning_interface_test_t_khtmty/
|   |-- competitor_learning_interface_test_tcs7y7l_/
|   |-- competitor_learning_module_test_1lrl8t30/
|   |-- competitor_learning_module_test_5p7vc5md/
|   |-- competitor_learning_module_test_5z8ajw46/
|   |-- competitor_learning_module_test_65p68fsn/
|   |-- competitor_learning_module_test_6tzrmd57/
|   |-- competitor_learning_module_test_8txdcawq/
|   |-- competitor_learning_module_test_aq6xd50b/
|   |-- competitor_learning_module_test_inzoxqm1/
|   |-- competitor_learning_module_test_j4lqsqsi/
|   |-- competitor_learning_module_test_ssyvqvwm/
|   |-- competitor_learning_module_test_w_ideh7i/
|   |-- competitor_learning_module_test_yt5ih826/
|   |-- competitor_learning_test_2fh_o4uh/
|   |-- competitor_learning_test_4pkywjjg/
|   |-- competitor_learning_test_6p9kmk6b/
|   |-- competitor_learning_test_7dffzs22/
|   |-- competitor_learning_test_82mloqko/
|   |-- competitor_learning_test_881f5n7o/
|   |-- competitor_learning_test_a9ok8e7p/
|   |-- competitor_learning_test_boyzy9my/
|   |-- competitor_learning_test_g6p4lqew/
|   |-- competitor_learning_test_gyib1x5m/
|   |-- competitor_learning_test_ieo4w5l4/
|   |-- competitor_learning_test_k13mid5x/
|   |-- competitor_learning_test_mor0ufhk/
|   |-- competitor_learning_test_p46xqxxc/
|   |-- competitor_learning_test_sjvsk6f5/
|   |-- competitor_learning_test_wq98wuc9/
|   |-- competitor_learning_test_wxlmzzan/
|   |-- evidence_selector_test_4j2omq3s/
|   |-- evidence_selector_test_jdsso62l/
|   |-- evidence_selector_test_tty6g8a7/
|   |-- instagram_research_test_0l2dgunb/
|   |-- instagram_research_test_0m80me7_/
|   |-- instagram_research_test_0uidxwko/
|   |-- instagram_research_test_2wjpe80k/
|   |-- instagram_research_test_4q8dl77n/
|   |-- instagram_research_test_4sdkzeah/
|   |-- instagram_research_test_4x5fukg8/
|   |-- instagram_research_test_89kshedp/
|   |-- instagram_research_test_8h_1m0q8/
|   |-- instagram_research_test__829nv8t/
|   |-- instagram_research_test__nuwnhk7/
|   |-- instagram_research_test__xanfo2z/
|   |-- instagram_research_test_a6astkh9/
|   |-- instagram_research_test_awxv43xo/
|   |-- instagram_research_test_cf6p9_0_/
|   |-- instagram_research_test_g09xftd0/
|   |-- instagram_research_test_gh51a_kg/
|   |-- instagram_research_test_h6wwdrw0/
|   |-- instagram_research_test_ie8j6ngo/
|   |-- instagram_research_test_k552o1wy/
|   |-- instagram_research_test_kgba_z0z/
|   |-- instagram_research_test_oh_1khvf/
|   |-- instagram_research_test_q32hzdfd/
|   |-- instagram_research_test_rstqo2df/
|   |-- instagram_research_test_sihzxr1v/
|   |-- instagram_research_test_skbpdext/
|   |-- risk_a_test_6pkek_yp/
|   |-- risk_a_test_7skf5vq5/
|   |-- risk_a_test_he5myoss/
|   |-- risk_a_test_nbkp36n2/
|   |-- risk_a_test_xicm38b3/
|   |-- risk_c_test_70hjhdgt/
|   |-- risk_c_test_angcm8_g/
|   |-- risk_c_test_o1tp8qtc/
|   |-- risk_e_test_7qtbq3rk/
|   `-- risk_f_test_mxx796h7/
|-- .playwright-mcp/
|   |-- console-2026-07-10T10-58-21-755Z.log
|   |-- console-2026-07-10T11-00-17-038Z.log
|   |-- console-2026-07-10T11-00-59-987Z.log
|   |-- console-2026-07-10T11-02-56-948Z.log
|   |-- console-2026-07-10T11-03-13-982Z.log
|   |-- console-2026-07-10T11-03-36-118Z.log
|   |-- console-2026-07-10T11-03-44-913Z.log
|   |-- console-2026-07-10T11-03-55-566Z.log
|   |-- console-2026-07-10T11-04-04-472Z.log
|   |-- console-2026-07-10T11-04-16-253Z.log
|   |-- console-2026-07-10T11-04-22-281Z.log
|   |-- console-2026-07-10T11-04-31-315Z.log
|   |-- console-2026-07-10T11-04-39-414Z.log
|   |-- console-2026-07-10T11-59-22-055Z.log
|   |-- console-2026-07-10T11-59-48-548Z.log
|   |-- console-2026-07-10T12-00-00-025Z.log
|   |-- console-2026-07-10T12-02-16-087Z.log
|   |-- console-2026-07-10T12-02-25-922Z.log
|   |-- console-2026-07-10T12-02-47-960Z.log
|   |-- console-2026-07-10T12-02-59-198Z.log
|   |-- console-2026-07-10T12-03-16-771Z.log
|   |-- console-2026-07-10T12-03-26-351Z.log
|   |-- console-2026-07-10T12-03-49-636Z.log
|   |-- console-2026-07-10T12-04-10-607Z.log
|   |-- console-2026-07-10T12-04-20-049Z.log
|   |-- console-2026-07-10T12-04-32-729Z.log
|   |-- console-2026-07-10T12-04-41-389Z.log
|   |-- console-2026-07-10T12-04-48-640Z.log
|   |-- console-2026-07-10T12-04-58-164Z.log
|   |-- page-2026-07-10T10-34-46-213Z.yml
|   |-- page-2026-07-10T10-58-22-784Z.yml
|   |-- page-2026-07-10T11-00-19-174Z.yml
|   |-- page-2026-07-10T11-01-15-699Z.yml
|   |-- page-2026-07-10T11-02-58-698Z.yml
|   |-- page-2026-07-10T11-03-15-961Z.yml
|   |-- page-2026-07-10T11-03-37-073Z.yml
|   |-- page-2026-07-10T11-03-46-529Z.yml
|   |-- page-2026-07-10T11-03-56-952Z.yml
|   |-- page-2026-07-10T11-04-05-773Z.yml
|   |-- page-2026-07-10T11-04-17-270Z.yml
|   |-- page-2026-07-10T11-04-23-696Z.yml
|   |-- page-2026-07-10T11-04-32-933Z.yml
|   |-- page-2026-07-10T11-04-40-600Z.yml
|   |-- page-2026-07-10T11-59-26-064Z.yml
|   |-- page-2026-07-10T11-59-49-191Z.yml
|   |-- page-2026-07-10T12-00-13-666Z.yml
|   |-- page-2026-07-10T12-02-17-371Z.yml
|   |-- page-2026-07-10T12-02-41-283Z.yml
|   |-- page-2026-07-10T12-02-49-460Z.yml
|   |-- page-2026-07-10T12-02-59-878Z.yml
|   |-- page-2026-07-10T12-03-18-031Z.yml
|   |-- page-2026-07-10T12-03-39-779Z.yml
|   |-- page-2026-07-10T12-04-03-112Z.yml
|   |-- page-2026-07-10T12-04-11-834Z.yml
|   |-- page-2026-07-10T12-04-20-662Z.yml
|   |-- page-2026-07-10T12-04-35-222Z.yml
|   |-- page-2026-07-10T12-04-42-664Z.yml
|   |-- page-2026-07-10T12-04-49-909Z.yml
|   `-- page-2026-07-10T12-04-59-417Z.yml
|-- .tmp/
|   |-- instagram_research_test_0sqsk8bl/
|   |-- instagram_research_test_16lxitgf/
|   |-- instagram_research_test_2ztvmvm1/
|   |-- instagram_research_test_3ymgs2l0/
|   |-- instagram_research_test_47w_t35g/
|   |-- instagram_research_test_4wb_cfk5/
|   |-- instagram_research_test_adi6lnog/
|   |-- instagram_research_test_bbc7jub3/
|   |-- instagram_research_test_g7y63b_d/
|   |-- instagram_research_test_h6cusuw2/
|   |-- instagram_research_test_i754luxc/
|   |-- instagram_research_test_inr6ley_/
|   |-- instagram_research_test_izpghcu4/
|   |-- instagram_research_test_k6rce6te/
|   |-- instagram_research_test_ktbyxpmf/
|   |-- instagram_research_test_m3kelqu9/
|   |-- instagram_research_test_n3ifvy3r/
|   |-- instagram_research_test_pmgs5_6u/
|   |-- instagram_research_test_sll3urmg/
|   |-- instagram_research_test_u_kr6k4x/
|   |-- instagram_research_test_w984co06/
|   |-- instagram_research_test_wc3bx8gn/
|   |-- instagram_research_test_wszio36o/
|   |-- instagram_research_test_xhtiqg0w/
|   |-- instagram_research_test_xn1nffoi/
|   |-- instagram_research_test_ytgq0m9c/
|   `-- instagram_research_test_yu43wz70/
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
|   |-- RESEARCH/
|   |   |-- AlphaCut.md
|   |   |-- Claude_Codex_Workflow.md
|   |   `-- Claude_Instagram_Audit.md
|   |-- AI_PLANNER.md
|   |-- AI_RULES.md
|   |-- AUDIT_ENGINE.md
|   |-- CLAUDE_SHORTS_PHASE_0_TASK.md
|   |-- COMPETITOR_ENGINE.md
|   |-- COST.md
|   |-- DEPLOYMENT.md
|   |-- DIRECTORY_STRUCTURE.md
|   |-- KNOWLEDGE_ENGINE.md
|   |-- MASTER_JSON.md
|   |-- MONETIZATION.md
|   |-- PROJECT_VISION.md
|   |-- RELEASE_RULE.md
|   |-- SHORTS_ARCHITECTURE_DRAFT.md
|   |-- SPRINT_01.md
|   |-- SYSTEM_ARCHITECTURE.md
|   |-- TECH_STACK.md
|   |-- TOPIC_ENGINE_SPEC.md
|   |-- WORK_CODEX_CAPABILITY_AUDIT.md
|   `-- WORKFLOW.md
|-- logs/
|   `-- README.md
|-- modules/
|   |-- ai_planner/
|   |   |-- __init__.py
|   |   |-- consumer_contract.py
|   |   |-- planner_consumer_adapter.py
|   |   |-- planner_contract.py
|   |   |-- planner_decision_engine.py
|   |   |-- planner_interface.py
|   |   |-- planner_module.py
|   |   |-- planning_context.py
|   |   `-- planning_result_schema.py
|   |-- analytics_engine/
|   |   |-- __init__.py
|   |   |-- analytics_engine_module.py
|   |   |-- analytics_history.py
|   |   |-- analytics_interface.py
|   |   |-- analytics_predictor.py
|   |   `-- analytics_storage.py
|   |-- audit_engine/
|   |   |-- __init__.py
|   |   |-- audit_checks.py
|   |   |-- audit_engine_module.py
|   |   |-- audit_history.py
|   |   |-- audit_interface.py
|   |   |-- audit_score.py
|   |   `-- audit_storage.py
|   |-- brand_dna_engine/
|   |   |-- __init__.py
|   |   |-- brand_dna_engine_module.py
|   |   |-- brand_dna_history.py
|   |   |-- brand_dna_interface.py
|   |   |-- brand_dna_storage.py
|   |   |-- brand_dna_tracker.py
|   |   `-- brand_profile_loader.py
|   |-- card_news/
|   |   |-- __init__.py
|   |   |-- card_news_module.py
|   |   |-- card_news_quality_checker.py
|   |   |-- card_news_text_optimizer.py
|   |   |-- debate_question_selector.py
|   |   |-- evidence_selector.py
|   |   |-- highlight_engine.py
|   |   |-- layout_rule_engine.py
|   |   |-- layout_selector.py
|   |   |-- mobile_readability_checker.py
|   |   |-- render_constants.py
|   |   |-- slide_designer.py
|   |   |-- social_proof_selector.py
|   |   |-- story_flow_planner.py
|   |   |-- typography_rules.py
|   |   `-- visual_rhythm_selector.py
|   |-- common/
|   |   |-- __init__.py
|   |   |-- metadata_standard.py
|   |   `-- service_diagnostic.py
|   |-- competitor_engine/
|   |   |-- __init__.py
|   |   |-- benchmark_source.py
|   |   |-- community_source.py
|   |   |-- competitor_engine_module.py
|   |   |-- competitor_history.py
|   |   |-- competitor_interface.py
|   |   |-- competitor_profile_builder.py
|   |   |-- competitor_storage.py
|   |   |-- instagram_benchmark_parser.py
|   |   |-- news_source.py
|   |   `-- tools_funnel_parser.py
|   |-- competitor_learning/
|   |   |-- __init__.py
|   |   |-- competitor_learning_dashboard.py
|   |   |-- competitor_learning_extractor.py
|   |   |-- competitor_learning_interface.py
|   |   |-- competitor_learning_module.py
|   |   |-- competitor_learning_score.py
|   |   |-- competitor_learning_statistics.py
|   |   `-- competitor_learning_storage.py
|   |-- content/
|   |   |-- brand_rule_evaluator.py
|   |   |-- content_duplicate_detector.py
|   |   |-- content_module.py
|   |   |-- content_output_normalizer.py
|   |   |-- content_output_validator.py
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
|   |-- image_strategy/
|   |   |-- __init__.py
|   |   |-- ai_image_decision.py
|   |   |-- content_type_classifier.py
|   |   |-- image_source_selector.py
|   |   `-- image_strategy_module.py
|   |-- instagram_research/
|   |   |-- __init__.py
|   |   |-- instagram_classifier.py
|   |   |-- instagram_normalizer.py
|   |   |-- instagram_post_schema.py
|   |   |-- instagram_research_interface.py
|   |   |-- instagram_statistics.py
|   |   `-- instagram_storage.py
|   |-- knowledge_engine/
|   |   |-- __init__.py
|   |   |-- duplicate_detector.py
|   |   |-- knowledge_classifier.py
|   |   |-- knowledge_extractor.py
|   |   |-- knowledge_history.py
|   |   |-- knowledge_index.py
|   |   |-- knowledge_interface.py
|   |   |-- knowledge_module.py
|   |   |-- knowledge_ranker.py
|   |   |-- knowledge_score.py
|   |   `-- knowledge_storage.py
|   |-- learning_engine/
|   |   |-- __init__.py
|   |   |-- content_performance_history.py
|   |   |-- learning_engine_module.py
|   |   |-- learning_history.py
|   |   |-- learning_interface.py
|   |   |-- learning_performance_analyzer.py
|   |   |-- learning_score.py
|   |   |-- learning_selector.py
|   |   `-- learning_storage.py
|   |-- pattern_engine/
|   |   |-- __init__.py
|   |   |-- cta_selector.py
|   |   |-- hook_selector.py
|   |   |-- layout_selector.py
|   |   |-- pattern_engine_module.py
|   |   |-- pattern_result_writer.py
|   |   `-- pattern_selector.py
|   |-- performance_score/
|   |   |-- __init__.py
|   |   |-- performance_score_calculator.py
|   |   |-- performance_score_history.py
|   |   |-- performance_score_interface.py
|   |   |-- performance_score_module.py
|   |   `-- performance_score_storage.py
|   |-- publishing/
|   |   |-- __init__.py
|   |   `-- publishing_module.py
|   |-- research/
|   |   |-- research_context_builder.py
|   |   |-- research_insight_generator.py
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
|   |   |-- bobaedream_collector.py
|   |   |-- fmkorea_collector.py
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
|   |-- trend_memory/
|   |   |-- __init__.py
|   |   |-- trend_memory_checker.py
|   |   |-- trend_memory_history.py
|   |   |-- trend_memory_interface.py
|   |   |-- trend_memory_module.py
|   |   `-- trend_memory_storage.py
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
|-- site/
|   |-- .next/
|   |   |-- cache/
|   |   |-- dev/
|   |   |-- diagnostics/
|   |   |-- server/
|   |   |-- static/
|   |   |-- types/
|   |   |-- app-path-routes-manifest.json
|   |   |-- build-manifest.json
|   |   |-- BUILD_ID
|   |   |-- export-marker.json
|   |   |-- fallback-build-manifest.json
|   |   |-- images-manifest.json
|   |   |-- next-minimal-server.js.nft.json
|   |   |-- next-server.js.nft.json
|   |   |-- package.json
|   |   |-- prerender-manifest.json
|   |   |-- required-server-files.js
|   |   |-- required-server-files.json
|   |   |-- routes-manifest.json
|   |   |-- trace
|   |   |-- trace-build
|   |   `-- turbopack
|   |-- .open-next/
|   |   |-- .build/
|   |   |-- assets/
|   |   |-- cache/
|   |   |-- cloudflare/
|   |   |-- cloudflare-templates/
|   |   |-- dynamodb-provider/
|   |   |-- middleware/
|   |   |-- server-functions/
|   |   `-- worker.js
|   |-- .openai/
|   |   `-- hosting.json
|   |-- app/
|   |   |-- commerce.css
|   |   |-- globals.css
|   |   |-- layout.js
|   |   |-- os.css
|   |   `-- page.js
|   |-- node_modules/
|   |   |-- .bin/
|   |   |-- @ast-grep/
|   |   |-- @aws/
|   |   |-- @aws-crypto/
|   |   |-- @aws-sdk/
|   |   |-- @cloudflare/
|   |   |-- @cspotcode/
|   |   |-- @dotenvx/
|   |   |-- @ecies/
|   |   |-- @esbuild/
|   |   |-- @img/
|   |   |-- @isaacs/
|   |   |-- @jridgewell/
|   |   |-- @next/
|   |   |-- @noble/
|   |   |-- @node-minify/
|   |   |-- @opennextjs/
|   |   |-- @poppinss/
|   |   |-- @sindresorhus/
|   |   |-- @smithy/
|   |   |-- @speed-highlight/
|   |   |-- @swc/
|   |   |-- @tsconfig/
|   |   |-- @types/
|   |   |-- abort-controller/
|   |   |-- accepts/
|   |   |-- acorn/
|   |   |-- agentkeepalive/
|   |   |-- ansi-colors/
|   |   |-- ansi-regex/
|   |   |-- ansi-styles/
|   |   |-- array-timsort/
|   |   |-- asynckit/
|   |   |-- aws4fetch/
|   |   |-- balanced-match/
|   |   |-- baseline-browser-mapping/
|   |   |-- blake3-wasm/
|   |   |-- body-parser/
|   |   |-- bowser/
|   |   |-- brace-expansion/
|   |   |-- buffer-from/
|   |   |-- bytes/
|   |   |-- call-bind-apply-helpers/
|   |   |-- call-bound/
|   |   |-- caniuse-lite/
|   |   |-- chalk/
|   |   |-- ci-info/
|   |   |-- client-only/
|   |   |-- cliui/
|   |   |-- cloudflare/
|   |   |-- combined-stream/
|   |   |-- commander/
|   |   |-- comment-json/
|   |   |-- content-disposition/
|   |   |-- content-type/
|   |   |-- cookie/
|   |   |-- cookie-signature/
|   |   |-- cross-spawn/
|   |   |-- debug/
|   |   |-- delayed-stream/
|   |   |-- depd/
|   |   |-- detect-libc/
|   |   |-- dotenv/
|   |   |-- dunder-proto/
|   |   |-- duplexer/
|   |   |-- eciesjs/
|   |   |-- ee-first/
|   |   |-- emoji-regex/
|   |   |-- encodeurl/
|   |   |-- enquirer/
|   |   |-- error-stack-parser-es/
|   |   |-- es-define-property/
|   |   |-- es-errors/
|   |   |-- es-object-atoms/
|   |   |-- es-set-tostringtag/
|   |   |-- esbuild/
|   |   |-- escalade/
|   |   |-- escape-html/
|   |   |-- esprima/
|   |   |-- etag/
|   |   |-- event-target-shim/
|   |   |-- execa/
|   |   |-- express/
|   |   |-- fdir/
|   |   |-- finalhandler/
|   |   |-- foreground-child/
|   |   |-- form-data/
|   |   |-- form-data-encoder/
|   |   |-- formdata-node/
|   |   |-- forwarded/
|   |   |-- fresh/
|   |   |-- fs.realpath/
|   |   |-- function-bind/
|   |   |-- get-caller-file/
|   |   |-- get-east-asian-width/
|   |   |-- get-intrinsic/
|   |   |-- get-proto/
|   |   |-- get-stream/
|   |   |-- glob/
|   |   |-- gopd/
|   |   |-- gzip-size/
|   |   |-- has-symbols/
|   |   |-- has-tostringtag/
|   |   |-- hasown/
|   |   |-- http-errors/
|   |   |-- human-signals/
|   |   |-- humanize-ms/
|   |   |-- iconv-lite/
|   |   |-- ignore/
|   |   |-- inherits/
|   |   |-- ipaddr.js/
|   |   |-- is-promise/
|   |   |-- is-stream/
|   |   |-- isexe/
|   |   |-- jackspeak/
|   |   |-- kleur/
|   |   |-- lru-cache/
|   |   |-- math-intrinsics/
|   |   |-- media-typer/
|   |   |-- merge-descriptors/
|   |   |-- merge-stream/
|   |   |-- mime-db/
|   |   |-- mime-types/
|   |   |-- mimic-fn/
|   |   |-- miniflare/
|   |   |-- minimatch/
|   |   |-- minipass/
|   |   |-- mkdirp/
|   |   |-- mnemonist/
|   |   |-- ms/
|   |   |-- nanoid/
|   |   |-- negotiator/
|   |   |-- next/
|   |   |-- node-domexception/
|   |   |-- node-fetch/
|   |   |-- npm-run-path/
|   |   |-- object-inspect/
|   |   |-- object-treeify/
|   |   |-- obliterator/
|   |   |-- on-finished/
|   |   |-- once/
|   |   |-- onetime/
|   |   |-- package-json-from-dist/
|   |   |-- parseurl/
|   |   |-- path-key/
|   |   |-- path-scurry/
|   |   |-- path-to-regexp/
|   |   |-- pathe/
|   |   |-- picocolors/
|   |   |-- picomatch/
|   |   |-- postcss/
|   |   |-- proxy-addr/
|   |   |-- qs/
|   |   |-- range-parser/
|   |   |-- raw-body/
|   |   |-- react/
|   |   |-- react-dom/
|   |   |-- router/
|   |   |-- safer-buffer/
|   |   |-- scheduler/
|   |   |-- semver/
|   |   |-- send/
|   |   |-- serve-static/
|   |   |-- setprototypeof/
|   |   |-- sharp/
|   |   |-- shebang-command/
|   |   |-- shebang-regex/
|   |   |-- side-channel/
|   |   |-- side-channel-list/
|   |   |-- side-channel-map/
|   |   |-- side-channel-weakmap/
|   |   |-- signal-exit/
|   |   |-- source-map/
|   |   |-- source-map-js/
|   |   |-- source-map-support/
|   |   |-- statuses/
|   |   |-- string-width/
|   |   |-- strip-ansi/
|   |   |-- strip-final-newline/
|   |   |-- styled-jsx/
|   |   |-- supports-color/
|   |   |-- terser/
|   |   |-- toidentifier/
|   |   |-- tr46/
|   |   |-- ts-tqdm/
|   |   |-- tslib/
|   |   |-- type-is/
|   |   |-- undici/
|   |   |-- undici-types/
|   |   |-- unenv/
|   |   |-- unpipe/
|   |   |-- urlpattern-polyfill/
|   |   |-- vary/
|   |   |-- web-streams-polyfill/
|   |   |-- webidl-conversions/
|   |   |-- whatwg-url/
|   |   |-- which/
|   |   |-- workerd/
|   |   |-- wrangler/
|   |   |-- wrap-ansi/
|   |   |-- wrappy/
|   |   |-- ws/
|   |   |-- y18n/
|   |   |-- yaml/
|   |   |-- yargs/
|   |   |-- yargs-parser/
|   |   |-- youch/
|   |   |-- youch-core/
|   |   `-- .package-lock.json
|   |-- .gitignore
|   |-- next.config.mjs
|   |-- open-next.config.ts
|   |-- package-lock.json
|   |-- package.json
|   `-- wrangler.jsonc
|-- src/
|   |-- llm_client.py
|   |-- main.py
|   |-- README.md
|   `-- workflow_engine.py
|-- storage/
|   |-- _instagram_research_test_tmp/
|   |   |-- tmp0y7jcb_i/
|   |   |-- tmp1x56c8__/
|   |   |-- tmp63alc08a/
|   |   |-- tmp6hhsj8cl/
|   |   |-- tmp7yjyjzif/
|   |   |-- tmp9w9ospx4/
|   |   |-- tmpaiubjq1c/
|   |   |-- tmpb_1v5tab/
|   |   |-- tmpc0nd1emr/
|   |   |-- tmpckhayk02/
|   |   |-- tmpeahkksku/
|   |   |-- tmpfecn_ja5/
|   |   |-- tmpfiwyww8j/
|   |   |-- tmpg45ljmgu/
|   |   |-- tmpgrhezw1r/
|   |   |-- tmphj2tvjq0/
|   |   |-- tmphlhg9mse/
|   |   |-- tmphn23aem5/
|   |   |-- tmphs5ehbc_/
|   |   |-- tmpi1tcrgks/
|   |   |-- tmpkh_uoix8/
|   |   |-- tmpl_mt7wa2/
|   |   |-- tmpmlennkgx/
|   |   |-- tmpmnufmiea/
|   |   |-- tmpnla3jmqn/
|   |   |-- tmpnloen1ja/
|   |   |-- tmpnn3d54_o/
|   |   |-- tmpovxojy08/
|   |   |-- tmppraqcaha/
|   |   |-- tmpps50m436/
|   |   |-- tmppu08uhrz/
|   |   |-- tmpq4gm16hm/
|   |   |-- tmpqpwc_kn3/
|   |   |-- tmpqtmuimn2/
|   |   |-- tmprjt5t2jz/
|   |   |-- tmprp4q1_um/
|   |   |-- tmps0ijghur/
|   |   |-- tmps3tab9an/
|   |   |-- tmps45iyd5y/
|   |   |-- tmpsb_exl9a/
|   |   |-- tmpsrnwdnuq/
|   |   |-- tmpsyiz70pc/
|   |   |-- tmpt3jlgxie/
|   |   |-- tmptook7i6x/
|   |   |-- tmpu2smcjoy/
|   |   |-- tmpuoau7nvi/
|   |   |-- tmpvqpy8cc2/
|   |   |-- tmpvw8a1z1o/
|   |   |-- tmpwuctwqgu/
|   |   |-- tmpx61s7b7p/
|   |   |-- tmpxcv781sw/
|   |   |-- tmpy5w79mxh/
|   |   |-- tmpysz08mfe/
|   |   |-- tmpyxwvate4/
|   |   `-- tmpzknm_wty/
|   |-- analytics/
|   |   |-- analytics_history.json
|   |   |-- analytics_result.json
|   |   `-- analytics_statistics.json
|   |-- audit/
|   |   |-- audit_history.json
|   |   |-- audit_result.json
|   |   `-- audit_statistics.json
|   |-- brand_dna/
|   |   |-- brand_dna.json
|   |   |-- brand_dna_history.json
|   |   `-- brand_dna_statistics.json
|   |-- cache/
|   |   |-- .gitkeep
|   |   |-- bobaedream_cache.json
|   |   |-- fmkorea_cache.json
|   |   |-- nate_pann_cache.json
|   |   `-- naver_news_cache.json
|   |-- card_news/
|   |   `-- (5 runtime file(s) omitted; gitignored, see .gitignore)
|   |-- competitor/
|   |   |-- competitor_history.json
|   |   |-- competitor_profile.json
|   |   |-- competitor_profiles.json
|   |   `-- competitor_statistics.json
|   |-- content/
|   |   `-- (1 runtime file(s) omitted; gitignored, see .gitignore)
|   |-- dashboard/
|   |   `-- daily_learning_report.json
|   |-- generated_images/
|   |   `-- (4 runtime file(s) omitted; gitignored, see .gitignore)
|   |-- history/
|   |   |-- .gitkeep
|   |   `-- content_performance_history.json
|   |-- image_strategy/
|   |   `-- image_strategy_result.json
|   |-- images/
|   |   `-- (4 runtime file(s) omitted; gitignored, see .gitignore)
|   |-- knowledge/
|   |   |-- competitor_learning_history.json
|   |   |-- competitor_statistics.json
|   |   |-- cta_statistics.json
|   |   |-- hook_statistics.json
|   |   |-- knowledge.json
|   |   |-- knowledge_database.json
|   |   |-- knowledge_history.json
|   |   |-- knowledge_index.json
|   |   |-- knowledge_statistics.json
|   |   |-- layout_statistics.json
|   |   `-- pattern_statistics.json
|   |-- learning/
|   |   |-- learning_history.json
|   |   |-- learning_memory.json
|   |   `-- learning_statistics.json
|   |-- llm_logs/
|   |   `-- (427 runtime file(s) omitted; gitignored, see .gitignore)
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
|   |-- performance_score/
|   |   |-- performance_score.json
|   |   |-- performance_score_history.json
|   |   `-- performance_score_statistics.json
|   |-- planner/
|   |   `-- .gitkeep
|   |-- publishing/
|   |   |-- caption.txt
|   |   |-- hashtags.txt
|   |   |-- publish_queue.json
|   |   `-- publishing_result.json
|   |-- research/
|   |   |-- instagram/
|   |   `-- research_result.json
|   |-- runtime/
|   |   `-- service_diagnostic.json
|   |-- topics/
|   |   |-- .gitkeep
|   |   `-- topic_result.json
|   |-- trend_memory/
|   |   |-- trend_memory.json
|   |   `-- trend_memory_history.json
|   |-- trends/
|   |   |-- snapshots/
|   |   |   `-- (72 runtime file(s) omitted; gitignored, see .gitignore)
|   |   |-- .gitkeep
|   |   |-- collector_statistics.json
|   |   |-- last_safe_trend_result.json
|   |   |-- selected_topic.json
|   |   |-- source_health.json
|   |   |-- trend_engine_status.json
|   |   |-- trend_result.json
|   |   `-- trend_run_log.jsonl
|   |-- workflow_results/
|   |   `-- (39 runtime file(s) omitted; gitignored, see .gitignore)
|   `-- README.md
|-- templates/
|   |-- card_news_layout_rules.json
|   |-- card_news_template.json
|   `-- publishing_template.json
|-- tests/
|   |-- test_ai_planner_consumer_adapter.py
|   |-- test_ai_planner_consumer_contract.py
|   |-- test_ai_planner_context.py
|   |-- test_ai_planner_contract.py
|   |-- test_ai_planner_decision_engine.py
|   |-- test_ai_planner_module.py
|   |-- test_ai_planner_schema.py
|   |-- test_card_news_production_quality.py
|   |-- test_competitor_learning_dashboard.py
|   |-- test_competitor_learning_extractor.py
|   |-- test_competitor_learning_interface.py
|   |-- test_competitor_learning_module.py
|   |-- test_competitor_learning_score.py
|   |-- test_competitor_learning_statistics.py
|   |-- test_competitor_learning_storage.py
|   |-- test_competitor_learning_wiring.py
|   |-- test_content_intelligence_helpers.py
|   |-- test_content_output_normalizer.py
|   |-- test_content_output_validator.py
|   |-- test_content_prompt_builder.py
|   |-- test_instagram_intelligence_risk_checks.py
|   |-- test_instagram_research_classifier.py
|   |-- test_instagram_research_independence.py
|   |-- test_instagram_research_interface.py
|   |-- test_instagram_research_normalizer.py
|   |-- test_instagram_research_schema.py
|   |-- test_instagram_research_statistics.py
|   |-- test_instagram_research_storage.py
|   |-- test_intelligence_feedback_safety.py
|   `-- test_workflow_planner_integration.py
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
|-- CTO_BRAIN.md
|-- CURRENT_TASK.md
|-- DECISIONS.md
|-- DIRECTORY_STRUCTURE.md
|-- ig_test_output.txt
|-- MODULE_SPEC.md
|-- MODULE_STATUS.md
|-- PROJECT_BIBLE.md
|-- PROJECT_MASTER.md
|-- PROJECT_OPERATING_SYSTEM.md
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
