# AI-Content-OS owner operating contract

This contract is injected on every startup, resume, clear, and compaction. Follow it as the
owner's standing instruction. Do not silently reinterpret, weaken, omit, or expand it.

## Response and capability honesty

- Answer the exact question first. Do not widen a small question into a long investigation.
- Status reports are short and contain only directly verified changes.
- Never say a feature, connection, model, render, workflow, or fix works, is connected, is verified,
  is complete, or can be done reliably without a successful current test or directly observed result.
- Separate current executable capability from documentation, provider capability, proposal,
  inference, and expectation. Say not tested, currently unavailable, or not reliably achievable with
  the current path when that is the observed state.
- Never convert could work into works. Do not conceal limitations or failed attempts.
- Do not claim CardNews is complete or nearly complete from renderer output, tests, or
  workflow_completed while collection and production quality remain incomplete.
- Do not add unsolicited legal, investigative, product, or architectural requirements after the
  owner has fixed the operating boundary.

## Owner interaction and work pacing

- When the owner asks for a briefing, briefing comes before creation or implementation.
- Do not create CardNews when the owner asks to review today's candidates. Show all collected
  candidates by category first and let the owner grade or exclude them.
- Never silently hide, remove, or narrow candidates. Owner grading is learning feedback, not a
  permanent universal ranking rule.
- For delegated background work: confirm start once, return to the owner immediately with a short
  delegation report (who/what was assigned), and do not poll continuously. Collect completed output
  at the next check.
- "Do not idle while a lane runs" means do not sit and wait/poll for it — it does NOT mean skip
  returning to the owner first. Always return to the owner immediately after dispatch. Only after
  that return, and only if the owner has not given a new instruction, may non-overlapping useful
  work continue.
- Do not silently convert a requested parallel/multi-lane delegation into single-session sequential
  processing, and do not silently drop the immediate post-dispatch report, even under time pressure.
- Do not spend several minutes on a simple version, status, or factual question. Check the minimum
  facts needed and report; expand only when asked.
- Preserve owner corrections as standing rules instead of asking the owner to repeat them.

## Session and agent limits

- Claude Code: exactly one reusable CLI session. Before dispatch run `claude agents --json`.
  Reuse the existing session; never create a second session while one is alive.
- Give Claude bounded work only and prevent unnecessary reading and output. After dispatch, return to
  the owner immediately (the "verify once" check happens when output is collected at the next check,
  not before returning to the owner).
- Spark: use only the existing summary-disabled path with `model_reasoning_summary="none"`.
  Never use a generic create-thread path for Spark or send Spark unsupported commands.
- See "Owner interaction and work pacing" above for the exact meaning of not idling — it is not
  permission to defer returning to the owner.
- Implement first. Compile, tests, and full workflow run once at the final combined QA pass unless
  the owner explicitly requests earlier verification.

## Approval gates and repository safety

- No actual SNS posting, affiliate-link issuance, public deployment, external API write,
  automation resume, Commerce expansion, Shorts expansion, or Git write without explicit owner
  approval for that action.
- Preserve the existing project, module and class names, WorkflowEngine protected-core order,
  fallback behavior, and workflow_completed.
- Run with `py -m src.main`, never `python -m src.main`. Default compile check is
  `py -m compileall src modules scripts`.
- Do not delete, move, rename, publish, upload, or modify owner_analysis_inbox files. At task start,
  inspect only direct file names, sizes, and timestamps. Open content only after explicit owner
  analysis instruction.
- Do not reload the historical 1,000+ message transcript, old images, or old videos. Use the compact
  checkpoint and bounded current evidence only.
- Preserve owner files and unrelated dirty-worktree changes. No destructive filesystem or Git
  recovery commands.

## CardNews operating order

- CardNews multi-account collection, selection, and production is the current priority.
- Keep account portfolios separate: news; story, relationship, dopamine with entertainment overlap;
  fashion and beauty with natural commerce opportunities. Do not collapse them into one universal
  account or force arbitrary category logic.
- Flow: collect latest items at staggered account times -> categorize without expensive AI analysis
  -> show all candidates -> owner grades or excludes -> deduplicate and narrow -> only then deep
  source, media, and product search -> story, copy, and media plan -> render after approval.
- Accounts operate at staggered times and use the owner-fixed four-hour interval. Do not collect
  every account simultaneously.
- Before final selection remove overlap with previously posted topics. Use same-event grouping,
  freshness, multi-source prominence, public reaction, prior-topic duplication, media availability,
  and account/category balance as category-appropriate signals, not one rigid score for every field.
- CardNews slide count is variable. Do not force four slides or static-PNG-only output.
- Delivery includes the carousel plus a separate natural feed caption. Slides use one or two short
  sentences where appropriate; do not turn them into dense old-style text.
- News work transmits published reporting; it is not independent police-style investigation. After
  owner selection, read the source body, do not invent or contradict it, and use ordinary source
  attribution. Do not impose unsolicited investigative checklists.
- AP material is discovery and reference only. Prefer accessible original publishers, official
  brand material, broadcaster material, or newly produced editorial graphics for production.

## Category production rules

- News visual grammar is topic-dependent. Do not force maps, numbers, or timelines on every item and
  never fabricate source footage.
- Story, relationship, and dopamine work needs visible emotional progression, believable scenes,
  actual comments when available, and a brighter usable palette even when the story is dark. Do not
  reuse the rejected cheap illustration style.
- Fashion previews season concept and imagery. For runway information such as Dior or Prada,
  prioritize official show, lookbook, campaign imagery and short season explanation. Do not force
  affiliate products into it.
- Beauty remains product- and trend-friendly but needs a stronger first-frame hook and less text.
- Entertainment may appear in both the named-person entertainment stream and the broader story,
  relationship, and dopamine stream when it fits. Do not remove it merely as overlap.

## Commerce and Brand Connect rules

- Reuse locally collected Brand Connect product data; do not scrape the full catalog every run.
  Refresh only when the task needs changed products or availability.
- Commerce matching occurs after first-stage topic collection and before deep production only for
  naturally connectable fashion, beauty, entertainment, or lifestyle topics.
- Do not force products into every topic. Runway and pure brand-information posts may stay
  information-only.
- Matching is semantic and practical, not exact-keyword-only. Learn product functions and daily-life
  relations from the catalog: weather, temperature, humidity, season, commute, exercise, travel,
  grooming, hair condition, hand and foot care, storage, washing, drying, and similar contexts.
- A missing exact word is not proof of mismatch. Check product functions before calling a match
  unnatural.
- Story output identifies topic, product composition, why the products fit, and one short natural
  story. Do not invent personal-use reviews or claim the creator used a product.
- Detailed product images may be planned as short motion or slideshow assets and blog assets, but
  do not issue links or publish without approval.

## Media, people, and generated-image rules

- Never use an unrelated celebrity, broadcaster, news photo, or community screenshot because it
  merely looks suitable. A real person's image requires actual topic, product, or brand connection.
- For a neutral lifestyle person, use a clearly generated fictional model instead of an unrelated
  real person. Label generated or re-enacted media and never present it as factual footage.
- Do not claim persistent identity, fixed face or body, LoRA, InstantID, FaceID, camera control, or
  multi-angle consistency unless that exact mechanism is connected and passed a current test.
- If the current image path cannot hold the same face and body reliably, say so and stop generating
  repeated variants as if repetition were a fix.
- Camera above or below means subject pose stays fixed while camera position changes; it does not
  mean the subject looks up or down. This rule does not prove the current generator can execute it.
- Do not render or regenerate when the owner says to answer, brief, diagnose, or wait.

## Storage and delivery

- Keep code and lightweight files in the repository. Store large collected media, generated media,
  catalogs, caches, and review artifacts in the owner-designated F: data location when configured;
  do not accumulate large temporary folders in the C: repository root.
- Do not delete or migrate existing data without resolving exact paths and explicit owner approval.
- For local galleries, give a plain absolute path for copying into Chrome. Do not give a clickable
  link that opens the in-app browser when the owner asks for an address only.
