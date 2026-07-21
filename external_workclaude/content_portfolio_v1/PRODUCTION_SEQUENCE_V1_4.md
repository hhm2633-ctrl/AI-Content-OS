# Production Sequence V1.4

## Wave assignment rationale

Waves are sorted by evidence/rights risk and residual manual-input dependency, not by expected completion speed (CardNews's Wave 1 items are still gated behind the external CardNews receipt blocker for their render/packaging stages -- see `BLOCKER_REGISTER_V1_4.md`).

**Wave 1 -- lowest risk (4):** CN-013, CN-014, CN-016, CN-017. All CardNews, all carry `evidence_not_required_reason: pure_operator_instruction`, all viable on CardNewsModule fallback backgrounds with zero mandatory real photo, and all cleared multiple red-team passes in V1.3.1 with no open question.

**Wave 2 -- needs additional review (4):** KN-008 (the one item where `evidence_not_required_reason` was deliberately left null per the classification-content exception -- needs a reviewer/CTO judgment call, not just file-based confirmation), KN-007 and IG-007 (both newly substituted into the batch in V1.3.1, only a single red-team pass so far), IG-013 (rewritten to remove a habit-formation psychology claim -- recommend a second confirming read before lock).

**Wave 3 -- needs manual input (4):** SH-017, SH-006, SH-018 (all three Shorts require real, self-filmed footage -- the clearest 'someone must physically do something' case in the batch) and IG-009 (rewritten to remove a mood-change claim -- grouped here because, like the Shorts items, finalizing it depends on a human reading the rewritten sentence and confirming it still reads naturally, not just a file check).

## CardNews-specific caution (binding for all 4 Wave-1 CardNews items)

Per the CTO's explicit instruction: until the existing global 07/08 workflow_results receipt false-ready issue is resolved (owned by the Common Engine/CardNews lane -- see `tests/test_workflow_card_news_output_receipts.py`, read-only reference, not modified by this package), CardNews's `RENDER_OUTPUT`, `INDEPENDENT_QA_FINAL`, and `PACKAGING_PUBLISH_HANDOFF` work orders stay `queued` with blocker code `CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED`. Only `COPY_STORY_FINALIZE`, `EVIDENCE_RIGHTS_CONFIRM`, and `LAYOUT_TYPOGRAPHY_PREP` are marked parallel-executable for CardNews items. Common Engine code itself is out of this package's ownership -- no fix is proposed or attempted here.

## Stage sequence per content type

- **CardNews**: 문안·스토리 -> Evidence·Rights -> 레이아웃·타이포 -> [QUEUED] 렌더링·산출물 -> [QUEUED] 독립 QA -> [QUEUED] 패키징·게시인계
- **Shorts**: 문안·스토리 -> Evidence·Rights -> Shorts(촬영/편집) -> 독립 QA -> 패키징·게시인계
- **Instagram**: 문안·스토리 -> Evidence·Rights -> 레이아웃·타이포 -> Instagram·Intelligence -> 독립 QA -> 패키징·게시인계
- **Knowledge/Evergreen**: 문안·스토리 -> Evidence·Rights -> 레이아웃·타이포 -> Knowledge·Learning -> 독립 QA -> 패키징·게시인계

## Full work order list by wave

### Wave 1

**CN-013 -- 반려동물 첫 입양 준비물** (cardnews)
  - CN-013-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - CN-013-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- parallel-ready
  - CN-013-WO-03 [LAYOUT_TYPOGRAPHY_PREP] role=레이아웃·타이포 -- parallel-ready
  - CN-013-WO-04 [RENDER_OUTPUT] role=렌더링·산출물 -- QUEUED
  - CN-013-WO-05 [INDEPENDENT_QA_FINAL] role=독립 QA -- QUEUED
  - CN-013-WO-06 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- QUEUED

**CN-014 -- 캠핑 초보 준비물 체크리스트** (cardnews)
  - CN-014-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - CN-014-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- parallel-ready
  - CN-014-WO-03 [LAYOUT_TYPOGRAPHY_PREP] role=레이아웃·타이포 -- parallel-ready
  - CN-014-WO-04 [RENDER_OUTPUT] role=렌더링·산출물 -- QUEUED
  - CN-014-WO-05 [INDEPENDENT_QA_FINAL] role=독립 QA -- QUEUED
  - CN-014-WO-06 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- QUEUED

**CN-016 -- 여행 전 짐싸기 체크리스트** (cardnews)
  - CN-016-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - CN-016-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- parallel-ready
  - CN-016-WO-03 [LAYOUT_TYPOGRAPHY_PREP] role=레이아웃·타이포 -- parallel-ready
  - CN-016-WO-04 [RENDER_OUTPUT] role=렌더링·산출물 -- QUEUED
  - CN-016-WO-05 [INDEPENDENT_QA_FINAL] role=독립 QA -- QUEUED
  - CN-016-WO-06 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- QUEUED

**CN-017 -- 커피 원두 보관법** (cardnews)
  - CN-017-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - CN-017-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- parallel-ready
  - CN-017-WO-03 [LAYOUT_TYPOGRAPHY_PREP] role=레이아웃·타이포 -- parallel-ready
  - CN-017-WO-04 [RENDER_OUTPUT] role=렌더링·산출물 -- QUEUED
  - CN-017-WO-05 [INDEPENDENT_QA_FINAL] role=독립 QA -- QUEUED
  - CN-017-WO-06 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- QUEUED

### Wave 2

**KN-008 -- 시간관리 매트릭스 활용법** (knowledge_evergreen)
  - KN-008-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - KN-008-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- QUEUED
  - KN-008-WO-03 [LAYOUT_TYPOGRAPHY_PREP] role=레이아웃·타이포 -- parallel-ready
  - KN-008-WO-04 [KNOWLEDGE_LEARNING_INTEGRATION] role=Knowledge·Learning -- parallel-ready
  - KN-008-WO-05 [INDEPENDENT_QA_FINAL] role=독립 QA -- sequential
  - KN-008-WO-06 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- sequential

**KN-007 -- 회의록 작성 기본기** (knowledge_evergreen)
  - KN-007-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - KN-007-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- parallel-ready
  - KN-007-WO-03 [LAYOUT_TYPOGRAPHY_PREP] role=레이아웃·타이포 -- parallel-ready
  - KN-007-WO-04 [KNOWLEDGE_LEARNING_INTEGRATION] role=Knowledge·Learning -- parallel-ready
  - KN-007-WO-05 [INDEPENDENT_QA_FINAL] role=독립 QA -- sequential
  - KN-007-WO-06 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- sequential

**IG-007 -- 문화생활 예산 관리 팁** (instagram_feed)
  - IG-007-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - IG-007-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- parallel-ready
  - IG-007-WO-03 [LAYOUT_TYPOGRAPHY_PREP] role=레이아웃·타이포 -- parallel-ready
  - IG-007-WO-04 [INSTAGRAM_INTELLIGENCE_PREP] role=Instagram·Intelligence -- parallel-ready
  - IG-007-WO-05 [INDEPENDENT_QA_FINAL] role=독립 QA -- sequential
  - IG-007-WO-06 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- sequential

**IG-013 -- 자기계발 습관 만들기 팁** (instagram_feed)
  - IG-013-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - IG-013-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- parallel-ready
  - IG-013-WO-03 [LAYOUT_TYPOGRAPHY_PREP] role=레이아웃·타이포 -- parallel-ready
  - IG-013-WO-04 [INSTAGRAM_INTELLIGENCE_PREP] role=Instagram·Intelligence -- parallel-ready
  - IG-013-WO-05 [INDEPENDENT_QA_FINAL] role=독립 QA -- sequential
  - IG-013-WO-06 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- sequential

### Wave 3

**SH-017 -- 반려동물 산책 준비물 점검** (shorts)
  - SH-017-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - SH-017-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- parallel-ready
  - SH-017-WO-03 [SHORTS_PRODUCTION] role=Shorts -- parallel-ready
  - SH-017-WO-04 [INDEPENDENT_QA_FINAL] role=독립 QA -- sequential
  - SH-017-WO-05 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- sequential

**SH-006 -- 커피 내리는 법 3단계** (shorts)
  - SH-006-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - SH-006-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- parallel-ready
  - SH-006-WO-03 [SHORTS_PRODUCTION] role=Shorts -- parallel-ready
  - SH-006-WO-04 [INDEPENDENT_QA_FINAL] role=독립 QA -- sequential
  - SH-006-WO-05 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- sequential

**SH-018 -- 캐리어 짐싸기 순서** (shorts)
  - SH-018-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - SH-018-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- parallel-ready
  - SH-018-WO-03 [SHORTS_PRODUCTION] role=Shorts -- parallel-ready
  - SH-018-WO-04 [INDEPENDENT_QA_FINAL] role=독립 QA -- sequential
  - SH-018-WO-05 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- sequential

**IG-009 -- 직장인 점심시간 활용법** (instagram_feed)
  - IG-009-WO-01 [COPY_STORY_FINALIZE] role=문안·스토리 -- parallel-ready
  - IG-009-WO-02 [EVIDENCE_RIGHTS_CONFIRM] role=Evidence·Rights -- parallel-ready
  - IG-009-WO-03 [LAYOUT_TYPOGRAPHY_PREP] role=레이아웃·타이포 -- parallel-ready
  - IG-009-WO-04 [INSTAGRAM_INTELLIGENCE_PREP] role=Instagram·Intelligence -- parallel-ready
  - IG-009-WO-05 [INDEPENDENT_QA_FINAL] role=독립 QA -- sequential
  - IG-009-WO-06 [PACKAGING_PUBLISH_HANDOFF] role=패키징·게시인계 -- sequential
