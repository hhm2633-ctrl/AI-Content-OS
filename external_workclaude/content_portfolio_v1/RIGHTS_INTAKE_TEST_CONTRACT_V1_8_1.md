# Rights Intake Test Contract V1.8.1

## 목적

- V1.8 권리 Intake 계약을 구현할 때 최소 회귀 범위를 고정한다.
- 테스트는 `RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8_1.json`의 변경 시나리오 기준으로 동작한다.

## 검증 규칙

### A. 계약 불변식 (필수)
1. `RIGHTS_INTAKE_CONTRACT_V1_8.json`의 레코드 수 = **24**.
2. 고유 콘텐츠 수 = **12** (`CN-013`, `CN-014`, `CN-016`, `CN-017`, `SH-017`, `SH-006`, `SH-018`, `IG-007`, `IG-009`, `IG-013`, `KN-008`, `KN-007`).
3. 카드뉴스는 콘텐츠당 정확히 4장, `card_index=1..4`.
4. `card_news_repo_relative_base`와 `card_path` prefix는 `storage/output_sets/card_news/sets/<output_set_id>/cards/card_news_1..4.png`와 일치.
5. `publish_ready`와 `actual_publish`는 기본적으로 `false`여야 하며, true 값은 검증 실패 케이스에서만 검증한다.

### B. 실패 케이스(레디니스 차단)
아래 케이스는 반드시 `publish_ready=false` 또는 `actual_publish=false`여야 하며, 해당 차단사유가 누락되면 실패한다.

- `missing_fields`: 필수 키 누락(`record` 누락 + `rights_evidence:null` + 체크리스트 null)
- `forged_approval`: 허위 승인(토큰 조합/권리 상태 위장)
- `absolute_path`: 절대경로 참조
- `runs_path`: `.runs` 경로
- `staging_path`: `.staging` 경로
- `output_set_id_mismatch`: `output_set_id` 위변조
- `publish_flags_manipulated`: publish 플래그 조작
- `publish_ready_type_confusion`: publish_ready/actual_publish을 문자열로 위변조
- `rights_output_set_whitespace`: 양끝 공백이 붙은 `output_set_id`
- `rights_evidence_shape_spoof`: `rights_evidence`를 dict가 아닌 타입으로 위조

### C. False-ready/False-blocked 추가 시나리오
- False-ready(should block):
  1) `publish_ready="true"`(문자열) + 나머지 placeholder 유지.
  2) `output_set_id` 앞뒤 공백 혼입.
  3) `rights_evidence` 타입 스푸핑.
- False-blocked(should still block intentionally?):
  1) `origin/role/rights_status` placeholder만 채운 상태에서 모든 경로가 유효한 계약.
  2) 계약 자체가 미완성 상태이므로 `publish`로 오인될 경우 재발.
  3) 구현 가이드에서는 위 상태를 `blocked`로 처리해야 함(특히 자동 완료 판단 금지).

## pass/fail 기대

| Case ID | Expected `publish_ready` | Expected `actual_publish` | Expected blocker |
|---|---:|---:|---|
| normal | false | false | 없음 |
| missing_fields | false | false | 필수필드/구조 결함 |
| forged_approval | false | false | rights/evidence/compliance 계열 |
| absolute_path | false | false | manifest/path 계열 |
| runs_path | false | false | path 계열 |
| staging_path | false | false | path 계열 |
| output_set_id_mismatch | false | false | output_set mismatch |
| publish_flags_manipulated | false | false | publish flags |
| publish_ready_type_confusion | false | false | 타입 불일치 |
| rights_output_set_whitespace | false | false | output_set mismatch |
| rights_evidence_shape_spoof | false | false | rights/evidence 구조 결함 |

## 구현 매핑

- `modules/compliance/card_news_publish_gate.py`  
  - `operator_checklist`/`_check_assets`/`_check_evidence`/`_check_quality` 동작과의 정합성
- `modules/publishing/publishing_module.py`  
  - `_resolve_package_readiness`의 문자열 비교(`is True`)/타입 엄격성
- `src/workflow_engine.py`  
  - `_build_pre_publish_attestation` 결과가 이 계약에서 placeholder 상태를 깨지 않도록 유지되는지 확인
