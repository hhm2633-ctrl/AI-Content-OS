---
name: ai-content-os-shorts
description: AI-Content-OS의 Shorts/Reels 확장, 스크립트·장면·자막·음성·영상 렌더링·전사·번역·게시 흐름을 설계하거나 검토할 때 사용한다. 현재 구현 전 Roadmap 게이트와 외부 API 선행조건을 강제한다.
---

# Shorts

## Current State

Treat Shorts as Roadmap planning unless the user explicitly authorizes a Sprint. Read `ROADMAP.md`, `docs/RESEARCH/AlphaCut.md`, and existing content/card-news contracts before proposing implementation.

## Planning Workflow

1. Reuse selected topic, research evidence, content hooks, brand DNA, and publishing metadata.
2. Define an additive pipeline: script -> scene plan -> assets -> voice/captions -> render -> QA -> publish preparation.
3. Identify external dependencies separately: transcription, TTS, video rendering, music rights, platform upload.
4. Prefer proven engines or installed tools such as Descript for editing workflows; do not hand-roll media engines without need.
5. Make every external failure a fallback or manual checklist, not a core workflow failure.

## Gates

- Do not wire Shorts into `WorkflowEngine` during planning.
- Do not claim transcript, view, retention, or engagement data without a real source.
- Do not add API keys or account automation without explicit approval.
- Keep card-news production operational while Shorts remains incomplete.

## Deliverable

Produce a scoped Sprint proposal with inputs, outputs, files, dependencies, fallback behavior, tests, and ROI. Implementation starts only after approval.
