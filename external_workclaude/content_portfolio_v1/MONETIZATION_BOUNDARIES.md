# Monetization Boundaries

What this portfolio approves for monetization today: **nothing directly.** Every monetization
route in this backlog is a documented future candidate, gated behind a real prerequisite that
does not yet exist in the repository.

## Per content type

| Content type | Monetization today | What would unlock it | Current gate |
|---|---|---|---|
| CardNews | None | N/A -- organic trust/reach format | N/A |
| Shorts/Reels | None | N/A -- organic reach format; Commerce tie-in is a later-Sprint candidate | N/A |
| Instagram feed/informational | None | N/A -- organic trust/reach format | N/A |
| BrandConnect | None | A real, signed brand contract with agreed deliverables and measurement | `OPERATOR_APPROVAL_REQUIRED`, `RIGHTS_REVIEW_REQUIRED`, `PLATFORM_POLICY_REVIEW_REQUIRED` |
| Commerce guide/comparison | None (criteria-only) | A real, rights-cleared product source with current price/stock/shipping data | `SOURCE_REQUIRED`, `PRICE_VERIFICATION_REQUIRED`, `RIGHTS_REVIEW_REQUIRED` |
| Knowledge/Evergreen | None | N/A -- organic authority-building format | N/A |
| Affiliate-conversion candidate | None -- not staged as a backlog item | A real, owned affiliate account + a real product + disclosure copy + operator approval | No backlog brief exists; documented only as a gated future extension of Commerce in `CONTENT_INVENTORY.md` §11 |
| Overseas sourcing / Amazon candidate | None -- not staged as a backlog item | A CTO market decision + a real overseas program/API connection + full legal review | No backlog brief exists; documented only as a Roadmap category in `CONTENT_INVENTORY.md` §12 |

## Hard boundaries (apply to every content type, without exception)

- No content in this backlog contains a real affiliate link, a real purchase CTA tied to a
  specific product, or a real brand-sponsored claim.
- No brief assumes automatic approval once a prerequisite is met -- every monetization-adjacent
  brief explicitly carries `OPERATOR_APPROVAL_REQUIRED` and/or `PLATFORM_POLICY_REVIEW_REQUIRED`
  in its `blocker_codes`, meaning a human decision is required even after the data/rights gate
  clears.
- Disclosure is never optional once monetization exists: BrandConnect discloses on every asset,
  Commerce discloses the moment any affiliate link is added.
- `auto_upload_performed`/"실제 게시 실행" style flags do not exist in this portfolio at all --
  this is a design asset, not an execution path, and no file here can trigger a real post,
  purchase, or link.

## Why so conservative

This mirrors the same fail-closed posture already enforced in `modules/commerce/` (Phase 1
contract: `upload_mode: manual_only`, `auto_upload_performed: false` until an explicit CTO
Phase 2 gate) and `modules/affiliate/`/`modules/brandconnect/` (policy-gate modules that exist
specifically to keep monetization behind an explicit approval step). This portfolio's job is
to make the eventual monetization path easy to execute once approved -- not to pre-approve it.
