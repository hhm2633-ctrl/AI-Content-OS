# QA Report V1.8

## Scope

- 대상: V1.8 Rights Intake Pack 생성 및 공격 fixture/self QA
- 기준 output_set_id: 91a28c88912849b58fa608330a217467

## 결과 요약

- contract records: 24
- fixture cases: 8
- contract card binding issues: 0
- contract missing field issues: 0

## 세부 검증

- 계약 레코드
  - cardnews 4장 경로 개수(내용별): expected 4
  - publish_ready/actual_publish default: false enforced
  - required fields exist: placeholders 및 null 허용

- 경로 보안
  - 절대경로 차단: 0
  - `.runs`/`.staging` 차단: 0
  - output_set_id 불일치: 0

- 조작 탐지
  - forged 또는 publish flag 조작: fixture 레벨에서 감지

## 파일

- RIGHTS_INTAKE_CONTRACT_V1_8.json: 생성됨
- RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8.json: 생성됨
- RIGHTS_INTAKE_OPERATOR_GUIDE_V1_8.md: 생성됨
- RIGHTS_INTAKE_IMPLEMENTATION_HANDOFF_V1_8.md: 생성됨
- tools/build_rights_intake_v1_8.py: 생성됨

