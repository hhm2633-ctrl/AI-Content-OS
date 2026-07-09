# Knowledge Engine

## Purpose

The Knowledge Engine defines how external material becomes project knowledge.

External sources are analyzed by ChatGPT acting as CTO. Claude and Codex do not re-analyze raw materials unless explicitly instructed. They use the CTO analysis result saved in GitHub documents.

## Processing Flow

```text
Material Collection
-> CTO Analysis
-> Project Asset Documentation
-> Sprint Classification
-> Codex Work Order
-> Implementation / Review
```

## Rules

- Store only analyzed conclusions that are useful to AI-Content-OS.
- Keep raw-source dependency low.
- Convert research into roadmap items, module specs, or sprint work.
- Do not let research expand the current MVP scope without ROI review.

## ROI Standard

- Direct contribution to the card news MVP: priority
- Shorts, video, dashboard, and report systems: roadmap
- External SaaS-dependent features: later priority

## Current Planning Targets

- Competitor Engine
- Audit Engine
- AI Planner
- Template and Layout research from AlphaCut
