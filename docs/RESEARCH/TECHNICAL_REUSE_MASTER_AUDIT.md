# External Materials Technical Reuse Master Audit

Date: 2026-07-14  
Status: technical research only; no package installation, account connection, external API call, or runtime integration authorized

## Audit Question

The materials shared in the current CTO conversation were previously assessed mainly for product fit, ROI,
policy risk, and future ownership. This audit asks the missing implementation questions:

1. Is source code publicly available?
2. Is the useful code actually the product core, or only an ancillary example/plugin?
3. Is there an official SDK, API, CLI, export, webhook, schema, or template that can shorten implementation?
4. What license and maintenance evidence controls reuse?
5. Which existing AI-Content-OS module can consume it without a rewrite?
6. If no code is reusable, which observable contract can be rebuilt clean-room?

## Classification Rules

| Label | Meaning |
|---|---|
| `DIRECT-CODE` | Public source with a verified license; a bounded file/package can be evaluated for reuse |
| `SERVICE-ADAPTER` | No reusable core source, but an official API/SDK/CLI/export can sit behind a project-owned interface |
| `CONFIG-AS-CODE` | A public schema/configuration/skill can be adopted without importing the vendor's core engine |
| `CLEAN-ROOM-PATTERN` | Only product behavior or workflow is observable; implement an independent contract, not copied code |
| `EXTERNAL-OPERATOR` | Keep the product as a manual external tool; no runtime integration is justified |
| `REJECT` | License, policy, security, duplication, or maintenance cost outweighs the benefit |

Marketing copy, screenshots, testimonials, generated examples, and an accessible web bundle are not treated as
reusable source code. Public GitHub organization membership also does not prove that a repository contains the
commercial product's core implementation.

## Sources Re-audited

### Agent and development workflow

- Halfdone specialist-agent workflow: <https://halfdoneclub.co/community/vibe-coding/d1a97046-8394-464a-a4dd-c3ab84d5cc6a>
- Halfdone Remotion/Claude workflow: <https://halfdoneclub.co/community/vibe-coding/942f2ba4-0a04-4fe9-a788-43eebe300228>
- Halfdone AI-service monetization cases: <https://halfdoneclub.co/community/vibe-coding/47d5a6e0-2fca-4daf-96f8-adb781385bb2>
- CodeRabbit: <https://www.coderabbit.ai/>

### Image and video

- <https://halfdoneclub.co/community/image-video-ai/6aea8176-eb26-44d1-aa4a-fabc84a8c82e>
- <https://halfdoneclub.co/community/image-video-ai/72dac4af-e7c1-4a0a-a470-f46e3ba62f0b>
- <https://halfdoneclub.co/community/image-video-ai/739fd40b-0f43-494f-99cd-9ad23a002d5c>
- <https://halfdoneclub.co/community/image-video-ai/3b568990-d524-4d9f-89eb-d7cc94ebe6df>

### Monetization and marketing intelligence

- AEDI-V: <https://aisum.com/ko/aediv>
- Snipit: <https://snipit.im/>

### Automation kit and commerce video

- REBORN AI Hub and Automation Kit: <https://rebornlabs.kr/ai-hub.html>
- Supplied `AI-automation-playbook-v2.pdf` (12 pages, inspected 2026-07-14)
- Supplied `2026 쇼핑몰 숏폼 전략 리포트_homepage.pdf` (43 pages, inspected 2026-07-14)

## Repository Reality Before Adoption

The project already contains the following contracts, so external material should fill a demonstrated gap rather
than create a parallel framework:

| Existing capability | Current implementation | Missing boundary relevant to this audit |
|---|---|---|
| Agent work ownership | `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, `docs/ACTIVE_PARALLEL_WORK_ORDERS.md` | Optional reusable specialist definitions/evaluation receipts, not another orchestrator |
| Content planning | `modules/ai_planner/`, `modules/content/` | External reference/search inputs with explicit provenance |
| Competitor intelligence | `modules/competitor_engine/`, `modules/competitor_learning/` | Normalized multi-platform `CreativeReference` intake and semantic retrieval |
| Knowledge reuse | `modules/knowledge_engine/`, `modules/knowledge/` | Source-linked creative pattern records; no need for a second knowledge store |
| Shorts planning/export | `modules/shorts/shorts_module.py`, `modules/shorts/shorts_exporter.py` | Replaceable renderer/provider adapters; existing package already supplies scene/caption/asset manifests |
| Affiliate routing | `modules/affiliate/` | Verified offer ingestion and scene/content-to-product candidate matching; never vendor-owned direct publication |
| Brand campaigns | `modules/brandconnect/` | Official campaign/link import and real performance receipts, subject to account/API approval |
| Commerce | `modules/commerce/` | Approved live product facts/providers; external recommendations cannot become facts automatically |
| Revenue feedback | internal quality/performance modules | Actual click, conversion, commission, ad-spend, and settlement imports remain separate external-data gates |

## Integration Principle

The fastest safe path is not to reproduce every product. It is:

```text
reuse licensed small code or official config
  -> wrap official service capability behind project-owned adapters
  -> rebuild differentiating contracts clean-room
  -> keep account/UI-only products as optional operator tools
```

No external source may replace the protected `WorkflowEngine`. Video, affiliate, brand, advertising, and external
review capabilities remain standalone until their existing approval gates are satisfied.

## Consolidated Findings

### A. Code or packages that are genuinely reusable

| Asset | Evidence/license boundary | Use in this project | Decision |
|---|---|---|---|
| `msitarzewski/agency-agents` converters/agent definitions | MIT | Reuse only a small converter or one bounded project-owned specialist contract; do not import the catalogue | Selective `DIRECT-CODE`; catalogue `BENCHMARK` |
| `coderabbitai/skills` | MIT | Review/autofix workflow contract reference; the actual CodeRabbit reviewer is still proprietary | `CONFIG-AS-CODE`, optional |
| `coderabbitai/claude-plugin` | MIT | Plugin packaging reference only; current Codex-first workflow does not need it | `BENCHMARK` |
| `coderabbitai/ast-grep-essentials` | Apache-2.0 | Review Python rules and selectively vendor only rules that beat current tests/linters | Conditional `DIRECT-CODE` |
| `coderabbitai/git-worktree-runner` | Apache-2.0 | Optional Git Bash/WSL helper; low value because the project already has work-order isolation | Defer |
| `remotion`, `@remotion/renderer`, `@remotion/cli` | Remotion custom license | Later Node renderer consuming the existing Shorts JSON package | Conditional `SERVICE-ADAPTER`/dependency |
| `higgsfield-ai/cli` | MIT | Future provider-neutral media adapter via subprocess JSON; prefer CLI boundary over importing provider internals | Strong conditional `SERVICE-ADAPTER` |
| `higgsfield-client` | Apache-2.0 but immature | Sync/async/poll/webhook/upload reference; not the first production dependency | Benchmark, defer SDK lock-in |
| `higgsfield-ai/skills` | MIT | Provider command/workflow reference; must still obey project rights/cost gates | Selective `CONFIG-AS-CODE` |
| `KlingAIResearch/LivePortrait` | MIT code with separate model restrictions | Possible local portrait-animation experiment only after replacing/revalidating noncommercial InsightFace assets | Conditional research spike; not production-ready as bundled |
| Figma `plugin-samples` and `rest-api-spec` | MIT | Build an owned CardNews JSON-to-editable-layers exporter/plugin instead of depending on html.to.design internals | `DIRECT-CODE` scaffolding candidate |

Every candidate above still needs exact commit/version pinning, license/NOTICE preservation, dependency and
security scanning, and a fixture-based evaluation before import.

### B. Official callable capability, but no reusable vendor core source

| Product | Available contract | Project boundary |
|---|---|---|
| CodeRabbit | Proprietary CLI with `--agent` JSONL findings; public configuration schema | Optional external QA after native tests; findings remain untrusted and independently verified |
| DomoAI | Official Talking Avatar REST task contract and callback/polling states | Later thin provider adapter; no official SDK source was verified |
| AEDI-V | Chrome extension/operator workflow only | Later manual YouTube productivity pilot; no DOM/private-API integration |
| Snipit | Manual SaaS search/archive/analysis; public developer contract not found | External research tool unless vendor grants export/API and commercial reuse rights |

### C. No directly reusable code found

- Halfdone AI-service monetization case collection: no repository, package, SDK, API, CLI, fixture, or license.
- AEDI-V core: no verified public repository/package/SDK/CLI/API/export contract.
- Snipit core: no verified public repository/package/SDK/CLI/developer API; observed client endpoints are private.
- html.to.design core: no verified public source; use manually or build an owned Figma plugin.
- DomoAI SDK: official REST documentation exists, but no verified official reusable SDK repository/license.
- Freepik Spaces implementation: no reusable source; only the typed node/edge workflow concept is adopted.
- Freepik MCP and Kling ComfyUI API-node repositories observed without an adequate license grant are not copied.
- REBORN Automation Kit: no public repository, source sample, package, SDK, CLI, OpenAPI, config schema,
  lockfile, test fixture, SBOM, or reusable license was verified before purchase.
- REBORN automation playbook PDF: all 12 pages are raster images and contain no embedded text, attachment,
  link, JavaScript, workflow export, command file, API schema, or license grant. Its prompts are not copied.
- Catenoid/Charlla shopping-shortform report: no embed snippet, player SDK/API, event schema, repository,
  configuration, or license is included. The one-line embed and conversion dashboard are vendor claims,
  not reusable implementation assets.

### D. Clean-room contracts worth owning

| Contract | Why it shortens current work | Existing consumer |
|---|---|---|
| `CreativeReference` | Normalizes Meta/Instagram/Google/YouTube/TikTok references with provenance and `render_allowed: false` | Competitor, Competitor Learning, Knowledge, Planner |
| `SceneProductMatchCandidate` | Turns scene/visual/speech/context evidence into a human-reviewed product candidate without trusting vendor commission claims | Shorts, Affiliate, Commerce |
| `MediaProviderAdapter` | One task/create/poll/cancel/result receipt across Higgsfield, DomoAI, Kling, or local providers | Standalone Shorts production |
| `Storyboard` / `ShotSpec` DAG | Preserves shot dependencies, prompts, reference assets, rights, and fallback independently of provider UI | Shorts exporter and future renderer |
| `RenderReceipt` | Records renderer/version/input hash/output/codec/duration/warnings instead of treating file existence as success | Shorts QA |
| `CreativeRightsReceipt` | Prevents competitor references, generated assets, faces/voices, and model-bundled assets from silently entering production | CardNews, Shorts, Compliance |
| `ExternalReviewFinding` | Normalizes CodeRabbit or other reviewers without granting edit/approval authority | QA/commit-check workflow |
| `CapabilityManifest` | Makes module dependencies, secrets, dry-run, approval, health, fallback, and evidence status inspectable | CTO operations, QA, provider adapters |
| `ConversionQuestionBrief` / `DecisiveSceneSpec` | Converts a verified purchase objection into a rights- and claim-gated commerce video scene | Shorts, Commerce, Affiliate, BrandConnect |
| `VideoPlacementManifest` | Separates the creative from owned-site placement, player behavior, CTA, approval, and experiment identity | Owned site, Ads, Commerce |
| `VideoCommerceEvent` / `ExperimentReceipt` | Prevents views or viewers from being mislabeled as incremental purchases | Revenue Analytics, Ads, Commerce |

### E. Priority by development acceleration

1. **Higgsfield CLI adapter research spike** when media generation is approved. It provides the clearest licensed,
   machine-readable provider surface and avoids writing upload/task/poll handling from scratch.
2. **Figma plugin/export spike** if editable CardNews delivery is a real operator requirement. Reuse the official
   MIT scaffolding and feed it current CardNews JSON; do not replace the proven Pillow renderer.
3. **Remotion renderer spike** after the Shorts renderer gate. Consume the existing export package rather than
   rewriting planning, captions, or asset validation.
4. **CreativeReference + SceneProductMatchCandidate contracts** as vendor-neutral inputs when the next revenue
   Sprint is approved. These unlock Snipit/AEDI-V-like workflows without vendor lock-in.
5. **CodeRabbit controlled fixture pilot**, not installation on the active dirty worktree. Reuse the JSONL contract
   and public skill/config assets only after repository-data/account/cost approval.
6. **DomoAI thin REST adapter** only if the Higgsfield/local option fails the Korean avatar/rights/cost evaluation.
7. **Shopping decision-scene fixture pilot** before any video SaaS purchase. Use the report's 27-scene
   taxonomy as vocabulary, but create owned contracts and owner-shot assets; measure no revenue without receipts.
8. **REBORN kit due diligence only**, not purchase/import. Its preflight -> config -> dry-run -> approval ->
   schedule pattern is useful, but the current project already has stricter execution and evidence gates.

### F. What not to build

- A wholesale agent catalogue or second orchestration system.
- A general AI code reviewer to compete with CodeRabbit.
- An AEDI-V clone that automates YouTube Studio DOM/private endpoints.
- A Snipit clone or client for its private `/api/v1` paths.
- A full video compositor before testing Remotion or a licensed provider adapter.
- Competitor creative copying, automated account sessions, bot-evasion, or unapproved publishing.
- Importing a purchased automation ZIP before its internal-use license, third-party notices, source tree,
  dependency locks, tests, secrets boundary, update integrity, and rollback behavior pass quarantine review.
- Treating generic prompts, vendor testimonials, report screenshots, or unattributed conversion statistics as code,
  product evidence, expected uplift, or advertising claims.

The detailed evidence tables are maintained in:

- `TECHNICAL_REUSE_AGENT_TOOLING.md`
- `TECHNICAL_REUSE_IMAGE_VIDEO.md`
- `TECHNICAL_REUSE_MONETIZATION_SAAS.md`
- `TECHNICAL_REUSE_REBORN_AUTOMATION_KIT.md`
- `TECHNICAL_REUSE_REBORN_PLAYBOOK.md`
- `SHOPPING_SHORTFORM_STRATEGY_TECHNICAL_AUDIT.md`

These documents distinguish verified source/license/API evidence from inference and record the smallest reversible
pilot for each candidate.

## Implementation Status

Research/documentation only. No external package, plugin, repository, extension, API, credential, account, media,
or copied code was added to the runtime.
