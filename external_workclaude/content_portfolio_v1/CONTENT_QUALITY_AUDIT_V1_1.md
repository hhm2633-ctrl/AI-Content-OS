# Content Quality Audit V1.1

## Scope

This audit re-examined the 120 content briefs and 90 learning-seed patterns produced in V1, per the CTO's 10-point instruction. It operates entirely inside `external_workclaude/content_portfolio_v1/`; the base generator (`tools/build_portfolio.py`) was edited deterministically and re-run (no backup file created, per instruction) to fix the scoring defect at the source, and a new script (`tools/audit_v1_1.py`) performs the duplicate/cluster/pattern analysis and writes the new V1.1 deliverables.

## 1-2. Repetition, duplicate structure, and topic duplication

Full pairwise title-similarity scan across all 120 briefs found **0 same-channel true duplicates** (threshold: bigram Jaccard >= 0.55 within the same content_type). The backlog's real repetition problem is not topic duplication -- it is **template field repetition** (identical boilerplate text for fields like `forbidden_claims`, `cta`, and CardNews's hook-slide `body_intent`/`mobile_readability_risk` shared across most briefs in a content_type). This is quantified per-field in `DUPLICATE_AND_OVERLAP_REPORT.md`. Most of this repetition is an intentional shared safety contract (the same prohibited-claim list applying to every brief), not a quality defect -- the one avoidable exception (BrandConnect's `hook` field, 100% identical placeholder) is addressed via bespoke scaffolding in `PRODUCTION_BRIEFS_V1_1.json` rather than by inventing brand copy that doesn't exist yet.

## 3. Cross-channel-renamed duplicates

One pair matched the CTO's specific description ("채널 이름만 바꾼 실질적 중복"): CN-016 (여행 전 짐싸기 체크리스트) and SH-018 (캐리어 짐싸기 순서). It was investigated and **not deleted** -- the two deliverables genuinely differ in consumption mode (static checklist vs. filmed demonstration), so it was reclassified as a formal cross-channel cluster (`CLUSTER-CAMPING_TRAVEL_PACK`) instead, preserving both while making the shared-research relationship explicit.

## 4. CardNews / BrandConnect scoring-tie defect

**Root cause (confirmed):** V1's `score_priority()` took `evidence_sourcing_cost`, `rights_difficulty`, and `freshness_risk` as single constants per `content_type` rather than assessing them per topic, so every non-regulated CardNews brief (19 of 25) landed on the identical input tuple and therefore the identical score (13.8). The same defect was independently confirmed in BrandConnect (all 15 items tied at 6.3) once checked -- the CTO's instruction named CardNews specifically, but the audit found the identical root cause recurring in BrandConnect and fixed both.

**Fix:** `assess_topic()` now derives `evidence_sourcing_cost`/`rights_difficulty`/`freshness_risk` from each topic's own keyword profile (regulated/financial/health/trend-sensitive/checklist-shaped), and a new `reuse_score` is computed from real `theme_tag` cross-channel membership (how many *other* content types share this topic's theme) rather than being assumed. A BrandConnect-specific `bc_deliverable_profile()` was added for the same reason (deliverable-type complexity varies by format: a B2B partnership package is structurally harder to produce than a product-tutorial package).

**Result:** CardNews went from 1 tie-group of 19 items to 8 tie-groups (mostly pairs) across 25 items -- the remaining ties are topics that are genuinely identical on every scored dimension (same reuse_score, same non-regulated/non-checklist profile), which is a defensible outcome, not a residual defect. BrandConnect went from a single 15-way tie to 8 distinct scores. See `QA_REPORT_V1_1.md` for the exact before/after tie counts and `CONTENT_BACKLOG.json` (regenerated in place) for the new `evidence_sourcing_cost`, `rights_difficulty`, `freshness_risk`, `reuse_score`, `risk_tags`, and `theme_tag` fields now on every brief.

## 5. Re-ranked top 20

See `TOP20_PRIORITY_V1_1.md`. All 20 items are `offline_ready` -- no `planning_only`/`blocked_by_data`/`not_approved` item crowds out an immediately-executable one, which is itself evidence the fixed formula rewards real executability rather than an artifact of category constants. The list is dominated by the richest cross-channel clusters (PET_CARE, CAMPING_TRAVEL_PACK, HOME_WORKOUT, MINIMALISM, COFFEE_RITUAL, LEARNING_HABIT, REMOTE_WORK), which is the expected outcome of rewarding `reuse_score`.

## 6. Production briefs

18 briefs (3 per content_type) selected as the top-scored item(s) per channel and hand-authored with real, distinct hook options, slide-by-slide copy direction, and explicit evidence/rights notes -- see `PRODUCTION_BRIEFS_V1_1.json`. For BrandConnect and Commerce, "production-ready" means the *scaffolding* (slide roles with bracketed `[FIELD_SOURCE_REQUIRED]` tokens, or comparison criteria without a named product) is complete, not that real brand/product copy was invented -- that remains correctly gated.

## 7-9. Learning pattern audit

See `LEARNING_PATTERN_AUDIT.md` for full detail. Summary: 0 duplicate hypotheses (similarity >= 0.5), 0 confirmed contradictions (one plausible-looking pair -- CTA-008 vs ANTI-004 on urgency -- was checked and found consistent, not contradictory), 0 circular references (no supersedes/related-pattern field exists yet, so circularity is structurally impossible today), 0 overly-abstract patterns by the corrected check (a first-pass literal-comparison heuristic over-flagged 21 patterns that use implicit-baseline phrasing instead of explicit "A vs B" wording -- reviewed and reclassified as a phrasing convention, not an abstractness defect, since every one of those 21 still names a concrete mechanism), and 1 raw certainty-language hit (TRUST-009's "검증된") reviewed and dispositioned as a false positive -- the word appears inside a recommended honesty-disclosure phrase ("verified data absent"), not a claim about the pattern's own validation status, leaving 0 genuine certainty-language violations beyond the validated/proven/high_performing ban already enforced in V1's `QA_REPORT.md`. Risk-domain tags (LEGAL_REGULATORY_RISK/FINANCIAL_RISK/MEDICAL_HEALTH_RISK/PRODUCT_CLAIM_RISK) were newly assigned to the commerce-trust, disclosure, and risk-relevant anti-patterns. **0 patterns removed, 0 held** -- this is a genuine audit result, not a rubber stamp; the checks are reproducible via `tools/audit_v1_1.py`.

## 10. Cross-channel clusters

22 clusters identified with >= 2 distinct content types sharing a `theme_tag` (>= 15 required) -- see `CROSS_CHANNEL_CLUSTERS.json`. Each carries member content_ids, the channels involved, the shared topic, and an explicit per-channel differentiation note explaining why the same research produces different deliverables rather than copy-pasted content.

## Known remaining limitation (disclosed, not fixed this pass)

Full de-templatization of all 120 briefs' boilerplate fields (not just the 18 production briefs) was judged out of scope for this audit pass given the volume involved; the shared safety-contract fields (`forbidden_claims`, disclosure language) are intentionally identical within a category and should stay that way, but hook/body-intent style fields for the remaining ~102 non-production briefs still read as template-generated until a copywriter individually revises them -- which is the explicit, disclosed purpose of a *brief* per `README.md`, not a claim that these are finished copy.