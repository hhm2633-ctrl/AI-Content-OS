# AI-Content-OS Project Snapshot

Updated at: 2026-07-22 (full regression closure)

## Execution Command

```powershell
py -m src.main
```

Do not use `python -m src.main` for this project.

## 2026-07-22 Production Safety Status

- Staged local entrypoints now connect existing daily collection data to multi-account discovery and owner review, then connect an explicit owner-selected queue to deep discovery, final 1-20 slide planning, approval-gated packaging, Controller rendering, automatic evidence QA, and explicit owner visual approval.
- Controller initialization rejects pending/unapproved production packages. Automatic OCR/OpenCLIP evidence cannot be accepted as owner visual approval, and final batch readiness retains owner visual receipt IDs and hashes.
- This is current code/test evidence only: compile and all 2,601 unit/regression tests passed. No real candidate deep fetch, authorized production render, publish, external write, or automation resume was performed.

- Standard Workflow remains available for planning/learning and can finish `workflow_completed`, but now emits blocked CardNews and publishing results unless controller authorization is supplied through the controlled production path.
- Unapproved standard execution performs zero image API calls and zero CardNews renders.
- Image generation authorization requires a future timezone-aware expiry, authorization ID, candidate ID, approver, controller-state hash, and `image_generation` scope.
- Production packages cannot become ready from synthesized/default approval data. Explicit owner-bound approval receipts are mandatory.
- Variable-slide production contract is 1-20 slides. Shallow planning preserves explicit/content signals, and selected-candidate production derives the final count from completed copy and usable media without silent truncation.
- Variable-slide production path: approved package -> controller -> Satori/resvg -> automatic local OCR/OpenCLIP evidence QA -> owner visual approval pending.
- Automatic visual QA is evidence only and cannot set owner approval, manual-upload readiness, publishing readiness, or actual publish state.
- Sentence Transformers is operationally connected to same-event clustering. Intel XPU is probe-only; SeaweedFS, Mixpost, and TryPost remain outside the critical path/reference-only.
- Safe final QA: `py -m compileall src modules scripts` passed; `py -m unittest discover -s tests -v` passed all 2,601 tests in 527.437 seconds.
- Research claims now require an exact non-fallback source/topic/item-URL match. MoneyToday manager routing, news profiles, and Account C editorial capability metadata are synchronized.
- Commerce approval remains fail-closed and target-bound. Brand Connect local catalog matching removes pack/size slot duplication without issuing links or performing external writes.
- Full `py -m src.main` was intentionally not re-run after this gate change because other modules may call external LLM APIs. No real authorized post-change render or publish was performed.

The stored workflow result below predates this final gate integration and is historical evidence, not proof of the current authorized production path.

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
- Image prompt generation: image_prompts_created
- Image generation: image_generation_completed
- Card news rendering: card_news_completed
- Publishing preparation: publishing_blocked
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
|   `-- skills/
|       |-- cto_operating_system/
|       `-- domain/
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
|   |   |-- context-efficiency/
|   |   |-- cto_operating_system/
|   |   |-- domain/
|   |   |-- graphify/
|   |   |-- architecture.md
|   |   |-- competitor_analysis.md
|   |   |-- content_roi.md
|   |   |-- image_strategy.md
|   |   |-- large_implementation.md
|   |   |-- planning.md
|   |   |-- refactoring.md
|   |   |-- research.md
|   |   `-- review.md
|   |-- worktrees/
|   |   |-- cardnews-topic-intelligence-v1/
|   |   |-- community-metrics-parser-v1/
|   |   |-- design-learning-import-v1/
|   |   |-- naver-news-parser-recovery/
|   |   |-- ruliweb-dogdrip-collectors/
|   |   |-- source-intake-v1/
|   |   `-- tender-soaring-seahorse/
|   |-- CLAUDE.md
|   |-- settings.json
|   `-- settings.local.json
|-- .codex/
|   |-- hooks/
|   |   |-- active_locks.json
|   |   |-- OWNER_OPERATING_CONTRACT.md
|   |   |-- pre_tool_use_guard.py
|   |   |-- README.md
|   |   `-- session_context.py
|   |-- skills/
|   |   |-- ai-content-os-card-news/
|   |   |-- ai-content-os-commit-check/
|   |   |-- ai-content-os-coupang/
|   |   |-- ai-content-os-cto-review/
|   |   |-- ai-content-os-dev/
|   |   |-- ai-content-os-doc-update/
|   |   |-- ai-content-os-instagram/
|   |   |-- ai-content-os-knowledge-intelligence/
|   |   |-- ai-content-os-publishing/
|   |   |-- ai-content-os-qa/
|   |   |-- ai-content-os-research/
|   |   |-- ai-content-os-research-intelligence/
|   |   |-- ai-content-os-retry-audit/
|   |   |-- ai-content-os-shorts/
|   |   |-- ai-content-os-sprint/
|   |   |-- ai-content-os-sprint-manager/
|   |   |-- ai-content-os-trend-collector/
|   |   `-- graphify/
|   |-- config.toml
|   `-- hooks.json
|-- .codex-remote-attachments/
|   |-- 019f5976-886d-7022-bbad-4230358aabac/
|   |   |-- 0668c370-70b9-4f9d-bec3-c26c57d424b8/
|   |   |-- 270ab293-40be-4029-af66-d1c8d85b8b57/
|   |   |-- 2f1ea6f5-b751-4482-a232-ee1f04a71ee8/
|   |   |-- 9f96287b-9e33-4e6f-a6f4-62a075fb9135/
|   |   `-- b261373c-a05e-4d60-9696-b1bd6e180cb9/
|   `-- 019f6d56-6303-7f22-b280-64073d7b4747/
|       |-- 6a7d4410-53ca-4e92-b8a5-701ccd5793fb/
|       `-- a65c2720-8071-459e-ab48-63cb32cc3766/
|-- .codex-test-tmp/
|   |-- card_news_render_test_jv0ik8c3/
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
|   |-- evidence_selector_test_2pnlumlf/
|   |-- evidence_selector_test_4j2omq3s/
|   |-- evidence_selector_test__zaci1mz/
|   |-- evidence_selector_test_emtgckup/
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
|   |-- knowledge_query_12lsx5b9/
|   |-- knowledge_query_34voqt_w/
|   |-- knowledge_query_34wewpbq/
|   |-- knowledge_query_36avm6yu/
|   |-- knowledge_query_3d2blwn0/
|   |-- knowledge_query_3tcwfv39/
|   |-- knowledge_query_4ava_rrf/
|   |-- knowledge_query_4wzlmv7e/
|   |-- knowledge_query_5_i698ts/
|   |-- knowledge_query_5h2tubwt/
|   |-- knowledge_query_6ljt2y0y/
|   |-- knowledge_query_7o2bk9j7/
|   |-- knowledge_query_7zqjxvsa/
|   |-- knowledge_query_8pl_ug9j/
|   |-- knowledge_query_9hgh10rs/
|   |-- knowledge_query_9r4be61r/
|   |-- knowledge_query_9xqpwkoe/
|   |-- knowledge_query__75sgxz0/
|   |-- knowledge_query__q3da527/
|   |-- knowledge_query__y8rfxpa/
|   |-- knowledge_query_b47aun12/
|   |-- knowledge_query_b8y98u_9/
|   |-- knowledge_query_bwzgf_lx/
|   |-- knowledge_query_epqad6_y/
|   |-- knowledge_query_f1043qtp/
|   |-- knowledge_query_fbit0dy7/
|   |-- knowledge_query_fcppsvub/
|   |-- knowledge_query_fsqb19y7/
|   |-- knowledge_query_iofrnmp4/
|   |-- knowledge_query_jmw6qrmz/
|   |-- knowledge_query_kpvvsam4/
|   |-- knowledge_query_kt8z73v6/
|   |-- knowledge_query_ms7o0v8i/
|   |-- knowledge_query_n6rziu7u/
|   |-- knowledge_query_nb31n4fi/
|   |-- knowledge_query_nf3a9e8r/
|   |-- knowledge_query_o8yuftox/
|   |-- knowledge_query_oi1xovty/
|   |-- knowledge_query_p9x80lfq/
|   |-- knowledge_query_pii7g2yg/
|   |-- knowledge_query_qwt7a3xw/
|   |-- knowledge_query_ru0dw57w/
|   |-- knowledge_query_ts1hwj1c/
|   |-- knowledge_query_wch7xbjy/
|   |-- knowledge_query_weuzfel9/
|   |-- knowledge_query_wnia5uu1/
|   |-- knowledge_query_yed378rz/
|   |-- knowledge_query_ztx10_ro/
|   |-- risk_a_test_6pkek_yp/
|   |-- risk_a_test_7skf5vq5/
|   |-- risk_a_test_he5myoss/
|   |-- risk_a_test_nbkp36n2/
|   |-- risk_a_test_xicm38b3/
|   |-- risk_c_test_70hjhdgt/
|   |-- risk_c_test_angcm8_g/
|   |-- risk_c_test_o1tp8qtc/
|   |-- risk_e_test_7qtbq3rk/
|   |-- risk_f_test_mxx796h7/
|   |-- tmp0a7nxccr/
|   |-- tmp0cx1svuo/
|   |-- tmp0i6r8guk/
|   |-- tmp14q6_m_l/
|   |-- tmp4os95fqg/
|   |-- tmp538qoh9b/
|   |-- tmp67x61xu6/
|   |-- tmp68ufgr__/
|   |-- tmp_4usidue/
|   |-- tmpanw1anbq/
|   |-- tmpbd_mprli/
|   |-- tmpelzv4522/
|   |-- tmpfalzhwhb/
|   |-- tmpgeos8_qo/
|   |-- tmpipa7u86_/
|   |-- tmpjkqiffrn/
|   |-- tmppm1m5stj/
|   |-- tmpqju1gmay/
|   |-- tmpqqu0g9oi/
|   |-- tmpqs962g8p/
|   |-- tmprwoh4vpq/
|   |-- tmpsy_u5cxu/
|   |-- tmpsyzqeh71/
|   |-- tmpvibg4jtd/
|   |-- tmpw6e9xmwg/
|   |-- tmpx0akgphw/
|   `-- tmpx4uthub2/
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
|   |-- console-2026-07-14T19-24-37-637Z.log
|   |-- console-2026-07-14T19-24-58-411Z.log
|   |-- console-2026-07-15T01-38-12-952Z.log
|   |-- console-2026-07-15T01-38-46-678Z.log
|   |-- console-2026-07-17T05-26-07-508Z.log
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
|   |-- page-2026-07-10T12-04-59-417Z.yml
|   |-- page-2026-07-14T19-24-37-863Z.yml
|   |-- page-2026-07-14T19-24-40-655Z.yml
|   |-- page-2026-07-14T19-24-45-676Z.yml
|   |-- page-2026-07-14T19-24-48-428Z.yml
|   |-- page-2026-07-14T19-24-58-739Z.yml
|   |-- page-2026-07-15T01-37-32-949Z.yml
|   |-- page-2026-07-15T01-37-53-555Z.yml
|   |-- page-2026-07-15T01-38-17-007Z.yml
|   |-- page-2026-07-15T01-38-47-079Z.yml
|   |-- page-2026-07-15T01-39-54-723Z.yml
|   |-- page-2026-07-17T05-26-10-177Z.yml
|   |-- page-2026-07-17T05-26-54-152Z.yml
|   |-- page-2026-07-17T05-27-35-362Z.yml
|   `-- page-2026-07-17T05-27-47-584Z.yml
|-- .tmp/
|-- .tmp-amazon-cli-audit/
|   |-- .gitignore
|   |-- amazon-cli.py
|   |-- LICENSE
|   `-- README.md
|-- .tmp_test_workspace/
|-- artifacts/
|   |-- agent_console_v1/
|   |   |-- adapter_receipts/
|   |   |-- contexts/
|   |   |-- handoffs/
|   |   |-- spark_host/
|   |   |-- spark_work/
|   |   |-- index.html
|   |   `-- state.json
|   |-- brandconnect_relation_learning_2026-07-18/
|   |   |-- beauty_relations.jsonl
|   |   |-- beauty_report.json
|   |   |-- beauty_story_relations.jsonl
|   |   |-- beauty_story_report.json
|   |   |-- fashion_relations.jsonl
|   |   |-- fashion_report.json
|   |   |-- fashion_story_relations.jsonl
|   |   |-- fashion_story_report.json
|   |   |-- lifestyle_relations.jsonl
|   |   |-- lifestyle_report.json
|   |   |-- lifestyle_story_relations.jsonl
|   |   `-- lifestyle_story_report.json
|   |-- cardnews_category_review_2026-07-17/
|   |   |-- account_a/
|   |   |-- account_b/
|   |   |-- account_c/
|   |   |-- desktop_gallery_preview.png
|   |   |-- index.html
|   |   `-- REVIEW_GUIDE.md
|   |-- cardnews_category_review_2026-07-17_v2/
|   |   |-- account_a_gibraltar/
|   |   |-- account_b_salon/
|   |   |-- account_c_dior/
|   |   |-- account_c_valentino/
|   |   |-- assets/
|   |   |-- build_gallery_v2.py
|   |   |-- index.html
|   |   `-- REVIEW_GUIDE.md
|   |-- cardnews_category_review_2026-07-17_v3/
|   |   |-- account_a_gibraltar/
|   |   |-- account_b_salon/
|   |   |-- account_c_dior/
|   |   |-- account_c_valentino/
|   |   |-- inputs/
|   |   |-- build_gallery_v3.py
|   |   |-- collection.json
|   |   |-- collection_review.html
|   |   |-- desktop_gallery_preview.png
|   |   `-- index.html
|   |-- cardnews_category_review_2026-07-17_v4/
|   |   |-- build_latest_collection.py
|   |   `-- collection.json
|   |-- cardnews_category_review_2026-07-19/
|   |   |-- collection.json
|   |   |-- commerce_story_hair.json
|   |   |-- commerce_story_skincare.json
|   |   |-- commerce_story_travel.json
|   |   |-- fragment_A.json
|   |   |-- fragment_B.json
|   |   |-- fragment_C.json
|   |   |-- independent_selection_A.json
|   |   |-- independent_selection_B.json
|   |   |-- independent_selection_C.json
|   |   |-- site-dev.err.log
|   |   `-- site-dev.log
|   |-- cardnews_motion_review_2026-07-17/
|   |   |-- dior_summer_2027_motion_01.mp4
|   |   |-- dior_summer_2027_motion_01.source.json
|   |   |-- dior_summer_2027_motion_01_preview.jpg
|   |   `-- index.html
|   |-- cardnews_no_video_samples_2026-07-17/
|   |   |-- dior/
|   |   |-- news/
|   |   |-- index.html
|   |   `-- manifest.json
|   |-- cardnews_preupload_2026-07-19/
|   |   `-- fragments/
|   |-- cardnews_production_packages/
|   |   |-- repair_inputs/
|   |   |-- repair_reviews/
|   |   |-- 20260717-2003-A-1257fdf5c746.json
|   |   |-- 20260717-2003-A-224828787208.json
|   |   |-- 20260717-2003-A-23652dc036e9.json
|   |   |-- 20260717-2003-A-4a4409ce4870.json
|   |   |-- 20260717-2003-A-54b45bfb6a07.json
|   |   |-- 20260717-2003-B-09d90bf39746.json
|   |   |-- 20260717-2003-B-1306f34dbbf1.json
|   |   |-- 20260717-2003-B-19e90e52b9f1.json
|   |   |-- 20260717-2003-B-3f823ec8a5ea.json
|   |   |-- 20260717-2003-C-04a43f508b99.json
|   |   |-- 20260717-2003-C-145cd25e7107.json
|   |   |-- 20260717-2003-C-52419867f5a5.json
|   |   |-- 20260717-2003-C-6c2dc4c716b5.json
|   |   |-- 20260717-2003-C-b220caa2019b.json
|   |   |-- latest.json
|   |   `-- quality_loop_receipt.json
|   |-- cardnews_prototypes/
|   |   `-- 2026-07-16/
|   |-- cardnews_style_review_2026-07-17/
|   |   `-- account_b/
|   |-- comment_auto_detect_only/
|   |   |-- comment_auto_detect_01.png
|   |   |-- comment_auto_detect_02.png
|   |   `-- comment_auto_detect_03.png
|   |-- fabric_single/
|   |   `-- fabric_single_20260719-B-f7c153fdfe11.png
|   |-- instagram_learning/
|   |   `-- 2026-07-17/
|   |-- integration_audits/
|   |   `-- cardnews_pipeline_post_connection_claude.json
|   |-- rembg_alpha_bbox_stage1/
|   |   |-- bbox_preview_summary.json
|   |   |-- dior_runway_01_bbox_overlay.png
|   |   |-- dior_runway_01_rembg.png
|   |   |-- dior_runway_13_bbox_overlay.png
|   |   |-- dior_runway_13_rembg.png
|   |   |-- dior_runway_18_bbox_overlay.png
|   |   `-- dior_runway_18_rembg.png
|   |-- stage3_subject_crop_guard/
|   |   |-- dior_runway_01_bad_left_crop.png
|   |   |-- dior_runway_01_near_fail.png
|   |   |-- dior_runway_01_near_pass.png
|   |   |-- dior_runway_01_original.png
|   |   |-- dior_runway_13_bad_left_crop.png
|   |   |-- dior_runway_13_near_fail.png
|   |   |-- dior_runway_13_near_pass.png
|   |   |-- dior_runway_13_original.png
|   |   |-- dior_runway_18_bad_left_crop.png
|   |   |-- dior_runway_18_near_fail.png
|   |   |-- dior_runway_18_near_pass.png
|   |   `-- dior_runway_18_original.png
|   |-- stage4_subject_crop_qa_test/
|   |   |-- manifest.json
|   |   |-- manifest2.json
|   |   |-- package.json
|   |   |-- package2.json
|   |   |-- qa_receipt.json
|   |   |-- qa_receipt2.json
|   |   |-- state.json
|   |   `-- state2.json
|   |-- codex_update_baseline_2026-07-17.json
|   `-- owner_review_workspace_2026-07-17.png
|-- benchmark/
|   |-- AI_CONTENT_STRATEGY.md
|   |-- CONTENT_PATTERNS.md
|   |-- CTA_LIBRARY.md
|   |-- HOOK_LIBRARY.md
|   |-- INSTAGRAM_BENCHMARK.md
|   `-- TOOLS_AND_FUNNEL_REFERENCES.md
|-- config/
|   |-- commerce/
|   |   |-- approval.json
|   |   |-- marketplaces.json
|   |   `-- settings.json
|   |-- external_tools/
|   |   |-- agency_agents_local.json
|   |   |-- agent_runtime_adapter_probe_2026-07-18.json
|   |   |-- hyperframes_local.json
|   |   `-- local_media_pipeline.json
|   |-- account_c_fixed_ai_model.json
|   |-- account_c_fixed_ai_model_prompt_template.md
|   |-- brand_profile.json
|   |-- card_news_account_variable_slides.json
|   |-- cardnews_category_packages.json
|   |-- claude_session_checkpoint.json
|   |-- news_category_profiles.json
|   |-- publishing.json
|   |-- README.md
|   |-- settings.json
|   |-- source_data_storage.json
|   |-- source_intake_account_routing.json
|   |-- source_intake_account_top_selection.json
|   |-- source_intake_category_stage2.json
|   |-- source_intake_clustering.json
|   |-- source_intake_field_completeness.json
|   |-- source_intake_instagram_pattern_binding.json
|   |-- source_intake_reviewed_watch_promotion.json
|   |-- source_intake_risk_rules.json
|   |-- source_intake_sources.json
|   |-- source_intake_watch_review.json
|   |-- topic_engine.json
|   `-- trend_sources.json
|-- docs/
|   |-- RESEARCH/
|   |   |-- AFFILIATE/
|   |   |-- COMMERCE/
|   |   |-- MANUS/
|   |   |-- AlphaCut.md
|   |   |-- Claude_Codex_Workflow.md
|   |   |-- Claude_Instagram_Audit.md
|   |   |-- HALFDONE_AGENT_WORKFLOWS.md
|   |   |-- HALFDONE_AI_AVATAR_VIDEO_TOOLS.md
|   |   |-- HALFDONE_AI_VIDEO_CAMPAIGN_PIPELINE.md
|   |   |-- REELS_INTELLIGENCE_PRODUCT_OPPORTUNITY.md
|   |   |-- SHOPPING_SHORTFORM_STRATEGY_TECHNICAL_AUDIT.md
|   |   |-- TECHNICAL_REUSE_AGENT_TOOLING.md
|   |   |-- TECHNICAL_REUSE_IMAGE_VIDEO.md
|   |   |-- TECHNICAL_REUSE_MASTER_AUDIT.md
|   |   |-- TECHNICAL_REUSE_MONETIZATION_SAAS.md
|   |   |-- TECHNICAL_REUSE_REBORN_AUTOMATION_KIT.md
|   |   `-- TECHNICAL_REUSE_REBORN_PLAYBOOK.md
|   |-- ACTIVE_PARALLEL_WORK_ORDERS.md
|   |-- AFFILIATE_REVENUE_ROUTER_PHASE_1_CONTRACT.md
|   |-- AI_PLANNER.md
|   |-- AI_RULES.md
|   |-- AUDIT_ENGINE.md
|   |-- BRANDCONNECT_PHASE_1_CONTRACT.md
|   |-- CAMPAIGN_COMPLIANCE_PHASE_1_CONTRACT.md
|   |-- CARD_NEWS_EVIDENCE_INPUT_CONTRACT.md
|   |-- CARD_NEWS_RESULT_GALLERY_SPEC.md
|   |-- CARD_NEWS_SEMANTIC_QA_SPEC.md
|   |-- CARDNEWS_MULTI_ACCOUNT_DIRECTIVE.md
|   |-- CHANGE_REQUESTS_REFACTORING_CANDIDATES.md
|   |-- CLAUDE_SHORTS_PHASE_0_TASK.md
|   |-- COMMERCE_PHASE_1_CONTRACT.md
|   |-- COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md
|   |-- COMPETITOR_ENGINE.md
|   |-- CONTENT_AUTOMATION_HARNESS_ARCHITECTURE.md
|   |-- COST.md
|   |-- CTO_HANDOFF_2026-07-22.md
|   |-- CTO_LOCAL_TOOLCHAIN_HANDOFF_2026-07-22.md
|   |-- CURRENT_TASK_2026-07-19_CAPACITY_RECOVERY_NOTES.md
|   |-- DEPLOYMENT.md
|   |-- DIRECTORY_STRUCTURE.md
|   |-- EXTERNAL_ENGINE_PORTFOLIO_STRATEGY.md
|   |-- KNOWLEDGE_ENGINE.md
|   |-- MASTER_JSON.md
|   |-- MCP_ECOSYSTEM_EVALUATION.md
|   |-- MONETIZATION.md
|   |-- NEW_ENGINE_MODULE_PROPOSALS.md
|   |-- OPEN_SOURCE_RECOMMENDATIONS.md
|   |-- PERFORMANCE_OPTIMIZATION_CANDIDATES.md
|   |-- PROJECT_VISION.md
|   |-- RELEASE_RULE.md
|   |-- RESEARCH_INDEX.md
|   |-- SHORTS_ARCHITECTURE_DRAFT.md
|   |-- SHORTS_PHASE_2A_IMPLEMENTATION_SPEC.md
|   |-- SPRINT_01.md
|   |-- SYSTEM_ARCHITECTURE.md
|   |-- TECH_STACK.md
|   |-- TOPIC_ENGINE_SPEC.md
|   |-- TREND_SOURCE_RECOVERY_RUNBOOK.md
|   |-- WORK_CODEX_CAPABILITY_AUDIT.md
|   `-- WORKFLOW.md
|-- external_workclaude/
|   |-- blog_story_learning_20260715/
|   |   |-- BLOG_COPY_SLOT_CONTRACT.json
|   |   |-- EXAMPLE_VALUE_EXCLUSION.md
|   |   |-- NAVER_AI_STORY_PATTERN.md
|   |   |-- QA_REPORT.md
|   |   `-- SOURCE_BINDING.json
|   |-- cardnews_design_learning_20260715/
|   |   |-- DESIGN_PATTERN_MATRIX.md
|   |   |-- FOUR_SLIDE_ADAPTATION.md
|   |   |-- QA_REPORT.md
|   |   |-- ROLE_HANDOFFS.md
|   |   |-- SOURCE_CATALOG.json
|   |   `-- VERTICAL_FIT_MATRIX.md
|   |-- cardnews_experiments_v1/
|   |   |-- assets/
|   |   |-- rendered_exp2/
|   |   |-- EXPERIMENT_MATRIX.json
|   |   |-- METRIC_AND_DECISION_PLAN.md
|   |   |-- PATTERN_BINDINGS.json
|   |   |-- QA_REPORT.md
|   |   |-- render_exp2.py
|   |   `-- SIX_PRODUCTION_BRIEFS.md
|   |-- category_publish_package_v1/
|   |   |-- HANDOFF.md
|   |   `-- WORK_ORDER.md
|   |-- content_portfolio_v1/
|   |   |-- tools/
|   |   |-- ACCEPTANCE_MATRIX_V1_4.json
|   |   |-- ASSET_PROVENANCE_AUDIT_V1_6.md
|   |   |-- BATCH_HANDOFF_V1_3.md
|   |   |-- BATCH_HANDOFF_V1_3_1.md
|   |   |-- BLOCKER_REGISTER_V1_4.md
|   |   |-- CARDNEWS_COPY_BATCH_V1_3.md
|   |   |-- CARDNEWS_WORKFLOW_RC_V1_5.json
|   |   |-- CARDNEWS_WORKFLOW_RC_V1_5.md
|   |   |-- CHANNEL_STRATEGY.md
|   |   |-- CONTENT_BACKLOG.json
|   |   |-- CONTENT_BACKLOG.md
|   |   |-- CONTENT_INVENTORY.md
|   |   |-- CONTENT_QUALITY_AUDIT_V1_1.md
|   |   |-- CROSS_CHANNEL_CLUSTERS.json
|   |   |-- DUPLICATE_AND_OVERLAP_REPORT.md
|   |   |-- EVIDENCE_RED_TEAM_V1_3_1.md
|   |   |-- EVIDENCE_REQUIREMENTS.md
|   |   |-- HANDOFF.md
|   |   |-- IMAGE_SHOT_LIST_V1_3.md
|   |   |-- INSTAGRAM_COPY_BATCH_V1_3.md
|   |   |-- KNOWLEDGE_CONTENT_BATCH_V1_3.md
|   |   |-- LEARNING_PATTERN_AUDIT.md
|   |   |-- LEARNING_SEED_PATTERNS.json
|   |   |-- MANIFEST_PATH_FIX_V1_7.json
|   |   |-- MANIFEST_PATH_FIX_V1_7.md
|   |   |-- MONETIZATION_BOUNDARIES.md
|   |   |-- OPERATOR_REVIEW_CHECKLIST.md
|   |   |-- PRODUCTION_BATCH_V1_3.json
|   |   |-- PRODUCTION_BATCH_V1_3_1.json
|   |   |-- PRODUCTION_BRIEFS_V1_1.json
|   |   |-- PRODUCTION_SEQUENCE_V1_4.md
|   |   |-- PUBLISH_BLOCKER_AUDIT_V1_6.md
|   |   |-- PUBLISH_BLOCKER_MATRIX_V1_6.json
|   |   |-- QA_REPORT.md
|   |   |-- QA_REPORT_V1_1.md
|   |   |-- QA_REPORT_V1_2.md
|   |   |-- QA_REPORT_V1_3.md
|   |   |-- QA_REPORT_V1_3_1.md
|   |   |-- QA_REPORT_V1_4.md
|   |   |-- QA_REPORT_V1_4_1.md
|   |   |-- QA_REPORT_V1_6.md
|   |   |-- QA_REPORT_V1_7.md
|   |   |-- QA_REPORT_V1_8.md
|   |   |-- QA_REPORT_V1_8_1.md
|   |   |-- README.md
|   |   |-- RELEASE_BOUNDARY_MATRIX_V1_4_1.md
|   |   |-- RIGHTS_AND_ATTRIBUTION_MATRIX.md
|   |   |-- RIGHTS_INTAKE_ACCEPTANCE_MATRIX_V1_8_1.json
|   |   |-- RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8.json
|   |   |-- RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8_1.json
|   |   |-- RIGHTS_INTAKE_CONTRACT_V1_8.json
|   |   |-- RIGHTS_INTAKE_IMPLEMENTATION_HANDOFF_V1_8.md
|   |   |-- RIGHTS_INTAKE_OPERATOR_GUIDE_V1_8.md
|   |   |-- RIGHTS_INTAKE_RED_TEAM_V1_8_1.md
|   |   |-- RIGHTS_INTAKE_TEMPLATE.json
|   |   |-- RIGHTS_INTAKE_TEST_CONTRACT_V1_8_1.md
|   |   |-- SHORTS_SCRIPT_BATCH_V1_3.md
|   |   |-- SOURCE_ACQUISITION_QUEUE.md
|   |   |-- TEAM_HANDOFFS_V1_4.md
|   |   |-- TOP20_EVIDENCE_PACK.json
|   |   |-- TOP20_IMAGE_BRIEFS.md
|   |   |-- TOP20_PRIORITY.md
|   |   |-- TOP20_PRIORITY_V1_1.md
|   |   |-- USER_INPUT_REQUEST_V1_4.md
|   |   |-- USER_INPUT_REQUEST_V1_4_1.md
|   |   |-- WORK_ORDERS_V1_4.json
|   |   |-- WORK_ORDERS_V1_4_1.json
|   |   `-- WORKFLOW_CHANGED_FILES_V1_5.md
|   |-- instagram_broad_learning_v1/
|   |   |-- ACCOUNT_AND_CATEGORY_SAMPLE.json
|   |   |-- AUDIT_REPORT.md
|   |   |-- BROAD_LEARNING_REPORT.md
|   |   |-- CARDNEWS_FEATURE_TAXONOMY.json
|   |   |-- CTA_AND_EVIDENCE_PATTERNS.json
|   |   |-- ENGAGEMENT_BENCHMARKS.json
|   |   |-- HOOK_PATTERN_LIBRARY.json
|   |   |-- LEARNING_CANDIDATES.json
|   |   |-- QA_REPORT.md
|   |   |-- RAW_OBSERVATIONS.json
|   |   |-- STORY_STRUCTURE_LIBRARY.json
|   |   `-- VISUAL_LAYOUT_LIBRARY.json
|   |-- instagram_feed_discovery_v1/
|   |   |-- CLASSIFICATION.md
|   |   |-- PATTERN_ANALYSIS.md
|   |   |-- RAW_COLLECTION.md
|   |   `-- README.md
|   |-- instagram_feed_native_design_scan_v1/
|   |   |-- DESIGN_TREND_REPORT.md
|   |   |-- QA_REPORT.md
|   |   |-- RAW_FEED_TRIAGE.md
|   |   |-- README.md
|   |   |-- RECOVERY_MERGE_REPORT.md
|   |   `-- WORK_ORDER.md
|   |-- source_collection_engine_v0_claude/
|   |   |-- AUTO_CLAUDE_STATUS_NAVER_API_HUB.md
|   |   |-- AUTO_CLAUDE_STATUS_NAVER_NEWS_PARSER_RECOVERY.md
|   |   |-- AUTO_CLAUDE_STATUS_RULIWEB_DOGDRIP_IMPLEMENTATION.md
|   |   |-- CLAUDE_NAVER_NEWS_PARSER_RECOVERY_WORK_ORDER.md
|   |   `-- CLAUDE_RULIWEB_DOGDRIP_COLLECTOR_IMPLEMENTATION_WORK_ORDER.md
|   |-- source_collection_engine_v0_cto/
|   |   |-- CTO_BOBAEDREAM_VISIBLE_SUMMARY_WORK_ORDER.md
|   |   |-- CTO_COLLECTION_QUALITY_IMPLEMENTATION_WORK_ORDER.md
|   |   `-- CTO_PPOMPPU_COLLECTOR_IMPLEMENTATION_WORK_ORDER.md
|   |-- source_collection_engine_v0_spark/
|   |   |-- ARTIFACT_INDEX_HANDOFF.md
|   |   |-- artifact_index_last_message.txt
|   |   |-- AUTO_SPARK_EXEC_20260715-112331.log
|   |   |-- AUTO_SPARK_EXEC_20260715-112331.log.err
|   |   |-- AUTO_SPARK_EXEC_20260715-113317.log
|   |   |-- AUTO_SPARK_EXEC_20260715-115345.log
|   |   |-- AUTO_SPARK_LAST_20260715-115345.md
|   |   |-- AUTO_SPARK_STATUS_18_SOURCE_LIVE_SHALLOW_VALIDATION.md
|   |   |-- AUTO_SPARK_STATUS_20260714_204612.md
|   |   |-- AUTO_SPARK_STATUS_20260715_034054.md
|   |   |-- AUTO_SPARK_STATUS_20260715_034109.md
|   |   |-- AUTO_SPARK_STATUS_20260715_190742.md
|   |   |-- AUTO_SPARK_STATUS_20260715_190819.md
|   |   |-- AUTO_SPARK_STATUS_20260715_190853.md
|   |   |-- AUTO_SPARK_STATUS_20260715_191300.md
|   |   |-- AUTO_SPARK_STATUS_20260715_211200.md
|   |   |-- AUTO_SPARK_STATUS_20260715_213000.md
|   |   |-- AUTO_SPARK_STATUS_20260715_220315.md
|   |   |-- AUTO_SPARK_STATUS_20260715_223000.md
|   |   |-- AUTO_SPARK_STATUS_20260715_224012.md
|   |   |-- AUTO_SPARK_STATUS_20260715_224512.md
|   |   |-- AUTO_SPARK_STATUS_20260715_234501.md
|   |   |-- AUTO_SPARK_STATUS_20260715_235900.md
|   |   |-- AUTO_SPARK_STATUS_20260715_235959.md
|   |   |-- AUTO_SPARK_STATUS_20260715_235959_fix1.md
|   |   |-- AUTO_SPARK_STATUS_COLLECTOR_INJECTION_F.md
|   |   |-- AUTO_SPARK_STATUS_COMBINED_COLLECTOR_REGRESSION.md
|   |   |-- AUTO_SPARK_STATUS_COMBINED_COLLECTOR_REGRESSION_FINAL.md
|   |   |-- AUTO_SPARK_STATUS_COMBINED_COLLECTOR_REGRESSION_FINAL2.md
|   |   |-- AUTO_SPARK_STATUS_COMBINED_COLLECTOR_REGRESSION_POST_E.md
|   |   |-- AUTO_SPARK_STATUS_DCINSIDE_IMPLEMENTATION.md
|   |   |-- AUTO_SPARK_STATUS_EXECUTOR_LEAK_FIX_E.md
|   |   |-- AUTO_SPARK_STATUS_FMKOREA_VISIBLE_METRICS.md
|   |   |-- AUTO_SPARK_STATUS_ISOLATION_A.md
|   |   |-- AUTO_SPARK_STATUS_ISOLATION_B.md
|   |   |-- AUTO_SPARK_STATUS_ISOLATION_D.md
|   |   |-- AUTO_SPARK_STATUS_MONEYTODAY_EXECUTOR.md
|   |   |-- AUTO_SPARK_STATUS_MONEYTODAY_QA.md
|   |   |-- AUTO_SPARK_STATUS_READINESS_REFRESH.md
|   |   |-- AUTO_SPARK_STATUS_READINESS_REGISTRY.md
|   |   |-- AUTO_SPARK_STATUS_SOURCE_AGREEMENT.md
|   |   |-- AUTO_SPARK_STATUS_SOURCE_HEALTH_DASHBOARD.md
|   |   |-- AUTO_SPARK_STATUS_SOURCE_INTAKE_RC.md
|   |   |-- AUTO_SPARK_STATUS_TOPIC_CANDIDATE_PIPELINE.md
|   |   |-- AUTO_SPARK_STATUS_TOPIC_INPUT_ADAPTER.md
|   |   |-- AUTO_SPARK_STATUS_TOPIC_INPUT_QUALITY_GATE.md
|   |   |-- AUTO_SPARK_STATUS_YONHAP_IMPLEMENTATION.md
|   |   |-- BRIEF_HANDOFF.md
|   |   |-- brief_last_message.txt
|   |   |-- gap_last_message.txt
|   |   |-- GAP_REPORT_HANDOFF.md
|   |   |-- GAP_RUNNER_HANDOFF.md
|   |   |-- gap_runner_last_message.txt
|   |   |-- LANE_SUMMARY_HANDOFF.md
|   |   |-- lane_summary_last_message.txt
|   |   |-- LANE_SUMMARY_RUNNER_HANDOFF.md
|   |   |-- lane_summary_runner_last_message.txt
|   |   |-- last_message.txt
|   |   |-- RUNNER_HANDOFF.md
|   |   |-- runner_last_message.txt
|   |   |-- SOURCE_COLLECTION_ENGINE_V0_SPARK.md
|   |   |-- SPARK_18_SOURCE_LIVE_SHALLOW_VALIDATION_WORK_ORDER.md
|   |   |-- spark_artifact_index_exec.log
|   |   |-- spark_brief_exec.log
|   |   |-- SPARK_DCINSIDE_COLLECTOR_IMPLEMENTATION_WORK_ORDER.md
|   |   |-- SPARK_FMKOREA_VISIBLE_METRICS_CONTRACT_WORK_ORDER.md
|   |   |-- spark_gap_report_exec.log
|   |   |-- spark_gap_runner_exec.log
|   |   |-- SPARK_IMMEDIATE_20260714_204520.log
|   |   |-- spark_lane_summary_exec.log
|   |   |-- spark_lane_summary_runner_exec.log
|   |   |-- spark_runner_exec.log
|   |   |-- SPARK_SOURCE_AGREEMENT_IMPLEMENTATION_WORK_ORDER.md
|   |   |-- SPARK_SOURCE_HEALTH_DASHBOARD_WORK_ORDER.md
|   |   |-- SPARK_SOURCE_INTAKE_RC_WORK_ORDER.md
|   |   |-- spark_status_bundle_exec.log
|   |   |-- spark_work_order_generator_exec.log
|   |   |-- SPARK_YONHAP_COLLECTOR_IMPLEMENTATION_WORK_ORDER.md
|   |   |-- STATUS_BUNDLE_HANDOFF.md
|   |   |-- status_bundle_last_message.txt
|   |   |-- tmp_test_error.txt
|   |   |-- tmp_test_output.txt
|   |   |-- WORK_ORDER_GENERATOR_HANDOFF.md
|   |   `-- work_order_generator_last_message.txt
|   `-- source_collector_work_orders/
|       |-- 2026-07-14/
|       `-- 2026-07-15/
|-- external_workcodex/
|   `-- instagram_carousel_deep_learning_v1/
|       |-- CLAUDE_FABLE_REVIEW_WORK_ORDER.md
|       `-- CODEX_OBSERVATIONS.json
|-- external_workmanus/
|   `-- seller_automation/
|       |-- app/
|       |-- data/
|       |-- docs/
|       |-- logs/
|       |-- venv/
|       |-- README.md
|       |-- requirements.txt
|       `-- run_server.bat
|-- graphify-out/
|   |-- 2026-07-18/
|   |   |-- .graphify_analysis.json
|   |   |-- .graphify_labels.json
|   |   |-- graph.json
|   |   |-- GRAPH_REPORT.md
|   |   `-- manifest.json
|   |-- 2026-07-19/
|   |   |-- .graphify_analysis.json
|   |   |-- .graphify_labels.json
|   |   |-- graph.json
|   |   |-- GRAPH_REPORT.md
|   |   `-- manifest.json
|   |-- cache/
|   |   |-- ast/
|   |   `-- stat-index.json
|   |-- .graphify_analysis.json
|   |-- .graphify_labels.json
|   |-- .graphify_labels.json.sig
|   |-- .graphify_root
|   |-- graph.json
|   |-- GRAPH_REPORT.md
|   |-- GRAPH_TREE.html
|   `-- manifest.json
|-- instiz_diag_tmp/
|-- knowledge/
|   |-- agent_training/
|   |   |-- agency_agents_cardnews_education.md
|   |   `-- category_execution_prompts.json
|   |-- owner_directives/
|   |   `-- cardnews_owner_directives.json
|   |-- owner_feedback/
|   |   |-- cardnews_owner_feedback.jsonl
|   |   |-- cardnews_owner_learning_index.json
|   |   `-- README.md
|   |-- patterns/
|   |   |-- initial_patterns.jsonl
|   |   |-- pattern_registry.jsonl
|   |   `-- promotion_policy.md
|   |-- registry/
|   |   |-- material_inventory_report.md
|   |   |-- source_registry.jsonl
|   |   `-- unresolved_sources.jsonl
|   |-- README.md
|   `-- taxonomy.json
|-- logs/
|   `-- README.md
|-- modules/
|   |-- affiliate/
|   |   |-- __init__.py
|   |   |-- affiliate_contract.py
|   |   |-- affiliate_policy_gate.py
|   |   |-- affiliate_result.py
|   |   |-- affiliate_revenue_router.py
|   |   `-- affiliate_safety_utils.py
|   |-- agent_console/
|   |   |-- __init__.py
|   |   |-- __main__.py
|   |   |-- cardnews_flow_bridge.py
|   |   |-- category_prompt_loader.py
|   |   |-- console.py
|   |   |-- contracts.py
|   |   |-- dashboard.py
|   |   |-- execution_prompt_pack.py
|   |   |-- executor.py
|   |   |-- NAEO_MCP.md
|   |   |-- owner_feedback_bridge.py
|   |   |-- owner_feedback_learning.py
|   |   |-- owner_review_bridge.py
|   |   |-- package_completion_gate.py
|   |   |-- production_package_batch_bridge.py
|   |   |-- spark_executor.py
|   |   |-- spark_host_bridge.py
|   |   |-- tool_assignment_policy.py
|   |   |-- tool_manifest.py
|   |   `-- UPSTREAM.md
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
|   |-- brandconnect/
|   |   |-- __init__.py
|   |   |-- brandconnect_candidate_matcher.py
|   |   |-- brandconnect_contract.py
|   |   |-- brandconnect_package_builder.py
|   |   |-- brandconnect_policy_gate.py
|   |   |-- brandconnect_product_catalog.py
|   |   |-- brandconnect_second_stage.py
|   |   |-- catalog_function_relation_builder.py
|   |   |-- commerce_story_integration.py
|   |   |-- incremental_commerce_story_engine.py
|   |   |-- relation_aware_candidate_matcher.py
|   |   `-- relation_story_shard_validator.py
|   |-- card_news/
|   |   |-- __init__.py
|   |   |-- account_variable_slide_planner.py
|   |   |-- canvas_contract.py
|   |   |-- card_news_module.py
|   |   |-- card_news_quality_checker.py
|   |   |-- card_news_result_manifest.py
|   |   |-- card_news_text_optimizer.py
|   |   |-- category_media_pack.py
|   |   |-- debate_question_selector.py
|   |   |-- evidence_input_validator.py
|   |   |-- evidence_selector.py
|   |   |-- highlight_engine.py
|   |   |-- layout_rule_engine.py
|   |   |-- layout_selector.py
|   |   |-- mobile_readability_checker.py
|   |   |-- package_content_quality_gate.py
|   |   |-- production_controller.py
|   |   |-- production_package_pipeline.py
|   |   |-- render_constants.py
|   |   |-- selected_candidate_production_package.py
|   |   |-- selected_candidate_production_planner.py
|   |   |-- selected_candidate_render_input_adapter.py
|   |   |-- slide_designer.py
|   |   |-- social_proof_selector.py
|   |   |-- source_image_motion_montage.py
|   |   |-- story_flow_planner.py
|   |   |-- typography_rules.py
|   |   |-- visual_qa_gate.py
|   |   `-- visual_rhythm_selector.py
|   |-- commerce/
|   |   |-- __init__.py
|   |   |-- approval_gate.py
|   |   |-- audit_logger.py
|   |   |-- commerce_engine.py
|   |   |-- commerce_module.py
|   |   |-- commerce_storage.py
|   |   |-- contract_loader.py
|   |   |-- coupang_adapter.py
|   |   |-- credential_manager.py
|   |   |-- dry_run_executor.py
|   |   |-- marketplace_base.py
|   |   |-- payload_builder.py
|   |   |-- rollback_manager.py
|   |   |-- schema_validator.py
|   |   `-- smartstore_adapter.py
|   |-- common/
|   |   |-- __init__.py
|   |   |-- card_news_output_set.py
|   |   |-- external_storage.py
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
|   |-- compliance/
|   |   |-- __init__.py
|   |   |-- campaign_compliance_checker.py
|   |   |-- campaign_contract.py
|   |   |-- card_news_publish_gate.py
|   |   |-- compliance_result.py
|   |   |-- copy_intake_loader.py
|   |   |-- manual_image_intake_loader.py
|   |   |-- rights_intake_loader.py
|   |   `-- rights_intake_v1_8_adapter.py
|   |-- content/
|   |   |-- brand_rule_evaluator.py
|   |   |-- commerce_story_content_adapter.py
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
|   |-- design_learning/
|   |   |-- __init__.py
|   |   |-- card_news_design_learning.py
|   |   |-- contact_sheet_generator.py
|   |   |-- instagram_feed_scan_importer.py
|   |   |-- layout_candidate_map.py
|   |   `-- local_image_intake.py
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
|   |-- knowledge/
|   |   |-- __init__.py
|   |   |-- knowledge_contract.py
|   |   |-- knowledge_registry.py
|   |   |-- knowledge_router.py
|   |   |-- pattern_contract.py
|   |   `-- pattern_registry.py
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
|   |-- media_intelligence/
|   |   |-- image_operations.py
|   |   |-- local_media_pipeline.py
|   |   `-- rembg_bbox.py
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
|   |   |-- category_publish_package.py
|   |   `-- publishing_module.py
|   |-- research/
|   |   |-- research_context_builder.py
|   |   |-- research_insight_generator.py
|   |   `-- research_module.py
|   |-- shorts/
|   |   |-- __init__.py
|   |   |-- shorts_exporter.py
|   |   `-- shorts_module.py
|   |-- source_intake/
|   |   |-- __init__.py
|   |   |-- account_c_style_matcher.py
|   |   |-- account_candidate_router.py
|   |   |-- account_deep_discovery_runner.py
|   |   |-- account_instagram_pattern_binder.py
|   |   |-- account_top_topic_selector.py
|   |   |-- candidate_evidence_bundle.py
|   |   |-- candidate_risk_detector.py
|   |   |-- candidate_selection_signal_normalizer.py
|   |   |-- category_candidate_pipeline.py
|   |   |-- category_specific_signal_builder.py
|   |   |-- category_stage2_selector.py
|   |   |-- collection_gap_report.py
|   |   |-- collection_gap_runner.py
|   |   |-- collection_quality_assessor.py
|   |   |-- collector_readiness_registry.py
|   |   |-- collector_work_order_generator.py
|   |   |-- common_candidate_signals.py
|   |   |-- community_comment_capture_provider.py
|   |   |-- content_production_handoff.py
|   |   |-- daily_collection_executor.py
|   |   |-- daily_collection_plan.py
|   |   |-- daily_collection_runner.py
|   |   |-- discovery_result_render_bridge.py
|   |   |-- external_deep_dive_store.py
|   |   |-- format_fit_router.py
|   |   |-- hierarchical_signal_normalizer.py
|   |   |-- instiz_diagnostic_contract.py
|   |   |-- lane_collection_summary.py
|   |   |-- lane_collection_summary_runner.py
|   |   |-- multi_account_card_news_discovery_pipeline.py
|   |   |-- naver_news_fallback_diagnostic.py
|   |   |-- naver_youtube_discovery_provider.py
|   |   |-- news_category_profiles.py
|   |   |-- newspaper4k_deep_discovery_provider.py
|   |   |-- origin_independence_resolver.py
|   |   |-- owner_ranked_deep_dive_adapter.py
|   |   |-- owner_ranked_final_candidate_selector.py
|   |   |-- portfolio_candidate_selector.py
|   |   |-- reviewed_evidence_validator.py
|   |   |-- reviewed_watch_promotion_gate.py
|   |   |-- same_event_topic_clusterer.py
|   |   |-- selected_candidate_production_flow.py
|   |   |-- selective_deep_dive_queue.py
|   |   |-- selective_verification_policy.py
|   |   |-- source_agreement.py
|   |   |-- source_capability_map.py
|   |   |-- source_field_completeness_audit.py
|   |   |-- source_health_dashboard.py
|   |   |-- source_intake_artifact_index.py
|   |   |-- source_intake_brief.py
|   |   |-- source_intake_consistency_validator.py
|   |   |-- source_intake_metrics.py
|   |   |-- source_intake_release_candidate.py
|   |   |-- source_intake_schema.py
|   |   |-- source_intake_status_bundle.py
|   |   |-- spark_task_queue_builder.py
|   |   |-- stage2_format_router_bridge.py
|   |   |-- stage2_review_calibrator.py
|   |   |-- topic_input_quality_gate.py
|   |   |-- validated_topic_candidate_pipeline.py
|   |   |-- validated_topic_input_adapter.py
|   |   `-- watch_candidate_review_queue.py
|   |-- tool_adapters/
|   |   |-- cardnews_renderer_runtime.py
|   |   |-- intel_xpu_runtime.py
|   |   |-- openclip_runtime.py
|   |   |-- paddleocr_runtime.py
|   |   |-- playwright_runtime.py
|   |   |-- publishing_reference_runtime.py
|   |   |-- pyscenedetect_runtime.py
|   |   |-- realesrgan_runtime.py
|   |   |-- rembg_runtime.py
|   |   |-- seaweedfs_runtime.py
|   |   |-- seleniumbase_page_adapter.py
|   |   |-- seleniumbase_runtime.py
|   |   `-- sentence_transformers_runtime.py
|   |-- topic/
|   |   `-- topic_engine.py
|   |-- topic_engine/
|   |   |-- __init__.py
|   |   |-- card_news_topic_intelligence.py
|   |   |-- confidence_score.py
|   |   |-- keyword_weight.py
|   |   |-- topic_classifier.py
|   |   |-- topic_cluster.py
|   |   `-- topic_engine_module.py
|   |-- trend/
|   |-- trend_collector/
|   |   |-- __init__.py
|   |   |-- allure_beauty_collector.py
|   |   |-- apparelnews_collector.py
|   |   |-- beautynury_collector.py
|   |   |-- bobaedream_collector.py
|   |   |-- cosin_collector.py
|   |   |-- daum_news_collector.py
|   |   |-- dcinside_collector.py
|   |   |-- dcinside_parser.py
|   |   |-- dogdrip_collector.py
|   |   |-- edaily_collector.py
|   |   |-- fashionbiz_collector.py
|   |   |-- fashionn_collector.py
|   |   |-- fmkorea_collector.py
|   |   |-- glowpick_ranking_collector.py
|   |   |-- gq_grooming_collector.py
|   |   |-- hankyung_economy_collector.py
|   |   |-- mk_pick_collector.py
|   |   |-- moneytoday_collector.py
|   |   |-- musinsa_beauty_collector.py
|   |   |-- musinsa_boutique_collector.py
|   |   |-- musinsa_monthly_ranking_collector.py
|   |   |-- nate_news_rank_collector.py
|   |   |-- nate_pann_collector.py
|   |   |-- naver_api_hub_client.py
|   |   |-- naver_news_collector.py
|   |   |-- naver_news_parser_v2.py
|   |   |-- news1_collector.py
|   |   |-- newsis_collector.py
|   |   |-- oliveyoung_ranking_collector.py
|   |   |-- ppomppu_collector.py
|   |   |-- retry_policy.py
|   |   |-- ruliweb_collector.py
|   |   |-- source_health_tracker.py
|   |   |-- theqoo_collector.py
|   |   |-- top_topic_picker.py
|   |   |-- trend_collector_module.py
|   |   |-- trend_engine_guard.py
|   |   |-- trend_quality_scorer.py
|   |   |-- trend_run_recorder.py
|   |   |-- trend_source_manager.py
|   |   |-- vogue_beauty_collector.py
|   |   |-- wkorea_beauty_collector.py
|   |   `-- yonhap_collector.py
|   |-- trend_memory/
|   |   |-- __init__.py
|   |   |-- trend_memory_checker.py
|   |   |-- trend_memory_history.py
|   |   |-- trend_memory_interface.py
|   |   |-- trend_memory_module.py
|   |   `-- trend_memory_storage.py
|   |-- base_module.py
|   `-- README.md
|-- owner_analysis_inbox/
|   |-- KakaoTalk_20260717_085746283 (1).jpg
|   |-- KakaoTalk_20260717_085746283 (2).jpg
|   |-- KakaoTalk_20260717_085746283.jpg
|   |-- KakaoTalk_20260717_085746283_01 (1).jpg
|   |-- KakaoTalk_20260717_085746283_01 (2).jpg
|   |-- KakaoTalk_20260717_085746283_01.jpg
|   |-- KakaoTalk_20260717_085746283_02 (1).jpg
|   |-- KakaoTalk_20260717_085746283_02 (2).jpg
|   |-- KakaoTalk_20260717_085746283_02.jpg
|   |-- KakaoTalk_20260717_085746283_03 (1).jpg
|   |-- KakaoTalk_20260717_085746283_03 (2).jpg
|   |-- KakaoTalk_20260717_085746283_03.jpg
|   |-- KakaoTalk_20260717_085746283_04 (1).jpg
|   |-- KakaoTalk_20260717_085746283_04 (2).jpg
|   |-- KakaoTalk_20260717_085746283_04.jpg
|   |-- KakaoTalk_20260717_085746283_05 (1).jpg
|   |-- KakaoTalk_20260717_085746283_05 (2).jpg
|   |-- KakaoTalk_20260717_085746283_05.jpg
|   |-- KakaoTalk_20260717_085746283_06 (1).jpg
|   |-- KakaoTalk_20260717_085746283_06 (2).jpg
|   |-- KakaoTalk_20260717_085746283_06.jpg
|   |-- KakaoTalk_20260717_085746283_07 (1).jpg
|   |-- KakaoTalk_20260717_085746283_07 (2).jpg
|   |-- KakaoTalk_20260717_085746283_07.jpg
|   |-- KakaoTalk_20260717_085746283_08 (1).jpg
|   |-- KakaoTalk_20260717_085746283_08 (2).jpg
|   |-- KakaoTalk_20260717_085746283_08.jpg
|   |-- KakaoTalk_20260717_085746283_09 (1).jpg
|   |-- KakaoTalk_20260717_085746283_09 (2).jpg
|   |-- KakaoTalk_20260717_085746283_09.jpg
|   |-- KakaoTalk_20260717_085746283_10 (1).jpg
|   |-- KakaoTalk_20260717_085746283_10 (2).jpg
|   |-- KakaoTalk_20260717_085746283_10.jpg
|   |-- KakaoTalk_20260717_085746283_11 (1).jpg
|   |-- KakaoTalk_20260717_085746283_11 (2).jpg
|   |-- KakaoTalk_20260717_085746283_11.jpg
|   |-- KakaoTalk_20260717_085746283_12 (1).jpg
|   |-- KakaoTalk_20260717_085746283_12 (2).jpg
|   |-- KakaoTalk_20260717_085746283_12.jpg
|   |-- KakaoTalk_20260717_085746283_13 (1).jpg
|   |-- KakaoTalk_20260717_085746283_13 (2).jpg
|   |-- KakaoTalk_20260717_085746283_13.jpg
|   |-- KakaoTalk_20260717_085746283_14 (1).jpg
|   |-- KakaoTalk_20260717_085746283_14 (2).jpg
|   |-- KakaoTalk_20260717_085746283_14.jpg
|   |-- KakaoTalk_20260717_085746283_15 (1).jpg
|   |-- KakaoTalk_20260717_085746283_15 (2).jpg
|   |-- KakaoTalk_20260717_085746283_15.jpg
|   |-- KakaoTalk_20260717_085746283_16 (1).jpg
|   |-- KakaoTalk_20260717_085746283_16 (2).jpg
|   |-- KakaoTalk_20260717_085746283_16.jpg
|   |-- KakaoTalk_20260717_085746283_17 (1).jpg
|   |-- KakaoTalk_20260717_085746283_17 (2).jpg
|   |-- KakaoTalk_20260717_085746283_17.jpg
|   |-- KakaoTalk_20260717_085746283_18 (1).jpg
|   |-- KakaoTalk_20260717_085746283_18 (2).jpg
|   |-- KakaoTalk_20260717_085746283_18.jpg
|   |-- KakaoTalk_20260717_085746283_19 (1).jpg
|   |-- KakaoTalk_20260717_085746283_19 (2).jpg
|   |-- KakaoTalk_20260717_085746283_19.jpg
|   |-- KakaoTalk_20260717_085746283_20 (1).jpg
|   |-- KakaoTalk_20260717_085746283_20 (2).jpg
|   |-- KakaoTalk_20260717_085746283_20.jpg
|   |-- KakaoTalk_20260717_085746283_21 (1).jpg
|   |-- KakaoTalk_20260717_085746283_21 (2).jpg
|   |-- KakaoTalk_20260717_085746283_21.jpg
|   |-- KakaoTalk_20260717_085746283_22 (1).jpg
|   |-- KakaoTalk_20260717_085746283_22 (2).jpg
|   |-- KakaoTalk_20260717_085746283_22.jpg
|   |-- KakaoTalk_20260717_085746283_23 (1).jpg
|   |-- KakaoTalk_20260717_085746283_23 (2).jpg
|   |-- KakaoTalk_20260717_085746283_23.jpg
|   |-- KakaoTalk_20260717_085746283_24 (1).jpg
|   |-- KakaoTalk_20260717_085746283_24 (2).jpg
|   |-- KakaoTalk_20260717_085746283_24.jpg
|   |-- KakaoTalk_20260717_085746283_25 (1).jpg
|   |-- KakaoTalk_20260717_085746283_25 (2).jpg
|   |-- KakaoTalk_20260717_085746283_25.jpg
|   |-- KakaoTalk_20260717_085746283_26 (1).jpg
|   |-- KakaoTalk_20260717_085746283_26 (2).jpg
|   |-- KakaoTalk_20260717_085746283_26.jpg
|   |-- KakaoTalk_20260717_085746283_27 (1).jpg
|   |-- KakaoTalk_20260717_085746283_27 (2).jpg
|   |-- KakaoTalk_20260717_085746283_27.jpg
|   |-- KakaoTalk_20260717_085746283_28 (1).jpg
|   |-- KakaoTalk_20260717_085746283_28 (2).jpg
|   |-- KakaoTalk_20260717_085746283_28.jpg
|   |-- KakaoTalk_20260717_085746283_29 (1).jpg
|   |-- KakaoTalk_20260717_085746283_29 (2).jpg
|   |-- KakaoTalk_20260717_085746283_29.jpg
|   |-- KakaoTalk_20260717_085800319 (1).jpg
|   |-- KakaoTalk_20260717_085800319.jpg
|   |-- KakaoTalk_20260717_085800319_01 (1).jpg
|   |-- KakaoTalk_20260717_085800319_01.jpg
|   |-- KakaoTalk_20260717_085800319_02 (1).jpg
|   |-- KakaoTalk_20260717_085800319_02.jpg
|   |-- KakaoTalk_20260717_085800319_03 (1).jpg
|   |-- KakaoTalk_20260717_085800319_03.jpg
|   |-- KakaoTalk_20260717_085800319_04 (1).jpg
|   |-- KakaoTalk_20260717_085800319_04.jpg
|   |-- KakaoTalk_20260717_085800319_05 (1).jpg
|   |-- KakaoTalk_20260717_085800319_05.jpg
|   |-- KakaoTalk_20260717_085800319_06 (1).jpg
|   |-- KakaoTalk_20260717_085800319_06.jpg
|   |-- KakaoTalk_20260717_085800319_07 (1).jpg
|   |-- KakaoTalk_20260717_085800319_07.jpg
|   |-- KakaoTalk_20260717_085800319_08 (1).jpg
|   |-- KakaoTalk_20260717_085800319_08.jpg
|   |-- KakaoTalk_20260717_085800319_09 (1).jpg
|   |-- KakaoTalk_20260717_085800319_09.jpg
|   |-- KakaoTalk_20260717_085800319_10 (1).jpg
|   |-- KakaoTalk_20260717_085800319_10.jpg
|   |-- KakaoTalk_20260717_085800319_11.jpg
|   |-- KakaoTalk_20260717_085800319_12.jpg
|   |-- KakaoTalk_20260717_085800319_13.jpg
|   |-- KakaoTalk_20260717_085800319_14.jpg
|   |-- KakaoTalk_20260717_085800319_15.jpg
|   |-- KakaoTalk_20260717_085800319_16.jpg
|   |-- KakaoTalk_20260717_085800319_17.jpg
|   |-- KakaoTalk_20260717_085800319_18.jpg
|   |-- KakaoTalk_20260717_085800319_19.jpg
|   |-- KakaoTalk_20260717_085800319_20.jpg
|   |-- KakaoTalk_20260717_085800319_21.jpg
|   |-- KakaoTalk_20260717_085800319_22.jpg
|   |-- KakaoTalk_20260717_085800319_23.jpg
|   |-- KakaoTalk_20260717_085813389 (1).jpg
|   |-- KakaoTalk_20260717_085813389.jpg
|   |-- KakaoTalk_20260717_085813389_01 (1).jpg
|   |-- KakaoTalk_20260717_085813389_01.jpg
|   |-- KakaoTalk_20260717_085813389_02 (1).jpg
|   |-- KakaoTalk_20260717_085813389_02.jpg
|   |-- KakaoTalk_20260717_085813389_03 (1).jpg
|   |-- KakaoTalk_20260717_085813389_03.jpg
|   |-- KakaoTalk_20260717_085813389_04 (1).jpg
|   |-- KakaoTalk_20260717_085813389_04.jpg
|   |-- KakaoTalk_20260717_085813389_05 (1).jpg
|   |-- KakaoTalk_20260717_085813389_05.jpg
|   |-- KakaoTalk_20260717_085813389_06 (1).jpg
|   |-- KakaoTalk_20260717_085813389_06.jpg
|   |-- KakaoTalk_20260717_085813389_07 (1).jpg
|   |-- KakaoTalk_20260717_085813389_07.jpg
|   |-- KakaoTalk_20260717_085813389_08 (1).jpg
|   |-- KakaoTalk_20260717_085813389_08.jpg
|   |-- KakaoTalk_20260717_085813389_09 (1).jpg
|   |-- KakaoTalk_20260717_085813389_09.jpg
|   |-- KakaoTalk_20260717_085813389_10 (1).jpg
|   |-- KakaoTalk_20260717_085813389_10.jpg
|   |-- KakaoTalk_20260717_085813389_11 (1).jpg
|   |-- KakaoTalk_20260717_085813389_11.jpg
|   |-- KakaoTalk_20260717_085813389_12 (1).jpg
|   |-- KakaoTalk_20260717_085813389_12.jpg
|   |-- KakaoTalk_20260717_085813389_13 (1).jpg
|   |-- KakaoTalk_20260717_085813389_13.jpg
|   |-- KakaoTalk_20260717_085813389_14 (1).jpg
|   |-- KakaoTalk_20260717_085813389_14.jpg
|   |-- KakaoTalk_20260717_085813389_15 (1).jpg
|   |-- KakaoTalk_20260717_085813389_15.jpg
|   |-- KakaoTalk_20260717_085813389_16 (1).jpg
|   |-- KakaoTalk_20260717_085813389_16.jpg
|   |-- KakaoTalk_20260717_085813389_17 (1).jpg
|   |-- KakaoTalk_20260717_085813389_17.jpg
|   |-- KakaoTalk_20260717_085813389_18 (1).jpg
|   |-- KakaoTalk_20260717_085813389_18.jpg
|   |-- KakaoTalk_20260717_085813389_19 (1).jpg
|   |-- KakaoTalk_20260717_085813389_19.jpg
|   |-- KakaoTalk_20260717_085813389_20 (1).jpg
|   |-- KakaoTalk_20260717_085813389_20.jpg
|   |-- KakaoTalk_20260717_085813389_21 (1).jpg
|   |-- KakaoTalk_20260717_085813389_21.jpg
|   |-- KakaoTalk_20260717_085813389_22 (1).jpg
|   |-- KakaoTalk_20260717_085813389_22.jpg
|   |-- KakaoTalk_20260717_085813389_23 (1).jpg
|   |-- KakaoTalk_20260717_085813389_23.jpg
|   |-- KakaoTalk_20260717_085813389_24 (1).jpg
|   |-- KakaoTalk_20260717_085813389_24.jpg
|   |-- KakaoTalk_20260717_085813389_25 (1).jpg
|   |-- KakaoTalk_20260717_085813389_25.jpg
|   |-- KakaoTalk_20260717_085813389_26 (1).jpg
|   |-- KakaoTalk_20260717_085813389_26.jpg
|   |-- KakaoTalk_20260717_085813389_27 (1).jpg
|   |-- KakaoTalk_20260717_085813389_27.jpg
|   |-- KakaoTalk_20260717_085813389_28 (1).jpg
|   |-- KakaoTalk_20260717_085813389_28.jpg
|   |-- KakaoTalk_20260717_085849034 (1).jpg
|   |-- KakaoTalk_20260717_085849034.jpg
|   |-- KakaoTalk_20260717_085849034_01 (1).jpg
|   |-- KakaoTalk_20260717_085849034_01.jpg
|   |-- KakaoTalk_20260717_085849034_02 (1).jpg
|   |-- KakaoTalk_20260717_085849034_02.jpg
|   |-- KakaoTalk_20260717_085849034_03 (1).jpg
|   |-- KakaoTalk_20260717_085849034_03.jpg
|   |-- KakaoTalk_20260717_085849034_04 (1).jpg
|   |-- KakaoTalk_20260717_085849034_04.jpg
|   |-- KakaoTalk_20260717_085849034_05 (1).jpg
|   |-- KakaoTalk_20260717_085849034_05.jpg
|   |-- KakaoTalk_20260717_085849034_06 (1).jpg
|   |-- KakaoTalk_20260717_085849034_06.jpg
|   |-- KakaoTalk_20260717_085849034_07 (1).jpg
|   |-- KakaoTalk_20260717_085849034_07.jpg
|   |-- KakaoTalk_20260717_085849034_08 (1).jpg
|   |-- KakaoTalk_20260717_085849034_08.jpg
|   |-- KakaoTalk_20260717_085849034_09 (1).jpg
|   |-- KakaoTalk_20260717_085849034_09.jpg
|   |-- KakaoTalk_20260717_085849034_10 (1).jpg
|   |-- KakaoTalk_20260717_085849034_10.jpg
|   |-- KakaoTalk_20260717_085849034_11 (1).jpg
|   |-- KakaoTalk_20260717_085849034_11.jpg
|   |-- KakaoTalk_20260717_085849034_12 (1).jpg
|   |-- KakaoTalk_20260717_085849034_12.jpg
|   |-- KakaoTalk_20260717_085849034_13 (1).jpg
|   |-- KakaoTalk_20260717_085849034_13.jpg
|   |-- KakaoTalk_20260717_085849034_14 (1).jpg
|   |-- KakaoTalk_20260717_085849034_14.jpg
|   |-- KakaoTalk_20260717_085849034_15 (1).jpg
|   |-- KakaoTalk_20260717_085849034_15.jpg
|   |-- KakaoTalk_20260717_085849034_16 (1).jpg
|   |-- KakaoTalk_20260717_085849034_16.jpg
|   |-- KakaoTalk_20260717_085849034_17 (1).jpg
|   |-- KakaoTalk_20260717_085849034_17.jpg
|   |-- KakaoTalk_20260717_085849034_18 (1).jpg
|   |-- KakaoTalk_20260717_085849034_18.jpg
|   |-- KakaoTalk_20260717_085849034_19 (1).jpg
|   |-- KakaoTalk_20260717_085849034_19.jpg
|   |-- KakaoTalk_20260717_085849034_20 (1).jpg
|   |-- KakaoTalk_20260717_085849034_20.jpg
|   |-- KakaoTalk_20260717_085849034_21 (1).jpg
|   |-- KakaoTalk_20260717_085849034_21.jpg
|   |-- KakaoTalk_20260717_085849034_22 (1).jpg
|   |-- KakaoTalk_20260717_085849034_22.jpg
|   |-- KakaoTalk_20260717_085849034_23.jpg
|   |-- KakaoTalk_20260717_085849034_24.jpg
|   |-- KakaoTalk_20260717_085849034_25.jpg
|   |-- KakaoTalk_20260717_085849034_26.jpg
|   |-- KakaoTalk_20260717_085849034_27.jpg
|   |-- KakaoTalk_20260717_085849034_28.jpg
|   |-- KakaoTalk_20260717_085849034_29.jpg
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
|   |-- build_cardnews_production_packages.py
|   |-- build_category_publish_packages.py
|   |-- build_owner_candidate_report.py
|   |-- build_owner_review_collection.py
|   |-- build_source_health_dashboard.py
|   |-- capture_selected_community_comments.py
|   |-- claude_session_checkpoint.py
|   |-- demo_subject_crop_guard_stage3.py
|   |-- extract_cardnews_video_clip.py
|   |-- generate_visual_qa_receipt_from_media.py
|   |-- import_design_candidates_to_owner_feedback.py
|   |-- import_instagram_learning_patterns.py
|   |-- knowledge_query.py
|   |-- knowledge_validate.py
|   |-- prepare_cardnews_local_media.py
|   |-- preview_rembg_alpha_bbox.py
|   |-- rebuild_owner_feedback_learning.py
|   |-- record_owner_feedback.py
|   |-- render_blackmonsterfit_cooling_carousel.py
|   |-- render_blackmonsterfit_heatwave_story_v2.py
|   |-- render_cardnews_prototypes.py
|   |-- render_no_video_motion_samples.py
|   |-- render_selected_cardnews_preupload.py
|   |-- run_brandconnect_second_stage.py
|   |-- run_cardnews_package_quality_loop.py
|   |-- run_cardnews_production.py
|   |-- run_local_image_intake.py
|   |-- run_owner_ranked_final_selection.py
|   |-- save_brandconnect_catalog_snapshot.py
|   |-- update_project_snapshot.py
|   `-- verify_cardnews_production_packages.py
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
|   |   |-- assets/
|   |   `-- worker.js
|   |-- .openai/
|   |   `-- hosting.json
|   |-- .wrangler/
|   |   |-- state/
|   |   `-- tmp/
|   |-- app/
|   |   |-- api/
|   |   |-- commerce.css
|   |   |-- decision.css
|   |   |-- globals.css
|   |   |-- layout.js
|   |   |-- os.css
|   |   |-- owner-review-workspace.js
|   |   |-- owner-review.css
|   |   |-- page.js
|   |   |-- production-package-review.js
|   |   `-- production-package-review.module.css
|   |-- lib/
|   |   |-- agent-console-bridge.js
|   |   |-- brandconnect-second-stage.js
|   |   |-- cardnews-final-selector.js
|   |   |-- owner-review-store.js
|   |   `-- production-package-review.js
|   |-- node_modules/
|   |   |-- .bin/
|   |   |-- .mf/
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
|   |   |-- baseline-browser-mapping/
|   |   |-- blake3-wasm/
|   |   |-- caniuse-lite/
|   |   |-- client-only/
|   |   |-- cookie/
|   |   |-- detect-libc/
|   |   |-- error-stack-parser-es/
|   |   |-- kleur/
|   |   |-- miniflare/
|   |   |-- nanoid/
|   |   |-- next/
|   |   |-- path-to-regexp/
|   |   |-- pathe/
|   |   |-- picocolors/
|   |   |-- postcss/
|   |   |-- react/
|   |   |-- react-dom/
|   |   |-- scheduler/
|   |   |-- semver/
|   |   |-- sharp/
|   |   |-- source-map-js/
|   |   |-- styled-jsx/
|   |   |-- supports-color/
|   |   |-- tslib/
|   |   |-- undici/
|   |   |-- unenv/
|   |   |-- workerd/
|   |   |-- wrangler/
|   |   |-- ws/
|   |   |-- youch/
|   |   |-- youch-core/
|   |   `-- .package-lock.json
|   |-- out/
|   |   |-- _next/
|   |   |-- _not-found/
|   |   |-- 404.html
|   |   |-- __next.__PAGE__.txt
|   |   |-- __next._full.txt
|   |   |-- __next._head.txt
|   |   |-- __next._index.txt
|   |   |-- __next._tree.txt
|   |   |-- _not-found.html
|   |   |-- _not-found.txt
|   |   |-- index.html
|   |   `-- index.txt
|   |-- scripts/
|   |   `-- prepare-static-worker.mjs
|   |-- tests/
|   |   |-- brandconnect-second-stage.test.mjs
|   |   |-- cardnews-final-selector.test.mjs
|   |   |-- owner-review-store.test.mjs
|   |   `-- production-package-review.test.mjs
|   |-- .gitignore
|   |-- ai-content-os-site-static.tar.gz
|   |-- ai-content-os-site.tar.gz
|   |-- next.config.mjs
|   |-- package-lock.json
|   |-- package.json
|   `-- wrangler.jsonc
|-- source_health_dashboard_tmp/
|-- source_intake_brief_tmp/
|-- source_intake_bundle_tmp/
|-- source_intake_consistency_tmp/
|-- source_intake_index_tmp/
|-- source_intake_naver_diag_tmp/
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
|   |-- _tmp_dbg/
|   |   `-- 2099-01-11/
|   |-- _tmp_nate/
|   |   `-- 2099-01-05/
|   |-- _tmp_nate2/
|   |   `-- 2099-01-05/
|   |-- _tmp_nate_news_rank_cache/
|   |-- _tmp_newsis_cap/
|   |   `-- 2099-01-11/
|   |-- _tmp_newsis_dbg2/
|   |   `-- 2099-01-11/
|   |-- _tmp_newsis_dbg3/
|   |   `-- 2099-01-11/
|   |-- _tmp_status_bundle/
|   |   |-- source_intake_bundle_5imyjnoo/
|   |   |-- source_intake_bundle_adfi4ezh/
|   |   |-- source_intake_bundle_gy19udaw/
|   |   |-- source_intake_bundle_i5_ohqco/
|   |   `-- source_intake_bundle_xm0pbu05/
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
|   |   |-- qa_fail_case/
|   |   |-- qa_threshold_sample/
|   |   |-- satori-ab-20260722-120625/
|   |   |-- satori-ab-20260722-120717/
|   |   |-- satori-ab-20260722-120833/
|   |   |-- satori-ab-20260722-121032/
|   |   |-- satori-ab-20260722-121105/
|   |   |-- satori-ab-20260722-121322/
|   |   |-- satori-ab-20260722-121621/
|   |   |-- satori-ab-20260722-121758/
|   |   |-- .gitkeep
|   |   |-- bobaedream_cache.json
|   |   |-- dcinside_cache.json
|   |   |-- dogdrip_cache.json
|   |   |-- edaily_cache.json
|   |   |-- fmkorea_cache.json
|   |   |-- hankyung_economy_cache.json
|   |   |-- local_media_smoke_request.json
|   |   |-- mk_economy_cache.json
|   |   |-- moneytoday_cache.json
|   |   |-- nate_news_rank_cache.json
|   |   |-- nate_pann_cache.json
|   |   |-- naver_news_cache.json
|   |   |-- news1_cache.json
|   |   |-- ppomppu_cache.json
|   |   |-- ruliweb_cache.json
|   |   |-- theqoo_cache.json
|   |   `-- yonhap_cache.json
|   |-- card_news/
|   |   `-- (1 runtime file(s) omitted; gitignored, see .gitignore)
|   |-- collection_gap_runner_test/
|   |   |-- no_commerce_detail/
|   |   |-- queue_excludes_ok/
|   |   |-- queue_rank_deterministic/
|   |   `-- successful_run/
|   |-- commerce/
|   |   |-- audit/
|   |   |-- dryrun/
|   |   |-- logs/
|   |   `-- payloads/
|   |-- competitor/
|   |   |-- competitor_history.json
|   |   |-- competitor_profile.json
|   |   |-- competitor_profiles.json
|   |   `-- competitor_statistics.json
|   |-- content/
|   |   `-- (1 runtime file(s) omitted; gitignored, see .gitignore)
|   |-- copy_intake/
|   |   `-- CN-006.json
|   |-- dashboard/
|   |   `-- daily_learning_report.json
|   |-- design_learning/
|   |   |-- local_image_intake_runs/
|   |   |-- card_news_design_candidates.json
|   |   |-- instagram_feed_native_design_scan_merged_v1.json
|   |   |-- instagram_feed_native_design_scan_merged_v1_flat.json
|   |   |-- instagram_feed_native_design_scan_merged_v1_imported.json
|   |   `-- instagram_feed_native_design_scan_v1.json
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
|   |-- lane_collection_summary_runner_test/
|   |   |-- 2026-07-14/
|   |   |-- no_commerce_detail/
|   |   |-- successful_write/
|   |   |-- weak_lanes_present/
|   |   `-- written_json_is_valid/
|   |-- learning/
|   |   |-- learning_history.json
|   |   |-- learning_memory.json
|   |   `-- learning_statistics.json
|   |-- llm_logs/
|   |   `-- (659 runtime file(s) omitted; gitignored, see .gitignore)
|   |-- logs/
|   |   `-- .gitkeep
|   |-- manual_image_intake/
|   |   |-- staged/
|   |   `-- staged_assets/
|   |-- memory/
|   |   `-- .gitkeep
|   |-- output_sets/
|   |   `-- card_news/
|   |-- outputs/
|   |   |-- card_news_result.json
|   |   |-- content_result.json
|   |   |-- image_generation_result.json
|   |   |-- image_prompt_result.json
|   |   |-- publishing_result.json
|   |   `-- research_result.json
|   |-- owner_review/
|   |   |-- brandconnect_catalog_snapshot.json
|   |   |-- cardnews_decisions.json
|   |   `-- selective_deep_dive_queue.json
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
|   |   `-- publishing_result.json
|   |-- research/
|   |   |-- instagram/
|   |   `-- research_result.json
|   |-- review_packages/
|   |   `-- CN-006/
|   |-- rights_intake/
|   |   |-- 026a241f9f05463fb3fbce3315b77d2a.json
|   |   |-- 050bf05583d54d5e8119fc14a42d1ed0.json
|   |   `-- d0f34e752b8a45339e9a66f5166586eb.json
|   |-- rights_records/
|   |   `-- CN-006/
|   |-- runtime/
|   |   `-- service_diagnostic.json
|   |-- source_intake/
|   |   |-- 2026-07-14/
|   |   |-- 2026-07-15/
|   |   |-- 2026-07-16/
|   |   |-- 2026-07-17/
|   |   |-- 2026-07-19/
|   |   `-- live_owner_review_2026-07-16_2328/
|   |-- topics/
|   |   |-- .gitkeep
|   |   |-- card_news_topic_intelligence_sample.json
|   |   `-- topic_result.json
|   |-- trend_memory/
|   |   |-- trend_memory.json
|   |   `-- trend_memory_history.json
|   |-- trends/
|   |   |-- snapshots/
|   |   |   `-- (125 runtime file(s) omitted; gitignored, see .gitignore)
|   |   |-- .gitkeep
|   |   |-- collector_statistics.json
|   |   |-- last_safe_trend_result.json
|   |   |-- selected_topic.json
|   |   |-- source_health.json
|   |   |-- trend_engine_status.json
|   |   |-- trend_result.json
|   |   `-- trend_run_log.jsonl
|   |-- workflow_results/
|   |   `-- (40 runtime file(s) omitted; gitignored, see .gitignore)
|   `-- README.md
|-- templates/
|   |-- card_news_layout_rules.json
|   |-- card_news_template.json
|   `-- publishing_template.json
|-- tests/
|   |-- .tmp_relation_shard_validator/
|   |-- commerce/
|   |   |-- __init__.py
|   |   |-- fixtures.py
|   |   |-- test_approval_gate.py
|   |   |-- test_audit_logger.py
|   |   |-- test_commerce_engine.py
|   |   |-- test_contract_loader.py
|   |   |-- test_coupang_adapter.py
|   |   |-- test_credential_manager.py
|   |   |-- test_dry_run_executor.py
|   |   |-- test_marketplace_base.py
|   |   |-- test_payload_builder.py
|   |   |-- test_rollback_manager.py
|   |   |-- test_schema_validator.py
|   |   `-- test_smartstore_adapter.py
|   |-- fixtures/
|   |   |-- card_news_corrupt_run_08gwioja/
|   |   |-- card_news_image_slots_1z7psimd/
|   |   |-- card_news_render_test_nzznzy6e/
|   |   |-- card_news_rights/
|   |   |-- card_news_ux/
|   |   |-- evidence_selector_test_fahes92l/
|   |   |-- evidence_selector_test_qau6pcs5/
|   |   `-- evidence_selector_test_xk1az_uw/
|   |-- tmp_spark_task_queue/
|   |   |-- deterministic/
|   |   `-- safe_tasks/
|   |-- __init__.py
|   |-- _temp_cleanup.py
|   |-- test_account_c_style_matcher.py
|   |-- test_account_deep_discovery_runner.py
|   |-- test_affiliate_revenue_router.py
|   |-- test_agent_console.py
|   |-- test_agent_console_cardnews_flow_bridge.py
|   |-- test_agent_console_category_prompts.py
|   |-- test_agent_console_execution_prompt_pack.py
|   |-- test_agent_console_owner_feedback_bridge.py
|   |-- test_agent_console_owner_feedback_learning.py
|   |-- test_agent_console_package_completion_gate.py
|   |-- test_agent_console_production_package_batch_bridge.py
|   |-- test_agent_console_spark_executor.py
|   |-- test_agent_console_spark_host_bridge.py
|   |-- test_agent_console_tool_assignment.py
|   |-- test_ai_planner_consumer_adapter.py
|   |-- test_ai_planner_consumer_contract.py
|   |-- test_ai_planner_context.py
|   |-- test_ai_planner_contract.py
|   |-- test_ai_planner_decision_engine.py
|   |-- test_ai_planner_module.py
|   |-- test_ai_planner_schema.py
|   |-- test_allure_beauty_collector.py
|   |-- test_apparelnews_collector.py
|   |-- test_artifact_script_routing.py
|   |-- test_audit_checks_and_scorer.py
|   |-- test_beautynury_collector.py
|   |-- test_brandconnect_candidate_matcher.py
|   |-- test_brandconnect_phase_1.py
|   |-- test_build_cardnews_production_packages.py
|   |-- test_campaign_compliance_checker.py
|   |-- test_candidate_evidence_bundle.py
|   |-- test_candidate_risk_detector.py
|   |-- test_candidate_selection_signal_normalizer.py
|   |-- test_card_news_design_learning.py
|   |-- test_card_news_evidence_input_validator.py
|   |-- test_card_news_output_set_integrity.py
|   |-- test_card_news_production_quality.py
|   |-- test_card_news_production_ux.py
|   |-- test_card_news_result_manifest.py
|   |-- test_card_news_rights_intake.py
|   |-- test_card_news_rights_intake_fixture.py
|   |-- test_card_news_topic_intelligence.py
|   |-- test_cardnews_heavy_output_routing.py
|   |-- test_cardnews_package_content_quality_gate.py
|   |-- test_cardnews_production_controller.py
|   |-- test_cardnews_production_package_pipeline.py
|   |-- test_cardnews_visual_qa_gate.py
|   |-- test_catalog_function_relation_builder.py
|   |-- test_category_candidate_pipeline.py
|   |-- test_category_media_pack.py
|   |-- test_category_publish_package.py
|   |-- test_category_specific_signal_builder.py
|   |-- test_category_stage2_selector.py
|   |-- test_collection_gap_report.py
|   |-- test_collection_gap_runner.py
|   |-- test_collection_quality_assessor.py
|   |-- test_collector_readiness_registry.py
|   |-- test_collector_work_order_generator.py
|   |-- test_commerce_phase_1.py
|   |-- test_commerce_story_content_adapter.py
|   |-- test_commerce_story_integration.py
|   |-- test_common_candidate_signals.py
|   |-- test_common_card_news_output_set.py
|   |-- test_community_comment_capture_provider.py
|   |-- test_community_metrics_parser.py
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
|   |-- test_content_production_handoff.py
|   |-- test_content_prompt_builder.py
|   |-- test_content_routing_skeleton.py
|   |-- test_copy_intake_loader.py
|   |-- test_copy_intake_release_revision.py
|   |-- test_cosin_collector.py
|   |-- test_create_release_revision.py
|   |-- test_daily_collection_category_normalization.py
|   |-- test_daily_source_collection_executor.py
|   |-- test_daily_source_collection_plan.py
|   |-- test_daily_source_collection_runner.py
|   |-- test_daum_news_collector.py
|   |-- test_dcinside_collector.py
|   |-- test_dcinside_parser.py
|   |-- test_design_learning_instagram_feed_scan_importer.py
|   |-- test_design_learning_local_image_intake.py
|   |-- test_discovery_result_render_bridge.py
|   |-- test_dogdrip_collector.py
|   |-- test_edaily_collector.py
|   |-- test_external_cardnews_publish_paths.py
|   |-- test_external_deep_dive_store.py
|   |-- test_external_storage.py
|   |-- test_fashionbiz_collector.py
|   |-- test_fashionn_collector.py
|   |-- test_format_fit_router.py
|   |-- test_generate_visual_qa_copy_density.py
|   |-- test_glowpick_ranking_collector.py
|   |-- test_gq_grooming_collector.py
|   |-- test_hankyung_economy_collector.py
|   |-- test_hierarchical_signal_normalizer.py
|   |-- test_hyperframes_adapter.py
|   |-- test_image_prompt_module.py
|   |-- test_incremental_commerce_story_engine.py
|   |-- test_instagram_benchmark_parser.py
|   |-- test_instagram_intelligence_risk_checks.py
|   |-- test_instagram_learning_import.py
|   |-- test_instagram_research_classifier.py
|   |-- test_instagram_research_independence.py
|   |-- test_instagram_research_interface.py
|   |-- test_instagram_research_normalizer.py
|   |-- test_instagram_research_schema.py
|   |-- test_instagram_research_statistics.py
|   |-- test_instagram_research_storage.py
|   |-- test_intelligence_feedback_safety.py
|   |-- test_knowledge_extractor_and_classifier.py
|   |-- test_knowledge_query.py
|   |-- test_knowledge_registry.py
|   |-- test_lane_collection_summary.py
|   |-- test_lane_collection_summary_runner.py
|   |-- test_local_media_image_operations.py
|   |-- test_local_media_pipeline.py
|   |-- test_manual_image_intake.py
|   |-- test_mk_pick_collector.py
|   |-- test_moneytoday_collector.py
|   |-- test_musinsa_beauty_collector.py
|   |-- test_musinsa_boutique_collector.py
|   |-- test_musinsa_monthly_ranking_collector.py
|   |-- test_nate_news_rank_collector.py
|   |-- test_naver_api_hub_client.py
|   |-- test_naver_news_collector.py
|   |-- test_naver_news_parser_recovery.py
|   |-- test_naver_news_parser_v2.py
|   |-- test_naver_youtube_discovery_provider.py
|   |-- test_news1_collector.py
|   |-- test_news_category_profiles.py
|   |-- test_newsis_collector.py
|   |-- test_newspaper4k_deep_discovery_provider.py
|   |-- test_oliveyoung_ranking_collector.py
|   |-- test_origin_independence_resolver.py
|   |-- test_owner_ranked_deep_dive_adapter.py
|   |-- test_owner_ranked_final_candidate_selector.py
|   |-- test_owner_ranked_final_selection_runner.py
|   |-- test_pattern_registry.py
|   |-- test_performance_score_calculator.py
|   |-- test_portfolio_candidate_selector.py
|   |-- test_ppomppu_collector.py
|   |-- test_prepare_cardnews_local_media.py
|   |-- test_publishing_image_gate.py
|   |-- test_publishing_module_gaps.py
|   |-- test_publishing_release_candidate.py
|   |-- test_reevaluate_active_set_compliance.py
|   |-- test_relation_aware_candidate_matcher.py
|   |-- test_relation_story_shard_validator.py
|   |-- test_render_selected_cardnews_preupload.py
|   |-- test_research_evidence_fallback.py
|   |-- test_reviewed_evidence_validator.py
|   |-- test_rights_intake_v1_8_adapter.py
|   |-- test_ruliweb_collector.py
|   |-- test_run_cardnews_package_quality_loop.py
|   |-- test_run_cardnews_production.py
|   |-- test_save_brandconnect_catalog_snapshot.py
|   |-- test_selected_candidate_production_flow.py
|   |-- test_selected_candidate_production_package.py
|   |-- test_selected_candidate_production_planner.py
|   |-- test_selected_candidate_render_input_adapter.py
|   |-- test_selective_deep_dive_queue.py
|   |-- test_service_diagnostic.py
|   |-- test_shorts_phase_1.py
|   |-- test_shorts_phase_2a_exporter.py
|   |-- test_source_agreement.py
|   |-- test_source_health_dashboard.py
|   |-- test_source_image_motion_montage.py
|   |-- test_source_intake_artifact_index.py
|   |-- test_source_intake_brief.py
|   |-- test_source_intake_capabilities.py
|   |-- test_source_intake_consistency_validator.py
|   |-- test_source_intake_instiz_diagnostic_contract.py
|   |-- test_source_intake_metrics.py
|   |-- test_source_intake_naver_news_fallback_diagnostic.py
|   |-- test_source_intake_release_candidate.py
|   |-- test_source_intake_review_pipeline.py
|   |-- test_source_intake_schema.py
|   |-- test_source_intake_spark_task_queue.py
|   |-- test_source_intake_status_bundle.py
|   |-- test_stage2_format_router_bridge.py
|   |-- test_stage2_review_calibrator.py
|   |-- test_theqoo_collector.py
|   |-- test_tool_adapter_cardnews_renderer_runtime.py
|   |-- test_tool_adapter_intel_xpu_runtime.py
|   |-- test_tool_adapter_openclip_runtime.py
|   |-- test_tool_adapter_paddleocr_runtime.py
|   |-- test_tool_adapter_playwright_runtime.py
|   |-- test_tool_adapter_publishing_reference_runtime.py
|   |-- test_tool_adapter_pyscenedetect_runtime.py
|   |-- test_tool_adapter_realesrgan_runtime.py
|   |-- test_tool_adapter_rembg_runtime.py
|   |-- test_tool_adapter_seaweedfs_runtime.py
|   |-- test_tool_adapter_seleniumbase_page_adapter.py
|   |-- test_tool_adapter_seleniumbase_runtime.py
|   |-- test_tool_adapter_sentence_transformers_runtime.py
|   |-- test_topic_input_quality_gate.py
|   |-- test_trend_collector_ranking.py
|   |-- test_trend_memory_checker.py
|   |-- test_trend_retry_policy.py
|   |-- test_validated_topic_candidate_pipeline.py
|   |-- test_validated_topic_input_adapter.py
|   |-- test_verify_cardnews_production_packages.py
|   |-- test_vogue_beauty_collector.py
|   |-- test_wkorea_beauty_collector.py
|   |-- test_workflow_card_news_output_receipts.py
|   |-- test_workflow_planner_integration.py
|   `-- test_yonhap_collector.py
|-- tmp/
|   `-- pdfs/
|       `-- graphify_review/
|-- tools/
|   `-- cardnews-renderer/
|       |-- node_modules/
|       |-- package-lock.json
|       |-- package.json
|       |-- production-render.mjs
|       |-- smoke.mjs
|       |-- tmp-fabric-probe.png
|       |-- tmp-fabric-probe2.png
|       |-- tmp-fabric-red.png
|       |-- tmp-fabric-single.js
|       `-- tmp-test-fabric.js
|-- utils/
|   `-- __init__.py
|-- workflows/
|   `-- README.md
|-- .claudeignore
|-- .env
|-- .gitignore
|-- .graphifyignore
|-- .tmp_unittest_run.txt
|-- AGENTS.md
|-- AI_CONTEXT.md
|-- AUTO_SPARK_STATUS_20260715_033525.md
|-- CHANGELOG.md
|-- check_masked_status.py
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
|-- qa_receipt.json
|-- README.md
|-- requirements.txt
|-- ROADMAP.md
|-- SYSTEM_ARCHITECTURE.md
|-- tmp_check_png.py
|-- tmp_check_png2.py
|-- tmp_visual_qa_manifest.json
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
