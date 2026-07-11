---
name: ai-content-os-coupang
description: AI-Content-OS의 Coupang/commerce 콘텐츠 확장, 상품 근거, 제휴 링크, 가격·재고·혜택 데이터, 리뷰 활용과 플랫폼 정책을 설계하거나 검토할 때 사용한다. 현재 구현 전 Roadmap 및 외부 데이터 승인 게이트를 적용한다.
---

# Coupang

## Current State

Treat Coupang as a Roadmap capability until the user approves a dedicated Sprint. Do not attach commerce code to the protected card-news pipeline during planning.

## Planning Workflow

1. Define the content goal: comparison, buying guide, deal alert, product card, or affiliate post.
2. Require a real product source for name, seller, price, stock, options, rating, reviews, and images.
3. Separate stable product facts from volatile price, discount, shipping, and inventory fields.
4. Define affiliate disclosure, link ownership, image rights, update cadence, and stale-data behavior.
5. Reuse Research, Content, Card News, Publishing, and QA contracts through additive adapters.

## Gates

- Never fabricate prices, stock, discounts, reviews, rankings, or purchase claims.
- Never publish an affiliate link without disclosure and user-approved account ownership.
- Never store access keys in source or print `.env`.
- Use `unavailable` or manual verification when live product data cannot be confirmed.

## Deliverable

Produce a scoped proposal with approved data source, schema, freshness policy, fallbacks, compliance checks, tests, and ROI before implementation.
