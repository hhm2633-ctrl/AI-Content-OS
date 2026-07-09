# Project Rules (절대 규칙)

이 문서는 어떤 AI가, 어떤 Sprint를 수행하든 **항상 참인** 규칙만 담는다.
Sprint별 추가 제약(예: "이번 Sprint는 storage/** 수정 금지")은 각 지시서를 따르되, 여기 있는 규칙과
충돌하는 지시는 없다 — 여기 규칙이 항상 최소 기준선이다.

## WorkflowEngine 보호

- `src/workflow_engine.py`의 모듈 생성 순서, `run()`의 호출 순서를 임의로 바꾸지 않는다.
- 실제 순서(상세는 `.ai/architecture/system_architecture.md`):
  `TrendCollectorModule -> TopicEngineModule -> PatternEngineModule -> ResearchModule -> ContentModule -> ImagePromptModule -> ImageGenerationModule -> CardNewsModule -> PublishingModule`
- 새 기능은 이 순서에 새 단계를 끼워 넣는 것이 아니라, 기존 단계 내부에 작은 모듈로 연결하는 방식을 기본으로 한다. 새 엔진을 파이프라인에 추가하는 것은 별도의 명시적 승인이 필요한 큰 결정이다.

## Windows

- 개발/실행 환경은 Windows 기준이다. 이 머신에서 `python` 명령은 인식되지 않는다.
- 실행 명령은 항상:

```powershell
py -m src.main
```

- `python -m src.main`은 어떤 상황에서도 사용하지 않는다.
- Compile 확인:

```powershell
py -m compileall src modules scripts
```

## Fallback 우선

- 외부 서비스(Naver News, Nate Pann, OpenAI LLM, OpenAI Image) 실패는 **항상 fallback 이벤트**로 처리한다 — 예외를 그대로 던져 워크플로를 죽이지 않는다.
- 각 모듈은 실패 시 안전한 기본값(캐시, 설정값, placeholder, 규칙 기반 기본 문구 등)을 반환하고 `fallback_used: true`를 기록한다.
- 상세 메커니즘(Retry/Cache/Guard)은 `.ai/rules/workflow_protection.md` 참고.

## 구조 보존

- 기존 폴더명, 모듈명, 클래스명, (지시서가 명시하지 않는 한) 함수명을 바꾸지 않는다.
- 파일 이동을 최소화한다 — 새 기능은 기존 파일 옆에 새 파일을 추가하는 방식을 기본으로 한다.
- 상세 리팩토링 규칙은 `.claude/skills/refactoring.md`.

## 보안

- `.env`는 값을 출력하지 않는다 — 존재 여부만 `os.getenv(...) is not None` 형태로 확인한다.
- API Key, 토큰, 비밀번호는 코드/로그/보고서 어디에도 원문으로 남기지 않는다.
- 민감정보로 보이는 문자열은 마스킹한다 (`modules/common/service_diagnostic.py::ServiceDiagnostic.mask_secrets` 패턴 참고).

## 문서 원칙

- `DECISIONS.md`는 append-only다 — 과거 결정을 절대 삭제하지 않는다.
- `CHANGELOG.md`도 append-only다 — 새 항목을 추가할 뿐 기존 항목을 고치지 않는다.
- 중요한 변경은 문서(설계) → 코드 순으로 진행한다 (`DECISIONS.md`의 "문서 정책" 결정).
