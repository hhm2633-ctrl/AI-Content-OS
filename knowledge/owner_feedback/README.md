# CardNews Human Owner Feedback Log

`cardnews_owner_feedback.jsonl` is the append-only record of explicit project-owner labels.
It is not chat memory and it is not Instagram performance evidence.

Every explicit owner decision about candidate acceptance, rejection, category correction, hook,
media, CTA, or production quality must be appended before the assistant reports that it learned the
feedback. Future daily review must read this log and `knowledge/owner_directives/
cardnews_owner_directives.json` before selecting or presenting candidates.

Required fields per line:

- `event_id`, `recorded_at`, `source`, `feedback_type`
- `candidate_id`, `category`, `title` when the feedback targets a candidate
- `owner_decision`, `owner_reason`
- `applies_to`, `is_performance_evidence`, `consumption_status`

Rules:

- Never rewrite or delete a prior event; append a correction with `supersedes_event_id`.
- Never infer approval for candidates the owner did not explicitly label.
- `APPROVE_FOR_REVIEW` does not mean production, publishing, or performance promotion approval.
- Owner directives may be active product rules without pretending they are measured performance.

## Automatic learning stages

`modules/agent_console/owner_feedback_learning.py` compiles this append-only log into
`cardnews_owner_learning_index.json` only when the source hash changes.

- Candidate-specific labels -> `CLASSIFIED_EXAMPLE` (kept as examples, never generalized automatically)
- Owner hypotheses -> `LEARNING_CANDIDATE` (not injected as active rules)
- Explicit active owner directions/corrections -> `ACTIVE_OWNER_RULE`
- Explicit `supersedes_event_id` or exact duplicate replacement -> `SUPERSEDED`

`ACTIVE_OWNER_RULE` means an owner-approved operating instruction. It is not Instagram performance
evidence and does not bypass the separate `PatternRegistry` performance-promotion gates. Agent
Console injects at most five relevant active rules for the current category and candidate and records
their IDs in the execution receipt.

New explicit feedback must enter through `append_owner_feedback_event()` or
`py scripts/record_owner_feedback.py <event.json>`. The append and index refresh happen as one
operation; duplicate event IDs fail closed. This is the capture boundary used by the agent workflow.
