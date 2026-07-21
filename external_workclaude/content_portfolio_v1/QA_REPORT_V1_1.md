# QA Report V1.1

Overall: PASS

- [PRODUCTION_BRIEFS_V1_1 content_id 유효성] PASS -- invalid=[]
- [채널별 production brief >= 3] PASS -- counts={'cardnews': 3, 'shorts': 3, 'instagram_feed': 3, 'brandconnect': 3, 'commerce_guide': 3, 'knowledge_evergreen': 3}
- [cluster_id 중복] PASS -- duplicates=[]
- [cross-channel cluster 수 >= 15] PASS -- count=22
- [cluster member content_id 유효성] PASS -- invalid=[]
- [신규 산출물 내 확인되지 않은 실제 수치] PASS -- hits=[]
- [CardNews 우선순위 동점 그룹 축소] V1: 19개 항목이 단일 점수로 묶임 -> V1.1: 12개 서로 다른 점수 (25개 중)
- [BrandConnect 우선순위 동점 그룹 축소] V1: 15개 항목 전원 동일 점수 -> V1.1: 서로 다른 점수 8개 (15개 중)
- [학습 패턴 감사: validated/proven 등 확신 표현] raw hits=1, 검토 후 false positive=1 (근거: LEARNING_PATTERN_AUDIT.md §5), 실제 위반=0 -- PASS
- [학습 패턴 감사: 중복 후보] 0건 (검토 후 제거 0건, 근거는 LEARNING_PATTERN_AUDIT.md 참조)
- [학습 패턴 감사: 모순 후보] 0건
- [학습 패턴 감사: 과도한 추상 패턴] 1차 휴리스틱(명시적 비교 표현 부재) 21건 -- 검토 결과 표현 관습 차이로 판정, 실질 기준(구체적 메커니즘 부재) 재검사 결과 0건 -- PASS