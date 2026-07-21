# Instagram Broad CardNews Learning V1 — 보고서

> **개정 이력**: Spark의 `AUDIT_REPORT.md`(판정: LEARNING_IMPORT_NO_GO)에서 지적된 3개 항목 — (1) 계정 수 오기재, (2) RAW 미수록 URL 4건, (3) 상태 표기 표준 위반 — 을 `RAW_OBSERVATIONS.json`을 유일한 원본으로 삼아 수정한 개정판. 수정 상세는 `QA_REPORT.md`의 "AUDIT 수정 이력" 참고. `AUDIT_REPORT.md` 자체는 수정하지 않음.

## 개요

특정 주제로 제한하지 않고 Instagram 검색(해시태그)·탐색을 통해 다양한 카드뉴스/캐러셀 제작 방식을 폭넓게 학습하기 위한 조사. 사용자 승인 범위(좋아요·댓글·저장·팔로우·DM·공유·게시 금지, 비공개 계정 접근 금지, 개인정보 수집 금지, 문안·이미지 복제 금지)를 준수하며 진행했고, 조사 도중 "1년 이내 게시물만 수집"이라는 추가 제약이 반영되어 최종 표본은 **39건**(목표 60건)이다.

## 표본 요약

- **39개 게시물, 37개 계정, 10개 분야**(뉴스·시사, 경제·재테크, 교육·지식, 생활정보, 건강, 여행·지역, 브랜드·제품, 문화·책, 패션·뷰티, 유머·이슈) 전부 확보
- 단일 계정 최대 비중 5.1% (10% 상한 이내)
- 게시일 범위: 2025-07-19 ~ 2026-07-14(관찰 당일)
- 상세 데이터: `RAW_OBSERVATIONS.json` / 계정·분야 분포: `ACCOUNT_AND_CATEGORY_SAMPLE.json`

## 핵심 관찰

각 항목의 상태(`benchmark_observed`=evidence_urls 2건 이상 반복 관측 / `hypothesis_only`=evidence_urls 1건 또는 인과·비교 주장)는 각 라이브러리 파일에 URL·계정 수·분야 수와 함께 결속되어 있음. 아래는 그중 `benchmark_observed` 등급인 항목만 요약.

### 1. 댓글 유도형 CTA가 댓글:좋아요 비율을 반복적으로 높인다 (`benchmark_observed`, n=11, 계정 11, 분야 2)
39건 중 11건(28%)이 "댓글에 [키워드]를 남기면 DM으로 자료를 보내드립니다" 형식의 CTA를 사용했다. 이 11건 전부에서 댓글 수가 좋아요 수의 24.21%~794.12%에 달했고(대부분 100% 초과, 즉 댓글이 좋아요보다 많음), 이 CTA가 없는 게시물은 대부분 10% 미만이었다. 다만 이는 상관관계 관찰이며, "이 CTA가 반응을 유발한다"는 인과 결론은 검증되지 않았다 — 이런 CTA를 쓰는 계정 자체의 청중 특성이 혼입 변수일 수 있다.

### 2. 번호형 큐레이션 리스트 구조 (`benchmark_observed`, n=3, 계정 3, 분야 3)
"장소/계정/제품 N개를 번호로 나열하고 각 항목을 동일 포맷(위치+한줄평+팁)으로 반복"하는 구조가 여행·지역, 생활정보, 유머·이슈 3개 분야에서 반복 관찰되었다.

### 3. 시각 레이아웃은 분야보다 "제작자 유형"과 더 강하게 연관되는 경향 (`benchmark_observed` 계열 다수, 상세는 `VISUAL_LAYOUT_LIBRARY.json`)
- 병원·공공기관 계정 → 캐릭터 의인화 일러스트 + 파스텔톤(n=4, 계정 4, 분야 3)
- 개인 AI/마케팅 교육 계정 → 손글씨·스크랩북 콜라주 스타일(n=3, 계정 3, 분야 1)
- 증권/데이터 서비스 계정 → 다크 배경 + 네온 대비(n=3, 계정 3, 분야 2)
- 하이엔드 패션 브랜드 → 흑백 매거진풍 서사형(n=1, 계정 1, 분야 1 — `hypothesis_only`, 단일 관측)

### 4. 출처/광고 라벨 표기는 전반적으로 희박하다
39건 중 출처를 명시한 것은 3건(`benchmark_observed`), 실무자 인터뷰 인용형은 2건(`benchmark_observed`), 광고/협찬을 자기 표기한 것은 3건(`benchmark_observed`)이었다. Instagram 공식 "유료 파트너십" 라벨이 붙은 사례는 0건(부재 통계, confidence 미부여) — 카드뉴스 포맷이 저널리즘적 출처 표기 관행과는 거리가 있음을 시사한다.

## 표본 한계 (반드시 참고)

- **60건 목표 대비 39건**: 1년 이내 필터를 소급 적용하며 기존 수집분 28건이 제외되었고, 추가 보강에도 60건에는 미달했다. 상세 사유와 제외 목록은 `QA_REPORT.md` 참고.
- **팔로워 수 대부분 미확인(37개 중 2개만 확인)**: "계정 규모가 비슷한 표본끼리 비교"는 이 2건 외에는 수행하지 못했다. 대신 팔로워 수에 의존하지 않는 댓글:좋아요 비율로 CTA 효과를 비교했다.
- **브랜드·제품(1건), 문화·책(1건)은 표본이 극히 얇음**: 이 두 분야 관련 학습 후보는 `hypothesis_only`로 표기했으며, 추가 조사 없이 확정적 결론으로 사용해서는 안 된다.
- **CN-006 비교는 사용자 지시에 따라 이번 단계에서 다루지 않음.**

## 파일 구성

- `RAW_OBSERVATIONS.json` — 39건 원자료(URL, 계정, 슬라이드 구조, 지표 등 전 항목) — **유일한 원본(canonical source)**
- `ACCOUNT_AND_CATEGORY_SAMPLE.json` — 계정/분야 분포 및 편중 검사(unique_accounts=37)
- `CARDNEWS_FEATURE_TAXONOMY.json` — 포맷 유형(캐러셀/모션 하이브리드/앱UI 목업 등) 분류
- `HOOK_PATTERN_LIBRARY.json` — 훅 문구 유형 15개 항목(evidence_urls/observation_count/account_count/category_count/confidence 결속)
- `STORY_STRUCTURE_LIBRARY.json` — 스토리 구조 10종(동일 결속)
- `VISUAL_LAYOUT_LIBRARY.json` — 시각 레이아웃 9개 계열(동일 결속)
- `CTA_AND_EVIDENCE_PATTERNS.json` — CTA 유형 및 출처/광고 표기 패턴(동일 결속)
- `ENGAGEMENT_BENCHMARKS.json` — 좋아요 3분위 비교, CTA별 댓글:좋아요 비율
- `LEARNING_CANDIDATES.json` — confidence 표기된 학습 후보 6건(동일 결속)
- `QA_REPORT.md` — QA 체크리스트 + AUDIT 수정 이력
