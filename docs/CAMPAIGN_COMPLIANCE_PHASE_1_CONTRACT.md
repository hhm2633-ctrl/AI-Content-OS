# Campaign Compliance Phase 1 Contract

Revision: Independent QA NO-GO correction pass (this Sprint). Section 8 records exactly what changed
and why; the rest of this document describes the corrected, current contract.

## 1. Decision and scope

Campaign Compliance Phase 1 is an offline, standalone checker that compares an advertiser/sponsor's
`CampaignRequirement` list against a single `ContentPackage` and reports which conditions are met,
missing, unverifiable offline, or possibly violated. It produces a manual-confirmation checklist and
a `publish_ready` verdict. It is implemented under `modules/compliance/` and is **not** wired into
`WorkflowEngine`, `PublishingModule`, or any other existing module -- standalone, on-demand, same
pattern as `modules/commerce/` and `modules/competitor_learning/`.

Phase 1 does **not** log in to any platform, publish content, automate a browser, call an external
API or LLM, perform image OCR, or collect personal data. Its terminal outcome is a structured
compliance result; a human always makes the actual publish decision.

## 2. Input contract

### 2.1 Campaign

```json
{
  "campaign_id": "campaign-001",
  "requirements": []
}
```

A bare list of `CampaignRequirement` objects is also accepted (`campaign_id` then resolves to
`null`). Any other shape is a **contract-level error** (see Section 3.0): a campaign that is neither
a dict nor a list, a dict missing its `requirements` key, or a dict whose `requirements` is present
but not a list, all block the entire check before any requirement or content-package rule runs.

### 2.2 CampaignRequirement

```json
{
  "requirement_id": "r1",
  "requirement_type": "required_keyword",
  "description": "",
  "required": true,
  "expected_value": null,
  "minimum_count": null,
  "maximum_count": null,
  "allowed_values": [],
  "prohibited_values": [],
  "verification_mode": "",
  "source_reference": null
}
```

Supported `requirement_type` values: `required_keyword`, `prohibited_keyword`, `disclosure_text`,
`image_count`, `video_required`, `map_required`, `link_required`, `hashtag`, `brand_name`,
`product_name`, `publishing_window`, `numeric_claim`, `manual_instruction`. An unsupported/unknown
type is never treated as satisfied -- it always resolves to `manual_review`.

`required` defaults to `true` when missing or not an explicit boolean (fail-closed).
`allowed_values`/`prohibited_values` take precedence over `expected_value` as the candidate set for
keyword-shaped checks. A **duplicate `requirement_id` is a contract-level blocker** (Section 3.0), not
a silently-deduplicated warning. A missing/blank `requirement_id` is assigned a stable positional id
before duplication is checked.

`verification_mode` must be `""` (unset), `"automatic"`, `"manual"`, or `"evidence_required"` -- see
Section 3.2 for the exact behavior of each. Any other value blocks that one requirement
(Section 3.0).

### 2.3 ContentPackage

```json
{
  "package_id": "pkg-001",
  "channel": "instagram",
  "title": "",
  "body": "",
  "caption": "",
  "hashtags": [],
  "links": [],
  "assets": [],
  "publishing_time": "2026-07-12T09:00:00+09:00",
  "evidence_refs": [],
  "rights_status": "owned",
  "rights_manifest": {}
}
```

`links` entries may be plain URL strings or `{"url": "..."}` objects. `assets` entries are dicts with
at least a `type` field (`"image"` or `"video"`); each asset also needs its own `rights_status` or an
`upstream_rights_manifest_id` (Section 3.4). `publishing_time` must be a timezone-aware ISO-8601
string or `datetime` -- a naive value is treated as invalid, never guessed into UTC. `rights_status`
is the package-level value and no longer implies every asset is rights-cleared (Section 3.4).
`rights_manifest` is `{manifest_id: {"rights_status": "..."}}`, an optional table an asset can link to
instead of carrying its own `rights_status` directly.

### 2.4 EvidenceReference (structured -- replaces bare strings)

```json
{
  "evidence_id": "ev1",
  "source_url": "https://merchant.example.com/sales-report",
  "locator": null,
  "captured_at": "2026-07-10T09:00:00+09:00",
  "verified_at": "2026-07-11T09:00:00+09:00",
  "rights_status": "owned"
}
```

`content_package.evidence_refs` is a list of these structured objects, not bare strings (Section
3.0/3.3). A bare string is still parsed (as `evidence_id` only, for backward-compatible input
parsing) but every other field stays empty, which makes it structurally incomplete by construction --
it can never satisfy the completeness check in Section 3.3.

## 3. Truth and fail-closed gates

### 3.0 Campaign contract validity (checked before anything else)

A campaign is rejected outright -- `requirement_results: []`, `blocking_reasons` explaining why,
`publish_ready: false` -- when any of the following hold, before any requirement or content-package
rule ever runs:

- the campaign root is neither a dict nor a list (e.g. `123`, `None`);
- a dict campaign is missing its `requirements` key;
- a dict campaign's `requirements` value is present but not a list;
- two requirements share the same `requirement_id` (after positional-id assignment for blank ids).

Each `CampaignRequirement`'s own `verification_mode` is validated at evaluation time, not contract
time: an unrecognized value blocks that specific requirement (`fail`, always contributing to
`blocking_reasons` regardless of `required`), while the rest of the campaign is still evaluated
normally.

1. **Required keyword**: checked across the combined title + body + caption + hashtags text,
   case/whitespace-normalized.
2. **Prohibited keyword**: any match returns the exact field(s) it was found in
   (`title`/`body`/`caption`/`hashtags`/`links`), never just a bare pass/fail.
3. **Disclosure text**: fail-closed and **always blocking when missing**, regardless of the
   requirement's own `required` flag -- an advertiser cannot mark a sponsorship disclosure
   "optional".
4. **Image/video/link/hashtag counts**: checked only against the structured `assets`/`links`/
   `hashtags` lists -- never inferred from prose text.
5. **`map_required`**: there is no structured "has a map/place tag" field anywhere in the
   `ContentPackage` input contract. This requirement type always resolves to `manual_review`; it is
   never guessed to `pass`.
6. **`publishing_window`**: a naive (no-timezone) `publishing_time` always fails. A window is
   defined by an optional `window_start`/`window_end` pair inside `expected_value`. See Section 3.1
   for the corrected parsing/ordering rules.
7. **`numeric_claim`**: see Section 3.3 for the corrected evidence-completeness and OCR-ambiguity
   rules.
8. **Package `rights_status`**: checked unconditionally against an allow-list mirroring
   `modules/card_news/evidence_input_validator.py`'s `RENDER_ALLOWED_COPYRIGHT_STATUSES`
   (`owned`/`licensed`/`public_domain`/`official_reuse_allowed`/`user_supplied_with_permission`).
   Missing or disallowed values block `publish_ready`. **This is independent of, and does not
   substitute for, per-asset rights (Section 3.4).**
9. **Required vs. optional**: a failed `required=true` requirement (or a failed `disclosure_text`,
   or any failure caused by an internal error or an unrecognized `verification_mode`) is added to
   `blocking_reasons` and forces `publish_ready=false`. A failed `required=false` requirement whose
   failure was a genuine, successfully-executed check is added to `warnings` only.
10. **Fail-closed on internal error**: any exception inside a single requirement's check now
    **always blocks publishing overall, regardless of that requirement's own `required` flag** --
    a check that could not actually run must never be treated as a harmless optional failure. Any
    exception in the surrounding pipeline is still caught by the outer `check()` call and returns a
    fully structured, blocked result (`compliance_check_internal_error`) instead of raising.
11. **Immutability**: `campaign`/`content_package` are only ever read via `.get()` and copied into
    new dicts/lists -- the caller's original objects are never mutated.
12. **No secret/URL leakage**: reason/message strings are fixed templates parameterized only by
    counts, thresholds, and field *names* -- raw link/body/caption content (and therefore any secret
    embedded in a URL) is never echoed back into the result. Internal exception text is likewise
    never included in the output.

### 3.1 `publishing_window` parsing and ordering

- `publishing_time` must parse as a timezone-aware date/time; a naive value fails.
- If `expected_value.window_start` or `window_end` is present but does not parse as a
  timezone-aware date/time, the requirement **fails** -- it is never silently ignored (previously,
  an unparseable bound was dropped and the check could still pass).
- If both bounds parse and `window_start` is after `window_end`, the requirement **fails** -- the
  campaign's own window definition is invalid, independent of `publishing_time`.
- Only once both bounds are valid and correctly ordered (or a bound is legitimately omitted for an
  open-ended window) is `publishing_time` compared against them.

### 3.2 `verification_mode` behavior

Applied on top of whatever the requirement-type dispatch already produced:

- `""` / `"automatic"`: no change -- the automatic result stands.
- `"manual"`: any `pass` or `fail` automatic result is forced to `manual_review` -- the campaign
  explicitly wants a human to decide this condition regardless of the automatic outcome.
- `"evidence_required"`: a `pass` can only survive if `source_reference` resolves to a *complete*
  structured `EvidenceReference` (Section 3.3's completeness rule, generalized to any requirement
  type). If evidence is complete, the result becomes `manual_review` (never an unattended `pass`); if
  evidence is missing or incomplete, the result becomes a blocking `fail`.
- Any other value: the requirement fails and always blocks (Section 3.0), regardless of `required`.

### 3.3 `numeric_claim` -- evidence completeness, Korean amount words, OCR-ambiguity

1. If `expected_value` is set, the exact text must appear in the content (case/whitespace-normalized)
   or the requirement fails. If `expected_value` is unset, the combined text is scanned for a
   claim-risk pattern (Section 3.5); if none is found, the requirement is `not_applicable`.
2. **OCR-ambiguity check** (new): if the matched claim text contains a digit immediately adjacent to
   a commonly OCR-confused letter (`0`/`O`, `1`/`l`/`I`, `5`/`S`, `8`/`B`, `2`/`Z`), the requirement
   resolves to `manual_review` immediately -- this module performs no OCR itself; the point is to
   never *confidently* confirm a suspicious digit/letter mixture one way or the other.
3. **Evidence lookup**: `source_reference` must resolve to an entry in `content_package.evidence_refs`
   by `evidence_id`. A bare string in `evidence_refs` (Section 2.4) can never resolve to a complete
   entry.
4. **Evidence completeness** (new, replaces the old "any matching string counts" rule): the resolved
   entry must have (a) a `source_url` or `locator`, (b) a parseable, timezone-aware `captured_at`,
   (c) a parseable, timezone-aware `verified_at`, and (d) a `rights_status` in the allowed set. Any
   missing/invalid field **blocks** the claim (`fail`), it does not degrade to `manual_review`.
5. Only a claim with *complete* evidence reaches `manual_review` -- it never reaches `pass`; verifying
   real-world truth still requires a human (no OCR/LLM judgment here).

### 3.4 Per-asset rights (new -- package-level rights no longer approves every asset)

If `content_package.assets` is non-empty, **each** asset independently needs either:

- its own `rights_status` in the allowed set, or
- an `upstream_rights_manifest_id` that resolves (via `content_package.rights_manifest`) to an entry
  whose own `rights_status` is in the allowed set.

An asset satisfying neither adds a blocking `asset_rights_status_missing` reason -- independent of,
and in addition to, the package-level `rights_status` check in Section 3 item 8. A valid package-level
`rights_status` never substitutes for a missing per-asset one.

### 3.5 Always-on package-level risk scan

Independent of whatever requirements the campaign lists, every check run also scans the combined
title/body/caption/hashtags text for two co-occurring patterns:

- a financial/numeric claim signal: either an existing claim keyword (수익, 매출, 수익률, 판매량,
  순위, 효능, 할인, 배당, 이자, 수수료, ...) together with a digit, **or** a spelled-out Korean
  amount/quantity word on its own (`십만원`, `백만원`, `천만원`, `억원`, `만원`, `억`, `천만`, `한 개`,
  `열 개`, `백 개`) -- these carry no ASCII digit, so a digit-only signal previously missed them
  entirely (e.g. "댓글 남기면 수익 십만원", "DM 주시면 백만원 정보 공개");
- an engagement-bait keyword (댓글, 디엠/DM, 팔로우, 좋아요, 공유, 저장) together with an inducement
  marker (남기면, 주시면, 하면, 드립니다, 이벤트, 추첨, ...).

If both are present anywhere in the package, an unconditional `engagement_bait_financial_claim_combo`
blocking reason is added -- a hard rule, not tied to any specific `CampaignRequirement`.

## 4. Output contract

```json
{
  "schema_version": "campaign_compliance_phase_1.v1",
  "package_id": "pkg-001",
  "campaign_id": "campaign-001",
  "checked_at": "2026-07-12T09:00:00+00:00",
  "requirement_results": [
    {
      "requirement_id": "r1",
      "requirement_type": "required_keyword",
      "required": true,
      "status": "pass",
      "reason": "Required keyword is present.",
      "location": null
    }
  ],
  "passed_count": 1,
  "failed_count": 0,
  "manual_review_count": 0,
  "blocking_reasons": [],
  "warnings": [],
  "manual_checklist": [],
  "publish_ready": true
}
```

Each requirement result's `status` is exactly one of `pass`, `fail`, `manual_review`, or
`not_applicable`. `publish_ready` is `true` only when `blocking_reasons` is empty **and**
`manual_review_count` is zero. When the campaign contract itself is invalid (Section 3.0),
`requirement_results` is `[]` and `blocking_reasons` carries one `campaign_contract_invalid` entry
per structural problem found.

## 5. Prohibited actions (never implemented here)

Real platform publishing, browser automation, network/API calls, advertiser account login, image
OCR (the OCR-*ambiguity* heuristic in Section 3.3 detects suspicious digit/letter patterns in text
that is already present -- it does not read pixels from any image), LLM-based judgment,
personal-data collection, and treating an unknown/unverifiable condition as `pass`.

## 6. Relationship to `PublishingModule` -- an AND gate, not a replacement

`modules/publishing/publishing_module.py` has its own, independent publish gate
(`operations.publishing_blocked`, `manual_image_required`, `image_sourcing_status`, etc.). This
checker's `publish_ready` is a **second, separately-required** gate: **actual publishing requires
both `PublishingModule`'s own gate AND this checker's `publish_ready` to be true.** Neither module
reads, calls, or overrides the other's fields; this document records the intended AND-relationship for
whatever future orchestration layer combines them. This checker's result alone must never be treated
as sufficient authorization to publish, and `PublishingModule`'s existing gate must never be treated
as sufficient authorization to skip a campaign compliance check when one applies.

**A `publish_ready: true` result from this checker, by itself, is not publish approval.** It reflects
only that this checker's own rules currently pass. Real publishing still requires (a) the
`PublishingModule` gate above, and (b) actual human sign-off recorded outside this checker (see
`manual_checklist`) -- this module records structured findings, it does not authorize an action.

## 7. Known open questions (recorded honestly, not resolved by this document)

- No structured "has map/place tag" field exists anywhere in the current `ContentPackage` contract;
  `map_required` will remain `manual_review` until such a field is introduced and approved.
- The claim-risk keyword and Korean amount/quantity word lists are a conservative, editable starting
  set, not a legally reviewed exhaustive list -- new evasion phrasing should be expected and will
  require future additions.
- The OCR-ambiguity heuristic (Section 3.3) is a plain-text digit/letter pattern check, not real OCR
  or image analysis; it cannot detect ambiguity that only exists inside an image asset itself.
- `rights_manifest` entries are accepted and trusted structurally (a resolvable id with an allowed
  `rights_status` value) -- this module does not verify the manifest's own authenticity, chain of
  custody, or who populated it. That remains a human/upstream-system responsibility.
- `verification_mode="evidence_required"`'s evidence-completeness rule intentionally reuses
  `numeric_claim`'s own rule; whether every requirement type should eventually gain its own richer,
  type-specific evidence shape (e.g. an image-specific evidence type) is left to a future Phase.

## 8. Independent QA NO-GO correction record (this Sprint)

| # | Before | After |
|---|---|---|
| 1 | `campaign=123` normalized to an empty campaign and evaluated as if nothing was wrong | Blocked outright: `campaign_contract_invalid` |
| 2 | A dict campaign missing/mistyping `requirements` silently became `[]` | Blocked outright: `campaign_contract_invalid` |
| 3 | An unparseable `window_start`/`window_end` was silently dropped and the check could still pass | The requirement fails; never passes on an unparseable bound |
| 4 | `window_start` after `window_end` was never checked | The requirement fails: invalid campaign window |
| 5 | An internal exception during a requirement check respected that requirement's own `required` flag (could end up in `warnings` only) | Always blocks `publish_ready`, regardless of `required` |
| 6 | Claim-risk detection required an ASCII digit; Korean number words (십만원, 백만원, ...) were invisible to it | Korean amount/quantity words are independently sufficient claim/numeric signals |
| 7 | No handling for OCR-misread-shaped numbers | Digit/confusable-letter adjacency forces `manual_review`, never a confident pass/fail |
| 8 | Any string in `evidence_refs` satisfied `source_reference` by bare string equality | `evidence_refs` are structured `EvidenceReference` objects; a bare string is parsed as an id-only shell that can never be "complete" |
| 9 | (same as 8) | Structured evidence contract documented in Section 2.4 |
| 10 | Missing evidence fields were not checked at all | Missing `source_url`/`locator`, `captured_at`, `verified_at`, or an unapproved `rights_status` blocks the claim |
| 11 | No per-asset rights check existed at all | Each asset needs its own `rights_status` or an approved `upstream_rights_manifest_id` link |
| 12 | Package-level `rights_status` was the only rights signal checked | Package-level and per-asset rights are independent, both required |
| 13 | A duplicate `requirement_id` was deduplicated (first wins) with a non-blocking note | A duplicate `requirement_id` blocks the whole campaign contract |
| 14 | `verification_mode` was accepted/normalized but never branched on | `automatic`/`manual`/`evidence_required` each have defined behavior (Section 3.2) |
| 15 | (same as 14) | An unrecognized `verification_mode` blocks that requirement, regardless of `required` |
| 16 | Not documented | Section 6: `PublishingModule` gate AND this checker's `publish_ready` are both independently required |
| 17 | Not documented | Section 6: this checker's result alone is never publish approval |

Test suite: `tests/test_campaign_compliance_checker.py` grew from 33 to 61 tests covering every row
above plus the original regression set. `py -m unittest tests.test_campaign_compliance_checker -v` and
`py -m compileall modules/compliance` both pass cleanly.
