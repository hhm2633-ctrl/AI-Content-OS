# Rights Intake Red-Team V1.8.1

## Scope

- 대상: `external_workclaude/content_portfolio_v1/RIGHTS_INTAKE_CONTRACT_V1_8.json`
- 재검증 범위: 24개 레코드 + `RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8.json` 8개 fixture 전체
- 추가 산출물: `RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8_1.json`
- 기준일: 2026-07-13

## 재검증 결론

- V1.8 계약 자체는 `cardnews` 16건/`shorts` 3건/`instagram_feed` 3건/`knowledge_evergreen` 2건으로 12개 콘텐츠, 24개 레코드 구성이 맞다.
- 8개 fixture 모두 공통적으로 다음을 점검해야 하는 구조가 보장된다:  
  `publish_ready=False`, `actual_publish=False`, `output_set_id=91a28c88912849b58fa608330a217467` 바인딩, `card_path` 4장 경로 결속.
- 위험도 높은 항목은 **구현 단계(Claude 코드 결합부)에서만** 발생할 수 있는 `false-ready` 계열이다. V1.8 계약 자체는 placeholder 중심의 선제 검증 스냅샷이므로 설계상 미완료 상태가 맞다.

## 공격 검토 포인트 (필드 모순/누락/우회/placeholder 오인)

### 1) Placeholder 오인으로 인한 false-ready 위험 (높음)
- 현재 계약은 `REQUIRED_*` 및 빈 문자열을 정상 placeholder로 허용한다.
- 구현자가 `"값이 존재하면 통과"` 형태로만 검사하면 placeholder를 실제 증빙으로 오인해 `publish_ready`를 열 가능성이 큼.
- 특히 `origin`, `role`, `rights_status`, `source_url`, `rights_evidence`, `topic_relevance`, `authenticity_status`는 V1.8 단계에서 모두 placeholder가 허용되는 값으로 들어오므로, 구현부에서 **명시적 placeholder blocklist/allowed set 검사**가 필수.

### 2) 필드 누락/타입 탈락이 쉬운 지점 (중간)
- `rights_evidence`는 계약에서 객체 타입만 요구되나, 실제 준수 게이트는 `rights_status`·`origin`·`type`·`review` 등 조합을 요구.
- `origin/role/rights_status` 조합은 구현에서 허용값 화이트리스트(예: `{"first_party","user_supplied","approved_external"}` 등)로 다시 강제해야 함.
- `operator_checklist`는 계약에서는 단순 객체이며 true/false를 모두 허용하는 구조처럼 보이지만, 하류 게이트는 특정 키 `source_opened...final_asset_reviewed`가 **모두 bool true**여야 함.

### 3) 경로 결속 우회
- `card_path`에서 `.runs`, `.staging`, 절대경로가 드러나는 fixture가 이미 존재해 탐지가 명시적이다.
- 구현자가 `normalize()`만 수행하고 스킴/루트 바인딩을 누락하면, 레포 내부 경로 검증이 우회될 여지가 있어 `manifest_paths_match` 단게에서 오탐/누락이 발생할 수 있음.

### 4) false-ready/false-blocked 취약 시나리오 (추가)
- **False-ready 후보**
  1. `publish_ready`가 문자열 `"true"`/`1`로 들어왔을 때 truthy로 오인.
  2. `output_set_id`에 공백(`" 91a... "`)이 섞인 값이 들어왔을 때 서로 다른 정규화 경로가 나뉘어 비교.
  3. `rights_evidence`를 문자열이나 다른 타입으로 위장해 타입 검증만 통과하는 구현.
  4. 오탐 방지 규칙을 생략하고 `REQUIRED_*` 토큰을 실제 값으로 분류.
- **False-blocked 후보**
  1. `cardnews` 4장과 `card_path` 갯수는 맞지만 순서(1~4)만 바뀐 경우를 집합 비교로 처리하면 유효해 보이기도 하나, 구현이 리스트 정합성 검사(`card_paths == manifest_paths`)에 의존하면 실제로도 막아야 한다고 결론.
  2. `origin/role/rights_status` 조합이 유효한 조합일 때도 `rights_evidence.reviewed_at` 같은 하위 필드 부재로 과거 게이트 버전이 과도하게 막는지 확인 필요(하향호환 safe path).

## 발견 항목

| 심각도 | 항목 | 설명 | 상태 |
|---|---|---|---|
| 중간 | placeholder를 실제 승인 신호로 오인할 위험 | 계약 설계상 빈칸/`REQUIRED_*` 토큰이 정상 상태임 | **보완 필요 (구현 가드 필수)** |
| 중간 | 타입 약화(권리 증빙 객체 구조) | `rights_evidence` 객체 여부만으로 통과 처리 시 우회 | **보완 필요 (타입+하위키 강제)** |
| 중간 | output_set_id 공백/정규화 차이 | 출력셋 정합성 비교에서 normalize 정책 불일치 시 false-ready 또는 false-blocked | **보완 필요 (동일 정규화 정책 사용)** |
| 낮음 | fixture 내 철자 오인 토큰 존재 | 기존 샘플에 토큰 오기입 유사 표기가 혼입될 가능성 | **추적 필요 (V1.8.1에서는 명시적으로 고지)** |

## 최소 수정 제안 (V1.8 구현 시 반영)

1. `build_rights_intake` 레이어에 `required_fields` 타입+값 규칙을 추가:
   - `publish_ready`/`actual_publish`는 반드시 `bool`.
   - `origin`, `role`, `rights_status`, `source_url`, `authenticity_status`는 `REQUIRED_*`·`null`인지 즉시 판별 가능한 allow-list 처리.
2. `publish` 레디니스 계산에서 placeholder-비placeholder를 명시 구분:
   - `contract placeholder` + `placeholder-free complete bundle`을 서로 분기.
3. 경로 바인딩 규칙 추가:
   - `cardnews`: `cardnews_1..4` 4개, set 경로 prefix 고정, repo-relative 검증.
   - `record.output_set_id == attestation.output_set_id == packaging output_set_id` 일치시 strict 문자열 비교 후 정규화 허용.
4. `rights_evidence`는 타입만이 아니라 최소 키(`evidence_id`, `evidence_type`, `proof_locator`) 존재 여부를 강제.
5. operator checklist는 `checks` 구조와 5개 키의 모두 `true`를 동시에 요구.

## 증적 파일

- `external_workclaude/content_portfolio_v1/RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8_1.json`  
  - V1.8 fixture + false-ready/false-blocked 유도 케이스 3건 추가.
- `external_workclaude/content_portfolio_v1/RIGHTS_INTAKE_TEST_CONTRACT_V1_8_1.md`  
  - 최소 테스트 시나리오/차단 기대값/블로커 점검표.
  - 최소 테스트 시나리오와 기대 blocker/ready 기대값 정리.
