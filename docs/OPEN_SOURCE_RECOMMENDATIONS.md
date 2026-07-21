# Open Source Recommendations — Immediate Productivity Candidates

Status: **RESEARCH/PROPOSAL ONLY. Nothing was installed; `requirements.txt` was not modified.**
Current dependency footprint (confirmed by reading `requirements.txt`): `openai`, `python-dotenv`,
`pillow` only — a genuinely minimal footprint, so every recommendation below is a real net-new
addition, not a duplicate of something already present.

Selection principle per the task instruction ("지금 당장 붙이면 생산성이 올라가는 것"): every item
below is chosen because it directly answers a **concrete duplication or gap this same audit already
found** (see `docs/CHANGE_REQUESTS_REFACTORING_CANDIDATES.md`), not a generic "nice library" list.

---

## Tier 1 — directly answers a finding in this audit's own Change Request document

### 1. `pydantic` (v2)
**Why now**: CR-9/CR-10 and the "13+ files with `_normalize_*`/`_clean_*` dict-defensive-parsing"
observation (Section 4 of the Change Request doc) show this project hand-rolls the same
"defensively parse an untrusted dict into a typed shape, never raise" logic in `campaign_contract.py`,
`brandconnect_contract.py`, `affiliate_contract.py`, `content_output_normalizer.py`,
`evidence_input_validator.py`, and more — every one of them reinventing field-by-field
`isinstance`/`.get()`/fallback logic that Pydantic does natively, with better error messages, for
free. Pydantic models can still return a "safe default on validation failure" shape (via
`model_validate(..., strict=False)` + a fallback-constructing `except ValidationError:` at the call
site) — the fallback-first philosophy is preserved, only the field-by-field boilerplate is removed.
**Adoption note**: this would be a real refactor, not a drop-in — recommend introducing it only for
**new** contract modules first (proves the pattern without touching the ~10 existing modules that
already work), then migrating existing ones opportunistically per the Change Request doc's own
"don't change working code without approval" caution.
**Estimated setup time**: 10 minutes to add the dependency; a full day to convert one existing
contract module as a proof-of-concept.

### 2. `tenacity`
**Why now**: this project has at least 2-3 independently-hand-written retry implementations
(`modules/trend_collector/retry_policy.py`'s `RetryPolicy`, `LLMClient`'s own
`retry_count`/`retry_backoff_seconds` loop in `src/llm_client.py`, and presumably similar logic inside
`ImageGenerationModule`'s retry handling per the earlier test-coverage audit's mention of
`_retry_delay_for_retry`). `tenacity` is the standard, battle-tested Python retry library
(exponential backoff, jitter, retry-on-exception-type, max-attempts) and would let these three
call sites share one well-tested implementation instead of three subtly-different hand-rolled ones —
directly the same "reduce duplicate reinvention" goal as this audit's Change Request document, just
for retry logic specifically instead of JSON/datetime/URL helpers.
**Adoption note**: same caution as Pydantic — do not touch the 3 existing working retry
implementations without explicit approval; introduce `tenacity` for any *new* retry-needing code
first.
**Estimated setup time**: 10 minutes to add; an hour to write one wrapped example.

### 3. `rapidfuzz`
**Why now**: `modules/trend_memory/trend_memory_checker.py::_similarity` uses Python's built-in
`difflib.SequenceMatcher` for topic-repeat-risk detection (confirmed by direct code reading during
this audit's test-writing pass). `difflib` is pure-Python and meaningfully slower than `rapidfuzz`
(a C++-backed library, drop-in-compatible `ratio()`-style API) for repeated string comparisons —
directly relevant since `_similarity` runs once per recent-record per check, i.e. up to
`RECENT_WINDOW` (10) comparisons per run. Also gives access to token-sort/partial-ratio matching
(useful if topic titles are ever reordered/paraphrased rather than verbatim-repeated, which
`SequenceMatcher`'s pure character-diff approach handles less gracefully).
**Adoption note**: `rapidfuzz.fuzz.ratio(a, b) / 100.0` is a near drop-in replacement for
`SequenceMatcher(None, a, b).ratio()` — low-risk, mechanical swap, but still requires the repo's
"don't change existing working code without approval" gate per this task's instructions; proposed
here as a candidate, not applied.
**Estimated setup time**: 10 minutes to add; under an hour to swap the one call site if approved.

### 4. A structured logging library (`structlog` or plain `logging` + `python-json-logger`)
**Why now**: the test-coverage/duplication audit found 357 `except Exception` blocks across 141
files, with three inconsistent handling idioms (silent-pass / print-then-fallback / no-handling-at-all
— Change Request Section 3). Every "print-then-fallback" site uses a bare `print(f"...")` — no log
level, no structured fields (module name, error type, timestamp beyond what's in the string), and no
way to filter/redirect output without changing source code. A structured logger (even just Python's
built-in `logging` module, configured once in `main.py`, is enough — `structlog` is a nicer-to-use
option if a dependency is acceptable) would let every module emit `logger.warning("fallback_used",
module=..., reason=...)`-shaped events that are filterable, greppable, and redirectable (e.g. to
`storage/runtime/` alongside the existing `ServiceDiagnostic` records) without changing the
underlying fallback-first behavior at all — purely a logging-mechanism upgrade.
**Adoption note**: highest blast-radius item in this list if done as a sweeping replace-all-prints
pass (357 call sites) — recommend introducing the logger and converting only *new* code plus perhaps
one pilot module, not a repo-wide mechanical find-replace, given this task's explicit "don't change
existing behavior without approval" constraint.
**Estimated setup time**: 30 minutes to configure; ongoing incremental adoption per-module.

---

## Tier 2 — general productivity tools with a plausible but less-audited fit

### 5. `python-magic` or Pillow's own format sniffing (already partially covered)
Commerce/Compliance/CardNews's evidence-input validators already check image decodability via
`PIL.Image.open(...).verify()` — this is already the right approach; no change recommended. Listed
here only to explicitly note it was checked and is **not** a gap (avoiding a false-positive
recommendation).

### 6. `jsonschema`
An alternative/complement to Pydantic (Tier 1 #1) for any place where a JSON Schema document itself
(not a Python class) is the more natural artifact — e.g. `docs/RESEARCH/AFFILIATE/AFFILIATE_NETWORK_EVIDENCE_MATRIX.md`'s
own §5 already writes out a JSON-Schema-shaped example contract by hand. If the team prefers
schema-as-data (versionable JSON files) over schema-as-Python-classes (Pydantic), `jsonschema` is the
standard validator for that style. Recommend picking **one** of Pydantic or `jsonschema` as the
project's standard, not both, to avoid yet another "two ways to do the same thing" duplication of the
exact kind this audit's Change Request document is trying to reduce.

### 7. `freezegun`
This project's own test suites (Compliance, Affiliate, and the new tests added in this task) all
hand-roll a `NOW = datetime(...)` constant plus an `iso(delta)` helper to get deterministic,
timezone-aware timestamps for freshness/expiry tests. `freezegun`'s `freeze_time()` context
manager/decorator would let `datetime.now(timezone.utc)` calls *inside the module under test* also be
frozen, which the current hand-rolled approach cannot do (today's tests only control the timestamps
*they pass in*, not what `datetime.now()` returns inside the module itself — this is fine for the
current fully-injected-timestamp design, but would matter if any future module calls
`datetime.now()` internally and needs to be tested deterministically). Low urgency, flagged as a
"know this exists" item for future test-writing Sprints.

### 8. `respx` or `responses` (HTTP mocking)
If/when the trend-collector network-calling collectors (`bobaedream_collector.py`,
`naver_news_collector.py`, `nate_pann_collector.py`, etc. — flagged as **zero-test** in the
test-coverage audit) are ever given real unit tests, they will need to mock outbound HTTP calls.
`responses` (for `requests`) or `respx` (for `httpx`) are the standard libraries for this — check
which HTTP client the collectors actually use (not verified in this pass) before picking one. Flagged
here specifically because it directly unblocks the single largest remaining test-coverage gap this
audit identified (`trend_collector`'s individual site collectors).

---

## Explicitly considered and NOT recommended

- **A local open-source image-generation model (Stable Diffusion/FLUX/Qwen-Image, run locally via
  ComfyUI/diffusers)**: this project already has a working, policy-compliant image pipeline via
  OpenAI's `gpt-image-1` with an established fallback chain (`ImageGenerationModule` →
  solid-color-background fallback). Self-hosting an open-source image model would add GPU/infra
  requirements, a new fallback-safety surface to design, and licensing/rights-provenance questions
  (exactly the kind of "unlicensed asset reuse" risk `docs/EXTERNAL_ENGINE_PORTFOLIO_STRATEGY.md`
  already flags as a rejection criterion for borrowed patterns) — not a "plug in today" win given the
  existing pipeline already works and passes QA.
- **A browser-automation library for direct SNS posting** (Selenium/Playwright-for-publishing,
  any "auto-poster" package): explicitly against this project's stated policy (see the MCP evaluation
  document, Sections 1, 7, 11) — not recommended regardless of library quality.
- **A full ORM (SQLAlchemy) or a database engine**: this project is deliberately flat-file/JSON-based
  (`storage/*.json`) by design across every existing Engine; introducing a database would be a
  structural change far outside this task's "don't change Workflow/architecture" boundary, and no
  finding in this audit suggests the current file-based approach is actually a bottleneck yet (see
  `docs/PERFORMANCE_OPTIMIZATION_CANDIDATES.md`'s PC-2 note that Knowledge DB growth is the one
  genuinely-worth-watching case, and even that doesn't yet justify a database migration).
