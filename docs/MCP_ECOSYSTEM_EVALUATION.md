# MCP Ecosystem Evaluation for AI-Content-OS

Status: **RESEARCH ONLY. No MCP was installed, configured, or connected as a result of this
document.** Findings below combine (a) live web research performed during this task (July 2026,
sources cited per section) and (b) direct observation of which MCP tools are *already* available in
this Claude Code session's tool list (noted explicitly — this changes the "설치 안정성"/"연동 난이도"
answer to "already zero-effort" for those specific servers).

Every recommendation respects this project's existing, repeatedly-stated policy: no real SNS
login/posting, no browser automation for live publishing, no credential storage without an explicit
CTO gate (see `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`). MCPs that could enable those prohibited
actions are still evaluated (the task asked for that), but their "추천 여부" explicitly separates
*development/QA use* (fine) from *production auto-publish use* (against current project policy,
flagged accordingly).

Evaluation criteria per server: **1) 유지보수 여부, 2) 설치 안정성, 3) AI-Content-OS 적용 가능성,
4) Claude Code 연동 난이도, 5) 예상 개발 시간, 6) ROI, 7) 추천 여부.**

---

## 1. Playwright MCP

- **유지보수**: Official Microsoft project (`microsoft/playwright-mcp`), Active tier, 28,500+ GitHub
  stars, last updated 2026-06-30 — actively maintained.
- **설치 안정성**: High — official npm package + Docker image, works with any MCP client.
- **AI-Content-OS 적용 가능성**: High for **QA/verification**, not for publishing: could drive a
  headless browser to visually inspect a rendered CardNews gallery page (if `site/` is ever approved
  as a real gallery), or to verify a WordPress/blog draft renders correctly before a human publishes
  it manually. Must **not** be used to auto-post to Instagram/Naver/Coupang — that contradicts this
  project's explicit no-browser-automation-for-publishing stance.
- **Claude Code 연동 난이도**: **Already connected in this session** (`mcp__playwright__*` tools are
  in the available deferred-tool list) — zero additional setup.
- **예상 개발 시간**: ~0 (already available); a first concrete QA script (e.g. "open the rendered
  CardNews PNGs in a browser gallery and screenshot each") would be a few hours.
- **ROI**: Medium — useful for a future gallery QA step, not urgent today since CardNews output is
  already manually inspected.
- **추천 여부**: **추천 (QA 용도로 한정)** — do not wire into any publish path.

## 2. Browser MCP (`claude-in-chrome` / general "Browser MCP" family)
- **유지보수**: The `claude-in-chrome` extension is Anthropic's own, actively maintained integration.
  Separately, community "Browser MCP" servers (browser-use, BrowserMCP.io) exist and are actively
  developed as of 2026.
- **설치 안정성**: High for `claude-in-chrome` (already installed as a Chrome extension in this
  environment per the system's own tool list).
- **AI-Content-OS 적용 가능성**: Same posture as Playwright MCP — QA/inspection only. Also useful
  for **manual research assistance** (e.g. an operator manually reviewing a competitor Instagram
  account through the browser, with Claude only reading/summarizing what's on screen, never
  auto-posting) — this matches Competitor Engine's existing "offline, human-provided benchmark
  documents only" posture; a live browser session could speed up the *human's own* research pass
  without becoming an automated crawler.
- **Claude Code 연동 난이도**: **Already connected in this session** (`mcp__claude-in-chrome__*`).
- **예상 개발 시간**: ~0 setup; any concrete workflow (e.g. "assist a human reviewing 10 competitor
  accounts") is a documentation/process task, not code.
- **ROI**: Medium — genuinely useful for human-in-the-loop research, must stay clearly separated from
  any auto-publish temptation.
- **추천 여부**: **추천 (사람의 리서치 보조 용도로 한정)**.

## 3. GitHub MCP
- **유지보수**: Official (`github/github-mcp-server`), 28,440 stars, last updated 2026-06-30,
  aligned with the 2026-01-26 stable MCP spec — actively maintained, remote-hosted option available.
- **설치 안정성**: High — GitHub-hosted remote server is the easiest path; a local Docker/binary
  variant exists if the client doesn't support remote MCP.
- **AI-Content-OS 적용 가능성**: Medium — this project's own workflow already treats Git operations as
  CTO/Codex-owned and explicitly prohibits Claude from doing `git add`/`commit`/`push` without
  explicit assignment (per this project's own repeated instructions in recent tasks). A GitHub MCP
  would mostly be useful for **read-only** work: querying issues/PRs, checking CI status, browsing
  code across repos — genuinely useful for a CTO-level orchestration/reporting role, not for Claude's
  current implementation-lane role in this project.
- **Claude Code 연동 난이도**: Not currently connected in this session; would need explicit
  installation + a GitHub PAT/OAuth setup (a credential-issuance step requiring its own approval, per
  this project's credential-handling policy).
- **예상 개발 시간**: 1-2 hours to connect (mostly credential setup), assuming approval.
- **ROI**: Low-Medium for Claude's current role in this project (git operations are explicitly
  someone else's job here); higher for a future CTO/Work orchestration layer that needs to read
  cross-repo state.
- **추천 여부**: **보류 (읽기 전용 용도로 필요해지면 재검토)** — not urgent given current
  git-ownership policy.

## 4. Google Drive MCP
- **유지보수**: Anthropic's own connector, actively maintained.
- **설치 안정성**: High — **already connected in this session** (`mcp__claude_ai_Google_Drive__*`).
- **AI-Content-OS 적용 가능성**: Medium — could serve as a lightweight "operator inbox" for
  brand assets, campaign briefs (feeding `modules/compliance`'s `CampaignRequirement` input),
  reference photos (feeding a future Photo-to-Evidence workflow per
  `docs/EXTERNAL_ENGINE_PORTFOLIO_STRATEGY.md`), read-only.
- **Claude Code 연동 난이도**: Already connected, zero setup.
- **예상 개발 시간**: A few hours to build one concrete import path (e.g. "read a campaign brief doc
  from Drive and normalize it into `CampaignRequirement` shape") if ever prioritized.
- **ROI**: Medium — genuinely lowers friction for non-technical operators to hand off input files,
  but not urgent until a real Compliance/Affiliate operator workflow needs it.
- **추천 여부**: **추천 (필요 시 즉시 활용 가능, 이미 연결됨)**.

## 5. Notion MCP
- **유지보수**: Anthropic's own connector, actively maintained.
- **설치 안정성**: High — **already connected in this session** (`mcp__claude_ai_Notion__*`).
- **AI-Content-OS 적용 가능성**: Medium — a natural fit for the project's own documentation-first
  culture (`docs/`, `DECISIONS.md`, Sprint tracking) if the team ever wants a non-Git-native view for
  non-technical stakeholders; also plausible as a lightweight campaign-brief/compliance-checklist
  intake surface, same idea as Google Drive above but structured (databases/properties) rather than
  freeform documents.
- **Claude Code 연동 난이도**: Already connected, zero setup.
- **예상 개발 시간**: Low if used read-only for status reporting; medium if building a two-way
  sync with `docs/`/`DECISIONS.md` (not recommended — this project's docs are Git-source-of-truth by
  design, per `PROJECT_OPERATING_SYSTEM.md`; a Notion mirror should stay read/write in one direction
  only, Git → Notion, never the reverse, to avoid two conflicting sources of truth).
- **ROI**: Low-Medium for now — the project's Markdown-in-Git documentation culture already works;
  Notion would mainly help non-technical stakeholders, which isn't a stated current need.
- **추천 여부**: **보류** — genuinely available and easy, but no concrete current need identified.

## 6. Figma MCP
- **유지보수**: Official, actively maintained.
- **설치 안정성**: High — **already connected in this session** (`mcp__claude_ai_Figma__*`).
- **AI-Content-OS 적용 가능성**: Medium-High for a **design-system/template layer for CardNews**:
  today, CardNews layout templates are defined in `templates/card_news_layout_rules.json` and
  rendered directly via Pillow — a Figma-side template library could let a human designer iterate on
  the *visual* layout language (typography, spacing, palette) in Figma, then this MCP could pull
  design tokens (`get_variable_defs`) to keep `render_constants.py`/`typography_rules.py` in sync with
  an actual designed system rather than hand-tuned constants. This is a genuinely good fit given
  CardNews's own Phase M8 already introduced a `render_constants.py` single-source-of-truth file — a
  Figma token pull would extend that discipline upstream into design.
- **Claude Code 연동 난이도**: Already connected, zero setup for read (`get_design_context`,
  `get_variable_defs`); write-back (`use_figma`) would need a concrete design file to target.
- **예상 개발 시간**: A few hours for a one-way "pull design tokens into
  `render_constants.py`-shaped JSON" script; more for genuine two-way design-to-code workflow.
- **ROI**: Medium — nice-to-have for design consistency, not solving an urgent current pain point
  (the current hand-tuned constants already pass QA per `MODULE_STATUS.md`'s Phase M8 entry).
- **추천 여부**: **추천 (디자인 시스템 정비 시점에 우선 검토)**.

## 7. Desktop Automation MCP (Windows)
- **유지보수**: Multiple active options as of 2026 — `CursorTouch/Windows-MCP` (2M+ Claude Desktop
  Extension installs, UI-Automation-tree-based, no vision model required), `shanselman/FlaUI-MCP`
  (FlaUI/UI Automation APIs, Playwright-like snapshot pattern), `mario-andreschak/mcp-windows-desktop-automation`
  (AutoIt-based), `windowsmcpserver.dev` (commercial-leaning, UIA-based, deterministic).
- **설치 안정성**: Medium — these are third-party, not Anthropic/Microsoft-official; `Windows-MCP`'s
  install base is the largest signal of real-world stability.
- **AI-Content-OS 적용 가능성**: **Explicitly against current project policy for any production use**
  — this project's `PROJECT_OPERATING_SYSTEM.md`/`AGENTS.md` prohibit real SNS login/posting and any
  form of stealth/coordinate-based automation (see `docs/EXTERNAL_ENGINE_PORTFOLIO_STRATEGY.md`'s own
  explicit rejection of "Naver BC automation"'s stealth/session-persistence approach as a direct
  precedent). A desktop automation MCP is exactly the shape of tool that pattern warns against for
  publishing. The only defensible use is a **local developer convenience** (e.g. driving a local
  Windows font-preview tool while debugging CardNews rendering) — narrow and optional.
- **Claude Code 연동 난이도**: Not connected; would require local install + explicit user consent per
  session (desktop automation tools generally require this).
- **예상 개발 시간**: 1-3 hours to install/verify, if ever approved for the narrow dev-tool use case.
- **ROI**: Low for this project given the policy conflict with its primary imaginable use case.
- **추천 여부**: **비추천 (게시/자동화 목적 절대 금지, 개발 편의 목적조차 우선순위 낮음)**.

## 8. Excel / Spreadsheet MCP
- **유지보수**: Multiple active options — `haris-musa/excel-mcp-server` (cross-platform, stdio/SSE/
  streamable-HTTP transports, formulas/charts/pivot tables), `negokaz/excel-mcp-server` (Windows-only
  live-editing + screen capture), `sbroenne/mcp-server-excel` (Windows COM-API-based, 23 tools/214
  operations, VBA/Power Query/DAX support).
- **설치 안정성**: High — these are pure local file-manipulation tools (no live Excel process
  required for the cross-platform ones), low operational risk.
- **AI-Content-OS 적용 가능성**: Medium — this project's data is JSON-native end-to-end (`storage/`,
  `config/`), so there's no existing Excel dependency to bridge. The plausible use is **operator-facing
  export/reporting**: e.g. exporting `storage/trends/collector_statistics.json` or
  `storage/performance_score/` history to a `.xlsx` for a non-technical stakeholder review, or
  accepting an operator-supplied `.xlsx` product/campaign list as Commerce/Compliance/Affiliate input
  instead of hand-written JSON.
- **Claude Code 연동 난이도**: Not connected; a local npm/Python server install, low complexity for
  the cross-platform variants.
- **예상 개발 시간**: A few hours for one concrete export script once a specific report is prioritized.
- **ROI**: Low-Medium — genuinely useful for non-technical stakeholder reporting, not blocking
  anything today.
- **추천 여부**: **보류 (리포팅 필요 시점에 재검토)**.

## 9. SmartStore 자동화에 활용 가능한 MCP
- **유지보수/현황**: No official Naver SmartStore *seller-operation* MCP exists. What does exist:
  general "Naver MCP" servers wrapping Naver's public OpenAPI services (blog/cafe/search), a
  `naver-shopping-insight-mcp` (shopping *trend* data, not seller listing management), and a
  community Naver Search-Ads keyword-tool MCP (`retn.kr`'s open-sourced 네이버 검색광고 MCP). None of
  these expose SmartStore's actual Commerce API (product registration/order/inventory) — that
  matches this project's own `docs/RESEARCH/AFFILIATE/AFFILIATE_NETWORK_EVIDENCE_MATRIX.md` finding
  that Naver's Commerce API auth mechanism and much of its policy detail remain `UNKNOWN`/unconfirmed
  even from direct research.
- **AI-Content-OS 적용 가능성**: Low today, for the right reason — Commerce Phase 2 (real SmartStore
  connection) is explicitly CTO-gated and unapproved (`COMMERCE_PHASE_1_CONTRACT.md` §9). No MCP
  changes that gate; if Phase 2 is ever approved, the actual Commerce API adapter would still need to
  be built against Naver's official Commerce API Center docs directly (per the evidence matrix), not
  through a generic third-party MCP wrapping unrelated OpenAPI services.
- **Claude Code 연동 난이도**: N/A — nothing exists to connect for the actual gated need.
- **예상 개발 시간**: N/A.
- **ROI**: N/A until the Commerce Phase 2 gate opens.
- **추천 여부**: **비추천 (해당 없음 — 필요한 MCP 자체가 존재하지 않으며, 존재해도 현재 정책상 미승인 상태)**.

## 10. Coupang 자동화에 활용 가능한 MCP
- **유지보수/현황**: No Coupang-specific MCP found in this research pass. Coupang's own official Open
  API (confirmed HMAC-auth, well-documented per the existing evidence matrix in this repo) has no
  known MCP wrapper as of this research; a future custom adapter would call Coupang's official REST
  API directly, same reasoning as SmartStore above.
- **AI-Content-OS 적용 가능성**: Same as SmartStore — gated behind an unopened Commerce/Affiliate
  Phase 2 approval; no MCP changes that.
- **Claude Code 연동 난이도**: N/A.
- **예상 개발 시간**: N/A.
- **ROI**: N/A until gated.
- **추천 여부**: **비추천 (해당 없음, 현재 정책상 미승인 상태)**.

## 11. Instagram 콘텐츠 제작에 활용 가능한 MCP
- **유지보수/현황**: Meta shipped an **official Facebook/Instagram Ads MCP on 2026-04-29** (ads
  management, not organic content posting). Several third-party "Instagram content" MCPs exist for
  **caption/hashtag/carousel drafting** (e.g. the Mirra MCP — carousel + Reels script + caption/
  hashtag drafting), but **actual auto-posting to Instagram via MCP is confirmed not possible** in
  current research due to Meta's own API restrictions on non-approved automation — third-party
  "posting" claims generally resolve to exporting a draft for a human or a separate scheduling tool,
  not a direct API post.
- **AI-Content-OS 적용 가능성**: **Low-to-none for anything beyond what this project already does
  better itself.** `modules/content/`, `modules/card_news/`, and `modules/publishing/` already
  generate evidence-gated captions/hashtags/four-slide copy with truth-gating, brand-rule evaluation,
  and a manual-upload checklist — a generic third-party Instagram-content MCP would offer *less*
  factual rigor (no truth/evidence gates, no rights/disclosure checks) than this project's own
  pipeline, and would reintroduce exactly the "false reviews / unverifiable claims" risk this
  project's Compliance/Commerce modules were built specifically to prevent. Meta's official Ads MCP is
  irrelevant here (this project doesn't run paid ads).
- **Claude Code 연동 난이도**: Not connected; would require Instagram Business account + Meta app
  review for any real API access, which is exactly the credential/policy gate this project already
  keeps closed.
- **예상 개발 시간**: N/A — not recommended to pursue.
- **ROI**: Low/negative — would duplicate and under-deliver relative to existing in-repo capability.
- **추천 여부**: **비추천** — this project's own Content/CardNews/Publishing pipeline is already a
  stronger, more truth-gated substitute for what these MCPs offer; adopting one would be a step
  backward, not a productivity gain.

## 12. OCR / PDF / 이미지 분석 MCP
- **유지보수/현황**: Active options as of 2026: `sandraschi/ocr-mcp` (13 backends incl. DeepSeek-OCR,
  Florence-2, PP-OCRv5), `lemopian/mistral-ocr-mcp` (Mistral's hosted OCR API), `jztan/pdf-mcp`
  (large-PDF semantic/keyword search, table/image extraction, explicitly handles multi-column and
  **Japanese** layouts — worth checking Korean-layout quality directly before adopting), generic
  `mcp_pdf_reader`.
- **AI-Content-OS 적용 가능성**: **Medium, and directly useful** — this project's Research/Content
  pipeline today only ingests already-machine-readable text/JSON sources; it has no way to pull facts
  out of a PDF spec sheet, a scanned product manual, or a screenshot-only source document. An OCR/PDF
  MCP would let a human feed a PDF/scanned source into Commerce's or Compliance's evidence pipeline
  (still subject to the same truth/source/freshness gates — the MCP only extracts text, it does not
  bypass any existing verification gate). This is one of the few MCPs in this evaluation with a
  concrete, currently-unmet need behind it (Commerce/Compliance's own docs already flag "no image OCR
  implemented" as an explicit current limitation).
- **Claude Code 연동 난이도**: Not connected; local Python MCP server install, low-medium complexity;
  cloud-API-backed variants (Mistral OCR) need their own API key + cost.
- **예상 개발 시간**: A few hours to connect + a half-day to build one concrete "PDF spec sheet →
  structured `ProductSnapshot`/`EvidenceReference` fields, human-reviewed" intake flow.
- **ROI**: **Medium-High** — directly unblocks a documented current gap (no OCR path) for Commerce/
  Compliance/the proposed Product Intelligence Engine (Section 1 of the New Engine proposals doc),
  without requiring any new external publishing/automation risk.
- **추천 여부**: **추천 (Commerce/Compliance 근거 수집 보조용, 항상 사람이 최종 검수)**.

## 13. Windows 로컬 자동화 MCP
- Same servers and same conclusion as Section 7 (Desktop Automation MCP) — evaluated once there to
  avoid duplication; see that section for the full 7-criteria breakdown.

---

## Summary table

| MCP | 유지보수 | 설치 안정성 | 적용 가능성 | 연동 난이도 | 개발 시간 | ROI | 추천 |
|---|---|---|---|---|---|---|---|
| Playwright | 매우 활발 (공식) | 높음 | 중 (QA만) | **이미 연결됨** | ~0 | 중 | 추천(QA 한정) |
| Browser (claude-in-chrome) | 활발 | 높음 | 중 (리서치 보조) | **이미 연결됨** | ~0 | 중 | 추천(리서치 한정) |
| GitHub | 매우 활발 (공식) | 높음 | 낮음-중 | 미연결 | 1-2h | 낮음-중 | 보류 |
| Google Drive | 활발 | 높음 | 중 | **이미 연결됨** | 수 시간 | 중 | 추천 |
| Notion | 활발 | 높음 | 중 | **이미 연결됨** | 수 시간 | 낮음-중 | 보류 |
| Figma | 활발 | 높음 | 중-높음 | **이미 연결됨** | 수 시간 | 중 | 추천(디자인 정비 시) |
| Desktop Automation (Windows) | 활발(제3자) | 중 | **정책 위반** | 미연결 | 1-3h | 낮음 | 비추천 |
| Excel/Spreadsheet | 활발(제3자) | 높음 | 낮음-중 | 미연결 | 수 시간 | 낮음-중 | 보류 |
| SmartStore 자동화 | 해당 없음 | - | 낮음(게이트 미승인) | - | - | - | 비추천 |
| Coupang 자동화 | 해당 없음 | - | 낮음(게이트 미승인) | - | - | - | 비추천 |
| Instagram 콘텐츠 | 활발(제3자) | 중 | **낮음(기존 파이프라인이 더 우수)** | 미연결 | - | 낮음/음수 | 비추천 |
| OCR/PDF | 활발(제3자) | 중-높음 | **중-높음(실제 미해결 gap)** | 미연결 | 반나절 | 중-높음 | 추천 |
| Windows 로컬 자동화 | (Desktop Automation과 동일) | | | | | | 비추천 |

Sources consulted (July 2026 web research):
- [github/github-mcp-server](https://github.com/github/github-mcp-server)
- [haris-musa/excel-mcp-server](https://github.com/haris-musa/excel-mcp-server), [negokaz/excel-mcp-server](https://github.com/negokaz/excel-mcp-server), [sbroenne/mcp-server-excel](https://github.com/sbroenne/mcp-server-excel)
- [CursorTouch/Windows-MCP](https://github.com/CursorTouch/Windows-MCP), [shanselman/FlaUI-MCP](https://github.com/shanselman/FlaUI-MCP), [mario-andreschak/mcp-windows-desktop-automation](https://github.com/mario-andreschak/mcp-windows-desktop-automation)
- [sandraschi/ocr-mcp](https://github.com/sandraschi/ocr-mcp), [lemopian/mistral-ocr-mcp](https://github.com/lemopian/mistral-ocr-mcp), [jztan/pdf-mcp](https://github.com/jztan/pdf-mcp)
- [Naver MCP servers overview — FlowHunt](https://www.flowhunt.io/mcp-servers/naver/), [tenacl/naver-shopping-insight-mcp](https://github.com/tenacl/naver-shopping-insight-mcp), [네이버 검색광고 MCP — retn.kr](https://retn.kr/blog/naver-searchad-mcp-seo-automation/)
- [Mirra Instagram MCP guide](https://www.mirra.my/en/blog/mcp-instagram-content-automation-guide-2026), [jlbadano/ig-mcp](https://github.com/jlbadano/ig-mcp)
- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)
