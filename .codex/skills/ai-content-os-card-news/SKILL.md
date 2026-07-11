---
name: ai-content-os-card-news
description: AI-Content-OS 카드뉴스의 4장 구조, 기존 10개 레이아웃, Pillow 렌더링, typography, visual rhythm, evidence/social proof, mobile readability, attribution과 production QA를 설계·구현·검수할 때 사용한다.
---

# Card News

## Context

Read `modules/card_news/`, `templates/card_news_layout_rules.json`, the related content/image results, and focused tests. Inspect generated PNGs visually when layout or typography changes.

## Workflow

1. Preserve the canonical `hook -> problem -> solution -> cta` four-slide contract.
2. Reuse the existing 10 layouts and `CardNewsModule` Pillow renderer.
3. Apply evidence only when topic relevance, copyright permission, and asset role all pass.
4. Use only real comment/reaction text for social proof; mask identities and scrub PII.
5. Plan text before drawing; preserve minimum font size, safe margins, attribution, and CTA space.
6. Keep metadata failures additive and fall back to the default renderer.

## Protected Contracts

- Do not add an 11th layout without explicit approval.
- Do not change slide count or roles as a local styling fix.
- Do not fabricate screenshots, comments, comparisons, or source attribution.
- Do not silently truncate content; show an ellipsis only at the hard limit.
- Do not replace `CardNewsModule` or alter `WorkflowEngine` for renderer work.

## Verification

Run `tests/test_card_news_production_quality.py`, relevant regression tests, compile, full workflow, and visual inspection of all four PNGs. Confirm `card_news_completed`, `publishing_ready`, and `workflow_completed`.
