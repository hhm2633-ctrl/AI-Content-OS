# Content Portfolio V1

Independent content-design asset for AI-Content-OS, produced outside `modules/`, `tests/`,
`docs/`, `storage/`, `config/`, and `site/`. This folder is self-contained: it does not change
any existing module, test, or shared status document, and it connects to nothing at runtime.

## What this is

A ready-to-hand-off content backlog and learning-pattern seed set covering the full content
portfolio AI-Content-OS could eventually produce: CardNews, Shorts/Reels, Instagram feed,
BrandConnect, Commerce guides, and Knowledge/Evergreen content. Every brief is a **design
asset for a copy/production team to complete**, not finished, publishable copy -- no brief
here has ever been posted, and none is connected to `WorkflowEngine` or any existing module.

## What this is not

- Not a new module, not a code change, not a Sprint proposal for implementation.
- Not real product data, real prices, real reviews, real Instagram performance, or real
  brand facts. Anywhere a real-world value would be required, the brief says so explicitly
  (`SOURCE_REQUIRED`, `PRICE_VERIFICATION_REQUIRED`, `RIGHTS_REVIEW_REQUIRED`,
  `CURRENT_DATA_REQUIRED`, `OPERATOR_APPROVAL_REQUIRED`, `PLATFORM_POLICY_REVIEW_REQUIRED`)
  instead of inventing a value.
- Not a publishing action of any kind. Nothing here was posted, uploaded, purchased, or
  linked to an affiliate account.

## Files

| File | Purpose |
|---|---|
| `README.md` | This file. |
| `CONTENT_INVENTORY.md` | What AI-Content-OS can and cannot produce today, per content type, against the existing module list. |
| `CHANNEL_STRATEGY.md` | Per-channel strategy notes (CardNews, Shorts, Instagram feed, BrandConnect, Commerce, Knowledge). |
| `CONTENT_BACKLOG.json` | Machine-readable backlog, 120 briefs. Source of truth. |
| `CONTENT_BACKLOG.md` | Human-readable rendering of the same 120 briefs, grouped by content type. |
| `TOP20_PRIORITY.md` | Top 20 briefs ranked by the Section-13 priority formula (see `tools/build_portfolio.py::score_priority`). |
| `LEARNING_SEED_PATTERNS.json` | 90 learning-seed hypotheses (hook/story/CTA/evidence/visual/commerce-trust/disclosure/anti-pattern). All `status` values are pre-validation (`hypothesis_only` / `needs_content_qa` / `needs_real_performance_data`) -- never `validated`/`proven`. |
| `EVIDENCE_REQUIREMENTS.md` | What counts as acceptable evidence per content type, and the fail-closed rule for missing evidence. |
| `RIGHTS_AND_ATTRIBUTION_MATRIX.md` | Image/text/review/brand-asset rights requirements per content type. |
| `MONETIZATION_BOUNDARIES.md` | What monetization is/isn't approved today, per content type. |
| `HANDOFF.md` | Final handoff report in the requested format, including per-team handoff notes. |
| `QA_REPORT.md` | Self-check output: duplicate IDs, missing fields, forbidden real-figure scan, CardNews 4-slide completeness, pattern status vocabulary -- all PASS. |
| `tools/build_portfolio.py` | The stdlib-only generator + QA script that produced `CONTENT_BACKLOG.json`, `CONTENT_BACKLOG.md`, `LEARNING_SEED_PATTERNS.json`, `TOP20_PRIORITY.md`, and `QA_REPORT.md`. Re-runnable; touches only files inside this folder. |

## How to regenerate

```powershell
py external_workclaude/content_portfolio_v1/tools/build_portfolio.py
```

This overwrites only the five generated files listed above, all inside this folder. It makes
no network call, reads no file outside this folder, and does not touch the repository's git
state.

## Status vocabulary used throughout

`implemented`, `offline_ready`, `manual_ready`, `planning_only`, `blocked_by_data`,
`blocked_by_rights`, `blocked_by_api`, `blocked_by_policy`, `not_approved`. No brief in this
portfolio claims `implemented` for a capability the repository does not actually have.
