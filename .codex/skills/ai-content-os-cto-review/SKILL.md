---
name: ai-content-os-cto-review
description: AI-Content-OS의 기능 제안, Sprint, 아키텍처, 외부 서비스, 스킬·플러그인, 대규모 변경을 CTO 관점에서 검토할 때 사용한다. ROI, 근거, 보호 계약, 운영비용, 데이터 정직성, 구현 순서와 승인 게이트를 판정한다.
---

# CTO Review

## Review Order

1. State the user outcome and current project phase.
2. Verify the proposal against repository reality, not memory.
3. Score direct ROI for the active CardNews-first objective.
4. Identify protected-core, data, security, cost, vendor, and rollback risks.
5. Separate implemented capability, available tool capability, planning, and speculation.
6. Choose: proceed now, narrow the scope, place on Roadmap, or reject.
7. Define success metrics and the smallest reversible Sprint.

## Tool and Plugin Review

- Prefer existing repository modules and installed first-party capabilities.
- Search official OpenAI plugin examples and primary vendor documentation before adding dependencies.
- Treat third-party skills and plugins as untrusted until code, permissions, maintenance, and license are reviewed.
- Do not add an integration only because it exists; require a real workflow owner and measurable benefit.

## Output

Lead with the decision, then rationale, risks, dependencies, scope, verification, and next action. Record durable architecture choices in `DECISIONS.md`; update Roadmap status without rewriting history.
