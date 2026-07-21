# Pattern Promotion Policy

## Purpose

The pattern registry is a governed learning layer, not an authority to invent facts. A pattern may guide production behavior only after its provenance, measured performance, and human approval are explicit. Unknown evidence or rights fails closed.

## Required record

Every JSONL record uses exactly these fields: `pattern_id`, `name`, `domain`, `source_claim_ids`, `preconditions`, `recommended_action`, `prohibited_actions`, `success_metrics`, `failure_signals`, `confidence`, `status`, `version`, `reviewed_at`, `owner_skill`, `supersedes`, and `expires_at`.

Allowed statuses are `CANDIDATE`, `VERIFIED`, `PROMOTED`, `DEPRECATED`, and `REJECTED`.

## Lifecycle gates

### CANDIDATE

A candidate is a hypothesis. It may have empty `source_claim_ids`, but it must not be treated as an approved operating rule. Initial patterns without verified project claim identifiers remain candidates.

### VERIFIED

Verification requires all of the following:

- At least one non-empty, resolvable `source_claim_ids` entry. A label, filename, or invented identifier is not a source claim.
- Review confirms that each referenced claim supports the recommended action and does not contradict the prohibited actions.
- Preconditions, success metrics, and failure signals are observable and specific enough to evaluate.
- Rights and license checks pass for any third-party material used as evidence.

Verification records a non-null `reviewed_at`. Source-free verification is prohibited.

### PROMOTED

Promotion requires all VERIFIED gates plus:

- Performance evidence from a representative evaluation or production observation against the declared success metrics.
- No unresolved declared failure signal in the evaluated scope.
- Explicit human approval by the accountable owner; automated confidence alone cannot promote a pattern.
- A named `owner_skill` responsible for applying, monitoring, and retiring the pattern.
- A current review timestamp and an expiration decision (`expires_at` date or an explicitly approved no-expiration value of null).

Source-free promotion, metric-free promotion, and approval-free promotion are prohibited. Confidence is supporting metadata, never a substitute for evidence or approval.

### DEPRECATED and REJECTED

Use `DEPRECATED` when a previously usable pattern is expired, superseded, contradicted by newer evidence, or repeatedly triggers failure signals. A deprecated pattern remains in history and must not be selected for new work.

Use `REJECTED` when evaluation disproves a candidate, provenance or rights cannot be made valid, or the proposed action violates a protected contract. Rejection is terminal for that version; reconsideration requires a new version with new evidence.

## Identity and version rules

- `pattern_id` is stable across versions; `version` is a positive integer and increases monotonically.
- The pair (`pattern_id`, `version`) must be unique. Exact duplicates and conflicting records for that pair are rejected.
- A new version must not silently overwrite or delete an older version.
- Material changes to preconditions, action, prohibitions, metrics, evidence, ownership, or expiration require a new version.
- Equivalent active patterns in the same domain are duplicate candidates. They must be merged or one must be rejected before promotion.

## Supersession and cycle rules

`supersedes` is null or identifies the prior pattern version under replacement. The target must exist, must not be the current record, and must precede the replacing version. The complete supersession graph must be acyclic. Self-links, forward references used to evade ordering, multi-node cycles, and promotion of a record participating in a cycle are rejected.

When a replacement is promoted, the superseded active record is deprecated in a separate append-only record; history is retained.

## Expiration and review

- Expired patterns cannot be VERIFIED or PROMOTED for use and must be moved to DEPRECATED before selection.
- Before `expires_at`, the owner reviews source validity, rights, observed metrics, failure signals, and continued domain fit.
- Evidence withdrawal, license change, owner loss, or a material failure signal triggers immediate review even before expiration.
- Extending expiration requires human approval and a new version; timestamps must not be edited merely to keep a pattern active.

## Release selection

Only non-expired PROMOTED patterns may be automatically recommended as established practice. VERIFIED patterns may be evaluated in controlled scope. CANDIDATE patterns are learning hypotheses only. DEPRECATED and REJECTED patterns are historical records and are never selected.
