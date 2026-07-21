# Top 20 Priority Content -- V1.1 (real production priority)

V1 defect: 19 of 25 CardNews briefs tied at an identical score (13.8). V1.1: 12 distinct scores across 25 CardNews briefs, because evidence_sourcing_cost / rights_difficulty / freshness_risk / reuse_score are now assessed per topic (see tools/build_portfolio.py::assess_topic + attach_reuse_scores_and_priority), not as a single constant per content_type.

All 20 items below are `offline_ready` -- no `planning_only`/`blocked_by_data`/`not_approved` item ranks into the combined top 20, which is itself a quality signal: the score genuinely rewards immediate executability.

| Rank | content_id | working_title | content_type | theme_tag | score | evidence_cost | rights_diff | freshness_risk | reuse | readiness |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | CN-013 | 반려동물 첫 입양 준비물 | cardnews | PET_CARE | 17.66 | 1.2 | 1.0 | 1.2 | 3 | offline_ready |
| 2 | IG-010 | 반려동물 상식 퀴즈형 카드 | instagram_feed | PET_CARE | 17.24 | 1.3 | 1.2 | 1.3 | 3 | offline_ready |
| 3 | SH-017 | 반려동물 산책 준비물 점검 | shorts | PET_CARE | 16.6 | 1.0 | 1.6 | 1.3 | 3 | offline_ready |
| 4 | CN-014 | 캠핑 초보 준비물 체크리스트 | cardnews | CAMPING_TRAVEL_PACK | 16.4 | 1.0 | 1.0 | 1.2 | 2 | offline_ready |
| 5 | CN-016 | 여행 전 짐싸기 체크리스트 | cardnews | CAMPING_TRAVEL_PACK | 16.4 | 1.0 | 1.0 | 1.2 | 2 | offline_ready |
| 6 | KN-004 | 습관 형성 21일 법칙 진실 | knowledge_evergreen | LEARNING_HABIT | 16.34 | 1.3 | 1.0 | 1.2 | 2 | offline_ready |
| 7 | KN-008 | 시간관리 매트릭스 활용법 | knowledge_evergreen | REMOTE_WORK | 16.34 | 1.3 | 1.0 | 1.2 | 2 | offline_ready |
| 8 | CN-006 | 미니멀리즘 시작하는 법 | cardnews | MINIMALISM | 16.16 | 1.2 | 1.0 | 1.2 | 2 | offline_ready |
| 9 | CN-009 | 재택근무 생산성 루틴 | cardnews | REMOTE_WORK | 16.16 | 1.2 | 1.0 | 1.2 | 2 | offline_ready |
| 10 | CN-010 | 초보자를 위한 홈트레이닝 루틴 | cardnews | HOME_WORKOUT | 16.16 | 1.2 | 1.0 | 1.2 | 2 | offline_ready |
| 11 | CN-017 | 커피 원두 보관법 | cardnews | COFFEE_RITUAL | 16.16 | 1.2 | 1.0 | 1.2 | 2 | offline_ready |
| 12 | CN-025 | 온라인 강의 완주하는 습관 | cardnews | LEARNING_HABIT | 16.16 | 1.2 | 1.0 | 1.2 | 2 | offline_ready |
| 13 | IG-009 | 직장인 점심시간 활용법 | instagram_feed | REMOTE_WORK | 15.74 | 1.3 | 1.2 | 1.3 | 2 | offline_ready |
| 14 | IG-013 | 자기계발 습관 만들기 팁 | instagram_feed | LEARNING_HABIT | 15.74 | 1.3 | 1.2 | 1.3 | 2 | offline_ready |
| 15 | SH-004 | 하루 만보 걷기 루틴 브이로그형 | shorts | HOME_WORKOUT | 15.1 | 1.0 | 1.6 | 1.3 | 2 | offline_ready |
| 16 | SH-005 | 방 정리 비포애프터 | shorts | MINIMALISM | 15.1 | 1.0 | 1.6 | 1.3 | 2 | offline_ready |
| 17 | SH-006 | 커피 내리는 법 3단계 | shorts | COFFEE_RITUAL | 15.1 | 1.0 | 1.6 | 1.3 | 2 | offline_ready |
| 18 | SH-014 | 편의점 다이어트 조합 | shorts | HOME_WORKOUT | 15.1 | 1.0 | 1.6 | 1.3 | 2 | offline_ready |
| 19 | SH-016 | 지갑 정리 미니멀 챌린지 | shorts | MINIMALISM | 15.1 | 1.0 | 1.6 | 1.3 | 2 | offline_ready |
| 20 | SH-018 | 캐리어 짐싸기 순서 | shorts | CAMPING_TRAVEL_PACK | 15.1 | 1.0 | 1.6 | 1.3 | 2 | offline_ready |