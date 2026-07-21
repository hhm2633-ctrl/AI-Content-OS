# Performance Optimization Candidates

Status: **PROPOSAL ONLY. Nothing in this document has been applied.** Each candidate lists the
concrete evidence found, the expected win, and the risk of applying it, so the CTO can triage
independently per item. None of these were benchmarked (no profiler run) — they are structural
candidates identified by code reading, not measured hotspots. Recommend profiling
(`cProfile`/`time.perf_counter` around a real `py -m src.main` run) before investing implementation
effort, especially for anything marked "unverified impact" below.

---

## 1. JSON input/output

### PC-1: No caching of repeatedly-read config/state files within a single process
Every engine module's `__init__` constructs its own `Storage`/`Interface`/config-loader objects,
each of which re-reads its JSON file from disk independently even when multiple modules read the
*same* underlying file in one `py -m src.main` run. Concretely: `config/brand_profile.json` is read
independently by at least `BrandProfileLoader` (`brand_dna_engine`) and `ResearchInsightGenerator`
(`research`) — two separate `json.load` calls for one file, in the same process, in the same run.
Similarly, every `*Interface` class (`KnowledgeInterface`, `CompetitorLearningInterface`,
`BrandDNAInterface`, `LearningInterface`, `PerformanceScoreInterface`, ...) is independently
constructed by 2-5 different orchestrator modules (`PatternEngineModule` alone constructs 4 of
them), each triggering its own storage read.

**Candidate**: a small `functools.lru_cache`-backed or explicit in-process cache keyed by resolved
file path for read-mostly config/state files (`config/brand_profile.json`,
`storage/knowledge/knowledge_database.json`, `config/*.json` generally). Risk: low for genuinely
static config files; **higher for anything written during the same run** (e.g. if Engine A writes
`storage/knowledge/...json` and Engine B later reads it in the same run expecting the fresh write —
a naive cache would serve stale data). Any implementation must be scoped per-run (cleared at
`WorkflowEngine` start) or explicitly excluded for files any Engine writes mid-run. Unverified impact
size — these are small JSON files today; the win grows if `storage/knowledge/knowledge_database.json`
grows large (see PC-2).

### PC-2: `KnowledgeModule`/`KnowledgeInterface` searches/ranks across the *entire* accumulated database on every run
Per `MODULE_STATUS.md`, Knowledge Engine v1 does "global rank across full DB" and exposes
`search()`. As `storage/knowledge/knowledge_database.json` grows across many production runs, every
future run's full-DB rank/search becomes `O(n)` (or worse) over an ever-growing file loaded entirely
into memory each time, with no apparent indexing or pagination.

**Candidate**: (a) confirm actual current DB size in `storage/knowledge/` (if still small, defer);
(b) if growth is real, consider an in-memory index built once per process (not per call) inside
`KnowledgeModule`'s lifetime, or a lightweight on-disk index (e.g. a sorted-by-score sidecar file) so
"top N" queries don't require a full deserialize-and-rank pass every time. Unverified impact — depends
entirely on real accumulated data volume, which this analysis pass did not measure.

### PC-3: `_load_json`/`_save_json` (see Change Request CR-5) always uses `json.dump(..., indent=2)`
Every write across ~17+ files pretty-prints with `indent=2`. Pretty-printing is meaningfully slower
than compact `json.dump` for larger payloads and produces larger files on disk (more bytes to write
and re-parse next time). This is a deliberate, reasonable trade for human-readability during
development/debugging of a fallback-first system, so this is **not a straightforward win** — flagged
as a candidate only for large, rarely-hand-inspected files (e.g. `storage/knowledge/knowledge_database.json`,
`storage/*/*_history.json` once they're large), not for small human-reviewed outputs like
`storage/workflow_results/*.json`. Needs an explicit CTO call per file class, not a blanket change.

---

## 2. Caching

### PC-4: CardNews font loading re-parses the TTF file on every call, no cache
`modules/card_news/card_news_module.py::_get_font(size, bold)` calls `ImageFont.truetype(font_path,
size)` fresh every invocation — and this is called once per distinct text element per slide (title,
body, CTA, source attribution, etc. — likely 5-10+ calls per slide × 4 slides per card-news run).
`ImageFont.truetype` does real font-file I/O and glyph-metrics parsing each time; the same
`(font_path, size, bold)` combination is requested repeatedly across slides (headline sizes repeat,
body sizes repeat).

**Candidate**: memoize `_get_font` by `(font_path_resolved, size, bold)` — a simple `dict` cache on
`self` (or `functools.lru_cache` on a staticmethod variant) avoids re-opening/re-parsing the same TTF
file 5-10+ times per run for what is typically only 3-5 distinct (size, bold) combinations. Low risk
(Pillow `ImageFont` objects are safe to reuse across draw calls within one process), likely the
highest-confidence "real win" in this document since font parsing is genuinely CPU-bound and the
call pattern (many repeats of a small combination set) is a textbook cache candidate.

### PC-5: No cross-run cache for Competitor Engine's static markdown parsing
`InstagramBenchmarkParser`/`ToolsFunnelParser`/etc. re-read and re-parse `benchmark/*.md` files from
scratch on every `py -m src.main` run, even though these source files change rarely (they're
CTO-curated reference documents, not per-run data). Candidate: a simple mtime-checked cache (skip
re-parsing if the markdown file's mtime hasn't changed since the last parse) — low complexity, but
also low-urgency since markdown parsing of a handful of files is unlikely to be a measured hotspot;
listed for completeness, not high priority.

---

## 3. Memory usage

### PC-6: Full-file reads for potentially-append-only structures
Every `*_history.py::record()` (see Change Request CR-6) loads the **entire** history JSON into
memory, appends one record, truncates to `MAX_RECORDS` (typically 200-500), and rewrites the entire
file. For a bounded 200-500 record cap this is not a real problem today (each file stays small by
construction), but it's worth noting the pattern doesn't scale if `MAX_RECORDS` is ever raised
significantly — flagged as "watch, don't fix" rather than an active candidate.

### PC-7: `ImageGenerationModule` and CardNews hold full generated-image bytes in memory during a run
Not independently verified line-by-line in this pass, but the general shape (`ImageGenerationModule`
writes PNGs, `CardNewsModule` opens them via Pillow to composite) suggests each 1080x1080+ image is
fully decoded into memory per slide. For 4 slides this is unlikely to be a real problem
today; flagged only in case future Sprints increase card count or resolution significantly.
**Unverified impact — no profiling done.**

---

## 4. Repeated/nested loops

### PC-8: Trend source collection runs strictly sequentially
`modules/trend_collector/trend_source_manager.py::collect_from_enabled_sources` (lines ~189-204+)
iterates `enabled_sources` in a single `for` loop, calling `_collect_naver_news`/`_collect_nate_pann`
(and presumably other collectors) one after another. Each collector performs real network I/O
(HTTP requests to news/community sites) with the project's own `RetryPolicy` potentially adding
multi-second backoff delays on failure. Sequential execution means total collection time is the
**sum** of every source's latency (including retry backoff), not the max.

**Candidate**: see PC-9 (parallelization) — this is the concrete site where it would apply first,
since it's the only multi-source sequential-network-call loop found in this pass.

### PC-9: No use of `concurrent.futures`/`asyncio`/threads anywhere in `modules/` (confirmed by grep)
Zero occurrences of `ThreadPoolExecutor`, `asyncio`, or `multiprocessing` in the entire `modules/`
tree. Every network-calling collector, every LLM call, every image-generation call runs strictly
synchronously, one at a time, even where requests are independent (e.g. the 4 image-generation calls
for 4 card-news slides, or the N trend sources in PC-8).

**Candidate**: introduce `concurrent.futures.ThreadPoolExecutor` (I/O-bound work, GIL is not the
bottleneck for network/LLM calls) at exactly two sites: (a) `TrendSourceManager`'s per-source
collection loop (PC-8), and (b) `ImageGenerationModule`'s per-slide image generation calls, if they
are today issued one-by-one (not independently re-verified in this pass — check
`image_generation_module.py::run()`'s loop shape before implementing). **This is the highest-risk
item in this document to implement carelessly**: the project's fallback-first contract requires
every failure to degrade safely and be recorded per-source/per-slide; a naive parallelization must
preserve exactly the same per-item fallback/retry/recording semantics, just run concurrently instead
of sequentially. Needs careful design + tests before implementation, not a drop-in change. Expected
win is real and potentially large (network/LLM latency is almost certainly the dominant wall-clock
cost of a full `py -m src.main` run) but this is squarely a "propose, don't implement without
explicit approval" item per this task's own instructions.

---

## 5. Unnecessary file access

### PC-10: `storage/<engine>` directories are created (`mkdir(parents=True, exist_ok=True)`) on every module construction
Confirmed pattern (`PublishingModule.__init__`, `LLMClient.__init__`, and others) — harmless
individually (`exist_ok=True` makes repeat calls cheap after the first), but it's still a filesystem
stat/syscall on every single module instantiation across a run with 18+ pipeline stages plus
Intelligence Engines. Not a measured hotspot, but a candidate for "construct storage directories once
at `WorkflowEngine` startup" if profiling ever shows this matters. Low priority — flagged for
completeness only.

### PC-11: `ServiceDiagnostic` and similar helpers re-read their own history file just to append one record
`ServiceDiagnostic._record` (and every `*History.record`, per Change Request CR-6) does a full
read-modify-write cycle for a single-record append, every single time `record()` is called — for a
`LLMClient` that logs every single call, this means one full JSON round-trip per LLM invocation just
to append one diagnostic entry (separate from `LLMClient`'s own per-call log file write to
`storage/llm_logs/`, which is a different, already-one-file-per-call pattern and not itself a
duplication concern). For today's call volumes (a handful of LLM calls per run) this is not a real
bottleneck; flagged because it compounds with PC-6 if history files are ever allowed to grow large.

---

## 6. Summary priority ranking (highest confidence / lowest risk first)

| # | Candidate | Confidence this is a real win | Implementation risk |
|---|---|---|---|
| PC-4 | CardNews font-load memoization | High (textbook cache case, confirmed repeat pattern) | Low |
| PC-1 | In-process config/state read cache | Medium (small files today, grows with usage) | Medium (staleness risk within a run) |
| PC-9 | Parallelize independent network/LLM calls | High potential win, but | **High** (must preserve fallback-per-item semantics) |
| PC-8 | Parallelize trend source collection specifically | Same as PC-9, narrower scope | Medium-High |
| PC-2 | Knowledge DB indexing for full-DB rank/search | Unverified (depends on real DB size) | Medium |
| PC-5 | mtime-cache for static benchmark markdown | Low urgency | Low |
| PC-3 | Selective compact JSON encoding for large files | Needs CTO judgment call per file | Low |
| PC-6, PC-7, PC-10, PC-11 | Watch-only, not currently a measured problem | N/A | N/A |

Recommend, if only one item is approved for a future Sprint: **PC-4** (font-load memoization) as the
lowest-risk, highest-confidence win, followed by a real profiling pass (`cProfile` around
`py -m src.main`) before committing to PC-9's parallelization work, since that item's actual wall-clock
win depends entirely on how much of a real run's time is network/LLM-bound vs. CPU-bound — this
document did not measure that split.
