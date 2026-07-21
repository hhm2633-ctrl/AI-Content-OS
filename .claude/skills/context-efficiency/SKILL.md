---
name: context-efficiency
description: Retrieve only relevant evidence from long project transcripts, logs, JSON outputs, generated status documents, and historical files. Use for session recovery, history or status questions, large-file investigation, or any task where loading a whole source would waste context or hide the current answer.
---

# Context Efficiency

Use query-first, range-bounded retrieval. Preserve source order and distinguish observed text from
inference.

## Workflow

1. State the exact question, target facts, likely file types, and whether current state or historical
   state is required.
2. Locate candidates with `rg --files` and search them with `rg -n` using exact terms, identifiers,
   dates, filenames, status labels, and one or two synonyms.
3. Inspect only bounded ranges around matches. Start with roughly 40 lines before and 80 lines after
   a hit, or at most 120 contiguous lines. Expand only the adjacent range that remains necessary.
4. Follow direct references one level at a time. Do not recursively load every linked document or
   every skill directory.
5. Stop when the required fact is supported. Record the file and line, and label any unresolved
   point instead of loading unrelated history.

PowerShell examples:

```powershell
rg -n "candidate_id|BLOCK|handoff" path/to/long_file.md
Get-Content path/to/long_file.md | Select-Object -Skip 240 -First 120
rg -n '"status"|"reason_code"|"fallback_used"' path/to/result.json
```

## Source-specific rules

- **Recovered transcripts:** treat retained text as the conversation record, preserve original
  order, and search by user phrase, task name, date, model name, or file path. Do not infer omitted
  images, browser state, tool output, internal reasoning, or heartbeat payloads.
- **Logs:** search error type, stage, timestamp, candidate/source ID, and the final completion marker.
  Read the first causal error and terminal status rather than the full log.
- **JSON:** retrieve the relevant object or keys. Keep `status`, provenance, confidence,
  `fallback_used`, and reason fields together so evidence meaning is not stripped.
- **Status/history docs:** prefer the newest applicable entry, but confirm mutable claims against
  repository code or current outputs when the task depends on present behavior.

## Guardrails

- For a long source, do not use `Get-Content -Raw`, print the whole file, or paste it into a prompt.
- Do not replace retrieval with memory. Repository evidence wins.
- Do not treat search silence as proof of absence. Retry with a stable identifier or synonym, then
  report `not found in searched scope` if still unresolved.
- Do not quote large passages. Extract the minimum supporting lines and summarize.
- Do not perform writes, network calls, browser actions, or workflow execution merely to recover
  context.

## Handoff

Report the answer first, then the exact sources and ranges inspected, unresolved gaps, and any
assumption made because the long source intentionally omits non-text state.
