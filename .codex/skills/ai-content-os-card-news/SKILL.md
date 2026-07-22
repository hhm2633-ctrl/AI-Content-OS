---
name: ai-content-os-card-news
description: AI-Content-OS 카드뉴스의 승인된 가변 슬라이드 구조, 기존 10개 레이아웃, Pillow 렌더링, typography, visual rhythm, evidence/social proof, mobile readability, attribution과 production QA를 설계·구현·검수할 때 사용한다.
---

# Card News

## Context

Read `modules/card_news/`, `templates/card_news_layout_rules.json`, the related content/image results, and focused tests. Inspect generated PNGs visually when layout or typography changes.

## Workflow

1. Require owner selection and explicit production authorization before any rendering.
2. Derive slide count, roles, and sequence from the approved variable-slide production plan; do not force a universal narrative sequence.
3. Reuse the existing 10 layouts and preserve the protected `CardNewsModule` Pillow renderer and fallback behavior.
4. Apply evidence only when topic relevance, copyright permission, and asset role all pass.
5. Use only real comment/reaction text for social proof; mask identities and scrub PII.
6. Plan text before drawing; preserve minimum font size, safe margins, attribution, and CTA space.
7. Keep metadata failures additive and fall back to the default renderer.
8. Treat variable-plan, controller, and renderer linkage as operational only after a successful current end-to-end execution proves the exact call path.

## Protected Contracts

- Do not add an 11th layout without explicit approval.
- Do not force a fixed slide count or change the approved slide count and roles as a local styling fix.
- Do not fabricate screenshots, comments, comparisons, or source attribution.
- Do not silently truncate content; show an ellipsis only at the hard limit.
- Do not replace `CardNewsModule` or alter `WorkflowEngine` for renderer work.

## Verification

Run `tests/test_card_news_production_quality.py`, relevant regression tests, compile, full workflow, and visual inspection of every generated slide. Confirm `card_news_completed`, `publishing_ready`, and `workflow_completed` only when the current authorized execution directly produces those states.
