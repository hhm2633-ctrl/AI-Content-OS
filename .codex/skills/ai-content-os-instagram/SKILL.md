---
name: ai-content-os-instagram
description: AI-Content-OS의 Instagram Research, competitor learning, benchmark, internal quality proxy, 실제 Graph API 성과 데이터 경계를 분석·수정·검수할 때 사용한다. 계정 조사, 게시 성과, 댓글, 경쟁계정 자료 요청에 적용한다.
---

# Instagram

## Context

Read only the relevant files in `modules/instagram_research/`, `modules/competitor_learning/`, `modules/competitor_engine/`, `benchmark/`, and the Instagram sections of `ROADMAP.md` and `DECISIONS.md`.

## Data Classification

- Treat existing Instagram Research and benchmark files as competitor/reference data.
- Treat local `quality_score` history as an internal pre-publish proxy, never real engagement.
- Treat likes, saves, shares, reach, CTR, follows, and DMs as measured only when imported from an authorized real source.

## Workflow

1. Identify whether the request concerns research, learning, publishing, or measured performance.
2. Preserve read-only boundaries around collected posts and append-only learning history.
3. Keep account handles masked where public output does not require them; scrub PII from comments.
4. Require explicit approval and OAuth/API readiness before Graph API or login automation.
5. When access is unavailable, produce a manual import checklist and honest fallback metadata.

## Verification

Run focused Instagram intelligence risk tests, compile, and full workflow for code changes. Confirm internal-proxy labels remain present and `workflow_completed` is preserved.
