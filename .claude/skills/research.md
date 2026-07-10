---
name: research
description: 외부 자료(PDF/사이트/UI/영상) 처리 규칙. Claude는 원자료를 재분석하지 않고 ChatGPT CTO가 분석해 GitHub에 저장한 Research 문서만 사용한다.
---

# Research Skill

## Purpose

AI-Content-OS는 외부 자료(경쟁 계정 분석, 벤치마크 PDF, UI 캡처, 영상 등)를
프로젝트에 들여올 때 정해진 절차를 따른다. Claude는 이 절차의 마지막 단계만 담당한다.

## 처리 흐름

```text
외부 자료 (PDF / 영상 / UI / 서비스 / 사이트)
        ↓
ChatGPT CTO 분석
        ↓
GitHub Research 문서 저장 (docs/, docs/RESEARCH/ 등)
        ↓
Claude는 Research 문서만 사용
```

## 규칙

- **원자료 재분석 금지**: Claude는 PDF, 스크린샷, 영상 등 원본 외부 자료를 직접 분석해 결론을 내리지 않는다. ChatGPT CTO의 분석 결과가 이미 GitHub 문서로 저장되어 있다고 가정하고, 그 문서를 신뢰할 수 있는 컨텍스트로 사용한다.
- 관련 문서는 주로 `docs/` 및 `docs/RESEARCH/` 아래에 위치한다 (예: `docs/KNOWLEDGE_ENGINE.md`, `docs/RESEARCH/AlphaCut.md`, `docs/RESEARCH/Claude_Instagram_Audit.md`, `docs/RESEARCH/Claude_Codex_Workflow.md`). 정확한 파일명은 매번 `Glob`으로 확인한다 — 목록은 계속 늘어날 수 있다.
- 사용자가 원자료(PDF/링크/스크린샷)를 직접 첨부하며 "이거 분석해줘"라고 요청하는 경우가 아니라면, 원자료를 찾아 열어보지 않는다.
- Research 문서의 결론이 현재 구현과 다르면, 코드를 임의로 그 결론에 맞춰 바꾸지 않는다 — 먼저 사용자에게 반영 여부를 확인한다.
- **구현이 필요한 경우, Research 문서를 기반으로만 구현한다.** 원자료(PDF/영상/스크린샷)를 다시 열어 세부사항을 보충하지 않는다 — Research 문서에 없는 내용은 "문서에 없음"으로 취급하고, 필요하면 문서 보강을 먼저 요청한다.

## 이 규칙의 근거

`DECISIONS.md`의 2026-07-09 "External Research Handling" 결정 참고:

> External materials are analyzed by ChatGPT CTO first. Claude and Codex do not re-analyze raw external materials by default. They use the analyzed GitHub documents as project context.
>
> Reason: 프로젝트 지식을 안정적으로 유지하고, AI 비용 중복을 줄이며, 구현 중 원본 해석이 흔들리는 것을 방지하기 위함.

## 새 Research 문서가 필요한 경우

Claude가 직접 새로운 Research 문서를 작성하지 않는다. 외부 자료 분석 및 문서화는
ChatGPT CTO의 역할이며, Claude는 이미 저장된 문서를 소비하는 역할에 머문다.

---

# AI-Content-OS Research Extension

## Purpose

Research는 자료를 모으는 작업이 아니다.

항상 재사용 가능한 Knowledge를 만든다.

## Workflow

Collect

↓

Analyze

↓

Extract

↓

Knowledge

↓

Pattern

↓

Save

## 반드시 추출

- Hook
- CTA
- Pattern
- Layout
- Brand DNA
- Funnel
- Workflow
- Image Strategy
- Prompt Pattern

## Sources

- News
- Community
- Instagram
- YouTube
- PDF
- Official Docs
- GitHub
- Benchmark Accounts

## Never

원문을 그대로 구현하지 않는다.

패턴만 추출한다.

Knowledge DB에 재사용 가능한 형태로 저장 가능한 구조를 우선 설계한다.
