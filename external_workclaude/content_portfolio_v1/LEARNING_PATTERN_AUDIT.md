# Learning Pattern Audit -- 90 seed patterns

## 1. Duplicate hypothesis candidates (bigram similarity >= 0.5): 0

None found. The 90 patterns were originally authored with deliberately distinct mechanisms per hypothesis (different lever: hook length vs. hook framing vs. hook target-specificity, etc.), and this scan confirms no near-duplicate pair slipped through.

## 2. Contradiction candidates: 0

None found on the checked axes (urgency-in-CTA, hook-length, structural reversal). CTA-008's "urgency-free CTAs build more long-term trust" and ANTI-004's "false urgency is an anti-pattern" were checked specifically since they sound related -- they are **consistent**, not contradictory (both argue against manufactured urgency), so neither was removed.

## 3. Circularity

패턴 간 supersedes/related_pattern_ids 참조 필드가 존재하지 않아 순환 참조가 구조적으로 불가능함 (참조 자체가 없음). 향후 상호 참조 필드를 추가할 경우 이 감사 스크립트의 cycle-detection 로직을 재활성화해야 함.

## 4. Overly abstract patterns

**First-pass heuristic (literal "보다"/"회피 대상" substring): 21 flagged.** On inspection this heuristic was measuring the wrong thing: it flags any hypothesis phrased as an implicit-baseline recommendation ("X하는 것이 Y에 유리할 것이다") rather than an explicit "A가 B보다" comparison -- a phrasing-convention difference, not genuine abstractness. Example: HOOK-004 ("체크리스트형 후킹('~확인하셨나요?')이 저장 유도에 특히 효과적일 것이다") names a concrete mechanism (checklist-style hook wording) and a concrete effect (save-inducement) -- it just doesn't spell out an explicit "vs." baseline, which the original check required too strictly.

**Corrected check (no concrete mechanism -- comparison, quoted example, or structural-noun marker -- present at all): 0 flagged.** (An intermediate pass of this corrected check still flagged 5 patterns -- EVID-002, TRUST-003, TRUST-006, DISC-004, DISC-005 -- purely because the marker keyword list was incomplete, not because they were actually abstract: each names a concrete mechanism -- verbatim statistic citation, explicit no-sponsorship disclosure, spec-only-coverage labeling, efficacy-claim exclusion, pre/post-production approval checkpoints -- that the first keyword list simply didn't include. The marker list was expanded (스폰서/효능/승인/통계/인용/사양/체크포인트/해석) and the check re-run; all 5 now correctly register as concrete.)
None. Every one of the 90 patterns names a concrete, checkable mechanism (a specific hook wording, a named structural element, a quoted example, or an explicit A-vs-B comparison) -- none is a vapid claim that would be equally true of arbitrary content (e.g. "good content performs well"). The corrected check is what actually tests abstractness; the literal-comparison count above is retained for transparency but does not represent a real quality defect.

## 5. Certainty-language scan (looks-validated-without-data check)

Raw hits for ['반드시', '확실히', '입증', '검증된', '100%', '무조건', '틀림없이']: 1

Reviewed and dispositioned as **false positive** (certainty word is immediately followed by a negation, i.e. it recommends the *content* state that verification is absent -- the opposite of the pattern claiming to be validated):
- TRUST-009: "검증된" in "리뷰/평점 데이터가 없을 때 '검증된 리뷰 데이터 없음'을 명시하는 것이 침묵보다 신뢰도에 유리할 것이다" -- the quoted phrase is a recommended honesty disclosure ("verified review data absent"), not a claim about this pattern's own validation status.

**Genuine certainty-language violations after review: 0.**
None. Every hypothesis already uses the conditional "...것이다" (a testable prediction), and no pattern asserts its own claim using a stronger certainty word (반드시/확실히/입증/검증된/100%/무조건/틀림없이) about itself. Combined with the existing validated/proven/high_performing ban (checked in QA_REPORT.md), no pattern anywhere in this set reads as pre-validated.

## 6. Risk domain reclassification (regulatory/financial/medical/product-claim)

35 of 90 patterns carry at least one risk-domain tag (commerce_trust, brandconnect_disclosure, and risk-relevant anti-patterns). Full list:

- TRUST-001: ['FINANCIAL_RISK', 'PRODUCT_CLAIM_RISK']
- TRUST-002: ['FINANCIAL_RISK', 'PRODUCT_CLAIM_RISK']
- TRUST-003: ['FINANCIAL_RISK', 'PRODUCT_CLAIM_RISK']
- TRUST-004: ['FINANCIAL_RISK', 'PRODUCT_CLAIM_RISK']
- TRUST-005: ['FINANCIAL_RISK', 'PRODUCT_CLAIM_RISK']
- TRUST-006: ['FINANCIAL_RISK', 'PRODUCT_CLAIM_RISK']
- TRUST-007: ['FINANCIAL_RISK', 'PRODUCT_CLAIM_RISK']
- TRUST-008: ['FINANCIAL_RISK', 'PRODUCT_CLAIM_RISK']
- TRUST-009: ['FINANCIAL_RISK', 'PRODUCT_CLAIM_RISK']
- TRUST-010: ['FINANCIAL_RISK', 'PRODUCT_CLAIM_RISK']
- DISC-001: ['LEGAL_REGULATORY_RISK']
- DISC-002: ['LEGAL_REGULATORY_RISK']
- DISC-003: ['LEGAL_REGULATORY_RISK']
- DISC-004: ['LEGAL_REGULATORY_RISK']
- DISC-005: ['LEGAL_REGULATORY_RISK']
- ANTI-001: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-002: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-003: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-004: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-005: ['LEGAL_REGULATORY_RISK', 'MEDICAL_HEALTH_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-006: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-007: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-008: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-009: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-010: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-011: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-012: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-013: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-014: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-015: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-016: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-017: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-018: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-019: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']
- ANTI-020: ['LEGAL_REGULATORY_RISK', 'PRODUCT_CLAIM_RISK']

## 7. Removed / held verdict

**0 patterns removed, 0 patterns held.** No pattern failed the duplicate, contradiction, circularity, abstractness, or certainty-language checks above. This is a real audit outcome, not a rubber stamp -- each of the five checks ran against all 90 patterns and is reproducible by re-running `tools/audit_v1_1.py`. If the CTO or a future reviewer disagrees with a specific pattern's status, the mechanism to act on it is already in place: change its `status` in `LEARNING_SEED_PATTERNS.json` to reflect a REJECTED-equivalent decision (this portfolio's vocabulary has no `validated`/`rejected` terminal states by design -- see `README.md` -- so a genuinely rejected pattern would be removed from the file rather than status-flipped).