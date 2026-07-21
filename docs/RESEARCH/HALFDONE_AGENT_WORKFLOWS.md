# Halfdone Agent and AI-Assisted Workflow Research Handoff

Date: 2026-07-13  
Future owner: **CTO / Integration — Agent Orchestration and Delivery Governance**  
Status: **RESEARCH ONLY / BACKLOG — no implementation, installation, runtime change, or external action is authorized**

## Source Type

- Public community guides about specialist AI-agent personas, agent-assisted Remotion production, and AI-service MVP case studies.
- Primary references used only to verify product/tool capabilities:
  - [agency-agents repository](https://github.com/msitarzewski/agency-agents)
  - [Claude Code custom subagents](https://code.claude.com/docs/en/sub-agents)
  - [Claude Code parallel-agent choices](https://code.claude.com/docs/en/agents)
  - [Remotion official site, workflow, and licensing](https://www.remotion.dev/)

Halfdone sources covered:

1. [AI agency / specialist-agent guide](https://halfdoneclub.co/community/vibe-coding/d1a97046-8394-464a-a4dd-c3ab84d5cc6a)
2. [Claude Code and Remotion workflow guide](https://halfdoneclub.co/community/vibe-coding/942f2ba4-0a04-4fe9-a788-43eebe300228)
3. [AI-service monetization case collection](https://halfdoneclub.co/community/vibe-coding/47d5a6e0-2fca-4daf-96f8-adb781385bb2)

The source prompts, course sequence, and proprietary wording are not reproduced here. This document preserves only high-level, project-specific conclusions.

## CTO Summary

The useful idea is not to import a large catalogue of personas. It is to select a small specialist role only when a recurring, bounded concern benefits from isolated context, explicit tool limits, and a fixed handoff contract. This reinforces the repository's existing delegation rules rather than replacing them.

The agency-agents repository confirms that specialist agent definitions can encode a role, workflow, deliverables, and success criteria. Claude Code's official documentation confirms that subagents provide separate context, custom instructions, and restricted tools, and that parallel work should be partitioned when files do not overlap. These capabilities do not prove that a community persona is accurate or suitable for AI-Content-OS.

The Remotion guide contributes a separate production lesson: a structured `spec -> preview -> feedback -> render -> QA` loop and parameterized templates are useful for future Shorts work. Remotion officially supports React-based programmatic video, Studio preview, parameterized workflows, agent skills, and local/server rendering. This is a secondary handoff to the future Shorts owner, not permission to install or integrate Remotion now.

The monetization case collection contributes only the conservative product principle `small problem -> narrow MVP -> observed user result -> measured iteration`. Its revenue, retention, valuation, time-saving, and growth figures were not established here from primary evidence and must not be used for forecasts, prioritization scores, or marketing claims.

## What To Adopt

### Adopt Now — governance and process only

No runtime or new agent is required to adopt these practices:

- Start with one bounded specialist lane; expand only after a repeated need and measured benefit.
- Define every lane with objective, owned files, prohibited files/actions, required reading, completion checks, and handoff format.
- Give one writer ownership of each file and keep shared status documents and Git in the CTO/integration lane.
- Separate reusable process knowledge (project skill) from an isolated worker (agent/subagent). Prefer a skill when the work needs shared repository context; prefer a worker when the task is independent, verbose, or needs narrower tool permissions.
- Require evidence and repository-specific contracts to override persona confidence, generic playbooks, or unsupported numeric advice.
- Keep specialist output advisory until CTO integration review; a specialist cannot approve its own architecture, QA, policy, publishing, or commercial claim.
- Compare a specialist pilot against the current Work/Codex path using actual elapsed time, review defects, rework, token/cost use, and ownership violations.
- Use the same small-MVP discipline for product ideas: solve one verified operator pain before proposing a new service or platform.

These points are already substantially represented by `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`, `docs/AI_PLANNER.md`, and `docs/WORK_CODEX_CAPABILITY_AUDIT.md`. The research does not authorize edits to those documents; the future owner should consolidate rather than duplicate rules.

### Roadmap — approval required

- Evaluate one repository-specific specialist role only when a recurring bottleneck is documented. Suitable first candidates are read-only independent QA, evidence review, or a narrowly scoped design review—not autonomous publishing or business operations.
- If a reusable agent contract is justified, build it from project skills and repository contracts rather than copying a community persona verbatim.
- Add an evaluation fixture that compares the specialist against the current baseline on the same bounded task.
- Route the Remotion concept to the future Shorts owner as a possible renderer/template candidate after the existing Shorts approval gates. Preserve the current offline/manual path and do not connect it to `WorkflowEngine` by default.
- Consider a standalone orchestration/evaluation layer only if several validated specialists create a repeated coordination burden. This must remain additive and must not become a second uncontrolled project workflow.

## What To Reject

- Installing or enabling an entire third-party agent catalogue.
- Treating persona wording, confidence, claimed experience, or embedded numeric rules as verified expertise.
- Copying Halfdone prompts, course structure, or community-agent text into project files.
- Allowing two agents to write the same file, letting workers edit shared status documents by default, or delegating final Git/integration ownership.
- Giving specialist agents broad filesystem, credential, browser, account, publishing, payment, or external messaging permissions.
- Nested or unbounded delegation without a CTO-owned work order, token/cost ceiling, and deterministic stop condition.
- Building an agent marketplace, autonomous AI agency, or new SaaS because a case study reports large revenue.
- Using the Halfdone case-study revenue, retention, valuation, user-count, time-saving, or cost figures as project evidence. Their primary-source support remains `UNKNOWN` in this handoff.
- Assuming Remotion or AI coding removes engineering, licensing, asset-rights, rendering, accessibility, or visual-QA work.
- Replacing the protected `WorkflowEngine`, existing project skills, or mandatory human approval gates with persona routing.

## AI-Content-OS Engines Affected

### Current

None. This research has no runtime-engine effect and introduces no new module, stage, API, dependency, agent, skill, plugin, or account connection.

### Future responsibility map

| Concern | Responsible future owner | Boundary |
|---|---|---|
| Specialist selection and work-order contract | CTO / Integration — Agent Orchestration and Delivery Governance | Repository process only; no autonomous production authority |
| Specialist evaluation and regression evidence | Independent QA assigned by CTO | Read-only unless a separate file-owned fix lane is opened |
| Project-specific reusable instructions | Relevant project-skill owner | Update only after duplication and evidence review |
| Remotion/template production concept | Future Shorts owner | Standalone/manual pilot first; no `WorkflowEngine` coupling |
| Product/MVP experiment | CTO / Product owner | Real problem evidence and measured results required |

Potentially affected documents in a later, separately approved integration lane are `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`, `docs/AI_PLANNER.md`, and `docs/WORK_CODEX_CAPABILITY_AUDIT.md`. They are references, not change requests from this research.

## Suggested Data Structures

The following are planning sketches only:

```json
{
  "specialist_role_contract": {
    "role_id": "read_only_evidence_reviewer",
    "objective": "one bounded concern",
    "owned_files": [],
    "prohibited_files": [],
    "allowed_tools": ["read", "search"],
    "prohibited_actions": ["git", "external_write", "account_access"],
    "required_reading": [],
    "completion_checks": [],
    "handoff_schema": "finding_severity_evidence_recommendation",
    "budget_ceiling": null,
    "approval_owner": "cto_integration"
  }
}
```

```json
{
  "specialist_evaluation_receipt": {
    "task_fixture": "fixture-id",
    "baseline": "work_codex_current_path",
    "elapsed_seconds": null,
    "token_or_cost_observed": null,
    "actionable_findings": null,
    "false_or_unsupported_findings": null,
    "rework_count": null,
    "ownership_violations": null,
    "decision": "unknown | reject | revise | approve_for_narrow_use"
  }
}
```

Unknown values must remain `null` or `unknown`; they must not be estimated and stored as measured outcomes.

## Workflow Impact

- **Current impact:** none.
- The protected `WorkflowEngine` order and `workflow_completed` contract are unchanged.
- Future specialist routing, if approved, belongs to the development/delivery process around the repository. It is not a content-runtime stage.
- A future Remotion experiment belongs to the standalone Shorts production path and must retain a manual/file fallback.
- External-service failures, worker failures, or unavailable agents must remain non-blocking to the existing CardNews workflow.

## Sprint Impact

No current Sprint scope is changed.

A future pilot may be opened only as a small, isolated work order after active QA/integration lanes close. Recommended sequence:

1. Select one recurring, evidence-backed bottleneck.
2. Define one specialist contract and a baseline fixture.
3. Run read-only or advisory evaluation with no external side effects.
4. Compare measured quality, cost, rework, and ownership compliance.
5. Reject, revise, or approve only that narrow role.

The Remotion path requires its own Shorts Sprint and is not part of an agent-governance pilot.

## Roadmap Impact

Backlog candidates, not approved roadmap commitments:

- `Agent Specialist Evaluation`: one-role fixture, least-privilege tools, handoff receipt, and baseline comparison.
- `Delivery Orchestration Audit`: determine whether existing skills plus work orders already solve the need before creating another layer.
- `Shorts Renderer Evaluation`: compare Remotion with the existing manual/offline package after Shorts rendering is explicitly approved.
- `MVP Evidence Loop`: require problem evidence, success metric, cost ledger, and stop condition before new service experiments.

No item authorizes a new project, runtime module, API, account, scheduler, publishing path, or agent installation.

## Approval Gates

Before any specialist-agent pilot:

1. CTO confirms a repeated bottleneck and names the single future owner.
2. Existing project skills and current Work/Codex capabilities are checked for duplication.
3. Third-party license, source, maintenance, prompt content, scripts, and requested permissions are reviewed.
4. The work order fixes owned/prohibited files and one-writer-per-file ownership.
5. Tools use least privilege; credentials, external writes, Git, account actions, publishing, payment, and messaging remain blocked unless separately authorized.
6. An evaluation fixture, baseline, success criteria, budget ceiling, retry/stop rule, and handoff schema are approved.
7. Independent QA reviews unsupported claims, ownership compliance, and regressions.
8. CTO/integration alone accepts the result and performs any final shared-document or Git action.

Additional gates before Remotion evaluation:

- Shorts phase and renderer pilot explicitly approved.
- Current Remotion license and intended organizational/automation use reviewed from official terms.
- Asset, font, music, image, voice, and likeness rights recorded.
- Local/manual fallback, render cost/time measurement, and visual/audio QA defined.

## ROI

| Candidate | Expected ROI | Confidence | Reason |
|---|---:|---:|---|
| Adopt stricter specialist work-order/governance checks | High | High | Low change cost; reduces ownership, context, and review failures |
| Pilot one read-only specialist on a recurring bottleneck | Medium | Medium | May reduce context/review load, but must beat the current path in measured tests |
| Import many community personas | Negative | High | Duplication, token cost, conflicting rules, permission risk, and maintenance burden |
| Remotion renderer/template pilot | Medium later | Medium | Useful for repeatable Shorts, but separate licensing, rendering, and QA costs apply |
| Build a new AI service from monetization examples | Unknown | Low | No validated user problem, unit economics, or primary evidence in this handoff |

No revenue or time-saving projection is approved. ROI must be recalculated from actual project receipts.

## Implementation Status

**Research-only / backlog.**

- No agent, skill, plugin, MCP, Remotion package, or external repository was installed.
- No production workflow, account, API, credential, browser automation, rendering, publishing, monetization, or SaaS implementation was created or approved.
- No `WorkflowEngine` integration is proposed for the current phase.
- The source URLs and consolidated conclusions are preserved for the future Agent Orchestration/CTO owner; the Remotion boundary is explicitly routed to the future Shorts owner.

## Codex Notes

- The three sources overlap on MVP-first execution and AI-assisted iteration; those ideas are consolidated once rather than treated as three separate implementation proposals.
- The first source's high-level agent catalogue shape is corroborated by the repository's own README, but catalogue size and popularity are volatile and irrelevant to adoption.
- Official Claude Code documentation supports specialist context isolation, tool restrictions, foreground/background work, and parallel execution. It also warns that parallel paths multiply token usage and that overlapping file writes need isolation/partitioning.
- Official Remotion material supports programmatic React video, Studio preview, parameterized templates, agent skills, rendering options, and a license distinction based on organization/use. Exact cost and license obligations must be rechecked at pilot time.
- Halfdone's monetization metrics and third-party success stories remain unverified and intentionally excluded from project forecasts.
- This document is a planning handoff, not proof that any proposed role, renderer, or business model will improve AI-Content-OS.
