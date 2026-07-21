# Batch Handoff V1.3.1 -- Evidence Red-Team Correction

## Final verdict: GO for manual production

This is a correction pass triggered by the CTO's explicit distrust of V1.3's 'SOURCE_REQUIRED == 0' check -- that check was a string-match, not a semantic audit. Every sentence in every V1.3 item was re-read individually; the full sentence-level reasoning is in `EVIDENCE_RED_TEAM_V1_3_1.md`. This document summarizes the outcome.

## What changed and why

**KN-004 (습관 형성 21일 법칙 진실) -- REMOVED, not just its number.** The V1.2 top-20 Knowledge pool contains exactly 2 items (KN-004, KN-008); removing KN-004 without a same-pool substitute would have left only 1 Knowledge item. Per the CTO's explicit authorization to lift the top-20 restriction for this replacement, KN-007 (회의록 작성 기본기) was selected from the full 120-item backlog -- a pure document-template instruction (what fields a meeting-minutes doc contains) with zero historical, statistical, or efficacy content.

**IG-010 (반려동물 상식 퀴즈형 카드) -- REMOVED, replaced rather than rewritten.** An OX-quiz-about-pet-facts format cannot be limited to pure prep/record content by construction: all three questions actually used in V1.3 were implicit health/behavior/hygiene-prevention claims (daily walking is beneficial, cats tolerate solitude well by nature, water bowls must be changed to prevent something unstated). None of the three allowed evidence_not_required_reason values legitimately cover a quiz whose entire premise is asserting facts about animal care. Same pool-size problem as Knowledge -- the top-20 has exactly 3 Instagram items -- so IG-007 (문화생활 예산 관리 팁) was pulled from the full backlog instead: rewritten as a pure personal-budget-tracking prompt (the reader records and plans their own spending, asserting nothing about the external world).

**CN-013 (반려동물 첫 입양 준비물) -- kept, rewritten.** The checklist itself (이동장, 급식기, 사료, 배변용품, 병원 연락처) is pure preparation/record content and stays. Removed: '이 다섯 가지만 챙기면 ... 적응을 도울 수 있습니다' -- an implicit behavioral/welfare-outcome claim about the animal's adjustment, unsupported by any citation.

**SH-017 (반려동물 산책 준비물 점검) -- kept, unchanged.** Reviewed sentence by sentence; found no health/behavior/prevention/safety-guarantee claim. It is already a pure gear checklist.

**KN-008 (시간관리 매트릭스 활용법) -- kept, rewritten.** Removed the 'Eisenhower' attribution entirely (a specific-person historical claim this batch cannot verify) and the 'you'll have time to spare' efficacy claim. It is now an unattributed description of a generic urgent/important classification tool plus a personal to-do-sorting prompt. Per instruction item 5, a classification-scheme description does not qualify for `evidence_not_required_reason` even once fully unattributed and effect-free -- so this item's field is deliberately left `null`, not defaulted to any of the three tokens. See the red-team table for the sentence-level split.

**CN-017 (커피 원두 보관법) and SH-006 (커피 내리는 법 3단계) -- kept, rewritten.** Removed every taste/freshness/extraction-effect assertion: '향이 금방 날아가고 신선함이 떨어집니다' (a chemistry/degradation claim), '신선함을 더 오래 유지할 수 있습니다' (an outcome guarantee), '충분해요' (a sufficiency/efficacy claim), '매번 맛이 다르셨다면' (an implicit taste-outcome causal claim). Storage/brewing steps are now presented as selectable options, never as causes of a promised result.

**IG-009 and IG-013 -- kept, rewritten (not named by the CTO, found during the mandated full re-read of every final sentence).** IG-009's '점심시간을 조금 다르게 써보는 것만으로 오후 기분이 달라질 수 있습니다' was an unsupported psychological-effect claim -- rewritten as 'a possible option,' not a promised mood change. IG-013's '큰 목표부터 세우면 오히려 지치기 쉽습니다' and '작게 오래 이어가는 것이 핵심입니다' were an unsupported behavioral-psychology causal claim and an assertive efficacy claim -- both rewritten into 'methods you can try,' asserting no mechanism.

## The new field: evidence_not_required_reason

Applied only where a sentence set is genuinely non-claim: `pure_operator_instruction` (CardNews/Shorts checklists, KN-007's document template), `personal_organization_prompt` (IG-007/IG-009/IG-013's self-tracking prompts), or `non-claim_creative_copy` (hooks/CTAs, noted at the sentence level in the red-team table, not separately tagged in the JSON's per-item summary field to avoid schema bloat). Per instruction item 5, this field is **never** applied to general facts, common knowledge, classification schemes, historical claims, health claims, or safety claims -- KN-008 is the one item where this restriction bites even after full rewriting, and it is left `null` rather than mislabeled.

## Selected 12 (final)

- **cardnews** (4): CN-013, CN-014, CN-016, CN-017
- **shorts** (3): SH-017, SH-006, SH-018
- **instagram_feed** (3): IG-007, IG-009, IG-013
- **knowledge_evergreen** (2): KN-008, KN-007

## QA summary

Overall: PASS (full detail in `QA_REPORT_V1_3_1.md`)

- [생성 개수 정확히 12개] PASS -- count=12
- [채널별 구성 4/3/3/2] PASS -- actual={'cardnews': 4, 'shorts': 3, 'instagram_feed': 3, 'knowledge_evergreen': 2}
- [KN-004 완전 제외] PASS -- present_as_id=False, mentioned_anywhere=False
- [content_id 중복] PASS -- duplicates=[]
- [중복/복제 문장 탐지] PASS -- duplicates=[]
- [제거 대상 문구 재출현 여부 (regression guard)] PASS -- hits=[]
- [건강·동물안전·효과 일반 위험 키워드 (regression guard)] PASS -- hits=[]
- [주의] 위 두 항목은 정규식 기반 회귀 방지 안전망이며, 실제 의미론적 판단은 EVIDENCE_RED_TEAM_V1_3_1.md의 문장 단위 수기 검토가 근거임 (형식 검사만으로 충분하다고 주장하지 않음).
- [evidence_not_required_reason 어휘 오용] PASS -- bad=[]
- [KN-008에 evidence_not_required_reason 미부여 확인 (분류 콘텐츠 제외 규칙)] PASS
- [실제 URL/승인/수치 조작] PASS -- hits=[]
- [publish_ready/actual_publish 전부 false] PASS -- violations=[]
- [숫자 약속-실제 항목 수 일치] PASS -- mismatches=[]
- [CardNews: 4장/문장완결/ellipsis 없음/단일 CTA] PASS -- issues=[]

## No changes outside the owned folder

This correction only reads from and writes to `external_workclaude/content_portfolio_v1/`. No file in `modules/`, `tests/`, `docs/`, `storage/`, `config/`, `site/`, or any shared status document was touched, and no Git operation was performed.