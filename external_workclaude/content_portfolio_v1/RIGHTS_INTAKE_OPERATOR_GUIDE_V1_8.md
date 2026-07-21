# Rights Intake Operator Guide V1.8

## 목적

이 가이드는 CardNews/Shorts/Instagram/Knowledge 12개 항목의 publish blocker 정합성 확보를 위해
권리·근거·운영자 확인 항목을 안전하게 수집하는 입력 체계를 정의합니다.

- 출력 집합 ID: `91a28c88912849b58fa608330a217467` (V1.7에서 확정)
- 파일: `RIGHTS_INTAKE_CONTRACT_V1_8.json`
- 모든 입력은 실제 승인 이전에는 실값을 넣지 않음

## 입력 규칙(필수)

각 카드/자산 레코드에서 아래 필드는 필수입니다.

- `origin`
- `role`
- `rights_status`
- `rights_evidence`
- `source_url`
- `reference_verified`
- `topic_relevance`
- `authenticity_status`
- `operator_checklist`
- `commercial_relationship_reviewed`
- `output_set_id`
- `card_path` (cardnews에 한해 repo-relative 4경로)

### 미확정 값 표기

실제 값이 없을 때는 `null` 또는 `REQUIRED_*` 토큰으로 유지해야 합니다.

예시: `REQUIRED_SOURCE_URL`, `REQUIRED_RIGHTS_EVIDENCE_ID`, `REQUIRED_PLACEHOLDER`

## 입력 검수 규칙

- 상대 경로만 허용: 절대경로(`C:\...`, `/home/...`) 사용 금지
- `.runs`, `.staging` 포함 경로 금지
- `output_set_id`는 반드시 `91a28c88912849b58fa608330a217467`
- 카드뉴스는 카드 4개(`card_news_1..4.png`) 경로 결속
- `publish_ready`, `actual_publish`는 기본 `false`

## 제출 방식(권장)

1. 콘텐츠당 자산 레코드를 생성
2. 카드뉴스의 경우 4개 레코드
3. 각 레코드별 `operator_checklist`와 `rights_evidence`를 함께 기록
4. 미완료 토큰을 그대로 둔 상태로 handoff
5. 실제 근거가 추가되면 해당 항목만 교체 업데이트
