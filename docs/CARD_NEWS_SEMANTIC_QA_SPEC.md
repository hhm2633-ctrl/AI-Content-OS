# CardNews Semantic QA — Design Spec

Author: Claude Specialist (docs/CLAUDE_*.md lane)
Status: **DRAFT, design-only. No code, tests, `site/`, storage, or shared status document
touched.**

Legend: `CONFIRMED` = verified directly against current repository code/data at the time of
writing. `PROPOSAL` = design suggestion, not built. `CTO GATE` = requires explicit CTO decision
before any implementation Sprint may start.

**Explicit disclaimer (per task constraint): this document never claims automated QA — rule-based
or LLM-based — fully replaces human final review.** Every check proposed here is meant to
*surface* risk earlier and more consistently, the same way `CardNewsQualityChecker` already does
for structural/rendering risk. Final publish sign-off remains a human decision, consistent with
the existing "Lane D: Output QA" / "Lane F: Visual QA" read-only human-review lanes already
defined in `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`.

---

## 0. Why This Document Exists (Confirmed Root Cause)

`CONFIRMED` — read directly, same session, for this document:

The latest real run's `storage/workflow_results/05_content_result.json` has:

```json
{
  "fallback_used": true,
  "fallback_reason": "no_usable_llm_slide_content",
  "slides": [
    {"page": 1, "role": "hook", "headline": "이 주제, 바로 써도 될까요?", "body": "출처와 맥락 확인이 먼저입니다."},
    {"page": 4, "role": "cta", "headline": "확인 전에는 발행하지 마세요", "body": "근거가 확보되면 저장하세요."}
  ]
}
```

This is **entirely generic safety-checklist boilerplate** produced by
`ContentOutputNormalizer._build_full_fallback()` — it carries no real information about the
actual selected topic ("톡커들의 선택 명예의 전당"). The same run's
`storage/card_news/card_news_quality.json` result is:

```json
{"qa_score": 0.85, "passed": true, "warnings": ["layout_result.fallback_used=True (안전한 기존 레이아웃으로 대체 선택됨)."]}
```

**`passed: true`, one warning, and that warning is about layout choice — not about the fact that
the entire card carries zero real information.** This is the exact, reproducible instance of the
reported problem "실질 정보 없이 fallback 안내만 존재" going undetected. Root cause, confirmed by
direct code inspection:

```
grep -n "content_result.get(\"fallback_used\"\|fallback_reason\"" modules/card_news/card_news_module.py
-> no matches
```

`CardNewsModule.run(content_result, ...)` never reads `content_result["fallback_used"]` or
`content_result["fallback_reason"]` — the exact signal `ContentOutputNormalizer` already computes
and labels honestly is silently dropped before it ever reaches `card_news_result` or
`CardNewsQualityChecker`. Every other reported problem in this task (topic/body mismatch,
truncation, incomplete headline, CTA mismatch, brand clipping, `manual_image_required` confusion)
is a variant of the same underlying pattern: **the checker validates that things exist and are
structurally shaped correctly, never that they mean the right thing.**

---

## 1. What Current Automatic QA Validates vs. Does Not (Confirmed Inventory)

`CONFIRMED`, read directly from `modules/card_news/card_news_quality_checker.py`'s full 39-key
`checks` dict and `CHECK_POINTS` (100-point budget).

### 1.1 Validated Today (Structural / Rendering / Metadata-Presence Only)

| Category | Checks (confirmed keys) |
|---|---|
| File/structural | `png_exists`, `card_count_ok`, `file_size_ok`, `resolution_ok` |
| Layout/rendering fallback (separated, `CONFIRMED` per M7-next correction) | `layout_applied`, `layout_fallback_used`, `rendering_fallback_used`, `fallback_used` |
| Content structure (shape only) | `story_flow_applied`, `slide_continuity_ok` (index order + headline **non-empty**, not headline **correct**), `cta_slide_exists`, `highlight_exists` |
| Evidence/Social Proof usage honesty | `evidence_available`/`evidence_applied`, `social_proof_available`/`social_proof_applied`, `prohibited_fake_screenshot_absent`, `unlicensed_asset_not_rendered` |
| Debate/CTA application | `debate_should_apply`, `debate_required`, `debate_applied` |
| Attribution presence | `attribution_needed`, `attribution_present` |
| Typography/Mobile/Contrast (numeric limits only) | `typography_hierarchy_ok` (char/line count vs. `typography_rules.py` limits), `cover_readability_ok`, `mobile_readability_ok`, `visual_rhythm_ok`, `text_overflow_free`, `contrast_ok`, `source_legible`, `cta_focus_ok` |

Every one of the above is a **presence, count, or numeric-bound** check. None of them read what
the headline/body text actually *says*.

### 1.2 Confirmed Gaps (What Is Never Checked)

| Reported problem | Currently checked? | Confirmed evidence |
|---|---|---|
| 주제와 본문 의미 불일치 | No | No field anywhere in `card_news_quality_checker.py` compares slide text against `research_result`/`topic_result` keywords |
| 문장 절단 (mid-sentence/mid-word cut) | Partially, structurally | `slide_continuity_ok` only checks headline is non-empty; no check reads whether a sentence *ends properly* |
| 미완성 headline | No | `typography_hierarchy_ok` only checks `length <= max_chars` and `line_count <= max_lines` — a headline can pass at 15/18 chars while ending mid-clause |
| CTA 역할과 실제 행동 문구 불일치 | No | `cta_slide_exists` only checks a slide has `role=="cta"` or `cta_area` — never reads whether the CTA body's verb matches `pattern_prompt_meta.cta_type` |
| 브랜드명 잘림 | No | No check measures rendered text width against box bounds for the `"AI-Content-OS"` brand text or any footer text |
| 실질 정보 없이 fallback 안내만 존재 | **No** — this is §0's confirmed root cause | `content_result.fallback_used`/`fallback_reason` are never read by `CardNewsModule` or the checker |
| `manual_image_required` 상태와 게시 가능 상태 혼동 | Partially, in a different module | `CONFIRMED`: `PublishingModule._resolve_publishing_gate()` already blocks `publishing_ready` on `manual_image_required`/`real_image_used_count<=0` — but `CardNewsQualityChecker.passed` is computed **independently** and has no awareness of this gate at all. A reviewer looking only at `card_news_quality.passed: true` has no signal that publishing is blocked. |

---

## 2. Topic–Body Semantic Alignment Check

`PROPOSAL`. Goal: detect the §0 case (generic fallback text that never mentions the real topic)
without an LLM call as the first line of defense.

### 2.1 Rule-Based Layer (always runs)

Reuse the **exact term-matching pattern already proven and reviewed** in
`modules/card_news/evidence_selector.py::_build_topic_terms()` /`_score_relevance()` — same
tokenizer, same "≥2 matched terms AND score ≥ threshold" two-condition gate that already passed
Codex review for Evidence Selection (`CONFIRMED`, that code exists and is already trusted for a
similar honesty guarantee). Do not re-derive a new algorithm; reuse the *pattern*, in a new file
(see §15), never importing `evidence_selector.py` directly (keeps `card_news` submodules
independent, consistent with `modules/shorts/`'s "reuse pattern, not code" precedent already
established in `docs/SHORTS_ARCHITECTURE_DRAFT.md`).

```text
topic_terms = tokenize(research_result.keyword + title + key_points + topic_intelligence.keywords)
for each slide:
    slide_terms = tokenize(slide.headline + slide.body)
    matched = topic_terms ∩ slide_terms
    topic_alignment_score = |matched| / max(1, min(|slide_terms|, |topic_terms|))
    topic_aligned = |matched| >= 1 AND topic_alignment_score >= ALIGNMENT_THRESHOLD (PROPOSAL: start at 0.15,
                                                                                       lower than Evidence's 0.34
                                                                                       since slide text is short
                                                                                       and paraphrasing is expected)
```

`PROPOSAL` — critically, this check must be **whole-card aware, not per-slide-only**: a single
low-scoring slide (e.g. a legitimate "가장 공감되는 항목은 무엇인가요?" debate question with no
topic keywords) should not fail the card. Compute `card_topic_alignment_score` as the max (not
average) of the 4 slides' scores, plus a separate hard rule (§12) for the case where **zero**
slides mention the topic at all — that specific all-zero case is what actually happened in §0.

### 2.2 LLM Layer (optional, see §10–§11)

`PROPOSAL`: an optional second-pass LLM prompt — "Does this 4-slide card news actually discuss
{topic_title}? Answer only from the text given, do not assume outside knowledge." — used only to
raise confidence on borderline rule-based scores, never as the sole authority (§10).

---

## 3. Sentence Completeness Check

`PROPOSAL`, rule-based, no LLM required.

`CONFIRMED` starting point: `CardNewsTextOptimizer._trim_naturally()` already guarantees every
*optimizer-truncated* string ends in `"…"` (verified in the current file, §4 below). The gap this
section addresses is **content that was never truncated by the optimizer at all** — i.e. the LLM
or fallback template itself produced an incomplete sentence, and nothing downstream catches it.

### 3.1 Rule-Based Heuristics (Korean-specific, deterministic)

| Rule | Detects |
|---|---|
| Text does not end in `.`, `!`, `?`, `다`, `요`, `죠`, `까`, `세요`, or `…` (the confirmed valid Korean sentence-final set) | Sentence cut off before its natural ending |
| Text ends in a dangling particle/connective — `PROPOSAL` regex class: `(은|는|이|가|을|를|에|에서|으로|로|와|과|하고|해서|지만|는데|면서)$` | Classic "cut mid-clause" pattern (e.g. "확인이 먼저") |
| Text ends with an open bracket/quote with no matching close | Structural truncation |

These are **heuristics, not a parser** — false positives are expected and acceptable (flag for
review, never silently rewrite text — rewriting content is out of this spec's scope entirely,
consistent with "do not modify code" and the CardNews skill's "do not fabricate" principle).

### 3.2 Distinguishing From Legitimate Short/Fragment Style

`CONFIRMED` constraint from `.claude/skills/domain/cardnews.md`: card-news headlines/body are
intentionally short, sometimes fragment-style by design (e.g. "출처와 맥락 확인이 먼저입니다." is
a complete sentence at 14 chars). The rule set above only flags **grammatically dangling**
endings, not **short** ones — length is already governed separately by `typography_hierarchy_ok`.

---

## 4. Hard Truncation vs. Intended Ellipsis

`PROPOSAL` classification layer on top of `CONFIRMED` existing renderer behavior.

`CONFIRMED` (`card_news_text_optimizer.py`, current file):

- `_trim_naturally()` **always** appends `"…"` when it actually cuts text, and budgets the
  ellipsis itself into `max_length` (never overflows by 1 char for the ellipsis).
- `_optimize_body()` prefers removing **whole trailing sentences** before ever falling back to
  character-level `_trim_naturally()` — this was the exact fix for the "번호 매긴 목록이 항목
  번호만 남고 내용이 사라지는" defect already found and corrected in Phase M8.
- `_balance_title_body_ratio()` has a `preserve_cta_action` exception (`CTA_ACTION_PATTERN`) so a
  CTA slide's actual action sentence ("저장하세요" etc.) is not discarded just because the ratio
  budget was exceeded.

Given this, **the renderer-level architecture already prevents most silent truncation** — the
remaining risk is narrower than the raw problem statement implies. `PROPOSAL` classification:

| Signal (rule-based, checkable from `card_news_result` + slide text alone) | Classification |
|---|---|
| Text ends in `"…"` | `intentional_ellipsis` — not a defect by itself; only flag if it *also* fails §3's completeness heuristics on the text **before** the ellipsis (e.g. "확인이 먼저…" — ellipsis after a dangling particle is still bad) |
| Text does not end in `"…"` AND fails §3's dangling-particle/no-terminal-punctuation heuristic | `hard_truncation_suspected` — this is the real target: content that was cut (by an LLM, a copy-paste, or any future code path) **without** going through the optimizer's own ellipsis-marking discipline |
| Text length is exactly at a `typography_rules.py` `max_chars` boundary and ends mid-word with no `"…"` | `hard_truncation_suspected`, elevated confidence (strong correlation with an actual cut) |

This directly operationalizes the CardNews skill's existing rule: *"Do not silently truncate
content; show an ellipsis only at the hard limit."* — this check verifies that rule was actually
followed, rather than trusting it was.

---

## 5. Headline Grammar / Completeness Check

`PROPOSAL`, rule-based.

Reuses §3's dangling-particle/terminal-punctuation heuristics, applied specifically to
`slide.headline`, plus two headline-specific additions:

1. **Fallback-template signature detection** (`PROPOSAL`, high-confidence, zero false-positive
   risk since it matches an exact known template): `CONFIRMED` from
   `content_output_normalizer.py::_fallback_title()`, the generic fallback title is always
   exactly `f"{quoted_keyword} 확인 전 체크리스트"`. A rule-based regex match against this **exact
   confirmed template shape** (and the equivalent per-slide fallback headlines in
   `ContentModule`'s own `_fallback_slides()`, not read for this spec but same category) lets the
   checker deterministically detect "this headline is a template, not real content" — this is the
   single highest-value, lowest-risk rule in this entire spec, since it does not need to *infer*
   fallback status via heuristics at all; it can just also read `content_result.fallback_used`
   directly (§13) as the authoritative signal and use the template-signature match as a secondary
   confirmation / backstop for cases where the fallback flag itself might not propagate correctly.
2. **Question-mark headline consistency** (`PROPOSAL`, minor): if `headline` ends in `?`/`까요`
   but the slide's `role != "hook"` and no matching answer pattern appears in `body`, flag as a
   minor style warning only (not a hard-block candidate) — headline/body mismatch of this kind is
   a real but low-severity issue.

---

## 6. CTA Role vs. Actual Action-Verb Check

`PROPOSAL`, rule-based, directly extending `CONFIRMED` existing infrastructure.

`CONFIRMED`: `card_news_text_optimizer.py::CTA_ACTION_PATTERN` already detects *whether* a CTA
slide contains **some** action verb (저장/공유/댓글/팔로우/...). It does **not** check whether that
verb is the *correct* one for the actual `pattern_prompt_meta.cta_type` the run chose. This is
the exact gap the task names: "CTA 역할과 실제 행동 문구 불일치."

### 6.1 Proposed `CTA_TYPE_KEYWORD_MAP`

`PROPOSAL`, built from `CONFIRMED` `cta_type` vocabulary
(`modules/pattern_engine/cta_selector.py::CTA_TYPES = ["save", "comment", "dm", "profile",
"follow"]`):

| `cta_type` | Required keyword family (Korean, at least one must appear in the CTA slide body) |
|---|---|
| `save` | 저장 |
| `comment` | 댓글, 의견, 생각 |
| `dm` | DM, 메시지, 보내 |
| `profile` | 프로필 |
| `follow` | 팔로우, 구독 |

### 6.2 Check Logic

```text
cta_slide = the slide with role == "cta"
declared_cta_type = pattern_prompt_meta.cta_type   (CONFIRMED field, e.g. "follow")
required_keywords = CTA_TYPE_KEYWORD_MAP[declared_cta_type]
cta_action_matches_role = any(keyword in cta_slide.body for keyword in required_keywords)
```

`CONFIRMED` real example that would **pass** this check today: latest run's CTA body is "근거가
확보되면 저장하세요." with `cta_type: "follow"` (per `05_content_result.json`
`pattern_prompt_meta.cta_type`) — **this is an actual, real, currently-undetected mismatch**: the
declared strategy is `follow` but the rendered action verb is `저장` (save). This single real
example is direct, `CONFIRMED` proof this check would catch a genuine live defect matching the
task's problem list ("CTA 역할과 실제 행동 문구 불일치").

`PROPOSAL` severity: soft warning, not hard-block by default (§12) — a `save` action on a
`follow`-strategy card is still a coherent, publishable CTA (it just didn't follow the chosen
strategy); only escalate to hard-block if `cta_action_matches_role` is false **and** no keyword
from *any* `CTA_TYPE_KEYWORD_MAP` entry appears at all (i.e. the CTA slide has no recognizable
action verb whatsoever — a genuinely broken CTA).

---

## 7. Brand Name / Footer Clipping Check

`PROPOSAL`, rule-based, measurement-based (no OCR, no pixel scan of the rendered PNG required).

### 7.1 Confirmed Renderer Constants Available for Reuse

`CONFIRMED`, `modules/card_news/render_constants.py` (already the single shared source of truth
between the renderer and `MobileReadabilityChecker`, per Phase M8):

```python
RENDERER_FONT_SIZES = {"headline": 60, "body": 39, "small": 28, "brand": 26}
BOX_MARGIN = 65
BOX_BOTTOM = 990
```

`CONFIRMED`: the brand text `"AI-Content-OS"` is a **fixed literal string**, drawn at a fixed font
size (26px) at a fixed position (`box_left + 40`, `box_bottom - 55`) — it is not
topic/content-dependent, so its clipping risk is a **rendering-constant** property, not a
per-run content property.

### 7.2 Proposed Check

`PROPOSAL`: a lightweight, standalone measurement using `PIL.ImageFont` + the same font file
resolution order already used by the renderer (`C:/Windows/Fonts/malgunbd.ttf` etc.) — compute
`text_width("AI-Content-OS", font_size=26)` and compare against the available horizontal space
(`self.width - 2 * BOX_MARGIN - 40`, `CONFIRMED` layout arithmetic from `card_news_module.py`).
Since the brand string and font are fixed, **this check does not need to run per-slide-per-run —
it is a one-time renderer-constant sanity check** that can be a simple assertion/test (§14) rather
than a per-run QA field, unless the brand string itself ever becomes configurable (`CTO GATE`: is
`"AI-Content-OS"` expected to stay a hardcoded literal, or will multi-account/white-label branding
ever make it dynamic? If dynamic, this becomes a real per-run check, not a one-time constant
check).

### 7.3 Source Attribution / Footer Text (dynamic, per-run — different from brand text)

`CONFIRMED`: `card_news_module.py`'s source-attribution text (§CardNews M7/M8 Source Attribution)
**is** per-run dynamic (`source_name` truncated to `source_rule["max_chars"]` before drawing,
`CONFIRMED` from the earlier M7/M8 implementation). `PROPOSAL`: extend the same
`PIL.ImageFont`-measurement approach to this dynamic text at QA time (not just headline/body),
since it is the one piece of footer-region text that varies by run and therefore carries real
per-run clipping risk, unlike the fixed brand string.

---

## 8. Fallback Information Density / User Value Check

`PROPOSAL` — this section directly targets §0's confirmed root cause.

### 8.1 The Core Signal: Thread `content_result.fallback_used` Through

`CONFIRMED` gap (§0, §1.2): this signal already exists, is already honestly computed, and is
already dropped. The single highest-leverage fix in this entire spec is **making this existing
signal visible**, not inventing a new detector. See §13 for the exact schema change.

### 8.2 Beyond the Binary Flag: Information-Density Heuristic

`PROPOSAL`, for the case where `content_result.fallback_used` is `false` (real LLM content was
used) but the content is still thin/generic — a genuine "low information value" case the binary
flag cannot catch by itself:

```text
generic_phrase_hits = count of matches against a small, explicit list of known-generic phrases
                       (PROPOSAL starting list, all confirmed to appear in actual fallback
                       templates read in this session: "확인 전", "원문", "게시일", "검증된 핵심",
                       "근거가 확보되면" — i.e. literally reuse ContentOutputNormalizer's own
                       fallback vocabulary as the generic-phrase dictionary, since it is the
                       ground truth for "what generic filler looks like" in this project)
topic_term_hits = count of §2's topic_terms found across all 4 slides combined
information_density_score = topic_term_hits / max(1, topic_term_hits + generic_phrase_hits)
```

`PROPOSAL`: this is intentionally a **weak, advisory signal** (contributes to score, §12) rather
than a hard-block condition on its own — unlike §8.1's binary flag (which is authoritative because
it is a direct, confirmed upstream fact), phrase-matching against a small dictionary is inherently
approximate and should never solely gate publishing.

---

## 9. `manual_image_required` and Publishing Status Linkage

`PROPOSAL`, resolving the `CONFIRMED` gap in §1.2's last row.

`CONFIRMED` current state: `PublishingModule._resolve_publishing_gate()` already correctly blocks
`publishing_ready` when `manual_image_required` or `real_image_used_count<=0` — this logic is
**correct and already exists**, it is simply **not visible from `CardNewsQualityChecker.passed`**,
creating exactly the confusion the task names.

### 9.1 Proposed Resolution: One Authoritative `publish_eligible` Signal

`PROPOSAL`: define a single derived boolean, computed once, consumed everywhere (Gallery, any
future dashboard, any future automation) —

```text
publish_eligible = card_news_quality.passed
                    AND semantic_qa_result.passed   (new, this spec)
                    AND NOT card_news_result.image_sourcing_status.manual_image_required
                    AND publishing_result.status == "publishing_ready"
```

`CTO GATE`: **where** this combined signal should live is a real design decision, not something
this spec can settle unilaterally, since it touches three different modules' owned files
(`CardNewsModule`, `CardNewsQualityChecker`, `PublishingModule`) plus the already-existing
`card_news_result_manifest.py` (which — `CONFIRMED`, per this spec's required reading of
`docs/CARD_NEWS_RESULT_GALLERY_SPEC.md` — already computes an equivalent combined `status: "ready"
| "incomplete"` at the manifest layer). **Recommendation** (not a decision): compute
`publish_eligible` **only** at the manifest layer (already the established single point of
truth for "is this run good to publish", per the Gallery spec's own finding), rather than adding
a fourth place that also tries to compute it — avoids the exact "several modules half-agree on
readiness" confusion this section exists to fix.

---

## 10. Separation: Rule-Based Checks vs. LLM-Based Checks

`PROPOSAL` architecture.

| Layer | Contains | Runs | Failure mode |
|---|---|---|---|
| **Rule-based (mandatory, always runs)** | §2.1 (topic-term overlap), §3 (sentence completeness), §4 (truncation classification), §5 (headline heuristics + fallback-signature match), §6 (CTA keyword match), §7 (text-width measurement), §8.1 (fallback flag passthrough), §8.2 (generic-phrase density) | Every run, no network/LLM call, no config flag needed | Never raises past its own `check()` — same fail-safe contract as `CardNewsQualityChecker.check()` today (`CONFIRMED` pattern: try/except wrapping the whole `_check()`, safe zeroed result on exception) |
| **LLM-based (optional, config-gated)** | §2.2 (semantic topic relevance via prompt), and optionally a holistic "does this read as coherent, on-topic, human-quality copy?" review pass | Only when explicitly enabled (`CTO GATE`: config flag name/default, e.g. `semantic_qa.llm_review_enabled`, `PROPOSAL` default `false` until cost/quality is evaluated) | Must degrade to the rule-based result alone on any failure (§11) — never becomes the sole source of a hard-block (§12) |

**Design principle** (`PROPOSAL`): the LLM layer may only **raise** confidence in an already
rule-flagged issue or **soften** a borderline rule-based warning — it must never be the sole
reason a card is hard-blocked, since LLM output is itself non-deterministic and this project's
existing Offline-First / fallback-first principles (`CONFIRMED`, `PROJECT_OPERATING_SYSTEM.md`)
require every gate to degrade safely when the LLM is unavailable.

---

## 11. Deterministic Fallback on External LLM Failure

`PROPOSAL`, reusing the `CONFIRMED` existing pattern already proven throughout this project.

`CONFIRMED` precedent: `src/llm_client.py::LLMClient` already centralizes retry logic; every
LLM-calling module (`ContentModule`, `ImagePromptModule`) already follows "parse-then-fallback" —
on any LLM/parse failure, substitute deterministic fallback content and record `fallback_used`
honestly, never raise into `WorkflowEngine`.

`PROPOSAL` for `SemanticQAChecker`'s optional LLM layer: identical shape —

```python
def check(self, card_news_result, content_result, research_result):
    rule_based_result = self._check_rule_based(...)   # always computed first, never skipped
    if not self.llm_review_enabled:
        return rule_based_result | {"llm_review": {"attempted": False, "reason": "disabled by config"}}
    try:
        llm_result = self._check_llm(...)
        return rule_based_result | {"llm_review": llm_result}
    except Exception as error:
        return rule_based_result | {"llm_review": {"attempted": True, "available": False, "reason": str(error)}}
```

The **rule-based result is always the base** — the LLM layer can only add an additional
`llm_review` sub-object, never replace or gate the rule-based `checks`/`score`/`passed` fields.
This guarantees `semantic_qa_result` is always present and structurally valid even with zero LLM
availability, matching `workflow_completed`'s non-negotiable reliability contract
(`CONFIRMED`, `PROJECT_OPERATING_SYSTEM.md`: *"workflow_completed must never regress"*).

---

## 12. Score Weighting and Hard-Block Conditions

`PROPOSAL`. Deliberately kept **separate** from `CardNewsQualityChecker.CHECK_POINTS`
(`CONFIRMED` existing 100-point structural/production budget) — do not renumber or rebalance the
existing 39-key/100-point contract; add a **new, independent** `semantic_qa_score` (0–100) so the
existing, already-reviewed structural score's meaning never shifts.

### 12.1 Proposed `SEMANTIC_CHECK_POINTS` (sums to 100, mirrors existing pattern)

| Check | Points | Conditional? (mirrors `CONDITIONAL_CHECKS` pattern) |
|---|---|---|
| `topic_aligned` (§2) | 25 | No — always evaluated (topic terms always exist from `research_result`) |
| `sentence_completeness_ok` (§3, all 8 headline+body fields) | 20 | No |
| `no_hard_truncation_suspected` (§4) | 15 | No |
| `headline_not_fallback_template` (§5.1) | 15 | No |
| `cta_action_matches_role` (§6) | 10 | Soft — see §12.2, contributes to score but is not itself a hard-block trigger |
| `footer_text_not_clipped` (§7.3, dynamic source text only; §7.2's brand check is a build-time assertion, not scored per-run) | 5 | Conditional — only relevant when attribution/source text is actually rendered (mirrors existing `source_legibility_relevant` pattern) |
| `information_density_ok` (§8.2, threshold `PROPOSAL` e.g. ≥0.3) | 10 | Conditional — only scored when `content_result.fallback_used == false` (if fallback is already true, §12.2's hard block already applies, scoring density on top would be redundant) |

### 12.2 Proposed Hard-Block Conditions (fail-closed regardless of numeric score)

`PROPOSAL`, mirroring `CardNewsQualityChecker.PASS_THRESHOLD`'s existing "score AND structural
conditions" pattern (`CONFIRMED`: `passed = qa_score >= PASS_THRESHOLD and card_count_ok and
png_exists and file_size_ok` — passing already requires more than just a score today):

| Hard-block condition | Rationale | Maps to reported problem |
|---|---|---|
| `content_result.fallback_used == true` (direct passthrough, §8.1/§13) | Ground-truth signal that zero real LLM content survived — the single highest-confidence, zero-inference condition in this spec | "실질 정보 없이 fallback 안내만 존재" |
| `headline_not_fallback_template == false` on **any** slide (§5.1) | Exact-signature match against a known generic template — near-zero false-positive risk | Same as above, secondary confirmation |
| `no_hard_truncation_suspected == false` on **any** slide (§4) | A sentence that neither ends properly nor carries the renderer's own truncation marker is a genuine defect, not a style choice | "문장 절단", "미완성 headline" |
| `topic_aligned == false` on **all 4 slides simultaneously** (§2.1 — note: "all 4", not "any 1", per §2.1's design to avoid false-blocking a legitimate topic-agnostic debate-question slide) | Whole-card topic drift is a real defect; a single low-scoring slide is expected and normal | "주제와 본문 의미 불일치" |
| `publish_eligible == false` (§9) blocks **publishing**, but deliberately does **not** hard-block `semantic_qa_result.passed` itself | `manual_image_required` is an operational/sourcing gap, not a copy-quality defect — conflating the two would make the semantic QA score punish runs for an unrelated missing asset, re-creating a different version of the same "conflated signals" confusion this spec exists to resolve | "manual_image_required 상태와 게시 가능 상태 혼동" (resolved by keeping them **visibly separate**, not merged) |

Every other check in §12.1 (CTA mismatch, footer clipping, information density) is **score-only**
— it lowers `semantic_qa_score` but does not, by itself, flip `passed` to `false`. This mirrors
the existing project-wide principle (`CONFIRMED`, `CardNewsQualityChecker`'s own
`_conditional_ok()` docstring): only conflate "detected" with "must block" where the signal is
strong enough to justify it.

---

## 13. Required Result Schema Extensions

`PROPOSAL`. All additive, mirroring the exact shape already used by `typography_result` /
`mobile_readability_result` (`CONFIRMED` precedent from Phase M8) — no existing field renamed or
removed.

### 13.1 New field on `content_result` → `card_news_result` (passthrough only, §8.1)

`PROPOSAL`, smallest possible change, additive:

```json
{
  "content_fallback_status": {
    "fallback_used": true,
    "fallback_reason": "no_usable_llm_slide_content"
  }
}
```

`CTO GATE`: this requires a one-line addition inside `CardNewsModule.run()` (reading
`content_result.get("fallback_used")`/`get("fallback_reason")` into the result dict it already
assembles) — `card_news_module.py` is not this spec's owned file; implementing this is out of
scope for this document (§15 marks it as a required, minimal, clearly-scoped change for whoever
owns that file next).

### 13.2 New top-level `semantic_qa_result` on `card_news_result`

```json
{
  "semantic_qa_result": {
    "semantic_qa_score": 0.0,
    "passed": false,
    "checks": {
      "topic_aligned": false,
      "sentence_completeness_ok": true,
      "no_hard_truncation_suspected": true,
      "headline_not_fallback_template": false,
      "cta_action_matches_role": true,
      "footer_text_not_clipped": true,
      "information_density_ok": null
    },
    "per_slide": [
      {
        "page": 1,
        "topic_alignment_score": 0.0,
        "matched_topic_terms": [],
        "sentence_completeness_ok": true,
        "truncation_classification": "none | intentional_ellipsis | hard_truncation_suspected",
        "is_fallback_template_headline": true
      }
    ],
    "llm_review": {
      "attempted": false,
      "available": false,
      "reason": "disabled by config"
    },
    "hard_block_reasons": ["content_result.fallback_used"],
    "warnings": ["..."],
    "recommendations": ["..."]
  }
}
```

### 13.3 New derived field (§9, `CTO GATE` on placement) — `publish_eligible`

`PROPOSAL`, recommended location per §9.1: `card_news_result_manifest.py`'s output (already the
established single source of publish-readiness truth), **not** a new field on
`card_news_result`/`publishing_result` themselves.

---

## 14. Risk-Based Test List

`PROPOSAL`, no test-count target — one test per named risk, mirroring the `CONFIRMED` existing
approach in `tests/test_card_news_production_quality.py` (35 tests, each mapped to one specific
risk, no padding). All fixtures below are drawn from real, `CONFIRMED` data already read for this
spec, so they are not hypothetical.

| Risk | Test approach | Confirmed fixture basis |
|---|---|---|
| Fallback content silently scores well | Feed the exact §0 fixture (`content_result.fallback_used: true`) through the checker; assert `semantic_qa_result.passed == False` and `"content_result.fallback_used"` appears in `hard_block_reasons` | `05_content_result.json`, this session |
| Fallback-template headline goes undetected | Feed a slide with headline exactly matching `f"{keyword} 확인 전 체크리스트"`; assert `headline_not_fallback_template == False` | `content_output_normalizer.py::_fallback_title()` |
| A real, on-topic card is not falsely blocked | Feed a slide set where all 4 slides genuinely share ≥2 topic terms; assert `topic_aligned == True` and no hard-block | Synthetic, but modeled on the passing `08_card_news_result.json` (`톡커들의`/`선택`/`전당` in headlines) |
| Legitimate topic-agnostic debate-question slide does not sink the whole card | Feed 3 on-topic slides + 1 generic debate question slide (`CONFIRMED` real example: "가장 공감되는 항목은 무엇인가요?"); assert card-level `topic_aligned` still passes (per §2.1's "any slide, not all slides" — wait, §12.2 correctly uses "all 4" for the *hard-block*, so verify this specific case does NOT trigger the all-4 hard-block) | `debate_result.question`, `08_card_news_result.json` |
| Optimizer-added ellipsis is never flagged as a defect | Feed text ending in `"…"` with an otherwise-complete preceding clause; assert `truncation_classification == "intentional_ellipsis"`, not `"hard_truncation_suspected"` | `card_news_text_optimizer.py::_trim_naturally()` contract |
| Genuinely cut text without ellipsis is flagged | Feed text ending mid-particle with no `"…"`; assert `hard_truncation_suspected == True` | §4 rule design |
| CTA mismatch is detected but does not hard-block alone | Feed the exact `CONFIRMED` real mismatch (`cta_type: "follow"`, body "근거가 확보되면 저장하세요."); assert `cta_action_matches_role == False` **and** `passed` is not forced `False` by this alone (unless another hard-block condition also fires) | `05_content_result.json` `pattern_prompt_meta.cta_type` vs. CTA slide body |
| `manual_image_required` never silently flips semantic QA `passed` | Feed a semantically clean card with `image_sourcing_status.manual_image_required: true`; assert `semantic_qa_result.passed` is unaffected (stays based on copy quality only) while a separately-computed `publish_eligible` (§9/§13.3, wherever implemented) is `False` | `08_card_news_result.json` `image_sourcing_status` |
| LLM layer failure never breaks the checker | Force `_check_llm()` to raise; assert `semantic_qa_result.checks`/`semantic_qa_score`/`passed` are still fully populated from the rule-based layer alone, `llm_review.available == False` | §11 fallback design |
| Whole-checker exception never raises past `check()` | Pass malformed/`None` input; assert a safe zeroed result, mirroring `CardNewsQualityChecker.check()`'s own top-level try/except | `CONFIRMED` existing pattern, `card_news_quality_checker.py` lines 97-107 |

---

## 15. Minimal Implementation Order (Renderer Untouched)

`PROPOSAL`, phased so each phase is independently shippable and none require modifying
`CardNewsModule`'s actual Pillow drawing code (`_draw_layout_card`, `_draw_layout_text_content`,
`_fit_lines`, etc. — none of these are touched by any phase below).

| Phase | Scope | Touches renderer? | Touches other lanes' owned files? | Risk |
|---|---|---|---|---|
| **A** | New standalone `modules/card_news/card_news_semantic_qa_checker.py` (`PROPOSAL` name, mirrors `card_news_quality_checker.py` naming) implementing §2.1, §3, §4, §5, §6, §7.3, §8.2 as pure functions of `(content_result, card_news_result, research_result)` — **read-only, not called from anywhere yet**, invoked only by its own standalone tests | No | No — brand-new file, no existing file edited | Zero — cannot affect any existing behavior since nothing calls it |
| **B** | Add `content_fallback_status` passthrough (§13.1) — the single highest-value, lowest-risk change identified in this spec | No | Yes — one additive read inside `CardNewsModule.run()`'s existing result-assembly block | Low — purely additive, same pattern as every other Phase M7/M8 field addition already reviewed |
| **C** | Wire Phase A's checker into `CardNewsModule.run()` additively (`card_news_result["semantic_qa_result"] = ...`, same pattern as `typography_result`/`mobile_readability_result` in Phase M8) | No | Yes — additive call + one dict key, mirrors the exact wiring pattern already used and reviewed for Phase M8's checkers | Low — purely additive, follows an already-approved precedent |
| **D** | Enable the optional LLM layer (§10, §11) behind a config flag, default `false` | No | Yes — `SemanticQAChecker` file only (Phase A's own file) | Medium — introduces a real external dependency; `CTO GATE` on cost/quota/prompt content before enabling |
| **E** | Extend `CardNewsQualityChecker`'s own `CHECK_POINTS`/`passed` to *reference* (not merge into) `semantic_qa_result`, OR keep the two scores fully independent per §12's design and only combine them at the manifest layer (§9.1, §13.3) | No | Yes — `card_news_quality_checker.py`, an existing, actively-owned file | Requires a real `CTO GATE` decision: combine at the checker level or the manifest level (§9.1 recommends manifest level to avoid a fourth half-agreeing readiness signal) |

Phases A and B are independently valuable and lowest-risk — **A** ships a working semantic checker
with zero blast radius, **B** alone (even without A) already fixes §0's confirmed root cause by
making the existing, already-honest `fallback_used` signal visible. Neither requires the LLM layer
or any renderer change.

---

## Summary for Reviewers

This spec traces every one of the task's seven reported problems to a `CONFIRMED` gap in the
current 39-key structural QA checker, with at least one real, reproducible example read directly
from this session's actual `storage/` data for the two highest-value findings (§0's fallback-copy
case, §6's CTA-mismatch case). It proposes a separate, additive `semantic_qa_result` with its own
100-point score and a narrow set of high-confidence hard-block conditions (§12.2), explicitly
keeps `manual_image_required`/publish-readiness signals separate from copy-quality signals (§9),
separates deterministic rule-based checks (always on) from an optional LLM layer (config-gated,
never solely authoritative, §10–§11), and proposes a 5-phase implementation order where the first
two phases require no LLM call and touch no renderer drawing code. No code, test, `site/`,
storage, or shared status document was modified in writing this spec.
