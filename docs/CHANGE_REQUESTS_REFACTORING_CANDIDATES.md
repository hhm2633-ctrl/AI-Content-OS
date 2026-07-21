# Change Request Candidates — Refactoring / Duplication / Consistency

Status: **PROPOSAL ONLY. No code was changed to produce this document.** Every finding below was
verified by direct code reading; concrete file:line citations are given wherever possible so a future
Sprint can act on any single row without re-deriving the analysis. This document does not authorize
implementation of any item — each is a candidate for the CTO to triage into a future Sprint.

Scope note: this covers `modules/` only. `src/workflow_engine.py` and the protected pipeline were not
touched or analyzed for restructuring (out of scope by task instruction).

---

## 1. Duplicate code inventory

### CR-1: URL-safety validator duplicated (2 implementations)
- `modules/card_news/evidence_input_validator.py::_assess_public_url`/`_valid_public_url`
- `modules/affiliate/affiliate_safety_utils.py::is_safe_public_url`

Same rejection logic (scheme, userinfo, localhost, private/loopback/link-local/reserved IP); the
card_news version also returns a diagnostic risk dict, the affiliate version returns a plain bool.
Both docstrings self-document that this was a deliberate copy, not an import (project convention:
"reuse pattern, not code, across engines").

**Change Request**: extract a single `is_safe_public_url(url) -> bool` (+ an optional
`assess_public_url(url) -> (bool, dict)` wrapper for the richer card_news use) into
`modules/common/url_safety.py`. Both call sites import it. Net effect: one authoritative
implementation instead of two that could silently drift apart on a future edge case (e.g. IPv6
literal handling).

### CR-2: Timezone-aware datetime parser duplicated (3 implementations, 2 byte-identical)
- `modules/card_news/evidence_input_validator.py::_parse_datetime`
- `modules/affiliate/affiliate_safety_utils.py::parse_tz_datetime`
- `modules/compliance/campaign_compliance_checker.py::_parse_tz_datetime`

The affiliate and compliance versions are **exact code twins**. The card_news version is the same
algorithm with a richer return shape (`(datetime|None, original_text)` vs. `datetime|None`).

**Change Request**: extract `modules/common/tz_datetime.py::parse_tz_datetime(value) -> Optional[datetime]`.
Compliance and affiliate can delete their private copies outright (drop-in replacement, identical
signature). card_news can wrap the shared function for its richer return shape rather than
reimplementing the parse logic.

### CR-3: Safe-id/path-sanitization helper reinvented 4 times, 3 different algorithms
- `modules/affiliate/affiliate_safety_utils.py::normalize_id_component` — char-substitution regex.
- `modules/commerce/dry_run_executor.py::_safe_request_id` — same char-substitution regex, different fallback string.
- `modules/commerce/commerce_storage.py::_safe_request_id`/`normalize_request_id` — full-match regex + secret-keyword regex + SHA-256 fallback (materially stricter).
- `modules/affiliate/affiliate_revenue_router.py::_safe_request_id` — thin wrapper over `make_id_output_safe` (secret-detection + opaque hash) — a *third*, unrelated algorithm.

**Change Request**: this is the messiest cluster because the three algorithms have genuinely
different threat models (path-safety only vs. path-safety + secret-detection). Recommend
standardizing on the **strictest** existing behavior (commerce's secret-regex + hash fallback,
generalized) as one shared `modules/common/id_safety.py`, with two exported functions:
`sanitize_id_component(value) -> str` (structural-safety only, replaces the char-substitution
copies) and `make_id_output_safe(value) -> str` (secret-detection + opaque hash, replaces
commerce's and affiliate's independent secret-heuristics — see also CR-8). Do **not** silently
change either module's current output shape without an explicit approval, since `commerce`'s
hash-based fallback string differs from `affiliate`'s `opaque:` prefix — picking one changes
existing persisted/echoed ids' format.

### CR-4: `ALLOWED_RIGHTS_STATUSES` vocabulary duplicated 5x, plus a 6th divergent set
- `modules/card_news/evidence_input_validator.py::RENDER_ALLOWED_COPYRIGHT_STATUSES` (6 values — adds `permission_granted`)
- `modules/card_news/evidence_selector.py::RENDER_ALLOWED_COPYRIGHT_STATUSES` (5 values, tuple not frozenset)
- `modules/compliance/compliance_result.py::ALLOWED_RIGHTS_STATUSES` (5 values, explicitly documented as a copy)
- `modules/affiliate/affiliate_result.py::ALLOWED_RIGHTS_STATUSES` (5 values, explicitly documented as a copy)
- `modules/brandconnect/brandconnect_contract.py::ALLOWED_RIGHTS_STATUSES` (5 values, undocumented copy)
- **Divergent**: `modules/commerce/commerce_module.py` inline set — `{"granted","owned","licensed","permitted","merchant_owned","merchant_authorized","permission_confirmed"}` — same concept, a *completely different* vocabulary.

**Change Request**: two separate actions.
1. (Low risk) Extract the 5-value set to `modules/common/rights_vocabulary.py::ALLOWED_RIGHTS_STATUSES`
   for card_news/evidence_selector/compliance/affiliate/brandconnect to import. This is a value-set
   import, not a behavior change, as long as the 5 values are identical everywhere they're used today
   — **verify card_news's 6th value (`permission_granted`) is intentional before unifying**; if it is,
   the shared constant should be 6 values and the other 4 modules gain a value they don't currently
   accept (a real behavior change requiring sign-off, not a pure refactor).
2. (Needs a decision, not just a refactor) Reconcile Commerce's divergent vocabulary with the shared
   one, or explicitly document why Commerce's rights model is intentionally different (e.g. it may be
   modeling merchant-authorization semantics rather than pure copyright-status). **Do not silently
   merge these two vocabularies** — they may encode a real domain difference.

### CR-5: `_load_json`/`_save_json` boilerplate copy-pasted in 17+ files
Byte-identical `(path, default) -> dict` / `(path, data) -> None` pair confirmed in:
`analytics_storage.py`, `audit_storage.py`, `competitor_storage.py`, `performance_score_storage.py`,
`learning_storage.py`, `knowledge_storage.py`, `source_health_tracker.py`,
`competitor_learning_storage.py`, `pattern_result_writer.py`, plus a second identical
no-args-history-load variant in `analytics_history.py`/`audit_history.py`/`brand_dna_history.py`/
`trend_memory_history.py`/`knowledge_history.py`/`learning_history.py`/
`content_performance_history.py`/`competitor_history.py`/`performance_score_history.py`. 43 files
total contain an inline `with open(...) json.load/dump` block.

**Change Request**: extract `modules/common/json_store.py` with `load_json(path, default) -> dict`
and `save_json(path, data) -> None` (fail-closed: any read error returns `default`, never raises).
This is the single highest-volume, lowest-risk duplication in the repo — every occurrence found is
logically identical, so this is a pure mechanical extraction with no behavior-preserving ambiguity.
Recommend doing this one first if only one CR from this document is approved.

### CR-6: The "*History" wrapper class is itself a template (superset of CR-5)
`MAX_RECORDS = 500` constant + `record()`/`_record()` + append-with-`recorded_at`-timestamp +
truncate-to-last-500 + `_save_json({"updated_at":..., "records":...})` — confirmed byte-identical
structure (differing only in field names and a print-prefix string) across `analytics_history.py`,
`audit_history.py`, `brand_dna_history.py`, `trend_memory_history.py`, `knowledge_history.py`,
`learning_history.py`, `content_performance_history.py`, `competitor_history.py`,
`performance_score_history.py` (9 files).

**Change Request**: once CR-5 lands, extract a `modules/common/bounded_history.py::BoundedHistory`
base class: constructor takes `output_dir`/`filename`/`max_records`; exposes `record(entry: dict)`
(adds `recorded_at`, truncates, saves) and `load() -> dict`. Each engine's `*History` class becomes a
thin subclass supplying only its own domain field names. Larger diff than CR-5 (9 classes touched)
but removes ~15-20 lines of copy-pasted logic per file.

### CR-7: `run()` fallback wrapper idiom inconsistently applied
Nine modules (`analytics_engine`, `audit_engine`, `brand_dna_engine`, `competitor_engine`,
`competitor_learning`, `knowledge_engine`, `learning_engine`, `performance_score`, `trend_memory`)
share one exact `except Exception as error: print(f"{Module} Failed, safe fallback returned: {error}")`
+ `self._fallback_result(...)` idiom. By contrast, `card_news_module.py`, `commerce_module.py`,
`trend_collector_module.py`, and `topic_engine_module.py::run()` have **no top-level try/except at
all** — an exception here propagates uncaught, unlike the fallback-first contract documented in
`CLAUDE.md`/`AGENTS.md` for the rest of the pipeline. `modules/base_module.py` provides no shared
safety net (`run()` just raises `NotImplementedError`; no template-method hook).

**Change Request**: two parts, different risk levels.
1. (Low risk, mechanical) For the 9 already-consistent modules, add a `BaseModule.run_safely(self,
   *args, **kwargs)` template method that wraps `self.run(...)` in the shared try/except idiom, so the
   print statement and fallback-invocation pattern lives in one place instead of 9. Existing `run()`
   bodies are unchanged; only the wrapper is centralized.
2. **(Needs explicit approval — a real behavior change, not a refactor)**: `card_news_module.py`,
   `commerce_module.py`, `trend_collector_module.py`, `topic_engine_module.py` currently have zero
   top-level exception handling in `run()`. Given this project's stated "fallback-first,
   `workflow_completed` must never regress" invariant, this is arguably a real gap, not just a style
   inconsistency — but adding a top-level try/except to these 4 core-pipeline modules changes their
   failure behavior and must not be done without explicit sign-off, since it touches the protected
   pipeline's error-propagation contract.

### CR-8: Five independent "does this look like a secret" heuristics
- `affiliate_safety_utils.py::looks_like_sensitive_identifier` — JWT-shape + path-char + keyword-regex + high-entropy-token regex → SHA-256[:16] opaque hash.
- `commerce_storage.py::_safe_request_id` — its own secret regex (`secret|token|password|api[_-]?key|...|sk-`) → SHA-256[:24] hash.
- `commerce/audit_logger.py::_looks_like_secret` — `len>=32 and no-space and isalnum()` heuristic + a hardcoded forbidden-key list.
- `common/service_diagnostic.py::mask_secrets` — regex-substitution keeping the key name, masking only the value (`sk-...`/`Bearer ...`/`key=...` patterns).
- `commerce/credential_manager.py::redact` — always returns the constant `"***REDACTED***"`.

**Change Request**: these solve genuinely different problems (id-replacement vs. log-line-masking
vs. dict-key-redaction vs. constant-redaction) so a single shared function is not a clean fit. Instead,
recommend consolidating the **detection** heuristic only (`looks_like_sensitive_identifier`-style:
JWT/path/keyword/entropy checks) into `modules/common/secret_detection.py`, and let each consumer
decide its own redaction *action* (hash vs. mask vs. constant) based on that shared detector. This
avoids a forced behavior change on any of the 5 call sites while still removing the 4x duplicated
detection logic itself.

### CR-9: `safe_number` sanitization present in 6 forms of varying strictness
Only `affiliate_safety_utils.py::safe_number` does the full NaN/Infinity/negative/bool rejection.
`compliance/campaign_contract.py::_clean_number` accepts `NaN`/`Infinity`/negative (materially
weaker — same name, different guarantee). `brandconnect_contract.py` only checks int/negative
inline. `card_news_result_manifest.py::_non_negative_int`, `instagram_post_schema.py`, and
`competitor_learning_statistics.py` each reinvent a subset.

**Change Request**: extract `modules/common/numeric_safety.py::safe_number(value) -> Optional[float]`
(the affiliate strictness level, since it's the most complete). **Flag `compliance/campaign_contract.py::_clean_number`
specifically for review** — it currently accepts `NaN`/`Infinity`/negative values for
`minimum_count`/`maximum_count` on a `CampaignRequirement`, which is a real correctness gap (not just
duplication) independent of any refactor: a malformed `minimum_count=float("inf")` would currently
pass through unrejected. This is worth a standalone bug ticket regardless of whether the shared
utility extraction happens.

### CR-10: Config-loading-with-fallback-dict pattern repeated ~7+ places
Identical `if not path.exists(): return fallback(); try: json.load(...) except Exception:
return fallback()` shape in `topic_classifier.py`, `publishing_module.py`, `trend_source_manager.py`,
`content/brand_rule_evaluator.py`, `content/cta_strategy.py`, `brand_dna_engine/brand_profile_loader.py`
(27 files contain some `_fallback_*`/`_DEFAULT_*_CONFIG` shape).

**Change Request**: extract `modules/common/config_loader.py::load_json_config(path, fallback_factory)
-> dict` (fallback as a zero-arg callable so each caller keeps its own hardcoded default dict, only
the load-with-fallback control flow is shared). Mechanical, low risk — the fallback *values* stay
exactly where they are today, only the surrounding try/except is centralized.

---

## 2. Recommended shape of a shared `modules/common/` addition

`modules/common/` today has only `metadata_standard.py` (already a good precedent for this kind of
module) and `service_diagnostic.py`. Proposed new files, in priority order (highest
duplication-count / lowest risk first):

1. `modules/common/json_store.py` — CR-5.
2. `modules/common/tz_datetime.py` — CR-2.
3. `modules/common/url_safety.py` — CR-1.
4. `modules/common/config_loader.py` — CR-10.
5. `modules/common/numeric_safety.py` — CR-9.
6. `modules/common/rights_vocabulary.py` — CR-4 (pending the value-set reconciliation decision above).
7. `modules/common/bounded_history.py` — CR-6 (larger diff, do after 1-5 land and prove the pattern).
8. `modules/common/secret_detection.py` — CR-8 (detection only).
9. `modules/common/id_safety.py` — CR-3 (needs an explicit decision on which existing algorithm becomes canonical before implementation).

## 3. Exception-handling consistency

357 `except Exception`/`except (...)` blocks across 141 files. Three inconsistent idioms coexist,
sometimes in the same file (e.g. `card_news_module.py` mixes silent `except Exception:` with
logged `except Exception as error:` in different methods):
- **Silent-pass** (no log at all) — common in `_load_json`-shaped helpers.
- **Print-then-fallback** — the dominant idiom in the 9 Intelligence Engine modules (CR-7).
- **No handling** — 4 core-pipeline modules (CR-7 part 2).

**Change Request**: adopt one written convention (e.g. "silent-pass is only acceptable inside a
`_load_json`-style pure loader that already has an explicit fallback return; every module-level
`run()`/public method must use print-then-fallback, never silent-pass") and record it in
`.claude/skills/` or `AGENTS.md` once agreed, rather than changing code first. This is a policy
decision the CTO should make before any mechanical enforcement pass.

## 4. Other repeated structural patterns worth naming (no CR yet — observation only)

- `build_<domain>_result`/`build_error_result` pairs (`affiliate_result.py`, `compliance_result.py`)
  are same-shape-different-details; not worth merging (the "blocking_reasons" schema differs per
  domain) but worth keeping as the template for any *future* new domain module (commerce/compliance/
  affiliate/brandconnect all already converged on this shape independently — a good sign it's the
  right idiom to keep using, not to fight).
- Two independent "most-restrictive-wins" rank tables exist inside the affiliate package alone
  (`affiliate_result.py::STATUS_RANK` and `affiliate_policy_gate.py::API_STATUS_RANK`) — low-risk,
  same-file consolidation candidate if that package is touched again.
- The `_normalize_*` dict-defensive-parsing idiom (`_clean_str`/`_clean_str_list`/`_clean_number`-style)
  is repeated in 13+ files; `compliance/campaign_contract.py`'s docstring already explicitly
  acknowledges copying it from `content_output_normalizer.py`/`evidence_input_validator.py`. Same
  disposition as CR-9/CR-10 — a shared "defensive dict parsing" helper module is plausible but lower
  priority than the JSON/datetime/URL extractions above since the per-domain field lists differ enough
  that the shared surface would be small (`_clean_str`/`_clean_str_list`/`_clean_bool` only).
- `modules/commerce/commerce_storage.py::save`'s atomic tempdir-write-then-`os.replace` pattern is
  more robust than the plain `open().write()` used by every `_save_json` elsewhere in the repo. Worth
  considering whether `json_store.py` (CR-5) should adopt the atomic-write pattern as its default,
  given how many modules would inherit it "for free" — flagged for CTO decision, not assumed.

## 5. Real bug found during this audit (not a duplication issue, but discovered while investigating CR-2/CR-9)

**`modules/image_prompt/image_prompt_module.py::run()`** does not wrap its `self.llm_client.generate_text(...)`
call in a try/except. Only `_safe_json_parse` (which processes the LLM's *response*) has a fallback
path; if `generate_text` itself raises (a real network/API failure, not a parse failure), the
exception propagates uncaught out of `run()`. This is inconsistent with the fallback-first contract
this project documents for every other external-API-calling module (e.g. `ImageGenerationModule`
explicitly catches and records failures). Confirmed by a new regression test
(`tests/test_image_prompt_module.py::test_llm_client_raising_exception_propagates_uncaught`) that pins
the current (uncaught) behavior rather than silently assuming it's already handled. **Recommend a
follow-up bug-fix Sprint item, separate from the refactor CRs above** — this is a correctness gap in
the fallback-first invariant, not a code-duplication concern.

## 6. Dead code candidate (not a duplication issue)

`modules/topic/topic_engine.py::TopicEngine` — confirmed zero references anywhere outside its own
file; `src/workflow_engine.py` imports only `modules/topic_engine/topic_engine_module.py::TopicEngineModule`.
The two files are near-identical in logic (both implement `_select_best_topic`/`_fallback_topic`/
`_save_result`), but only the live `TopicEngineModule` additionally handles
`trend_result["selected_topic"]`. **Recommend deletion** once the CTO confirms no external
tool/script/notebook references `modules.topic.topic_engine` — this document does not delete it.

Similarly, `modules/trend/` is an empty directory (no `__init__.py`, no files) — vestigial, safe to
remove or ignore.
