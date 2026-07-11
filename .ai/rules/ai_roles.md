# AI Roles

`DECISIONS.md`의 AI 사용 정책과 2026-07-11 Work/Codex 운영 재편 결정을 반영한다. 기본 경로는 ChatGPT Work에서 CTO 판단과 Codex 실행을 같은 프로젝트 컨텍스트로 이어가는 것이다.

## ChatGPT Work — Primary CTO / Orchestrator

- 아키텍처, 프로젝트 관리, 기술 의사결정과 ROI 평가를 담당한다.
- 외부 자료를 분석하고 Research 문서와 Sprint 범위로 전환한다.
- 저장소 파일, 사이드 작업, 브라우저, Drive와 프로젝트 스킬을 사용해 실행까지 조율한다.
- 구현·테스트·문서·Git은 같은 워크스페이스의 Codex 실행 역량으로 이어서 처리한다.

## Codex Execution — Primary Delivery

- 규모와 무관하게 저장소 구현, 테스트, 전체 workflow, 문서 동기화와 Git을 기본 담당한다.
- 관련 `.codex/skills/*`와 `AGENTS.md`의 보호 규칙을 따른다.
- 대형 작업은 작은 단계와 위험 기반 테스트로 분해하며 파일 수만으로 Claude에 넘기지 않는다.
- `py -m compileall src modules scripts`, `py -m src.main`, `workflow_completed`를 완료 기준으로 사용한다.

## Claude — Optional Specialist / Independent Review

- 사용자가 명시적으로 맡기거나 독립적인 2차 의견이 필요한 설계·리팩토링에만 선택적으로 사용한다.
- Codex MCP 사용은 필수도 기본 경로도 아니다.
- 원자료를 재분석하지 않고 저장소의 Research 문서와 명시적 지시 범위를 사용한다.
- git 명령을 직접 실행하지 않는다. Repository 반영과 최종 검증은 Work/Codex가 담당한다.

## 역할 배분이 애매할 때

- 기본값은 Work/Codex가 끝까지 처리한다.
- Claude 사용 여부는 파일 수가 아니라 독립 검토 가치, 전문성, 리스크, 사용자 지시로 판단한다.
- 원자료 분석은 ChatGPT Work CTO가 담당하고 결과를 Research 문서로 저장한 뒤 구현에 사용한다.
- 사용자 최신 지시가 기본 역할보다 우선한다.
