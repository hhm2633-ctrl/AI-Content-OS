# AI-Content-OS — AI Developer Kit

## 이게 뭔가

`.ai/`는 AI-Content-OS에서 협업하는 **모든 AI(ChatGPT CTO, Claude, Codex, 그리고 향후 추가될 AI)가 공통으로 참조하는**
프로젝트 개발 인프라다. 특정 AI 전용 절차는 각자의 폴더(`.claude/skills/`, `.codex/skills/`)에 있고,
`.ai/`는 그 위에 있는 **AI에 상관없이 항상 같아야 하는 사실/규칙/템플릿**을 모아둔다.

목적은 매 Sprint/작업마다 "이 프로젝트가 어떻게 동작하는지", "누가 뭘 담당하는지", "무엇을 절대 바꾸면 안 되는지"를
반복 설명하지 않고, 이 문서를 가리키는 것만으로 충분하게 만드는 것이다.

## 구성

```text
.ai/
├── README.md                          (이 문서)
├── architecture/
│   └── system_architecture.md         전체 구조, WorkflowEngine, Module/Engine/문서 관계
├── workflows/
│   ├── development_workflow.md        사용자 -> ChatGPT CTO -> Claude -> Codex -> GitHub
│   └── sprint_workflow.md             Sprint 시작 -> ROI -> 작업 분해 -> ... -> 문서 업데이트
├── rules/
│   ├── project_rules.md               절대 규칙 (WorkflowEngine 보호, Windows, Fallback 우선)
│   ├── ai_roles.md                    ChatGPT/Claude/Codex 역할 분담
│   └── workflow_protection.md         workflow_completed / Fallback / Retry / Cache 보호 규칙
├── prompts/
│   └── README.md                      Prompt 관리 원칙, Prompt Library 구조
├── templates/
│   ├── task_template.md               AI 작업지시서(Sprint 지시) 작성 템플릿
│   └── sprint_template.md             Sprint 계획 템플릿
├── knowledge/
│   └── knowledge_system.md            외부 자료 -> CTO 분석 -> Research 문서 -> 프로젝트 자산
└── decision/
    └── decision_engine.md             ROI/파일 수/위험도 기반 AI 의사결정 규칙
```

## 사용 방법

- **작업을 시작하기 전**: `architecture/system_architecture.md`로 현재 구조를 확인하고, `rules/project_rules.md` +
  `rules/workflow_protection.md`로 절대 규칙을 재확인한다.
- **새 Sprint 지시서를 쓸 때** (주로 ChatGPT CTO): `templates/task_template.md` 또는 `templates/sprint_template.md`를 기준으로 작성한다.
- **작업 범위/담당 AI를 정할 때**: `decision/decision_engine.md`의 기준(ROI, 파일 수, 위험도)으로 판단한다.
- **외부 자료(PDF/영상/UI/서비스/사이트)를 다룰 때**: `knowledge/knowledge_system.md`의 흐름을 따른다.
- **새 프롬프트를 추가/수정할 때**: `prompts/README.md`의 원칙(중복 프롬프트 금지, 버전 관리)을 따른다.
- **AI별 세부 작업 절차**는 이 문서가 아니라 각자의 스킬 시스템을 본다:
  - Claude: `.claude/skills/*.md` (교차 규칙) + `.claude/skills/domain/*.md` (엔진별 상세)
  - Codex: `.codex/skills/*/SKILL.md`

## AI 역할 (요약)

상세 기준은 `rules/ai_roles.md`를 따른다.

| AI | 역할 |
|---|---|
| ChatGPT | CTO — 아키텍처 설계, ROI 판단, Sprint 지시서 작성, 외부 자료 분석 |
| Claude | Large Implementation — 대량 구현, 복잡한 리팩토링, 신규 모듈 생성 |
| Codex | Repository/Test — git 관리, compile/workflow 실행, 커밋, 문서 최종 반영 |

## 절대 원칙 (요약)

상세 규칙은 `rules/project_rules.md`, `rules/workflow_protection.md`를 따른다. 요약하면:

- `WorkflowEngine`(`src/workflow_engine.py`) 구조와 모듈 호출 순서를 바꾸지 않는다.
- `workflow_completed`를 절대 깨뜨리지 않는다 — 외부 서비스 실패는 항상 fallback 이벤트로 처리한다.
- Windows 환경에서는 항상 `py -m src.main`을 쓰고, `python -m src.main`은 쓰지 않는다.
- `.env`는 값을 읽어 존재 여부만 확인하고, 절대 출력하지 않는다.
