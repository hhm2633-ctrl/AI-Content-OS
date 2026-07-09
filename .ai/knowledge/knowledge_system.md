# Knowledge System

AI-Content-OS가 외부 세계의 정보(경쟁 계정, 벤치마크, UI 패턴, 서비스 사례 등)를 프로젝트 자산으로
편입시키는 절차다. 이 절차는 `DECISIONS.md`의 2026-07-09 "External Research Handling" 결정에 근거한다.

## 흐름

```text
외부 자료 (PDF / 영상 / UI / 서비스 / 사이트)
        ↓
ChatGPT CTO 분석
        ↓
GitHub Research 문서 저장 (docs/, docs/RESEARCH/)
        ↓
프로젝트 자산 (PROJECT_MASTER.md/ROADMAP.md/DECISIONS.md가 참조 가능한 형태)
```

## 왜 이렇게 하는가

- 프로젝트 지식을 안정적으로 유지한다 (원자료를 볼 때마다 다른 AI가 다르게 해석하는 것을 방지).
- AI 비용 중복을 줄인다 (같은 PDF를 여러 AI가 각자 다시 분석하지 않는다).
- 구현 중 원본 해석이 흔들리는 것(scope drift)을 방지한다.

## 각 AI의 역할

- **ChatGPT CTO**: 원자료를 1차로 분석하고, 결론을 GitHub 문서(`docs/`, `docs/RESEARCH/`)로 저장한다. 이 프로젝트에서 원자료를 직접 분석하는 것은 사실상 ChatGPT CTO만의 역할이다.
- **Claude**: 원자료를 재분석하지 않는다. Research 문서를 프로젝트 컨텍스트로 사용하고, 구현이 필요하면 **그 문서에 있는 내용만을 기반으로** 구현한다. 문서에 없는 세부사항은 "문서에 없음"으로 취급하고, 필요하면 문서 보강을 먼저 요청한다.
- **Codex**: Claude와 동일하게 원자료를 재분석하지 않는다.

## 현재 알려진 Research 자산

- `docs/KNOWLEDGE_ENGINE.md` — Knowledge Engine 자체의 설계 문서.
- `docs/RESEARCH/AlphaCut.md`, `docs/RESEARCH/Claude_Instagram_Audit.md`, `docs/RESEARCH/Claude_Codex_Workflow.md` — 분석 완료된 개별 리서치 문서.
- `benchmark/*.md` (`AI_CONTENT_STRATEGY.md`, `INSTAGRAM_BENCHMARK.md`, `HOOK_LIBRARY.md`, `CTA_LIBRARY.md`, `CONTENT_PATTERNS.md`, `TOOLS_AND_FUNNEL_REFERENCES.md`) — 콘텐츠 전략/후킹/CTA/패턴 벤치마크. 이미 `modules/pattern_engine/`, `modules/content/`의 실제 코드(패턴/훅/CTA 매핑)에 반영되어 있다.

정확한 최신 목록은 매번 `Glob("docs/**/*.md")`, `Glob("docs/RESEARCH/**/*.md")`로 확인한다 — 이 목록은 계속 늘어난다.

## 새 Research 문서가 필요할 때

- Claude/Codex는 새 Research 문서를 스스로 작성하지 않는다. 원자료 분석 및 문서화 요청이 오면, 이 흐름대로
  ChatGPT CTO의 분석 결과를 먼저 요청하도록 사용자에게 안내한다.
- 이미 있는 Research 문서와 새로 받은 내용이 충돌하면, 임의로 어느 한쪽을 정답으로 취급하지 않고 사용자에게
  확인한다.
