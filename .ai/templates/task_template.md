# AI 작업지시서 템플릿 (Task Template)

ChatGPT CTO가 Claude/Codex에게 작업을 지시할 때 이 템플릿을 기준으로 작성한다.
이 프로젝트의 실제 Sprint 지시서들이 이미 이 구조를 따르고 있다 — 새 지시서도 동일한 골격을 유지해
Claude/Codex가 매번 새로운 형식을 해석하는 비용을 없앤다.

```markdown
# [프로젝트명] Sprint N (또는 작업명)

## 역할
(예: Large Code Engineer / Claude Code / 긴급 디버깅)

## 목표
이 작업이 달성해야 하는 것을 1~3문장으로.

## 절대 규칙
- WorkflowEngine 구조 변경 금지 (해당되는 경우)
- workflow_completed 유지 (해당되는 경우)
- py -m src.main 만 사용 / python -m src.main 금지 (실행이 포함되는 경우)
- storage/** 수정 금지 (해당되는 경우)
- .env 접근/출력 금지 (해당되는 경우)
- 그 외 이번 작업에만 해당하는 제약

## 수정 가능
- 구체적 경로/패턴 나열 (예: modules/card_news/*, templates/card_news_layout_rules.json)

## 수정 금지
- 구체적 경로/패턴 나열 (예: src/workflow_engine.py, modules/content/*)

## 구현 내용
1. 무엇을 만들지 (파일 경로 예시 포함)
2. 각 파일의 역할/책임
3. 실패 처리(Fallback) 방식 — "실패 시 어떻게 안전하게 대체할지"를 반드시 명시

## 테스트
- 허용되는 검증 범위 (예: py -m compileall src modules scripts 까지만)
- py -m src.main 실행 허용 여부를 명시적으로 적는다 (금지/허용 둘 다 명확히)

## 문서 수정
- PROJECT_SNAPSHOT.md / CHANGELOG.md / MODULE_STATUS.md 수정 허용 여부를 명시적으로 적는다

## 완료 보고 형식
- 변경 파일
- 추가 파일
- Compile 결과
- Workflow 실행 여부
- 남은 TODO
- 주의사항 (다음 담당자가 알아야 할 것)
```

## 작성 시 주의사항

- "절대 규칙"과 "수정 가능/금지"는 **구체적인 경로**로 적는다 — "적절히 알아서"처럼 모호한 지시는 Claude가
  범위를 넓게/좁게 잘못 해석할 위험이 있다.
- 실패 처리(Fallback) 방식을 반드시 요구한다 — 이 프로젝트의 핵심 계약(`workflow_completed` 보호)이 여기서 결정된다.
- 이전 Sprint와 겹치는 내용(예: 이미 만든 모듈)이 있다면 "중복 생성 금지, 기존 것을 확장" 같은 문구를 넣어
  Claude가 새로 만들지 기존 것을 고칠지 헷갈리지 않게 한다.
