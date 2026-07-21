# Agent / Remotion / CodeRabbit Technical Reuse Audit

Audit date: 2026-07-14  
Status: **RESEARCH ONLY — no install, account connection, dependency, code integration, or Git action authorized**

## Decision First

There is reusable public material, but no item supplies a drop-in replacement for AI-Content-OS.

| Material | Exact reusable asset | Directly reusable now? | Decision |
|---|---|---:|---|
| **AI 에이전시를 통째로 들이는 법 — 83,000명이 본 Claude Code 에이전트** | `msitarzewski/agency-agents`: MIT agent Markdown plus Codex conversion/install scripts | **Technically yes, operationally no**: copying the catalogue would duplicate and weaken project contracts | **BENCHMARK**; selectively **BUILD** project-owned roles |
| **Claude Code x Remotion — 설치 가이드 & 팀 소개 영상 워크플로우** | Remotion npm packages and source; programmatic React video/render APIs | **Not in the current approved phase**; usable in a later standalone Shorts renderer pilot | **INTEGRATE later** |
| **AI 서비스 수익화 사례집 — 기술 장벽이 무너진 지금, 실행이 답!** | **None found**: no linked public repository, package, SDK, API, CLI, or reproducible implementation | No | **BENCHMARK** product method; **REJECT** unsupported metrics as evidence |
| **CodeRabbit** | Proprietary review service/CLI; MIT `coderabbitai/skills`; MIT Claude plugin; Apache-2.0 static rules/worktree helper | Skill contract is readable/reusable; actual review engine is not reusable source | **BUY/INTEGRATE conditionally**, not rebuild |

The fastest useful path is therefore: retain the repository's existing work-order and skill system, borrow only small contracts or licensed static rules, and evaluate Remotion/CodeRabbit through isolated fixtures. None belongs in the protected `WorkflowEngine` now.

## Evidence Rules

- **Verified fact** means confirmed from the linked public repository, registry, or official vendor documentation on the audit date.
- **Inference** means an implementation pattern derived from observable behavior; it is not vendor source code.
- Repository stars, versions, and maintenance dates are volatile snapshots, not adoption evidence.
- No proprietary source, paywalled course text, private prompt, or authenticated network traffic was copied or inspected.

## 1. Specialist Agent Catalogue

### Source and exact product

- Halfdone: [AI 에이전시를 통째로 들이는 법 — 83,000명이 본 Claude Code 에이전트](https://halfdoneclub.co/community/vibe-coding/d1a97046-8394-464a-a4dd-c3ab84d5cc6a)
- Underlying public project: [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)

### Verified public code

- Repository: public, active, MIT; latest observed push `2026-07-12`; about 131k stars at audit time.
- Reusable assets:
  - role definitions under domain folders such as `engineering/*.md`;
  - converters and installers under `scripts/`;
  - tool-specific adapters under `integrations/`, including the documented [Codex integration](https://github.com/msitarzewski/agency-agents/tree/main/integrations/codex);
  - generated Codex format: one TOML per role with `name`, `description`, and `developer_instructions`.
- License: [MIT](https://github.com/msitarzewski/agency-agents/blob/main/LICENSE), so copying/modification is legally permitted if the copyright and license notice are preserved.
- Public package/SDK/API/hosted service: **none found**. This is a prompt/instruction catalogue plus conversion/install tooling, not an orchestration runtime.

### What is directly reusable

The TOML conversion shape and small converter/installer mechanics are directly reusable code under MIT. The persona catalogue is technically copyable but should **not** be imported wholesale. AI-Content-OS already has stronger repository-specific contracts in `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`, `.codex/skills/`, and `.agents/skills/`.

Useful contract shape, expressed independently rather than copied:

```text
SpecialistRole = {
  id, objective, owned_files, prohibited_files, required_reading,
  allowed_tools, completion_checks, handoff_schema, stop_condition
}
```

### Inferred implementation pattern

**Inference:** source Markdown frontmatter is normalized into each agent platform's native configuration, while the full role body becomes system/developer instructions. A deterministic converter can validate unique names, required fields, file ownership, and prohibited actions before emitting platform-specific files.

### Project mapping

- Reuse existing project skills as source-of-truth; do not create a second persona catalogue.
- If one repeated bottleneck is proven, a project-owned role can be derived from the applicable `.codex/skills/<skill>/SKILL.md` and enforced by `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`.
- This is development governance around the repository, not `modules/ai_planner/` and not a `src/workflow_engine.py` stage. The runtime AI Planner plans content; it does not allocate coding agents.

### Risks

- Generic personas can conflict with protected-core, fallback-first, file ownership, and human approval rules.
- Installer scripts write to user-level agent directories; installation was not reviewed or authorized here.
- Large catalogues increase instruction conflicts, context/token cost, and maintenance surface.
- MIT permits reuse but requires preservation of notice; project-authored adaptations should record provenance.

### Smallest pilot

Create no agent yet. First run the same read-only evidence-review fixture with the current project skill/work-order path and one manually written specialist contract. Measure actionable findings, false findings, rework, elapsed time, token/cost, and ownership violations. Build a permanent role only if it wins repeatedly.

## 2. Claude Code x Remotion Workflow

### Source and exact product

- Halfdone: [Claude Code x Remotion — 설치 가이드 & 팀 소개 영상 워크플로우](https://halfdoneclub.co/community/vibe-coding/942f2ba4-0a04-4fe9-a788-43eebe300228)
- Product/source: [Remotion](https://www.remotion.dev/) and [remotion-dev/remotion](https://github.com/remotion-dev/remotion)

### Verified public code/packages

- Main monorepo: public and active; latest observed push `2026-07-13`; about 53k stars at audit time.
- npm packages observed at version `4.0.489`, published `2026-07-12`:
  - [`remotion`](https://www.npmjs.com/package/remotion): React composition primitives;
  - [`@remotion/renderer`](https://www.npmjs.com/package/@remotion/renderer): Node/Bun rendering;
  - [`@remotion/cli`](https://www.npmjs.com/package/@remotion/cli): Studio/render CLI.
- Official source is available, but it uses the [Remotion custom license](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md), not MIT. Individuals, nonprofits, and for-profit organizations with up to three employees are eligible for the free license; larger for-profit organizations require a company license. Derivative resale/relicensing is restricted.
- The separate [remotion-dev/skills](https://github.com/remotion-dev/skills) repository exposes many `SKILL.md` files but declared **no repository license was found**. Do not copy those files unless Remotion clarifies the license. Its package is marked private and is not a reusable public runtime package.
- Hosted API: Remotion has rendering products/options, but no external service is required for a local renderer pilot. Account/cloud use remains out of scope.

### What is directly reusable

The supported npm APIs are usable without copying Remotion internals, subject to license eligibility and a separately approved Node/React dependency boundary. The useful interface is:

```text
ShortsPlan JSON -> React Composition(inputProps)
                 -> preview in Studio
                 -> selectComposition()
                 -> renderMedia()
                 -> MP4 + render receipt + visual/audio QA
```

This is an independently stated integration interface, not copied vendor code. The current `modules/shorts/shorts_module.py` and `modules/shorts/shorts_exporter.py` can remain Python producers of stable JSON; a later isolated Node renderer can consume that export. No rewrite of the Shorts planning code is needed.

### Inferred implementation pattern

**Inference:** treat every video as deterministic data plus a reusable scene template. Resolve frame duration from input metadata, map scenes to timed sequences, validate assets before render, preview the same composition used for final rendering, and persist a receipt containing template version, props hash, renderer version, duration, codec, warnings, and fallback reason.

### Project mapping

- Producer: existing `modules/shorts/` planning/export contract.
- Future consumer: a standalone renderer outside `WorkflowEngine`, because current Shorts phases explicitly exclude rendering/TTS/publishing.
- QA: future tests should validate schema, frame boundaries, missing assets, deterministic duration, output existence, and representative frames; visual/audio checks belong under the `ai-content-os-shorts` and `ai-content-os-qa` approval gates.
- Fallback: if Node, Chromium, codec, font, or asset loading fails, preserve the current manual/offline export and record the failure; never regress `workflow_completed`.

### Risks

- Custom license and announced Remotion 5 license change require re-check at pilot time.
- Adds Node/React/Chromium/codec supply-chain and render-resource costs to a Python project.
- Fonts, music, stock assets, voice, likeness, and generated-media rights remain separate obligations.
- Templates can render successfully but still fail mobile readability, pacing, caption timing, or brand QA.
- Copying the unlicensed skills repository is not approved.

### Smallest pilot

When the Shorts renderer gate opens, render one 10–20 second synthetic fixture from existing exported JSON, with local assets only and no TTS/API/publishing. Compare deterministic output, setup time, render time, peak resources, representative-frame QA, and manual fallback. Do not connect it to `WorkflowEngine` during the pilot.

## 3. AI Service Monetization Case Collection

### Source and exact product

- Halfdone: [AI 서비스 수익화 사례집 — 기술 장벽이 무너진 지금, 실행이 답!](https://halfdoneclub.co/community/vibe-coding/47d5a6e0-2fca-4daf-96f8-adb781385bb2)

### Verified reusable code

- Linked public repository: **none found**.
- Public package/SDK/API/CLI: **none found**.
- Reproducible architecture, schema, benchmark fixture, or license covering implementation assets: **none found**.
- Primary-source support for the article's revenue, retention, valuation, user-count, cost, or time-saving claims: **none established in this audit**.

There is therefore no code to copy or integrate from this item. The only safe reuse is the product experiment pattern: one observed operator problem, one narrow MVP, one measurable outcome, and an explicit stop rule.

### Inferred implementation pattern

**Inference:** a reusable experiment ledger can store `problem_evidence`, `target_user`, `manual_baseline`, `smallest_solution`, `success_metric`, `observed_cost`, `observed_revenue`, `stop_condition`, and `decision`. Unknown values remain null; article claims must not seed forecasts.

### Project mapping and decision

- Map the method to future CardNews, Shorts, affiliate, brand, and advertising revenue experiments, not to a new runtime engine.
- **BENCHMARK** the small-MVP method.
- **REJECT** implementing a cloned SaaS or using the case-study numbers as ROI evidence.

### Smallest pilot

Choose one already documented operator pain, run the current manual path for a baseline, build at most one reversible helper, and continue only if measured time/quality/revenue evidence improves. No pilot is justified by this article alone.

## 4. CodeRabbit

### Exact product and verified availability

- Product: [CodeRabbit AI code reviews](https://www.coderabbit.ai/)
- Official CLI documentation: [Command-Line Review Tool](https://docs.coderabbit.ai/cli)
- Public documentation source: [coderabbitai/docs-public](https://github.com/coderabbitai/docs-public) — active, but **no repository license found**, so cite/read it; do not copy substantial documentation code.
- Actual review engine/service source: **none found**. The CLI calls CodeRabbit's service; it is not evidence of an open-source reviewer engine.
- Public SDK/API for embedding the review model into AI-Content-OS runtime: **none found**. The documented automation interface is the CLI and agent/headless authentication, not an in-process Python SDK.

### Exact reusable public assets

1. [coderabbitai/skills](https://github.com/coderabbitai/skills)
   - MIT, version `1.1.1` shown in README, latest observed push `2026-07-09`.
   - Contains portable `code-review` and guarded `autofix` `SKILL.md` contracts.
   - The directly reusable part is workflow instruction text/structure under MIT, not the review model.
2. [coderabbitai/claude-plugin](https://github.com/coderabbitai/claude-plugin)
   - MIT, latest observed push `2026-04-13`.
   - Packaging for Claude Code; useful as a plugin layout reference, unnecessary for the current Codex-first repository.
3. [coderabbitai/ast-grep-essentials](https://github.com/coderabbitai/ast-grep-essentials)
   - Apache-2.0, latest observed push `2026-06-03`.
   - Static `ast-grep` rules and tests across languages including Python. These can be reviewed and selectively vendored with license/notice preservation; they do not reproduce CodeRabbit AI review.
4. [coderabbitai/git-worktree-runner](https://github.com/coderabbitai/git-worktree-runner)
   - Apache-2.0, latest observed push `2026-06-12`.
   - Reusable Bash worktree tooling with command-trust controls; Windows support is Git Bash/WSL, not native PowerShell. It is optional because Codex worktrees and the project's ownership board already provide the core isolation mechanism.
5. `coderabbitai/coderabbit-pr-review`, VS Code repository, and Codex-related repositories inspected
   - No useful licensed reviewer source was established. `coderabbit-pr-review` contained only a one-line README; the VS Code and public docs repositories showed no declared license. **Not reusable as source.**

### Supported machine interface

Official CLI docs specify `cr review --agent` as newline-delimited JSON events. Relevant events are `review_context`, `status`, `heartbeat`, `finding`, `complete`, and `error`; a finding carries severity, file name, agent-oriented fix instructions/suggestions, or a human comment. This is sufficient for a bounded external review adapter, without reverse engineering.

```text
local diff -> cr review --agent
           -> validate JSONL event schema
           -> normalize finding(severity, file, message, evidence)
           -> independently verify against repository code
           -> human/CTO-approved fix lane
           -> native tests + optional second review, maximum two passes
```

### Project mapping

- Use as an optional external reviewer after native checks governed by `.codex/skills/ai-content-os-qa/SKILL.md` and `.codex/skills/ai-content-os-commit-check/SKILL.md`; it cannot replace compile, unit/regression, workflow, JSON, or visual QA.
- Review output is untrusted advisory data. It must not execute commands, access credentials, expand file scope, edit protected/shared documents, or approve its own fix.
- The existing `docs/ACTIVE_PARALLEL_WORK_ORDERS.md` supplies ownership boundaries. CodeRabbit findings may open a new file-owned lane only after CTO validation.
- It has no content-runtime role and must never be called from `src/workflow_engine.py`.

### Security, data, cost, and vendor risks

- Official CodeRabbit skill instructions state that code diffs are sent to the CodeRabbit API. Secret scanning and explicit repository/data approval are mandatory before any test.
- Authentication/account, organization resolution, retention, subprocess/binary provenance, network availability, rate limits, and per-file overage are external dependencies.
- The CLI is open beta and service behavior can change independently of this repository.
- Reviewer comments and suggested commands are untrusted input and can be wrong or prompt-injection-bearing.
- A dirty worktree makes broad `all` review expensive/noisy; any pilot must use a controlled fixture or narrow diff.
- The MIT skills are not a substitute for the proprietary service, and installing them does not create offline review capability.

### Smallest pilot

Do not install against the active dirty worktree. After explicit account/data approval, use a disposable branch/worktree containing one known-good Python defect fixture and one clean control. Run native tests first, then one `--agent` review with a fixed file scope; independently score true positives, false positives, missed seeded defects, elapsed time, transmitted scope, and cost. Stop after one verification pass. Adopt only if it adds material findings beyond current QA without ownership/security violations.

## Recommended Build / Buy Boundary

### Build and own

- Repository-specific specialist role contracts and evaluation receipts.
- Work-order/file-ownership enforcement using the existing project governance.
- Stable Shorts JSON export and render receipt schema.
- Review-finding normalization, independent validation, and native QA gates if an external reviewer is later approved.

### Integrate or buy

- Remotion rendering APIs instead of creating a video compositor, after the Shorts/license gate.
- CodeRabbit review service instead of rebuilding a general AI reviewer, only after data/account/cost approval.

### Reuse selectively

- MIT `agency-agents` converter concepts or small script portions only when a concrete project-owned role is approved.
- MIT CodeRabbit skill safety patterns and Apache-2.0 Python `ast-grep` rules after line-by-line license/security/false-positive review.

### Do not reuse

- Wholesale persona catalogues.
- Unlicensed Remotion skills or CodeRabbit documentation/repository code.
- Proprietary reviewer internals, private prompts, or authenticated traffic.
- Halfdone monetization claims as technical or financial evidence.

## Approval Gates

1. CTO identifies a measured bottleneck and a single owner.
2. Existing project capability is checked before any dependency or agent is added.
3. Exact version, source, checksum/signature where available, transitive dependencies, license, and maintenance are revalidated.
4. Data leaving the machine, account permissions, retention/deletion, cost ceiling, and revocation are approved.
5. Pilot uses a disposable fixture/worktree, least privilege, one writer per file, deterministic stop condition, and no protected-core changes.
6. Native QA remains authoritative; external agents/reviewers cannot self-approve.
7. Failure preserves offline/manual behavior and cannot break `workflow_completed`.

## Implementation Status

**Research complete / implementation not approved.** No package, agent, skill, plugin, CLI, account,
API, renderer, dependency, or runtime stage was installed or connected. Any reuse below requires a
separate file-owned Sprint with version/license revalidation and fixture-based QA.

## Final Handoff

- **Exact code reusable under a clear license:** `agency-agents` Markdown/converters/installers (MIT); `coderabbitai/skills` (MIT); `coderabbitai/claude-plugin` (MIT, but not needed); selected `ast-grep-essentials` rules/tests (Apache-2.0); `git-worktree-runner` (Apache-2.0, optional); Remotion npm/source only under its custom eligibility/company-license terms.
- **No reusable code found:** Halfdone monetization case collection; CodeRabbit's actual AI review engine; a public CodeRabbit in-process SDK/API; licensed Remotion skills repository content.
- **Current runtime impact:** none. No package, account, plugin, agent, API, renderer, or `WorkflowEngine` stage was added.
