---
name: ai-content-os-research-intelligence
description: AI-Content-OS의 ResearchModule, 근거 수집, research context, insight 생성, 출처 신뢰도와 콘텐츠 근거 연결을 분석하거나 수정할 때 사용한다. 외부 원자료를 프로젝트 지식으로 반영하는 작업은 ai-content-os-research와 함께 사용한다.
---

# Research Intelligence

## Context

Inspect `modules/research/`, `storage/research/research_result.json`, relevant `docs/RESEARCH/`, and upstream topic/pattern outputs. Do not re-read the full repository.

## Workflow

1. Separate raw source facts, project-authored analysis, and generated content suggestions.
2. Trace each insight to a source or label it as inference.
3. Preserve the ResearchModule result contract and downstream ContentModule inputs.
4. On LLM or network failure, return structured fallback content with the reason recorded.
5. Save durable external analysis through `ai-content-os-research`; do not silently bury it in runtime JSON.

## Evidence Rules

- Never present competitor references as evidence for the selected topic.
- Never invent citations, metrics, quotes, or source access.
- Prefer primary sources when browsing; preserve source URLs and retrieval status.
- Keep unavailable evidence explicit rather than filling it with plausible text.

## Verification

Run focused research/content contract tests, compile, then the full workflow when behavior changes. Confirm `04_research_result.json` and `workflow_completed`.
