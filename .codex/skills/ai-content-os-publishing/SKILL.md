---
name: ai-content-os-publishing
description: AI-Content-OS의 PublishingModule, caption, hashtag, publish queue, schedule, manual upload checklist, 플랫폼별 발행 준비 계약을 분석·수정·검수할 때 사용한다. 실제 플랫폼 게시 자동화는 명시적 승인과 API 준비 상태를 먼저 확인한다.
---

# Publishing

## Context

Inspect `modules/publishing/publishing_module.py`, `config/publishing.json`, card-news output, and current publish result/queue. Treat runtime files as outputs, not editable source.

## Workflow

1. Preserve the input contract from `card_news_result`.
2. Generate platform-ready caption, normalized hashtags, card paths, schedule, account, and next action.
3. Surface manual image or compliance requirements in operations metadata, not public caption text.
4. Keep `upload_mode: manual` unless real API authorization is explicitly approved.
5. On missing config or external access, use fallback configuration and record the reason.

## Protected Contracts

- Do not publish automatically from a planning request.
- Do not expose tokens, account identifiers, or internal diagnostics in public copy.
- Do not mark content as published when it is only prepared.
- Keep `publishing_ready` compatible with downstream intelligence modules.

## Verification

Check caption and hashtag files, publish queue schema, focused publishing tests, compile, and full workflow. Confirm `09_publishing_result.json`, `publishing_ready`, and `workflow_completed`.
