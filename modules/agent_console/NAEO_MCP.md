# NAEO Blog MCP

- Endpoint: `https://www.naeo.kr/api/mcp`
- Official setup: `https://www.naeo.kr/mcp`
- Purpose: future Naver Blog keyword recommendations, AEO writing guidance,
  account tone reference, and owner-approved draft handoff.
- Authentication: interactive NAEO OAuth; no project API key is stored.
- Current state: registered as a deferred capability, not connected.
- Read operations may be enabled after the OAuth tool list is inspected.
- Draft storage, image upload, extension handoff, and any publishing-related
  operation require explicit owner approval for that action.
- This tool is not a CardNews trend, source-media, or video discovery provider.
- NAEO states that saved drafts can be stored on its service for up to 30 days.

Do not mark `loader_registered` true until a current authenticated MCP
`tools/list` succeeds and the returned tool schemas have been reviewed.
