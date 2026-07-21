---
name: debug
description: Claude Debug 원칙. 원인 분석을 코드 수정보다 먼저 하고, 기존 구조를 유지한 채 최소 수정만 하며, WorkflowEngine을 보호한다.
---

# Debug Skill

## Purpose

AI-Content-OS에서 문제(fallback 반복, 느린 실행, 이상한 결과물 등)를 조사할 때
"일단 코드부터 고치기"가 아니라 "먼저 원인을 증거로 확인하기"를 우선하기 위한 스킬이다.

## 원인 분석 우선순위

코드를 고치기 전에 아래 순서로 증거를 모은다:

1. **런타임 결과물 확인** — `storage/workflow_results/99_final_result.json`의 `status`, 각 단계별 `NN_<name>_result.json`, `storage/runtime/service_diagnostic.json`(`error_type`/`safe_message`/`api_key_present`), `storage/card_news/card_news_quality.json` 등 이미 기록된 진단 데이터를 먼저 읽는다.
2. **CHANGELOG.md / MODULE_STATUS.md 확인** — 최근에 무엇이 바뀌었고 어떤 결과가 검증되었는지 확인한다.
3. **재현 가능한 최소 증거 확보** — 필요하면 읽기 전용 점검(로그 존재 여부, 프로세스 상태, 네트워크 연결 테스트 등)으로 가설을 검증한다. 이때도 `.env` 값 자체나 API Key는 절대 출력하지 않는다 — 존재 여부(boolean)만 확인한다.
4. **원인을 문장으로 명확히 하고 나서** 코드 수정 여부를 판단한다.

## 기존 구조 유지 / 최소 수정

- 디버깅 중 발견한 문제와 무관한 코드를 "김에 정리"하지 않는다. 문제와 직접 관련된 부분만 고친다.
- 원인이 네트워크/외부 서비스(예: 테더링 환경의 간헐적 연결 거부)처럼 코드로 고칠 수 없는 것이라면, 코드를 억지로 바꾸기보다 **사실을 있는 그대로 보고**한다 (`performance.md`의 재시도 비용 참고).
- 이미 존재하는 fallback/재시도/진단 장치(`ServiceDiagnostic`, `RetryPolicy`, `TrendEngineGuard` 등)를 다시 만들지 않는다 — 있는 것을 먼저 활용한다.

## WorkflowEngine 보호

- 디버깅 목적이라도 `src/workflow_engine.py`의 구조나 모듈 호출 순서를 바꾸지 않는다.
- 디버깅 지시에 "코드 수정 금지"/"py -m src.main 실행 금지"/"git 명령 실행 금지" 같은 제약이 있다면 문자 그대로 지킨다 — 읽기 전용 조사만으로 결론을 낸다.
- 원인 규명 결과 실제 코드 수정이 필요하다고 판단되면, 그 수정 자체는 별도 Sprint(지시)로 넘기고 이번 디버깅에서는 수행하지 않는다 (지시받지 않은 한).

## 보고 형식

디버깅 보고에는 최소한 아래를 포함한다:

- 확인한 사실 (로그/결과 파일 근거와 함께)
- 배제한 가설과 그 근거
- 최종 원인 추정 (확실하지 않으면 확실하지 않다고 명시)
- 다음에 필요한 조치 (코드 수정이 필요하면 별도 Sprint로 제안)
