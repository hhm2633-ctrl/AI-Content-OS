---
name: ai-content-os-research
description: ChatGPT CTO가 분석한 외부 자료를 AI-Content-OS 프로젝트 지식으로 문서화하는 절차. 원자료 재분석 없이 분석 결과를 docs/RESEARCH와 관련 문서에 반영한다.
---

# AI-Content-OS Research Knowledge Skill

## Purpose

Use this skill when the user provides CTO-analyzed external materials that must be saved into the repository.

External materials include:

- PDF
- screenshots
- SaaS tools
- competitor services
- YouTube or Instagram references
- AI workflow guides
- UI references

## Critical Rule

Codex does not re-analyze raw external material unless explicitly asked.

The standard process is:

```text
User material
↓
ChatGPT CTO analysis
↓
Repository research document
↓
Roadmap/Sprint integration
↓
Implementation later
```

## Required Folder

Use:

```text
docs/RESEARCH/
```

## Standard Research Document Structure

Each research document should include:

```markdown
# Title

## Source Type

## CTO Summary

## What To Adopt

## What To Reject

## AI-Content-OS Engines Affected

## Suggested Data Structures

## Workflow Impact

## Sprint Impact

## Roadmap Impact

## ROI

## Implementation Status

## Codex Notes
```

## Required Index Updates

When adding research docs, update or create:

```text
docs/RESEARCH_INDEX.md
```

Index columns:

- Date
- Source
- Type
- ROI
- Adopt / Roadmap / Reject
- Related Engines
- Status

## Current Research Items To Preserve

### AlphaCut UI

Adopt:

- Template Engine
- Layout Engine
- Highlight Engine
- Rendering Engine

Roadmap:

- Timeline Engine
- Animation Engine
- Video Renderer

Reject:

- manual drag editing
- user-driven animation setup

Suggested structure:

```text
Project -> Template -> Scene -> Layer -> Component -> Animation -> Render
```

### Claude Instagram Audit

Adopt:

- Competitor Engine
- Audit Engine
- Brand DNA Engine
- Hook Analyzer
- Content Pillar Engine
- Format Analyzer
- Posting Time Analyzer
- Blind Spot Engine
- Growth Score Engine
- Content Score Engine

KPI:

- Save Rate
- Share Rate
- Comment Rate
- Hook Retention
- Brand Consistency

Reject for now:

- Windsor.ai direct dependency

### Claude + Codex Workflow

Adopt:

- ChatGPT = CTO
- Claude = large implementation / complex refactor
- Codex = repository changes / compile / test / git diff / docs
- AI Planner
- AI Task Router
- AI Cost Optimizer
- Sprint Planner

Routing rule:

- 1-3 files -> Codex
- 4-7 files -> ChatGPT decomposes and decides
- 8+ files or complex refactor -> Claude draft, Codex verifies
- Repository verification -> Codex

## Related Docs To Update When Relevant

- `PROJECT_MASTER.md`
- `PROJECT_SNAPSHOT.md`
- `ROADMAP.md`
- `DECISIONS.md`
- `MODULE_STATUS.md`
- `CHANGELOG.md`

## Do Not

- Do not implement new engines during research documentation.
- Do not modify WorkflowEngine.
- Do not create runtime files.
- Do not add external API dependencies.
