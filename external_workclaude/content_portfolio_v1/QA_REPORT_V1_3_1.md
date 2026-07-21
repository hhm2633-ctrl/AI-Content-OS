# QA Report V1.3.1 -- Evidence Red-Team Correction

Overall: PASS

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