# Evidence Requirements

The single rule underlying every brief in this portfolio: **a claim without a real, checkable
source is not written as fact.** This mirrors the fail-closed contract already established in
`docs/COMMERCE_PHASE_1_CONTRACT.md` and the CardNews evidence-selection gate
(`MODULE_STATUS.md` Phase M7), extended here to the full content portfolio.

## Tiering

| Tier | Definition | Example content types |
|---|---|---|
| No evidence needed | Common-knowledge, non-factual, or purely procedural content with no statistical/regulatory claim | Lifestyle checklists, general how-to steps, minimalism/organization tips |
| Soft evidence recommended | A claim that reads as generalizable advice; a citation strengthens trust but its absence doesn't make the content false | Productivity tips, general wellness framing (non-medical) |
| Hard evidence required (`SOURCE_REQUIRED`) | A specific statistic, ranking, or "trending" claim | Trend-explainer content, any cited statistic |
| Official-source required (`CURRENT_DATA_REQUIRED`) | Law, tax, consumer-rights, financial-regulation, or procedural-government content | 연말정산, 신용점수, 전세 계약, 이직 서류, 육아휴직 신청, 자동차 정기점검, 세금 용어, 저작권, 개인정보보호, 온라인 쇼핑 환불 규정, 소비자 권리 |
| Real-time verification required (`PRICE_VERIFICATION_REQUIRED`) | Price, stock, discount, shipping, ranking, review count, rating | All Commerce guide/comparison content |
| Rights confirmation required (`RIGHTS_REVIEW_REQUIRED`) | Any non-self-authored image, review quote, brand asset, or community text | Any content using a photo, review, or brand asset not created in-house |
| Operator/policy gate required (`OPERATOR_APPROVAL_REQUIRED` / `PLATFORM_POLICY_REVIEW_REQUIRED`) | Sponsored content, affiliate content, anything with a real monetization path | BrandConnect, Affiliate-conversion candidates |

## Fail-closed rule

If the required evidence tier for a brief cannot be met at write time:

1. The claim is **not written**, not softened into a vague approximation, and not replaced
   with a plausible-sounding placeholder number.
2. The field is marked with the matching token (`SOURCE_REQUIRED`,
   `PRICE_VERIFICATION_REQUIRED`, `RIGHTS_REVIEW_REQUIRED`, `CURRENT_DATA_REQUIRED`,
   `OPERATOR_APPROVAL_REQUIRED`, `PLATFORM_POLICY_REVIEW_REQUIRED`) in the brief's
   `blocker_codes` and/or `volatile_claims`.
3. `current_readiness` reflects the real blocked state (`blocked_by_data`,
   `blocked_by_rights`, `not_approved`, or `planning_only`), never `implemented` or
   `offline_ready`.
4. `fallback_behavior` describes what the content team should do instead (usually: publish a
   reduced, evidence-safe version, or hold the piece entirely).

## What this portfolio never invented

Per the explicit list in the CTO instruction, no brief in `CONTENT_BACKLOG.json` contains a
real price, discount rate, stock count, sales volume, ranking, review count, rating, product
efficacy claim, a specific person's real quoted statement, a current news fact, real Instagram
performance data, competitor-account performance data, market share, or purchase-conversion
rate. This is verified mechanically, not just claimed: `tools/build_portfolio.py::run_qa()`
regex-scans every string value in every brief and pattern for price-like, percentage-discount,
rating-point, ranking, stock-count, and review-count patterns and asserts zero matches (see
`QA_REPORT.md`).

## Evidence placement inside a brief

For CardNews specifically, evidence has one designated home: slide 3
("evidence-backed solution"). Slides 1, 2, and 4 are evidence-free by contract
(`evidence_placement: "없음"` on slides 1 and 4) so that a missing citation never blocks the
hook or CTA slides -- only the solution slide's claims are gated, and if evidence cannot be
sourced for it, the brief's `fallback_behavior` calls for reducing that slide to general
advice rather than deleting the whole piece.
