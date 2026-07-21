# V1.8 Rights Intake Implementation Handoff

## 목표

`src/modules/tests`에서 구현할 최소 변경점은 다음 항목입니다.

1. 카드뉴스/커머스/숏츠/IG/KN 파이프라인에서
   `output_set_id == 91a28c88912849b58fa608330a217467` 고정 검증 유지
2. `rights_evidence` 입력을 `pre_publish_attestation`에 반영
3. operator checklist를 publish readiness 판정의 입력으로 사용
4. `PUBLISH_RIGHTS_BLOCKED`, `PUBLISH_EVIDENCE_BLOCKED`, `PUBLISH_COMPLIANCE_BLOCKED`,
   `PUBLISH_MANUAL_IMAGE_REQUIRED`, `PUBLISH_COMMITTED_ATTESTATION_INVALID`
   유지 조건은 그대로 두되, 실제 근거 입력이 들어오면 통과 가능하도록 처리

## 최소 코드 범위(다음 구현 단계)

- `src/workflow_engine.py`
  - `_build_pre_publish_attestation`: rights 증빙 텍스트/체크리스트 반영 지점
  - `_correct_committed_attestation` 혹은 equivalent 단계에서 rights_intake 레코드 조합
- `modules/publishing/publishing_module.py`
  - `_resolve_package_readiness` 입력 값으로 `rights_evidence`/`operator_checklist`를 재확인
- `modules/compliance/card_news_publish_gate.py`
  - `final_cards_invalid`/`manifest_paths_match` 기존 로직은 유지, 신규 권리 근거는 검증 함수로 연결만 확장
- tests
  - `tests/test_workflow_card_news_output_receipts.py`
  - `tests/test_workflow_card_news_output_set_integrity.py`
  - 필요 시 `tests/test_publishing_rights_intake_v1_8.py` 신규 추가

## 권장 테스트 케이스

1. commit-path 카드 경로와 rights_intake 의 `card_path`가 1:1 바인딩되었는지
2. output_set_id 불일치 시 publish readiness false
3. 절대경로/.runs/.staging path는 즉시 실패
4. `reference_verified=true`인 경우 source_url/evidence/operator_checklist가 같이 존재할 때만 통과
5. 누락 레코드(`origin/role/rights_evidence`)는 PUBLISH_RIGHTS_BLOCKED 유지
6. publish_ready/actual_publish 수동 조작 시 fail-close

## 계약 위반 시 대안

- 누락이나 조작이 있으면 실제 publish pipeline로는 진입하지 말고 `publish_ready=false`와 `actual_publish=false`를 강제 유지.
- `RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8.json`의 `forged`/`output_set_id_mismatch` 케이스를 기준으로 회귀 테스트를 설계하세요.
