# Work/Codex Capability Audit

Date: 2026-07-11

## Decision

Use ChatGPT Work as the primary CTO and orchestration surface, with Codex execution in the same project workspace for repository implementation, tests, documentation, and Git. Keep Claude optional for explicitly assigned specialist work or independent review. Do not require Claude to call Codex MCP.

## Available Capabilities

| Capability | Current use |
|---|---|
| Workspace files and side work | Open, inspect, edit, and compare project files in the app |
| Codex execution | Repository changes, compile, tests, full workflow, documentation, Git |
| Browser and computer control | Research, inspect UI, verify local/web workflows when needed |
| GitHub | Repository metadata, issues/PRs, CI, review, and authenticated repository actions |
| Google Drive | Search/read/write Drive-family files and manage project folders |
| Documents/PDF/Sheets/Slides | Create, edit, analyze, render, and visually verify artifacts |
| Image generation | Generate or edit bitmap assets when the content workflow needs them |
| Data Analytics | Data quality, KPI, diagnostics, reports, dashboards, and visualization |
| Descript | Optional media import/edit/publish support for a future approved Shorts workflow |

## Plugin Decision

No additional general AI plugin is required now. The current capabilities already cover the active CardNews-first workflow. Extra marketplace AI writers, summarizers, image generators, detectors, and humanizers duplicate project behavior and create unnecessary data-access risk.

Conditional additions:

- Slack/Teams: install only when there is a real operations notification channel.
- Gmail/Outlook: install only when approval or publishing email becomes an owned workflow.
- Figma: install only when design handoff becomes a recurring production step.
- Instagram Graph API: build or connect only after explicit OAuth, account, metric, and publishing approval.
- Coupang product/affiliate data: build or connect only after approved data source, account ownership, disclosure, and freshness policy.
- YouTube/Shorts publishing or transcription: connect only after the target platform, credentials, cost, and fallback path are approved.

## Skill Decision

The former `openai/skills` catalog is deprecated in favor of current plugin examples and the official skill format. Project-specific behavior belongs in versioned `.codex/skills/` folders so Work and Codex use the same repository truth.

Created project skills:

- `ai-content-os-trend-collector`
- `ai-content-os-research-intelligence`
- `ai-content-os-card-news`
- `ai-content-os-shorts`
- `ai-content-os-publishing`
- `ai-content-os-instagram`
- `ai-content-os-coupang`
- `ai-content-os-qa`
- `ai-content-os-cto-review`
- `ai-content-os-sprint-manager`

Official references:

- https://github.com/openai/plugins
- https://developers.openai.com/codex/skills/
- https://developers.openai.com/codex/plugins/build/

## Security and Quality Rules

- Review third-party skill or plugin code, requested permissions, maintenance, and license before installation.
- Prefer primary vendor documentation and existing project modules.
- Never store credentials in source or print `.env`.
- Treat external service failure as fallback/status data and preserve `workflow_completed`.
- Do not claim unavailable Instagram, commerce, or platform metrics as measured data.
