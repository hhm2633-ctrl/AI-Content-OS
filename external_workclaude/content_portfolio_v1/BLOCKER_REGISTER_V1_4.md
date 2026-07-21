# Blocker Register V1.4

## Active blockers

### CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED

Owner: Common Engine / CardNews lane (not this package). Reference: `tests/test_workflow_card_news_output_receipts.py` (read-only, not modified). The 07/08 `workflow_results` receipt validation for `publishing_ready`/`legacy_receipt_blocked` is under active correction elsewhere in the repository. This package cannot resolve it, work around it, or estimate a completion date -- it can only wait and re-check.

Affected work orders: ['CN-013-WO-04', 'CN-013-WO-05', 'CN-013-WO-06', 'CN-014-WO-04', 'CN-014-WO-05', 'CN-014-WO-06', 'CN-016-WO-04', 'CN-016-WO-05', 'CN-016-WO-06', 'CN-017-WO-04', 'CN-017-WO-05', 'CN-017-WO-06']

### EVIDENCE_REVIEW_PENDING

Owner: CTO / content reviewer. KN-008's `evidence_not_required_reason` was deliberately left `null` in V1.3.1 because a classification-scheme description does not qualify for that field per the CTO's own rule, even fully unattributed and effect-free. This blocker records that a human judgment call is still open, not a file-completeness gap.

Affected work orders: ['KN-008-WO-02']

## No-blocker work orders (parallel-ready now)

40 work orders: ['CN-013-WO-01', 'CN-013-WO-02', 'CN-013-WO-03', 'CN-014-WO-01', 'CN-014-WO-02', 'CN-014-WO-03', 'CN-016-WO-01', 'CN-016-WO-02', 'CN-016-WO-03', 'CN-017-WO-01', 'CN-017-WO-02', 'CN-017-WO-03', 'SH-017-WO-01', 'SH-017-WO-02', 'SH-017-WO-03', 'SH-006-WO-01', 'SH-006-WO-02', 'SH-006-WO-03', 'SH-018-WO-01', 'SH-018-WO-02', 'SH-018-WO-03', 'IG-007-WO-01', 'IG-007-WO-02', 'IG-007-WO-03', 'IG-007-WO-04', 'IG-009-WO-01', 'IG-009-WO-02', 'IG-009-WO-03', 'IG-009-WO-04', 'IG-013-WO-01', 'IG-013-WO-02', 'IG-013-WO-03', 'IG-013-WO-04', 'KN-008-WO-01', 'KN-008-WO-03', 'KN-008-WO-04', 'KN-007-WO-01', 'KN-007-WO-02', 'KN-007-WO-03', 'KN-007-WO-04']