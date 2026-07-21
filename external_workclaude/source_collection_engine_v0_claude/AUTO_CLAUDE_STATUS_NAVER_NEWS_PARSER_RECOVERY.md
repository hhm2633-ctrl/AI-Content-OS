# AUTO CLAUDE STATUS — Naver News Parser Recovery

- **Status**: `IMPLEMENTATION_COMPLETE_AWAITING_JOINT_TEST`
- **Verification**: `PENDING`
- **Decision**: `GO/NO-GO` — awaiting joint test result (Claude recommends GO for joint testing)
- **Date**: 2026-07-15
- **Work order**: `external_workclaude/source_collection_engine_v0_claude/CLAUDE_NAVER_NEWS_PARSER_RECOVERY_WORK_ORDER.md`
- **Working location**: git worktree `.claude/worktrees/naver-news-parser-recovery` (branch `worktree-naver-news-parser-recovery`, uncommitted — no Git operations performed per work order)

## Changed files (owned)

1. `modules/trend_collector/naver_news_collector.py` — parser hardening, full file rewrite on top of the current uncommitted API Hub version from the main checkout (the worktree base lacked the API Hub layer, so the newer main-checkout file was used as the true base and all API Hub behavior preserved verbatim).
2. `tests/test_naver_news_collector.py` — new offline fixture-driven test suite (15 tests, `unittest`, zero network/browser usage; all payloads are inline fixtures served through a `_fetch_url` override and a stub API Hub client).
3. `external_workclaude/source_collection_engine_v0_claude/AUTO_CLAUDE_STATUS_NAVER_NEWS_PARSER_RECOVERY.md` — this handoff.

### Non-owned file note (verbatim copy only, no modification)

- `modules/trend_collector/naver_api_hub_client.py` was copied **byte-identical** from the main checkout into the worktree, because it is untracked in git and therefore absent from the worktree while the owned collector imports it. It was **not** edited. If integration applies the owned files onto the main checkout, this copy can be ignored.

## What changed in the collector

- **RSS namespace/case tolerance**: item and field lookup now matches XML *local names* case-insensitively (`{ns}item`, `nns:item`, `<ITEM>`, `<PubDate>` all parse) instead of exact `find("item")`/`find("title")`. Field text is gathered via `itertext()` so nested/namespaced children still yield visible text.
- **Lenient RSS recovery**: when `ET.fromstring` raises (stray entities, unbound prefixes) but `<item>` blocks are intact, a bounded regex recovery extracts visible title/link/summary/pubDate (CDATA unwrapped). If recovery yields nothing, the original `ParseError` is preserved.
- **RSS parse failure no longer aborts the query**: `_collect_by_query` now falls through to the HTML search path on `ParseError` (including the RSS endpoint serving an HTML page, detected via `looks_like_html`) and re-raises the original `ParseError` only if HTML also yields nothing — so the `parse_failed` reason code is preserved while recovery improves. Network errors on the RSS fetch propagate immediately, exactly as before.
- **HTML extraction hardening**: search-result anchors are parsed into attribute dictionaries (order-independent, double- or single-quoted, extra attributes tolerated). Supports the legacy `news_tit` layout (title attribute or visible inner text; title-only fallback subsumed) and the newer `data-heatmap-target=".tit"/".body"` layout with visible title/link/summary pairing.
- **No fabrication**: publisher remains derived from the link domain only (existing behavior); summary/link/published_at stay `""` when absent; no metrics or popularity fields added.
- **Preserved unchanged**: API Hub -> RSS -> HTML chain order, `last_status` schema including `api_hub` block, all reason codes (`http_403_forbidden`, `connection_refused`, `timeout`, `network_error`, `parse_failed`, `no_results`, `unknown_error`) and their priority order, `_classify_error`, service diagnostic recording, dedupe, trend item schema, `WorkflowEngine` contract.

## Test coverage added (offline fixtures)

- API Hub success short-circuits RSS/HTML; API Hub failure falls back to RSS with `missing_credentials` recorded.
- Plain RSS; default-namespace RSS; prefixed-namespace RSS; case-varied tags; CDATA fields (visible text only).
- Malformed-but-recoverable RSS (stray `&` + unbound prefix) recovered leniently without touching HTML path.
- RSS endpoint returning an HTML document falls through to HTML search successfully.
- HTML with shuffled attribute order and single quotes; heatmap layout with title/link/summary; title-only anchor with no fabricated fields.
- Reason codes: `parse_failed` (unparsable RSS + empty HTML, both paths attempted), `no_results` (valid-empty RSS + empty HTML), `timeout` propagation, `ParseError` classification helper.

## Unexecuted checks (per work order prohibitions)

- `py -m unittest tests.test_naver_news_collector` — NOT run.
- `py -m compileall src modules scripts` — NOT run.
- Full workflow `py -m src.main` / `workflow_completed` check — NOT run.
- No live network, browser, login, or credential inspection performed.
- No Git operations performed (files are uncommitted in the worktree listed above).

## Joint test suggestion (for the integration lane)

```powershell
py -m unittest tests.test_naver_news_collector -v
py -m compileall src modules scripts
```

