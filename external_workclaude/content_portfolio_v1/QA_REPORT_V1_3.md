# QA Report V1.3 -- Production Content Batch

Overall: PASS

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