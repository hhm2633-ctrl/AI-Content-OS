# Batch Handoff V1.3 -- Production Content Batch

## Final verdict: GO for manual production

All 12 packages are finished copy, ready for a human production team to shoot/render and for an operator to complete the rights intake before any publish decision. `publish_ready` and `actual_publish` are hardcoded `false` on every item -- this batch does not publish anything.

## Selection and exclusions (full transparency)

Selected from V1.2's `TOP20_EVIDENCE_PACK.json` (the only pool this instruction authorized selecting from), by priority score, after screening every one of the 20 against the exclusion list (legal/tax/finance/medical, current news/trend, real product/price/review, real brand/expert, topics requiring an efficacy/statistic/performance claim, and anything still carrying an outstanding source-required marker).

**Excluded from the top-20 pool and why:**
- CN-010 (초보자를 위한 홈트레이닝 루틴): fitness/health-adjacent (matched the health keyword filter) -- excluded out of caution even though 'exercise routine' is not strictly medical, since a safer CardNews alternative (CN-017) was available at the same score tier.
- SH-004 (하루 만보 걷기 루틴): same health-adjacency reasoning as CN-010.
- SH-014 (편의점 다이어트 조합): explicitly diet/weight-related -- excluded.
- SH-016 (지갑 정리 미니멀 챌린지): not excluded for risk, simply not selected once 3 safer Shorts slots were filled by score (SH-017, SH-006, SH-018); it remains a safe candidate for a future batch.

**Two items required careful rewriting rather than straightforward inclusion:**
- IG-010 (반려동물 상식 퀴즈형 카드): the OX-quiz format risks inviting a veterinary/health claim. The three questions actually used (daily walks are good, cats tolerate solitude well, water bowls should be changed regularly) were deliberately restricted to uncontroversial pet-ownership routine knowledge -- no toxicology, no medical, no specific figure. See the item's `evidence_status` note for the explicit boundary drawn.
- KN-004 (습관 형성 21일 법칙 진실): the working title itself invites a 'here's the real number' framing, which would require citing a specific study -- exactly what this batch must avoid. It was rewritten to make **no competing numeric claim at all**: it says the 21-day figure is a popular oversimplification and that formation time varies by person, without asserting any alternative statistic, then pivots to an evidence-free behavioral recommendation (focus on consistency, not a fixed deadline). This was the only way to include it without an outstanding evidence requirement -- the V1.2 top-20 Knowledge pool has exactly 2 items, and excluding KN-004 without substitution would have left only 1 Knowledge item, short of the required 2. If the CTO judges this topic too close to the exclusion line regardless of the rewrite, the recommended replacement is any non-regulated Knowledge/Evergreen brief from the full 120-item backlog (e.g. KN-011/KN-020 style concept explainers) in a follow-up batch.

## Selected 12

- **cardnews** (4): CN-013, CN-014, CN-016, CN-017
- **shorts** (3): SH-017, SH-006, SH-018
- **instagram_feed** (3): IG-010, IG-009, IG-013
- **knowledge_evergreen** (2): KN-008, KN-004

## QA summary

Overall: PASS (full detail in `QA_REPORT_V1_3.md`)

- [생성 개수 정확히 12개] PASS -- count=12
- [채널별 구성 4/3/3/2] PASS -- actual={'cardnews': 4, 'shorts': 3, 'instagram_feed': 3, 'knowledge_evergreen': 2}
- [content_id 중복] PASS -- duplicates=[]
- [중복/복제 문장 탐지 (final_copy 프로즈 필드 한정)] PASS -- duplicates=[]
- [미확인 수치·효과·전문가 주장] PASS -- hits=[]
- [SOURCE_REQUIRED 잔존] PASS -- hits=[]
- [권리 승인 조작] PASS -- hits=[]
- [publish_ready/actual_publish 전부 false] PASS -- violations=[]
- [CardNews: 4장/문장완결/ellipsis 없음/숫자일치/단일 CTA] PASS -- issues=[]
- [Shorts: 4장면/15-45초/내레이션/자막/구도/실행경계] PASS -- issues=[]
- [Instagram: hook/본문/해시태그 정책 준수] PASS -- issues=[]
- [전 항목 단일 CTA 문장] PASS -- issues=[]

## No changes outside the owned folder

This batch only reads from and writes to `external_workclaude/content_portfolio_v1/`. No file in `modules/`, `tests/`, `docs/`, `storage/`, `config/`, `site/`, or any shared status document was touched, and no Git operation was performed.