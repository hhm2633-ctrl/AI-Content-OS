# Rights and Attribution Matrix

Per-content-type rights requirements. "Self-authored" means the copy/graphic is created
in-house and carries no third-party rights question by default.

| Content type | Text rights | Image rights | Third-party quote rights | Brand asset rights | Disclosure |
|---|---|---|---|---|---|
| CardNews | self-authored | fallback background (in-repo) or licensed photo/illustration -- confirm license before using anything non-fallback | N/A unless quoting a public source, in which case attribution required | N/A | Not required (organic content) |
| Shorts/Reels | self-authored script | footage must be self-filmed or explicitly licensed B-roll; no stock substitution without a license check | N/A | N/A | Not required (organic content) |
| Instagram feed/informational | self-authored | category illustration or licensed photo | If quoting a community post/comment: attribution required, PII scrubbed, identity masked, labeled "community opinion" not fact | N/A | Not required (organic content) |
| BrandConnect | self-authored copy, brand-approved claims only | brand-provided assets only; self-shot footage requires brand written approval | N/A | Trademark/likeness confirmation required from the brand before any asset is used | **Required on every slide/caption** (`#광고` + in-copy disclosure) |
| Commerce guide/comparison | self-authored | no real product photo until the specific product's manufacturer/seller rights are confirmed; category-generic illustration only until then | Review quotes require confirmed authenticity, permission, attribution, and PII removal before use (mirrors `docs/COMMERCE_PHASE_1_CONTRACT.md` §7) | N/A unless comparing named brands, in which case factual accuracy (not just rights) must be confirmed | Required once any affiliate link exists |
| Knowledge/Evergreen | self-authored | infographic-style, self-authored preferred | Official-document quotes require source attribution | N/A | Not required (organic content) |

## Rules that apply everywhere

- No image is used without either being a fallback/self-authored asset or having a confirmed
  license. "I found it online" is not a license.
- No review, testimonial, or comment is quoted without confirmed authenticity, explicit
  permission, attribution, and PII removal -- if any one of those is missing, the quote is not
  used (mirrors the CardNews social-proof gate and the Commerce Phase 1 review gate).
- No competitor account's screenshot is used as content; competitor material is
  analysis-only, never rendered into public-facing content (mirrors the existing
  `render_allowed: false` contract for Instagram competitor screenshots in `MODULE_STATUS.md`).
- Sponsored/BrandConnect content always discloses; there is no threshold below which
  disclosure is optional.
- Commerce content discloses the moment any affiliate link exists; criteria-only comparison
  content with no link and no sponsorship does not require disclosure.

## Where this shows up in the backlog

Every brief's `rights_status_required` field states the specific rights condition for that
brief; every BrandConnect and Commerce brief's `disclosure_required` field is `true`. This is
enforced mechanically -- `tools/build_portfolio.py::run_qa()` fails the batch if any brief is
missing a non-empty `rights_status_required` value or a non-null `disclosure_required` value
(see `QA_REPORT.md`, both checks PASS with zero missing entries).
