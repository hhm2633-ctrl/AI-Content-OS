# Team Handoffs V1.4

Per-role view of every work order this role owns, so each team can pick up its queue without reading the entire pipeline.

## 문안·스토리 (12 work orders)

### CN-013-WO-01 -- CN-013 반려동물 첫 입양 준비물
- task_goal: V1.3.1 최종 문안(4장)을 프로덕션 확정본으로 재확인하고, 슬라이드별 역할(hook/problem/solution/cta)과 문장 완결성을 최종 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: CN-013_copy_signoff.md (문안 최종 확인 서명)
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '최종 문안의 의미를 변경하는 재작성 (변경 필요 시 Evidence·Rights 역할과 협의 후 별도 개정 요청)']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장 완성 문안이 존재함
- definition_of_done: 4장 문장 완결성(말줄임표 없음), 숫자 약속-실제 항목 수 일치, CTA 단일 여부를 재확인하고 서명 완료
- acceptance_checks: ['4장 존재 확인', 'ellipsis 없음 확인', 'number_consistency_check.match == true 확인', 'CTA 1개 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### CN-014-WO-01 -- CN-014 캠핑 초보 준비물 체크리스트
- task_goal: V1.3.1 최종 문안(4장)을 프로덕션 확정본으로 재확인하고, 슬라이드별 역할(hook/problem/solution/cta)과 문장 완결성을 최종 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: CN-014_copy_signoff.md (문안 최종 확인 서명)
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '최종 문안의 의미를 변경하는 재작성 (변경 필요 시 Evidence·Rights 역할과 협의 후 별도 개정 요청)']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장 완성 문안이 존재함
- definition_of_done: 4장 문장 완결성(말줄임표 없음), 숫자 약속-실제 항목 수 일치, CTA 단일 여부를 재확인하고 서명 완료
- acceptance_checks: ['4장 존재 확인', 'ellipsis 없음 확인', 'number_consistency_check.match == true 확인', 'CTA 1개 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### CN-016-WO-01 -- CN-016 여행 전 짐싸기 체크리스트
- task_goal: V1.3.1 최종 문안(4장)을 프로덕션 확정본으로 재확인하고, 슬라이드별 역할(hook/problem/solution/cta)과 문장 완결성을 최종 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: CN-016_copy_signoff.md (문안 최종 확인 서명)
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '최종 문안의 의미를 변경하는 재작성 (변경 필요 시 Evidence·Rights 역할과 협의 후 별도 개정 요청)']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장 완성 문안이 존재함
- definition_of_done: 4장 문장 완결성(말줄임표 없음), 숫자 약속-실제 항목 수 일치, CTA 단일 여부를 재확인하고 서명 완료
- acceptance_checks: ['4장 존재 확인', 'ellipsis 없음 확인', 'number_consistency_check.match == true 확인', 'CTA 1개 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### CN-017-WO-01 -- CN-017 커피 원두 보관법
- task_goal: V1.3.1 최종 문안(4장)을 프로덕션 확정본으로 재확인하고, 슬라이드별 역할(hook/problem/solution/cta)과 문장 완결성을 최종 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: CN-017_copy_signoff.md (문안 최종 확인 서명)
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '최종 문안의 의미를 변경하는 재작성 (변경 필요 시 Evidence·Rights 역할과 협의 후 별도 개정 요청)']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장 완성 문안이 존재함
- definition_of_done: 4장 문장 완결성(말줄임표 없음), 숫자 약속-실제 항목 수 일치, CTA 단일 여부를 재확인하고 서명 완료
- acceptance_checks: ['4장 존재 확인', 'ellipsis 없음 확인', 'number_consistency_check.match == true 확인', 'CTA 1개 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### SH-017-WO-01 -- SH-017 반려동물 산책 준비물 점검
- task_goal: V1.3.1 최종 스크립트(4장면, 내레이션/자막)를 프로덕션 확정본으로 재확인하고 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: SH-017_script_signoff.md
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장면 스크립트가 존재함
- definition_of_done: 4장면의 내레이션/자막/촬영 구도가 재확인되고 서명 완료
- acceptance_checks: ['4장면 존재 확인', 'narration/subtitle/shot_composition 필드 존재 확인']
- blocker_codes: 없음
- next_handoff_target: Evidence·Rights
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### SH-006-WO-01 -- SH-006 커피 내리는 법 3단계
- task_goal: V1.3.1 최종 스크립트(4장면, 내레이션/자막)를 프로덕션 확정본으로 재확인하고 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: SH-006_script_signoff.md
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장면 스크립트가 존재함
- definition_of_done: 4장면의 내레이션/자막/촬영 구도가 재확인되고 서명 완료
- acceptance_checks: ['4장면 존재 확인', 'narration/subtitle/shot_composition 필드 존재 확인']
- blocker_codes: 없음
- next_handoff_target: Evidence·Rights
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### SH-018-WO-01 -- SH-018 캐리어 짐싸기 순서
- task_goal: V1.3.1 최종 스크립트(4장면, 내레이션/자막)를 프로덕션 확정본으로 재확인하고 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: SH-018_script_signoff.md
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장면 스크립트가 존재함
- definition_of_done: 4장면의 내레이션/자막/촬영 구도가 재확인되고 서명 완료
- acceptance_checks: ['4장면 존재 확인', 'narration/subtitle/shot_composition 필드 존재 확인']
- blocker_codes: 없음
- next_handoff_target: Evidence·Rights
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### IG-007-WO-01 -- IG-007 문화생활 예산 관리 팁
- task_goal: V1.3.1 최종 hook/본문/CTA를 프로덕션 확정본으로 재확인하고 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: IG-007_copy_signoff.md
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 hook/body/cta가 존재함
- definition_of_done: hook/본문/CTA가 완결된 문장이며 해시태그 정책(무해시태그) 준수를 재확인
- acceptance_checks: ['hook/body 존재 확인', '해시태그 미포함 확인', 'CTA 1개 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### IG-009-WO-01 -- IG-009 직장인 점심시간 활용법
- task_goal: V1.3.1 최종 hook/본문/CTA를 프로덕션 확정본으로 재확인하고 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: IG-009_copy_signoff.md
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 hook/body/cta가 존재함
- definition_of_done: hook/본문/CTA가 완결된 문장이며 해시태그 정책(무해시태그) 준수를 재확인
- acceptance_checks: ['hook/body 존재 확인', '해시태그 미포함 확인', 'CTA 1개 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### IG-013-WO-01 -- IG-013 자기계발 습관 만들기 팁
- task_goal: V1.3.1 최종 hook/본문/CTA를 프로덕션 확정본으로 재확인하고 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: IG-013_copy_signoff.md
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 hook/body/cta가 존재함
- definition_of_done: hook/본문/CTA가 완결된 문장이며 해시태그 정책(무해시태그) 준수를 재확인
- acceptance_checks: ['hook/body 존재 확인', '해시태그 미포함 확인', 'CTA 1개 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### KN-008-WO-01 -- KN-008 시간관리 매트릭스 활용법
- task_goal: V1.3.1 최종 4장 설명 문안을 프로덕션 확정본으로 재확인하고 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: KN-008_copy_signoff.md
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장 문안이 존재함
- definition_of_done: 4장 문장이 완결되고 특정 인물/연구 귀속 주장이 없음을 재확인
- acceptance_checks: ['4장 존재 확인', '역사적 인물 귀속 문구 부재 확인', 'CTA 1개 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### KN-007-WO-01 -- KN-007 회의록 작성 기본기
- task_goal: V1.3.1 최종 4장 설명 문안을 프로덕션 확정본으로 재확인하고 서명한다.
- upstream_inputs: ['PRODUCTION_BATCH_V1_3_1.json', 'EVIDENCE_RED_TEAM_V1_3_1.md']
- exclusive_output: KN-007_copy_signoff.md
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장 문안이 존재함
- definition_of_done: 4장 문장이 완결되고 특정 인물/연구 귀속 주장이 없음을 재확인
- acceptance_checks: ['4장 존재 확인', '역사적 인물 귀속 문구 부재 확인', 'CTA 1개 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

## Evidence·Rights (12 work orders)

### CN-013-WO-02 -- CN-013 반려동물 첫 입양 준비물
- task_goal: RIGHTS_INTAKE_TEMPLATE.json 양식을 사용해 이미지 사용 경로(자체 촬영/생성 배경/라이선스)를 확정하고 attribution 필요 여부를 재확인한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json', 'PRODUCTION_BATCH_V1_3_1.json']
- exclusive_output: CN-013_rights_intake.json (완료된 intake 레코드)
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', "실제 이미지 라이선스를 확보하지 않은 채 '확보됨'으로 표기"]
- definition_of_ready: 해당 content_id의 evidence_status/rights_status가 V1.3.1에 명시되어 있음
- definition_of_done: 이미지 사용 경로가 자체 촬영/CardNewsModule fallback/라이선스 확보 중 하나로 확정되고, 미확정 항목은 명시적 placeholder로 남음
- acceptance_checks: ['rights_intake 레코드의 모든 필드가 null 또는 허용된 placeholder 토큰인지 확인', 'attribution_required 판단이 evidence_status와 일치하는지 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### CN-014-WO-02 -- CN-014 캠핑 초보 준비물 체크리스트
- task_goal: RIGHTS_INTAKE_TEMPLATE.json 양식을 사용해 이미지 사용 경로(자체 촬영/생성 배경/라이선스)를 확정하고 attribution 필요 여부를 재확인한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json', 'PRODUCTION_BATCH_V1_3_1.json']
- exclusive_output: CN-014_rights_intake.json (완료된 intake 레코드)
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', "실제 이미지 라이선스를 확보하지 않은 채 '확보됨'으로 표기"]
- definition_of_ready: 해당 content_id의 evidence_status/rights_status가 V1.3.1에 명시되어 있음
- definition_of_done: 이미지 사용 경로가 자체 촬영/CardNewsModule fallback/라이선스 확보 중 하나로 확정되고, 미확정 항목은 명시적 placeholder로 남음
- acceptance_checks: ['rights_intake 레코드의 모든 필드가 null 또는 허용된 placeholder 토큰인지 확인', 'attribution_required 판단이 evidence_status와 일치하는지 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### CN-016-WO-02 -- CN-016 여행 전 짐싸기 체크리스트
- task_goal: RIGHTS_INTAKE_TEMPLATE.json 양식을 사용해 이미지 사용 경로(자체 촬영/생성 배경/라이선스)를 확정하고 attribution 필요 여부를 재확인한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json', 'PRODUCTION_BATCH_V1_3_1.json']
- exclusive_output: CN-016_rights_intake.json (완료된 intake 레코드)
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', "실제 이미지 라이선스를 확보하지 않은 채 '확보됨'으로 표기"]
- definition_of_ready: 해당 content_id의 evidence_status/rights_status가 V1.3.1에 명시되어 있음
- definition_of_done: 이미지 사용 경로가 자체 촬영/CardNewsModule fallback/라이선스 확보 중 하나로 확정되고, 미확정 항목은 명시적 placeholder로 남음
- acceptance_checks: ['rights_intake 레코드의 모든 필드가 null 또는 허용된 placeholder 토큰인지 확인', 'attribution_required 판단이 evidence_status와 일치하는지 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### CN-017-WO-02 -- CN-017 커피 원두 보관법
- task_goal: RIGHTS_INTAKE_TEMPLATE.json 양식을 사용해 이미지 사용 경로(자체 촬영/생성 배경/라이선스)를 확정하고 attribution 필요 여부를 재확인한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json', 'PRODUCTION_BATCH_V1_3_1.json']
- exclusive_output: CN-017_rights_intake.json (완료된 intake 레코드)
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', "실제 이미지 라이선스를 확보하지 않은 채 '확보됨'으로 표기"]
- definition_of_ready: 해당 content_id의 evidence_status/rights_status가 V1.3.1에 명시되어 있음
- definition_of_done: 이미지 사용 경로가 자체 촬영/CardNewsModule fallback/라이선스 확보 중 하나로 확정되고, 미확정 항목은 명시적 placeholder로 남음
- acceptance_checks: ['rights_intake 레코드의 모든 필드가 null 또는 허용된 placeholder 토큰인지 확인', 'attribution_required 판단이 evidence_status와 일치하는지 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### SH-017-WO-02 -- SH-017 반려동물 산책 준비물 점검
- task_goal: 촬영 예정 소재(반려동물/원두/캐리어 등)의 소유권 및 제3자 동의 필요 여부를 RIGHTS_INTAKE_TEMPLATE.json으로 확인한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json']
- exclusive_output: SH-017_rights_intake.json
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '실제 촬영 없이 소유권을 확보됨으로 표기']
- definition_of_ready: manual_assets_needed 목록이 V1.3.1에 명시되어 있음
- definition_of_done: 촬영 소재 소유권/동의 상태가 확정되거나 명시적 placeholder로 남음
- acceptance_checks: ['manual_assets_needed 각 항목에 대한 소유권 확인 상태 기록 여부']
- blocker_codes: 없음
- next_handoff_target: Shorts
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### SH-006-WO-02 -- SH-006 커피 내리는 법 3단계
- task_goal: 촬영 예정 소재(반려동물/원두/캐리어 등)의 소유권 및 제3자 동의 필요 여부를 RIGHTS_INTAKE_TEMPLATE.json으로 확인한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json']
- exclusive_output: SH-006_rights_intake.json
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '실제 촬영 없이 소유권을 확보됨으로 표기']
- definition_of_ready: manual_assets_needed 목록이 V1.3.1에 명시되어 있음
- definition_of_done: 촬영 소재 소유권/동의 상태가 확정되거나 명시적 placeholder로 남음
- acceptance_checks: ['manual_assets_needed 각 항목에 대한 소유권 확인 상태 기록 여부']
- blocker_codes: 없음
- next_handoff_target: Shorts
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### SH-018-WO-02 -- SH-018 캐리어 짐싸기 순서
- task_goal: 촬영 예정 소재(반려동물/원두/캐리어 등)의 소유권 및 제3자 동의 필요 여부를 RIGHTS_INTAKE_TEMPLATE.json으로 확인한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json']
- exclusive_output: SH-018_rights_intake.json
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '실제 촬영 없이 소유권을 확보됨으로 표기']
- definition_of_ready: manual_assets_needed 목록이 V1.3.1에 명시되어 있음
- definition_of_done: 촬영 소재 소유권/동의 상태가 확정되거나 명시적 placeholder로 남음
- acceptance_checks: ['manual_assets_needed 각 항목에 대한 소유권 확인 상태 기록 여부']
- blocker_codes: 없음
- next_handoff_target: Shorts
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### IG-007-WO-02 -- IG-007 문화생활 예산 관리 팁
- task_goal: 이미지 사용 경로(자체 제작 카드 배경/자체 촬영)를 확정하고 attribution 필요 여부를 재확인한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json']
- exclusive_output: IG-007_rights_intake.json
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: evidence_status/rights_status가 V1.3.1에 명시되어 있음
- definition_of_done: 이미지 사용 경로가 확정되거나 명시적 placeholder로 남음
- acceptance_checks: ['rights_intake 레코드 필드가 null 또는 허용된 placeholder인지 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### IG-009-WO-02 -- IG-009 직장인 점심시간 활용법
- task_goal: 이미지 사용 경로(자체 제작 카드 배경/자체 촬영)를 확정하고 attribution 필요 여부를 재확인한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json']
- exclusive_output: IG-009_rights_intake.json
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: evidence_status/rights_status가 V1.3.1에 명시되어 있음
- definition_of_done: 이미지 사용 경로가 확정되거나 명시적 placeholder로 남음
- acceptance_checks: ['rights_intake 레코드 필드가 null 또는 허용된 placeholder인지 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### IG-013-WO-02 -- IG-013 자기계발 습관 만들기 팁
- task_goal: 이미지 사용 경로(자체 제작 카드 배경/자체 촬영)를 확정하고 attribution 필요 여부를 재확인한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json']
- exclusive_output: IG-013_rights_intake.json
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: evidence_status/rights_status가 V1.3.1에 명시되어 있음
- definition_of_done: 이미지 사용 경로가 확정되거나 명시적 placeholder로 남음
- acceptance_checks: ['rights_intake 레코드 필드가 null 또는 허용된 placeholder인지 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### KN-008-WO-02 -- KN-008 시간관리 매트릭스 활용법
- task_goal: 이미지 사용 경로(자체 제작 인포그래픽)를 확정한다. evidence_not_required_reason이 null인 항목(KN-008)은 별도 검토 필요로 표시한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json']
- exclusive_output: KN-008_rights_intake.json
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: evidence_status가 V1.3.1에 명시되어 있음
- definition_of_done: 이미지 사용 경로가 확정되거나 명시적 placeholder로 남음; evidence_not_required_reason이 null인 항목은 CTO/리뷰어 확인 대기로 명시
- acceptance_checks: ['rights_intake 레코드 필드 확인', 'evidence_not_required_reason null 항목에 대한 추가 검토 플래그 확인']
- blocker_codes: ['EVIDENCE_REVIEW_PENDING']
- next_handoff_target: 레이아웃·타이포
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### KN-007-WO-02 -- KN-007 회의록 작성 기본기
- task_goal: 이미지 사용 경로(자체 제작 인포그래픽)를 확정한다. evidence_not_required_reason이 null인 항목(KN-008)은 별도 검토 필요로 표시한다.
- upstream_inputs: ['RIGHTS_INTAKE_TEMPLATE.json', 'TOP20_EVIDENCE_PACK.json']
- exclusive_output: KN-007_rights_intake.json
- read_only_references: ['EVIDENCE_RED_TEAM_V1_3_1.md']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: evidence_status가 V1.3.1에 명시되어 있음
- definition_of_done: 이미지 사용 경로가 확정되거나 명시적 placeholder로 남음; evidence_not_required_reason이 null인 항목은 CTO/리뷰어 확인 대기로 명시
- acceptance_checks: ['rights_intake 레코드 필드 확인', 'evidence_not_required_reason null 항목에 대한 추가 검토 플래그 확인']
- blocker_codes: 없음
- next_handoff_target: 레이아웃·타이포
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

## 레이아웃·타이포 (9 work orders)

### CN-013-WO-03 -- CN-013 반려동물 첫 입양 준비물
- task_goal: 4장 슬라이드의 레이아웃 초안(기존 CardNewsModule 10개 레이아웃 중 선택)과 타이포그래피 계획(제목/본문 크기, 안전 여백)을 준비한다.
- upstream_inputs: ['CN-013_copy_signoff.md', 'CN-013_rights_intake.json']
- exclusive_output: CN-013_layout_plan.md (레이아웃/타이포 초안)
- read_only_references: ['templates/card_news_layout_rules.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '11번째 레이아웃 신규 추가', 'CardNewsModule 코드 수정']
- definition_of_ready: 문안 서명 및 이미지 경로가 확정됨
- definition_of_done: 각 슬라이드에 대해 레이아웃 유형, 텍스트 위계, 이미지 배치, 안전 여백 계획이 문서화됨 -- 실제 렌더링은 수행하지 않음
- acceptance_checks: ['4장 모두 레이아웃 유형이 지정되었는지 확인', '안전 여백 기준 명시 확인']
- blocker_codes: 없음
- next_handoff_target: 렌더링·산출물 (07/08 receipt 이슈 해결 전까지 queued)
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

### CN-014-WO-03 -- CN-014 캠핑 초보 준비물 체크리스트
- task_goal: 4장 슬라이드의 레이아웃 초안(기존 CardNewsModule 10개 레이아웃 중 선택)과 타이포그래피 계획(제목/본문 크기, 안전 여백)을 준비한다.
- upstream_inputs: ['CN-014_copy_signoff.md', 'CN-014_rights_intake.json']
- exclusive_output: CN-014_layout_plan.md (레이아웃/타이포 초안)
- read_only_references: ['templates/card_news_layout_rules.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '11번째 레이아웃 신규 추가', 'CardNewsModule 코드 수정']
- definition_of_ready: 문안 서명 및 이미지 경로가 확정됨
- definition_of_done: 각 슬라이드에 대해 레이아웃 유형, 텍스트 위계, 이미지 배치, 안전 여백 계획이 문서화됨 -- 실제 렌더링은 수행하지 않음
- acceptance_checks: ['4장 모두 레이아웃 유형이 지정되었는지 확인', '안전 여백 기준 명시 확인']
- blocker_codes: 없음
- next_handoff_target: 렌더링·산출물 (07/08 receipt 이슈 해결 전까지 queued)
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

### CN-016-WO-03 -- CN-016 여행 전 짐싸기 체크리스트
- task_goal: 4장 슬라이드의 레이아웃 초안(기존 CardNewsModule 10개 레이아웃 중 선택)과 타이포그래피 계획(제목/본문 크기, 안전 여백)을 준비한다.
- upstream_inputs: ['CN-016_copy_signoff.md', 'CN-016_rights_intake.json']
- exclusive_output: CN-016_layout_plan.md (레이아웃/타이포 초안)
- read_only_references: ['templates/card_news_layout_rules.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '11번째 레이아웃 신규 추가', 'CardNewsModule 코드 수정']
- definition_of_ready: 문안 서명 및 이미지 경로가 확정됨
- definition_of_done: 각 슬라이드에 대해 레이아웃 유형, 텍스트 위계, 이미지 배치, 안전 여백 계획이 문서화됨 -- 실제 렌더링은 수행하지 않음
- acceptance_checks: ['4장 모두 레이아웃 유형이 지정되었는지 확인', '안전 여백 기준 명시 확인']
- blocker_codes: 없음
- next_handoff_target: 렌더링·산출물 (07/08 receipt 이슈 해결 전까지 queued)
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

### CN-017-WO-03 -- CN-017 커피 원두 보관법
- task_goal: 4장 슬라이드의 레이아웃 초안(기존 CardNewsModule 10개 레이아웃 중 선택)과 타이포그래피 계획(제목/본문 크기, 안전 여백)을 준비한다.
- upstream_inputs: ['CN-017_copy_signoff.md', 'CN-017_rights_intake.json']
- exclusive_output: CN-017_layout_plan.md (레이아웃/타이포 초안)
- read_only_references: ['templates/card_news_layout_rules.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '11번째 레이아웃 신규 추가', 'CardNewsModule 코드 수정']
- definition_of_ready: 문안 서명 및 이미지 경로가 확정됨
- definition_of_done: 각 슬라이드에 대해 레이아웃 유형, 텍스트 위계, 이미지 배치, 안전 여백 계획이 문서화됨 -- 실제 렌더링은 수행하지 않음
- acceptance_checks: ['4장 모두 레이아웃 유형이 지정되었는지 확인', '안전 여백 기준 명시 확인']
- blocker_codes: 없음
- next_handoff_target: 렌더링·산출물 (07/08 receipt 이슈 해결 전까지 queued)
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

### IG-007-WO-03 -- IG-007 문화생활 예산 관리 팁
- task_goal: 정보 요약형 카드 배경 또는 단일 피드 이미지의 레이아웃/타이포 초안을 준비한다.
- upstream_inputs: ['IG-007_copy_signoff.md', 'IG-007_rights_intake.json']
- exclusive_output: IG-007_layout_plan.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: 문안 서명 및 이미지 경로가 확정됨
- definition_of_done: 텍스트 삽입 여백을 포함한 카드 레이아웃 계획이 문서화됨
- acceptance_checks: ['텍스트 삽입 여백 명시 확인']
- blocker_codes: 없음
- next_handoff_target: Instagram·Intelligence
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

### IG-009-WO-03 -- IG-009 직장인 점심시간 활용법
- task_goal: 정보 요약형 카드 배경 또는 단일 피드 이미지의 레이아웃/타이포 초안을 준비한다.
- upstream_inputs: ['IG-009_copy_signoff.md', 'IG-009_rights_intake.json']
- exclusive_output: IG-009_layout_plan.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: 문안 서명 및 이미지 경로가 확정됨
- definition_of_done: 텍스트 삽입 여백을 포함한 카드 레이아웃 계획이 문서화됨
- acceptance_checks: ['텍스트 삽입 여백 명시 확인']
- blocker_codes: 없음
- next_handoff_target: Instagram·Intelligence
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

### IG-013-WO-03 -- IG-013 자기계발 습관 만들기 팁
- task_goal: 정보 요약형 카드 배경 또는 단일 피드 이미지의 레이아웃/타이포 초안을 준비한다.
- upstream_inputs: ['IG-013_copy_signoff.md', 'IG-013_rights_intake.json']
- exclusive_output: IG-013_layout_plan.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: 문안 서명 및 이미지 경로가 확정됨
- definition_of_done: 텍스트 삽입 여백을 포함한 카드 레이아웃 계획이 문서화됨
- acceptance_checks: ['텍스트 삽입 여백 명시 확인']
- blocker_codes: 없음
- next_handoff_target: Instagram·Intelligence
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

### KN-008-WO-03 -- KN-008 시간관리 매트릭스 활용법
- task_goal: 인포그래픽 스타일 카드의 레이아웃/타이포 초안을 준비한다.
- upstream_inputs: ['KN-008_copy_signoff.md', 'KN-008_rights_intake.json']
- exclusive_output: KN-008_layout_plan.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: 문안 서명 및 이미지 경로가 확정됨
- definition_of_done: 인포그래픽 레이아웃 계획이 문서화됨
- acceptance_checks: ['텍스트 위계 명시 확인']
- blocker_codes: 없음
- next_handoff_target: Knowledge·Learning
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

### KN-007-WO-03 -- KN-007 회의록 작성 기본기
- task_goal: 인포그래픽 스타일 카드의 레이아웃/타이포 초안을 준비한다.
- upstream_inputs: ['KN-007_copy_signoff.md', 'KN-007_rights_intake.json']
- exclusive_output: KN-007_layout_plan.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: 문안 서명 및 이미지 경로가 확정됨
- definition_of_done: 인포그래픽 레이아웃 계획이 문서화됨
- acceptance_checks: ['텍스트 위계 명시 확인']
- blocker_codes: 없음
- next_handoff_target: Knowledge·Learning
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

## 렌더링·산출물 (4 work orders)

### CN-013-WO-04 -- CN-013 반려동물 첫 입양 준비물
- task_goal: 레이아웃 계획을 CardNewsModule Pillow 렌더러로 실제 4장 PNG를 생성한다.
- upstream_inputs: ['CN-013_layout_plan.md', 'CN-013_rights_intake.json']
- exclusive_output: CN-013_render_output.png x4 (미실행)
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '07/08 receipt 이슈를 우회하거나 임시 처리로 강제 실행', 'workflow_results/07,08 파일을 직접 수정']
- definition_of_ready: 07/08 workflow_results receipt false-ready 이슈(tests/test_workflow_card_news_output_receipts.py 대상)가 담당 팀에 의해 해결되어 CardNewsModule 렌더 경로가 신뢰 가능한 상태가 됨
- definition_of_done: N/A -- 이 작업지시는 상위 블로커 해소 전까지 시작하지 않음
- acceptance_checks: ['07/08 receipt 이슈 해결 여부를 Common Engine/CardNews 담당 팀에 확인']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: 독립 QA (동일하게 queued)
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### CN-014-WO-04 -- CN-014 캠핑 초보 준비물 체크리스트
- task_goal: 레이아웃 계획을 CardNewsModule Pillow 렌더러로 실제 4장 PNG를 생성한다.
- upstream_inputs: ['CN-014_layout_plan.md', 'CN-014_rights_intake.json']
- exclusive_output: CN-014_render_output.png x4 (미실행)
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '07/08 receipt 이슈를 우회하거나 임시 처리로 강제 실행', 'workflow_results/07,08 파일을 직접 수정']
- definition_of_ready: 07/08 workflow_results receipt false-ready 이슈(tests/test_workflow_card_news_output_receipts.py 대상)가 담당 팀에 의해 해결되어 CardNewsModule 렌더 경로가 신뢰 가능한 상태가 됨
- definition_of_done: N/A -- 이 작업지시는 상위 블로커 해소 전까지 시작하지 않음
- acceptance_checks: ['07/08 receipt 이슈 해결 여부를 Common Engine/CardNews 담당 팀에 확인']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: 독립 QA (동일하게 queued)
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### CN-016-WO-04 -- CN-016 여행 전 짐싸기 체크리스트
- task_goal: 레이아웃 계획을 CardNewsModule Pillow 렌더러로 실제 4장 PNG를 생성한다.
- upstream_inputs: ['CN-016_layout_plan.md', 'CN-016_rights_intake.json']
- exclusive_output: CN-016_render_output.png x4 (미실행)
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '07/08 receipt 이슈를 우회하거나 임시 처리로 강제 실행', 'workflow_results/07,08 파일을 직접 수정']
- definition_of_ready: 07/08 workflow_results receipt false-ready 이슈(tests/test_workflow_card_news_output_receipts.py 대상)가 담당 팀에 의해 해결되어 CardNewsModule 렌더 경로가 신뢰 가능한 상태가 됨
- definition_of_done: N/A -- 이 작업지시는 상위 블로커 해소 전까지 시작하지 않음
- acceptance_checks: ['07/08 receipt 이슈 해결 여부를 Common Engine/CardNews 담당 팀에 확인']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: 독립 QA (동일하게 queued)
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### CN-017-WO-04 -- CN-017 커피 원두 보관법
- task_goal: 레이아웃 계획을 CardNewsModule Pillow 렌더러로 실제 4장 PNG를 생성한다.
- upstream_inputs: ['CN-017_layout_plan.md', 'CN-017_rights_intake.json']
- exclusive_output: CN-017_render_output.png x4 (미실행)
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '07/08 receipt 이슈를 우회하거나 임시 처리로 강제 실행', 'workflow_results/07,08 파일을 직접 수정']
- definition_of_ready: 07/08 workflow_results receipt false-ready 이슈(tests/test_workflow_card_news_output_receipts.py 대상)가 담당 팀에 의해 해결되어 CardNewsModule 렌더 경로가 신뢰 가능한 상태가 됨
- definition_of_done: N/A -- 이 작업지시는 상위 블로커 해소 전까지 시작하지 않음
- acceptance_checks: ['07/08 receipt 이슈 해결 여부를 Common Engine/CardNews 담당 팀에 확인']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: 독립 QA (동일하게 queued)
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

## 패키징·게시인계 (12 work orders)

### CN-013-WO-06 -- CN-013 반려동물 첫 입양 준비물
- task_goal: 독립 QA를 통과한 산출물을 게시 준비 패키지(캡션/해시태그/발행 큐 항목)로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['CN-013_qa_report.md']
- exclusive_output: CN-013_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정', '실제 발행 큐에 등록']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: N/A -- 상위 작업지시가 완료되기 전까지 시작하지 않음
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### CN-014-WO-06 -- CN-014 캠핑 초보 준비물 체크리스트
- task_goal: 독립 QA를 통과한 산출물을 게시 준비 패키지(캡션/해시태그/발행 큐 항목)로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['CN-014_qa_report.md']
- exclusive_output: CN-014_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정', '실제 발행 큐에 등록']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: N/A -- 상위 작업지시가 완료되기 전까지 시작하지 않음
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### CN-016-WO-06 -- CN-016 여행 전 짐싸기 체크리스트
- task_goal: 독립 QA를 통과한 산출물을 게시 준비 패키지(캡션/해시태그/발행 큐 항목)로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['CN-016_qa_report.md']
- exclusive_output: CN-016_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정', '실제 발행 큐에 등록']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: N/A -- 상위 작업지시가 완료되기 전까지 시작하지 않음
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### CN-017-WO-06 -- CN-017 커피 원두 보관법
- task_goal: 독립 QA를 통과한 산출물을 게시 준비 패키지(캡션/해시태그/발행 큐 항목)로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['CN-017_qa_report.md']
- exclusive_output: CN-017_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정', '실제 발행 큐에 등록']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: N/A -- 상위 작업지시가 완료되기 전까지 시작하지 않음
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### SH-017-WO-05 -- SH-017 반려동물 산책 준비물 점검
- task_goal: QA를 통과한 영상을 게시 준비 패키지로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['SH-017_qa_report.md']
- exclusive_output: SH-017_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: 게시 준비 메타데이터가 구성되고 publish_ready/actual_publish가 false로 유지됨
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: 없음
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

### SH-006-WO-05 -- SH-006 커피 내리는 법 3단계
- task_goal: QA를 통과한 영상을 게시 준비 패키지로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['SH-006_qa_report.md']
- exclusive_output: SH-006_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: 게시 준비 메타데이터가 구성되고 publish_ready/actual_publish가 false로 유지됨
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: 없음
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

### SH-018-WO-05 -- SH-018 캐리어 짐싸기 순서
- task_goal: QA를 통과한 영상을 게시 준비 패키지로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['SH-018_qa_report.md']
- exclusive_output: SH-018_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: 게시 준비 메타데이터가 구성되고 publish_ready/actual_publish가 false로 유지됨
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: 없음
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

### IG-007-WO-06 -- IG-007 문화생활 예산 관리 팁
- task_goal: QA를 통과한 카드/캡션을 게시 준비 패키지로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['IG-007_qa_report.md']
- exclusive_output: IG-007_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: 게시 준비 메타데이터가 구성되고 publish_ready/actual_publish가 false로 유지됨
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: 없음
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

### IG-009-WO-06 -- IG-009 직장인 점심시간 활용법
- task_goal: QA를 통과한 카드/캡션을 게시 준비 패키지로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['IG-009_qa_report.md']
- exclusive_output: IG-009_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: 게시 준비 메타데이터가 구성되고 publish_ready/actual_publish가 false로 유지됨
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: 없음
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

### IG-013-WO-06 -- IG-013 자기계발 습관 만들기 팁
- task_goal: QA를 통과한 카드/캡션을 게시 준비 패키지로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['IG-013_qa_report.md']
- exclusive_output: IG-013_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: 게시 준비 메타데이터가 구성되고 publish_ready/actual_publish가 false로 유지됨
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: 없음
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

### KN-008-WO-06 -- KN-008 시간관리 매트릭스 활용법
- task_goal: QA를 통과한 카드를 게시 준비 패키지로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['KN-008_qa_report.md']
- exclusive_output: KN-008_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: 게시 준비 메타데이터가 구성되고 publish_ready/actual_publish가 false로 유지됨
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: 없음
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

### KN-007-WO-06 -- KN-007 회의록 작성 기본기
- task_goal: QA를 통과한 카드를 게시 준비 패키지로 포장하되, 실제 게시는 수행하지 않는다.
- upstream_inputs: ['KN-007_qa_report.md']
- exclusive_output: KN-007_publish_package.json (publish_ready=false 고정)
- read_only_references: ['config/publishing.json (읽기 전용, 수정 금지)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'publish_ready 또는 actual_publish를 true로 설정']
- definition_of_ready: 독립 QA가 통과 상태로 완료됨
- definition_of_done: 게시 준비 메타데이터가 구성되고 publish_ready/actual_publish가 false로 유지됨
- acceptance_checks: ['publish_ready == false 확인', 'actual_publish == false 확인']
- blocker_codes: 없음
- next_handoff_target: (외부) 실제 게시 승인 -- 이 패키지 범위 밖
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

## 독립 QA (12 work orders)

### CN-013-WO-05 -- CN-013 반려동물 첫 입양 준비물
- task_goal: 렌더링된 4장 PNG를 대상으로 가독성, 안전 여백, 텍스트 잘림, 문안-이미지 일치를 독립적으로 검수한다.
- upstream_inputs: ['CN-013_render_output.png x4']
- exclusive_output: CN-013_qa_report.md (독립 QA 결과)
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '렌더링되지 않은 자산에 대해 QA 통과 처리']
- definition_of_ready: 렌더링된 4장 PNG가 실제로 존재함
- definition_of_done: N/A -- 렌더링 작업지시가 완료되기 전까지 시작하지 않음
- acceptance_checks: ['렌더된 PNG 4장 존재 확인 후 시각 검수']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: 패키징·게시인계 (동일하게 queued)
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### CN-014-WO-05 -- CN-014 캠핑 초보 준비물 체크리스트
- task_goal: 렌더링된 4장 PNG를 대상으로 가독성, 안전 여백, 텍스트 잘림, 문안-이미지 일치를 독립적으로 검수한다.
- upstream_inputs: ['CN-014_render_output.png x4']
- exclusive_output: CN-014_qa_report.md (독립 QA 결과)
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '렌더링되지 않은 자산에 대해 QA 통과 처리']
- definition_of_ready: 렌더링된 4장 PNG가 실제로 존재함
- definition_of_done: N/A -- 렌더링 작업지시가 완료되기 전까지 시작하지 않음
- acceptance_checks: ['렌더된 PNG 4장 존재 확인 후 시각 검수']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: 패키징·게시인계 (동일하게 queued)
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### CN-016-WO-05 -- CN-016 여행 전 짐싸기 체크리스트
- task_goal: 렌더링된 4장 PNG를 대상으로 가독성, 안전 여백, 텍스트 잘림, 문안-이미지 일치를 독립적으로 검수한다.
- upstream_inputs: ['CN-016_render_output.png x4']
- exclusive_output: CN-016_qa_report.md (독립 QA 결과)
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '렌더링되지 않은 자산에 대해 QA 통과 처리']
- definition_of_ready: 렌더링된 4장 PNG가 실제로 존재함
- definition_of_done: N/A -- 렌더링 작업지시가 완료되기 전까지 시작하지 않음
- acceptance_checks: ['렌더된 PNG 4장 존재 확인 후 시각 검수']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: 패키징·게시인계 (동일하게 queued)
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### CN-017-WO-05 -- CN-017 커피 원두 보관법
- task_goal: 렌더링된 4장 PNG를 대상으로 가독성, 안전 여백, 텍스트 잘림, 문안-이미지 일치를 독립적으로 검수한다.
- upstream_inputs: ['CN-017_render_output.png x4']
- exclusive_output: CN-017_qa_report.md (독립 QA 결과)
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '렌더링되지 않은 자산에 대해 QA 통과 처리']
- definition_of_ready: 렌더링된 4장 PNG가 실제로 존재함
- definition_of_done: N/A -- 렌더링 작업지시가 완료되기 전까지 시작하지 않음
- acceptance_checks: ['렌더된 PNG 4장 존재 확인 후 시각 검수']
- blocker_codes: ['CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED']
- next_handoff_target: 패키징·게시인계 (동일하게 queued)
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### SH-017-WO-04 -- SH-017 반려동물 산책 준비물 점검
- task_goal: 편집된 영상이 스크립트와 일치하는지, 미검증 수치/효과 주장이 삽입되지 않았는지 독립 검수한다.
- upstream_inputs: ['SH-017_edited_clip.mp4']
- exclusive_output: SH-017_qa_report.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '편집되지 않은 자산에 대해 QA 통과 처리']
- definition_of_ready: 편집된 영상이 실제로 존재함
- definition_of_done: 스크립트 일치 및 자막 내 미검증 수치 부재를 확인
- acceptance_checks: ['자막에 실제 성과/수치가 삽입되지 않았는지 확인']
- blocker_codes: 없음
- next_handoff_target: 패키징·게시인계
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### SH-006-WO-04 -- SH-006 커피 내리는 법 3단계
- task_goal: 편집된 영상이 스크립트와 일치하는지, 미검증 수치/효과 주장이 삽입되지 않았는지 독립 검수한다.
- upstream_inputs: ['SH-006_edited_clip.mp4']
- exclusive_output: SH-006_qa_report.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '편집되지 않은 자산에 대해 QA 통과 처리']
- definition_of_ready: 편집된 영상이 실제로 존재함
- definition_of_done: 스크립트 일치 및 자막 내 미검증 수치 부재를 확인
- acceptance_checks: ['자막에 실제 성과/수치가 삽입되지 않았는지 확인']
- blocker_codes: 없음
- next_handoff_target: 패키징·게시인계
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### SH-018-WO-04 -- SH-018 캐리어 짐싸기 순서
- task_goal: 편집된 영상이 스크립트와 일치하는지, 미검증 수치/효과 주장이 삽입되지 않았는지 독립 검수한다.
- upstream_inputs: ['SH-018_edited_clip.mp4']
- exclusive_output: SH-018_qa_report.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '편집되지 않은 자산에 대해 QA 통과 처리']
- definition_of_ready: 편집된 영상이 실제로 존재함
- definition_of_done: 스크립트 일치 및 자막 내 미검증 수치 부재를 확인
- acceptance_checks: ['자막에 실제 성과/수치가 삽입되지 않았는지 확인']
- blocker_codes: 없음
- next_handoff_target: 패키징·게시인계
- parallel_executable: False | critical_path: True
- publish_ready: False / actual_publish: False

### IG-007-WO-05 -- IG-007 문화생활 예산 관리 팁
- task_goal: 최종 카드/캡션이 근거·권리·해시태그 정책을 준수하는지 독립 검수한다.
- upstream_inputs: ['IG-007_ig_prep_note.md']
- exclusive_output: IG-007_qa_report.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: Instagram Intelligence Prep이 완료됨
- definition_of_done: 근거 없는 해시태그/성과 주장이 없음을 확인
- acceptance_checks: ['해시태그 정책 준수 재확인', 'hook/body 완결성 재확인']
- blocker_codes: 없음
- next_handoff_target: 패키징·게시인계
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

### IG-009-WO-05 -- IG-009 직장인 점심시간 활용법
- task_goal: 최종 카드/캡션이 근거·권리·해시태그 정책을 준수하는지 독립 검수한다.
- upstream_inputs: ['IG-009_ig_prep_note.md']
- exclusive_output: IG-009_qa_report.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: Instagram Intelligence Prep이 완료됨
- definition_of_done: 근거 없는 해시태그/성과 주장이 없음을 확인
- acceptance_checks: ['해시태그 정책 준수 재확인', 'hook/body 완결성 재확인']
- blocker_codes: 없음
- next_handoff_target: 패키징·게시인계
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

### IG-013-WO-05 -- IG-013 자기계발 습관 만들기 팁
- task_goal: 최종 카드/캡션이 근거·권리·해시태그 정책을 준수하는지 독립 검수한다.
- upstream_inputs: ['IG-013_ig_prep_note.md']
- exclusive_output: IG-013_qa_report.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: Instagram Intelligence Prep이 완료됨
- definition_of_done: 근거 없는 해시태그/성과 주장이 없음을 확인
- acceptance_checks: ['해시태그 정책 준수 재확인', 'hook/body 완결성 재확인']
- blocker_codes: 없음
- next_handoff_target: 패키징·게시인계
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

### KN-008-WO-05 -- KN-008 시간관리 매트릭스 활용법
- task_goal: 최종 카드 문안이 역사적 귀속/효과 주장 없이 정확한지 독립 검수한다.
- upstream_inputs: ['KN-008_knowledge_note.md']
- exclusive_output: KN-008_qa_report.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: Knowledge/Learning Integration 검토가 완료됨
- definition_of_done: 역사적 인물 귀속·효과 단정 문장이 없음을 확인
- acceptance_checks: ['역사적 귀속 문구 부재 재확인', '효과 단정 문구 부재 재확인']
- blocker_codes: 없음
- next_handoff_target: 패키징·게시인계
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

### KN-007-WO-05 -- KN-007 회의록 작성 기본기
- task_goal: 최종 카드 문안이 역사적 귀속/효과 주장 없이 정확한지 독립 검수한다.
- upstream_inputs: ['KN-007_knowledge_note.md']
- exclusive_output: KN-007_qa_report.md
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정']
- definition_of_ready: Knowledge/Learning Integration 검토가 완료됨
- definition_of_done: 역사적 인물 귀속·효과 단정 문장이 없음을 확인
- acceptance_checks: ['역사적 귀속 문구 부재 재확인', '효과 단정 문구 부재 재확인']
- blocker_codes: 없음
- next_handoff_target: 패키징·게시인계
- parallel_executable: False | critical_path: False
- publish_ready: False / actual_publish: False

## Shorts (3 work orders)

### SH-017-WO-03 -- SH-017 반려동물 산책 준비물 점검
- task_goal: 실제 소재를 촬영하고 장면표에 따라 편집한다 (TTS/음악/자동 렌더링 없음, 전부 수동).
- upstream_inputs: ['SH-017_script_signoff.md', 'SH-017_rights_intake.json']
- exclusive_output: SH-017_edited_clip.mp4 (미실행)
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'TTS 자동 생성', '배경음악 자동 삽입', '자동 렌더링 도구로 대체', '실제 업로드']
- definition_of_ready: 촬영 소재 권리 확인이 완료됨
- definition_of_done: 실제 촬영/편집이 완료되고 원본 스크립트와 일치함
- acceptance_checks: ['실제 촬영 여부 확인 (스톡 영상 대체 금지)', '제3자 동의 필요 여부 재확인']
- blocker_codes: 없음
- next_handoff_target: 독립 QA
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### SH-006-WO-03 -- SH-006 커피 내리는 법 3단계
- task_goal: 실제 소재를 촬영하고 장면표에 따라 편집한다 (TTS/음악/자동 렌더링 없음, 전부 수동).
- upstream_inputs: ['SH-006_script_signoff.md', 'SH-006_rights_intake.json']
- exclusive_output: SH-006_edited_clip.mp4 (미실행)
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'TTS 자동 생성', '배경음악 자동 삽입', '자동 렌더링 도구로 대체', '실제 업로드']
- definition_of_ready: 촬영 소재 권리 확인이 완료됨
- definition_of_done: 실제 촬영/편집이 완료되고 원본 스크립트와 일치함
- acceptance_checks: ['실제 촬영 여부 확인 (스톡 영상 대체 금지)', '제3자 동의 필요 여부 재확인']
- blocker_codes: 없음
- next_handoff_target: 독립 QA
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

### SH-018-WO-03 -- SH-018 캐리어 짐싸기 순서
- task_goal: 실제 소재를 촬영하고 장면표에 따라 편집한다 (TTS/음악/자동 렌더링 없음, 전부 수동).
- upstream_inputs: ['SH-018_script_signoff.md', 'SH-018_rights_intake.json']
- exclusive_output: SH-018_edited_clip.mp4 (미실행)
- read_only_references: []
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', 'TTS 자동 생성', '배경음악 자동 삽입', '자동 렌더링 도구로 대체', '실제 업로드']
- definition_of_ready: 촬영 소재 권리 확인이 완료됨
- definition_of_done: 실제 촬영/편집이 완료되고 원본 스크립트와 일치함
- acceptance_checks: ['실제 촬영 여부 확인 (스톡 영상 대체 금지)', '제3자 동의 필요 여부 재확인']
- blocker_codes: 없음
- next_handoff_target: 독립 QA
- parallel_executable: True | critical_path: True
- publish_ready: False / actual_publish: False

## Instagram·Intelligence (3 work orders)

### IG-007-WO-04 -- IG-007 문화생활 예산 관리 팁
- task_goal: 게시 포맷/캡션 길이/내부 quality_score proxy 기준 부합 여부를 확인한다 (실제 Graph API 성과 데이터는 사용하지 않음).
- upstream_inputs: ['IG-007_layout_plan.md']
- exclusive_output: IG-007_ig_prep_note.md
- read_only_references: ['ROADMAP.md의 Instagram Requires External API 섹션 (읽기 전용)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '실제 Instagram 성과 데이터 존재를 가정한 최적화 주장 생성']
- definition_of_ready: 레이아웃 계획이 완료됨
- definition_of_done: 내부 proxy 기준으로만 검토되고 실제 성과 데이터가 없다는 점이 명시됨
- acceptance_checks: ['실제 성과 데이터 미사용 확인']
- blocker_codes: 없음
- next_handoff_target: 독립 QA
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

### IG-009-WO-04 -- IG-009 직장인 점심시간 활용법
- task_goal: 게시 포맷/캡션 길이/내부 quality_score proxy 기준 부합 여부를 확인한다 (실제 Graph API 성과 데이터는 사용하지 않음).
- upstream_inputs: ['IG-009_layout_plan.md']
- exclusive_output: IG-009_ig_prep_note.md
- read_only_references: ['ROADMAP.md의 Instagram Requires External API 섹션 (읽기 전용)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '실제 Instagram 성과 데이터 존재를 가정한 최적화 주장 생성']
- definition_of_ready: 레이아웃 계획이 완료됨
- definition_of_done: 내부 proxy 기준으로만 검토되고 실제 성과 데이터가 없다는 점이 명시됨
- acceptance_checks: ['실제 성과 데이터 미사용 확인']
- blocker_codes: 없음
- next_handoff_target: 독립 QA
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

### IG-013-WO-04 -- IG-013 자기계발 습관 만들기 팁
- task_goal: 게시 포맷/캡션 길이/내부 quality_score proxy 기준 부합 여부를 확인한다 (실제 Graph API 성과 데이터는 사용하지 않음).
- upstream_inputs: ['IG-013_layout_plan.md']
- exclusive_output: IG-013_ig_prep_note.md
- read_only_references: ['ROADMAP.md의 Instagram Requires External API 섹션 (읽기 전용)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '실제 Instagram 성과 데이터 존재를 가정한 최적화 주장 생성']
- definition_of_ready: 레이아웃 계획이 완료됨
- definition_of_done: 내부 proxy 기준으로만 검토되고 실제 성과 데이터가 없다는 점이 명시됨
- acceptance_checks: ['실제 성과 데이터 미사용 확인']
- blocker_codes: 없음
- next_handoff_target: 독립 QA
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

## Knowledge·Learning (2 work orders)

### KN-008-WO-04 -- KN-008 시간관리 매트릭스 활용법
- task_goal: 이 콘텐츠를 Knowledge Engine 패턴 후보(CANDIDATE)로 등록할지 검토한다 -- 실제 성과 데이터 없이는 VERIFIED로 승격하지 않는다.
- upstream_inputs: ['KN-008_layout_plan.md']
- exclusive_output: KN-008_knowledge_note.md
- read_only_references: ['.codex/skills/ai-content-os-knowledge-intelligence/SKILL.md (읽기 전용)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '실제 성과 증거 없이 패턴을 VERIFIED로 승격', 'PatternRegistry.promote() 호출']
- definition_of_ready: 레이아웃 계획이 완료됨
- definition_of_done: CANDIDATE 상태 등록 여부만 검토 기록, 승격은 수행하지 않음
- acceptance_checks: ['승격(promote) 미수행 확인']
- blocker_codes: 없음
- next_handoff_target: 독립 QA
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False

### KN-007-WO-04 -- KN-007 회의록 작성 기본기
- task_goal: 이 콘텐츠를 Knowledge Engine 패턴 후보(CANDIDATE)로 등록할지 검토한다 -- 실제 성과 데이터 없이는 VERIFIED로 승격하지 않는다.
- upstream_inputs: ['KN-007_layout_plan.md']
- exclusive_output: KN-007_knowledge_note.md
- read_only_references: ['.codex/skills/ai-content-os-knowledge-intelligence/SKILL.md (읽기 전용)']
- forbidden_actions: ['실제 API 호출·웹 스크래핑·게시·구매·계정 자동화', 'modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정', 'Git add/commit/push/reset 등 모든 Git 작업', '실제 권리 승인·성과·가격·재고·통계 생성 또는 조작', '실제 담당자 이름·채팅 ID·완료일 임의 지정', '실제 성과 증거 없이 패턴을 VERIFIED로 승격', 'PatternRegistry.promote() 호출']
- definition_of_ready: 레이아웃 계획이 완료됨
- definition_of_done: CANDIDATE 상태 등록 여부만 검토 기록, 승격은 수행하지 않음
- acceptance_checks: ['승격(promote) 미수행 확인']
- blocker_codes: 없음
- next_handoff_target: 독립 QA
- parallel_executable: True | critical_path: False
- publish_ready: False / actual_publish: False
