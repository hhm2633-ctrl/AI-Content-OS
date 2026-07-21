# Instagram Feed-Native Design Scan V1 — Recovery & Merge Report

Status: CANDIDATE only. No VERIFIED, PROVEN, or performance-causal claim is made anywhere
in this recovery or in the merged/imported outputs it describes.

## Source runs reconciled

- **Run A** — `.claude/worktrees/ig-feed-native-scan-v1/storage/design_learning/instagram_feed_native_design_scan_v1.json`
  `scan_id: instagram_feed_native_design_scan_v1`, `generated_at: 2026-07-14`, sources
  `home_feed_natural` + `explore_feed_natural`, **8 detailed candidates** (of a 30-candidate
  target; 47 posts triaged). QA report: `.claude/worktrees/ig-feed-native-scan-v1/external_workclaude/instagram_feed_native_design_scan_v1/QA_REPORT.md`.
- **Run B** — `storage/design_learning/instagram_feed_native_design_scan_v1.json` (main checkout)
  `scan_id: instagram_feed_native_design_scan_v1`, `scan_date: 2026-07-15`, source
  `home_feed_natural` only, **18 detailed candidates** (of a 30-candidate target; ~40 posts
  scrolled past). Session logged in as `ho_hong_hongs`; screenshot-capture tool was
  intermittently unreliable mid-session (documented as a tool limitation, not a content issue).

Both files pass JSON validation and are internally consistent with their own counts fields.

## Deduplication method

1. Match on `post_url` (exact string match) first.
2. Where `post_url` is missing on either side, fall back to an `(account_handle,
   cover_hook_text)` signature match.

## Results

| Metric | Value |
|---|---|
| Run A candidate count | 8 |
| Run B candidate count | 18 |
| URL-based overlap | 0 |
| Signature-based overlap | 1 |
| **Total overlap (duplicate posts)** | **1** |
| **Merged unique candidate count** | **25** |

### The one duplicate found

`hongik.man`'s "Claude Fable 5 / 페이블 활용법 8가지" post was observed independently in both
runs:

- Run A, `observed_order: 2`: `post_url: null`, `visible_post_age: "2시간"`,
  `mapped_existing_layout_candidate: "number_list"`.
- Run B, `observed_order: 1`: `post_url: "https://www.instagram.com/p/DaxEq30IB53/"`,
  `visible_post_age: "9시간"`, `mapped_existing_layout_candidate: "tutorial"`.

Both entries share the identical `cover_hook_text` ("Caude Fable 5 / 페이블 활용법 8가지") and the
same caption CTA deadline text ("7월 19일까지 연장"), and the age gap (2h → 9h) is consistent with
the same post being observed ~7 hours apart across the two scan sessions (Run A generated
2026-07-14, Run B scan_date 2026-07-15). This is treated as **one real-world post observed
twice**, not two distinct posts.

Resolution: Run B's observation was kept as the canonical merged entry (it has a resolvable
`post_url`, which Run A's does not). Run A's observation was preserved in full as a
`duplicate_observations` entry attached to the canonical candidate, for provenance — it was
**not** double-counted in the merged/imported totals. Note the two observations disagree on
`mapped_existing_layout_candidate` (`number_list` vs `tutorial`); the merge does not attempt to
adjudicate which is "more correct" — both raw observations are preserved as-is for a human to
review if needed.

No other account/signature overlaps were found. All other 24 candidates (7 remaining from Run
A, 17 remaining from Run B) are distinct posts by distinct accounts with distinct post URLs (or
distinct content where URL was unresolved).

## Outputs produced

1. **`storage/design_learning/instagram_feed_native_design_scan_merged_v1.json`**
   Merged, deduplicated, provenance-preserving dataset. Every one of the 25 unique candidates
   keeps its original per-candidate fields unchanged, wrapped with `merged_id`, `provenance`
   (`run_id`, `observed_order`), and — for the one duplicate — a `duplicate_observations` array
   holding the folded-in Run A record. Top-level `source_runs`, `dedup_method`, `counts`, and
   `duplicate_pairs` document exactly how the merge was performed. `output_judgment` reiterates
   the CANDIDATE-only status.

2. **`storage/design_learning/instagram_feed_native_design_scan_merged_v1_flat.json`**
   Intermediate flattened form (candidate fields at top level, `merged_id` /
   `provenance_run_id` embedded) used only as import-time input — the existing
   `instagram_feed_scan_importer.import_scan()` contract expects a flat `candidates` array
   matching the original per-run scan schema, so this flattening step lets the unmodified,
   already-tested importer run against the merged data without changing its logic or its test
   suite's expectations.

3. **`storage/design_learning/instagram_feed_native_design_scan_merged_v1_imported.json`**
   The importer's output: **25 imported, 0 rejected, 0 warnings**. Every imported candidate has
   `status: "candidate"`, a `layout_id` drawn from the existing 10-layout catalog (source of
   truth: `LayoutRuleEngine.supported_layouts()`), a `confidence` of `"low"` or `"medium"`
   (never higher — the importer has no `"high"`/`"verified"` tier), and an `evidence` block
   built only from fields actually present in the scan (nulls are preserved, never
   backfilled/fabricated).

## Importer code brought into the main checkout

Copied unmodified from `.claude/worktrees/design-learning-import-v1/modules/design_learning/`
into `modules/design_learning/` in the main checkout (this module directory previously only
held the older `card_news_design_learning.py` for the separate
`external_workclaude/instagram_broad_learning_v1` importer path — that file was left untouched):

- `modules/design_learning/layout_candidate_map.py` — `known_layout_ids()`, reading the 10
  layout IDs from `LayoutRuleEngine.supported_layouts()` (fallback to
  `LayoutRuleEngine.FALLBACK_RULES.keys()` on any exception) so this module never maintains its
  own copy of the layout list.
- `modules/design_learning/instagram_feed_scan_importer.py` — `import_scan(scan_path,
  output_path=None)`. Rejects any candidate whose `post_type != "carousel_cardnews"`, whose
  `mapped_existing_layout_candidate` is missing, or whose layout id isn't one of the 10 known
  ids. Never raises on a missing/malformed scan file — returns `status: "candidate"` with a
  `warnings` entry instead (fallback-first, consistent with the rest of this codebase).
- `tests/test_design_learning_instagram_feed_scan_importer.py` — 11 focused unit tests (layout
  count, successful import + evidence passthrough, each rejection reason, low-confidence
  triggers, non-fabrication of null engagement metrics, missing-file and malformed-input
  handling, output-file writing).

`py -m compileall modules\design_learning tests\test_design_learning_instagram_feed_scan_importer.py`
and `py -m unittest tests.test_design_learning_instagram_feed_scan_importer -v` both pass
(**11/11 tests OK**) in the main checkout.

## Guardrails respected

- No browser automation was used — this recovery only read/merged existing JSON files.
- No git operations were performed (no commit, no push, no branch change).
- No shared docs (`PROJECT_SNAPSHOT.md`, `CHANGELOG.md`, `MODULE_STATUS.md`, etc.) were touched.
- `WorkflowEngine`, `card_news`, `publishing`, and compliance modules were not modified.
- Every imported candidate is `status: "candidate"` only — nothing was promoted, verified, or
  marked as proven-performing.

## Verified file existence (main checkout)

- `storage/design_learning/instagram_feed_native_design_scan_merged_v1.json` — exists
- `storage/design_learning/instagram_feed_native_design_scan_merged_v1_flat.json` — exists
- `storage/design_learning/instagram_feed_native_design_scan_merged_v1_imported.json` — exists
- `modules/design_learning/layout_candidate_map.py` — exists
- `modules/design_learning/instagram_feed_scan_importer.py` — exists
- `tests/test_design_learning_instagram_feed_scan_importer.py` — exists
- `external_workclaude/instagram_feed_native_design_scan_v1/RECOVERY_MERGE_REPORT.md` — this file
