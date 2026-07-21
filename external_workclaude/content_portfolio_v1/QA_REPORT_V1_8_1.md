# Rights Intake QA Report V1.8.1

- 실행 일시: 2026-07-13T12:00:00Z

## 요약
- PASS 수: 1
- FAIL 수: 10
- 전체 fixture 시나리오 수: 11
- Fixture 매핑 수: 11 (기대: 11)

## 계약 정합성
- contract records: 24
- unique content: 12
- cardnews record: 16
- record_id duplicate: 0
- contract pass: True

### contract check map
- record_count: PASS
- unique_content_count: PASS
- card_news_count: PASS
- cardnews_content_count: PASS
- cardnews_index_coverage: PASS
- publish_flags_bool_false: PASS
- record_id_no_duplicate: PASS
- card_path_binding: PASS

## Fixture 시나리오
- 기대 PASS: 1
- 기대 FAIL: 10
- 실제 PASS: 1
- 실제 FAIL: 10

- normal: PASS | actual=[] | expected=[]
- missing_fields: PASS | actual=['MISSING_REQUIRED_FIELDS'] | expected=['MISSING_REQUIRED_FIELDS']
- forged_approval: PASS | actual=['FORGED_APPROVAL'] | expected=['FORGED_APPROVAL']
- absolute_path: PASS | actual=['PATH_FORBIDDEN_ABSOLUTE'] | expected=['PATH_FORBIDDEN_ABSOLUTE']
- runs_path: PASS | actual=['PATH_FORBIDDEN_RUNS_OR_STAGING'] | expected=['PATH_FORBIDDEN_RUNS_OR_STAGING']
- staging_path: PASS | actual=['PATH_FORBIDDEN_RUNS_OR_STAGING'] | expected=['PATH_FORBIDDEN_RUNS_OR_STAGING']
- output_set_id_mismatch: PASS | actual=['OUTPUT_SET_ID_MISMATCH'] | expected=['OUTPUT_SET_ID_MISMATCH']
- publish_flags_manipulated: PASS | actual=['PUBLISH_FLAG_TRUE'] | expected=['PUBLISH_FLAG_TRUE']
- publish_ready_type_confusion: PASS | actual=['PUBLISH_FLAG_TYPE_INVALID'] | expected=['PUBLISH_FLAG_TYPE_INVALID']
- rights_output_set_whitespace: PASS | actual=['OUTPUT_SET_ID_WHITESPACE_BLOCK'] | expected=['OUTPUT_SET_ID_WHITESPACE_BLOCK']
- rights_evidence_shape_spoof: PASS | actual=['RIGHTS_EVIDENCE_INVALID_TYPE'] | expected=['RIGHTS_EVIDENCE_INVALID_TYPE']

## 보안 정합성
- placeholder 오인 승인 오탐 차단: PASS
- path/.runs/.staging 제로: PASS

## 기존 V1.7/V1.8 바이트 무변경
- external_workclaude/content_portfolio_v1/MANIFEST_PATH_FIX_V1_7.json: PASS
- external_workclaude/content_portfolio_v1/MANIFEST_PATH_FIX_V1_7.md: PASS
- external_workclaude/content_portfolio_v1/QA_REPORT_V1_7.md: PASS
- external_workclaude/content_portfolio_v1/QA_REPORT_V1_8.md: PASS
- external_workclaude/content_portfolio_v1/RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8.json: PASS
- external_workclaude/content_portfolio_v1/RIGHTS_INTAKE_CONTRACT_V1_8.json: PASS
- external_workclaude/content_portfolio_v1/RIGHTS_INTAKE_IMPLEMENTATION_HANDOFF_V1_8.md: PASS
- external_workclaude/content_portfolio_v1/RIGHTS_INTAKE_OPERATOR_GUIDE_V1_8.md: PASS
