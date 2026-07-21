# Release Boundary Matrix V1.4.1

Per content_id, the three-tier readiness state as of right now. `copy_draft_ready` being true does **not** imply `production_asset_ready` or `publish_review_ready` -- these are three separate gates, and today every item in this batch sits at the same point: copy is done, nothing else is.

| content_id | copy_draft_ready | production_asset_ready | publish_review_ready | asset_provenance_required | operator_approval_required | technical_release_gate |
|---|---|---|---|---|---|---|
| CN-013 | True | False | False | True | True | 07/08 workflow_results receipt false-ready 이슈(CARDNEWS_RECEI... |
| CN-014 | True | False | False | True | True | 07/08 workflow_results receipt false-ready 이슈(CARDNEWS_RECEI... |
| CN-016 | True | False | False | True | True | 07/08 workflow_results receipt false-ready 이슈(CARDNEWS_RECEI... |
| CN-017 | True | False | False | True | True | 07/08 workflow_results receipt false-ready 이슈(CARDNEWS_RECEI... |
| SH-017 | True | False | False | True | True | 자동 렌더링/TTS/음악 삽입 파이프라인 없음 -- 전 과정 수동 촬영·편집 후 운영자 검수 필요, 이 패키... |
| SH-006 | True | False | False | True | True | 자동 렌더링/TTS/음악 삽입 파이프라인 없음 -- 전 과정 수동 촬영·편집 후 운영자 검수 필요, 이 패키... |
| SH-018 | True | False | False | True | True | 자동 렌더링/TTS/음악 삽입 파이프라인 없음 -- 전 과정 수동 촬영·편집 후 운영자 검수 필요, 이 패키... |
| IG-007 | True | False | False | True | True | N/A -- CardNewsModule 렌더 파이프라인에 의존하지 않는 단순 카드/이미지 포맷, 별도 기술적... |
| IG-009 | True | False | False | True | True | N/A -- CardNewsModule 렌더 파이프라인에 의존하지 않는 단순 카드/이미지 포맷, 별도 기술적... |
| IG-013 | True | False | False | True | True | N/A -- CardNewsModule 렌더 파이프라인에 의존하지 않는 단순 카드/이미지 포맷, 별도 기술적... |
| KN-008 | True | False | False | conditional | True | N/A -- 문서형 콘텐츠, 별도 기술적 게이트 없음 (운영자 검수는 별도로 필요)... |
| KN-007 | True | False | False | conditional | True | N/A -- 문서형 콘텐츠, 별도 기술적 게이트 없음 (운영자 검수는 별도로 필요)... |

## Full detail per content_id

### CN-013
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': True, 'description': '실제 게시에는 권리 승인된 이미지 또는 승인된 생성 이미지 기록이 필요함. CardNewsModule fallback 배경(단색/그라디언트)은 dev-safe 검증(레이아웃/타이포 확인) 전용이며, 게시 승인 이미지로 취급하지 않음.'}
- operator_approval_required: True
- technical_release_gate: 07/08 workflow_results receipt false-ready 이슈(CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED)가 해결되기 전까지 package/publish review 진행 금지 -- Common Engine/CardNews 담당 팀 확인 필요 (이 패키지는 수정하지 않음)
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED']

### CN-014
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': True, 'description': '실제 게시에는 권리 승인된 이미지 또는 승인된 생성 이미지 기록이 필요함. CardNewsModule fallback 배경(단색/그라디언트)은 dev-safe 검증(레이아웃/타이포 확인) 전용이며, 게시 승인 이미지로 취급하지 않음.'}
- operator_approval_required: True
- technical_release_gate: 07/08 workflow_results receipt false-ready 이슈(CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED)가 해결되기 전까지 package/publish review 진행 금지 -- Common Engine/CardNews 담당 팀 확인 필요 (이 패키지는 수정하지 않음)
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED']

### CN-016
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': True, 'description': '실제 게시에는 권리 승인된 이미지 또는 승인된 생성 이미지 기록이 필요함. CardNewsModule fallback 배경(단색/그라디언트)은 dev-safe 검증(레이아웃/타이포 확인) 전용이며, 게시 승인 이미지로 취급하지 않음.'}
- operator_approval_required: True
- technical_release_gate: 07/08 workflow_results receipt false-ready 이슈(CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED)가 해결되기 전까지 package/publish review 진행 금지 -- Common Engine/CardNews 담당 팀 확인 필요 (이 패키지는 수정하지 않음)
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED']

### CN-017
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': True, 'description': '실제 게시에는 권리 승인된 이미지 또는 승인된 생성 이미지 기록이 필요함. CardNewsModule fallback 배경(단색/그라디언트)은 dev-safe 검증(레이아웃/타이포 확인) 전용이며, 게시 승인 이미지로 취급하지 않음.'}
- operator_approval_required: True
- technical_release_gate: 07/08 workflow_results receipt false-ready 이슈(CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED)가 해결되기 전까지 package/publish review 진행 금지 -- Common Engine/CardNews 담당 팀 확인 필요 (이 패키지는 수정하지 않음)
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED']

### SH-017
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': True, 'description': '실제 촬영 영상과 촬영자 소유권/동의 확인이 반드시 필요함. 음악·음성(TTS)·배경 자산을 사용할 경우 각각 별도의 라이선스 확인이 필요하며, 촬영 영상의 존재가 음악/음성 자산의 권리까지 자동으로 충족시키지 않음.'}
- operator_approval_required: True
- technical_release_gate: 자동 렌더링/TTS/음악 삽입 파이프라인 없음 -- 전 과정 수동 촬영·편집 후 운영자 검수 필요, 이 패키지 범위에서 자동화되는 기술적 게이트는 없음
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED']

### SH-006
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': True, 'description': '실제 촬영 영상과 촬영자 소유권/동의 확인이 반드시 필요함. 음악·음성(TTS)·배경 자산을 사용할 경우 각각 별도의 라이선스 확인이 필요하며, 촬영 영상의 존재가 음악/음성 자산의 권리까지 자동으로 충족시키지 않음.'}
- operator_approval_required: True
- technical_release_gate: 자동 렌더링/TTS/음악 삽입 파이프라인 없음 -- 전 과정 수동 촬영·편집 후 운영자 검수 필요, 이 패키지 범위에서 자동화되는 기술적 게이트는 없음
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED']

### SH-018
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': True, 'description': '실제 촬영 영상과 촬영자 소유권/동의 확인이 반드시 필요함. 음악·음성(TTS)·배경 자산을 사용할 경우 각각 별도의 라이선스 확인이 필요하며, 촬영 영상의 존재가 음악/음성 자산의 권리까지 자동으로 충족시키지 않음.'}
- operator_approval_required: True
- technical_release_gate: 자동 렌더링/TTS/음악 삽입 파이프라인 없음 -- 전 과정 수동 촬영·편집 후 운영자 검수 필요, 이 패키지 범위에서 자동화되는 기술적 게이트는 없음
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED']

### IG-007
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': True, 'description': '최종 게시 이미지/그래픽의 출처(자체 제작/자체 촬영/라이선스)가 확인되어야 함.'}
- operator_approval_required: True
- technical_release_gate: N/A -- CardNewsModule 렌더 파이프라인에 의존하지 않는 단순 카드/이미지 포맷, 별도 기술적 게이트 없음 (운영자 검수는 별도로 필요)
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED']

### IG-009
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': True, 'description': '최종 게시 이미지/그래픽의 출처(자체 제작/자체 촬영/라이선스)가 확인되어야 함.'}
- operator_approval_required: True
- technical_release_gate: N/A -- CardNewsModule 렌더 파이프라인에 의존하지 않는 단순 카드/이미지 포맷, 별도 기술적 게이트 없음 (운영자 검수는 별도로 필요)
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED']

### IG-013
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': True, 'description': '최종 게시 이미지/그래픽의 출처(자체 제작/자체 촬영/라이선스)가 확인되어야 함.'}
- operator_approval_required: True
- technical_release_gate: N/A -- CardNewsModule 렌더 파이프라인에 의존하지 않는 단순 카드/이미지 포맷, 별도 기술적 게이트 없음 (운영자 검수는 별도로 필요)
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED']

### KN-008
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': 'conditional', 'description': '독립 게시물로 발행할 경우 최종 이미지 사용 여부와 attribution 필요 여부를 별도로 판단해야 함. 현재는 자체 제작 인포그래픽 우선 방침이며, 이미지를 사용하지 않으면 provenance 이슈가 발생하지 않지만 이 판단 자체는 아직 내려지지 않았음.'}
- operator_approval_required: True
- technical_release_gate: N/A -- 문서형 콘텐츠, 별도 기술적 게이트 없음 (운영자 검수는 별도로 필요)
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'EVIDENCE_REVIEW_PENDING', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED_IF_IMAGE_USED']

### KN-007
- copy_draft_ready: True
- production_asset_ready: False
- publish_review_ready: False
- asset_provenance_required: {'required': 'conditional', 'description': '독립 게시물로 발행할 경우 최종 이미지 사용 여부와 attribution 필요 여부를 별도로 판단해야 함. 현재는 자체 제작 인포그래픽 우선 방침이며, 이미지를 사용하지 않으면 provenance 이슈가 발생하지 않지만 이 판단 자체는 아직 내려지지 않았음.'}
- operator_approval_required: True
- technical_release_gate: N/A -- 문서형 콘텐츠, 별도 기술적 게이트 없음 (운영자 검수는 별도로 필요)
- release_blockers: ['ASSET_PROVENANCE_UNCONFIRMED', 'NO_OPERATOR_APPROVAL_RECORDED', 'NO_REAL_ASSET_CAPTURED_IF_IMAGE_USED']
