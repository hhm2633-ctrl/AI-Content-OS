# CardNews Evidence Input Contract

## 목적

이 문서는 실제 근거와 이미지 부족으로 `publishing_blocked`가 된 CardNews를 운영자가 안전하게
보완하기 위한 입력 계약이다. 근거·댓글·이미지를 새로 만들어 내는 규격이 아니라, 실제로 확보한
자료가 현재 `EvidenceSelector`, `SocialProofSelector`, `CardNewsModule`, `PublishingModule`의
보호 조건을 충족하는지 확인하는 규격이다.

운영자는 자료가 불충분하면 `publishing_blocked`를 유지해야 한다. 출처 표시는 사용 허가를
대체하지 않으며, AI 생성 이미지와 경쟁 계정 참고 자료는 주제의 실제 근거로 취급하지 않는다.

## 적용 원칙

- 원문, 게시일, 출처, 사용 권한을 실제 자료에서 확인한다.
- `caption_text`나 댓글 개수는 실제 제3자 댓글/반응으로 취급하지 않는다.
- 경쟁 계정 분석용 캡처는 기본적으로 `competitor_reference`이며 자동 렌더링하지 않는다.
- 근거가 카드 주제와 직접 관련됐다는 확인 없이 `topic_evidence`로 승격하지 않는다.
- 전화번호·이메일은 마스킹하고 계정 식별자는 최소화한다.
- 모든 판정은 보수적으로 한다. 알 수 없는 값은 허용 값으로 추정하지 않는다.
- 발행 준비는 자동 게시 승인이 아니다. 현재 `upload_mode: manual` 계약을 유지한다.

## 1. 원문 근거 입력

자료별로 다음 값을 확보한다. 비어 있거나 검증할 수 없는 필드는 빈 상태로 남기고 NO-GO로
판정한다.

| 필드 | 필수 | 계약 |
|---|---:|---|
| `source_url` | 예 | 브라우저에서 확인 가능한 실제 원문 URL. 검색 결과·재게시 모음 URL은 원문으로 대체하지 않는다. |
| `published_at` | 예 | 원문에 표시된 게시일. 시간대가 확인되면 함께 기록한다. 확인 불가는 추정하지 않는다. |
| `observed_at` | 예 | 운영자가 원문을 확인한 시각. 게시일을 대신하지 않는다. |
| `source_name` | 예 | 매체, 기관, 게시 계정 등 실제 출처명. |
| `source_type` | 예 | `official`, `news`, `community`, `social`, `owned` 중 실제 성격에 맞는 값. |
| `title` | 예 | 원문 제목 또는 게시물의 식별 가능한 제목. 의미를 바꾸어 재작성하지 않는다. |
| `excerpt` | 조건부 | 카드에 반영할 최소 범위의 원문 요약 또는 인용 대상. 원문에 없는 사실을 추가하지 않는다. |
| `topic_terms` | 예 | CardNews 주제와 직접 연결되는 실제 용어. 관련성 판정 근거로 사용한다. |
| `verification_note` | 예 | 누가 무엇을 대조했는지와 불확실성. 사실 확인 완료를 선언하는 문장이 아니라 확인 기록이다. |

주제 관련성은 현재 Evidence 계약을 따른다. 의미 있는 용어가 최소 2개 이상 일치하고 관련성
점수가 `0.34` 이상이어야 `topic_relevant=true` 후보가 될 수 있다. 임계치 통과는 출처 신뢰성이나
저작권 허가를 대신하지 않는다.

## 2. 이미지 자산 입력

이미지는 실제 파일과 provenance를 함께 관리한다.

| 필드 | 필수 | 허용/판정 규칙 |
|---|---:|---|
| `asset_path` | 예 | 실제 존재하고 열리는 로컬 파일 경로. 존재하지 않는 경로를 만들지 않는다. |
| `source_url` | 예 | 이미지를 확인할 수 있는 실제 원문 URL. |
| `source_name` | 예 | 이미지 소유자 또는 제공 출처. |
| `captured_at` | 조건부 | 운영자가 캡처한 시각. 원 게시일과 구분한다. |
| `copyright_status` | 예 | 아래 허용·차단 값 중 하나. 증빙 없이 허용 값으로 기록하지 않는다. |
| `permission_evidence` | 조건부 | 라이선스 URL, 서면 허가 기록, 내부 소유 확인 등 사용 권한의 근거 위치. |
| `asset_role` | 예 | `topic_evidence` 또는 `competitor_reference`. |
| `attribution_required` | 예 | 출처 표시 필요 여부. 사용 권한과 별개의 값이다. |
| `attribution_text` | 조건부 | 실제 렌더링 시 표시할 짧은 출처명. URL을 카드 본문에 노출하지 않는다. |
| `topic_relevance_note` | 예 | 주제와 이미지의 직접 관계를 확인한 근거. |

현재 렌더링 허용 `copyright_status`:

- `owned`
- `licensed`
- `public_domain`
- `official_reuse_allowed`
- `user_supplied_with_permission`
- `permission_granted`

현재 렌더링 차단 `copyright_status`:

- `third_party_unlicensed_reference`
- `unknown`
- `restricted`

`render_allowed=true`가 되려면 허용 상태와 실제 권한 증빙이 일치해야 한다. 출처를 표시한다는
이유만으로 `unknown` 또는 제3자 무허가 자료를 허용하지 않는다.

`permission_evidence`는 임의 문자열이 아니라 다음 필드를 가진 객체여야 한다.

- `type`: 권리 상태별 허용 증빙 유형
- `reference`: 공개 URL 또는 저장소 내부의 실제 검토 문서 경로
- `review_status`: 반드시 `approved`
- `reviewed_at`: timezone이 포함된 ISO-8601 검토 시각이며 미래 시각은 금지
- `asset_path`: 권리 검토 대상인 동일한 저장소 상대 이미지 경로

권리 상태와 증빙 유형은 다음 조합만 허용한다. 의미가 다른 조합은 fail-closed한다.

| `copyright_status` | 허용 `permission_evidence.type` |
|---|---|
| `owned` | `ownership_record` |
| `licensed` | `license_url` |
| `public_domain` | `public_domain_record` |
| `official_reuse_allowed` | `official_reuse_policy` |
| `user_supplied_with_permission` | `written_permission` |
| `permission_granted` | `written_permission` |

Validator는 DNS 조회를 수행하지 않는다. localhost와 literal private/loopback/link-local/reserved/
unspecified IP는 차단한다. 일반 hostname은 목적지 IP를 오프라인에서 확인할 수 없으므로 위험 상태를
`UNKNOWN`으로 기록하고 `source_verification_pending=true` 및 수동 URL 확인을 유지한다.
Credential이 포함되거나 그 밖의 이유로 URL·권리 참조가 invalid 판정을 받으면 validator 결과에서
해당 원문을 제거한다. 사용자명, 비밀번호, key, token 문자열을 진단·provenance에 다시 노출하지 않는다.

이미지는 다음 네 조건을 모두 충족해야 CardNews evidence 후보로 사용할 수 있다.

1. 실제 파일이 존재한다: `candidate_found=true`.
2. 현재 주제와 직접 관련된다: `topic_relevant=true`.
3. 게시용 렌더링 권한이 확인됐다: `render_allowed=true`.
4. 실제 사건·주제의 근거다: `asset_role=topic_evidence`.

Instagram Research나 Competitor Learning에서 확보한 경쟁 계정 캡처는 기본값을
`competitor_reference`로 유지한다. 공식성·직접 관련성·사용 권한을 별도로 입증하지 못하면
`topic_evidence`로 변경하지 않는다.

## 3. 실제 댓글·반응 입력

Social Proof는 공개된 실제 제3자 반응의 원문만 허용한다. 다음 필드 중 하나에 실제 본문이
있어야 후보가 된다.

- `comment_text`
- `reply_text`
- `reaction_text`
- `quote_text`

댓글·반응 레코드는 다음 보조 정보를 함께 기록한다.

| 필드 | 필수 | 계약 |
|---|---:|---|
| `source_url` | 예 | 해당 반응을 확인할 수 있는 실제 게시물 URL. |
| `account_handle` | 조건부 | 실제 계정명. 표시 단계에서는 마스킹한다. |
| `observed_at` | 예 | 운영자가 반응을 확인한 시각. |
| `visible_like_text` | 선택 | 반응 수치 참고용. 댓글 본문을 대신하지 않는다. |
| `visible_comment_text` | 선택 | 댓글 개수 참고용. 댓글 본문을 대신하지 않는다. |
| `consent_or_public_basis` | 예 | 공개 게시물 확인 또는 별도 동의 등 처리 근거. |

다음 값은 Social Proof 본문으로 인정하지 않는다.

- 게시물 작성자의 `caption_text`
- `visible_like_text`, `visible_comment_text`, `visible_repost_text` 같은 개수 표시
- 운영자나 AI가 만든 댓글 형태의 문장
- 실제 원문을 의미가 달라지도록 요약·재작성한 문장

선정된 반응은 `커뮤니티 반응`으로 표시하고, 사실 근거가 아닌 의견이라는 고지를 유지한다.
찬성·반대 반응이 모두 실제로 존재하면 현재 균형 선정 계약을 따라 최대 2개를 사용한다.

## 4. PII 및 식별자 처리

- 이메일은 `[이메일 비공개]`로 치환한다.
- 전화번호는 `[전화번호 비공개]`로 치환한다.
- 계정명은 앞 2글자와 뒤 1글자만 남기고 중간을 `*`로 마스킹한다. 3글자 이하는 전체를
  마스킹한다.
- 주소, 실명, 주문번호, 차량번호 등 추가 식별정보가 보이면 자동 규칙만 믿지 말고 수동으로
  제거한다.
- PII 제거 외에는 댓글 원문의 의미를 바꾸지 않는다.
- 공개 게시물이어도 불필요한 개인 식별정보는 카드에 노출하지 않는다.

## 5. 수동 운영 체크리스트

### 원문·사실

- [ ] 원문 URL을 열어 실제 자료와 일치함을 확인했다.
- [ ] 게시일과 운영자 확인 시각을 구분해 기록했다.
- [ ] 제목·본문·핵심 주장 사이에 모순이 없다.
- [ ] CardNews 주제와 의미 있는 용어가 최소 2개 이상 직접 연결된다.
- [ ] 최신성 또는 시점 차이로 의미가 달라지지 않았는지 확인했다.

### 이미지·권리

- [ ] 로컬 이미지 파일이 실제로 열리고 손상되지 않았다.
- [ ] 이미지 역할이 `topic_evidence`인지 `competitor_reference`인지 구분했다.
- [ ] `copyright_status`와 권한 증빙을 확인했다.
- [ ] 필요한 attribution 문구를 준비했다.
- [ ] AI 이미지나 무허가 경쟁 계정 캡처를 실제 근거로 표시하지 않았다.
- [ ] 최종 렌더 결과에 실제 이미지가 반영돼 `real_image_used_count > 0`임을 확인했다.

### 댓글·PII

- [ ] 실제 댓글/반응 본문 필드가 존재한다.
- [ ] caption 또는 반응 개수를 댓글 본문으로 오인하지 않았다.
- [ ] 이메일·전화번호와 기타 식별정보를 제거했다.
- [ ] 계정명을 마스킹했다.
- [ ] 반응을 의견으로 표시하고 사실 근거처럼 사용하지 않았다.

### 최종 산출물

- [ ] 네 장이 `hook -> problem -> solution -> cta` 순서를 유지한다.
- [ ] 문안에 근거가 없는 사실·수치·인용이 없다.
- [ ] 출처 표시, 안전 여백, 글자 크기, 대비, CTA 공간을 직접 확인했다.
- [ ] `image_sourcing_status.manual_image_required=false`를 확인했다.
- [ ] `image_sourcing_status.real_image_used_count > 0`을 확인했다.
- [ ] Publishing 결과가 `publishing_ready`, queue가 `ready_for_manual_upload`인지 확인했다.
- [ ] 실제 업로드 전 사람이 이미지·캡션·해시태그를 최종 승인했다.

## 6. GO / NO-GO 판정

### GO: 수동 업로드 준비 가능

아래 조건을 모두 만족할 때만 `publishing_blocked` 해제를 허용한다.

- 원문 URL, 게시일, 출처가 실제 자료와 대조됐다.
- 카드에 사용한 모든 사실·인용이 원문에서 확인된다.
- 사용 이미지 파일이 실제로 렌더링됐고 `real_image_used_count > 0`이다.
- `manual_image_required=false`다.
- 이미지가 `topic_evidence`로 확인됐으며 주제 관련성과 사용 권한을 모두 통과했다.
- 차단 저작권 상태의 자산이 렌더링되지 않았다.
- 사용한 댓글/반응이 실제 본문 필드에서 왔고 PII·계정명 처리가 완료됐다.
- CardNews production QA가 통과하고 네 PNG를 사람이 직접 검수했다.
- Publishing 결과가 `publishing_ready`이며 queue 상태가 `ready_for_manual_upload`다.

GO는 “자동 게시”가 아니라 “사람이 수동 업로드를 진행해도 되는 준비 상태”를 뜻한다.

### NO-GO: `publishing_blocked` 유지

다음 중 하나라도 해당하면 차단 상태를 유지한다.

- 원문 URL, 게시일, 출처 중 하나를 확인할 수 없다.
- 주제 관련성이 없거나 관련성 근거가 부족하다.
- 이미지 파일이 없거나 최종 카드에 실제로 반영되지 않았다.
- `manual_image_required=true` 또는 `real_image_used_count <= 0`이다.
- `copyright_status`가 `unknown`, `restricted`, `third_party_unlicensed_reference`다.
- 자산 역할이 `competitor_reference`인데 실제 근거처럼 사용하려 한다.
- 실제 댓글 본문 없이 caption, 개수, 생성 문장을 Social Proof로 사용하려 한다.
- PII 또는 불필요한 계정 식별정보가 남아 있다.
- attribution 필요 자료에 출처 표시가 없거나, attribution만으로 권리 문제를 덮으려 한다.
- QA 실패, 텍스트 절단·겹침, CTA 불일치 등 사람이 확인한 제작 결함이 남아 있다.

## 7. 현재 시스템과의 연결

운영 입력이 준비돼도 상태 값을 손으로 바꾸지 않는다. 실제 이미지가 CardNews 렌더링에 반영된
후 `CardNewsModule`이 `image_sourcing_status`를 다시 계산하고, `PublishingModule`이 다음 값을
검사하도록 전체 흐름을 재실행한다.

- `manual_image_required`
- `real_image_used_count`
- `operations.publishing_blocked`
- `operations.blocking_reasons`
- Publishing `status`
- Publish queue `status`

현재 Publishing 게이트는 `manual_image_required`가 참이거나 `real_image_used_count`가 0 이하이면
각각 `manual_image_required`, `real_image_used_count_zero` 차단 사유를 기록한다. 운영자는 차단
사유를 삭제하거나 결과 JSON을 직접 편집하지 말고, 실제 입력과 렌더 결과를 보완해야 한다.
