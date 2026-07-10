---
name: architecture
description: AI-Content-OS 프로젝트 구조를 파악할 때 항상 먼저 사용하는 문서. 어떤 Sprint/작업을 시작하든 이 순서로 컨텍스트를 잡는다.
---

# Architecture Skill

## Purpose

Claude가 AI-Content-OS에서 어떤 작업(Sprint, 디버깅, 리서치 반영 등)을 시작하든
가장 먼저 프로젝트 상태를 파악하기 위해 사용하는 스킬이다.

이 스킬보다 먼저 `.claude/skills/cto_operating_system/SKILL.md`와 프로젝트 루트의
`PROJECT_OPERATING_SYSTEM.md`(Mandatory Reading Order, Protected Core/Intelligence Layer
구분, Offline-First 원칙 등 최상위 운영 규칙)를 확인한다. 아래 목록은 그 Reading Order를
실제로 수행하는 구체적인 절차다.

코드를 열어보기 전에 이 문서들을 통해 "지금 프로젝트가 어디까지 왔는지"를 먼저 확인한다.

## 읽는 문서 (우선순위 순)

1. `PROJECT_MASTER.md` — 프로젝트 목적, 현재 핵심 기능, 향후 확장 방향
2. `PROJECT_SNAPSHOT.md` — 가장 최근 `py -m src.main` 실행 결과, 현재 WorkflowEngine 단계, 프로젝트 트리
3. `MODULE_STATUS.md` — Sprint별로 완료된 기능 목록, 남은 작업(Next), 운영 규칙(Notes)
4. `ROADMAP.md` — 현재/향후 마일스톤. 카드뉴스 MVP가 항상 최우선이며, 그 외 항목은 후순위임을 확인
5. `AGENTS.md` — Codex 실행/구조/안정성/문서화 규칙 (Claude도 동일 원칙을 따름)
6. `CURRENT_TASK.md` — (필요 시) 현재 진행 중인 작업 컨텍스트
7. `DECISIONS.md` — (필요 시) 과거에 내려진 의사결정과 그 이유. 절대 삭제되지 않는 append-only 로그이므로, 과거 결정을 뒤집는 작업 전에는 반드시 확인

전체를 매번 다 읽을 필요는 없다. 작업 범위에 맞는 문서만 선택적으로 확인한다.

## 읽는 순서 (개념 순서)

1. **프로젝트 구조** — 위 문서들로 현재 상태를 파악한다.
2. **WorkflowEngine 구조 / Workflow 순서** — 아래 실제 파이프라인 순서를 항상 전제로 작업한다.
3. **WorkflowEngine 보호 규칙** — 절대 변경 금지 항목을 확인한다.
4. **Windows 실행 규칙** — 실행 명령이 필요한 경우 아래 규칙을 따른다.

## 프로젝트 구조 (요약)

AI-Content-OS는 `src/workflow_engine.py::WorkflowEngine`이 여러 `modules/<engine>/` 모듈을 순서대로 호출하는
단일 파이프라인 구조다. 각 모듈은 이전 단계의 결과 dict를 받아 자신의 결과 dict를 반환하고,
`WorkflowEngine`이 매 단계 결과를 `storage/workflow_results/`에 저장한다.

- `modules/<engine_name>/` — 각 파이프라인 단계의 실제 로직 (예: `modules/content/`, `modules/card_news/`)
- `src/` — 진입점(`main.py`)과 `WorkflowEngine`, 공용 `LLMClient`
- `config/` — 모듈별 설정 JSON (`settings.json`, `brand_profile.json` 등)
- `templates/` — 레이아웃/렌더링 규칙 등 데이터 템플릿
- `prompts/` — LLM 프롬프트 가이드 (패턴별 `prompts/patterns/*.md` 포함)
- `storage/` — 런타임 산출물(JSON 결과, PNG, 로그). Claude는 이 폴더를 직접 수정하지 않는다.
- `.claude/skills/` — 이 스킬 문서들 (Claude Developer Kit)
- `.codex/skills/` — Codex용 병렬 스킬 시스템

## WorkflowEngine 구조 / Workflow 순서

`WorkflowEngine.__init__`이 아래 9개 모듈을 생성하고, `WorkflowEngine.run()`이 항상 이 순서로 호출한다.
이 순서 자체가 프로젝트의 핵심 계약이며, 지시 없이 바꾸지 않는다.

```text
TrendCollectorModule
  ↓
TopicEngineModule
  ↓
PatternEngineModule
  ↓
ResearchModule
  ↓
ContentModule
  ↓
ImagePromptModule
  ↓
ImageGenerationModule
  ↓
CardNewsModule
  ↓
PublishingModule
```

- 각 단계 결과는 `storage/workflow_results/NN_<name>_result.json`으로 저장된다.
- 모든 단계가 끝나면 `storage/workflow_results/99_final_result.json`에 `status: "workflow_completed"`가 기록된다.
- 한 단계 안에서 외부 서비스(Naver/Nate/LLM/Image)가 실패해도, 그 모듈은 fallback 값을 반환할 뿐 예외를 던지지 않는다 — 그래야 다음 단계로 계속 진행되고 `workflow_completed`가 유지된다.

## WorkflowEngine 보호 규칙

- `src/workflow_engine.py`의 구조(모듈 순서, 호출 방식)를 임의로 바꾸지 않는다.
- 기존 모듈/폴더/클래스 이름을 바꾸지 않는다.
- `workflow_completed` 상태를 깨뜨리는 변경은 하지 않는다.
- 외부 API/네트워크/렌더링 실패는 항상 fallback 이벤트로 처리되어야 하며, `workflow_failed`로 이어지면 안 된다.
- 새 기능은 기존 흐름에 연결되는 작은 모듈로 추가한다 (WorkflowEngine을 새로 설계하지 않는다).

## Windows 실행 규칙

```powershell
py -m src.main
```

- `python -m src.main`은 사용하지 않는다 (이 환경에서 `python` 명령이 인식되지 않음).
- Compile 확인은 `py -m compileall src modules scripts`를 사용한다.

## workflow_completed 보호 규칙

- 모든 변경 후 `storage/workflow_results/99_final_result.json`의 `status`가 `workflow_completed`인지가 최종 기준이다.
- 이 파일은 `storage/**`에 속하므로 Claude가 직접 수정하지 않는다 — 오직 `py -m src.main` 실행 결과로만 갱신된다.
- Sprint 지시에서 "py -m src.main 실행 금지"라고 명시된 경우, 이 확인은 Codex가 담당한다.
