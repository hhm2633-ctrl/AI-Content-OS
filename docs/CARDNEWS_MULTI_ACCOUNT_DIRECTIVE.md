# CardNews Multi-Account Product Directive

Status: USER DIRECTIVE — highest-priority CardNews product rule

Date recorded: 2026-07-16

## 1. Product Shape

AI-Content-OS CardNews is a **multi-account system**. It is not one account that mixes every
category. Each account has its own category portfolio, audience, issue-selection rules, learned
Instagram patterns, voice, visual system, CTA policy, and performance history.

Initial examples supplied by the project owner; they are examples to refine, not a license to
collapse all categories into one account:

- Account group A: 국내뉴스, 세계뉴스, 사건, 세계사건
- Account group B: 이슈, 썰, 도파민, 썸, 감정
- Account group C: 패션, 뷰티

Category normalization may share a common engine, but account-level selection, editorial angle,
hook/story/CTA, visual identity, risk tolerance, and learning must remain separated.

## 2. Slide Count Is Variable

Four slides are **not** the canonical product contract. Four-slide
`HOOK -> PROBLEM -> SOLUTION -> CTA` is only one legacy template.

The slide count and roles must be chosen from current, actually observed Instagram CardNews/
carousel patterns and the needs of the selected account/category/topic. Do not force a topic into
four slides. The system must learn and support variable-length carousels after current Instagram
examples are reviewed. No fixed slide-count claim is allowed without evidence by account/category.

## 3. Carousel Media Is Hybrid and Role-Driven

CardNews is **not a static-PNG-only product**. One Instagram carousel may mix:

- editorial text/image panels;
- source screenshots or evidence panels;
- short video clips;
- motion graphics or animated text;
- example/resource panels;
- CTA or account-brand outro panels.

Choose `media_type` separately for every slide after considering the selected account/category/topic,
the number of useful examples or evidence items, source and rights status, and the role of that slide.
The minimum planning contract is:

```text
slide_role
media_type: image | video | screenshot | editorial | motion_graphic
headline/body
source_credit
rights_status
optional duration/transition/motion direction
```

The project owner's Instagram screen recording reviewed on 2026-07-16 showed current examples such
as 7 slides (cover + 5 moving examples + brand outro), 9 slides (cover + 7 examples + outro),
10 slides (cover + 8 examples + outro), and 8 slides (cover + intro + 5 resource examples + CTA).
These are observed pattern evidence, **not new fixed templates**. A topic with three strong examples
must not be padded to match them, and a topic with eight useful examples must not be compressed into
four legacy roles.

Generated or animated media must never be presented as source footage or factual evidence. Tool and
provider choices remain replaceable production adapters; they must not become the CardNews product
contract.

### 3.1 Account C Fixed AI Lifestyle Model

Account C auxiliary lifestyle scenes must reuse `account_c_fixed_model_01`; do not generate a new
random human identity for each card or scene. Every new scene generation must include both the
authoritative face references and the authoritative body references registered in
`config/account_c_fixed_ai_model.json`. Expression, pose, wardrobe, setting, and composition may
change, but face geometry, age impression, skin tone, hairline, body build, shoulder width, limb
thickness, and torso/leg proportions may not. Reject rather than publish any output with visible
identity or body drift.

This fixed model is limited to clearly labelled auxiliary AI lifestyle scenes. It must not replace a
real celebrity, witness, customer, brand model, product image, source screenshot, or news evidence.

## 4. Required End-to-End Order

```text
reliable broad data collection
-> same-event/topic clustering
-> freshness, recurrence, source, risk, evidence, and account/category fit
-> account-specific candidate portfolios
-> Instagram-learned hook/story/visual/CTA pattern binding
-> variable-length, mixed-media CardNews planning
-> source, rights, and asset-readiness gate
-> production-quality image/video/editorial rendering
-> account-specific QA
-> publish approval
-> account-specific performance learning
```

Instagram learning data must affect actual selection and production decisions. Saving patterns in a
registry without consuming them in topic selection, story planning, layout, typography, imagery,
and CTA is not learning completion.

## 5. Current Truth and Completion Language

The project is currently blocked/incomplete at the **first data-collection section**. Renderer,
schema, QA, or `workflow_completed` results do not mean the operational CardNews system is nearly
complete.

Until collection coverage, live-data quality, and downstream input readiness are verified, reports
must say exactly:

- collection foundation: incomplete/blocked where evidence shows it;
- renderer or standalone modules: implemented only in their narrow scope;
- operational multi-account CardNews automation: not complete;
- publish-ready system: not complete.

Never convert module count, test count, PNG generation, or workflow completion into a percentage or
near-completion claim for the product.

## 6. Priority Freeze

CardNews multi-account collection, discovery, selection, learned production, and real output quality
are the active priority. Do not redirect the active implementation to Commerce, Shorts, or unrelated
future expansion unless the project owner explicitly changes this directive.
